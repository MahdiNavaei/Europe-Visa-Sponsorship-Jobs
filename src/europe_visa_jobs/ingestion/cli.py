from __future__ import annotations

import argparse
import asyncio
import json
from contextlib import nullcontext
from pathlib import Path

import httpx

from europe_visa_jobs.db.locking import database_write_lock
from europe_visa_jobs.db.session import SessionLocal, init_db
from europe_visa_jobs.db.source_registry import SourceRegistry
from europe_visa_jobs.discovery.orchestrator import discover_and_validate
from europe_visa_jobs.discovery.snapshot import build_snapshot
from europe_visa_jobs.ingestion.pipeline import ingest_source
from europe_visa_jobs.ingestion.sources import load_sources
from europe_visa_jobs.ingestion.sponsors import (
    import_production_sponsor_evidence,
    import_sponsor_csv,
)
from europe_visa_jobs.schemas import ATSProvider
from europe_visa_jobs.settings import get_settings


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Europe Visa Sponsorship Jobs ingestion CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    jobs = subparsers.add_parser("jobs", help="Fetch and normalize ATS sources")
    jobs.add_argument("--sources", help="Path to source JSON")
    jobs.add_argument("--registry", action="store_true", help="Ingest verified enabled registry sources")
    jobs.add_argument("--only-uningested", action="store_true", help="Resume with verified boards not yet successfully ingested")
    jobs.add_argument("--provider", action="append", choices=[provider.value for provider in ATSProvider], help="Limit registry ingestion to one or more providers")
    jobs.add_argument("--limit", type=int, default=None, help="Limit registry sources")
    jobs.add_argument("--largest-first", action="store_true", help="Prioritize verified un-ingested boards with the most recently observed jobs")

    sponsors = subparsers.add_parser("sponsors", help="Import verified sponsor registry records")
    sponsors.add_argument("--file", required=True, help="CSV with company_name,country,registry_name,source_url")
    sponsors.add_argument("--production", action="store_true", help="Bulk-load the packaged official evidence cache")

    sources = subparsers.add_parser("sources", help="Discover, validate, and inspect the ATS source registry")
    source_commands = sources.add_subparsers(dest="source_command", required=True)
    bootstrap = source_commands.add_parser("bootstrap", help="Import static seeds as manual registry entries")
    bootstrap.add_argument("--config", default="config/sources.json")
    bootstrap.add_argument("--snapshot", help="Verified registry snapshot to import before manual seeds")
    snapshot = source_commands.add_parser("snapshot", help="Export the verified registry as a packaged bootstrap artifact")
    snapshot.add_argument("--output", default="config/source-registry.snapshot.json")
    snapshot.add_argument("--minimum-verified", type=int, default=500)
    discover = source_commands.add_parser("discover", help="Run additive board discovery and live validation")
    discover.add_argument("--mode", choices=("recent", "full"), default="recent")
    discover.add_argument("--provider", action="append", choices=[provider.value for provider in ATSProvider])
    discover.add_argument("--method", action="append", choices=("manual", "wayback", "common_crawl", "urlscan"))
    discover.add_argument("--limit", type=int, default=None)
    discover.add_argument("--batch-size", type=int, default=None, help="Maximum due candidates validated in this run")
    discover.add_argument("--force", action="store_true", help="Ignore retry deadlines for the selected candidates")
    discover.add_argument("--full-content", action="store_true", help="Fetch public job payloads during validation to measure observed volume")
    discover.add_argument("--config", default="config/sources.json")
    validate = source_commands.add_parser("validate", help="Validate a bounded set of manual/registry candidates")
    validate.add_argument("--provider", action="append", choices=[provider.value for provider in ATSProvider])
    validate.add_argument("--limit", type=int, default=None)
    validate.add_argument("--batch-size", type=int, default=None, help="Maximum due candidates validated in this run")
    validate.add_argument("--force", action="store_true", help="Ignore retry deadlines for the selected candidates")
    validate.add_argument("--full-content", action="store_true", help="Fetch public job payloads during validation to measure observed volume")
    validate.add_argument("--config", default="config/sources.json")
    health = source_commands.add_parser("health", help="Show source health and coverage")
    health.add_argument("--json", action="store_true")
    health.add_argument("--limit", type=int, default=100)
    retry = source_commands.add_parser("retry-failed", help="Retry only degraded, failing, or blocked sources")
    retry.add_argument("--limit", type=int, default=None)
    return parser


def _safe_ingestion_concurrency(settings) -> int:
    # SQLite serializes writers; Postgres can use the configured bounded fan-out.
    database_url = getattr(settings, "database_url", "")
    configured = getattr(settings, "ingestion_concurrency", 1)
    return 1 if database_url.startswith("sqlite") else max(1, configured)


async def _ingest(
    path: str | None,
    *,
    registry_mode: bool = False,
    only_uningested: bool = False,
    providers: set[str] | None = None,
    limit: int | None = None,
    largest_first: bool = False,
) -> None:
    settings = get_settings()
    if registry_mode:
        with SessionLocal() as session:
            registry = SourceRegistry(session)
            items = registry.un_ingested_verified_sources(
                providers=providers,
                limit=limit,
                largest_first=largest_first,
            ) if only_uningested else registry.list_sources(
                verified_only=True,
                statuses={"healthy", "degraded", "failing", "empty"},
                limit=limit,
            )
            sources = [registry.to_config(item) for item in items if providers is None or item.provider in providers]
    else:
        if not path:
            raise RuntimeError("--sources is required unless --registry is used")
        sources = load_sources(path)
    timeout = httpx.Timeout(settings.request_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        semaphore = asyncio.Semaphore(_safe_ingestion_concurrency(settings))

        async def ingest_one(source):
            async with semaphore:
                try:
                    with SessionLocal() as session:
                        run = await ingest_source(session, source, client=client)
                    return source, run, None
                except Exception as exc:
                    return source, None, exc

        results = await asyncio.gather(*(ingest_one(source) for source in sources))
    failures: list[str] = []
    for source, run, error in results:
        if error is None:
            print(f"{source.provider.value}:{source.slug} fetched={run.fetched_count} stored={run.stored_count} status={run.status}")
        else:
            label = f"{source.provider.value}:{source.slug}"
            failures.append(label)
            print(f"{label} fetched=0 stored=0 status=failed error={str(error)[:300]}")
    if failures:
        raise RuntimeError(f"{len(failures)} source(s) failed after processing the full batch: {', '.join(failures)}")


async def _ingest_failed(sources) -> None:
    settings = get_settings()
    timeout = httpx.Timeout(settings.request_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        semaphore = asyncio.Semaphore(_safe_ingestion_concurrency(settings))

        async def ingest_one(source):
            async with semaphore:
                try:
                    with SessionLocal() as session:
                        run = await ingest_source(session, source, client=client)
                    return source, run, None
                except Exception as exc:
                    return source, None, exc

        results = await asyncio.gather(*(ingest_one(source) for source in sources))
    failures: list[str] = []
    for source, run, error in results:
        if error is None:
            print(f"{source.provider.value}:{source.slug} fetched={run.fetched_count} stored={run.stored_count} status={run.status}")
        else:
            label = f"{source.provider.value}:{source.slug}"
            failures.append(label)
            print(f"{label} status=failed error={str(error)[:300]}")
    if failures:
        raise RuntimeError(f"{len(failures)} failed source(s) remain: {', '.join(failures)}")


def _run(args: argparse.Namespace) -> None:
    if args.command == "jobs":
        asyncio.run(
            _ingest(
                args.sources,
                registry_mode=args.registry,
                only_uningested=args.only_uningested,
                providers=set(args.provider) if args.provider else None,
                limit=args.limit,
                largest_first=args.largest_first,
            )
        )
    elif args.command == "sponsors":
        with SessionLocal() as session:
            count = import_production_sponsor_evidence(session, args.file) if args.production else import_sponsor_csv(session, args.file)
        print(f"imported {count} sponsor records")
    elif args.command == "sources":
        if args.source_command == "bootstrap":
            with SessionLocal() as session:
                registry = SourceRegistry(session)
                if args.snapshot:
                    for config in load_sources(args.snapshot, minimum_snapshot_sources=500):
                        registry.import_verified_snapshot(config)
                configs = load_sources(args.config)
                for config in configs:
                    registry.import_config(config.model_copy(update={"manual_override": True}))
                session.commit()
            print(f"bootstrapped {len(configs)} source seeds" + (" and verified registry snapshot" if args.snapshot else ""))
        elif args.source_command == "snapshot":
            if args.minimum_verified < 1:
                raise ValueError("--minimum-verified must be positive")
            with SessionLocal() as session:
                payload = build_snapshot(SourceRegistry(session).list_sources(verified_only=True))
            # validate_snapshot is intentionally exercised by the loader before
            # a package can use this artifact; the threshold guards accidental
            # publication of a small/demo registry.
            if payload["verified_source_count"] < args.minimum_verified:
                raise RuntimeError(
                    f"refusing to write a suspiciously small registry snapshot: "
                    f"{payload['verified_source_count']} verified boards < {args.minimum_verified}"
                )
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(f"wrote {payload['verified_source_count']} verified boards to {output}")
        elif args.source_command == "discover":
            providers = {ATSProvider(item) for item in args.provider} if args.provider else None
            methods = set(args.method) if args.method else None
            with SessionLocal() as session:
                result = asyncio.run(discover_and_validate(session, mode=args.mode, providers=providers, methods=methods, limit=args.limit, batch_size=args.batch_size, force=args.force, probe_only=not args.full_content, seed_path=args.config))
            print(json.dumps(result, indent=2, default=str))
        elif args.source_command == "validate":
            providers = {ATSProvider(item) for item in args.provider} if args.provider else None
            with SessionLocal() as session:
                result = asyncio.run(
                    discover_and_validate(
                        session,
                        mode="recent",
                        providers=providers,
                        methods={"manual"},
                        limit=args.limit,
                        batch_size=args.batch_size,
                        force=args.force,
                        probe_only=not args.full_content,
                        seed_path=args.config,
                    )
                )
            print(json.dumps(result, indent=2, default=str))
        elif args.source_command == "health":
            with SessionLocal() as session:
                registry = SourceRegistry(session)
                payload = {
                    "coverage": registry.coverage(),
                    "sources": [
                        {
                            "id": source.id,
                            "provider": source.provider,
                            "board_identifier": source.board_identifier,
                            "company_name": source.company_name,
                            "status": source.status,
                            "enabled": source.enabled,
                            "consecutive_failures": source.consecutive_failures,
                            "last_http_status": source.last_http_status,
                            "last_error_category": source.last_error_category,
                            "last_error": source.last_error,
                        }
                        for source in registry.list_sources(limit=args.limit)
                    ],
                }
            print(json.dumps(payload, indent=2, default=str) if args.json else json.dumps(payload["coverage"], indent=2, default=str))
        elif args.source_command == "retry-failed":
            with SessionLocal() as session:
                registry = SourceRegistry(session)
                sources = [registry.to_config(item) for item in registry.failed_sources(limit=args.limit)]
            asyncio.run(_ingest_failed(sources))


def main() -> None:
    args = _parser().parse_args()
    # Health reporting is read-only. Every other command can mutate the local
    # registry/jobs database, including init_db's SQLite schema checks.
    writes_database = args.command != "sources" or args.source_command != "health"
    context = database_write_lock(get_settings().database_url) if writes_database else nullcontext()
    with context:
        init_db()
        _run(args)


if __name__ == "__main__":  # pragma: no cover
    main()

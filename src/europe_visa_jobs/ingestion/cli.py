from __future__ import annotations

import argparse
import asyncio

import httpx

from europe_visa_jobs.db.session import SessionLocal, init_db
from europe_visa_jobs.ingestion.pipeline import ingest_source
from europe_visa_jobs.ingestion.sources import load_sources
from europe_visa_jobs.ingestion.sponsors import import_sponsor_csv
from europe_visa_jobs.settings import get_settings


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Europe Visa Sponsorship Jobs ingestion CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    jobs = subparsers.add_parser("jobs", help="Fetch and normalize configured ATS sources")
    jobs.add_argument("--sources", required=True, help="Path to source JSON")

    sponsors = subparsers.add_parser("sponsors", help="Import verified sponsor registry records")
    sponsors.add_argument("--file", required=True, help="CSV with company_name,country,registry_name,source_url")
    return parser


async def _ingest(path: str) -> None:
    settings = get_settings()
    sources = load_sources(path)
    timeout = httpx.Timeout(settings.request_timeout_seconds)
    failures: list[str] = []

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for source in sources:
            try:
                with SessionLocal() as session:
                    run = await ingest_source(session, source, client=client)
                print(
                    f"{source.provider.value}:{source.slug} fetched={run.fetched_count} "
                    f"stored={run.stored_count} status={run.status}"
                )
            except Exception as exc:
                label = f"{source.provider.value}:{source.slug}"
                failures.append(label)
                print(f"{label} fetched=0 stored=0 status=failed error={str(exc)[:300]}")

    if failures:
        joined = ", ".join(failures)
        raise RuntimeError(f"{len(failures)} source(s) failed after processing the full batch: {joined}")


def main() -> None:
    args = _parser().parse_args()
    init_db()
    if args.command == "jobs":
        asyncio.run(_ingest(args.sources))
    elif args.command == "sponsors":
        with SessionLocal() as session:
            count = import_sponsor_csv(session, args.file)
        print(f"imported {count} sponsor records")


if __name__ == "__main__":  # pragma: no cover
    main()

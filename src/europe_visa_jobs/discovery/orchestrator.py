from __future__ import annotations

import asyncio
from collections import Counter
from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from europe_visa_jobs.db.source_registry import SourceRegistry
from europe_visa_jobs.discovery.methods import (
    common_crawl_candidates,
    common_crawl_index,
    urlscan_candidates,
    wayback_candidates,
)
from europe_visa_jobs.discovery.patterns import (
    IdentifiedSource,
    identify_config,
    identify_source_url,
)
from europe_visa_jobs.discovery.validation import validate_candidate
from europe_visa_jobs.ingestion.sources import load_sources
from europe_visa_jobs.schemas import ATSProvider, SourceCandidate, SourceValidation
from europe_visa_jobs.settings import get_settings


async def discover_and_validate(
    session: Session,
    *,
    mode: str = "recent",
    providers: set[ATSProvider] | None = None,
    methods: set[str] | None = None,
    limit: int | None = None,
    seed_path: str = "config/sources.json",
) -> dict[str, int | float | dict[str, int] | str]:
    """Union discovery indexes, validate candidates, and persist only live boards as enabled."""
    settings = get_settings()
    # The default universe is every provider with a discovery/validation
    # boundary.  Callers can still pass an explicit subset for bounded runs.
    selected = providers or set(ATSProvider)
    chosen_methods = methods or ({"manual", "wayback", "urlscan"} if mode == "recent" else {"manual", "wayback", "common_crawl", "urlscan"})
    registry = SourceRegistry(session)
    run = registry.create_discovery_run(mode, sorted(chosen_methods))
    # Make long index scans observable before any network work begins. A
    # process interruption must leave an unfinished run that operators can
    # distinguish from a scan that never started.
    session.commit()
    started = asyncio.get_running_loop().time()
    candidates: dict[tuple[str, str], SourceCandidate] = {}

    if "manual" in chosen_methods:
        for config in load_sources(seed_path):
            if config.provider in selected:
                identified = identify_config(config)
                item = SourceCandidate(
                    provider=config.provider,
                    board_identifier=config.board_identifier,
                    canonical_url=identified.canonical_url,
                    api_url=identified.api_url,
                    company_name=config.company_name,
                    country_hint=config.default_country,
                    discovery_method="manual_seed",
                    metadata=config.metadata,
                )
                candidates[(item.provider.value, item.board_identifier)] = item

    timeout = httpx.Timeout(settings.discovery_timeout_seconds)
    limits = httpx.Limits(max_connections=max(settings.discovery_concurrency * 2, 16), max_keepalive_connections=settings.discovery_concurrency)
    index_errors: list[str] = []
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, limits=limits) as client:
        common_crawl_api: str | None = None
        if "common_crawl" in chosen_methods:
            try:
                common_crawl_api = await common_crawl_index(client)
            except Exception as exc:
                index_errors.append(f"common_crawl: {str(exc)[:500]}")
        for provider in sorted(selected, key=lambda item: item.value):
            try:
                if "wayback" in chosen_methods:
                    items = await wayback_candidates(client, provider, recent_days=30 if mode == "recent" else None, max_rows=limit)
                    candidates.update({(item.provider.value, item.board_identifier): item for item in items})
                if "common_crawl" in chosen_methods:
                    if common_crawl_api is None:
                        continue
                    page_limit = settings.discovery_common_crawl_max_pages
                    if limit:
                        page_limit = min(page_limit, 5)
                    items = await common_crawl_candidates(
                        client,
                        provider,
                        max_pages=max(1, page_limit),
                        collection_api=common_crawl_api,
                    )
                    candidates.update({(item.provider.value, item.board_identifier): item for item in items})
                if "urlscan" in chosen_methods and mode == "recent":
                    items = await urlscan_candidates(client, provider)
                    candidates.update({(item.provider.value, item.board_identifier): item for item in items})
            except Exception as exc:
                index_errors.append(f"{provider.value}: {str(exc)[:500]}")

        run.error = "; ".join(index_errors)[:2000] if index_errors else None

        known = {(source.provider, source.board_identifier): source for source in registry.list_sources()}
        for key, source in known.items():
            if source.verified_at is not None:
                candidates.setdefault(key, SourceCandidate(
                    provider=ATSProvider(source.provider),
                    board_identifier=source.board_identifier,
                    canonical_url=source.board_url or source.careers_url or "",
                    api_url=source.api_url,
                    company_name=source.company_name,
                    country_hint=source.country_hint,
                    discovery_method="previous_registry",
                    metadata=source.source_metadata or {},
                ))

        if limit:
            # Keep a bounded run representative across providers instead of
            # spending the whole limit on whichever index was visited first.
            grouped: dict[str, list[SourceCandidate]] = {}
            for item in candidates.values():
                grouped.setdefault(item.provider.value, []).append(item)
            candidate_list = []
            max_group_size = max((len(items) for items in grouped.values()), default=0)
            for position in range(max_group_size):
                for provider in sorted(grouped):
                    items = grouped[provider]
                    if position < len(items):
                        candidate_list.append(items[position])
                        if len(candidate_list) == limit:
                            break
                if len(candidate_list) == limit:
                    break
        else:
            candidate_list = list(candidates.values())
        semaphore = asyncio.Semaphore(settings.discovery_concurrency)

        async def validate_one(item: SourceCandidate):
            async with semaphore:
                identified = identify_source_url(item.canonical_url)
                if identified is None and item.api_url:
                    identified = identify_source_url(item.api_url)
                if identified is None:
                    identified = IdentifiedSource(item.provider, item.board_identifier, item.canonical_url, item.api_url, dict(item.metadata))
                if identified is None:
                    return item, None
                identified.metadata.update(item.metadata)
                try:
                    result = await validate_candidate(client, identified)
                except Exception as exc:
                    result = SourceValidation(
                        valid=False,
                        provider=item.provider,
                        board_identifier=item.board_identifier,
                        canonical_url=item.canonical_url,
                        api_url=item.api_url,
                        error_category="validation_exception",
                        error=str(exc)[:1000],
                    )
                return item, result

        counts: Counter[str] = Counter()
        run.candidate_count = len(candidate_list)
        session.commit()
        checkpoint_size = max(1, settings.discovery_checkpoint_size)

        async def persist_result(item: SourceCandidate, validation: SourceValidation | None) -> None:
            source = registry.upsert_candidate(item, enabled=False)
            if validation is None:
                counts["invalid"] += 1
                return
            registry.record_validation(source, validation, run_id=run.id)
            counts["validated" if validation.valid else "failed"] += 1
            counts[f"provider:{item.provider.value}"] += 1 if validation.valid else 0

        tasks = [asyncio.create_task(validate_one(item)) for item in candidate_list]
        try:
            for completed in asyncio.as_completed(tasks):
                item, validation = await completed
                await persist_result(item, validation)
                processed = counts["validated"] + counts["invalid"] + counts["failed"]
                if processed % checkpoint_size == 0:
                    run.validated_count = counts["validated"]
                    run.invalid_count = counts["invalid"]
                    run.failed_count = counts["failed"]
                    run.provider_counts = {
                        key.split(":", 1)[1]: value
                        for key, value in counts.items()
                        if key.startswith("provider:")
                    }
                    session.commit()
        except BaseException:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise

        run.validated_count = counts["validated"]
        run.invalid_count = counts["invalid"]
        run.failed_count = counts["failed"]
        run.provider_counts = {
            key.split(":", 1)[1]: value for key, value in counts.items() if key.startswith("provider:")
        }
        run.finished_at = datetime.now(UTC)
        session.commit()
    return {
        "mode": mode,
        "candidate_count": len(candidate_list),
        "validated_count": counts["validated"],
        "invalid_count": counts["invalid"],
        "failed_count": counts["failed"],
        "duration_seconds": round(asyncio.get_running_loop().time() - started, 2),
        "provider_counts": run.provider_counts,
    }

from __future__ import annotations

import asyncio
from collections import Counter, defaultdict
from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from europe_visa_jobs.db.models import Source
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
    plausible_identifier,
)
from europe_visa_jobs.discovery.validation import validate_candidate
from europe_visa_jobs.ingestion.sources import load_sources
from europe_visa_jobs.schemas import ATSProvider, SourceCandidate, SourceValidation
from europe_visa_jobs.settings import get_settings


def _failure_payload(counts: Counter[str]) -> dict[str, int]:
    return dict(sorted(((key, value) for key, value in counts.items() if value), key=lambda item: item[0]))


async def discover_and_validate(
    session: Session,
    *,
    mode: str = "recent",
    providers: set[ATSProvider] | None = None,
    methods: set[str] | None = None,
    limit: int | None = None,
    batch_size: int | None = None,
    force: bool = False,
    probe_only: bool = True,
    seed_path: str = "config/sources.json",
) -> dict[str, object]:
    """Discover candidates, apply quality filters, and validate one durable batch.

    Discovery is additive. Every candidate is persisted, but only sources whose
    retry deadline has arrived enter the bounded validation batch. This keeps
    permanent 404s and already-verified boards out of repeated network runs while
    allowing new and transient candidates to move through the queue.
    """
    settings = get_settings()
    selected = providers or set(ATSProvider)
    chosen_methods = methods or (
        {"manual", "wayback", "urlscan"} if mode == "recent" else {"manual", "wayback", "common_crawl", "urlscan"}
    )
    registry = SourceRegistry(session)
    run = registry.create_discovery_run(mode, sorted(chosen_methods))
    session.commit()
    started = asyncio.get_running_loop().time()
    candidates: dict[tuple[str, str], SourceCandidate] = {}
    harvest_metrics: dict[str, dict[str, int]] = defaultdict(dict)

    if "manual" in chosen_methods:
        for config in load_sources(seed_path):
            if config.provider not in selected:
                continue
            identified = identify_config(config)
            if not plausible_identifier(config.provider, identified.board_identifier):
                continue
            item = SourceCandidate(
                provider=config.provider,
                board_identifier=identified.board_identifier,
                canonical_url=identified.canonical_url,
                api_url=identified.api_url,
                company_name=config.company_name,
                country_hint=config.default_country,
                discovery_method="manual_seed",
                metadata=config.metadata,
            )
            candidates[(item.provider.value, item.board_identifier)] = item
            metric = harvest_metrics[item.provider.value]
            metric["raw"] = metric.get("raw", 0) + 1
            metric["accepted"] = metric.get("accepted", 0) + 1

    timeout = httpx.Timeout(settings.discovery_timeout_seconds)
    limits = httpx.Limits(
        max_connections=max(settings.discovery_concurrency * 2, 16),
        max_keepalive_connections=settings.discovery_concurrency,
    )
    index_errors: list[str] = []
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, limits=limits) as client:
        common_crawl_api: str | None = None
        if "common_crawl" in chosen_methods:
            try:
                common_crawl_api = await common_crawl_index(client)
            except Exception as exc:
                index_errors.append(f"common_crawl: {str(exc)[:500]}")

        for provider in sorted(selected, key=lambda item: item.value):
            metric = harvest_metrics[provider.value]
            try:
                if "wayback" in chosen_methods:
                    items = await wayback_candidates(
                        client,
                        provider,
                        recent_days=30 if mode == "recent" else None,
                        max_rows=limit,
                        stats=metric,
                    )
                    candidates.update({(item.provider.value, item.board_identifier): item for item in items})
                if "common_crawl" in chosen_methods and common_crawl_api is not None:
                    page_limit = settings.discovery_common_crawl_max_pages
                    if limit:
                        page_limit = min(page_limit, 5)
                    items = await common_crawl_candidates(
                        client,
                        provider,
                        max_pages=max(1, page_limit),
                        collection_api=common_crawl_api,
                        stats=metric,
                    )
                    candidates.update({(item.provider.value, item.board_identifier): item for item in items})
                if "urlscan" in chosen_methods and mode == "recent":
                    items = await urlscan_candidates(
                        client,
                        provider,
                        stats=metric,
                        max_pages=getattr(settings, "discovery_urlscan_max_pages", 10),
                        errors=index_errors,
                    )
                    candidates.update({(item.provider.value, item.board_identifier): item for item in items})
            except Exception as exc:
                index_errors.append(f"{provider.value}: {str(exc)[:500]}")

        # Previous verified and retryable registry entries are a durable source of
        # candidates independent of archive availability.
        for source in registry.list_sources():
            if source.provider not in {provider.value for provider in selected}:
                continue
            if not source.verified_at and source.validation_state in {"invalid", "blocked"}:
                continue
            candidate = SourceCandidate(
                provider=ATSProvider(source.provider),
                board_identifier=source.board_identifier,
                canonical_url=source.board_url or source.careers_url or "",
                api_url=source.api_url,
                company_name=source.company_name,
                country_hint=source.country_hint,
                discovery_method="previous_registry",
                metadata=source.source_metadata or {},
            )
            candidates.setdefault((candidate.provider.value, candidate.board_identifier), candidate)

        # A final provider-aware filter protects manual/previous-registry records
        # and makes the before/after funnel explicit in the run record.
        filtered: dict[tuple[str, str], SourceCandidate] = {}
        for key, item in candidates.items():
            if plausible_identifier(item.provider, item.board_identifier):
                filtered[key] = item
        candidates = filtered
        run.candidate_before_filter_count = max(
            len(candidates), sum(metric.get("raw", 0) for metric in harvest_metrics.values())
        )
        run.candidate_after_filter_count = len(candidates)

        pending: list[tuple[int, SourceCandidate, Source]] = []
        now = datetime.now(UTC)
        for item in candidates.values():
            source = registry.upsert_candidate(item, enabled=False)
            if not registry.should_validate(source, now=now, force=force):
                run.skipped_cached_count += 1
                continue
            priority = {
                "discovered": 0,
                "pending_validation": 0,
                "retry_later": 1,
                "transient_failure": 1,
                "verified": 2,
                "invalid": 3,
                "blocked": 3,
            }.get(source.validation_state, 2)
            pending.append((priority, item, source))

        pending.sort(key=lambda value: (value[0], value[1].provider.value, value[1].board_identifier))
        max_batch = int(batch_size or limit or getattr(settings, "discovery_batch_size", 250))  # type: ignore[arg-type]
        selected_batch = pending[:max(1, max_batch)]
        # Only work actually selected for this run may transition to pending.
        # Marking the whole candidate universe first makes an interrupted or
        # bounded run erase the current verified state of unselected boards.
        for _, _, source in selected_batch:
            registry.mark_pending(source)
        run.candidate_count = len(selected_batch)
        session.commit()

        semaphore = asyncio.Semaphore(settings.discovery_concurrency)

        async def validate_one(item: SourceCandidate) -> tuple[SourceCandidate, SourceValidation | None]:
            async with semaphore:
                identified = identify_source_url(item.canonical_url)
                if identified is None and item.api_url:
                    identified = identify_source_url(item.api_url)
                if identified is None:
                    identified = IdentifiedSource(
                        item.provider,
                        item.board_identifier,
                        item.canonical_url,
                        item.api_url,
                        dict(item.metadata),
                    )
                identified.metadata.update(item.metadata)
                try:
                    try:
                        result = await validate_candidate(client, identified, probe_only=probe_only)
                    except TypeError as exc:
                        # Keep small test doubles and downstream integrations that
                        # still expose the pre-probe callable compatible.
                        if "probe_only" not in str(exc):
                            raise
                        result = await validate_candidate(client, identified)
                except Exception as exc:
                    result = SourceValidation(
                        valid=False,
                        provider=item.provider,
                        board_identifier=item.board_identifier,
                        canonical_url=item.canonical_url,
                        api_url=item.api_url,
                        error_category="validation_exception",
                        failure_type="validation_exception",
                        error=str(exc)[:1000],
                    )
                return item, result

        attempted = Counter[str]()
        verified = Counter[str]()
        failures = Counter[str]()
        provider_failures: dict[str, Counter[str]] = defaultdict(Counter)
        checkpoint_size = max(1, settings.discovery_checkpoint_size)

        async def persist_result(item: SourceCandidate, validation: SourceValidation | None) -> None:
            source = registry.get(item.provider, item.board_identifier)
            if source is None:
                source = registry.upsert_candidate(item, enabled=False)
            attempted[item.provider.value] += 1
            if validation is None:
                validation = SourceValidation(
                    valid=False,
                    provider=item.provider,
                    board_identifier=item.board_identifier,
                    canonical_url=item.canonical_url,
                    api_url=item.api_url,
                    error_category="endpoint_error",
                    failure_type="endpoint_error",
                    error="candidate could not be canonicalized",
                )
            registry.record_validation(source, validation, run_id=run.id)
            if validation.valid:
                verified[item.provider.value] += 1
            else:
                category = validation.failure_type or validation.error_category or "unknown"
                failures[category] += 1
                provider_failures[item.provider.value][category] += 1

        tasks = [asyncio.create_task(validate_one(item)) for _, item, _ in selected_batch]
        try:
            for completed in asyncio.as_completed(tasks):
                item, validation = await completed
                await persist_result(item, validation)
                processed = sum(attempted.values())
                if processed % checkpoint_size == 0:
                    run.validated_count = sum(verified.values())
                    run.failed_count = sum(failures.values())
                    run.provider_counts = dict(verified)
                    run.failure_breakdown = _failure_payload(failures)
                    run.provider_failure_breakdown = {
                        provider: _failure_payload(counts) for provider, counts in provider_failures.items()
                    }
                    session.commit()
        except BaseException:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            run.error = "validation batch interrupted before completion; pending candidates remain retryable"
            session.commit()
            raise

        run.validated_count = sum(verified.values())
        run.invalid_count = 0  # malformed candidates are filtered before this batch
        run.failed_count = sum(failures.values())
        run.provider_counts = dict(verified)
        run.failure_breakdown = _failure_payload(failures)
        run.provider_failure_breakdown = {
            provider: _failure_payload(counts) for provider, counts in provider_failures.items()
        }
        run.finished_at = datetime.now(UTC)
        session.commit()

    return {
        "mode": mode,
        "candidate_count": run.candidate_count,
        "candidate_before_filter_count": run.candidate_before_filter_count,
        "candidate_after_filter_count": run.candidate_after_filter_count,
        "skipped_cached_count": run.skipped_cached_count,
        "validated_count": run.validated_count,
        "invalid_count": run.invalid_count,
        "failed_count": run.failed_count,
        "duration_seconds": round(asyncio.get_running_loop().time() - started, 2),
        "provider_counts": run.provider_counts,
        "failure_breakdown": run.failure_breakdown,
        "provider_failure_breakdown": run.provider_failure_breakdown,
        "harvest_metrics": dict(harvest_metrics),
        "index_errors": index_errors,
    }

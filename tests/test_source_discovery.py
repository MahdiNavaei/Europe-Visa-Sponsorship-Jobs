from __future__ import annotations

from datetime import UTC, datetime, timedelta

from europe_visa_jobs.db.models import Company, Job
from europe_visa_jobs.db.source_registry import SourceRegistry
from europe_visa_jobs.discovery.patterns import identify_source_url
from europe_visa_jobs.schemas import (
    ATSProvider,
    SourceCandidate,
    SourceConfig,
    SourceStatus,
    SourceValidation,
    SourceValidationState,
)


def test_provider_patterns_namespace_board_ids_and_canonical_urls():
    cases = {
        "https://boards.greenhouse.io/acme/jobs/123": (ATSProvider.GREENHOUSE, "acme"),
        "https://jobs.eu.lever.co/acme/abc": (ATSProvider.LEVER, "acme"),
        "https://jobs.ashbyhq.com/acme/abc": (ATSProvider.ASHBY, "acme"),
        "https://acme.recruitee.com/o/data-engineer": (ATSProvider.RECRUITEE, "acme"),
        "https://jobs.smartrecruiters.com/Acme/123": (ATSProvider.SMARTRECRUITERS, "acme"),
    }
    for url, (provider, identifier) in cases.items():
        result = identify_source_url(url)
        assert result is not None
        assert (result.provider, result.board_identifier) == (provider, identifier)
        assert result.api_url


def test_registry_health_transitions_and_coverage(db_session):
    registry = SourceRegistry(db_session)
    candidate = SourceCandidate(
        provider=ATSProvider.GREENHOUSE,
        board_identifier="acme",
        canonical_url="https://boards.greenhouse.io/acme",
        api_url="https://boards-api.greenhouse.io/v1/boards/acme/jobs",
        company_name="Acme",
        discovery_method="test",
    )
    source = registry.upsert_candidate(candidate)
    registry.record_validation(source, SourceValidation(valid=False, provider=ATSProvider.GREENHOUSE, board_identifier="acme", canonical_url=candidate.canonical_url, http_status=503, error_category="server_error"))
    assert source.status == SourceStatus.DEGRADED
    registry.record_validation(source, SourceValidation(valid=True, provider=ATSProvider.GREENHOUSE, board_identifier="acme", canonical_url=candidate.canonical_url, job_count=2, http_status=200))
    registry.record_ingestion_counts(source, raw_jobs=2, technical_jobs=2, active_jobs=2, eligible_jobs=1, unknown_jobs=1, rejected_jobs=0)
    db_session.commit()
    coverage = registry.coverage()
    assert coverage["verified_sources"] == 1
    assert coverage["live_verified_sources"] == 1
    assert coverage["active_jobs"] == 0  # no Job rows were fabricated by registry accounting
    assert coverage["raw_jobs_scanned"] == 2
    assert coverage["european_ai_data_ml_jobs"] == 0


def test_coverage_counts_explicit_europe_location_regardless_of_remote_word_order(db_session):
    db_session.add(
        Company(
            name="Europe Remote Co",
            normalized_name="europe remote co",
            country=None,
        )
    )
    db_session.flush()
    company = db_session.query(Company).one()
    db_session.add(
        Job(
            company_id=company.id,
            external_id="europe-1",
            provider="greenhouse",
            source_slug="europe-remote-co",
            company_name=company.name,
            title="Senior Software Engineer",
            description="",
            location="Europe (Full Remote)",
            apply_url="https://example.test/jobs/europe-1",
            job_family="software_engineering",
            eligibility_status="unknown",
            active=True,
        )
    )
    db_session.commit()

    coverage = SourceRegistry(db_session).coverage()
    assert coverage["european_technical_jobs"] == 1


def test_registry_filters_and_cache_round_trip(db_session):
    registry = SourceRegistry(db_session)
    config = SourceConfig(
        provider=ATSProvider.GREENHOUSE,
        company_name="Acme",
        slug="acme",
        careers_url="https://boards.greenhouse.io/acme",
        enabled=True,
        manual_override=True,
    )
    source = registry.import_config(config)
    registry.record_validation(
        source,
        SourceValidation(
            valid=True,
            provider=ATSProvider.GREENHOUSE,
            board_identifier="acme",
            canonical_url=config.careers_url,
            job_count=0,
            http_status=200,
            etag="v1",
        ),
    )
    db_session.commit()
    assert registry.get(ATSProvider.GREENHOUSE, "acme") is source
    assert registry.list_sources(enabled_only=True, verified_only=True, statuses={SourceStatus.EMPTY.value}, limit=1) == [source]
    restored = registry.to_config(source)
    assert restored.enabled and restored.manual_override
    # A discovery probe must not conditionally fetch the first persisted job
    # payload, otherwise a 304 can falsely look like an ingestion.
    assert "cache" not in restored.metadata
    registry.record_ingestion_counts(
        source,
        raw_jobs=0,
        technical_jobs=0,
        active_jobs=0,
        eligible_jobs=0,
        unknown_jobs=0,
        rejected_jobs=0,
    )
    assert registry.to_config(source).metadata["cache"]["etag"] == "v1"


def test_registry_blocks_repeated_failures_and_recovers(db_session):
    registry = SourceRegistry(db_session)
    candidate = SourceCandidate(
        provider=ATSProvider.GREENHOUSE,
        board_identifier="blocked",
        canonical_url="https://boards.greenhouse.io/blocked",
        api_url="https://boards-api.greenhouse.io/v1/boards/blocked/jobs",
        company_name="Blocked",
        discovery_method="test",
    )
    source = registry.upsert_candidate(candidate)
    blocked = SourceValidation(
        valid=False,
        provider=ATSProvider.GREENHOUSE,
        board_identifier="blocked",
        canonical_url=candidate.canonical_url,
        http_status=403,
        error_category="blocked",
    )
    registry.record_validation(source, blocked)
    assert source.status == SourceStatus.BLOCKED and source.enabled is False

    source.status = SourceStatus.UNVERIFIED.value
    source.enabled = True
    source.consecutive_failures = 0
    for _ in range(3):
        registry.record_validation(source, SourceValidation(
            valid=False,
            provider=ATSProvider.GREENHOUSE,
            board_identifier="blocked",
            canonical_url=candidate.canonical_url,
            http_status=503,
            error_category="server_error",
        ))
    assert source.status == SourceStatus.FAILING and source.enabled is False
    registry.record_validation(source, SourceValidation(
        valid=True,
        provider=ATSProvider.GREENHOUSE,
        board_identifier="blocked",
        canonical_url=candidate.canonical_url,
        http_status=200,
        job_count=1,
    ))
    assert source.status == SourceStatus.HEALTHY and source.enabled is True and source.consecutive_failures == 0


def test_registry_lifecycle_and_negative_cache(db_session):
    registry = SourceRegistry(db_session)
    candidate = SourceCandidate(
        provider=ATSProvider.LEVER,
        board_identifier="cache-me",
        canonical_url="https://jobs.lever.co/cache-me",
        api_url="https://api.lever.co/v0/postings/cache-me",
        discovery_method="urlscan_recent",
    )
    source = registry.upsert_candidate(candidate)
    assert source.validation_state == SourceValidationState.DISCOVERED.value
    assert registry.should_validate(source)
    registry.mark_pending(source)
    assert source.validation_state == SourceValidationState.PENDING_VALIDATION.value
    registry.record_validation(
        source,
        SourceValidation(
            valid=False,
            provider=ATSProvider.LEVER,
            board_identifier="cache-me",
            canonical_url=candidate.canonical_url,
            http_status=404,
            error_category="not_found",
        ),
    )
    assert source.validation_state == SourceValidationState.INVALID.value
    assert source.retry_after is not None and source.last_checked_at is not None
    assert not registry.should_validate(source)
    source.retry_after = datetime.now(UTC) - timedelta(seconds=1)
    assert registry.should_validate(source)
    registry.record_validation(
        source,
        SourceValidation(
            valid=True,
            provider=ATSProvider.LEVER,
            board_identifier="cache-me",
            canonical_url=candidate.canonical_url,
            http_status=200,
            job_count=3,
        ),
    )
    assert source.validation_state == SourceValidationState.VERIFIED.value
    assert not registry.should_validate(source)


def test_failed_source_retry_selection_respects_retry_after(db_session):
    registry = SourceRegistry(db_session)
    candidate = SourceCandidate(
        provider=ATSProvider.LEVER,
        board_identifier="rate-limited",
        canonical_url="https://jobs.lever.co/rate-limited",
        api_url="https://api.lever.co/v0/postings/rate-limited",
        company_name="Rate Limited",
        discovery_method="test",
    )
    source = registry.upsert_candidate(candidate)
    registry.record_validation(
        source,
        SourceValidation(
            valid=False,
            provider=ATSProvider.LEVER,
            board_identifier=source.board_identifier,
            canonical_url=source.careers_url or candidate.canonical_url,
            http_status=429,
            error_category="rate_limited",
            metadata={"retry_after_seconds": 7200},
        ),
    )
    assert source.status == SourceStatus.DEGRADED.value
    assert source.retry_after is not None
    assert source.retry_after > datetime.now(UTC) + timedelta(minutes=119)
    assert source not in registry.failed_sources()

    source.retry_after = datetime.now(UTC) - timedelta(seconds=1)
    db_session.flush()
    assert source in registry.failed_sources()


def test_import_config_canonicalizes_provider_case_and_endpoint(db_session):
    registry = SourceRegistry(db_session)
    source = registry.import_config(
        SourceConfig(
            provider=ATSProvider.ASHBY,
            company_name="Acme",
            slug="Acme",
            careers_url="https://jobs.ashbyhq.com/Acme/jobs/123",
        )
    )
    assert source.board_identifier == "acme"
    assert source.api_url == "https://api.ashbyhq.com/posting-api/job-board/acme"
    assert registry.get(ATSProvider.ASHBY, "acme") is source


def test_import_config_honors_manual_override_flag(db_session):
    registry = SourceRegistry(db_session)
    source = registry.import_config(
        SourceConfig(provider=ATSProvider.GREENHOUSE, company_name="Snapshot board", slug="snapshot-board")
    )
    assert source.manual_override is False


def test_uningested_verified_sources_are_resumable(db_session):
    registry = SourceRegistry(db_session)
    source = registry.upsert_candidate(
        SourceCandidate(
            provider=ATSProvider.GREENHOUSE,
            board_identifier="resume-me",
            canonical_url="https://boards.greenhouse.io/resume-me",
            api_url="https://boards-api.greenhouse.io/v1/boards/resume-me/jobs",
            discovery_method="test",
        ),
        enabled=True,
    )
    registry.record_validation(
        source,
        SourceValidation(
            valid=True,
            provider=ATSProvider.GREENHOUSE,
            board_identifier="resume-me",
            canonical_url="https://boards.greenhouse.io/resume-me",
            http_status=200,
        ),
    )
    assert registry.un_ingested_verified_sources() == [source]
    assert registry.un_ingested_verified_sources(providers={"personio"}) == []
    assert registry.un_ingested_verified_sources(providers={"greenhouse"}) == [source]
    registry.record_ingestion_counts(source, raw_jobs=1, technical_jobs=1, active_jobs=1, eligible_jobs=0, unknown_jobs=1, rejected_jobs=0)
    assert registry.un_ingested_verified_sources() == []


def test_uningested_sources_can_prioritize_observed_job_volume(db_session):
    registry = SourceRegistry(db_session)
    sources = []
    for identifier, jobs in (("small", 2), ("large", 20)):
        source = registry.upsert_candidate(
            SourceCandidate(
                provider=ATSProvider.GREENHOUSE,
                board_identifier=identifier,
                canonical_url=f"https://boards.greenhouse.io/{identifier}",
                api_url=f"https://boards-api.greenhouse.io/v1/boards/{identifier}/jobs",
                discovery_method="test",
            ),
            enabled=True,
        )
        registry.record_validation(
            source,
            SourceValidation(
                valid=True,
                provider=ATSProvider.GREENHOUSE,
                board_identifier=identifier,
                canonical_url=source.careers_url or "",
                job_count=jobs,
                http_status=200,
            ),
        )
        sources.append(source)
    assert registry.un_ingested_verified_sources(largest_first=True) == [sources[1], sources[0]]


def test_due_ingestion_scheduler_is_deterministic_fair_and_respects_backoff(db_session):
    registry = SourceRegistry(db_session)
    now = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)

    def add_source(
        identifier: str,
        *,
        ingested_at: datetime | None,
        status: str = SourceStatus.HEALTHY.value,
        enabled: bool = True,
        retry_after: datetime | None = None,
    ):
        source = registry.upsert_candidate(
            SourceCandidate(
                provider=ATSProvider.GREENHOUSE,
                board_identifier=identifier,
                canonical_url=f"https://boards.greenhouse.io/{identifier}",
                discovery_method="scheduler_test",
            ),
            enabled=enabled,
        )
        source.verified_at = now - timedelta(days=30)
        source.status = status
        source.validation_state = SourceValidationState.VERIFIED.value
        source.last_ingested_at = ingested_at
        source.retry_after = retry_after
        return source

    due = [
        add_source(f"due-{index}", ingested_at=now - timedelta(hours=40 - index))
        for index in range(6)
    ]
    never = [add_source(f"never-{index}", ingested_at=None) for index in range(12)]
    recent = add_source("recent", ingested_at=now - timedelta(hours=2))
    backed_off = add_source(
        "backed-off",
        ingested_at=now - timedelta(days=2),
        status=SourceStatus.DEGRADED.value,
        retry_after=now + timedelta(hours=1),
    )
    retry_due = add_source(
        "retry-due",
        ingested_at=now - timedelta(days=2),
        status=SourceStatus.FAILING.value,
        enabled=False,
        retry_after=now - timedelta(minutes=1),
    )
    db_session.flush()

    first = registry.due_for_ingestion(
        refresh_interval=timedelta(hours=18),
        now=now,
        limit=4,
        stale_share=0.75,
    )
    assert [source.board_identifier for source in first] == [
        "retry-due",
        "due-0",
        "due-1",
        "never-0",
    ]
    assert recent not in first
    assert backed_off not in first

    # Mark each bounded batch as processed and prove that both partitions make
    # progress across repeated scheduler runs. The old last_ingested_at-NULL
    # selector would never include any of the due sources above.
    selected_ids: set[int] = set()
    for _ in range(6):
        batch = registry.due_for_ingestion(
            refresh_interval=timedelta(hours=18),
            now=now,
            limit=4,
            stale_share=0.75,
        )
        if not batch:
            break
        selected_ids.update(source.id for source in batch)
        for source in batch:
            source.last_ingested_at = now
        db_session.flush()

    assert {source.id for source in due} <= selected_ids
    assert retry_due.id in selected_ids
    assert {source.id for source in never} <= selected_ids


def test_verified_snapshot_does_not_erase_newer_ingestion_backoff(db_session):
    registry = SourceRegistry(db_session)
    source = registry.import_verified_snapshot(
        SourceConfig(
            provider=ATSProvider.GREENHOUSE,
            company_name="Backoff Co",
            slug="backoff-co",
            metadata={
                "snapshot_health": {
                    "validation_state": "verified",
                    "health_state": "healthy",
                    "last_success_at": "2026-08-24T10:00:00+00:00",
                    "last_checked_at": "2026-08-24T10:00:00+00:00",
                }
            },
        )
    )
    source.status = SourceStatus.FAILING.value
    source.enabled = False
    source.last_checked_at = datetime(2026, 8, 26, 10, 0, tzinfo=UTC)
    source.retry_after = datetime(2026, 8, 26, 16, 0, tzinfo=UTC)
    db_session.flush()

    refreshed = registry.import_verified_snapshot(
        SourceConfig(
            provider=ATSProvider.GREENHOUSE,
            company_name="Backoff Co",
            slug="backoff-co",
            metadata={
                "snapshot_health": {
                    "validation_state": "verified",
                    "health_state": "healthy",
                    "last_success_at": "2026-08-24T10:00:00+00:00",
                    "last_checked_at": "2026-08-24T10:00:00+00:00",
                }
            },
        )
    )
    assert refreshed.status == SourceStatus.FAILING.value
    assert refreshed.enabled is False
    assert refreshed.retry_after == datetime(2026, 8, 26, 16, 0, tzinfo=UTC)


def test_two_scheduled_runs_retain_registry_state_and_skip_cached_candidates(db_session):
    registry = SourceRegistry(db_session)
    verified = registry.upsert_candidate(
        SourceCandidate(
            provider=ATSProvider.GREENHOUSE,
            board_identifier="verified-run-one",
            canonical_url="https://boards.greenhouse.io/verified-run-one",
            api_url="https://boards-api.greenhouse.io/v1/boards/verified-run-one/jobs",
            discovery_method="run_one",
        ),
        enabled=True,
    )
    registry.record_validation(
        verified,
        SourceValidation(
            valid=True,
            provider=ATSProvider.GREENHOUSE,
            board_identifier=verified.board_identifier,
            canonical_url=verified.careers_url or "",
            http_status=200,
            job_count=4,
        ),
    )
    invalid = registry.upsert_candidate(
        SourceCandidate(
            provider=ATSProvider.GREENHOUSE,
            board_identifier="invalid-run-one",
            canonical_url="https://boards.greenhouse.io/invalid-run-one",
            discovery_method="run_one",
        )
    )
    registry.record_validation(
        invalid,
        SourceValidation(
            valid=False,
            provider=ATSProvider.GREENHOUSE,
            board_identifier=invalid.board_identifier,
            canonical_url=invalid.careers_url or "",
            http_status=404,
            error_category="not_found",
        ),
    )
    cached = registry.upsert_candidate(
        SourceCandidate(
            provider=ATSProvider.GREENHOUSE,
            board_identifier="cached-run-one",
            canonical_url="https://boards.greenhouse.io/cached-run-one",
            discovery_method="run_one",
        )
    )
    registry.record_validation(
        cached,
        SourceValidation(
            valid=True,
            provider=ATSProvider.GREENHOUSE,
            board_identifier=cached.board_identifier,
            canonical_url=cached.careers_url or "",
            http_status=200,
            job_count=2,
        ),
    )
    cached.last_checked_at = datetime.now(UTC)
    cached.retry_after = datetime.now(UTC) + timedelta(days=2)
    db_session.commit()

    new_source = registry.upsert_candidate(
        SourceCandidate(
            provider=ATSProvider.GREENHOUSE,
            board_identifier="new-run-two",
            canonical_url="https://boards.greenhouse.io/new-run-two",
            discovery_method="run_two",
        )
    )
    db_session.commit()

    persisted_ids = {source.board_identifier for source in registry.list_sources()}
    assert {"verified-run-one", "invalid-run-one", "cached-run-one", "new-run-two"} <= persisted_ids
    assert not registry.should_validate(cached)
    assert registry.should_validate(new_source)
    assert invalid.validation_state == SourceValidationState.INVALID.value
    assert invalid.retry_after is not None

from __future__ import annotations

from europe_visa_jobs.db.source_registry import SourceRegistry
from europe_visa_jobs.discovery.patterns import identify_source_url
from europe_visa_jobs.schemas import (
    ATSProvider,
    SourceCandidate,
    SourceConfig,
    SourceStatus,
    SourceValidation,
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
    assert coverage["active_jobs"] == 0  # no Job rows were fabricated by registry accounting
    assert coverage["raw_jobs_scanned"] == 2


def test_registry_filters_and_cache_round_trip(db_session):
    registry = SourceRegistry(db_session)
    config = SourceConfig(
        provider=ATSProvider.GREENHOUSE,
        company_name="Acme",
        slug="acme",
        careers_url="https://boards.greenhouse.io/acme",
        metadata={"cache": {"etag": "v1"}},
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
        ),
    )
    db_session.commit()
    assert registry.get(ATSProvider.GREENHOUSE, "acme") is source
    assert registry.list_sources(enabled_only=True, verified_only=True, statuses={SourceStatus.EMPTY.value}, limit=1) == [source]
    restored = registry.to_config(source)
    assert restored.enabled and restored.manual_override
    assert restored.metadata["cache"]["etag"] == "v1"


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

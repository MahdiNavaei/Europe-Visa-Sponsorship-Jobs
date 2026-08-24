from __future__ import annotations

import json

import pytest

from europe_visa_jobs.db.source_registry import SourceRegistry
from europe_visa_jobs.discovery.snapshot import (
    SnapshotValidationError,
    build_snapshot,
    validate_snapshot,
)
from europe_visa_jobs.ingestion.sources import load_sources
from europe_visa_jobs.schemas import ATSProvider, SourceCandidate, SourceValidation


def _verified_source(registry: SourceRegistry):
    candidate = SourceCandidate(
        provider=ATSProvider.GREENHOUSE,
        board_identifier="acme",
        canonical_url="https://boards.greenhouse.io/acme",
        api_url="https://boards-api.greenhouse.io/v1/boards/acme/jobs",
        company_name="Acme",
        discovery_method="live_test",
    )
    source = registry.upsert_candidate(candidate)
    registry.record_validation(
        source,
        SourceValidation(
            valid=True,
            provider=candidate.provider,
            board_identifier=candidate.board_identifier,
            canonical_url=candidate.canonical_url,
            job_count=4,
            http_status=200,
        ),
    )
    return source


def test_snapshot_is_deterministic_and_preserves_verified_health(db_session, tmp_path):
    registry = SourceRegistry(db_session)
    _verified_source(registry)
    db_session.commit()

    first = build_snapshot(registry.list_sources(verified_only=True))
    second = build_snapshot(registry.list_sources(verified_only=True))
    assert first == second
    configs = validate_snapshot(first, minimum_verified=1)
    assert len(configs) == 1
    assert configs[0].metadata["snapshot_health"]["validation_state"] == "verified"

    path = tmp_path / "registry.snapshot.json"
    path.write_text(json.dumps(first), encoding="utf-8")
    assert load_sources(path, minimum_snapshot_sources=1)[0].slug == "acme"


def test_snapshot_rejects_small_or_unverified_records(db_session):
    registry = SourceRegistry(db_session)
    _verified_source(registry)
    payload = build_snapshot(registry.list_sources(verified_only=True))
    with pytest.raises(SnapshotValidationError, match="at least 2"):
        validate_snapshot(payload, minimum_verified=2)
    payload["sources"][0]["metadata"]["snapshot_health"]["validation_state"] = "pending_validation"
    with pytest.raises(SnapshotValidationError, match="verified health"):
        validate_snapshot(payload, minimum_verified=1)


def test_snapshot_excludes_historically_verified_sources_no_longer_current(db_session):
    registry = SourceRegistry(db_session)
    source = _verified_source(registry)
    source.validation_state = "pending_validation"
    db_session.commit()

    payload = build_snapshot(registry.list_sources(verified_only=True))
    assert payload["verified_source_count"] == 0


def test_snapshot_bootstrap_preserves_verified_state(db_session):
    registry = SourceRegistry(db_session)
    source = _verified_source(registry)
    db_session.commit()
    payload = build_snapshot([source])
    config = validate_snapshot(payload, minimum_verified=1)[0]

    # Simulate a fresh desktop database.
    db_session.query(type(source)).delete()
    db_session.commit()
    restored = registry.import_verified_snapshot(config)
    assert restored.verified_at is not None
    assert restored.validation_state == "verified"
    assert restored.enabled is True
    assert restored.manual_override is False


def test_production_snapshot_bootstraps_full_verified_registry_from_empty_db(db_session):
    configs = load_sources("config/source-registry.snapshot.json", minimum_snapshot_sources=500)
    registry = SourceRegistry(db_session)
    for config in configs:
        registry.import_verified_snapshot(config)
    db_session.commit()

    assert len(configs) >= 500
    assert len(registry.list_sources(limit=100000)) == len(configs)
    assert all(source.validation_state == "verified" for source in registry.list_sources(limit=100000))

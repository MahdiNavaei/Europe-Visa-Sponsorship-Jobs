from __future__ import annotations

from fastapi.testclient import TestClient

from europe_visa_jobs.api.app import app
from europe_visa_jobs.db.session import get_db
from europe_visa_jobs.db.source_registry import SourceRegistry
from europe_visa_jobs.schemas import ATSProvider, SourceCandidate, SourceValidation


def test_coverage_and_source_health_endpoints(session_factory):
    with session_factory() as session:
        registry = SourceRegistry(session)
        candidate = SourceCandidate(provider=ATSProvider.GREENHOUSE, board_identifier="acme", canonical_url="https://boards.greenhouse.io/acme", discovery_method="test")
        source = registry.upsert_candidate(candidate)
        registry.record_validation(source, SourceValidation(valid=True, provider=ATSProvider.GREENHOUSE, board_identifier="acme", canonical_url=candidate.canonical_url, job_count=1, http_status=200))
        session.commit()

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        coverage = client.get("/api/v1/coverage")
        health = client.get("/api/v1/sources/health")
        assert coverage.status_code == 200
        assert coverage.json()["verified_sources"] == 1
        assert health.status_code == 200
        assert health.json()[0]["status"] == "healthy"
    finally:
        app.dependency_overrides.clear()

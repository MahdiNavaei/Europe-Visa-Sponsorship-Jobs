from __future__ import annotations

from fastapi.testclient import TestClient

from europe_visa_jobs.api.app import app
from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.db.session import get_db
from europe_visa_jobs.eligibility import EligibilityEngine
from europe_visa_jobs.schemas import ATSProvider, NormalizedJob


def seed(session_factory):
    with session_factory() as session:
        repo = Repository(session)
        item = NormalizedJob(
            external_id="1",
            provider=ATSProvider.GREENHOUSE,
            source_slug="acme",
            company_name="Acme",
            title="Backend Engineer",
            description="Visa sponsorship and relocation support are available.",
            location="Berlin, Germany",
            country="Germany",
            apply_url="https://example.com/apply",
        )
        repo.upsert_job(item, EligibilityEngine().assess(item))
        session.commit()


def test_api_health_jobs_details_companies_and_stats(session_factory):
    seed(session_factory)

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        health = client.get("/health")
        assert health.json()["status"] == "ok"
        assert health.headers["x-content-type-options"] == "nosniff"
        assert health.headers["x-frame-options"] == "DENY"
        assert health.headers["referrer-policy"] == "no-referrer"

        countries = client.get("/api/v1/countries").json()["countries"]
        assert "Germany" in countries and "Netherlands" in countries

        jobs = client.get("/api/v1/jobs", params={"country": "Germany"})
        assert jobs.status_code == 200
        assert jobs.headers["x-total-count"] == "1"
        assert len(jobs.json()) == 1
        job_id = jobs.json()[0]["id"]

        details = client.get(f"/api/v1/jobs/{job_id}")
        assert details.status_code == 200
        assert details.json()["evidence"]

        companies = client.get("/api/v1/companies")
        assert companies.status_code == 200
        assert companies.json()[0]["name"] == "Acme"

        stats = client.get("/api/v1/stats").json()
        assert stats["total_jobs"] == 1
        assert stats["eligible_jobs"] == 1
        assert client.get("/api/v1/jobs/9999").status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_api_cors_is_explicit_and_exposes_pagination_header():
    client = TestClient(app)
    allowed_origin = "http://localhost:3000"

    preflight = client.options(
        "/api/v1/jobs",
        headers={
            "Origin": allowed_origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == allowed_origin
    assert "access-control-allow-credentials" not in preflight.headers
    assert "PATCH" not in preflight.headers["access-control-allow-methods"]

    response = client.get("/health", headers={"Origin": allowed_origin})
    assert response.headers["access-control-allow-origin"] == allowed_origin
    assert response.headers["access-control-expose-headers"] == "X-Total-Count"

    denied = client.get("/health", headers={"Origin": "https://attacker.example"})
    assert "access-control-allow-origin" not in denied.headers

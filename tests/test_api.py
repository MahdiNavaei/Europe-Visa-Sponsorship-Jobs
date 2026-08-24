from __future__ import annotations

from fastapi.testclient import TestClient

from europe_visa_jobs.api.app import app
from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.db.session import get_db
from europe_visa_jobs.eligibility import EligibilityEngine
from europe_visa_jobs.schemas import ATSProvider, EligibilityStatus, NormalizedJob


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


def test_catalog_status_is_read_only_and_safe_when_not_configured(monkeypatch):
    monkeypatch.delenv("CAREERRADAR_DATA_DIR", raising=False)
    response = TestClient(app).get("/api/v1/catalog/status")
    assert response.status_code == 200
    assert response.json() == {
        "state": "not_started",
        "started_at": None,
        "completed_at": None,
        "last_successful_sync": None,
        "next_scheduled_sync": None,
        "dataset_version": None,
        "generated_at": None,
        "sources_loaded": None,
        "jobs_loaded": None,
        "partial_success": False,
        "successful_sources": None,
        "failed_sources": None,
        "sources_updated": None,
        "jobs_added": None,
        "jobs_changed": None,
        "jobs_removed": None,
        "degraded_providers": [],
        "error": None,
    }


def test_default_jobs_browse_includes_unknown_but_excludes_rejected(session_factory):
    with session_factory() as session:
        repo = Repository(session)
        for index, status in enumerate((EligibilityStatus.ELIGIBLE, EligibilityStatus.UNKNOWN, EligibilityStatus.REJECTED)):
            job = NormalizedJob(
                external_id=f"browse-policy-{index}",
                provider=ATSProvider.GREENHOUSE,
                source_slug="browse-policy",
                company_name="Browse Policy Labs",
                title="Backend Engineer",
                description="Visa sponsorship and relocation support are available.",
                location="Berlin, Germany",
                country="Germany",
                apply_url=f"https://example.com/browse/{index}",
            )
            stored = repo.upsert_job(job, EligibilityEngine().assess(job))
            stored.eligibility_status = status.value
        session.commit()

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        default = client.get("/api/v1/jobs", params={"query": "Browse Policy"})
        assert default.status_code == 200
        assert {item["eligibility_status"] for item in default.json()} == {"eligible", "unknown"}
        assert default.headers["X-Total-Count"] == "2"

        rejected = client.get("/api/v1/jobs", params={"query": "Browse Policy", "status": "rejected"})
        assert rejected.status_code == 200
        assert len(rejected.json()) == 1
        assert rejected.json()[0]["eligibility_status"] == "rejected"
    finally:
        app.dependency_overrides.clear()


def test_company_metrics_use_full_active_catalog_not_first_page(session_factory):
    with session_factory() as session:
        repo = Repository(session)
        for index in range(101):
            job = NormalizedJob(
                external_id=f"aggregate-{index}",
                provider=ATSProvider.GREENHOUSE,
                source_slug="aggregate-board",
                company_name="Aggregate Labs",
                title="Backend Engineer",
                description="Visa sponsorship and relocation support are available.",
                location="Berlin, Germany",
                country="Germany",
                apply_url=f"https://example.com/apply/{index}",
            )
            repo.upsert_job(job, EligibilityEngine().assess(job))
        session.commit()

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        company = client.get("/api/v1/companies/1")
        assert company.status_code == 200
        payload = company.json()
        assert payload["active_jobs"] == 101
        assert payload["eligible_jobs"] == 101
        assert payload["jobs_total"] == 101
        assert len(payload["jobs"]) == 50
        assert company.headers["X-Total-Count"] == "101"
    finally:
        app.dependency_overrides.clear()

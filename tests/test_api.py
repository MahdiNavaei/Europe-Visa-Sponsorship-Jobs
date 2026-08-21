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
        assert client.get("/health").json()["status"] == "ok"
        countries = client.get("/api/v1/countries").json()["countries"]
        assert "Germany" in countries and "Netherlands" in countries

        jobs = client.get("/api/v1/jobs", params={"country": "Germany"})
        assert jobs.status_code == 200
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

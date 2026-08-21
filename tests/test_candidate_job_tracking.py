from __future__ import annotations

from fastapi.testclient import TestClient

from europe_visa_jobs.api.app import app
from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.db.session import get_db
from europe_visa_jobs.eligibility import EligibilityEngine
from europe_visa_jobs.schemas import ATSProvider, CandidateCreate, NormalizedJob


def test_saved_job_and_application_state_api(session_factory):
    with session_factory() as session:
        repo = Repository(session)
        candidate = repo.create_candidate(
            CandidateCreate(
                name="Tracker Candidate",
                target_roles=["AI Engineer"],
                skills=["Python"],
                preferred_countries=["Germany"],
            )
        )
        normalized = NormalizedJob(
            external_id="tracking-job",
            provider=ATSProvider.GREENHOUSE,
            source_slug="tracking",
            company_name="Tracker GmbH",
            title="AI Engineer",
            description="Visa sponsorship is available. Required skills: Python.",
            location="Berlin, Germany",
            country="Germany",
            apply_url="https://example.invalid/tracking",
        )
        job = repo.upsert_job(normalized, EligibilityEngine().assess(normalized))
        session.commit()
        candidate_id, job_id = candidate.id, job.id

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        initial = client.get(f"/api/v1/candidates/{candidate_id}/jobs/{job_id}/state")
        assert initial.status_code == 200
        assert initial.json() is None

        saved = client.put(
            f"/api/v1/candidates/{candidate_id}/jobs/{job_id}/state",
            json={"saved": True, "application_status": "applied", "note": "Applied through ATS"},
        )
        assert saved.status_code == 200
        assert saved.json()["saved"] is True
        assert saved.json()["application_status"] == "applied"
        assert saved.json()["job"]["id"] == job_id

        listing = client.get(f"/api/v1/candidates/{candidate_id}/job-states", params={"saved_only": True})
        assert listing.status_code == 200
        assert len(listing.json()) == 1

        removed = client.delete(f"/api/v1/candidates/{candidate_id}/jobs/{job_id}/state")
        assert removed.status_code == 204
        assert client.get(f"/api/v1/candidates/{candidate_id}/job-states").json() == []
    finally:
        app.dependency_overrides.clear()

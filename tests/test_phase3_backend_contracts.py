from __future__ import annotations

from fastapi.testclient import TestClient

from europe_visa_jobs.api.app import app
from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.db.session import get_db
from europe_visa_jobs.eligibility import EligibilityEngine
from europe_visa_jobs.schemas import ATSProvider, CandidateCreate, CompanySponsorEvidence, NormalizedJob


def _seed(session_factory) -> tuple[int, int, int]:
    with session_factory() as session:
        repo = Repository(session)
        repo.add_sponsor_record(
            CompanySponsorEvidence(
                company_name="Northstar Labs",
                country="Germany",
                registry_name="Demo registry",
                source_url="https://example.invalid/registry",
            )
        )
        job = NormalizedJob(
            external_id="phase3-contract",
            provider=ATSProvider.GREENHOUSE,
            source_slug="phase3-contract",
            company_name="Northstar Labs",
            title="Senior AI Engineer",
            description="Visa sponsorship and relocation support are available. Required skills: Python, PyTorch.",
            location="Berlin, Germany",
            country="Germany",
            apply_url="https://example.invalid/apply",
        )
        stored_job = repo.upsert_job(job, EligibilityEngine().assess(job))
        candidate = repo.create_candidate(
            CandidateCreate(
                name="Samira Ahmadi",
                target_roles=["AI Engineer"],
                skills=["Python", "PyTorch"],
                years_of_experience=6,
                seniority="senior",
                preferred_countries=["Germany"],
                visa_required=True,
            )
        )
        session.commit()
        return candidate.id, stored_job.id, stored_job.company_id


def test_phase3_frontend_contracts(session_factory):
    candidate_id, job_id, company_id = _seed(session_factory)

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        jobs = client.get("/api/v1/jobs", params={"query": "AI", "limit": 1, "offset": 0})
        assert jobs.status_code == 200
        assert jobs.headers["X-Total-Count"] == "1"
        assert jobs.json()[0]["id"] == job_id

        single_match = client.get(f"/api/v1/recommendations/{candidate_id}/jobs/{job_id}")
        assert single_match.status_code == 200
        assert single_match.json()["scores"]["overall"] > 0

        company = client.get(f"/api/v1/companies/{company_id}")
        assert company.status_code == 200
        payload = company.json()
        assert payload["company"]["id"] == company_id
        assert payload["active_jobs"] == 1
        assert payload["eligible_jobs"] == 1
        assert payload["visa_friendliness_score"] > 0

        updated = client.put(
            f"/api/v1/candidates/{candidate_id}",
            json={
                "name": "Samira Updated",
                "target_roles": ["Machine Learning Engineer"],
                "skills": ["python3", "Torch"],
                "years_of_experience": 7,
                "seniority": "senior",
                "preferred_countries": ["Germany", "Netherlands"],
                "visa_required": True,
                "relocation_preference": "preferred",
                "remote_preference": "preferred",
                "excluded_locations": [],
            },
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "Samira Updated"
        assert updated.json()["skills"] == ["Python", "PyTorch"]
    finally:
        app.dependency_overrides.clear()

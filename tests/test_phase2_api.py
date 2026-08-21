from __future__ import annotations

from fastapi.testclient import TestClient

from europe_visa_jobs.api.app import app
from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.db.session import get_db
from europe_visa_jobs.eligibility import EligibilityEngine
from europe_visa_jobs.schemas import ATSProvider, NormalizedJob


def test_candidate_and_recommendation_endpoints(session_factory):
    with session_factory() as session:
        job = NormalizedJob(
            external_id="api-job",
            provider=ATSProvider.GREENHOUSE,
            source_slug="api-fixture",
            company_name="API Company",
            title="AI Engineer",
            description="Visa sponsorship and relocation support are available. Required skills: Python, PyTorch.",
            location="Berlin, Germany",
            country="Germany",
            apply_url="https://example.com/api-job",
        )
        Repository(session).upsert_job(job, EligibilityEngine().assess(job))
        session.commit()

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    payload = {
        "name": "API Candidate",
        "target_roles": ["AI Engineer"],
        "skills": ["python3", "torch"],
        "years_of_experience": 5,
        "seniority": "senior",
        "preferred_countries": ["Germany"],
        "visa_required": True,
    }
    try:
        created = client.post("/api/v1/candidates", json=payload)
        assert created.status_code == 201
        candidate = created.json()
        assert candidate["skills"] == ["Python", "PyTorch"]
        assert client.get(f"/api/v1/candidates/{candidate['id']}").status_code == 200

        recommendations = client.get(f"/api/v1/recommendations/{candidate['id']}")
        assert recommendations.status_code == 200
        assert recommendations.json()[0]["job"]["title"] == "AI Engineer"
        assert recommendations.json()[0]["reasons"]

        explanation = client.get(f"/api/v1/recommendations/{candidate['id']}/explain")
        assert explanation.status_code == 200
        assert explanation.json()["weights"]["visa"] == 0.35
    finally:
        app.dependency_overrides.clear()

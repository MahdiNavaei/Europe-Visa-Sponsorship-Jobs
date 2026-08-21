from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from europe_visa_jobs.api.app import app
from europe_visa_jobs.db.models import Candidate, Job
from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.db.session import get_db
from europe_visa_jobs.eligibility import EligibilityEngine
from europe_visa_jobs.intelligence.ontology import SkillOntology
from europe_visa_jobs.intelligence.ranking import RankingConfig, RankingEngine, load_ranking_config
from europe_visa_jobs.schemas import ATSProvider, CandidateCreate, NormalizedJob
from europe_visa_jobs.utils import classify_role
from scripts.seed_demo import seed_demo


def test_ranking_configuration_is_loaded_from_yaml(tmp_path: Path):
    config_path = tmp_path / "ranking.yaml"
    config_path.write_text(
        """visa_score:\n  weight: 0.40\nskill_score:\n  weight: 0.25\nexperience_score:\n  weight: 0.15\ncountry_score:\n  weight: 0.10\ncompany_score:\n  weight: 0.10\n""",
        encoding="utf-8",
    )
    config = RankingConfig.from_yaml(config_path)
    assert config.as_dict() == {
        "visa": 0.4,
        "skill": 0.25,
        "experience": 0.15,
        "country": 0.1,
        "company": 0.1,
    }
    assert load_ranking_config().as_dict() == RankingEngine().config.as_dict()


def test_invalid_ranking_configuration_is_rejected(tmp_path: Path):
    config_path = tmp_path / "ranking.yaml"
    config_path.write_text(
        """visa_score:\n  weight: 0.9\nskill_score:\n  weight: 0\nexperience_score:\n  weight: 0\ncountry_score:\n  weight: 0\ncompany_score:\n  weight: 0\n""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="sum to 1"):
        RankingConfig.from_yaml(config_path)


def test_skill_ontology_uses_the_reviewable_data_file():
    ontology = SkillOntology()
    assert ontology.category("PyTorch") == "machine_learning"
    assert {item.canonical_name for item in ontology.definitions()} >= {"Python", "PyTorch", "LLM"}


def test_demo_seed_is_fictional_and_idempotent(db_session):
    assert seed_demo(db_session) == (3, 3)
    assert seed_demo(db_session) == (3, 0)
    assert db_session.query(Job).count() == 3
    assert db_session.query(Candidate).count() == 3
    assert all("DEMO SAMPLE DATA ONLY" in job.description for job in db_session.query(Job).all())


def test_recommendation_pagination_filters_and_structured_scores(session_factory):
    with session_factory() as session:
        repo = Repository(session)
        jobs = (
            ("ai", "AI Engineer", "Berlin, Germany", "Germany", "Python, PyTorch"),
            ("backend", "Backend Engineer", "Stockholm, Sweden", "Sweden", "Python, PostgreSQL"),
        )
        for external_id, title, location, country, skills in jobs:
            job = NormalizedJob(
                external_id=external_id,
                provider=ATSProvider.GREENHOUSE,
                source_slug="hardening",
                company_name=f"Demo {external_id}",
                title=title,
                description=f"Visa sponsorship is available. Required skills: {skills}.",
                location=location,
                country=country,
                apply_url=f"https://example.invalid/{external_id}",
                job_family=classify_role(title),
            )
            repo.upsert_job(job, EligibilityEngine().assess(job))
        candidate = repo.create_candidate(
            CandidateCreate(
                name="Hardening Candidate",
                target_roles=["AI Engineer"],
                skills=["Python", "PyTorch"],
                years_of_experience=5,
                preferred_countries=["Germany", "Sweden"],
            )
        )
        session.commit()
        candidate_id = candidate.id

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        page = client.get(f"/api/v1/recommendations/{candidate_id}", params={"limit": 1, "offset": 1})
        assert page.status_code == 200
        assert page.headers["x-total-count"] == "2"
        assert len(page.json()) == 1
        assert "scores" in page.json()[0]
        assert page.json()[0]["scores"]["overall"] == page.json()[0]["total_score"]

        all_items = client.get(f"/api/v1/recommendations/{candidate_id}").json()
        best_score = max(item["total_score"] for item in all_items)
        high_score = client.get(
            f"/api/v1/recommendations/{candidate_id}",
            params={"min_score": best_score},
        )
        assert len(high_score.json()) == 1

        role = client.get(f"/api/v1/recommendations/{candidate_id}", params={"role": "AI Engineer"})
        assert [item["job"]["title"] for item in role.json()] == ["AI Engineer"]

        country = client.get(f"/api/v1/recommendations/{candidate_id}", params={"country": "Sweden"})
        assert [item["job"]["country"] for item in country.json()] == ["Sweden"]

        jobs = client.get("/api/v1/jobs", params={"category": "ai_ml", "visa_status": "eligible"})
        assert jobs.status_code == 200
        assert [item["title"] for item in jobs.json()] == ["AI Engineer"]
    finally:
        app.dependency_overrides.clear()

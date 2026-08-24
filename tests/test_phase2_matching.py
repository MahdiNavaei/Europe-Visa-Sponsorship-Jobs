from __future__ import annotations

import json
from pathlib import Path

from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.eligibility import EligibilityEngine
from europe_visa_jobs.intelligence.ranking import RankingEngine
from europe_visa_jobs.schemas import ATSProvider, CandidateCreate, NormalizedJob

FIXTURES = Path(__file__).parent / "fixtures"


def test_candidate_is_normalized_and_ranked_explainably(db_session):
    candidate_data = json.loads((FIXTURES / "phase2_candidate.json").read_text(encoding="utf-8"))
    job_rows = json.loads((FIXTURES / "phase2_jobs.json").read_text(encoding="utf-8"))
    expected = json.loads((FIXTURES / "phase2_expected_ranking.json").read_text(encoding="utf-8"))
    repo = Repository(db_session)
    candidate = repo.create_candidate(CandidateCreate.model_validate(candidate_data))

    for row in job_rows:
        normalized = NormalizedJob(
            external_id=row["external_id"],
            provider=ATSProvider.GREENHOUSE,
            source_slug="phase2-fixture",
            company_name=row["company_name"],
            title=row["title"],
            description=row["description"],
            location=row["location"],
            country=row["country"],
            apply_url=row["apply_url"],
        )
        repo.upsert_job(normalized, EligibilityEngine().assess(normalized))
    db_session.commit()

    recommendations = RankingEngine().recommend(candidate, repo.list_recommendation_jobs())
    assert [item.job.external_id for item in recommendations] == expected["top_external_ids"]
    top = recommendations[0]
    assert top.match.required_skill_coverage == 1
    assert set(top.match.matched_skills) >= {"Python", "PyTorch", "Kubernetes"}
    assert top.match.missing_skills == []
    assert top.match.visa_score == 1
    assert top.match.reasons


def test_excluded_location_and_missing_skills_are_warnings(db_session):
    repo = Repository(db_session)
    candidate = repo.create_candidate(
        CandidateCreate(
            name="Candidate",
            target_roles=["Backend Engineer"],
            skills=["Python"],
            years_of_experience=2,
            preferred_countries=["Germany"],
            excluded_locations=["Berlin"],
        )
    )
    normalized = NormalizedJob(
        external_id="warning",
        provider=ATSProvider.GREENHOUSE,
        source_slug="phase2-fixture",
        company_name="Acme",
        title="Senior Backend Engineer",
        description="Visa sponsorship is available. Required skills: Python, Kubernetes.",
        location="Berlin, Germany",
        country="Germany",
        apply_url="https://example.com/warning",
    )
    repo.upsert_job(normalized, EligibilityEngine().assess(normalized))
    db_session.commit()
    recommendation = RankingEngine().recommend(candidate, repo.list_recommendation_jobs())[0]
    assert recommendation.match.country_score == 0
    assert "Kubernetes" in recommendation.match.missing_skills
    assert any("excluded" in warning for warning in recommendation.match.warnings)


def test_unpublished_requirements_are_neutral_not_perfect(db_session):
    repo = Repository(db_session)
    candidate = repo.create_candidate(
        CandidateCreate(
            name="Candidate",
            target_roles=["Backend Engineer"],
            skills=["Python"],
            years_of_experience=10,
            preferred_countries=["Germany"],
        )
    )
    normalized = NormalizedJob(
        external_id="requirements-unknown",
        provider=ATSProvider.GREENHOUSE,
        source_slug="phase2-fixture",
        company_name="Acme",
        title="Backend Engineer",
        description="Visa sponsorship is available. Join our engineering team.",
        location="Berlin, Germany",
        country="Germany",
        apply_url="https://example.com/requirements-unknown",
    )
    repo.upsert_job(normalized, EligibilityEngine().assess(normalized))
    db_session.commit()

    match = RankingEngine().recommend(candidate, repo.list_recommendation_jobs())[0].match
    assert match.skill_score == 50
    assert match.experience_score == 50
    assert match.required_skill_coverage == 0.5
    assert any("did not publish enough skill" in warning for warning in match.warnings)
    assert any("did not publish enough experience" in warning for warning in match.warnings)

from __future__ import annotations

from pathlib import Path

from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.eligibility import EligibilityEngine
from europe_visa_jobs.intelligence.matching import CandidateMatcher
from europe_visa_jobs.intelligence.ontology import SkillOntology
from europe_visa_jobs.intelligence.ranking import RankingConfig, RankingEngine
from europe_visa_jobs.schemas import ATSProvider, CandidateCreate, JobFamily, NormalizedJob
from europe_visa_jobs.utils.roles import classify_role


def test_eligible_visa_component_uses_the_same_100_point_scale(db_session):
    repo = Repository(db_session)
    candidate = repo.create_candidate(
        CandidateCreate(
            name="Visa-scale regression",
            target_roles=["Software Engineering"],
            skills=["Python"],
            years_of_experience=5,
            preferred_countries=["Germany"],
            visa_required=True,
        )
    )
    job = NormalizedJob(
        external_id="visa-scale",
        provider=ATSProvider.GREENHOUSE,
        source_slug="feedback-regression",
        company_name="Example GmbH",
        title="Software Engineer",
        description="Visa sponsorship and relocation support are available. Python is required.",
        location="Berlin, Germany",
        country="Germany",
        apply_url="https://example.com/visa-scale",
    )
    repo.upsert_job(job, EligibilityEngine().assess(job))
    db_session.commit()

    recommendation = RankingEngine(
        config=RankingConfig(visa=1.0, skill=0.0, experience=0.0, country=0.0, company=0.0, role=0.0)
    ).recommend(candidate, repo.list_recommendation_jobs())[0]

    assert recommendation.match.visa_score == 1.0
    assert recommendation.total_score == 100.0


def test_software_engineering_is_a_real_broad_target_family():
    assert classify_role("Software Engineering") is JobFamily.SOFTWARE_ENGINEERING
    assert classify_role("Backend Engineering") is JobFamily.BACKEND
    assert classify_role("Data Engineering") is JobFamily.DATA_ENGINEERING
    assert classify_role("Mobile Engineering") is JobFamily.MOBILE
    assert classify_role("Security Engineering") is JobFamily.SECURITY_ENGINEERING

    assert CandidateMatcher._role_similarity(
        ["Software Engineering"], "Senior Backend Engineer", JobFamily.BACKEND
    ) == 0.9
    assert CandidateMatcher._role_similarity(
        ["Backend Engineering"], "Software Engineer", JobFamily.SOFTWARE_ENGINEERING
    ) == 0.85


def test_expanded_skill_ontology_covers_common_backend_frontend_and_ml_skills():
    ontology = SkillOntology()
    expected = {
        "Machine Learning",
        "C#",
        ".NET",
        "NestJS",
        "MongoDB",
        "Next.js",
        "LangGraph",
        "GitHub Actions",
    }
    available = {definition.canonical_name for definition in ontology.definitions()}
    assert expected <= available

    assert ontology.normalize_skill("dotnet") == ".NET"
    assert ontology.normalize_skill("c sharp") == "C#"
    assert ontology.normalize_skill("nextjs") == "Next.js"
    assert {"NestJS", "MongoDB", "Docker"} <= set(
        ontology.extract("Backend stack: NestJS, MongoDB and Docker are required.")
    )


def test_onboarding_exposes_grouped_role_aware_skill_choices():
    source = (
        Path(__file__).resolve().parents[1]
        / "apps"
        / "web"
        / "src"
        / "features"
        / "onboarding"
        / "onboarding-page.tsx"
    ).read_text(encoding="utf-8")

    assert '"Software Engineering"' in source
    assert 'key: "backend"' in source
    assert 'key: "frontend"' in source
    assert 'key: "machine_learning"' in source
    assert "priorityKeys(selectedRoles)" in source
    assert "Search skills..." in source

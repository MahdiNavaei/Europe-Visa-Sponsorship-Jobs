from __future__ import annotations

from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.eligibility import EligibilityEngine
from europe_visa_jobs.intelligence.matching import CandidateMatcher
from europe_visa_jobs.intelligence.ranking import RankingEngine
from europe_visa_jobs.schemas import ATSProvider, CandidateCreate, NormalizedJob
from europe_visa_jobs.utils import classify_role


def test_ai_ml_profile_keeps_unrelated_mobile_and_frontend_roles_out_of_top_three(db_session):
    relevant = [
        "Machine Learning Engineer",
        "Senior AI Engineer",
        "Applied Scientist",
        "Data Scientist",
        "ML Platform Engineer",
        "MLOps Engineer",
        "Generative AI Engineer",
        "LLM Engineer",
        "Deep Learning Engineer",
        "NLP Engineer",
    ]
    unrelated = [
        "iOS Engineer",
        "Senior Android Engineer",
        "Frontend Engineer",
        "React Developer",
        "Mobile Engineer",
        "Senior Backend Engineer",
        "QA Automation Engineer",
        "Site Reliability Engineer",
        "Cloud Engineer",
        "Full Stack Developer",
    ]
    repo = Repository(db_session)
    candidate = repo.create_candidate(
        CandidateCreate(
            name="Alex Morgan",
            target_roles=["AI / Machine Learning", "Data Science"],
            skills=["Python", "Machine Learning", "PyTorch", "SQL"],
            years_of_experience=7,
            seniority="senior",
            preferred_countries=["Germany", "Netherlands"],
            visa_required=True,
            relocation_preference="preferred",
        )
    )
    assessment_engine = EligibilityEngine()
    for index, title in enumerate([*relevant, *unrelated]):
        job = NormalizedJob(
            external_id=f"ranking-{index}",
            provider=ATSProvider.GREENHOUSE,
            source_slug="real-user-ranking",
            company_name="Audited Employer",
            title=title,
            description="Visa sponsorship is available. Required skills: Python, Machine Learning, PyTorch, SQL.",
            location="Berlin, Germany",
            country="Germany",
            apply_url=f"https://example.invalid/ranking-{index}",
            job_family=classify_role(title),
        )
        repo.upsert_job(job, assessment_engine.assess(job))
    db_session.commit()

    ranked = RankingEngine().recommend(candidate, repo.list_recommendation_jobs())
    labels = [item.job.title in relevant for item in ranked]

    assert all(labels[:3])
    assert sum(labels[:3]) / 3 >= 0.9
    assert sum(labels[:5]) / 5 >= 0.9
    assert sum(labels[:10]) / 10 >= 0.9
    assert classify_role("Data Science") == classify_role("Data Scientist")


def test_role_classifier_does_not_promote_data_platform_product_roles():
    assert classify_role("Senior Data Platform Engineer") == "data_engineering"
    assert classify_role("Senior Product Manager - Credit and Data Platform") == "other"
    assert classify_role("Senior Service Designer - Platform Engineering") == "other"


def test_description_keywords_only_confirm_technical_shaped_titles():
    description = "Works with Python, SQL, Kubernetes, and software developers."
    assert classify_role("Product Manager", description=description) == "other"
    assert classify_role("Business Analyst", description=description) == "other"
    assert classify_role("Platform Specialist", description=description) == "software_engineering"


def test_matching_uses_current_title_for_stale_job_family_labels():
    assert CandidateMatcher._effective_job_family(
        type("JobStub", (), {"title": "Senior Data Platform Engineer", "job_family": "other"})()
    ) == "data_engineering"
    assert CandidateMatcher._effective_job_family(
        type("JobStub", (), {"title": "Senior Product Manager - Data Platform", "job_family": "data_engineering"})()
    ) == "other"
    assert CandidateMatcher._effective_job_family(
        type("JobStub", (), {"title": "Senior Engineer", "job_family": "backend"})()
    ) == "backend"


def test_role_matching_does_not_match_short_role_names_inside_unrelated_words():
    assert CandidateMatcher._role_similarity(["SRE"], "Werksreiniger", "other") == 0.2

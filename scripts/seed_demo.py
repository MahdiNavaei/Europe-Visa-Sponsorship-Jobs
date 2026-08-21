"""Seed a small, clearly fictional dataset for local demos and screenshots."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

DEMO_CANDIDATES = (
    {
        "name": "Demo Candidate — Senior AI Engineer",
        "target_roles": ["AI Engineer", "Machine Learning Engineer"],
        "skills": ["Python", "PyTorch", "LLM", "RAG", "Kubernetes", "MLflow"],
        "years_of_experience": 7,
        "seniority": "senior",
        "preferred_countries": ["Germany", "Netherlands", "Sweden"],
        "visa_required": True,
    },
    {
        "name": "Demo Candidate — Backend Engineer",
        "target_roles": ["Backend Engineer"],
        "skills": ["Python", "PostgreSQL", "Docker", "Kubernetes"],
        "years_of_experience": 5,
        "seniority": "senior",
        "preferred_countries": ["Germany", "Sweden"],
        "visa_required": True,
    },
    {
        "name": "Demo Candidate — Data Scientist",
        "target_roles": ["Data Scientist"],
        "skills": ["Python", "SQL", "scikit-learn", "Spark"],
        "years_of_experience": 4,
        "seniority": "mid",
        "preferred_countries": ["Sweden", "Germany"],
        "visa_required": True,
    },
)

DEMO_JOBS = (
    {
        "external_id": "demo-ai-berlin",
        "company_name": "Demo Aurora AI GmbH (Sample)",
        "title": "Senior Machine Learning Engineer",
        "description": (
            "DEMO SAMPLE DATA ONLY — not a real sponsorship claim. "
            "Visa sponsorship and relocation support are available. "
            "Required skills: Python, PyTorch, Kubernetes. Nice to have: MLflow."
        ),
        "location": "Berlin, Germany",
        "country": "Germany",
        "apply_url": "https://example.invalid/demo-ai-berlin",
    },
    {
        "external_id": "demo-data-stockholm",
        "company_name": "Demo Northstar Analytics AB (Sample)",
        "title": "Data Scientist",
        "description": (
            "DEMO SAMPLE DATA ONLY — not a real sponsorship claim. "
            "Work permit support and relocation assistance are available. "
            "Required skills: Python, SQL, scikit-learn."
        ),
        "location": "Stockholm, Sweden",
        "country": "Sweden",
        "apply_url": "https://example.invalid/demo-data-stockholm",
    },
    {
        "external_id": "demo-backend-amsterdam",
        "company_name": "Demo Canal Systems B.V. (Sample)",
        "title": "Backend Engineer",
        "description": (
            "DEMO SAMPLE DATA ONLY — not a real sponsorship claim. "
            "Visa sponsorship and relocation support are mentioned for this sample vacancy. "
            "Required skills: Python, PostgreSQL, Docker."
        ),
        "location": "Amsterdam, Netherlands",
        "country": "Netherlands",
        "apply_url": "https://example.invalid/demo-backend-amsterdam",
    },
)


def seed_demo(session) -> tuple[int, int]:
    """Insert or refresh demo jobs and insert demo candidates once.

    Returns ``(jobs_upserted, candidates_created)``. No real company, vacancy, or sponsor
    assertion is represented by this dataset.
    """
    from europe_visa_jobs.db.repository import Repository
    from europe_visa_jobs.eligibility import EligibilityEngine
    from europe_visa_jobs.schemas import ATSProvider, CandidateCreate, NormalizedJob
    from europe_visa_jobs.utils import classify_role

    repo = Repository(session)
    engine = EligibilityEngine()
    jobs_upserted = 0
    for job_row in DEMO_JOBS:
        job = NormalizedJob(
            external_id=job_row["external_id"],
            provider=ATSProvider.GREENHOUSE,
            source_slug="demo",
            company_name=job_row["company_name"],
            title=job_row["title"],
            description=job_row["description"],
            location=job_row["location"],
            country=job_row["country"],
            apply_url=job_row["apply_url"],
            job_url=job_row["apply_url"],
            posted_at=datetime(2026, 1, 1, tzinfo=UTC),
            job_family=classify_role(job_row["title"]),
        )
        repo.upsert_job(job, engine.assess(job))
        jobs_upserted += 1

    candidates_created = 0
    for candidate_row in DEMO_CANDIDATES:
        candidate_name = str(candidate_row["name"])
        if repo.get_candidate_by_name(candidate_name) is not None:
            continue
        repo.create_candidate(CandidateCreate.model_validate(candidate_row))
        candidates_created += 1
    session.commit()
    return jobs_upserted, candidates_created


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed clearly fictional Phase 2 demo records.")
    parser.add_argument("--database-url", help="Database URL; defaults to DATABASE_URL/settings.")
    args = parser.parse_args()
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    from europe_visa_jobs.db.session import SessionLocal, init_db

    init_db()
    with SessionLocal() as session:
        jobs, candidates = seed_demo(session)
    print(f"Seeded demo data only: {jobs} jobs upserted, {candidates} candidates created.")


if __name__ == "__main__":  # pragma: no cover
    main()

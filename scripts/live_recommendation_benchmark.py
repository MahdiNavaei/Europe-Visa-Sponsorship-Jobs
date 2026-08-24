"""Measure recommendation precision on a bounded live connector catalog sample."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from typing import Any

import httpx

from europe_visa_jobs.connectors import build_connector
from europe_visa_jobs.db.models import Company, Job
from europe_visa_jobs.ingestion.sources import load_sources
from europe_visa_jobs.intelligence.ranking import RankingEngine
from europe_visa_jobs.schemas import CandidateCreate
from europe_visa_jobs.settings import get_settings
from europe_visa_jobs.utils import classify_role

PERSONAS = {
    "ai_ml": CandidateCreate(name="Benchmark AI/ML", target_roles=["AI Engineer", "Machine Learning Engineer"], skills=["Python", "Machine Learning", "PyTorch", "SQL"], years_of_experience=7, preferred_countries=["Germany", "Netherlands"]),
    "backend": CandidateCreate(name="Benchmark Backend", target_roles=["Backend Engineer"], skills=["Python", "SQL", "Docker", "Kubernetes"], years_of_experience=7, preferred_countries=["Germany", "Netherlands"]),
    "data": CandidateCreate(name="Benchmark Data", target_roles=["Data Engineer", "Data Scientist"], skills=["Python", "SQL", "Spark", "Machine Learning"], years_of_experience=6, preferred_countries=["Germany", "Netherlands"]),
    "devops": CandidateCreate(name="Benchmark DevOps", target_roles=["DevOps Engineer", "SRE"], skills=["Kubernetes", "Docker", "AWS", "Python"], years_of_experience=7, preferred_countries=["Germany", "Netherlands"]),
}


def _job(index: int, normalized) -> Job:
    company = Company(name=normalized.company_name, normalized_name=normalized.company_name.casefold(), country=normalized.country, sponsor_verified=False)
    return Job(
        id=index,
        company=company,
        external_id=normalized.external_id,
        provider=normalized.provider.value,
        source_slug=normalized.source_slug,
        company_name=normalized.company_name,
        title=normalized.title,
        description=normalized.description,
        location=normalized.location,
        country=normalized.country,
        apply_url=normalized.apply_url,
        job_url=normalized.job_url,
        posted_at=normalized.posted_at or datetime.now(UTC),
        job_family=classify_role(normalized.title).value,
        required_skills=[],
        preferred_skills=[],
        eligibility_status="unknown",
        eligibility_score=0,
        active=True,
    )


async def run(snapshot: str) -> dict[str, Any]:
    sources = load_sources(snapshot)
    settings = get_settings()
    jobs = []
    async with httpx.AsyncClient(timeout=httpx.Timeout(settings.request_timeout_seconds), follow_redirects=True) as client:
        semaphore = asyncio.Semaphore(8)

        async def fetch(source):
            async with semaphore:
                try:
                    return await build_connector(client, source).fetch_jobs()
                except Exception:
                    return []

        batches = await asyncio.gather(*(fetch(source) for source in sources))
        for batch in batches:
            jobs.extend(batch)
    engine = RankingEngine()
    output: dict[str, Any] = {"sources": len(sources), "jobs": len(jobs), "personas": {}}
    for key, candidate_input in PERSONAS.items():
        candidate = type("CandidateFixture", (), {
            "target_roles": candidate_input.target_roles,
            "skills": candidate_input.skills,
            "years_of_experience": candidate_input.years_of_experience,
            "seniority": candidate_input.seniority,
            "preferred_countries": candidate_input.preferred_countries,
            "visa_required": True,
            "relocation_preference": "preferred",
            "remote_preference": "no_preference",
            "excluded_locations": [],
        })()
        ranked = engine.recommend(candidate, [_job(index + 1, item) for index, item in enumerate(jobs)], limit=None)
        rows = []
        for k in (3, 5, 10):
            top = ranked[:k]
            relevant = sum(item.match.role_similarity >= 0.75 for item in top)
            rows.append({"k": k, "relevant": relevant, "precision": round(relevant / k, 4) if k else 0.0})
        output["personas"][key] = {"p_at_k": rows, "top_titles": [item.job.title for item in ranked[:10]]}
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", default="config/sources.json")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args.snapshot)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

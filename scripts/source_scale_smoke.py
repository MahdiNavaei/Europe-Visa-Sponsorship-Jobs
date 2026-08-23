"""Build and measure a representative local registry/job dataset.

This is a deterministic storage/query smoke test, not a replacement for live
ATS validation. It verifies that the desktop SQLite path remains usable with
thousands of persisted sources and tens of thousands of jobs.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

from sqlalchemy import create_engine, func, insert, select
from sqlalchemy.orm import Session

from europe_visa_jobs.db.models import Base, Company, Job, Source
from europe_visa_jobs.db.source_registry import SourceRegistry


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default="sqlite:///./build/source-scale.sqlite")
    parser.add_argument("--sources", type=int, default=5000)
    parser.add_argument("--jobs", type=int, default=20000)
    parser.add_argument("--json", action="store_true")
    return parser


def run(database_url: str, source_count: int, job_count: int) -> dict[str, int | float | str]:
    if source_count < 1 or job_count < 1:
        raise ValueError("sources and jobs must be positive")
    if database_url.startswith("sqlite:///"):
        db_path = Path(database_url.removeprefix("sqlite:///"))
        db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(database_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    started = time.perf_counter()
    now = datetime.now(UTC)
    with Session(engine) as session:
        # Use a deterministic provider mix and the same persisted source model
        # used by live discovery; no external company dataset is imported.
        providers = ("greenhouse", "lever", "ashby", "workable", "personio")
        session.execute(
            insert(Source),
            [
                {
                    "company_name": f"Scale Company {index:05d}",
                    "normalized_company_name": f"scale company {index:05d}",
                    "provider": providers[index % len(providers)],
                    "board_identifier": f"scale-{index:05d}",
                    "careers_url": f"https://jobs.example.test/scale-{index:05d}",
                    "board_url": f"https://jobs.example.test/scale-{index:05d}",
                    "country_hint": "Germany" if index % 2 else "Netherlands",
                    "discovery_method": "deterministic_scale_fixture",
                    "discovered_at": now,
                    "verified_at": now,
                    "last_health_check_at": now,
                    "last_success_at": now,
                    "status": "healthy",
                    "enabled": True,
                    "manual_override": False,
                    "source_metadata": {"fixture": True},
                }
                for index in range(source_count)
            ],
        )
        session.execute(
            insert(Company),
            [
                {
                    "name": f"Scale Company {index:05d}",
                    "normalized_name": f"scale company {index:05d}",
                    "country": "Germany" if index % 2 else "Netherlands",
                    "career_url": f"https://jobs.example.test/scale-{index:05d}",
                    "sponsor_verified": False,
                    "created_at": now,
                    "updated_at": now,
                }
                for index in range(max(1, min(source_count, 1000)))
            ],
        )
        company_ids = list(session.scalars(select(Company.id).order_by(Company.id)))
        session.execute(
            insert(Job),
            [
                {
                    "company_id": company_ids[index % len(company_ids)],
                    "external_id": f"scale-job-{index:06d}",
                    "provider": providers[index % len(providers)],
                    "source_slug": f"scale-{index % source_count:05d}",
                    "company_name": f"Scale Company {index % source_count:05d}",
                    "title": "Machine Learning Engineer" if index % 5 == 0 else "Backend Engineer",
                    "description": "Deterministic scale fixture.",
                    "location": "Berlin, Germany" if index % 2 else "Amsterdam, Netherlands",
                    "country": "Germany" if index % 2 else "Netherlands",
                    "apply_url": f"https://jobs.example.test/apply/{index:06d}",
                    "posted_at": now - timedelta(days=index % 14),
                    "job_family": "ai_ml" if index % 5 == 0 else "backend",
                    "required_skills": ["Python"],
                    "preferred_skills": [],
                    "eligibility_status": "unknown" if index % 3 else "eligible",
                    "eligibility_score": 25 if index % 3 else 90,
                    "first_seen_at": now,
                    "last_seen_at": now,
                    "active": True,
                }
                for index in range(job_count)
            ],
        )
        session.commit()
        insert_seconds = time.perf_counter() - started

        coverage_started = time.perf_counter()
        coverage = SourceRegistry(session).coverage()
        coverage_seconds = time.perf_counter() - coverage_started
        health_started = time.perf_counter()
        health_rows = SourceRegistry(session).list_sources(limit=100)
        health_seconds = time.perf_counter() - health_started
        stats_started = time.perf_counter()
        active_jobs = session.scalar(select(func.count()).select_from(Job).where(Job.active.is_(True))) or 0
        stats_seconds = time.perf_counter() - stats_started
    return {
        "database_url": database_url,
        "sources": source_count,
        "jobs": job_count,
        "health_rows": len(health_rows),
        "active_jobs": active_jobs,
        "verified_sources": cast(int, coverage["verified_sources"]),
        "insert_seconds": round(insert_seconds, 3),
        "coverage_seconds": round(coverage_seconds, 3),
        "health_lookup_seconds": round(health_seconds, 3),
        "stats_seconds": round(stats_seconds, 3),
    }


def main() -> None:
    args = _parser().parse_args()
    payload = run(args.database_url, args.sources, args.jobs)
    print(json.dumps(payload, indent=2) if args.json else " ".join(f"{key}={value}" for key, value in payload.items()))


if __name__ == "__main__":
    main()

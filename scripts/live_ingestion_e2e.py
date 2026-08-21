from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select

from europe_visa_jobs.api.app import app
from europe_visa_jobs.db.models import Job
from europe_visa_jobs.db.session import SessionLocal
from europe_visa_jobs.ingestion.pipeline import ingest_source
from europe_visa_jobs.ingestion.sources import load_sources
from europe_visa_jobs.settings import get_settings

SOURCES_PATH = "config/sources.live-smoke.json"
MAX_POST_AGE_DAYS = 60


def _job_snapshot(slugs: set[str]) -> dict[tuple[str, str, str], Job]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(Job).where(Job.source_slug.in_(slugs), Job.active.is_(True))
        ).all()
        return {(job.provider, job.source_slug, job.external_id): job for job in rows}


async def _ingest_once() -> list[tuple[str, int, int]]:
    settings = get_settings()
    sources = load_sources(SOURCES_PATH)
    timeout = httpx.Timeout(settings.request_timeout_seconds)
    results: list[tuple[str, int, int]] = []
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for source in sources:
            with SessionLocal() as session:
                run = await ingest_source(session, source, client=client)
            results.append((f"{source.provider.value}:{source.slug}", run.fetched_count, run.stored_count))
    return results


async def main() -> None:
    sources = load_sources(SOURCES_PATH)
    if len(sources) < 2:
        raise AssertionError("live smoke requires at least two independent ATS sources")
    slugs = {source.slug for source in sources}

    first_runs = await _ingest_once()
    first = _job_snapshot(slugs)
    if not first:
        raise AssertionError("live ingestion stored zero active technical jobs")
    if not any(stored > 0 for _, _, stored in first_runs):
        raise AssertionError("live ATS responses contained no supported technical roles")

    second_runs = await _ingest_once()
    second = _job_snapshot(slugs)
    if set(first) != set(second):
        added = sorted(set(second) - set(first))[:5]
        removed = sorted(set(first) - set(second))[:5]
        raise AssertionError(
            f"immediate second ingestion was not idempotent; added={added}, removed={removed}"
        )

    recent_cutoff = datetime.now(UTC) - timedelta(days=MAX_POST_AGE_DAYS)
    recent = [job for job in second.values() if job.posted_at and job.posted_at >= recent_cutoff]
    if not recent:
        newest = max((job.posted_at for job in second.values() if job.posted_at), default=None)
        raise AssertionError(
            f"no live technical posting was updated/published in the last {MAX_POST_AGE_DAYS} days; newest={newest}"
        )

    eligible = [job for job in second.values() if job.eligibility_status == "eligible"]
    if not eligible:
        statuses: dict[str, int] = {}
        for job in second.values():
            key = job.eligibility_status or "none"
            statuses[key] = statuses.get(key, 0) + 1
        raise AssertionError(f"live ingestion produced no strict-mode eligible jobs; statuses={statuses}")

    with TestClient(app) as client:
        response = client.get("/api/v1/jobs", params={"limit": 100, "sort": "newest"})
        response.raise_for_status()
        api_jobs = response.json()
    if not api_jobs:
        raise AssertionError("API default eligible-jobs endpoint returned no live ingested jobs")
    if not any(item["source_slug"] in slugs for item in api_jobs):
        raise AssertionError("API response did not expose any job from the live smoke sources")
    if not all(str(item.get("apply_url", "")).startswith("http") for item in api_jobs):
        raise AssertionError("API returned an invalid application URL")

    print("LIVE_INGESTION_E2E_OK")
    print(f"sources={len(sources)} active_tech_jobs={len(second)} recent={len(recent)} eligible={len(eligible)}")
    print("first_runs=" + repr(first_runs))
    print("second_runs=" + repr(second_runs))
    print(
        "sample="
        + repr(
            [
                {
                    "company": job.company_name,
                    "title": job.title,
                    "country": job.country,
                    "posted_at": job.posted_at.isoformat() if job.posted_at else None,
                    "status": job.eligibility_status,
                }
                for job in sorted(eligible, key=lambda item: item.posted_at or datetime.min.replace(tzinfo=UTC), reverse=True)[:5]
            ]
        )
    )


if __name__ == "__main__":
    asyncio.run(main())

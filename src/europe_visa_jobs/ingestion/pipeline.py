from __future__ import annotations

from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from europe_visa_jobs.connectors import build_connector
from europe_visa_jobs.db.models import IngestionRun
from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.eligibility import EligibilityEngine, SponsorRegistryStore
from europe_visa_jobs.schemas import SourceConfig
from europe_visa_jobs.utils import is_supported_tech_role


async def ingest_source(
    session: Session,
    source: SourceConfig,
    *,
    client: httpx.AsyncClient,
) -> IngestionRun:
    run = IngestionRun(provider=source.provider.value, source_slug=source.slug)
    session.add(run)
    session.flush()
    repo = Repository(session)

    try:
        connector = build_connector(client, source)
        fetched = await connector.fetch_jobs()
        run.fetched_count = len(fetched)

        sponsor_store = SponsorRegistryStore(repo.sponsor_evidence())
        engine = EligibilityEngine(sponsor_registry=sponsor_store)
        seen_ids: set[str] = set()
        stored = 0

        for job in fetched:
            # Phase 1 intentionally limits the catalog to target technical job families.
            if not is_supported_tech_role(job.title):
                continue
            seen_ids.add(job.external_id)
            assessment = engine.assess(job)
            repo.upsert_job(job, assessment, career_url=source.careers_url)
            stored += 1

        repo.mark_source_jobs_inactive_except(source.provider.value, source.slug, seen_ids)
        run.stored_count = stored
        run.status = "success"
        run.finished_at = datetime.now(UTC)
        session.commit()
        return run
    except Exception as exc:
        session.rollback()
        # Preserve failure observability in a fresh transaction.
        failed = IngestionRun(
            provider=source.provider.value,
            source_slug=source.slug,
            status="failed",
            error=str(exc)[:2000],
            finished_at=datetime.now(UTC),
        )
        session.add(failed)
        session.commit()
        raise

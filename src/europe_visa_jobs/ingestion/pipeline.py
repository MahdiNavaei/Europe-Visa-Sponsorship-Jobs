from __future__ import annotations

from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from europe_visa_jobs.connectors import build_connector
from europe_visa_jobs.connectors.base import ConnectorNotModified
from europe_visa_jobs.db.models import IngestionRun
from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.db.source_registry import SourceRegistry
from europe_visa_jobs.eligibility import EligibilityEngine, SponsorRegistryStore
from europe_visa_jobs.schemas import (
    EligibilityAssessment,
    EligibilityStatus,
    SourceConfig,
    SourceValidation,
)
from europe_visa_jobs.utils import is_supported_tech_role


async def ingest_source(
    session: Session,
    source: SourceConfig,
    *,
    client: httpx.AsyncClient,
    sponsor_registry: SponsorRegistryStore | None = None,
) -> IngestionRun:
    run = IngestionRun(provider=source.provider.value, source_slug=source.slug)
    repo = Repository(session)
    registry = SourceRegistry(session)
    registry_source = registry.get(source.provider.value, source.slug) or registry.import_config(source)

    try:
        connector = build_connector(client, source)
        try:
            fetched = await connector.fetch_jobs()
        except ConnectorNotModified:
            # Do not open a SQLite write transaction while waiting on the
            # provider network request. The run row is added after fetch so
            # profile/tracking writes can proceed during slow refreshes.
            session.add(run)
            session.flush()
            response_headers = getattr(connector, "last_response_headers", {})
            fetch_duration_ms = getattr(connector, "last_fetch_duration_ms", 0)
            registry.record_validation(
                registry_source,
                SourceValidation(
                    valid=True,
                    provider=source.provider,
                    board_identifier=source.slug,
                    canonical_url=source.board_url or source.careers_url or "",
                    api_url=source.api_url,
                    job_count=registry_source.raw_job_count,
                    http_status=304,
                    etag=response_headers.get("etag"),
                    last_modified=response_headers.get("last-modified"),
                    metadata={"duration_ms": fetch_duration_ms, "not_modified": True},
                ),
            )
            run.fetched_count = registry_source.raw_job_count
            run.stored_count = registry_source.technical_job_count
            run.status = "success"
            run.finished_at = datetime.now(UTC)
            session.commit()
            return run
        run.fetched_count = len(fetched)

        # The connector fetch above is intentionally outside the transaction.
        # In particular, the desktop refresh must not hold SQLite's writer
        # lock across a slow or rate-limited ATS response.
        session.add(run)
        session.flush()

        sponsor_store = sponsor_registry or SponsorRegistryStore(repo.sponsor_evidence_for_jobs(fetched))
        engine = EligibilityEngine(sponsor_registry=sponsor_store)
        seen_ids: set[str] = set()
        stored = 0
        statuses: dict[str, int] = {"eligible": 0, "unknown": 0, "rejected": 0}

        for job in fetched:
            seen_ids.add(job.external_id)
            technical = is_supported_tech_role(job.title, job.department, job.description)
            assessment = engine.assess(job) if technical else EligibilityAssessment(
                status=EligibilityStatus.REJECTED,
                score=0,
                country=job.country,
                evidence=[],
                hard_rejection_reasons=["nontechnical_role"],
            )
            repo.upsert_job(
                job,
                assessment,
                career_url=source.careers_url,
                classification_status="technical" if technical else "nontechnical",
            )
            statuses[assessment.status.value] = statuses.get(assessment.status.value, 0) + 1
            stored += int(technical)

        completeness = getattr(connector, "completeness", "complete")
        registry_source.source_metadata = {
            **(registry_source.source_metadata or {}),
            "enumeration_completeness": completeness,
        }
        if completeness == "complete":
            repo.mark_source_jobs_inactive_except(source.provider.value, source.slug, seen_ids)
        response_headers = getattr(connector, "last_response_headers", {})
        fetch_duration_ms = getattr(connector, "last_fetch_duration_ms", 0)
        registry.record_validation(
            registry_source,
            SourceValidation(
                valid=True,
                provider=source.provider,
                board_identifier=source.slug,
                canonical_url=source.board_url or source.careers_url or "",
                api_url=source.api_url,
                company_name=source.company_name,
                job_count=len(fetched),
                http_status=200,
                etag=response_headers.get("etag"),
                last_modified=response_headers.get("last-modified"),
                metadata={"duration_ms": fetch_duration_ms, "completeness": completeness},
            ),
        )
        registry_source.etag = response_headers.get("etag") or registry_source.etag
        registry_source.last_modified = response_headers.get("last-modified") or registry_source.last_modified
        registry_source.last_fetch_duration_ms = fetch_duration_ms
        active_count = len(seen_ids)
        registry.record_ingestion_counts(
            registry_source,
            raw_jobs=len(fetched),
            technical_jobs=stored,
            active_jobs=active_count,
            eligible_jobs=statuses.get("eligible", 0),
            unknown_jobs=statuses.get("unknown", 0),
            rejected_jobs=statuses.get("rejected", 0),
        )
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
        failed_source = SourceRegistry(session).get(source.provider.value, source.slug)
        if failed_source is None:
            failed_source = SourceRegistry(session).import_config(source)
        error_status = getattr(exc, "status_code", None)
        error_category = getattr(exc, "category", "ingestion")
        SourceRegistry(session).record_validation(
            failed_source,
            SourceValidation(
                valid=False,
                provider=source.provider,
                board_identifier=source.slug,
                canonical_url=source.board_url or source.careers_url or "",
                api_url=source.api_url,
                http_status=error_status,
                error_category=error_category,
                error=str(exc)[:2000],
            ),
        )
        session.commit()
        raise

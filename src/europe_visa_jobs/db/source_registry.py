from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from europe_visa_jobs.db.models import DiscoveryRun, Job, Source, SourceHealthEvent
from europe_visa_jobs.schemas import (
    ATSProvider,
    SourceCandidate,
    SourceConfig,
    SourceStatus,
    SourceValidation,
)
from europe_visa_jobs.utils import EUROPEAN_COUNTRIES, normalize_company_name, normalize_country


class SourceRegistry:
    """Database authority for discovered and verified ATS boards."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_candidate(
        self,
        candidate: SourceCandidate,
        *,
        enabled: bool = False,
        manual_override: bool = False,
    ) -> Source:
        source = self.session.scalar(
            select(Source).where(
                Source.provider == candidate.provider.value,
                Source.board_identifier == candidate.board_identifier,
            )
        )
        now = datetime.now(UTC)
        if source is None:
            source = Source(
                company_name=candidate.company_name,
                normalized_company_name=normalize_company_name(candidate.company_name or "") or None,
                provider=candidate.provider.value,
                board_identifier=candidate.board_identifier,
                careers_url=candidate.canonical_url,
                board_url=candidate.canonical_url,
                api_url=candidate.api_url,
                country_hint=normalize_country(candidate.country_hint) if candidate.country_hint else None,
                discovery_method=candidate.discovery_method,
                discovered_at=now,
                status=SourceStatus.UNVERIFIED.value,
                enabled=enabled,
                manual_override=manual_override,
                source_metadata=dict(candidate.metadata),
            )
            self.session.add(source)
            self.session.flush()
            return source
        source.company_name = candidate.company_name or source.company_name
        source.normalized_company_name = normalize_company_name(candidate.company_name or source.company_name or "") or source.normalized_company_name
        source.careers_url = source.careers_url or candidate.canonical_url
        source.board_url = source.board_url or candidate.canonical_url
        source.api_url = candidate.api_url or source.api_url
        source.country_hint = normalize_country(candidate.country_hint) if candidate.country_hint else source.country_hint
        source.discovery_method = source.discovery_method if source.manual_override else candidate.discovery_method
        source.source_metadata = {**(source.source_metadata or {}), **candidate.metadata}
        source.manual_override = source.manual_override or manual_override
        if enabled:
            source.enabled = True
        self.session.flush()
        return source

    def import_config(self, config: SourceConfig) -> Source:
        candidate = SourceCandidate(
            provider=config.provider,
            board_identifier=config.board_identifier,
            canonical_url=config.board_url or config.careers_url or "",
            api_url=config.api_url,
            company_name=config.company_name,
            country_hint=config.default_country,
            discovery_method=config.discovery_method,
            metadata=config.metadata,
        )
        source = self.upsert_candidate(candidate, enabled=config.enabled, manual_override=config.manual_override or True)
        source.company_name = config.company_name
        source.normalized_company_name = normalize_company_name(config.company_name)
        source.careers_url = config.careers_url or source.careers_url
        source.board_url = config.board_url or source.board_url
        source.api_url = config.api_url or source.api_url
        source.country_hint = normalize_country(config.default_country) if config.default_country else source.country_hint
        if source.status == SourceStatus.UNVERIFIED.value:
            source.status = SourceStatus.UNVERIFIED.value
        self.session.flush()
        return source

    def get(self, provider: str | ATSProvider, board_identifier: str) -> Source | None:
        provider_value = provider.value if isinstance(provider, ATSProvider) else provider
        return self.session.scalar(
            select(Source).where(Source.provider == provider_value, Source.board_identifier == board_identifier)
        )

    def list_sources(self, *, enabled_only: bool = False, verified_only: bool = False, statuses: set[str] | None = None, limit: int | None = None) -> list[Source]:
        stmt = select(Source).order_by(Source.provider, Source.board_identifier)
        if enabled_only:
            stmt = stmt.where(Source.enabled.is_(True))
        if verified_only:
            stmt = stmt.where(Source.verified_at.is_not(None))
        if statuses:
            stmt = stmt.where(Source.status.in_(statuses))
        if limit:
            stmt = stmt.limit(limit)
        return list(self.session.scalars(stmt))

    def to_config(self, source: Source) -> SourceConfig:
        metadata = {**(source.source_metadata or {})}
        cache = {key: value for key, value in {"etag": source.etag, "last_modified": source.last_modified}.items() if value}
        if cache:
            metadata["cache"] = cache
        return SourceConfig(
            provider=ATSProvider(source.provider),
            company_name=source.company_name or source.board_identifier,
            slug=source.board_identifier,
            default_country=source.country_hint,
            careers_url=source.careers_url,
            board_url=source.board_url,
            api_url=source.api_url,
            discovery_method=source.discovery_method,
            metadata=metadata,
            manual_override=source.manual_override,
            enabled=source.enabled,
        )

    def create_discovery_run(self, mode: str, methods: list[str]) -> DiscoveryRun:
        run = DiscoveryRun(mode=mode, methods=methods, started_at=datetime.now(UTC))
        self.session.add(run)
        self.session.flush()
        return run

    def record_validation(self, source: Source, validation: SourceValidation, *, run_id: int | None = None) -> None:
        now = datetime.now(UTC)
        source.last_health_check_at = now
        source.last_http_status = validation.http_status
        source.last_error_category = validation.error_category
        source.last_error = validation.error
        source.last_fetch_duration_ms = int(validation.metadata.get("duration_ms", 0)) or source.last_fetch_duration_ms
        source.etag = validation.etag or source.etag
        source.last_modified = validation.last_modified or source.last_modified
        if validation.valid:
            source.verified_at = source.verified_at or now
            source.last_success_at = now
            source.consecutive_failures = 0
            source.status = SourceStatus.HEALTHY.value if validation.job_count else SourceStatus.EMPTY.value
            source.enabled = True
            source.company_name = validation.company_name or source.company_name
            source.normalized_company_name = normalize_company_name(source.company_name or "") or source.normalized_company_name
        else:
            source.last_failure_at = now
            source.consecutive_failures += 1
            if validation.http_status == 403:
                source.status = SourceStatus.BLOCKED.value
                source.enabled = False
            elif source.consecutive_failures >= 3:
                source.status = SourceStatus.FAILING.value
                source.enabled = False
            else:
                source.status = SourceStatus.DEGRADED.value
        self.session.add(
            SourceHealthEvent(
                source_id=source.id,
                discovery_run_id=run_id,
                observed_at=now,
                outcome="success" if validation.valid else "failure",
                http_status=validation.http_status,
                error_category=validation.error_category,
                error=validation.error,
                raw_job_count=validation.job_count,
            )
        )
        self.session.flush()

    def record_ingestion_counts(
        self,
        source: Source,
        *,
        raw_jobs: int,
        technical_jobs: int,
        active_jobs: int,
        eligible_jobs: int,
        unknown_jobs: int,
        rejected_jobs: int,
    ) -> None:
        source.raw_job_count = raw_jobs
        source.technical_job_count = technical_jobs
        source.active_job_count = active_jobs
        source.eligible_job_count = eligible_jobs
        source.unknown_job_count = unknown_jobs
        source.rejected_job_count = rejected_jobs
        source.last_ingested_at = datetime.now(UTC)
        if source.status == SourceStatus.EMPTY.value and raw_jobs:
            source.status = SourceStatus.HEALTHY.value
        self.session.flush()

    def failed_sources(self, *, limit: int | None = None) -> list[Source]:
        return self.list_sources(statuses={SourceStatus.DEGRADED.value, SourceStatus.FAILING.value, SourceStatus.BLOCKED.value}, limit=limit)

    def coverage(self) -> dict[str, int | datetime | None]:
        sources = self.list_sources()
        status_counts = Counter(source.status for source in sources)
        latest_run = self.session.scalar(
            select(DiscoveryRun).where(DiscoveryRun.finished_at.is_not(None)).order_by(DiscoveryRun.finished_at.desc()).limit(1)
        )
        jobs = select(Job).where(Job.active.is_(True))
        counts = {
            "active_jobs": self.session.scalar(select(func.count()).select_from(jobs.subquery())) or 0,
            "technical_jobs": self.session.scalar(select(func.count()).select_from(jobs.where(Job.job_family != "other").subquery())) or 0,
            "ai_ml_jobs": self.session.scalar(select(func.count()).select_from(jobs.where(Job.job_family.in_(["ai_ml", "data_science", "mlops"])).subquery())) or 0,
            "eligible_jobs": self.session.scalar(select(func.count()).select_from(jobs.where(Job.eligibility_status == "eligible").subquery())) or 0,
            "unknown_jobs": self.session.scalar(select(func.count()).select_from(jobs.where(Job.eligibility_status == "unknown").subquery())) or 0,
            "rejected_jobs": self.session.scalar(select(func.count()).select_from(jobs.where(Job.eligibility_status == "rejected").subquery())) or 0,
            "european_technical_jobs": self.session.scalar(
                select(func.count()).select_from(
                    jobs.where(
                        Job.job_family != "other",
                        or_(
                            Job.country.in_(EUROPEAN_COUNTRIES),
                            Job.location.ilike("%remote%eu%"),
                            Job.location.ilike("%remote%europe%"),
                            Job.location.ilike("%remote%emea%"),
                        ),
                    ).subquery()
                )
            ) or 0,
        }
        sources_scanned = 0
        if latest_run is not None:
            sources_scanned = self.session.scalar(
                select(func.count(func.distinct(SourceHealthEvent.source_id))).where(
                    SourceHealthEvent.discovery_run_id == latest_run.id
                )
            ) or 0
        latest_ingestion = max((source.last_ingested_at for source in sources if source.last_ingested_at), default=None)
        latest_refresh = max((item for item in (latest_run.finished_at if latest_run else None, latest_ingestion) if item), default=None)
        return {
            "configured_sources": sum(bool(source.manual_override) for source in sources),
            "discovered_sources": len(sources),
            "verified_sources": sum(source.verified_at is not None for source in sources),
            "healthy_sources": status_counts[SourceStatus.HEALTHY.value],
            "degraded_sources": status_counts[SourceStatus.DEGRADED.value],
            "failing_sources": status_counts[SourceStatus.FAILING.value],
            "blocked_sources": status_counts[SourceStatus.BLOCKED.value],
            "empty_sources": status_counts[SourceStatus.EMPTY.value],
            "disabled_sources": status_counts[SourceStatus.DISABLED.value],
            "sources_scanned_latest_run": int(sources_scanned),
            "raw_jobs_scanned": sum(source.raw_job_count for source in sources),
            "last_refresh_at": latest_refresh,
            **counts,
        }

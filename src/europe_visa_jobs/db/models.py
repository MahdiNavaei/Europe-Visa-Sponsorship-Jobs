from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Source(Base):
    """Persisted ATS board registry; static JSON is only a bootstrap input."""

    __tablename__ = "sources"
    __table_args__ = (
        UniqueConstraint("provider", "board_identifier", name="uq_source_provider_board"),
        Index("ix_sources_status_enabled", "status", "enabled"),
        Index("ix_sources_provider_status", "provider", "status"),
        Index("ix_sources_enabled_verified_provider_board", "enabled", "verified_at", "provider", "board_identifier"),
        Index("ix_sources_validation_state_retry_after", "validation_state", "retry_after"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    normalized_company_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    board_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    careers_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    board_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    country_hint: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    discovery_method: Mapped[str] = mapped_column(String(80), nullable=False, default="manual_seed")
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_health_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    raw_job_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    technical_job_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active_job_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    eligible_job_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unknown_job_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected_job_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="unverified", nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    manual_override: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    etag: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_modified: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_fetch_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
    validation_state: Mapped[str] = mapped_column(String(30), default="discovered", nullable=False, index=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    failure_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    validation_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class DiscoveryRun(Base):
    __tablename__ = "discovery_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    mode: Mapped[str] = mapped_column(String(30), nullable=False)
    methods: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    candidate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    validated_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invalid_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    provider_counts: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    candidate_before_filter_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    candidate_after_filter_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_cached_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_breakdown: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    provider_failure_breakdown: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class SourceHealthEvent(Base):
    __tablename__ = "source_health_events"
    __table_args__ = (Index("ix_source_health_events_source_observed", "source_id", "observed_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    discovery_run_id: Mapped[int | None] = mapped_column(ForeignKey("discovery_runs.id", ondelete="SET NULL"), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    outcome: Mapped[str] = mapped_column(String(30), nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_job_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_roles: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    years_of_experience: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    seniority: Mapped[str | None] = mapped_column(String(50), nullable=True)
    preferred_countries: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    visa_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    relocation_preference: Mapped[str] = mapped_column(String(30), default="preferred", nullable=False)
    remote_preference: Mapped[str] = mapped_column(String(30), default="no_preference", nullable=False)
    excluded_locations: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (UniqueConstraint("normalized_name", "country", name="uq_company_name_country"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    career_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    sponsor_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    name_quality: Mapped[str] = mapped_column(String(20), default="verified", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    jobs: Mapped[list[Job]] = relationship(back_populates="company", cascade="all, delete-orphan")


class SponsorRecord(Base):
    __tablename__ = "sponsor_records"
    __table_args__ = (
        UniqueConstraint("normalized_name", "country", "registry_name", name="uq_sponsor_record"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    registry_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("provider", "source_slug", "external_id", name="uq_job_source_external"),
        Index("ix_jobs_country_eligibility", "country", "eligibility_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_slug: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    location: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    workplace_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    apply_url: Mapped[str] = mapped_column(Text, nullable=False)
    job_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_apply_url: Mapped[str | None] = mapped_column(String(1000), nullable=True, index=True)
    duplicate_of_job_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    job_family: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    required_skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    preferred_skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    min_experience_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    seniority: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    eligibility_status: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    eligibility_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    classification_status: Mapped[str] = mapped_column(String(30), default="classification_unknown", nullable=False, index=True)
    job_sponsorship_signal: Mapped[str] = mapped_column(String(30), default="not_mentioned", nullable=False, index=True)
    company_sponsor_status: Mapped[str] = mapped_column(String(30), default="unresolved", nullable=False, index=True)
    final_candidate_eligibility: Mapped[str] = mapped_column(String(30), default="unknown", nullable=False, index=True)

    company: Mapped[Company] = relationship(back_populates="jobs")
    evidence: Mapped[list[JobEvidence]] = relationship(back_populates="job", cascade="all, delete-orphan")


class JobEvidence(Base):
    __tablename__ = "job_evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False)
    matched_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    job: Mapped[Job] = relationship(back_populates="evidence")


class CandidateJobState(Base):
    __tablename__ = "candidate_job_states"
    __table_args__ = (UniqueConstraint("candidate_id", "job_id", name="uq_candidate_job_state"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    saved: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    application_status: Mapped[str] = mapped_column(String(30), default="not_applied", nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    job: Mapped[Job] = relationship()


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="running", nullable=False)
    fetched_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stored_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

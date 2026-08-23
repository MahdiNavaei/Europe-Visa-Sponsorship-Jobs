from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ATSProvider(StrEnum):
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ASHBY = "ashby"
    WORKABLE = "workable"
    PERSONIO = "personio"
    TEAMTAILOR = "teamtailor"
    RECRUITEE = "recruitee"
    SMARTRECRUITERS = "smartrecruiters"
    WORKDAY = "workday"


class SourceStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    BLOCKED = "blocked"
    EMPTY = "empty"
    DISABLED = "disabled"
    UNVERIFIED = "unverified"


class EligibilityStatus(StrEnum):
    ELIGIBLE = "eligible"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class EvidenceKind(StrEnum):
    JOB_POSITIVE = "job_positive"
    JOB_NEGATIVE = "job_negative"
    COMPANY_REGISTRY = "company_registry"
    COUNTRY_RULE = "country_rule"
    LOCATION_RESTRICTION = "location_restriction"


class JobFamily(StrEnum):
    SOFTWARE_ENGINEERING = "software_engineering"
    BACKEND = "backend"
    FRONTEND = "frontend"
    FULLSTACK = "fullstack"
    MOBILE = "mobile"
    AI_ML = "ai_ml"
    DATA_SCIENCE = "data_science"
    DATA_ENGINEERING = "data_engineering"
    MLOPS = "mlops"
    DEVOPS_CLOUD = "devops_cloud"
    QA_AUTOMATION = "qa_automation"
    OTHER = "other"


class SeniorityLevel(StrEnum):
    INTERN = "intern"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    STAFF = "staff"
    LEAD = "lead"
    PRINCIPAL = "principal"
    DIRECTOR = "director"


class PreferenceLevel(StrEnum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    NO_PREFERENCE = "no_preference"


class SourceConfig(BaseModel):
    provider: ATSProvider
    company_name: str = Field(min_length=1)
    slug: str = Field(min_length=1)
    default_country: str | None = None
    region: str | None = None
    careers_url: str | None = None
    board_url: str | None = None
    api_url: str | None = None
    discovery_method: str = "manual_seed"
    metadata: dict[str, Any] = Field(default_factory=dict)
    manual_override: bool = False
    enabled: bool = True

    @property
    def board_identifier(self) -> str:
        return self.slug


class SourceCandidate(BaseModel):
    provider: ATSProvider
    board_identifier: str
    canonical_url: str
    api_url: str | None = None
    company_name: str | None = None
    country_hint: str | None = None
    discovery_method: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceValidation(BaseModel):
    valid: bool
    provider: ATSProvider
    board_identifier: str
    canonical_url: str
    api_url: str | None = None
    company_name: str | None = None
    job_count: int = 0
    http_status: int | None = None
    error_category: str | None = None
    error: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizedJob(BaseModel):
    external_id: str
    provider: ATSProvider
    source_slug: str
    company_name: str
    title: str
    description: str = ""
    location: str = ""
    country: str | None = None
    department: str | None = None
    employment_type: str | None = None
    workplace_type: str | None = None
    apply_url: str
    job_url: str | None = None
    posted_at: datetime | None = None
    job_family: JobFamily = JobFamily.OTHER
    raw: dict[str, Any] = Field(default_factory=dict, repr=False)

    model_config = ConfigDict(use_enum_values=False)


class CandidateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    target_roles: list[str] = Field(min_length=1, max_length=20)
    skills: list[str] = Field(default_factory=list, max_length=100)
    years_of_experience: float = Field(default=0, ge=0, le=60)
    seniority: SeniorityLevel | None = None
    preferred_countries: list[str] = Field(default_factory=list, max_length=30)
    visa_required: bool = True
    relocation_preference: PreferenceLevel = PreferenceLevel.PREFERRED
    remote_preference: PreferenceLevel = PreferenceLevel.NO_PREFERENCE
    excluded_locations: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("target_roles", "skills", "preferred_countries", "excluded_locations", mode="before")
    @classmethod
    def clean_list(cls, value: object) -> object:
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        return [item.strip() if isinstance(item, str) else item for item in value]

    @field_validator("target_roles", "skills", "preferred_countries", "excluded_locations")
    @classmethod
    def reject_empty_items(cls, value: list[object]) -> list[object]:
        if any(isinstance(item, str) and not item for item in value):
            raise ValueError("list items must not be empty")
        return value


class CandidateRead(CandidateCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Evidence(BaseModel):
    kind: EvidenceKind
    code: str
    message: str
    weight: int
    matched_text: str | None = None
    source_url: str | None = None


class CountryRule(BaseModel):
    country: str
    supported: bool = True
    primary_routes: list[str]
    sponsor_registry_required: bool = False
    sponsor_registry_name: str | None = None
    notes: list[str] = Field(default_factory=list)


class EligibilityAssessment(BaseModel):
    status: EligibilityStatus
    score: int = Field(ge=0, le=100)
    country: str | None
    visa_routes: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    hard_rejection_reasons: list[str] = Field(default_factory=list)
    assessed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CompanySponsorEvidence(BaseModel):
    company_name: str
    country: str
    registry_name: str
    source_url: str
    verified: bool = True


class JobRead(BaseModel):
    id: int
    company_id: int
    external_id: str
    provider: ATSProvider
    source_slug: str
    company_name: str
    title: str
    description: str
    location: str
    country: str | None
    department: str | None
    employment_type: str | None
    workplace_type: str | None
    apply_url: str
    job_url: str | None
    posted_at: datetime | None
    job_family: JobFamily
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    min_experience_years: float | None = None
    seniority: SeniorityLevel | None = None
    eligibility_status: EligibilityStatus | None = None
    eligibility_score: int | None = None

    model_config = ConfigDict(from_attributes=True)


class JobEvidenceRead(BaseModel):
    kind: EvidenceKind
    code: str
    message: str
    weight: int
    matched_text: str | None = None
    source_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class JobDetailRead(JobRead):
    evidence: list[JobEvidenceRead] = Field(default_factory=list)


class CompanyRead(BaseModel):
    id: int
    name: str
    normalized_name: str
    country: str | None
    career_url: str | None
    sponsor_verified: bool

    model_config = ConfigDict(from_attributes=True)


class CompanyIntelligenceRead(BaseModel):
    company: CompanyRead
    visa_friendliness_score: float = Field(ge=0, le=100)
    positive_signals: list[str] = Field(default_factory=list)
    negative_signals: list[str] = Field(default_factory=list)
    active_jobs: int = Field(ge=0)
    eligible_jobs: int = Field(ge=0)
    jobs: list[JobRead] = Field(default_factory=list)


class StatsRead(BaseModel):
    total_jobs: int
    eligible_jobs: int
    rejected_jobs: int
    unknown_jobs: int
    companies: int


class CoverageRead(BaseModel):
    configured_sources: int
    discovered_sources: int
    verified_sources: int
    healthy_sources: int
    degraded_sources: int
    failing_sources: int
    blocked_sources: int
    empty_sources: int
    disabled_sources: int
    sources_scanned_latest_run: int
    raw_jobs_scanned: int
    technical_jobs: int
    european_technical_jobs: int
    active_jobs: int
    ai_ml_jobs: int
    eligible_jobs: int
    unknown_jobs: int
    rejected_jobs: int
    last_refresh_at: datetime | None = None


class SourceHealthRead(BaseModel):
    id: int
    provider: ATSProvider
    board_identifier: str
    company_name: str | None
    careers_url: str | None
    status: SourceStatus
    enabled: bool
    manual_override: bool
    last_health_check_at: datetime | None
    last_success_at: datetime | None
    last_failure_at: datetime | None
    consecutive_failures: int
    raw_job_count: int
    technical_job_count: int
    active_job_count: int
    eligible_job_count: int
    unknown_job_count: int
    rejected_job_count: int
    last_http_status: int | None
    last_error_category: str | None
    last_error: str | None
    model_config = ConfigDict(from_attributes=True)


class RecommendationScoresRead(BaseModel):
    """Grouped scores for frontend clients; flat score fields remain for compatibility."""

    overall: float = Field(ge=0, le=100)
    visa: float = Field(ge=0, le=100)
    skill: float = Field(ge=0, le=100)
    experience: float = Field(ge=0, le=100)
    country: float = Field(ge=0, le=100)
    company: float = Field(ge=0, le=100)


class JobRecommendationRead(BaseModel):
    job_id: int
    scores: RecommendationScoresRead
    total_score: float = Field(ge=0, le=100)
    visa_score: float = Field(ge=0, le=100)
    skill_score: float = Field(ge=0, le=100)
    skill_match: float = Field(ge=0, le=1)
    experience_score: float = Field(ge=0, le=100)
    country_score: float = Field(ge=0, le=100)
    company_score: float = Field(ge=0, le=100)
    required_skill_coverage: float = Field(ge=0, le=1)
    preferred_skill_coverage: float = Field(ge=0, le=1)
    seniority_match: float = Field(ge=0, le=1)
    role_similarity: float = Field(ge=0, le=1)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    missing_preferred_skills: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    explanation: list[str] = Field(default_factory=list)
    job: JobRead


class RecommendationExplanationRead(BaseModel):
    candidate: CandidateRead
    weights: dict[str, float]
    recommendations: list[JobRecommendationRead]

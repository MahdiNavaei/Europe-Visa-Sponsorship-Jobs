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
    enabled: bool = True


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


class StatsRead(BaseModel):
    total_jobs: int
    eligible_jobs: int
    rejected_jobs: int
    unknown_jobs: int
    companies: int


class JobRecommendationRead(BaseModel):
    job_id: int
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

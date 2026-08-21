from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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

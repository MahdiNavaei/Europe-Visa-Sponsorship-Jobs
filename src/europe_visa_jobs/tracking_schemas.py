from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from europe_visa_jobs.schemas import JobRead


class ApplicationStatus(StrEnum):
    NOT_APPLIED = "not_applied"
    APPLIED = "applied"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class CandidateJobStateInput(BaseModel):
    saved: bool = True
    application_status: ApplicationStatus = ApplicationStatus.NOT_APPLIED
    note: str | None = Field(default=None, max_length=2000)


class CandidateJobStateRead(CandidateJobStateInput):
    id: int
    candidate_id: int
    job_id: int
    created_at: datetime
    updated_at: datetime
    job: JobRead

    model_config = ConfigDict(from_attributes=True)

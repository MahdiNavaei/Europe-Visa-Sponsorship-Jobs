from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from europe_visa_jobs.db.models import CandidateJobState
from europe_visa_jobs.tracking_schemas import (
    ApplicationStatus,
    CandidateJobStateInput,
)


class TrackingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, candidate_id: int, job_id: int) -> CandidateJobState | None:
        stmt = (
            select(CandidateJobState)
            .options(joinedload(CandidateJobState.job))
            .where(CandidateJobState.candidate_id == candidate_id, CandidateJobState.job_id == job_id)
        )
        return self.session.scalar(stmt)

    def list(
        self,
        candidate_id: int,
        *,
        saved_only: bool = False,
        application_status: ApplicationStatus | None = None,
    ) -> list[CandidateJobState]:
        stmt = (
            select(CandidateJobState)
            .options(joinedload(CandidateJobState.job))
            .where(CandidateJobState.candidate_id == candidate_id)
        )
        if saved_only:
            stmt = stmt.where(CandidateJobState.saved.is_(True))
        if application_status is not None:
            stmt = stmt.where(CandidateJobState.application_status == application_status.value)
        stmt = stmt.order_by(CandidateJobState.updated_at.desc(), CandidateJobState.id.desc())
        return list(self.session.scalars(stmt))

    def upsert(self, candidate_id: int, job_id: int, data: CandidateJobStateInput) -> CandidateJobState:
        item = self.get(candidate_id, job_id)
        if item is None:
            item = CandidateJobState(candidate_id=candidate_id, job_id=job_id)
            self.session.add(item)
        item.saved = data.saved
        item.application_status = data.application_status.value
        item.note = data.note.strip() if data.note and data.note.strip() else None
        item.updated_at = datetime.now(UTC)
        self.session.flush()
        return self.get(candidate_id, job_id) or item

    def delete(self, candidate_id: int, job_id: int) -> bool:
        item = self.get(candidate_id, job_id)
        if item is None:
            return False
        self.session.delete(item)
        self.session.flush()
        return True

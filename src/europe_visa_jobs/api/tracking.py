from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.db.session import get_db
from europe_visa_jobs.db.tracking import TrackingRepository
from europe_visa_jobs.tracking_schemas import (
    ApplicationStatus,
    CandidateJobStateInput,
    CandidateJobStateRead,
)

router = APIRouter(prefix="/api/v1", tags=["application-tracking"])
SessionDep = Annotated[Session, Depends(get_db)]


def _ensure_entities(candidate_id: int, job_id: int, session: Session) -> None:
    repo = Repository(session)
    if repo.get_candidate(candidate_id) is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if repo.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")


@router.get("/candidates/{candidate_id}/job-states", response_model=list[CandidateJobStateRead])
def list_job_states(
    candidate_id: int,
    session: SessionDep,
    saved_only: bool = False,
    application_status: ApplicationStatus | None = Query(default=None),
) -> list[CandidateJobStateRead]:
    if Repository(session).get_candidate(candidate_id) is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    items = TrackingRepository(session).list(
        candidate_id,
        saved_only=saved_only,
        application_status=application_status,
    )
    return [CandidateJobStateRead.model_validate(item) for item in items]


@router.get(
    "/candidates/{candidate_id}/jobs/{job_id}/state",
    response_model=CandidateJobStateRead | None,
)
def get_job_state(candidate_id: int, job_id: int, session: SessionDep) -> CandidateJobStateRead | None:
    _ensure_entities(candidate_id, job_id, session)
    item = TrackingRepository(session).get(candidate_id, job_id)
    return CandidateJobStateRead.model_validate(item) if item else None


@router.put(
    "/candidates/{candidate_id}/jobs/{job_id}/state",
    response_model=CandidateJobStateRead,
)
def upsert_job_state(
    candidate_id: int,
    job_id: int,
    data: CandidateJobStateInput,
    session: SessionDep,
) -> CandidateJobStateRead:
    _ensure_entities(candidate_id, job_id, session)
    item = TrackingRepository(session).upsert(candidate_id, job_id, data)
    session.commit()
    return CandidateJobStateRead.model_validate(item)


@router.delete("/candidates/{candidate_id}/jobs/{job_id}/state", status_code=204)
def delete_job_state(candidate_id: int, job_id: int, session: SessionDep) -> Response:
    _ensure_entities(candidate_id, job_id, session)
    TrackingRepository(session).delete(candidate_id, job_id)
    session.commit()
    return Response(status_code=204)

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from europe_visa_jobs.api.security import authorize_candidate
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


def _ensure_candidate(candidate_id: int, session: Session, request: Request, response: Response) -> None:
    repo = Repository(session)
    candidate = repo.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    authorize_candidate(request, response, candidate)


def _ensure_entities(candidate_id: int, job_id: int, session: Session, request: Request, response: Response) -> None:
    repo = Repository(session)
    _ensure_candidate(candidate_id, session, request, response)
    if repo.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")


@router.get("/candidates/{candidate_id}/job-states", response_model=list[CandidateJobStateRead])
def list_job_states(
    candidate_id: int,
    session: SessionDep,
    request: Request,
    response: Response,
    saved_only: bool = False,
    application_status: ApplicationStatus | None = None,
) -> list[CandidateJobStateRead]:
    _ensure_candidate(candidate_id, session, request, response)
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
def get_job_state(candidate_id: int, job_id: int, session: SessionDep, request: Request, response: Response) -> CandidateJobStateRead | None:
    _ensure_entities(candidate_id, job_id, session, request, response)
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
    request: Request,
    response: Response,
) -> CandidateJobStateRead:
    _ensure_entities(candidate_id, job_id, session, request, response)
    item = TrackingRepository(session).upsert(candidate_id, job_id, data)
    session.commit()
    return CandidateJobStateRead.model_validate(item)


@router.delete("/candidates/{candidate_id}/jobs/{job_id}/state", status_code=204)
def delete_job_state(candidate_id: int, job_id: int, session: SessionDep, request: Request, response: Response) -> Response:
    _ensure_entities(candidate_id, job_id, session, request, response)
    TrackingRepository(session).delete(candidate_id, job_id)
    session.commit()
    response.status_code = 204
    return response

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session

from europe_visa_jobs import __version__
from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.db.session import get_db, init_db
from europe_visa_jobs.eligibility import CountryRulesRegistry
from europe_visa_jobs.schemas import (
    CompanyRead,
    EligibilityStatus,
    JobDetailRead,
    JobRead,
    StatsRead,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Europe Visa Sponsorship Jobs API",
    version=__version__,
    description="Strict, evidence-based European tech jobs for candidates who need sponsorship.",
    lifespan=lifespan,
)

SessionDep = Annotated[Session, Depends(get_db)]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/api/v1/countries")
def countries() -> dict[str, list[str]]:
    return {"countries": CountryRulesRegistry().supported_countries()}


@app.get("/api/v1/jobs", response_model=list[JobRead])
def list_jobs(
    session: SessionDep,
    country: str | None = None,
    status: EligibilityStatus | None = EligibilityStatus.ELIGIBLE,
    job_family: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[JobRead]:
    jobs = Repository(session).list_jobs(
        country=country,
        status=status,
        job_family=job_family,
        limit=limit,
        offset=offset,
    )
    return [JobRead.model_validate(item) for item in jobs]


@app.get("/api/v1/jobs/{job_id}", response_model=JobDetailRead)
def get_job(job_id: int, session: SessionDep) -> JobDetailRead:
    job = Repository(session).get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobDetailRead.model_validate(job)


@app.get("/api/v1/companies", response_model=list[CompanyRead])
def list_companies(
    session: SessionDep,
    country: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[CompanyRead]:
    companies = Repository(session).list_companies(country=country, limit=limit)
    return [CompanyRead.model_validate(item) for item in companies]


@app.get("/api/v1/stats", response_model=StatsRead)
def stats(session: SessionDep) -> StatsRead:
    return StatsRead.model_validate(Repository(session).stats())


def run() -> None:  # pragma: no cover
    uvicorn.run("europe_visa_jobs.api.app:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":  # pragma: no cover
    run()

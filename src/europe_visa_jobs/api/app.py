from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, Response
from sqlalchemy.orm import Session

from europe_visa_jobs import __version__
from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.db.session import get_db, init_db
from europe_visa_jobs.eligibility import CountryRulesRegistry
from europe_visa_jobs.intelligence.ranking import JobRecommendation, RankingEngine
from europe_visa_jobs.schemas import (
    CandidateCreate,
    CandidateRead,
    CompanyRead,
    EligibilityStatus,
    JobDetailRead,
    JobRead,
    JobRecommendationRead,
    RecommendationExplanationRead,
    RecommendationScoresRead,
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
    visa_status: EligibilityStatus | None = None,
    job_family: str | None = None,
    category: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[JobRead]:
    jobs = Repository(session).list_jobs(
        country=country,
        status=visa_status if visa_status is not None else status,
        job_family=job_family or category,
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


def _recommendation_read(item: JobRecommendation) -> JobRecommendationRead:
    match = item.match
    return JobRecommendationRead(
        job_id=item.job.id,
        scores=RecommendationScoresRead(
            overall=item.total_score,
            visa=round(match.visa_score * 100, 2),
            skill=round(match.skill_score, 2),
            experience=round(match.experience_score, 2),
            country=round(match.country_score * 100, 2),
            company=round(match.company_score, 2),
        ),
        total_score=item.total_score,
        visa_score=round(match.visa_score * 100, 2),
        skill_score=round(match.skill_score, 2),
        skill_match=round(match.skill_score / 100, 4),
        experience_score=round(match.experience_score, 2),
        country_score=round(match.country_score * 100, 2),
        company_score=round(match.company_score, 2),
        required_skill_coverage=round(match.required_skill_coverage, 4),
        preferred_skill_coverage=round(match.preferred_skill_coverage, 4),
        seniority_match=round(match.seniority_match, 4),
        role_similarity=round(match.role_similarity, 4),
        matched_skills=match.matched_skills,
        missing_skills=match.missing_skills,
        missing_preferred_skills=match.missing_preferred_skills,
        reasons=match.reasons,
        warnings=match.warnings,
        explanation=[*match.reasons, *match.warnings],
        job=JobRead.model_validate(item.job),
    )


@app.post("/api/v1/candidates", response_model=CandidateRead, status_code=201)
@app.post("/candidates", response_model=CandidateRead, status_code=201, include_in_schema=False)
def create_candidate(candidate: CandidateCreate, session: SessionDep) -> CandidateRead:
    item = Repository(session).create_candidate(candidate)
    session.commit()
    return CandidateRead.model_validate(item)


@app.get("/api/v1/candidates/{candidate_id}", response_model=CandidateRead)
@app.get("/candidates/{candidate_id}", response_model=CandidateRead, include_in_schema=False)
def get_candidate(candidate_id: int, session: SessionDep) -> CandidateRead:
    item = Repository(session).get_candidate(candidate_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return CandidateRead.model_validate(item)


def _rank_recommendations(
    candidate_id: int,
    session: Session,
    *,
    limit: int,
    offset: int,
    country: str | None,
    role: str | None,
    min_score: float,
    include_unknown: bool,
) -> tuple[list[JobRecommendation], int]:
    repo = Repository(session)
    candidate = repo.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    engine = RankingEngine()
    jobs = repo.list_recommendation_jobs(
        include_unknown=include_unknown,
        country=country,
        role=role,
    )
    ranked = [item for item in engine.recommend(candidate, jobs, limit=500) if item.total_score >= min_score]
    return ranked[offset : offset + limit], len(ranked)


@app.get("/api/v1/recommendations/{candidate_id}", response_model=list[JobRecommendationRead])
@app.get("/recommendations/{candidate_id}", response_model=list[JobRecommendationRead], include_in_schema=False)
def recommendations(
    candidate_id: int,
    session: SessionDep,
    response: Response,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    country: str | None = None,
    role: str | None = None,
    min_score: float = Query(default=0, ge=0, le=100),
    include_unknown: bool = False,
) -> list[JobRecommendationRead]:
    ranked, total = _rank_recommendations(
        candidate_id,
        session,
        limit=limit,
        offset=offset,
        country=country,
        role=role,
        min_score=min_score,
        include_unknown=include_unknown,
    )
    response.headers["X-Total-Count"] = str(total)
    return [_recommendation_read(item) for item in ranked]


@app.get("/api/v1/recommendations/{candidate_id}/explain", response_model=RecommendationExplanationRead)
@app.get("/recommendations/{candidate_id}/explain", response_model=RecommendationExplanationRead, include_in_schema=False)
def explain_recommendations(
    candidate_id: int,
    session: SessionDep,
    response: Response,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    country: str | None = None,
    role: str | None = None,
    min_score: float = Query(default=0, ge=0, le=100),
    include_unknown: bool = False,
) -> RecommendationExplanationRead:
    repo = Repository(session)
    candidate = repo.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    engine = RankingEngine()
    ranked, total = _rank_recommendations(
        candidate_id,
        session,
        limit=limit,
        offset=offset,
        country=country,
        role=role,
        min_score=min_score,
        include_unknown=include_unknown,
    )
    response.headers["X-Total-Count"] = str(total)
    return RecommendationExplanationRead(
        candidate=CandidateRead.model_validate(candidate),
        weights=engine.config.as_dict(),
        recommendations=[_recommendation_read(item) for item in ranked],
    )


def run() -> None:  # pragma: no cover
    uvicorn.run("europe_visa_jobs.api.app:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":  # pragma: no cover
    run()

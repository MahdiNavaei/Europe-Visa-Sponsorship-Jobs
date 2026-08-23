from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from europe_visa_jobs import __version__
from europe_visa_jobs.api.tracking import router as tracking_router
from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.db.session import get_db, init_db
from europe_visa_jobs.db.source_registry import SourceRegistry
from europe_visa_jobs.eligibility import CountryRulesRegistry
from europe_visa_jobs.intelligence.company import CompanyIntelligenceScorer
from europe_visa_jobs.intelligence.ranking import JobRecommendation, RankingEngine
from europe_visa_jobs.schemas import (
    CandidateCreate,
    CandidateRead,
    CatalogSyncRead,
    CompanyIntelligenceRead,
    CompanyRead,
    CoverageRead,
    EligibilityStatus,
    JobDetailRead,
    JobRead,
    JobRecommendationRead,
    RecommendationExplanationRead,
    RecommendationScoresRead,
    SourceHealthRead,
    StatsRead,
)
from europe_visa_jobs.settings import get_settings


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

_settings = get_settings()
_allowed_origins = sorted(
    {
        origin
        for origin in (
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            _settings.web_origin.strip(),
        )
        if origin
    }
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Content-Type"],
    expose_headers=["X-Total-Count"],
    max_age=600,
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    return response


app.include_router(tracking_router)

SessionDep = Annotated[Session, Depends(get_db)]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/api/v1/catalog/status", response_model=CatalogSyncRead)
def catalog_status() -> CatalogSyncRead:
    data_dir = os.environ.get("CAREERRADAR_DATA_DIR")
    if not data_dir:
        return CatalogSyncRead(state="not_started")
    path = Path(data_dir) / "last-refresh.json"
    try:
        with path.open(encoding="utf-8") as stream:
            return CatalogSyncRead.model_validate(json.load(stream))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return CatalogSyncRead(state="not_started")


@app.get("/api/v1/countries")
def countries() -> dict[str, list[str]]:
    return {"countries": CountryRulesRegistry().supported_countries()}


@app.get("/api/v1/jobs", response_model=list[JobRead])
def list_jobs(
    session: SessionDep,
    response: Response,
    country: str | None = None,
    status: EligibilityStatus | None = None,
    visa_status: EligibilityStatus | None = None,
    job_family: str | None = None,
    category: str | None = None,
    company_id: int | None = Query(default=None, ge=1),
    query: str | None = Query(default=None, max_length=200),
    min_visa_score: float | None = Query(default=None, ge=0, le=100),
    sort: str = Query(default="newest", pattern="^(newest|visa)$"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[JobRead]:
    repo = Repository(session)
    resolved_status = visa_status if visa_status is not None else status
    browse_default = resolved_status is None
    resolved_family = job_family or category
    jobs = repo.list_jobs(
        country=country,
        status=resolved_status,
        include_unknown=browse_default,
        job_family=resolved_family,
        company_id=company_id,
        query=query,
        min_eligibility_score=min_visa_score,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    response.headers["X-Total-Count"] = str(
        repo.count_jobs(
            country=country,
            status=resolved_status,
            include_unknown=browse_default,
            job_family=resolved_family,
            company_id=company_id,
            query=query,
            min_eligibility_score=min_visa_score,
        )
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
    response: Response,
    country: str | None = None,
    query: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[CompanyRead]:
    companies = Repository(session).list_companies(country=country, query=query, limit=limit, offset=offset)
    response.headers["X-Total-Count"] = str(Repository(session).count_companies(country=country, query=query))
    return [CompanyRead.model_validate(item) for item in companies]


@app.get("/api/v1/companies/{company_id}", response_model=CompanyIntelligenceRead)
def company_intelligence(company_id: int, session: SessionDep) -> CompanyIntelligenceRead:
    repo = Repository(session)
    company = repo.get_company(company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    # Metrics must describe the complete active company catalog, not the first
    # page returned to the browser. Keep the response bounded while aggregating
    # over every active job for truthful counts and signals.
    all_jobs = repo.list_company_jobs(company_id, limit=None)
    jobs = all_jobs[:100]
    scorer = CompanyIntelligenceScorer()
    summaries = [scorer.score(company, job) for job in all_jobs]
    if summaries:
        score = round(sum(item.score for item in summaries) / len(summaries), 2)
    else:
        score = 70.0 if company.sponsor_verified else 25.0
    positive = list(dict.fromkeys(signal for item in summaries for signal in item.positive_signals))
    negative = list(dict.fromkeys(signal for item in summaries for signal in item.negative_signals))
    if company.sponsor_verified and "Recognized sponsor evidence is on file." not in positive:
        positive.insert(0, "Recognized sponsor evidence is on file.")
    eligible_jobs = repo.count_company_jobs(company_id, eligibility_status=EligibilityStatus.ELIGIBLE)
    return CompanyIntelligenceRead(
        company=CompanyRead.model_validate(company),
        visa_friendliness_score=score,
        positive_signals=positive,
        negative_signals=negative,
        active_jobs=repo.count_company_jobs(company_id),
        eligible_jobs=eligible_jobs,
        jobs=[JobRead.model_validate(job) for job in jobs],
    )


@app.get("/api/v1/stats", response_model=StatsRead)
def stats(session: SessionDep) -> StatsRead:
    return StatsRead.model_validate(Repository(session).stats())


@app.get("/api/v1/coverage", response_model=CoverageRead)
def coverage(session: SessionDep) -> CoverageRead:
    """Return source-discovery and live-ingestion coverage, including explicit unknowns."""
    return CoverageRead.model_validate(SourceRegistry(session).coverage())


@app.get("/api/v1/sources/health", response_model=list[SourceHealthRead])
def source_health(
    session: SessionDep,
    status: str | None = None,
    limit: int = Query(default=500, ge=1, le=5000),
) -> list[SourceHealthRead]:
    statuses = {status} if status else None
    sources = SourceRegistry(session).list_sources(statuses=statuses, limit=limit)
    return [SourceHealthRead.model_validate(item) for item in sources]


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


@app.put("/api/v1/candidates/{candidate_id}", response_model=CandidateRead)
def update_candidate(candidate_id: int, candidate: CandidateCreate, session: SessionDep) -> CandidateRead:
    repo = Repository(session)
    item = repo.get_candidate(candidate_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    updated = repo.update_candidate(item, candidate)
    session.commit()
    return CandidateRead.model_validate(updated)


def _rank_recommendations(
    candidate_id: int,
    session: Session,
    *,
    limit: int,
    offset: int,
    country: str | None,
    role: str | None,
    query: str | None,
    min_score: float,
    include_unknown: bool,
    sort: str,
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
        query=query,
    )
    # Personalized recommendations should not turn a visa/country match into an
    # irrelevant profession recommendation. The general Jobs page remains the
    # place to browse every eligible technical role; this endpoint is a shortlist.
    ranked = [
        item
        for item in engine.recommend(candidate, jobs, limit=None)
        if item.total_score >= min_score and item.match.role_similarity >= 0.5
    ]
    if sort == "newest":
        ranked.sort(
            key=lambda item: (
                -(item.job.posted_at.timestamp() if item.job.posted_at else 0),
                -item.total_score,
                item.job.id,
            )
        )
    elif sort == "visa":
        ranked.sort(
            key=lambda item: (
                -item.match.visa_score,
                -item.total_score,
                -(item.job.posted_at.timestamp() if item.job.posted_at else 0),
                item.job.id,
            )
        )
    return ranked[offset : offset + limit], len(ranked)


@app.get("/api/v1/recommendations/{candidate_id}/jobs/{job_id}", response_model=JobRecommendationRead)
def recommendation_for_job(candidate_id: int, job_id: int, session: SessionDep) -> JobRecommendationRead:
    repo = Repository(session)
    candidate = repo.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    job = repo.get_job(job_id)
    if job is None or not job.active:
        raise HTTPException(status_code=404, detail="Job not found")
    return _recommendation_read(RankingEngine().score(candidate, job))


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
    query: str | None = Query(default=None, max_length=200),
    min_score: float = Query(default=0, ge=0, le=100),
    include_unknown: bool = True,
    sort: str = Query(default="match", pattern="^(match|newest|visa)$"),
) -> list[JobRecommendationRead]:
    ranked, total = _rank_recommendations(
        candidate_id,
        session,
        limit=limit,
        offset=offset,
        country=country,
        role=role,
        query=query,
        min_score=min_score,
        include_unknown=include_unknown,
        sort=sort,
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
    query: str | None = Query(default=None, max_length=200),
    min_score: float = Query(default=0, ge=0, le=100),
    include_unknown: bool = True,
    sort: str = Query(default="match", pattern="^(match|newest|visa)$"),
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
        query=query,
        min_score=min_score,
        include_unknown=include_unknown,
        sort=sort,
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

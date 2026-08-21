from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from europe_visa_jobs import __version__
from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.db.session import get_db, init_db
from europe_visa_jobs.eligibility import CountryRulesRegistry
from europe_visa_jobs.intelligence.company import CompanyIntelligenceScorer
from europe_visa_jobs.intelligence.ranking import JobRecommendation, RankingEngine
from europe_visa_jobs.schemas import (
    CandidateCreate,
    CandidateRead,
    CompanyIntelligenceRead,
    CompanyRead,
    EligibilityStatus,
    JobDetailRead,
    JobRead,
    JobRecommendationRead,
    RecommendationExplanationRead,
    RecommendationScoresRead,
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=list({"http://localhost:3000", "http://127.0.0.1:3000", _settings.web_origin}),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    response: Response,
    country: str | None = None,
    status: EligibilityStatus | None = EligibilityStatus.ELIGIBLE,
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
    resolved_family = job_family or category
    jobs = repo.list_jobs(
        country=country,
        status=resolved_status,
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
    country: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[CompanyRead]:
    companies = Repository(session).list_companies(country=country, limit=limit)
    return [CompanyRead.model_validate(item) for item in companies]


@app.get("/api/v1/companies/{company_id}", response_model=CompanyIntelligenceRead)
def company_intelligence(company_id: int, session: SessionDep) -> CompanyIntelligenceRead:
    repo = Repository(session)
    company = repo.get_company(company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    jobs = repo.list_company_jobs(company_id, limit=100)
    scorer = CompanyIntelligenceScorer()
    summaries = [scorer.score(company, job) for job in jobs]
    if summaries:
        score = round(sum(item.score for item in summaries) / len(summaries), 2)
    else:
        score = 70.0 if company.sponsor_verified else 25.0
    positive = list(dict.fromkeys(signal for item in summaries for signal in item.positive_signals))
    negative = list(dict.fromkeys(signal for item in summaries for signal in item.negative_signals))
    if company.sponsor_verified and "Recognized sponsor evidence is on file." not in positive:
        positive.insert(0, "Recognized sponsor evidence is on file.")
    eligible_jobs = sum(job.eligibility_status == EligibilityStatus.ELIGIBLE.value for job in jobs)
    return CompanyIntelligenceRead(
        company=CompanyRead.model_validate(company),
        visa_friendliness_score=score,
        positive_signals=positive,
        negative_signals=negative,
        active_jobs=len(jobs),
        eligible_jobs=eligible_jobs,
        jobs=[JobRead.model_validate(job) for job in jobs],
    )


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
    ranked = [item for item in engine.recommend(candidate, jobs, limit=500) if item.total_score >= min_score]
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
    include_unknown: bool = False,
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
    include_unknown: bool = False,
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

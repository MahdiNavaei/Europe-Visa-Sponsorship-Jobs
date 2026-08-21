from __future__ import annotations

from dataclasses import dataclass

from europe_visa_jobs.db.models import Candidate, Job
from europe_visa_jobs.intelligence.matching import CandidateMatcher, MatchResult


@dataclass(frozen=True)
class RankingConfig:
    visa: float = 0.35
    skill: float = 0.30
    experience: float = 0.15
    country: float = 0.10
    company: float = 0.10

    def __post_init__(self) -> None:
        weights = (self.visa, self.skill, self.experience, self.country, self.company)
        if any(weight < 0 for weight in weights) or abs(sum(weights) - 1.0) > 1e-9:
            raise ValueError("ranking weights must be non-negative and sum to 1")

    def as_dict(self) -> dict[str, float]:
        return {"visa": self.visa, "skill": self.skill, "experience": self.experience, "country": self.country, "company": self.company}


@dataclass(frozen=True)
class JobRecommendation:
    job: Job
    total_score: float
    match: MatchResult


class RankingEngine:
    def __init__(self, config: RankingConfig | None = None, matcher: CandidateMatcher | None = None) -> None:
        self.config = config or RankingConfig()
        self.matcher = matcher or CandidateMatcher()

    def recommend(self, candidate: Candidate, jobs: list[Job], *, limit: int = 100) -> list[JobRecommendation]:
        ranked = [self.score(candidate, job) for job in jobs]
        ranked.sort(key=lambda item: (-item.total_score, -(item.job.posted_at.timestamp() if item.job.posted_at else 0), item.job.id))
        return ranked[:limit]

    def score(self, candidate: Candidate, job: Job) -> JobRecommendation:
        match = self.matcher.match(candidate, job)
        total = (
            self.config.visa * match.visa_score
            + self.config.skill * match.skill_score
            + self.config.experience * match.experience_score
            + self.config.country * (match.country_score * 100)
            + self.config.company * match.company_score
        )
        return JobRecommendation(job=job, total_score=round(total, 2), match=match)

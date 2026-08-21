from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from europe_visa_jobs.db.models import Candidate, Job
from europe_visa_jobs.intelligence.matching import CandidateMatcher, MatchResult
from europe_visa_jobs.runtime import resource_path


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

    @classmethod
    def from_yaml(cls, path: str | Path) -> RankingConfig:
        payload: Any = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("ranking configuration must be a YAML mapping")

        def weight(name: str) -> float:
            key = f"{name}_score"
            item = payload.get(key)
            if not isinstance(item, dict) or "weight" not in item:
                raise ValueError(f"ranking configuration is missing {key}.weight")
            return float(item["weight"])

        return cls(
            visa=weight("visa"),
            skill=weight("skill"),
            experience=weight("experience"),
            country=weight("country"),
            company=weight("company"),
        )


def load_ranking_config(path: str | Path | None = None) -> RankingConfig:
    config_path = Path(path) if path else resource_path("config", "ranking.yaml")
    if not config_path.is_file():
        return RankingConfig()
    return RankingConfig.from_yaml(config_path)


@dataclass(frozen=True)
class JobRecommendation:
    job: Job
    total_score: float
    match: MatchResult


class RankingEngine:
    def __init__(
        self,
        config: RankingConfig | None = None,
        matcher: CandidateMatcher | None = None,
        config_path: str | Path | None = None,
    ) -> None:
        self.config = config or load_ranking_config(config_path)
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

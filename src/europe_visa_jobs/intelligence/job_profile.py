from __future__ import annotations

import re
from dataclasses import dataclass

from europe_visa_jobs.intelligence.ontology import SkillOntology
from europe_visa_jobs.schemas import JobFamily, SeniorityLevel
from europe_visa_jobs.utils.roles import classify_role


@dataclass(frozen=True)
class JobProfile:
    required_skills: list[str]
    preferred_skills: list[str]
    min_experience_years: float | None
    seniority: SeniorityLevel | None
    job_family: JobFamily


_SENIORITY_PATTERNS: tuple[tuple[SeniorityLevel, tuple[str, ...]], ...] = (
    (SeniorityLevel.PRINCIPAL, (r"\bprincipal\b",)),
    (SeniorityLevel.STAFF, (r"\bstaff\b",)),
    (SeniorityLevel.LEAD, (r"\blead\b", r"\bhead of\b")),
    (SeniorityLevel.DIRECTOR, (r"\bdirector\b",)),
    (SeniorityLevel.SENIOR, (r"\bsenior\b", r"\bsr\.?\b")),
    (SeniorityLevel.MID, (r"\bmid[- ]level\b", r"\bmid[- ]senior\b")),
    (SeniorityLevel.JUNIOR, (r"\bjunior\b", r"\bjr\.?\b", r"\bentry[- ]level\b")),
    (SeniorityLevel.INTERN, (r"\bintern(ship)?\b",)),
)


def infer_seniority(text: str) -> SeniorityLevel | None:
    for level, patterns in _SENIORITY_PATTERNS:
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
            return level
    return None


def infer_min_experience(text: str) -> float | None:
    patterns = (
        r"(?:at least|minimum of|min\.?|more than)\s+(\d+(?:\.\d+)?)\s*\+?\s*years?",
        r"(\d+(?:\.\d+)?)\s*\+?\s*years?\s+(?:of\s+)?experience",
        r"experience\s+of\s+(\d+(?:\.\d+)?)\s*\+?\s*years?",
    )
    values = [float(match.group(1)) for pattern in patterns for match in re.finditer(pattern, text, re.IGNORECASE)]
    return max(values) if values else None


def analyze_job(title: str, description: str, job_family: JobFamily | str | None = None, *, ontology: SkillOntology | None = None) -> JobProfile:
    ontology = ontology or SkillOntology()
    full_text = f"{title}\n{description}"
    all_skills = ontology.extract(full_text)
    preferred_text = " ".join(
        sentence
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", description)
        if re.search(r"\b(?:nice to have|preferred|bonus|plus|desirable|ideally)\b", sentence, re.IGNORECASE)
    )
    preferred = ontology.extract(preferred_text)
    preferred_keys = {skill.casefold() for skill in preferred}
    required = [skill for skill in all_skills if skill.casefold() not in preferred_keys]
    family = JobFamily(job_family) if job_family else classify_role(title)
    return JobProfile(required, preferred, infer_min_experience(full_text), infer_seniority(title), family)

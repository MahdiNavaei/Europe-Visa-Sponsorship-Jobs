from __future__ import annotations

import re

from europe_visa_jobs.intelligence.job_profile import infer_min_experience, infer_seniority
from europe_visa_jobs.intelligence.ontology import SkillOntology
from europe_visa_jobs.schemas import CandidateCreate
from europe_visa_jobs.utils.countries import COUNTRY_ALIASES, infer_country
from europe_visa_jobs.utils.roles import classify_role


class CandidateProfileParser:
    """Extracts a conservative candidate profile from plain text without an LLM."""

    def __init__(self, ontology: SkillOntology | None = None) -> None:
        self.ontology = ontology or SkillOntology()

    def parse(self, text: str, *, name: str) -> CandidateCreate:
        roles = self._roles(text)
        countries = self._countries(text)
        years = infer_min_experience(text) or 0
        return CandidateCreate(
            name=name,
            target_roles=roles or ["Software Engineer"],
            skills=self.ontology.extract(text),
            years_of_experience=min(years, 60),
            seniority=infer_seniority(text),
            preferred_countries=countries,
            visa_required=True,
        )

    @staticmethod
    def _roles(text: str) -> list[str]:
        roles: list[str] = []
        for line in text.splitlines():
            cleaned = re.sub(r"^[\s•*-]*(?:title|role|position)\s*:\s*", "", line, flags=re.IGNORECASE).strip()
            if cleaned and classify_role(cleaned).value != "other" and len(cleaned) <= 100:
                roles.append(cleaned)
        return list(dict.fromkeys(roles))

    @staticmethod
    def _countries(text: str) -> list[str]:
        found: list[str] = []
        for country, aliases in COUNTRY_ALIASES.items():
            if any(re.search(rf"(?<![\w]){re.escape(alias)}(?![\w])", text, re.IGNORECASE) for alias in aliases):
                found.append(country)
        return found or ([infer_country(text)] if infer_country(text) else [])

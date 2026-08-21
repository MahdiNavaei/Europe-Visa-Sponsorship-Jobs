from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from europe_visa_jobs.db.models import Company, Job


@dataclass(frozen=True)
class CompanyIntelligence:
    score: float
    positive_signals: list[str]
    negative_signals: list[str]


class CompanyIntelligenceScorer:
    """Scores sponsor friendliness from persisted Phase-1 company and job evidence."""

    POSITIVE: ClassVar[dict[str, tuple[int, str]]] = {
        "verified_sponsor_registry": (45, "Recognized sponsor evidence is on file."),
        "relocation_support": (15, "Relocation support is mentioned."),
        "relocation_provided": (15, "The employer says relocation is provided."),
        "international_candidates": (15, "International candidates are welcomed."),
        "apply_from_abroad": (15, "Applications from abroad are accepted."),
        "visa_sponsorship": (10, "The vacancy explicitly mentions visa sponsorship."),
        "sponsor_work_visa": (10, "The employer explicitly mentions sponsoring a work visa."),
        "work_permit_support": (10, "Work-permit support is mentioned."),
        "immigration_support": (10, "Immigration support is mentioned."),
    }
    NEGATIVE: ClassVar[dict[str, tuple[int, str]]] = {
        "no_sponsorship": (-55, "The vacancy says sponsorship is unavailable."),
        "no_sponsorship_direct": (-55, "The vacancy says sponsorship is unavailable."),
        "without_sponsorship": (-45, "Existing work authorization without sponsorship is required."),
        "existing_work_rights": (-45, "Existing local work rights are required."),
        "eu_eea_only": (-45, "The vacancy is restricted to EU/EEA candidates."),
        "local_candidates_only": (-45, "The vacancy is limited to local or regional residents."),
        "citizenship_required": (-45, "The vacancy requires a specific citizenship."),
    }

    def score(self, company: Company, job: Job) -> CompanyIntelligence:
        score = 25.0
        positive: list[str] = []
        negative: list[str] = []
        if company.sponsor_verified:
            score += 45
            positive.append("Recognized sponsor evidence is on file.")

        seen: set[str] = set()
        for evidence in job.evidence:
            if evidence.code in seen:
                continue
            seen.add(evidence.code)
            if evidence.code == "verified_sponsor_registry" and company.sponsor_verified:
                continue
            if evidence.code in self.POSITIVE:
                points, message = self.POSITIVE[evidence.code]
                score += points
                positive.append(message)
            elif evidence.code in self.NEGATIVE:
                points, message = self.NEGATIVE[evidence.code]
                score += points
                negative.append(message)
        return CompanyIntelligence(max(0.0, min(100.0, score)), positive, negative)

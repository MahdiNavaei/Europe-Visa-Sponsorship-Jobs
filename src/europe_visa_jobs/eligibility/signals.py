from __future__ import annotations

import re
from dataclasses import dataclass

from europe_visa_jobs.schemas import Evidence, EvidenceKind


@dataclass(frozen=True)
class SignalMatch:
    code: str
    matched_text: str
    weight: int
    message: str


class SponsorshipSignalDetector:
    """Deterministic job-description signal detector with hard-negative precedence."""

    HARD_NEGATIVE_PATTERNS: tuple[tuple[str, str, str], ...] = (
        ("no_sponsorship", r"\b(?:do(?:es)?\s+not|don['’]?t|cannot|can['’]?t|unable\s+to|not\s+able\s+to|will\s+not|won['’]?t)\s+(?:provide|offer|support|sponsor)?\s*(?:visa|work\s+permit|immigration)\s*(?:sponsorship|support)?\b", "Employer explicitly says sponsorship or immigration support is unavailable."),
        ("no_sponsorship_direct", r"\bno\s+(?:visa\s+)?sponsorship\b|\b(?:visa\s+)?sponsorship\s+(?:is|will\s+be)\s+not\s+(?:available|provided|offered)\b", "Vacancy explicitly states that sponsorship is unavailable."),
        ("without_sponsorship", r"\b(?:authorized|authorised|eligible)\s+to\s+work\b.{0,80}\bwithout\s+(?:current\s+or\s+future\s+)?sponsorship\b", "Existing work authorization without sponsorship is required."),
        ("existing_work_rights", r"\bmust\s+(?:already\s+)?(?:have|hold)\s+(?:the\s+)?(?:legal\s+)?right\s+to\s+work\b", "Existing local work rights are required."),
        ("eu_eea_only", r"\b(?:eu|eea|european\s+union)\s+(?:citizens?|nationals?|residents?)\s+only\b|\bonly\s+(?:eu|eea)\s+(?:citizens?|nationals?|residents?)\b", "Vacancy is restricted to EU/EEA candidates."),
        ("local_candidates_only", r"\b(?:candidates?|applicants?)\s+must\s+(?:currently\s+)?(?:reside|live|be\s+based)\s+in\s+(?:the\s+)?(?:eu|eea|uk|united\s+kingdom)\b", "Vacancy requires residence in a restricted region."),
        ("citizenship_required", r"\b(?:must\s+be|requires?)\s+(?:an?\s+)?(?:uk|british|eu|eea)\s+citizen\b", "Vacancy requires a specific citizenship."),
    )

    EXPLICIT_POSITIVE_PATTERNS: tuple[tuple[str, str, str], ...] = (
        ("visa_sponsorship", r"\bvisa\s+sponsorship\b", "Vacancy explicitly mentions visa sponsorship."),
        ("sponsor_work_visa", r"\b(?:we\s+)?(?:can|will|do)\s+sponsor\b.{0,50}\b(?:visa|work\s+permit)\b", "Employer explicitly states that it sponsors a visa or work permit."),
        ("work_permit_support", r"\b(?:work\s+permit|residence\s+permit)\s+(?:support|sponsorship|assistance)\b", "Vacancy explicitly mentions work/residence permit support."),
        ("immigration_support", r"\bimmigration\s+(?:support|assistance|sponsorship)\b", "Vacancy explicitly mentions immigration support."),
        ("visa_and_relocation", r"\b(?:visa|work\s+permit)\b.{0,60}\brelocation\b|\brelocation\b.{0,60}\b(?:visa|work\s+permit)\b", "Vacancy links visa/work-permit support with relocation."),
        ("highly_skilled_migrant", r"\bhighly\s+skilled\s+migrant\b|\bkennismigrant\b", "Vacancy mentions the Dutch highly skilled migrant route."),
        ("blue_card", r"\b(?:eu|european\s+union)\s+blue\s+card\b", "Vacancy mentions the EU Blue Card route."),
    )

    RELOCATION_PATTERNS: tuple[tuple[str, str, str], ...] = (
        ("relocation_support", r"\brelocation\s+(?:support|assistance|package|provided|available)\b", "Vacancy mentions relocation support."),
        ("relocation_provided", r"\bwe\s+(?:offer|provide)\b.{0,40}\brelocation\b", "Employer states that relocation is provided."),
    )

    INTERNATIONAL_PATTERNS: tuple[tuple[str, str, str], ...] = (
        ("international_candidates", r"\b(?:international|overseas)\s+(?:candidates?|applicants?|talent)\b", "Vacancy welcomes international/overseas candidates."),
        ("apply_from_abroad", r"\b(?:apply|applications?)\s+from\s+abroad\b", "Vacancy accepts applications from abroad."),
    )

    def hard_negatives(self, text: str) -> list[Evidence]:
        return self._scan(text, self.HARD_NEGATIVE_PATTERNS, EvidenceKind.JOB_NEGATIVE, -100)

    def explicit_positives(self, text: str) -> list[Evidence]:
        return self._scan(text, self.EXPLICIT_POSITIVE_PATTERNS, EvidenceKind.JOB_POSITIVE, 50)

    def relocation_signals(self, text: str) -> list[Evidence]:
        return self._scan(text, self.RELOCATION_PATTERNS, EvidenceKind.JOB_POSITIVE, 20)

    def international_signals(self, text: str) -> list[Evidence]:
        return self._scan(text, self.INTERNATIONAL_PATTERNS, EvidenceKind.JOB_POSITIVE, 15)

    @staticmethod
    def _scan(
        text: str,
        patterns: tuple[tuple[str, str, str], ...],
        kind: EvidenceKind,
        default_weight: int,
    ) -> list[Evidence]:
        matches: list[Evidence] = []
        for code, pattern, message in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
            if match:
                matched = re.sub(r"\s+", " ", match.group(0)).strip()
                matches.append(
                    Evidence(
                        kind=kind,
                        code=code,
                        message=message,
                        weight=default_weight,
                        matched_text=matched[:200],
                    )
                )
        return matches

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
    """Conservative detector: a bare sponsorship mention is never positive evidence."""

    HARD_NEGATIVE_PATTERNS: tuple[tuple[str, str, str], ...] = (
        (
            "no_sponsorship",
            r"\b(?:do(?:es)?\s+not|don(?:'|\u2019)?t|cannot|can(?:'|\u2019)?t|unable\s+to|not\s+able\s+to|"
            r"will\s+not|won(?:'|\u2019)?t)\s+(?:provide|offer|support|sponsor)?\s*(?:visa|work\s+permit|"
            r"immigration)\s*(?:sponsorship|support|assistance)?\b",
            "Employer explicitly says sponsorship or immigration support is unavailable.",
        ),
        (
            "no_sponsorship_direct",
            r"\b(?:no|without)\s+(?:(?:visa|work[- ]permit|immigration)\s+)?(?:sponsorship|support|assistance)\b|"
            r"\b(?:visa|work[- ]permit|immigration)\s+(?:sponsorship|support|assistance)\s+"
            r"(?:is|will\s+be|are)\s+(?:not\s+available|not\s+provided|not\s+offered|unavailable)\b",
            "Vacancy explicitly states that sponsorship is unavailable.",
        ),
        (
            "without_sponsorship",
            r"\b(?:authorized|authorised|eligible)\s+to\s+work\b.{0,80}\bwithout\s+"
            r"(?:current\s+or\s+future\s+)?sponsorship\b",
            "Existing work authorization without sponsorship is required.",
        ),
        (
            "existing_work_rights",
            r"\bmust\s+(?:already\s+)?(?:have|hold|possess)\s+(?:the\s+)?(?:legal\s+)?(?:right|permission|"
            r"authori[sz]ation)\s+to\s+work\b",
            "Existing local work rights are required.",
        ),
        (
            "eu_eea_only",
            r"\b(?:eu|eea|european\s+union)\s+(?:citizens?|nationals?|residents?)\s+only\b|"
            r"\bonly\s+(?:eu|eea)\s+(?:citizens?|nationals?|residents?)\b",
            "Vacancy is restricted to EU/EEA candidates.",
        ),
        (
            "local_candidates_only",
            r"\b(?:candidates?|applicants?)\s+must\s+(?:currently\s+)?(?:reside|live|be\s+based)\s+in\s+"
            r"(?:the\s+)?(?:eu|eea|uk|united\s+kingdom)\b",
            "Vacancy requires residence in a restricted region.",
        ),
        (
            "citizenship_required",
            r"\b(?:must\s+be|requires?)\s+(?:an?\s+)?(?:uk|british|eu|eea)\s+citizen\b",
            "Vacancy requires a specific citizenship.",
        ),
        (
            "de_no_sponsorship",
            r"\b(?:kein(?:e|en|er)?\s+(?:visa|visum|visums)[- ]?(?:sponsoring|unterst(?:u|ü)tzung)|"
            r"visumsponsoring\s+(?:ist\s+)?(?:nicht\s+m(?:o|ö)glich|nicht\s+verf(?:u|ü)gbar)|"
            r"(?:bewerber|bewerberinnen|kandidaten)\s+m(?:u|ü)ssen\s+bereits\s+(?:eine\s+)?"
            r"(?:g(?:u|ü)ltige\s+)?arbeitserlaubnis\s+besitzen)\b",
            "Vacancy requires existing German work authorization or refuses visa support.",
        ),
        (
            "nl_no_sponsorship",
            r"\b(?:geen\s+(?:visum|visa)[- ]?sponsoring|visumsponsoring\s+(?:is\s+)?niet\s+beschikbaar|"
            r"(?:sollicitanten|kandidaten)\s+moeten\s+reeds\s+(?:over\s+)?(?:een\s+)?"
            r"(?:geldige\s+)?(?:werkvergunning|werktoestemming)\s+beschikken)\b",
            "Vacancy requires existing Dutch work authorization or refuses visa support.",
        ),
        (
            "fr_no_sponsorship",
            r"\b(?:aucun(?:e)?\s+(?:parrainage|prise\s+en\s+charge|assistance)\s+(?:de\s+)?visa|"
            r"parrainage\s+(?:de\s+)?visa\s+(?:n(?:'|\u2019)est\s+pas|non)\s+disponible|"
            r"(?:candidats?|vous)\s+(?:devez|doivent)\s+d(?:é|e)j(?:à|a)\s+(?:disposer|poss(?:é|e)der)\s+"
            r"d(?:'|\u2019)une\s+autorisation\s+de\s+travail)\b",
            "Vacancy requires existing French work authorization or refuses visa support.",
        ),
    )

    EXPLICIT_POSITIVE_PATTERNS: tuple[tuple[str, str, str], ...] = (
        (
            "visa_sponsorship",
            r"\b(?:we|the\s+(?:company|employer)|this\s+role)\s+(?:can\s+|will\s+|do\s+)?"
            r"(?:provide|offer|support)\b.{0,40}\bvisa\s+sponsorship\b|"
            r"\bvisa\s+sponsorship\s+(?:is\s+)?(?:available|provided|offered|supported)\b",
            "Employer affirmatively states that visa sponsorship is available.",
        ),
        (
            "sponsor_work_visa",
            r"\b(?:we|the\s+(?:company|employer))\s+(?:can|will|do)\s+sponsor\b.{0,50}"
            r"\b(?:visa|work\s+permit)\b",
            "Employer explicitly states that it sponsors a visa or work permit.",
        ),
        (
            "work_permit_support",
            r"\b(?:we|the\s+(?:company|employer))\s+(?:can\s+|will\s+|do\s+)?(?:provide|offer)\b.{0,40}"
            r"\b(?:work|residence)\s+permit\s+(?:support|sponsorship|assistance)\b|"
            r"\b(?:work|residence)\s+permit\s+(?:support|sponsorship|assistance)\s+"
            r"(?:is\s+)?(?:available|provided|offered)\b",
            "Employer affirmatively offers work/residence permit support.",
        ),
        (
            "immigration_support",
            r"\bimmigration\s+(?:support|assistance|sponsorship)\s+(?:is\s+)?"
            r"(?:available|provided|offered)\b|\bwe\s+(?:provide|offer)\s+immigration\s+"
            r"(?:support|assistance|sponsorship)\b",
            "Employer affirmatively offers immigration support.",
        ),
        (
            "visa_and_relocation",
            r"\b(?:we\s+(?:provide|offer)\s+)?(?:visa|work\s+permit)\s+(?:support|sponsorship|assistance)\b"
            r".{0,60}\brelocation\b|\brelocation\b.{0,60}\b(?:visa|work\s+permit)\s+"
            r"(?:support|sponsorship|assistance)\b",
            "Vacancy affirmatively links visa/work-permit support with relocation.",
        ),
        (
            "de_visa_support",
            r"\b(?:wir\s+(?:bieten|unterst(?:u|ü)tzen|(?:u|ü)bernehmen)\b.{0,45}"
            r"(?:visum|arbeitserlaubnis)|visumsponsoring\s+(?:wird\s+)?(?:angeboten|bereitgestellt|unterst(?:u|ü)tzt))\b",
            "Employer affirmatively offers visa/work-permit support in German.",
        ),
        (
            "nl_visa_support",
            r"\b(?:wij\s+(?:bieden|regelen|ondersteunen)\b.{0,45}(?:visum|werkvergunning)|"
            r"visumsponsoring\s+(?:is\s+)?(?:beschikbaar|mogelijk|voorzien))\b",
            "Employer affirmatively offers visa/work-permit support in Dutch.",
        ),
        (
            "fr_visa_support",
            r"\b(?:nous\s+(?:offrons|proposons|prenons\s+en\s+charge)\b.{0,45}(?:visa|permis\s+de\s+travail)|"
            r"parrainage\s+(?:de\s+)?visa\s+(?:est\s+)?(?:disponible|offert|propos(?:é|e)))\b",
            "Employer affirmatively offers visa/work-permit support in French.",
        ),
    )

    RELOCATION_PATTERNS: tuple[tuple[str, str, str], ...] = (
        (
            "relocation_support",
            r"\brelocation\s+(?:support|assistance|package|provided|available)\b",
            "Vacancy mentions relocation support.",
        ),
        (
            "relocation_provided",
            r"\bwe\s+(?:offer|provide)\b.{0,40}\brelocation\b",
            "Employer states that relocation is provided.",
        ),
    )

    INTERNATIONAL_PATTERNS: tuple[tuple[str, str, str], ...] = (
        (
            "international_candidates",
            r"\b(?:international|overseas)\s+(?:candidates?|applicants?|talent)\b",
            "Vacancy welcomes international/overseas candidates.",
        ),
        (
            "apply_from_abroad",
            r"\b(?:apply|applications?)\s+from\s+abroad\b",
            "Vacancy accepts applications from abroad.",
        ),
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

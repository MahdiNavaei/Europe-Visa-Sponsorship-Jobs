from __future__ import annotations

from datetime import UTC, datetime

from europe_visa_jobs.eligibility.country_rules import CountryRulesRegistry
from europe_visa_jobs.eligibility.signals import SponsorshipSignalDetector
from europe_visa_jobs.eligibility.sponsor_registry import SponsorRegistryStore
from europe_visa_jobs.schemas import (
    EligibilityAssessment,
    EligibilityStatus,
    Evidence,
    EvidenceKind,
    NormalizedJob,
)


class EligibilityEngine:
    """Strict, explainable, no-LLM eligibility gate for phase 1."""

    def __init__(
        self,
        sponsor_registry: SponsorRegistryStore | None = None,
        country_rules: CountryRulesRegistry | None = None,
        detector: SponsorshipSignalDetector | None = None,
    ) -> None:
        self.sponsor_registry = sponsor_registry or SponsorRegistryStore()
        self.country_rules = country_rules or CountryRulesRegistry()
        self.detector = detector or SponsorshipSignalDetector()

    def assess(self, job: NormalizedJob) -> EligibilityAssessment:
        text = f"{job.title}\n{job.description}\n{job.location}"
        hard_negatives = self.detector.hard_negatives(text)
        if hard_negatives:
            return EligibilityAssessment(
                status=EligibilityStatus.REJECTED,
                score=0,
                country=job.country,
                evidence=hard_negatives,
                hard_rejection_reasons=[item.code for item in hard_negatives],
                assessed_at=datetime.now(UTC),
            )

        country_rule = self.country_rules.get(job.country)
        if country_rule is None or not country_rule.supported:
            return EligibilityAssessment(
                status=EligibilityStatus.UNKNOWN,
                score=0,
                country=job.country,
                evidence=[
                    Evidence(
                        kind=EvidenceKind.COUNTRY_RULE,
                        code="unsupported_country",
                        message="Country is not covered by the phase-1 rule registry.",
                        weight=0,
                    )
                ],
                assessed_at=datetime.now(UTC),
            )

        evidence: list[Evidence] = [
            Evidence(
                kind=EvidenceKind.COUNTRY_RULE,
                code="supported_country",
                message=f"Country rule available for {country_rule.country}.",
                weight=5,
            )
        ]
        score = 5
        explicit = self.detector.explicit_positives(text)
        relocation = self.detector.relocation_signals(text)
        international = self.detector.international_signals(text)
        evidence.extend(explicit)
        evidence.extend(relocation)
        evidence.extend(international)

        if explicit:
            score += 50
        if relocation:
            score += 20
        if international:
            score += 15

        registry_record = self.sponsor_registry.find(job.company_name, job.country)
        if registry_record:
            evidence.append(
                Evidence(
                    kind=EvidenceKind.COMPANY_REGISTRY,
                    code="verified_sponsor_registry",
                    message=f"Company is verified in {registry_record.registry_name}.",
                    weight=45,
                    source_url=registry_record.source_url,
                )
            )
            score += 45

        # Strict phase-1 policy:
        # 1) Countries with a formal sponsor register require verified company evidence.
        # 2) Every displayed job needs explicit job-level visa/work-permit evidence, OR a verified
        #    sponsor plus a relocation/international-candidate signal.
        if country_rule.sponsor_registry_required and registry_record is None:
            evidence.append(
                Evidence(
                    kind=EvidenceKind.COUNTRY_RULE,
                    code="sponsor_registry_not_verified",
                    message=f"Strict mode requires a match in {country_rule.sponsor_registry_name}.",
                    weight=0,
                )
            )
            return self._unknown(job, country_rule.primary_routes, evidence, min(score, 69))

        strong_job_evidence = bool(explicit) or bool(registry_record and (relocation or international))
        if not strong_job_evidence:
            evidence.append(
                Evidence(
                    kind=EvidenceKind.JOB_POSITIVE,
                    code="insufficient_job_level_evidence",
                    message="No strong job-level sponsorship evidence was found; strict mode hides this job.",
                    weight=0,
                )
            )
            return self._unknown(job, country_rule.primary_routes, evidence, min(score, 69))

        return EligibilityAssessment(
            status=EligibilityStatus.ELIGIBLE,
            score=min(score, 100),
            country=job.country,
            visa_routes=country_rule.primary_routes,
            evidence=evidence,
            assessed_at=datetime.now(UTC),
        )

    @staticmethod
    def _unknown(
        job: NormalizedJob,
        routes: list[str],
        evidence: list[Evidence],
        score: int,
    ) -> EligibilityAssessment:
        return EligibilityAssessment(
            status=EligibilityStatus.UNKNOWN,
            score=max(0, score),
            country=job.country,
            visa_routes=routes,
            evidence=evidence,
            assessed_at=datetime.now(UTC),
        )

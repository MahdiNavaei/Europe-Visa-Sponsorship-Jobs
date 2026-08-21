from __future__ import annotations

from europe_visa_jobs.eligibility import EligibilityEngine, SponsorRegistryStore
from europe_visa_jobs.schemas import (
    ATSProvider,
    CompanySponsorEvidence,
    EligibilityStatus,
    NormalizedJob,
)


def job(description: str, *, country: str = "Germany", company: str = "Acme") -> NormalizedJob:
    return NormalizedJob(
        external_id="1",
        provider=ATSProvider.GREENHOUSE,
        source_slug="acme",
        company_name=company,
        title="Senior Software Engineer",
        description=description,
        location=f"Remote, {country}",
        country=country,
        apply_url="https://example.com/apply",
    )


def test_explicit_sponsorship_is_eligible_in_non_registry_country():
    result = EligibilityEngine().assess(job("We provide visa sponsorship and relocation support."))
    assert result.status == EligibilityStatus.ELIGIBLE
    assert result.score >= 70
    assert any(item.code == "visa_sponsorship" for item in result.evidence)


def test_hard_negative_overrides_positive_words():
    result = EligibilityEngine().assess(
        job("We are unable to provide visa sponsorship. You must already have the right to work in Germany.")
    )
    assert result.status == EligibilityStatus.REJECTED
    assert result.score == 0
    assert "no_sponsorship" in result.hard_rejection_reasons


def test_direct_no_sponsorship_phrase_is_rejected():
    result = EligibilityEngine().assess(job("This role offers great benefits. No visa sponsorship."))
    assert result.status == EligibilityStatus.REJECTED
    assert "no_sponsorship_direct" in result.hard_rejection_reasons


def test_eu_only_restriction_is_rejected():
    result = EligibilityEngine().assess(job("Visa sponsorship may be discussed. EU citizens only."))
    assert result.status == EligibilityStatus.REJECTED
    assert "eu_eea_only" in result.hard_rejection_reasons


def test_unknown_when_job_has_no_sponsorship_evidence():
    result = EligibilityEngine().assess(job("Great engineering team and flexible hybrid work."))
    assert result.status == EligibilityStatus.UNKNOWN
    assert any(item.code == "insufficient_job_level_evidence" for item in result.evidence)


def test_netherlands_requires_verified_registry_in_strict_mode():
    result = EligibilityEngine().assess(
        job("Visa sponsorship and relocation support are available.", country="Netherlands")
    )
    assert result.status == EligibilityStatus.UNKNOWN
    assert any(item.code == "sponsor_registry_not_verified" for item in result.evidence)


def test_registry_plus_relocation_qualifies_netherlands_job():
    registry = SponsorRegistryStore(
        [
            CompanySponsorEvidence(
                company_name="Acme B.V.",
                country="Netherlands",
                registry_name="IND Public Register Recognised Sponsors - Labour",
                source_url="https://ind.nl/example",
            )
        ]
    )
    result = EligibilityEngine(sponsor_registry=registry).assess(
        job("We provide a relocation package for international candidates.", country="Netherlands", company="Acme")
    )
    assert result.status == EligibilityStatus.ELIGIBLE
    assert result.score >= 70
    assert any(item.code == "verified_sponsor_registry" for item in result.evidence)


def test_unsupported_country_is_hidden():
    result = EligibilityEngine().assess(job("Visa sponsorship available.", country="Italy"))
    assert result.status == EligibilityStatus.UNKNOWN
    assert result.score == 0

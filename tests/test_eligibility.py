from __future__ import annotations

import pytest

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


@pytest.mark.parametrize(
    "description",
    [
        "We are unable to sponsor candidates for this position.",
        "This role is not eligible for sponsorship.",
    ],
)
def test_generic_sponsorship_refusals_are_rejected(description: str):
    result = EligibilityEngine().assess(job(description))
    assert result.status == EligibilityStatus.REJECTED
    assert "no_sponsorship_generic" in result.hard_rejection_reasons


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


def test_known_european_country_uses_conservative_country_rule():
    result = EligibilityEngine().assess(job("Visa sponsorship available.", country="Italy"))
    assert result.status == EligibilityStatus.ELIGIBLE
    assert result.score >= 50


def test_unknown_non_european_country_is_not_claimed_as_european_coverage():
    result = EligibilityEngine().assess(job("Visa sponsorship available.", country="Canada"))
    assert result.status == EligibilityStatus.UNKNOWN
    assert result.score == 0
    assert any(item.code == "visa_sponsorship" for item in result.evidence)
    assert any(item.code == "unsupported_country" for item in result.evidence)


@pytest.mark.parametrize(
    "description",
    [
        "Will you now or in the future require visa sponsorship?",
        "Please state whether visa sponsorship would be required.",
        "Visa sponsorship may be discussed during the interview process.",
        "Experience with immigration support systems is a plus.",
    ],
)
def test_ambiguous_sponsorship_mentions_are_not_positive(description: str):
    result = EligibilityEngine().assess(job(description))
    assert result.status == EligibilityStatus.UNKNOWN
    assert not any(item.kind.value == "job_positive" and item.weight >= 50 for item in result.evidence)


@pytest.mark.parametrize(
    ("description", "reason"),
    [
        ("Visa sponsorship is unavailable for this position.", "no_sponsorship_direct"),
        ("Work permit support is not provided.", "no_sponsorship_direct"),
        ("Bewerber müssen bereits eine Arbeitserlaubnis besitzen.", "de_no_sponsorship"),
        ("Visumsponsoring ist nicht möglich.", "de_no_sponsorship"),
        ("Kandidaten moeten reeds over een werkvergunning beschikken.", "nl_no_sponsorship"),
        ("Visumsponsoring is niet beschikbaar.", "nl_no_sponsorship"),
        ("Vous devez déjà disposer d\u2019une autorisation de travail.", "fr_no_sponsorship"),
        ("Parrainage de visa non disponible.", "fr_no_sponsorship"),
    ],
)
def test_multilingual_restriction_corpus_is_rejected(description: str, reason: str):
    result = EligibilityEngine().assess(job(description))
    assert result.status == EligibilityStatus.REJECTED
    assert reason in result.hard_rejection_reasons


@pytest.mark.parametrize(
    "description",
    [
        "Wir bieten Unterstützung beim Visum und bei der Arbeitserlaubnis.",
        "Visumsponsoring wird angeboten.",
        "Wij bieden ondersteuning bij het visum en de werkvergunning.",
        "Visumsponsoring is beschikbaar.",
        "Nous offrons une prise en charge du visa et du permis de travail.",
        "Parrainage de visa disponible.",
    ],
)
def test_multilingual_affirmative_corpus_is_eligible(description: str):
    result = EligibilityEngine().assess(job(description))
    assert result.status == EligibilityStatus.ELIGIBLE
    assert any(item.kind.value == "job_positive" and item.weight >= 50 for item in result.evidence)


def test_negative_clause_overrides_affirmative_clause_in_any_order():
    result = EligibilityEngine().assess(
        job("We provide relocation support. However, visa sponsorship is unavailable for this position.")
    )
    assert result.status == EligibilityStatus.REJECTED

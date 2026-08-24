from __future__ import annotations

from europe_visa_jobs.schemas import CountryRule
from europe_visa_jobs.utils.countries import EUROPEAN_COUNTRIES

# Phase-1 rules deliberately encode route structure, not legal advice or volatile salary numbers.
# Numeric thresholds should be maintained as dated datasets once salary-aware filtering is added.
_RULES: dict[str, CountryRule] = {
    "Netherlands": CountryRule(
        country="Netherlands",
        primary_routes=["Highly Skilled Migrant"],
        sponsor_registry_required=True,
        sponsor_registry_name="IND Public Register Recognised Sponsors - Labour",
        notes=["Recognised sponsor evidence is required by the strict phase-1 gate."],
    ),
    "Germany": CountryRule(
        country="Germany",
        primary_routes=["EU Blue Card", "Skilled Worker Residence Permit"],
        notes=["Eligibility depends on the specific role and candidate; no sponsor licence register is required."],
    ),
    "United Kingdom": CountryRule(
        country="United Kingdom",
        primary_routes=["Skilled Worker"],
        sponsor_registry_required=True,
        sponsor_registry_name="UKVI Register of Licensed Sponsors (Workers)",
        notes=["A sponsor licence alone does not prove that a specific vacancy is sponsored."],
    ),
    "Ireland": CountryRule(
        country="Ireland",
        primary_routes=["Critical Skills Employment Permit", "General Employment Permit"],
        notes=["Employer permit history is useful evidence but is not treated as a blanket guarantee."],
    ),
    "Sweden": CountryRule(
        country="Sweden",
        primary_routes=["Work Permit"],
        notes=["Job-level work-permit or immigration support evidence is required by the strict phase-1 gate."],
    ),
    "Finland": CountryRule(
        country="Finland",
        primary_routes=["Residence Permit for Specialists", "Residence Permit for an Employed Person"],
        notes=["Job-level permit or immigration support evidence is required by the strict phase-1 gate."],
    ),
    "Denmark": CountryRule(
        country="Denmark",
        primary_routes=["Pay Limit Scheme", "Positive List for People with a Higher Education"],
        notes=["Job-level permit or immigration support evidence is required by the strict phase-1 gate."],
    ),
}

# The product covers European hiring markets, not only the small set of routes
# that had country-specific phase-1 notes originally.  These conservative
# fallback rules deliberately do not assert sponsorship or a sponsor register;
# they only keep a known European country from being mislabeled as unsupported.
# JD-level evidence and the candidate-specific gate remain authoritative.
for _country in EUROPEAN_COUNTRIES:
    _RULES.setdefault(
        _country,
        CountryRule(
            country=_country,
            primary_routes=["Country-specific work permit route"],
            notes=[
                "Country coverage is geographic only; verify the current national route and employer policy before applying."
            ],
        ),
    )


class CountryRulesRegistry:
    def get(self, country: str | None) -> CountryRule | None:
        if not country:
            return None
        return _RULES.get(country)

    def supported_countries(self) -> list[str]:
        return sorted(_RULES)

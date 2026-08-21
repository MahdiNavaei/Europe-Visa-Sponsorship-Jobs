# Contributing

Thanks for helping improve Europe Visa Sponsorship Jobs.

The project is designed to become community-driven once public. Accuracy matters more than job volume: a false claim that a vacancy supports immigration can waste a candidate's time.

## Phase 1 contribution areas

Contributions are especially useful for:

- ATS connectors and parser fixtures
- European country-rule metadata
- verified official sponsor-registry data
- visa/work-permit signal phrases
- hard restriction phrases
- country and city normalization
- technical role classification
- tests and documentation

## Non-negotiable rules

1. **No paid LLM/API dependency.** Phase 1 must run without OpenAI, Anthropic, Gemini, or similar services.
2. **Evidence over guesses.** Missing evidence should produce `unknown`, not `eligible`.
3. **Hard negatives win.** Existing-work-authorization, citizenship, EU/EEA-only, or no-sponsorship restrictions must override positive wording.
4. **A sponsor company does not imply every job is sponsored.** Vacancy-level evidence is still required.
5. **Prefer first-party sources.** Use documented/public company ATS feeds and official immigration/sponsor sources where possible.
6. **Do not bypass authentication, anti-bot controls, or website restrictions.**
7. **Add tests with behavior changes.**

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
```

Run the quality suite:

```bash
python -m compileall -q src
ruff check src tests
pytest --cov=europe_visa_jobs --cov-report=term-missing --cov-fail-under=85
```

Migration smoke test:

```bash
DATABASE_URL=sqlite:///./migration_check.db alembic upgrade head
DATABASE_URL=sqlite:///./migration_check.db alembic downgrade base
```

## Adding an ATS connector

A connector must:

- inherit from `BaseConnector`
- consume a public job feed
- return `list[NormalizedJob]`
- keep provider parsing separate from eligibility logic
- preserve the canonical apply URL
- include mocked connector tests
- raise `ConnectorError` for malformed/unavailable feeds

Register it in `connectors/factory.py` only after tests exist.

## Adding or changing visa rules

Country route metadata belongs in `eligibility/country_rules.py`.

Textual sponsorship/restriction evidence belongs in `eligibility/signals.py`.

Do not hard-code volatile salary thresholds into regex rules. Time-sensitive legal thresholds should be maintained as dated datasets with an official source.

## Pull requests

Before opening a PR:

- run the full test suite
- run Ruff
- run the migration smoke test for schema changes
- document new public data sources
- explain false-positive/false-negative implications for eligibility changes

The project deliberately prefers false negatives over false positives for the default user-facing job list.

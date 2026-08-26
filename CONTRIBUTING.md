# Contributing

Thanks for helping improve Career Radar / Europe Visa Sponsorship Jobs. Accuracy
matters more than job volume: a false sponsorship claim can waste a candidate's time.

## Useful contribution areas

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

1. **No paid LLM/API dependency at runtime.** The product must run without OpenAI, Anthropic, Gemini, or similar paid services.
2. **Evidence over guesses.** Missing evidence should produce `unknown`, not `eligible`.
3. **Hard negatives win.** Existing-work-authorization, citizenship, EU/EEA-only, or no-sponsorship restrictions must override positive wording.
4. **A sponsor company does not imply every job is sponsored.** Vacancy-level evidence is still required.
5. **Prefer first-party sources.** Use documented/public company ATS feeds and official immigration/sponsor sources where possible.
6. **Do not bypass authentication, anti-bot controls, or website restrictions.**
7. **Add tests with behavior changes.**

## Contribution licensing

The repository is source-available under the PolyForm Noncommercial License 1.0.0.
By submitting a contribution, you represent that you have the right to submit it and
agree it may be distributed as part of this project under that public license.

To preserve the project's dual-licensing model, you also grant **Mahdi Navaei**, as
maintainer, a perpetual, worldwide, non-exclusive, royalty-free license to use,
reproduce, modify, distribute, sublicense, and relicense your contribution, including
under commercial terms. This grant applies only to your contribution and does not
transfer ownership of your copyright. If you lack authority to make these grants,
please do not submit the contribution.

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

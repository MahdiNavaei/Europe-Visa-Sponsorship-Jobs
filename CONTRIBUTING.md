# Contributing

Thanks for helping improve Europe Visa Sponsorship Jobs / Career Radar.

Accuracy matters more than job volume: a false claim that a vacancy supports
immigration can waste a candidate's time.

## Useful contribution areas

Contributions are especially useful for:

- ATS connectors and parser fixtures
- European country-rule metadata
- verified official sponsor-registry data
- visa/work-permit signal phrases
- hard restriction phrases
- country and city normalization
- technical role classification
- tests, accessibility, and documentation

## Non-negotiable rules

1. **No paid LLM/API dependency at runtime.** The core product must remain usable without OpenAI, Anthropic, Gemini, or similar paid services.
2. **Evidence over guesses.** Missing evidence should not be promoted into a positive sponsorship claim.
3. **Hard negatives win.** Existing-work-authorization, citizenship, EU/EEA-only, or no-sponsorship restrictions must override positive wording.
4. **A sponsor company does not imply every job is sponsored.** Vacancy-level evidence is still required.
5. **Prefer first-party sources.** Use documented/public company ATS feeds and official immigration/sponsor sources where possible.
6. **Do not bypass authentication, anti-bot controls, or website restrictions.**
7. **Add tests with behavior changes.**

## Contribution licensing

The public repository is licensed under the PolyForm Noncommercial License 1.0.0.
By submitting a contribution, you represent that you have the right to submit it and
agree that the contribution may be distributed as part of this project under the
repository's public license.

To preserve the project's dual-licensing model, you also grant **Mahdi Navaei**, as
project maintainer, a perpetual, worldwide, non-exclusive, royalty-free license to use,
reproduce, modify, distribute, sublicense, and relicense your contribution, including
under commercial terms. This additional grant applies only to the contribution you
submit and does not transfer ownership of your copyright.

If you do not have the authority to make these grants, do not submit the contribution.
If your employer or another party owns rights in your work, obtain any required
permission first.

See [`LICENSE`](LICENSE), [`NOTICE`](NOTICE), and
[`COMMERCIAL_LICENSE.md`](COMMERCIAL_LICENSE.md).

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

Do not hard-code volatile salary thresholds into regex rules. Time-sensitive legal
thresholds should be maintained as dated datasets with an official source.

## Pull requests

Before opening a PR:

- run the full test suite
- run Ruff
- run the migration smoke test for schema changes
- document new public data sources
- explain false-positive/false-negative implications for eligibility changes
- confirm that you can make the contribution-licensing grants described above

The project deliberately prioritizes evidence quality over inflated coverage claims.

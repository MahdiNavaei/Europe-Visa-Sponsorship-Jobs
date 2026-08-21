# Phase 1 Completion Notes

Phase 1 establishes the backend and data-intelligence foundation for Europe Visa Sponsorship Jobs.

## Delivered

### Data ingestion

Five first-party ATS connectors normalize public vacancies into one schema:

- Greenhouse
- Lever
- Ashby
- Workable
- Personio

### Catalog integrity

- deterministic technical-role classification
- provider/source/external-id uniqueness
- first/last seen timestamps
- stale job deactivation after successful source refresh
- ingestion success/failure tracking

### Visa intelligence

- hard-negative precedence
- explicit sponsorship signals
- work/residence permit signals
- relocation signals
- international candidate signals
- formal sponsor-registry evidence
- country-route metadata
- strict `eligible/rejected/unknown` states
- persisted evidence for every assessment

### Storage/API

- SQLAlchemy schema
- PostgreSQL and SQLite support
- Alembic initial migration
- FastAPI health, jobs, job detail, companies, countries, and stats endpoints

### Quality

- deterministic unit/integration tests
- connector normalization tests with mocked public-feed payloads
- eligibility regression tests
- repository tests
- ingestion tests
- API tests
- CI coverage threshold

## Explicit non-goals in Phase 1

- candidate/CV matching (Phase 2)
- frontend/UI (Phase 3)
- complete production E2E matrix (Phase 4)
- LLM/paid AI APIs (not required)

# Roadmap

The project is intentionally divided into four delivery phases.

## Phase 1 — Core Platform & Data Intelligence Engine ✅

- [x] Python package and project structure
- [x] Normalized job schema
- [x] PostgreSQL/SQLite database schema
- [x] Alembic migration
- [x] Company, job, evidence, sponsor-record, and ingestion-run persistence
- [x] ATS connector interface
- [x] Greenhouse connector
- [x] Lever connector (global + EU)
- [x] Ashby connector
- [x] Workable connector
- [x] Personio XML connector
- [x] Job normalization
- [x] Country inference
- [x] Technical-role classification
- [x] Hard work-authorization/geographic restriction detection
- [x] Positive visa/work-permit/relocation signal detection
- [x] Sponsor registry evidence store and CSV importer
- [x] Country-rule registry: NL, DE, UK, IE, SE, FI, DK
- [x] Explainable strict eligibility engine
- [x] Stale-job deactivation
- [x] FastAPI endpoints
- [x] Docker/PostgreSQL development environment
- [x] CI + coverage gate
- [x] Optional scheduled ingestion workflow
- [x] No LLM / no paid AI API dependency

## Phase 2 — Candidate Matching & Intelligence ✅

- [x] Candidate profile
- [x] Role preferences and experience level
- [x] Skill taxonomy
- [x] Skill aliases/synonyms
- [x] Deterministic CV/profile parsing where practical
- [x] Job-to-profile match score
- [x] Country preferences
- [x] Candidate-specific eligibility checks
- [x] Explainable ranking
- [ ] Saved jobs and application state

## Phase 3 — Professional UI/UX

- [x] Product design system
- [x] Responsive public landing page
- [x] Candidate onboarding flow
- [x] Professional job discovery dashboard
- [x] Search, filters, sort, and empty/loading/error states
- [x] Visa-evidence visualization
- [x] Job detail experience
- [x] Company intelligence page
- [x] Candidate profile/settings UX
- [x] Accessibility review
- [x] Mobile/tablet/desktop responsive behavior
- [x] UX polish and interaction states

## Phase 4 — Full Testing, Integration & E2E Hardening

- [ ] Complete backend unit coverage
- [ ] Complete frontend component tests
- [ ] Connector contract tests
- [ ] Database migration tests
- [ ] API integration suite
- [ ] Browser E2E with Playwright
- [ ] Full user journey E2E
- [ ] Production-like Docker E2E environment
- [ ] Failure/retry/stale-data scenarios
- [ ] Security checks
- [ ] Performance/load tests for critical endpoints
- [ ] CI quality gates for the complete stack
- [ ] Release checklist and reproducible production build

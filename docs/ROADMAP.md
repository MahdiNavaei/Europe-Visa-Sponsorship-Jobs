# Roadmap

The v1 project was intentionally delivered in four phases. All four phases are complete; future work can extend source coverage and product capabilities without weakening the strict evidence policy.

Release hardening is continuous. The current v1.1.4 closure requires final Windows
artifacts, hosted validation evidence, PR review/merge, main-branch validation, and
post-publication asset verification before it is called finished.

## Phase 1 — Core Data & Visa Intelligence ✅

- [x] Normalized job schema
- [x] PostgreSQL/SQLite persistence
- [x] Alembic migrations
- [x] Public ATS connectors
- [x] Deterministic tech-role classification
- [x] Visa/relocation signal detection
- [x] Hard work-right/citizenship/local-hiring restriction detection
- [x] Country rule registry
- [x] Sponsor registry evidence store
- [x] Explainable eligibility scoring
- [x] Ingestion run tracking
- [x] Stale job deactivation
- [x] REST API
- [x] Docker/PostgreSQL runtime
- [x] Scheduled GitHub ingestion workflow
- [x] CI/coverage gate

## Phase 2 — Candidate Matching & Intelligence ✅

- [x] Candidate profile
- [x] Role preferences and experience level
- [x] File-backed skill taxonomy
- [x] Skill aliases/synonyms
- [x] Deterministic CV/profile parsing where practical
- [x] Job-to-profile match score
- [x] Country preferences
- [x] Candidate-specific eligibility checks
- [x] Explainable ranking
- [x] Configurable ranking weights
- [x] Company friendliness intelligence
- [x] Frontend-friendly recommendation contracts
- [x] Server filters and pagination foundation
- [x] Deterministic fictional demo seed
- [x] Saved jobs and application state persistence/API

## Phase 3 — Professional UI/UX ✅

- [x] Next.js/TypeScript product frontend
- [x] Original design system and responsive app shell
- [x] English-default bilingual routing
- [x] Server-rendered Persian RTL
- [x] Inter + Vazirmatn typography
- [x] Light/dark/system theme
- [x] Premium landing page
- [x] Career Radar dashboard with data-derived KPIs
- [x] Server-filtered/sorted/paginated job discovery
- [x] Evidence-rich job detail
- [x] Candidate-specific match analysis on job detail
- [x] Company intelligence index and detail profiles
- [x] Six-step onboarding and persisted profile editing
- [x] Recommendation explanation view
- [x] Saved jobs/application tracker UI
- [x] Loading, empty, error, mobile and accessibility states
- [x] Vitest/React Testing Library coverage
- [x] Playwright critical user journeys

## Phase 4 — Release Hardening & Real E2E ✅

- [x] Fresh-clone production-like acceptance test
- [x] Chromium, Firefox and WebKit browser matrix
- [x] Responsive visual regression snapshots
- [x] Accessibility and keyboard audit
- [x] Performance/Lighthouse budgets
- [x] Python/frontend dependency security audits
- [x] Public-repository secret/artifact audit
- [x] PostgreSQL migration upgrade/downgrade/re-upgrade scenarios
- [x] Failure/retry and degraded-source tests
- [x] Production Docker Compose configuration
- [x] Secure CORS and baseline browser/API security headers
- [x] Real production ATS source catalog
- [x] Live health validation for every configured v1 ATS feed
- [x] Live ATS → PostgreSQL → eligibility → FastAPI E2E
- [x] Real production-browser validation of ingested jobs and application links
- [x] Immediate second-ingestion idempotency validation
- [x] Freshness validation for live postings
- [x] Daily persistent ingestion workflow with explicit configuration failure
- [x] README release screenshot and v1 documentation
- [x] Release checklist and public-repository audit

## After v1

The strongest next improvements are broader verified source coverage, additional European sponsor registries, richer country-rule maintenance, and deployment/operations for a public hosted instance. New sources should be added only when their public ATS endpoint can be health-checked and their normalized output passes the same live-data validation used by v1.

## Source coverage architecture

The persistent source registry, additive Wayback/Common Crawl/urlscan discovery, provider health lifecycle, bounded retries/cache, coverage API/UI, and scheduled workflows are documented in [`SOURCE_DISCOVERY.md`](SOURCE_DISCOVERY.md). The first measured live run is recorded in [`SOURCE_COVERAGE_REPORT.md`](SOURCE_COVERAGE_REPORT.md); its counts are deliberately limited to validated public feeds rather than unverified archive candidates.

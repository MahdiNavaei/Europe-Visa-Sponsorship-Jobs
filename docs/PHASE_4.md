# Phase 4 — Release Hardening & Full-System Validation

Phase 4 turns the Phase 1–3 product into a release candidate that can be published and deployed with evidence that the full stack works outside a developer workstation.

The release philosophy is simple: **green unit tests are necessary, but they are not sufficient**. A release must also survive real PostgreSQL migrations, deterministic installs, multiple browser engines, production-like containers, dependency audits, accessibility checks, performance budgets, degraded upstream sources, and a fresh-clone acceptance test.

## Release gates

### 1. Python compatibility and regression suite

CI runs the backend on Python 3.11 and 3.12 and requires:

- bytecode compilation
- Ruff
- mypy
- SQLite Alembic upgrade/downgrade smoke test
- full pytest suite with coverage >= 85%
- backend Docker image build

### 2. PostgreSQL migration compatibility

A dedicated PostgreSQL 16 job validates behavior that SQLite can hide:

1. upgrade a fresh database to `head`
2. seed deterministic demo data
3. downgrade one revision and re-upgrade
4. downgrade to `base`
5. upgrade to `head` again
6. seed demo data again
7. start the live FastAPI service against PostgreSQL
8. smoke-test health, stats, and jobs endpoints

This gate found and fixed a real PostgreSQL incompatibility in Alembic's default 32-character revision table because the Phase 2 revision identifier is longer than 32 characters. The migration environment now prepares a 128-character version column on PostgreSQL.

### 3. Deterministic frontend installation

Frontend CI uses `npm ci`, not `npm install`. The package lock is required to match the manifest exactly. This gate found and repaired an out-of-sync lockfile that older CI had silently tolerated.

### 4. Browser matrix and responsive visual validation

Playwright runs critical flows in:

- Chromium
- Firefox
- WebKit

Canonical visual snapshots are generated with reduced motion and disabled animations so screenshots represent settled UI rather than an intermediate animation frame.

The snapshot set includes:

- English desktop landing page
- Persian RTL desktop landing page
- populated Career Radar dashboard
- English mobile landing page
- mobile Career Radar dashboard

### 5. Accessibility and keyboard checks

Automated browser checks enforce:

- correct `lang` and `dir`
- exactly one main landmark and one H1 on audited pages
- accessible names for links and buttons
- labels for form controls
- image alt attributes
- no duplicate IDs
- no heading-level jumps
- no horizontal overflow on phone viewport
- keyboard-visible skip-to-content navigation
- reduced-motion support

### 6. Security and public-repository safety

Release CI performs:

- `pip-audit`
- `npm audit --audit-level=high`
- tracked-file public-repository audit
- secret-pattern checks
- local database/artifact checks
- accidental `.env` checks
- oversized tracked-file checks
- local absolute-path checks

The FastAPI service also uses explicit CORS origins/methods/headers, disables credentialed CORS, exposes only the pagination header required by the browser client, and adds baseline defensive response headers.

The Next.js application disables its framework identification header and adds browser security headers including `nosniff`, frame denial, referrer policy, permissions policy, COOP, and production HSTS.

### 7. Degraded upstream-source behavior

A failing ATS source must not prevent healthy sources in the same ingestion batch from being processed. The ingestion command therefore:

- records/prints the failed source
- continues processing remaining sources
- returns a failed batch result at the end so monitoring still detects the problem
- preserves previously active jobs when a refresh source fails

### 8. Performance budgets

Lighthouse CI audits both `/en` and `/fa` production builds with release thresholds for:

- performance
- accessibility
- best practices
- SEO
- first contentful paint
- largest contentful paint
- cumulative layout shift
- total blocking time

Reports are retained as CI artifacts.

### 9. Production-like deployment stack

`docker-compose.production.yml` builds and runs:

- PostgreSQL 16
- FastAPI backend
- standalone Next.js frontend

All services use health checks. The frontend runs as a non-root user in its production container.

### 10. Fresh-clone acceptance test

The final acceptance job starts from a clean GitHub checkout and:

1. builds the complete production-like Docker stack
2. waits for API and web health checks
3. seeds deterministic demo data inside the API container
4. verifies API health and stats
5. verifies English and Persian web routes
6. tears the stack down and removes its volume

This is the final automated release gate.

## Remaining product limitation

Visa and sponsorship results are deterministic, evidence-based signals. They are not legal advice and are not a guarantee that an employer will sponsor a particular applicant. Employer policy and immigration rules can change after data is collected.

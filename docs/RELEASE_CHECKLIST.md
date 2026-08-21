# Release Checklist

This checklist is intentionally evidence-driven. Items are checked only after the corresponding GitHub Actions release gate has passed on the final Phase 4 head.

## Code quality

- [ ] Python 3.11 compile, Ruff, mypy, tests, coverage and Docker build pass
- [ ] Python 3.12 compile, Ruff, mypy, tests, coverage and Docker build pass
- [ ] Backend coverage remains at or above 85%
- [ ] Frontend deterministic `npm ci`, lint, unit tests and production build pass

## Data and migrations

- [ ] SQLite migration upgrade/downgrade passes
- [ ] PostgreSQL 16 migration full round trip passes
- [ ] Demo seed is idempotent after database recreation
- [ ] Live FastAPI smoke tests pass against PostgreSQL

## Browser and UX

- [ ] Chromium critical E2E flows pass
- [ ] Firefox critical E2E flows pass
- [ ] WebKit critical E2E flows pass
- [ ] English desktop visual snapshot generated
- [ ] Persian RTL desktop visual snapshot generated
- [ ] Populated dashboard visual snapshot generated
- [ ] Mobile landing and dashboard snapshots generated
- [ ] Accessibility/keyboard semantic audit passes
- [ ] Phone viewport overflow audit passes

## Security and supply chain

- [ ] `pip-audit` has no known vulnerable installed dependencies
- [ ] `npm audit --audit-level=high` passes
- [ ] Public-repository tracked-file/secret audit passes
- [ ] API CORS is explicit and pagination headers are browser-visible
- [ ] Backend and frontend defensive response headers are enabled
- [ ] CI uses read-only repository contents permission

## Resilience

- [ ] One failed ATS source does not stop healthy sources in the same batch
- [ ] A failed source refresh does not deactivate previously valid jobs
- [ ] Batch still exits unsuccessfully when one or more sources fail

## Performance

- [ ] Lighthouse English page budgets pass
- [ ] Lighthouse Persian page budgets pass
- [ ] Performance, accessibility, best-practices and SEO thresholds pass
- [ ] Core paint/layout/blocking budgets pass

## Deployment and acceptance

- [ ] Production-like PostgreSQL + API + web Compose stack builds
- [ ] All production-like services become healthy
- [ ] Demo data seeds successfully inside the API container
- [ ] API health/stats endpoint checks pass
- [ ] English web route responds
- [ ] Persian web route responds
- [ ] Fresh-clone acceptance stack tears down cleanly

## Documentation and publication

- [ ] Final UI screenshots are committed under `docs/assets/`
- [ ] README includes product screenshots and production startup instructions
- [ ] Phase 4 documentation records final validation results
- [ ] Roadmap marks all four phases complete
- [ ] PR #4 description matches actual validation results
- [ ] Final Phase 4 PR is merged only after all required gates are green

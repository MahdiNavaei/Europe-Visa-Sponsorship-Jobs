# Release checklist

This operational checklist is intentionally evidence-driven. Check an item only after
the corresponding validation has passed on the release candidate SHA.

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
- [ ] Release notes and README claims match the validated release candidate
- [ ] Release PR is merged only after all required gates are green

## Windows desktop distribution

- [ ] Setup EXE builds with the release version
- [ ] Setup, portable ZIP, and SHA256SUMS are uploaded before smoke validation
- [ ] SHA256SUMS matches both release files
- [ ] Silent clean install succeeds into a fresh directory
- [ ] Installed smoke test passes without host Python or Node on PATH
- [ ] Installed runtime validates migrations, API health/version, jobs API, and frontend response
- [ ] Installed runtime terminates backend and Node child processes cleanly
- [ ] Portable ZIP extracts cleanly and passes the same no-host-runtime smoke test
- [ ] User data remains under `%LOCALAPPDATA%\\CareerRadar` across upgrades
- [ ] Windows signing mode is recorded in workflow output and release notes; if `SIGNED`, both executables have valid Authenticode signatures, and if `UNSIGNED`, both signing secrets are absent
- [ ] A partially configured signing-secret pair fails closed; signing failures are never masked as unsigned
- [ ] The release tag targets the final validated main commit
- [ ] GitHub Release attaches the exact verified Setup, Portable, and checksum files
- [ ] Release assets are downloaded from GitHub and hashes are re-verified

# Source coverage report

Run date: 2026-08-22 (Asia/Tehran)
Branch: `feat/scalable-source-discovery`
Base/final working-tree commit: `555173a3c3d9ee0807c482ba8a19917207445f7f` (implementation is currently uncommitted)

This report records observed results, not a claim of Europe-wide completeness. All counts below came from the live SQLite acceptance database `build/source-discovery-live.sqlite`, using public ATS responses and the repository's strict eligibility engine.

## Observed run

| Metric | Observed value |
| --- | ---: |
| Static source seeds bootstrapped | 15 |
| Candidate boards returned by bounded recent runs | 3 |
| Candidate boards returned by a Common Crawl page | 563 Greenhouse; 1,722 Ashby |
| Multi-provider Common Crawl breadth probe (2 pages/provider) | 7,715 candidates |
| Live-verified sources | 8 |
| Healthy sources | 7 |
| Valid-but-empty sources | 1 |
| Boards with current raw jobs | 7 |
| Verified providers | Greenhouse, Ashby |
| Raw postings fetched | 646 |
| Active technical jobs | 75 |
| European technical jobs | 50 |
| AI/data/ML-family jobs | 21 |
| AI/data/ML-family jobs in Europe | 16 |
| Eligible | 13 |
| Unknown | 62 |
| Rejected | 0 |
| Posted in last 24 hours | 2 |
| Posted in last 7 days | 26 |
| Duplicate rows | 0 (provider/source/external-id uniqueness) |
| Inactive/stale jobs | 0 in this fresh database |
| Current failing/blocked sources | 0 |
| Persisted HTTP failure breakdown | 20 × HTTP 404 validation failures; 8 prior ingestion-category failures |

The eight verified boards were Greenhouse Atolls, HelloFresh, and N26 plus Ashby 0g, 0x, 10xteam, 1bios, and 1mind. Seven had current raw jobs; 0x was valid-but-empty. The Greenhouse boards contributed 497 raw/67 technical jobs in the earlier Greenhouse-only snapshot; after the complete acceptance refresh the database contains 646 raw/75 active technical jobs, including 8 Ashby technical jobs and the retained Greenhouse rows. A repeat ingestion returned HTTP 304 for the unchanged Atolls snapshot and retained its previous jobs. Successful ingestion runtimes were 2.30s, 3.93s, and 2.44s on the repeat Greenhouse run. A simulated/observed failed writer attempt on SQLite initially showed `database is locked`; the CLI now serializes SQLite ingestion while retaining bounded parallel ingestion for PostgreSQL.

## Discovery evidence

The first manual recent run returned three candidates, live-validated all three in 2.60s, and recorded no source failures. The subsequent Wayback recent run returned the same three deduplicated candidates and live-validated all three, but the archive index request timed out during the 136.48s run; this is recorded on the discovery run as an index error, not as a healthy board. A live Common Crawl page returned 563 Greenhouse candidates and 1,722 Ashby candidates. A broader two-page-per-provider breadth probe returned 7,715 candidates: Greenhouse 1,307, Lever 44, Ashby 2,820, Workable 3,017, Personio 0, Teamtailor 1, Recruitee 0, SmartRecruiters 526, and Workday 0. That breadth probe was candidate discovery evidence, not verified coverage. The subsequent 5,000-board live-validation attempt exceeded the 30-minute acceptance window under the configured timeout/retry policy; the later collection endpoint also timed out before a complete second pass. It is therefore recorded as incomplete rather than reported as zero valid boards. A bounded 20-board Greenhouse validation exercise produced 0 verified and 20 HTTP 404 failures. A direct Ashby probe validated 30 sampled candidates; the application persisted and ingested five Ashby boards in 30.92s. Full-mode Wayback/Common Crawl discovery is additive and bounded; it must not be interpreted as verified coverage until each candidate passes a live provider response check.

A later fresh full-mode run on 2026-08-22 used all nine provider boundaries, two Common Crawl pages per provider, a five-second timeout, one retry, and concurrency 32 against a new SQLite database. It discovered 4,381 unique candidates, validated 12 live boards, recorded 4,369 failed validations, and completed in 843.17s (14m 3.17s). Candidate totals were Greenhouse 1,318, Lever 44, Ashby 1, Workable 3,017, Teamtailor 1, and Personio/Recruitee/SmartRecruiters/Workday 0. The 12 verified boards were Greenhouse (11) and Ashby (1); Lever, Workable, and Teamtailor produced candidates but no verified boards in this run. The exact persisted failure breakdown was Greenhouse: 913 HTTP 404, 369 timeout, and 25 network failures; Lever: 44 timeouts; Workable: 3,017 timeouts; Teamtailor: 1 timeout. No HTTP 403, 429, or 5xx responses occurred in this run. Wayback index failures for Recruitee and SmartRecruiters were recorded on the run rather than counted as source failures. This run is the authoritative current mass-validation evidence; it remains below the 5,000 verified-board target because the public indexes returned mostly stale/dead or timeout-bound candidates.

Provider breakdown for the persisted registry after the exercises: Greenhouse 34 candidate records (3 healthy/verified, 20 degraded 404s, 11 unverified seeds), Lever 0, Ashby 6 candidate records (5 healthy/verified, 1 valid-but-empty), Workable 0, Personio 0, Teamtailor 0, Recruitee 0, SmartRecruiters 0, Workday 0, Other 0. Current jobs: Greenhouse 67 active technical rows and Ashby 8 active technical rows. Lever produced 44 candidates in its Common Crawl page, but a 30-candidate live sample had 0 valid and 30 HTTP 404 results.

The architecture can process thousands of candidates with provider/ingestion concurrency limits and registry deduplication. This run did not claim 5,000 verified boards because the available public index response was not sufficiently fast or stable to complete that volume during the acceptance window. The system reports the measured count rather than padding it with unvalidated archive URLs.

## Local SQLite scale smoke

`scripts/source_scale_smoke.py` generated a deterministic local fixture of 10,000 persisted sources and 40,000 active jobs using the production schema (no external company dataset). On this Windows workstation it measured:

| Operation | Runtime |
| --- | ---: |
| Insert fixture | 3.811s |
| Coverage query | 0.360s |
| Source health lookup (100 rows) | 0.003s |
| Active-job count | 0.002s |

An earlier 5,000-source/20,000-job run completed in 2.433s insert and 0.228s coverage-query time. These fixtures validate local registry/query scale, not live-board verification. PostgreSQL parallel ingestion remains the production path for larger live refreshes.

The same 10,000-source/40,000-job fixture was loaded into PostgreSQL 16 after the full migration chain. It measured 14.175s insert, 0.379s coverage, 0.005s source-health lookup, and 0.012s active-job count. PostgreSQL `EXPLAIN (ANALYZE, BUFFERS)` used the `ix_jobs_active` bitmap index for active-job counts (14.052ms) and the source registry ordering index for the verified-source page (0.139ms).

## Regression evidence

- Backend: 66 tests, Python 3.11 and 3.12, 85.03% coverage; compile, Ruff, and mypy pass.
- Frontend: 4 Vitest tests, ESLint, production build, and deterministic `npm ci`/production Docker web build pass.
- Browser: 24/24 deterministic critical flows pass across Chromium (installed Chrome channel), Firefox, and WebKit—8 per engine—including coverage diagnostics, unknown counts, onboarding, pagination, job detail, recommendations, and Persian RTL. Accessibility/responsive checks also pass 12/12 across the three engines. A separate gated live acceptance test also passed 1/1 against the production Next server and live FastAPI database, including a real employer apply URL.
- Migrations: SQLite and PostgreSQL 16 upgrade, downgrade-one, re-upgrade, and downgrade-base round trips pass through revision `0006_source_query_indexes`.
- Backend Docker image: built successfully. Production Compose was built and started successfully on an isolated explicit bridge network; Postgres 16 became healthy, the API returned health 200 and coverage 200, and the container registry bootstrap persisted all 15 seeds. The host's default Compose network allocation remains exhausted, so the acceptance run used an explicit temporary subnet without deleting existing networks.
- Windows: source launcher tests pass; PyInstaller 6.22.2 completed under Python 3.12. Inno Setup 6.7.3 compiled the installer and 7-Zip 26.02 created/tested the portable archive. Silent installed-runtime and portable-runtime smoke tests both passed with host Python/Node removed from `PATH`; each persisted one smoke job while serving the bundled API and production Next standalone frontend.
- Security: `pip-audit --skip-editable` and `npm audit --audit-level=high` both report no known vulnerabilities. The local project itself is skipped by pip-audit because it is an editable distribution, as expected.
- Lighthouse: an isolated Lighthouse 12.8.2 audit generated `build/lighthouse-en.json` against the production Next page. The measured category scores were performance 0.99, accessibility 0.95, best practices 0.96, and SEO 1.00. The CLI still exited nonzero only during Chrome-launcher temporary-directory cleanup (`EPERM`), so the score artifact is available but the command is not fully green. The initial `npx lighthouse` path also hit npm `ECOMPROMISED`.

## Evidence policy

Eligibility is not inferred from a board's existence, job title, location, or a generic “visa” keyword. Positive, negative, and missing sponsorship evidence are preserved; missing evidence remains `unknown`. European location filtering is applied during normalization and the existing country rules/evidence engine remains the final gate.

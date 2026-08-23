# Source coverage report

Run date: 2026-08-23 (Asia/Tehran)
Branch: `feat/scalable-source-discovery`
Base: current `origin/main` (`380d18a3415e19b7243d938c0d01bb9e8c2009fe`)

This report records measured public-service results. It does not claim that an
archive candidate is a live board until the provider endpoint has responded
successfully.

## Implementation status

The scalable discovery implementation is committed in the working branch and
merged with current main. The branch preserves the PR #6 real-user ranking/UI
changes and the release-hardening/runtime migration from current main.

The registry now persists:

- candidate lifecycle: `discovered`, `pending_validation`, `verified`,
  `invalid`, `transient_failure`, `blocked`, and `retry_later`;
- last check, failure type, validation attempts, and `retry_after`;
- discovery-run candidate counts before/after filtering, cache skips, and
  provider/category failure breakdowns;
- verified and invalid candidates so future runs validate only new, due,
  transient, or stale sources.

Full-mode discovery follows the reference control design: Wayback CDX first,
Common Crawl fallback/additive discovery, paginated recent urlscan discovery,
provider-specific slug filters, seed union, previous-registry union, cheap
provider probes, and bounded validation batches.

## Controlled live runs

All runs below used the persisted SQLite registry at
`build/prompt1-live.sqlite`. The database is a local evidence artifact and is
not committed.

| Provider | Harvest records | Accepted after shape filter | Unique candidates | Verified | 404 | 403/blocked | Timeout | Network | Cache skips |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Greenhouse (paginated urlscan) | 1,100 | 1,096 | 117 | 107 | 10 | 0 | 0 | 0 | 0 |
| Lever (paginated urlscan) | 157 | 156 | 84 | 49 | 3 | 0 | 0 | 32 | 0 |
| Ashby (paginated urlscan) | 100 | 96 | 66 | 0 | 0 | 66 | 0 | 0 | 0 |
| Workable (public control board) | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |

Percentages among attempted candidates:

- Greenhouse: 91.45% verified, 8.55% HTTP 404.
- Lever: 58.33% verified, 38.10% network failure, 3.57% HTTP 404.
- Ashby: 100% blocked by the current Cloudflare edge for this client.
- Workable: 100% verified in the one independently controlled public board.

The previous persisted Ashby live run also recorded five real successful boards
(`0x`, `0g`, `10xteam`, `1bios`, `1mind`) with HTTP 200 responses and jobs. The
new run could not repeat them because the Ashby edge began returning HTTP 403
for both API and hosted-page requests from this client. This is recorded as a
provider limitation, not as verified current Ashby coverage.

## Why the old 4,381-board run yielded 12

The earlier full-mode Common Crawl run remains useful diagnostic evidence:

| Provider | Candidates | Verified | Failure distribution |
| --- | ---: | ---: | --- |
| Greenhouse | 1,318 | 11 | 913 HTTP 404 (69.27%), 369 timeout (27.99%), 25 network (1.90%) |
| Lever | 44 | 0 | 44 timeout (100%) |
| Ashby | 1 | 1 | — |
| Workable | 3,017 | 0 | 3,017 validation timeouts/exceptions (100%) |
| Teamtailor | 1 | 0 | 1 timeout (100%) |
| Total | 4,381 | 12 | 4,369 failed validations (including stale 404s and transient failures) |

The causes are now separated:

- Greenhouse’s high 404 rate is stale archived URL paths, not a Greenhouse
  endpoint failure. The new urlscan sample verifies 107 boards with the same
  canonical API.
- Lever’s old zero-result run was dominated by Common Crawl candidates and
  long GET/retry behavior. The corrected canonical endpoint and cheap probe
  produce 49 live boards in the new sample; the remaining network failures are
  transient and retryable.
- Workable was probed against the wrong `/api/v3/accounts/.../jobs` route in
  the old implementation. The public widget route
  `/api/v1/widget/accounts/{slug}` now validates; Hugging Face returned HTTP
  200 with seven jobs.
- Ashby’s API endpoint is currently Cloudflare-blocked from this client. The
  validator and ingestion connector fall back to the server-rendered hosted
  board’s `window.__appData` when that page is reachable; it returned 47 and
  136 jobs for independent direct probes before the edge began challenging the
  client.
- Teamtailor’s tenant-domain index produced 45 candidates, but its network
  requests exceeded the bounded resolution/timeout window. Those candidates
  remain `pending_validation`, not invalid.

Wayback failed at the connection layer in this environment, and Common Crawl
failed with connection errors. The reference project was run independently as
a control; its legacy HTTP Wayback URL was also refused. urlscan remained
reachable and its cursor pagination was added so the control was not limited to
its first 100 results per domain.

## Incremental and negative-cache evidence

After the Greenhouse run, a repeat urlscan run harvested the same 1,100 records,
selected zero validation attempts, and reported `skipped_cached_count=117`.
Verified sources carry a seven-day health deadline; permanent-looking 404s
carry a long retry deadline; transient/network failures carry a short retry
deadline. An interrupted Teamtailor batch left its 45 sources in
`pending_validation` and its discovery run unfinished, ready for a later
bounded retry.

## Expanded product evidence

The verified registry contained 157 sources at the time of the sample
ingestion. A bounded SQLite product run successfully ingested 29 Greenhouse
sources before the local serial-writer limit was reached:

| Metric | Observed value |
| --- | ---: |
| Verified sources in registry | 157 |
| Sources with ingested jobs | 20 |
| Successful raw postings fetched across ingestion runs | 5,485 |
| Active technical jobs | 876 |
| European technical jobs | 82 |
| AI/ML-family jobs | 78 |
| Eligible | 0 |
| Unknown | 871 |
| Rejected | 5 |
| Posted in last 24 hours | 128 |
| Posted in last 7 days | 276 |

The zero eligible count reflects that this isolated evidence database did not
include a matching sponsor-evidence dataset; unknown and rejected counts are
still exposed rather than silently treated as eligible.

## Support policy

Greenhouse and Lever are live-proven in the current run. Workable is proven by
the controlled public board and is now supported through its public widget
endpoint. Ashby has a working hosted-page fallback and historical HTTP-200
evidence, but current Cloudflare blocking prevents claiming fresh broad Ashby
coverage. Personio, Teamtailor, Recruitee, SmartRecruiters, and Workday remain
experimental until a live source is validated and ingested.

The final completion audit still requires the full backend/frontend/browser,
PostgreSQL/SQLite, security, Lighthouse, Docker, Windows, and clean-PR gates
to run against the final committed branch. No release tag or published release
was retargeted or published during this Prompt 1 work.

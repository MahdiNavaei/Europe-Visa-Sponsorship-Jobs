# Source coverage report

Run date: 2026-08-24 (Asia/Tehran)
Branch: `fix/product-truth-continuous-data`
Base: `ac2683f5650f6e68840a41a3771b9444c2f71918` (`v1.1.3`)

This document contains historical control measurements followed by the current
continuation evidence. Historical sections are retained for traceability and are
not current release claims; the dated continuation section is the current evidence.

This report records measured public-service results. It does not claim that an
archive candidate is a live board until the provider endpoint has responded
successfully.

## Implementation status

The scalable discovery implementation and the current product-truth continuation
are committed on the branch above. The branch preserves the earlier real-user
ranking/UI changes and release-hardening/runtime migration from current main.

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

The full PR #9 audit passed on the pushed implementation: backend tests on
Python 3.11/3.12, frontend/browser, PostgreSQL integration, live ingestion E2E,
security, Lighthouse, Docker/acceptance, and Windows packaging. The release
publish job was skipped. No release tag or published release was retargeted or
published during this Prompt 1 work.

## v1.1 launch-registry evidence — 2026-08-23

The v1.1 launch registry was rebuilt separately from the historical control
above. Candidate slugs came from the MIT-licensed Freehire source catalog and
were stored only as unverified inputs with their catalog provenance. Career
Radar then queried each candidate's own public ATS endpoint; only a current
successful validation can enter the release snapshot.

| Metric | Observed value |
| --- | ---: |
| Current live-verified, enabled boards | 653 |
| Greenhouse live-verified boards | 460 |
| Source snapshot validation threshold | 500 |
| Snapshot result | pass (653 boards) |
| European technical jobs after resumable ingestion | 654 / 1,000 required |
| European AI/data/ML jobs after resumable ingestion | 118 / 100 required |

This passes the source-breadth gate, but it is not a release declaration.
The AI/data/ML usefulness gate has passed, but the European technical-role
gate remains short by 346 roles. The Windows package, remote merge, CI, tag,
and published release remain gated on that completion.

## Latest local recovery measurement — 2026-08-23

The interrupted resumable-ingestion database was recovered by copying the
SQLite database and its rollback journal before opening the copy. SQLite
reported `integrity_check = ok`. The recovered database initially contained
4,182 active jobs. After live-ingesting the provenance-preserving European
candidate set and backfilling only explicit country/city information already
present in stored locations, the current coverage API reports:

| Metric | Current local value |
| --- | ---: |
| Live-verified enabled boards | 771 |
| Active technical jobs | 4,974 |
| European technical jobs | 1,041 |
| European AI/data/ML jobs | 169 |
| Eligible | 28 |
| Unknown | 4,909 |
| Rejected | 37 |

The packaged snapshot was regenerated from this registry and validates at 771
verified boards. These are current local evidence values, not a release claim:
frontend, Windows, cross-browser, hosted-CI, and publication gates remain
separate requirements.

## Current product-truth continuation evidence — 2026-08-24

The current branch is `fix/product-truth-continuous-data`, based on
`ac2683f5650f6e68840a41a3771b9444c2f71918` (`v1.1.3`). The following bounded live
run used the current `config/source-registry.snapshot.json`, not historical report
values:

| Provider | Boards sampled | Successful | Failed | Raw/normalized jobs | Technical | Nontechnical | Completeness |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Greenhouse | 20 | 20 | 0 | 152 / 152 | 34 | 118 | complete; provider total exposed on all 20 |
| Lever | 20 | 20 | 0 | 2,112 / 2,112 | 780 | 1,332 | complete public collection; provider total not exposed |
| Personio | 10 | 10 | 0 | 94 / 94 | 10 | 84 | complete published XML surface; provider total not exposed |
| Teamtailor | 10 | 10 | 0 | 0 / 0 | 0 | 0 | partial public HTML surface; no completeness claim |

The configured 15-board live smoke also passed with 1,860 fetched jobs. This is a
sample and does not establish that every board in the 771-source snapshot is healthy
at this instant. Teamtailor public sources remain explicitly partial.

The deterministic role corpus contains 36 labeled titles (24 technical, 12 hard
negatives) and currently measures precision 1.0000 and recall 1.0000. The live
recommendation benchmark used the 1,860-job sample and four personas; measured P@3,
P@5, and P@10 were 1.0000 for AI/ML, Backend, Data, and DevOps/SRE under the
role-similarity relevance definition. These are bounded audit measurements, not a
claim that a human relevance panel has been completed.

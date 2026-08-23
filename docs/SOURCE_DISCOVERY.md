# Source discovery and coverage

The source catalog is a database registry, not a checked-in list. `config/sources.json` is a bootstrap input and remains useful for explicit manual overrides; discovered boards are persisted in `sources`, with every validation recorded in `source_health_events` and every index pass recorded in `discovery_runs`.

## Licensed candidate catalogs

`scripts/build_freehire_candidate_catalog.py` may convert the MIT-licensed
[Freehire](https://github.com/strelov1/freehire) source catalog into a local,
unverified discovery input. It records the catalog URL and license in each
candidate's metadata. The catalog is never copied into a release artifact and
does not constitute source verification: each board must pass Career Radar's
own current public-ATS validation before it is enabled, ingested, or included
in a source-registry snapshot.

For a European usefulness catch-up, the same converter can accept current city
board files from the CC BY 4.0 [Lynceus jobs repository](https://github.com/trylynceus/jobs)
via `--location-board`. That input is only a geographic prioritization hint;
the candidate still needs a Freehire board identifier and an independent live
ATS validation. Its URL and license are recorded in source metadata whenever
the hint is used.

## Discovery contract

`evj-ingest sources discover` performs an additive union of:

- manual seeds;
- Wayback CDX URLs (`recent` or full archive mode);
- Common Crawl CDX pages (full mode);
- urlscan public search (recent mode); and
- previously verified registry entries.

Recent urlscan results are cursor-paginated with a bounded page count. Full
mode uses Wayback as the primary archive and retains Common Crawl as an
additive/fallback index; index failures never get counted as dead boards.

Unless `--provider` is supplied, the run considers every provider boundary in
the registry: Greenhouse, Lever, Ashby, Workable, Personio, Teamtailor,
Recruitee, SmartRecruiters, and Workday. Provider-scoped runs remain available
for bounded tests and operational recovery.

Archive and index URLs are candidates only. A candidate becomes enabled only after its provider-specific public response is validated. The database key is `(provider, board_identifier)`, so an archived job URL cannot create duplicate boards. A failed refresh never closes or deletes jobs: active jobs are closed only after a successful provider snapshot, while conditional 304 responses preserve the prior snapshot. Cheap `HEAD` probes are used where providers support them; Workable and Ashby use provider-specific GET/hosted-page fallbacks when their public edges reject `HEAD` or the API edge.

Use `evj-ingest sources discover --full-content` (or the matching
`sources validate` flag) for a deliberate volume-measurement pass. It fetches
the public payload rather than the normal cheap probe, persists the observed
job count, and makes `jobs --registry --only-uningested --largest-first`
meaningful for a bounded launch catch-up. It is opt-in because it is more
expensive for source providers.

Common Crawl page results are retained when a later page token fails, and Wayback/index latency is recorded separately from source health. In the 2026-08-23 control, paginated urlscan returned 1,100 Greenhouse records and 117 unique candidates, 157 Lever records and 84 unique candidates, and 100 Ashby records and 66 unique candidates. Wayback and Common Crawl were unavailable at the connection layer in the local network; these index failures are explicit run errors, not source failures.

## Provider boundary

Greenhouse, Lever, Ashby, Workable, Personio, Recruitee, and SmartRecruiters have normalization paths. Teamtailor requires an API token for its JSON:API; public JSON-LD is accepted only when present. Workday is intentionally tenant-specific: its `wday/cxs/{tenant}/{site}/jobs` endpoint and POST query must be supplied by the candidate metadata. The system records unsupported or unavailable public feeds as health events instead of inventing sponsorship evidence.

## Health and retry policy

Discovery and connectors use bounded concurrency, request timeouts, retryable 429/5xx/network failures, Retry-After support, User-Agent identification, and ETag/Last-Modified cache validators. A Common Crawl collection endpoint is resolved once per discovery run and reused across providers. Validation results are checkpointed in configurable batches (`DISCOVERY_CHECKPOINT_SIZE`, default 100), so a long scan persists partial health evidence instead of holding one unbounded transaction. Common Crawl and urlscan page breadth are configurable; bounded CI/live exercises can use fewer pages while scheduled full discovery uses their defaults.

Each source has a durable validation state: `discovered`, `pending_validation`,
`verified`, `invalid`, `transient_failure`, `blocked`, or `retry_later`. The
registry records `last_checked_at`, failure type, validation attempts, and
`retry_after`. Permanent-looking 404s receive a long negative-cache deadline;
network, timeout, and rate-limit failures are retried sooner; verified sources
are rechecked only after their health deadline. This prevents repeated probes
of permanent archive noise while preserving new and transient candidates.

Operational health labels remain `unverified`, `healthy`, `empty`, `degraded`,
`failing`, or `blocked` for compatibility with the existing API/UI. Three
consecutive ingestion failures disable a source for normal registry ingestion;
the validation lifecycle remains visible separately. Static manual overrides
remain auditable and are never silently replaced by an archive result.

## Runbook

```powershell
$env:PYTHONPATH = "src"
evj-ingest sources bootstrap --config config/sources.json
evj-ingest sources discover --mode recent
evj-ingest jobs --registry
evj-ingest sources health --json
evj-ingest sources retry-failed
```

For a deterministic offline run, use a mocked `httpx.AsyncClient` around `discover_and_validate` and the fixtures in `tests/`. For live operation, use PostgreSQL and keep `DISCOVERY_CONCURRENCY`, `DISCOVERY_TIMEOUT_SECONDS`, and `INGESTION_CONCURRENCY` bounded. SQLite intentionally serializes ingestion writers for Windows/local safety.

The API exposes `GET /api/v1/coverage` and `GET /api/v1/sources/health`; the web client exposes the same accounting at `/{locale}/coverage`.

Job identity remains `(provider, source_slug, external_id)`. A second, cross-source signal canonicalizes apply URLs by removing tracking parameters and normalizing host/path; exact matches for the same normalized company are marked with `duplicate_of_job_id` but are retained rather than blindly merged. Distinct postings with merely similar titles or locations are not deduplicated.

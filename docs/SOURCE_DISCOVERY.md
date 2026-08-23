# Source discovery and coverage

The source catalog is a database registry, not a checked-in list. `config/sources.json` is a bootstrap input and remains useful for explicit manual overrides; discovered boards are persisted in `sources`, with every validation recorded in `source_health_events` and every index pass recorded in `discovery_runs`.

## Discovery contract

`evj-ingest sources discover` performs an additive union of:

- manual seeds;
- Wayback CDX URLs (`recent` or full archive mode);
- Common Crawl CDX pages (full mode);
- urlscan public search (recent mode); and
- previously verified registry entries.

Unless `--provider` is supplied, the run considers every provider boundary in
the registry: Greenhouse, Lever, Ashby, Workable, Personio, Teamtailor,
Recruitee, SmartRecruiters, and Workday. Provider-scoped runs remain available
for bounded tests and operational recovery.

Archive and index URLs are candidates only. A candidate becomes enabled only after its provider-specific public response is validated. The database key is `(provider, board_identifier)`, so an archived job URL cannot create duplicate boards. A failed refresh never closes or deletes jobs: active jobs are closed only after a successful provider snapshot, while conditional 304 responses preserve the prior snapshot.

Common Crawl page results are retained when a later page token fails, and Wayback/index latency is recorded separately from source health. In the 2026-08-22 live exercise, Common Crawl returned 563 Greenhouse candidates, while a bounded 20-board validation sample returned twenty current HTTP 404 responses; none were promoted. Wayback's recent query timed out in the local network after returning the already-known three-board set.

## Provider boundary

Greenhouse, Lever, Ashby, Workable, Personio, Recruitee, and SmartRecruiters have normalization paths. Teamtailor requires an API token for its JSON:API; public JSON-LD is accepted only when present. Workday is intentionally tenant-specific: its `wday/cxs/{tenant}/{site}/jobs` endpoint and POST query must be supplied by the candidate metadata. The system records unsupported or unavailable public feeds as health events instead of inventing sponsorship evidence.

## Health and retry policy

Discovery and connectors use bounded concurrency, request timeouts, retryable 429/5xx/network failures, Retry-After support, User-Agent identification, and ETag/Last-Modified cache validators. A Common Crawl collection endpoint is resolved once per discovery run and reused across providers. Validation results are checkpointed in configurable batches (`DISCOVERY_CHECKPOINT_SIZE`, default 100), so a long scan persists partial health evidence instead of holding one unbounded transaction. Common Crawl page breadth is configurable with `DISCOVERY_COMMON_CRAWL_MAX_PAGES`; bounded CI/live exercises can use fewer pages while scheduled full discovery uses the default 20. Sources transition through `unverified`, `healthy`, `empty`, `degraded`, `failing`, or `blocked`. Three consecutive failures disable a source for normal registry ingestion; `sources retry-failed` retries it explicitly. Static manual overrides remain auditable and are never silently replaced by an archive result.

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

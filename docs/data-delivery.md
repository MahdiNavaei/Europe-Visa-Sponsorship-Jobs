# Continuous catalog data delivery

Career Radar has two data boundaries:

- The global market catalog contains source health, normalized vacancies, job-level
  evidence, and company registry signals. It is generated centrally and published as
  a versioned, gzip-compressed data-only snapshot on the `market-data` branch.
- Candidate profiles, saved jobs, application status, notes, and preferences remain in
  the user's local database. Catalog synchronization is additive/update-oriented and
  does not replace those tables.

The default published job dataset is deliberately narrower than the raw source
registry. Publication and desktop import both enforce the same canonical market
policy from `europe_visa_jobs.utils.market`: only technical vacancies in a supported
European country, or remote vacancies explicitly limited to Europe, are admitted.
This is defense in depth; the web UI is not the market-policy boundary.

Market-scope behavior is fail closed:

- a country-specific supported European location is included;
- a multi-location vacancy is included when at least one supported European location
  is explicit, even if non-European alternatives are also listed;
- `Remote — Europe` is included;
- global/worldwide remote, generic remote, EMEA, unknown location, US-only,
  Canada-only, and other non-European vacancies are excluded;
- an unknown location is never inferred to be European.

Raw source-health metadata remains available so failures and coverage are observable,
but out-of-market and nontechnical vacancies are not serialized as default market jobs.

Each publication includes `latest.json` with a schema version, dataset version,
generation time, source-registry version, job-dataset version, compressed payload name,
byte count, and SHA-256. The Windows client checks this manifest in the background. It
rejects non-HTTPS/non-allowlisted endpoints, unsafe payload paths, oversized payloads,
schema mismatches, and hash failures. Files are staged and atomically replaced; the
database import runs in one transaction so a failed update leaves the prior catalog
usable offline.

The current provider contract is explicit: a connector may report complete or partial
enumeration. Only complete fetches may deactivate unseen jobs. Teamtailor's public HTML
fallback is intentionally partial; authenticated JSON:API mode follows its `links.next`
pagination. Provider limitations remain visible in source health and coverage rather
than being presented as a complete market census.

| Provider | Current enumeration contract |
| --- | --- |
| Greenhouse | Paginated public board API; requests continue until a page has fewer than 100 rows |
| Lever | Public postings JSON feed; provider returns the board collection in one response |
| Ashby | Public posting API is complete when available; hosted HTML fallback is partial |
| Workable | Public account widget feed; completeness follows provider response contract |
| Personio | XML position feed; complete for the published XML surface |
| Teamtailor | Authenticated JSON:API follows `links.next`; public HTML JSON-LD is partial |
| Recruitee | Public offers feed is explicitly partial because pagination is not proven |
| SmartRecruiters | Offset pagination follows `totalFound` or short-page exhaustion |
| Workday | Tenant POST contract is explicitly partial until tenant pagination metadata is supplied |

Scheduled discovery and source health use `SOURCE_STATE_DATABASE_URL` when configured.
Without that secret they restore, update, sanitize, and republish a durable SQLite
checkpoint on the `market-data` branch; runner-local state alone is never treated as
authoritative. Recurring ingestion bootstraps the verified registry snapshot and loads
`data/sponsors.csv.gz` before evaluating jobs.

The source-discovery workflow publishes its latest verified registry to
`market-data/source-registry.latest.json`. Recurring ingestion consumes that publication
before falling back to the checked-in bootstrap snapshot, so a newly verified board
can enter the central job dataset and then reach existing desktop installations
without a software reinstall.

Central job ingestion runs hourly with a bounded batch of 150. Healthy boards become
due 18 hours after their last successful ingestion. When new and previously-ingested
boards are both waiting, at least 75% of each batch (113 slots) is reserved for the
oldest due refreshes and the remaining slots advance first-ingestion coverage; unused
capacity flows to the other partition. Retryable degraded/failing boards re-enter only
after their backoff deadline. Ordering is deterministic by oldest ingestion/discovery
time and provider identity.

The checked-in production snapshot currently contains 771 verified boards. The
reserved recurring capacity is therefore 18 × 113 = 2,034 board slots per 18-hour
window, and draining all 771 simultaneously due boards takes at most seven hourly
batches. The configured bound is consequently approximately 25 hours from one
successful fetch to the next under normal healthy-run assumptions. The workflow has a
capacity assertion so registry growth cannot silently make this statement false.

The publication branch is rewritten as a single orphan snapshot under the shared
`market-data-publication` concurrency lock. The catalog retains at most 14 compressed
payload versions, while unreachable workflow history cannot grow without bound.

The desktop status record also exposes the last successful sync, next scheduled sync,
successful/failed source counts, degraded providers, and added/changed/removed job
counts. A provider failure is represented as partial/degraded state while cached data
remains available.
If central sync fails and the desktop imports its bundled catalog, status is explicitly
`stale_fallback`, includes the bundle generation time, and does not advance
`last_successful_sync`.

Catalog downloads use the application's `httpx` stack with separate connection/read
timeouts, bounded streaming, transient retries, Content-Length checks, SHA-256 and
gzip/schema validation, and a temporary staging directory. A versioned payload is
promoted first and `latest.json` is replaced last, only after validation and database
import succeed. A failed update therefore leaves the previous valid cache and local
candidate state intact.

The update regressions use the same already-ingested source across versions N and
N+1. They prove new eligible jobs and changed evidence reach an existing client while
candidate, Saved, Applied, and notes state survive. Separate complete/partial provider
cycles prove that authoritative removals propagate and partial omissions do not cause
false deactivation. The packaged Windows runtime also exercises two catalog versions
through one installed executable without reinstalling.

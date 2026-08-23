# Continuous catalog data delivery

Career Radar has two data boundaries:

- The global market catalog contains source health, normalized vacancies, job-level
  evidence, and company registry signals. It is generated centrally and published as
  a versioned, gzip-compressed data-only snapshot on the `market-data` branch.
- Candidate profiles, saved jobs, application status, notes, and preferences remain in
  the user's local database. Catalog synchronization is additive/update-oriented and
  does not replace those tables.

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

Scheduled discovery and source health require `SOURCE_STATE_DATABASE_URL`, a durable
database connection. A runner-local SQLite file or an Actions artifact is not treated
as authoritative state. Daily ingestion bootstraps the verified registry snapshot and
loads `data/sponsors.csv.gz` before evaluating jobs.

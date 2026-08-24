# Phase 1–2 Architecture

## Design goals

- First-party job data wherever possible
- Deterministic, auditable decisions
- No LLM dependency
- Provider-specific parsing isolated behind connectors
- Country immigration logic isolated from text signals
- Storage of evidence, not only final labels
- Truthful default: only evidence-backed eligible jobs are shown; unknown requires an explicit research filter

## Packages

```text
src/europe_visa_jobs/
├── api/            FastAPI application
├── connectors/     ATS-specific public feed adapters
├── discovery/      additive board discovery, validation, and source orchestration
├── db/             SQLAlchemy models, session, repository
├── eligibility/    country rules, sponsor evidence, signal detector, engine
├── intelligence/   skill ontology, job analysis, matching, ranking, company scoring
├── ingestion/      source loading, sponsor import, ingestion pipeline, CLI
├── utils/          text, country, remote-geography and role normalization
├── schemas.py      shared Pydantic domain models
└── settings.py     environment configuration
```

## Connector contract

Every connector receives a `SourceConfig` and returns `list[NormalizedJob]`.

Provider-specific fields are converted into the canonical model before eligibility logic is executed. No eligibility rule is allowed inside an ATS connector.

Supported Phase-1 feeds:

| ATS | Feed |
|---|---|
| Greenhouse | public Job Board API |
| Lever | public Postings API (global/EU) |
| Ashby | public Job Posting API |
| Workable | public account job feed |
| Personio | public careers XML feed |
| Recruitee | public offers feed |
| SmartRecruiters | public postings API |
| Teamtailor | token-backed JSON:API or public JSON-LD boundary |
| Workday | tenant-specific `wday/cxs` POST boundary |

## Ingestion flow

```text
Central verified source registry
   ↓ scheduled connector enumeration
NormalizedJob[] (every fetched row retained)
   ↓ technical/nontechnical classification
EligibilityEngine (JD evidence + country rule + registry evidence)
   ↓
Company/job upsert and evidence persistence
   ↓
Versioned gzip catalog publication
   ↓ atomic desktop import
Only a proven COMPLETE source fetch may deactivate unseen jobs
```

A failed source run does not deactivate existing jobs.

## Eligibility flow

Hard negatives are checked first.

```text
hard negative found? ──yes──> rejected
        │ no
        ↓
country rule exists? ──no──> unknown
        │ yes
        ↓
collect job signals + registry evidence
        ↓
formal sponsor registry required but unverified? ──yes──> unknown
        │ no
        ↓
strong job-level evidence? ──no──> unknown
        │ yes
        ↓
eligible
```

### Strong job-level evidence

One of:

- explicit visa/work-permit/immigration evidence, or
- verified sponsor record **plus** relocation/international-candidate evidence

This prevents the common mistake `company is a sponsor => every job is sponsored`.

## Persistence

Tables:

- `companies`
- `sponsor_records`
- `jobs`
- `job_evidence`
- `ingestion_runs`
- `sources`
- `discovery_runs`
- `source_health_events`
- `candidates`

Phase 2 adds persisted job intelligence fields (`required_skills`, `preferred_skills`, minimum
experience, and seniority) while retaining runtime analysis for legacy rows.

The unique job identity is:

```text
(provider, source_slug, external_id)
```

## API default safety

`GET /api/v1/jobs` defaults to active eligible records. Unknown and rejected records
remain excluded from normal browse but are available explicitly for research or audit.

`unknown` and `rejected` records remain available for audit/debugging when explicitly requested.

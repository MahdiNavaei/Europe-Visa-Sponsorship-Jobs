# Phase 1 Architecture

## Design goals

- First-party job data wherever possible
- Deterministic, auditable decisions
- No LLM dependency
- Provider-specific parsing isolated behind connectors
- Country immigration logic isolated from text signals
- Storage of evidence, not only final labels
- Safe default: unknown jobs are hidden

## Packages

```text
src/europe_visa_jobs/
├── api/            FastAPI application
├── connectors/     ATS-specific public feed adapters
├── db/             SQLAlchemy models, session, repository
├── eligibility/    country rules, sponsor evidence, signal detector, engine
├── ingestion/      source loading, sponsor import, ingestion pipeline, CLI
├── utils/          text, country and role normalization
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

## Ingestion flow

```text
SourceConfig
   ↓
ATS connector
   ↓
NormalizedJob[]
   ↓
Tech role filter
   ↓
EligibilityEngine
   ↓
Company/job upsert
   ↓
Evidence persistence
   ↓
Deactivate source jobs not seen in current successful run
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

The unique job identity is:

```text
(provider, source_slug, external_id)
```

## API default safety

`GET /api/v1/jobs` defaults to `status=eligible`.

`unknown` and `rejected` records remain available for audit/debugging when explicitly requested.

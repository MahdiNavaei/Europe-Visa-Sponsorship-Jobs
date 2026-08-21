# Europe Visa Sponsorship Jobs

> Find European tech jobs where visa sponsorship and relocation are realistically possible for non-EU candidates.

**Europe Visa Sponsorship Jobs** is an open-source, evidence-based job intelligence engine for software engineers, data professionals, AI/ML engineers, and other technical candidates who need employer-supported immigration to Europe.

The project is intentionally **not another giant job aggregator**. Its default API only returns vacancies that pass a strict, explainable sponsorship gate. Jobs with missing or ambiguous evidence are marked `unknown` and hidden from the default results.

## Why this exists

International candidates waste enormous amounts of time on vacancies that look global but later reveal restrictions such as:

- `must already have the right to work`
- `no visa sponsorship`
- `EU/EEA candidates only`
- `must currently reside in the EU`

This project treats those sentences as first-class data, not footnotes.

## Phase 1 status

**Phase 1 — Core Platform & Data Intelligence Engine: complete.**

Implemented:

- Normalized job schema
- PostgreSQL/SQLite persistence
- Alembic migration
- Public ATS connectors for:
  - Greenhouse
  - Lever (global and EU instances)
  - Ashby
  - Workable
  - Personio
- Deterministic tech-role classifier
- Strict visa/relocation signal detector
- Hard restriction detector
- Country-rule registry for:
  - Netherlands
  - Germany
  - United Kingdom
  - Ireland
  - Sweden
  - Finland
  - Denmark
- Verified sponsor-registry evidence store
- Explainable eligibility score
- Ingestion run tracking
- Stale-job deactivation
- REST API with FastAPI
- Docker/PostgreSQL environment
- CI tests and coverage gate
- Optional scheduled ingestion workflow

## No LLM. No paid AI API.

Phase 1 has **zero LLM dependency** and requires **no OpenAI, Anthropic, Gemini, or other paid AI API**.

Decisions are made with:

- public ATS data
- verified sponsor evidence
- deterministic rules
- transparent regex/context signals
- country-specific immigration route metadata

The output is inspectable and reproducible.

## Strict eligibility policy

A vacancy can have one of three internal states:

| Status | Meaning | Shown by default? |
|---|---|---|
| `eligible` | Strong evidence supports sponsorship and no hard restriction was found | Yes |
| `rejected` | A hard restriction was found | No |
| `unknown` | Evidence is incomplete or ambiguous | No |

Countries with a formal sponsor register (currently the Netherlands and UK in Phase 1) require verified company-registry evidence in strict mode.

A sponsor licence alone is never treated as proof that every vacancy is sponsored. The job itself must also contain strong sponsorship/relocation/international-candidate evidence.

## Architecture

```text
Public company ATS feeds
        │
        ├── Greenhouse
        ├── Lever
        ├── Ashby
        ├── Workable
        └── Personio
        │
        ▼
Job normalization
        │
        ├── country inference
        ├── tech-role classification
        └── canonical source identity
        │
        ▼
Eligibility engine
        │
        ├── hard negative restrictions
        ├── explicit visa/work-permit signals
        ├── relocation signals
        ├── international-candidate signals
        ├── verified sponsor registry
        └── country rules
        │
        ▼
PostgreSQL
        │
        ├── jobs
        ├── companies
        ├── sponsor records
        ├── evidence
        └── ingestion runs
        │
        ▼
FastAPI
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for details.

## Quick start

### Local SQLite

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e ".[dev]"

alembic upgrade head
uvicorn europe_visa_jobs.api.app:app --reload
```

Open:

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

### Docker + PostgreSQL

```bash
docker compose up --build
```

API: `http://localhost:8000`

## Configure job sources

Copy the example:

```bash
cp config/sources.example.json config/sources.json
```

Example source:

```json
{
  "provider": "lever",
  "company_name": "Example EU Company",
  "slug": "example",
  "default_country": "Germany",
  "region": "eu"
}
```

Run ingestion:

```bash
evj-ingest jobs --sources config/sources.json
```

Only supported technical job families are stored during Phase 1.

## Import verified sponsor evidence

Sponsor records are deliberately separate from jobs. Import a normalized CSV:

```csv
company_name,country,registry_name,source_url
Example Company,Netherlands,IND Public Register Recognised Sponsors - Labour,https://ind.nl/...
```

Then:

```bash
evj-ingest sponsors --file data/sponsors.csv
```

See [`data/sponsors.example.csv`](data/sponsors.example.csv).

## API

### Eligible jobs

```http
GET /api/v1/jobs
```

Default behavior: `status=eligible`.

Filters:

```http
GET /api/v1/jobs?country=Germany
GET /api/v1/jobs?country=Netherlands&job_family=ai_ml
GET /api/v1/jobs?status=unknown
```

### Job evidence

```http
GET /api/v1/jobs/{id}
```

Returns the evidence used to make the decision.

### Companies

```http
GET /api/v1/companies
```

### Countries

```http
GET /api/v1/countries
```

### Stats

```http
GET /api/v1/stats
```

## Tests

```bash
pytest --cov=europe_visa_jobs --cov-report=term-missing --cov-fail-under=85
```

CI also runs compilation, Ruff, and the coverage gate on pushes and pull requests.

## Current job families

- Software Engineering
- Backend
- Frontend
- Full Stack
- Mobile
- AI / Machine Learning
- Data Science
- Data Engineering
- MLOps
- DevOps / Cloud / SRE / Platform
- QA Automation

## Accuracy philosophy

The project prefers **false negatives over false positives**.

If we cannot prove enough, the job becomes `unknown` instead of being shown as sponsorship-ready. A user should not lose an hour because the system guessed.

This project is not legal or immigration advice. Visa rules and employer policies change; evidence is stored so decisions can be audited and refreshed.

## Roadmap

The project is delivered in four phases:

1. **Core Platform & Data Intelligence Engine** ✅
2. **Candidate Matching & Intelligence**
3. **Professional UI/UX**
4. **Full Testing, Integration & E2E Hardening**

See [`docs/ROADMAP.md`](docs/ROADMAP.md).

## License

MIT

---

Keywords: Europe visa sponsorship jobs, EU visa sponsorship jobs, relocation jobs Europe, non-EU developer jobs, European tech jobs with visa sponsorship, Blue Card jobs, Highly Skilled Migrant jobs, Skilled Worker sponsorship jobs.

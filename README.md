# Europe Visa Sponsorship Jobs — Career Radar

> Evidence-based European tech job intelligence for non-EU candidates who need visa sponsorship or relocation support.

**v1.0.0** turns public company ATS feeds into a strict, explainable career radar: it collects current technical vacancies, rejects hard work-authorization restrictions, evaluates sponsorship evidence, ranks opportunities against a candidate profile, and explains why a job is—or is not—a realistic target.

It uses **no LLM and no paid AI API at runtime**. Decisions are deterministic, inspectable, reproducible, and backed by stored evidence.

![Career Radar dashboard](docs/assets/dashboard-en.png)

## Windows — one-click install

For most Windows users, no developer setup is needed.

1. Open **GitHub Releases**.
2. Download `CareerRadar-Setup-v1.0.0.exe`.
3. Install and launch **Career Radar**.

The Windows package bundles the Python backend runtime, the production Next.js server, a private Node runtime, database migrations, and project configuration. Users do **not** need to install Python, Node.js, npm packages, pip packages, Docker, or PostgreSQL.

On first launch it creates a local SQLite database, fetches live ATS jobs, starts the API and web app on loopback-only ports, and opens the browser automatically. A portable ZIP and SHA-256 checksums are published with the installer as well.

See [`docs/WINDOWS.md`](docs/WINDOWS.md) for local-data paths, refresh behavior, portable usage, and the current unsigned-binary/SmartScreen note.

## Why this project exists

International candidates routinely lose time on vacancies that look global but later contain restrictions such as:

- `must already have the right to work`
- `no visa sponsorship`
- `EU/EEA candidates only`
- `must currently reside in the EU`

Career Radar treats those sentences as first-class eligibility data rather than footnotes.

A company appearing in a sponsor register is **not** enough to approve every vacancy. Job-level evidence still matters, and hard negative restrictions always win.

## What v1.0 includes

- Public ATS connectors: Greenhouse, Lever, Ashby, Workable, Personio
- Explicit, audited production source catalog in `config/sources.json`
- Daily source refresh workflow
- Technical-role classification
- Country inference and normalized job identity
- Visa, relocation, international-candidate, and hard-restriction detection
- Country-specific immigration rule registry
- Verified sponsor-registry evidence store
- Strict `eligible / rejected / unknown` eligibility states
- Candidate profiles and deterministic skill ontology
- Explainable candidate/job matching and ranking
- Company visa-friendliness intelligence
- Saved jobs and application-stage tracking
- FastAPI + PostgreSQL backend
- Bilingual Next.js application (`/en`, `/fa`) with true RTL Persian
- Light/dark themes and responsive desktop/mobile UI
- Docker production stack
- Dependency-free Windows installer + portable package
- PostgreSQL migration round-trip validation
- Chromium, Firefox, and WebKit E2E coverage
- Accessibility, security, dependency, and public-repository audits
- Lighthouse performance budgets
- Live public-ATS-to-browser E2E validation

## Strict eligibility policy

| Status | Meaning | Default UI/API |
|---|---|---:|
| `eligible` | Strong sponsorship/relocation evidence and no hard restriction | Shown |
| `rejected` | A hard restriction was found | Hidden |
| `unknown` | Evidence is incomplete or ambiguous | Hidden |

The system intentionally prefers false negatives over false positives. If it cannot prove enough, the job stays `unknown` instead of wasting a candidate's time.

## Verified live-data path

Phase 4 contains a networked E2E gate with **no mocked job data path**:

```text
Public ATS
   ↓
Connector + normalization
   ↓
Eligibility engine
   ↓
PostgreSQL
   ↓
FastAPI
   ↓
Production Next.js
   ↓
Real browser → Job detail → Apply URL
```

Release validation on **2026-08-21 UTC** verified all 10 configured production feeds live and fetched **1,373 raw current positions** across them.

A smaller independent Greenhouse + Ashby smoke set was then ingested twice into fresh PostgreSQL:

- 96 active technical jobs
- 79 postings inside the 60-day freshness window
- 40 strict-mode eligible jobs
- identical source/external-id key set after immediate re-ingestion
- real FastAPI response verified
- real production Next.js UI verified in Chromium
- job detail and outbound application link verified

The smoke run included current postings from N26 and Clera dated August 19–21, 2026.

Live upstream services can change, so CI also validates the configured source catalog rather than assuming ATS slugs remain valid forever.

## Daily refresh: what it guarantees

`.github/workflows/daily-ingest.yml` is scheduled for **03:17 UTC every day** and can also be dispatched manually.

It:

1. migrates the persistent database,
2. reads the audited `config/sources.json` catalog,
3. re-fetches current ATS vacancies,
4. upserts jobs deterministically,
5. deactivates jobs that disappeared from a successfully refreshed source,
6. re-runs eligibility analysis,
7. reports active, eligible, and newest-posting statistics.

A deployed instance must provide a persistent PostgreSQL connection through the repository secret `DATABASE_URL`. The workflow fails loudly if that configuration is missing.

**Daily refresh does not mean employers publish a new eligible vacancy every calendar day.** It means the configured feeds are checked every day, and newly published eligible jobs appear after the next successful refresh.

The Windows desktop runtime has its own local refresh cycle: first launch fetches live jobs, later launches refresh data when it is older than 24 hours, and users can trigger a refresh manually from the launcher.

## Current production source catalog

The tracked v1 catalog currently includes live-verified public feeds for:

- N26
- HelloFresh
- Atolls
- Canonical
- GetYourGuide
- trivago
- Kalepa
- Coinbase
- PRISMA European Capacity Platform
- Clera

The catalog is deliberately explicit and auditable rather than an unrestricted crawler. Coverage can grow safely by adding verified ATS sources.

## Architecture

```text
ATS connectors
   │
   ├─ Greenhouse
   ├─ Lever
   ├─ Ashby
   ├─ Workable
   └─ Personio
   ↓
Normalization + role classification
   ↓
Visa / relocation / restriction evidence
   ↓
Country rules + sponsor evidence
   ↓
Strict eligibility engine
   ↓
PostgreSQL / local Windows SQLite
   ├─ jobs + evidence
   ├─ companies + sponsor records
   ├─ candidates
   ├─ application states
   └─ ingestion runs
   ↓
Candidate matching + ranking
   ↓
FastAPI
   ↓
Next.js Career Radar (EN / FA RTL)
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/PHASE_2.md`](docs/PHASE_2.md), [`docs/PHASE_3.md`](docs/PHASE_3.md), and [`docs/PHASE_4.md`](docs/PHASE_4.md).

## Developer quick start

### Backend with SQLite

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

alembic upgrade head
uvicorn europe_visa_jobs.api.app:app --reload
```

API: `http://localhost:8000`  
Swagger: `http://localhost:8000/docs`  
Health: `http://localhost:8000/health`

### Web application

```bash
cd apps/web
npm ci
npm run dev
```

English: `http://localhost:3000/en`  
Persian RTL: `http://localhost:3000/fa`

The web app defaults to `http://localhost:8000` for the API. Set `NEXT_PUBLIC_API_URL` when using another origin and configure `WEB_ORIGIN` on the backend.

### Production-like Docker stack

A production-style stack with PostgreSQL, FastAPI, and standalone Next.js is provided:

```bash
export POSTGRES_PASSWORD='choose-a-strong-password'
docker compose -f docker-compose.production.yml up -d --build
```

The production compose file intentionally has no default database password.

## Run real job ingestion

`config/sources.json` already contains the live-verified v1 source catalog.

```bash
evj-ingest jobs --sources config/sources.json
```

To maintain a custom deployment, edit that catalog or start from `config/sources.example.json` and validate the ATS slugs before relying on them.

## Demo data

For UI development without external network traffic:

```bash
python scripts/seed_demo.py
```

The demo dataset is deterministic and fictional; it never claims that a real employer sponsors a fictional vacancy.

## Candidate intelligence API

```http
POST /api/v1/candidates
GET  /api/v1/candidates/{candidate_id}
GET  /api/v1/recommendations/{candidate_id}
GET  /api/v1/recommendations/{candidate_id}/explain
```

Recommendations combine visa compatibility, skill coverage, experience/seniority, country preference, role similarity, and company evidence. Ranking weights live in [`config/ranking.yaml`](config/ranking.yaml), while skill aliases/categories live in [`data/skills.yaml`](data/skills.yaml).

## Job API

Default behavior returns eligible jobs only:

```http
GET /api/v1/jobs
GET /api/v1/jobs/{id}
GET /api/v1/jobs?country=Germany&category=ai_ml&limit=20&offset=0
```

Pagination exposes `X-Total-Count`. Job detail returns the evidence used by the eligibility engine.

## Verification

Backend:

```bash
pytest --cov=europe_visa_jobs --cov-report=term-missing --cov-fail-under=85
ruff check src tests scripts
mypy src scripts --ignore-missing-imports
```

Frontend:

```bash
cd apps/web
npm ci
npm run lint
npm test
npm run build
npx playwright test
```

Release CI additionally validates:

- Python 3.11 and 3.12
- SQLite and PostgreSQL Alembic round trips
- backend and frontend production builds
- Chromium / Firefox / WebKit critical flows
- live public ATS source health
- live ATS → PostgreSQL → API → production browser E2E
- Windows self-contained installer build and silent-install smoke test
- `pip-audit` and `npm audit --audit-level=high`
- secret/local-artifact/public-repository safety
- accessibility and responsive behavior
- Lighthouse budgets for English and Persian
- fresh-checkout production Docker acceptance

## Project status

All four v1 phases are implemented:

1. **Core Platform & Data Intelligence Engine** ✅
2. **Candidate Matching & Intelligence** ✅
3. **Professional bilingual UI/UX** ✅
4. **Full Testing, Integration & E2E Hardening** ✅

See [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Accuracy and legal boundary

Visa and sponsorship results are deterministic evidence signals, **not legal or immigration advice and not a sponsorship guarantee**. Employer policy and immigration rules can change after data is collected. Evidence is retained so decisions can be audited and refreshed.

## License

MIT

---

Keywords: Europe visa sponsorship jobs, EU visa sponsorship jobs, relocation jobs Europe, non-EU developer jobs, AI jobs Europe, data jobs Europe, Blue Card jobs, Highly Skilled Migrant jobs, Skilled Worker sponsorship jobs.

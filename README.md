# Career Radar — Europe Visa Sponsorship Jobs

> Evidence-based European tech job intelligence for non-EU candidates who need visa sponsorship or relocation support.

[![CI](https://github.com/MahdiNavaei/Europe-Visa-Sponsorship-Jobs/actions/workflows/ci.yml/badge.svg)](https://github.com/MahdiNavaei/Europe-Visa-Sponsorship-Jobs/actions/workflows/ci.yml)
[![License: PolyForm Noncommercial 1.0.0](https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![Windows](https://img.shields.io/badge/Windows-installer-0078D6.svg)](docs/WINDOWS.md)

**Career Radar v1.1.4** helps international candidates stop wasting applications on jobs that cannot realistically sponsor them.

It collects current technical vacancies from public employer ATS feeds, identifies hard work-authorization restrictions, evaluates sponsorship and relocation evidence, ranks jobs against a candidate profile, and explains the evidence behind every decision.

No LLM and no paid AI API are required at runtime. The core decision path is deterministic, inspectable, reproducible, and evidence-backed.

![Career Radar dashboard](docs/assets/dashboard-en.png)

## Why Career Radar exists

A job can look international and still contain a single sentence that makes it unusable for a non-EU candidate:

- `must already have the right to work`
- `no visa sponsorship`
- `EU/EEA candidates only`
- `must currently reside in the EU`

Traditional job search treats those lines as ordinary description text. Career Radar treats them as first-class eligibility evidence.

It also avoids a common false positive: **a company appearing on a sponsor register does not mean every vacancy at that company is sponsored.** Job-level evidence still matters, and explicit restrictions take priority over positive company-level signals.

## What it does

### Find realistic opportunities

- Connects to public Greenhouse, Lever, Ashby, Workable, and Personio job feeds
- Normalizes companies, countries, locations, roles, and stable job identities
- Detects sponsorship, relocation, international-candidate, and hard-restriction evidence
- Uses country-specific immigration rules and official sponsor-register evidence
- Tracks evidence instead of returning unexplained yes/no predictions

### Match jobs to a candidate

- Candidate profiles and deterministic skill ontology
- Visa compatibility and sponsorship evidence
- Skill coverage and role similarity
- Experience and seniority fit
- Country preferences
- Explainable ranking and recommendation scores

### Track the search

- Saved jobs
- Application stages
- Company visa-friendliness intelligence
- Bilingual English/Persian interface
- True RTL Persian layout
- Light/dark themes
- Responsive desktop/mobile UI

## Eligibility model

Career Radar uses three explicit evidence states:

| Status | Meaning |
|---|---|
| `eligible` | Sufficient positive sponsorship/relocation evidence and no overriding hard restriction |
| `rejected` | A hard work-authorization or sponsorship restriction was found |
| `unknown` | Available evidence is incomplete or ambiguous |

The system intentionally avoids turning uncertainty into a sponsorship claim. Evidence and reason codes are retained so decisions can be inspected and refreshed as employer policies change.

## Windows — one-click install

For most Windows users, no developer setup is needed.

1. Open **GitHub Releases**.
2. Download the setup file matching the current release, for example `CareerRadar-Setup-v1.1.4.exe`.
3. Install and launch **Career Radar**.

The Windows package includes the Python backend runtime, production Next.js server, private Node runtime, database migrations, and project configuration. Users do **not** need to install Python, Node.js, npm packages, pip packages, Docker, or PostgreSQL.

On first launch, Career Radar creates a local SQLite database, loads the packaged verified source-registry snapshot and sponsor evidence, synchronizes the current market catalog, starts the API and web application on loopback-only ports, and opens the browser automatically.

A portable ZIP and SHA-256 checksums are published with release assets.

Windows artifacts may be signed or unsigned depending on the configured release mode. The release notes state the actual mode for each release, and SHA-256 integrity artifacts remain mandatory regardless of signing mode. Unsigned builds may trigger a Windows SmartScreen unknown-publisher warning. See [`docs/WINDOWS.md`](docs/WINDOWS.md) and [`CODE_SIGNING_POLICY.md`](CODE_SIGNING_POLICY.md).

Desktop privacy behavior is documented in [`PRIVACY.md`](PRIVACY.md).

## Live data and daily refresh

Career Radar maintains a verified source registry rather than assuming every discovered ATS slug is valid forever.

The scheduled `.github/workflows/daily-ingest.yml` workflow runs daily and can also be triggered manually. It:

1. migrates the persistent database,
2. bootstraps the verified source registry and audited manual seeds,
3. fetches current ATS vacancies,
4. upserts jobs deterministically,
5. deactivates disappeared jobs only when provider enumeration is complete,
6. re-runs eligibility analysis,
7. publishes updated catalog state and refresh statistics.

When a hosted deployment provides `DATABASE_URL`, it can use persistent PostgreSQL. Without that secret, the workflow uses the project's sanitized branch-backed durable data path.

Daily refresh means configured sources are checked every day. It does **not** imply that employers publish a new eligible vacancy every calendar day.

### Verified release path

Release validation has exercised the complete production path with real public ATS data rather than mocked job records:

```text
Public ATS
   ↓
Connector + normalization
   ↓
Sponsorship / restriction evidence
   ↓
Country rules + sponsor evidence
   ↓
Eligibility engine
   ↓
PostgreSQL / local SQLite
   ↓
FastAPI
   ↓
Production Next.js
   ↓
Real browser → Job detail → Apply URL
```

The v1.1 release validation on 2026-08-21 UTC checked all 10 configured production feeds live and fetched **1,373 raw current positions**. An independent Greenhouse + Ashby smoke set was ingested twice into fresh PostgreSQL and verified through the API and production browser path, including real outbound application links.

Live upstream services change, so current source health is continuously revalidated rather than inferred from historical success.

## Source coverage

`config/sources.json` is a small auditable bootstrap seed set. Production registry operations use the persisted verified registry and generated source snapshot.

The bootstrap seeds currently include public feeds for:

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

A provider page, archive, or search result is only a discovery candidate. It becomes part of the verified catalog after its current provider endpoint or documented fallback passes validation.

Daily ingestion publishes a versioned compressed market catalog plus `latest.json` to the `market-data` branch. Existing clients can consume updated market data without reinstalling the desktop application. The packaged `config/source-registry.snapshot.json` is an offline fallback, not the continuously updated source universe.

## Architecture

```text
ATS connectors
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
Country rules + official sponsor evidence
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
Next.js Career Radar — EN / FA RTL
```

Global market data is separated from local candidate state. Catalog imports are hash-verified, staged, and transactional; profiles, saved jobs, application tracking, notes, and preferences are not replaced by market-data updates.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/data-delivery.md`](docs/data-delivery.md).

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

```bash
export POSTGRES_PASSWORD='choose-a-strong-password'
docker compose -f docker-compose.production.yml up -d --build
```

The production compose file intentionally has no default database password.

## Run real job ingestion

```bash
evj-ingest sources bootstrap --config config/sources.json --snapshot config/source-registry.snapshot.json
evj-ingest jobs --registry
```

For UI development without external network traffic:

```bash
python scripts/seed_demo.py
```

The demo dataset is deterministic and fictional; it never claims that a real employer sponsors a fictional vacancy.

## API examples

### Candidate intelligence

```http
POST /api/v1/candidates
GET  /api/v1/candidates/{candidate_id}
GET  /api/v1/recommendations/{candidate_id}
GET  /api/v1/recommendations/{candidate_id}/explain
```

Ranking weights live in [`config/ranking.yaml`](config/ranking.yaml), while skill aliases and categories live in [`data/skills.yaml`](data/skills.yaml).

### Jobs

```http
GET /api/v1/jobs
GET /api/v1/jobs/{id}
GET /api/v1/jobs?country=Germany&category=ai_ml&limit=20&offset=0
```

Job detail responses expose the evidence used by the eligibility engine.

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

Release CI additionally covers:

- Python 3.11 and 3.12
- SQLite and PostgreSQL Alembic round trips
- backend and frontend production builds
- Chromium, Firefox, and WebKit critical flows
- live public ATS source health
- live ATS → PostgreSQL → API → production-browser E2E
- Windows self-contained package and silent-install smoke tests
- `pip-audit` and `npm audit --audit-level=high`
- secret/local-artifact/public-repository safety checks
- accessibility and responsive behavior
- Lighthouse budgets for English and Persian
- fresh-checkout production Docker acceptance

## Project status

All four original v1 implementation phases are complete:

1. **Core Platform & Data Intelligence Engine** ✅
2. **Candidate Matching & Intelligence** ✅
3. **Professional bilingual UI/UX** ✅
4. **Full Testing, Integration & E2E Hardening** ✅

See [`docs/ROADMAP.md`](docs/ROADMAP.md) and [`CHANGELOG.md`](CHANGELOG.md).

## Accuracy, data, and legal boundary

Visa and sponsorship results are deterministic evidence signals, **not legal or immigration advice and not a sponsorship guarantee**. Employer policies, vacancies, and immigration rules can change after data is collected.

Third-party job descriptions, company content, and government-register data retain their original rights and terms. See [`DATA_LICENSES.md`](DATA_LICENSES.md).

## License and commercial use

Career Radar is **source-available** under the **PolyForm Noncommercial License 1.0.0** (`PolyForm-Noncommercial-1.0.0`). It is not presented as an OSI-approved open-source license.

In practical terms:

- personal, educational, research, hobby, and other noncommercial use is permitted under the license terms,
- modification and noncommercial redistribution are permitted under those terms,
- the required copyright/project notices must be preserved,
- **commercial use requires a separate written license** from the project owner.

See [`LICENSE`](LICENSE), [`NOTICE`](NOTICE), and [`COMMERCIAL_LICENSE.md`](COMMERCIAL_LICENSE.md).

Versions previously released under MIT retain the MIT permissions that accompanied those versions; the license change is not retroactive.

## Contributing

Issues, fixes, new ATS connectors, evidence rules, country coverage, tests, and documentation improvements are welcome.

Because the project supports dual licensing, contributors should read the contribution-licensing terms before submitting code: [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Support the project

If Career Radar saves you time or helps you find a realistic opportunity, the easiest ways to support it are to **star the repository, share it with other international candidates, report bad sponsorship signals, and contribute verified improvements**.

Organizations that want to support ongoing development, infrastructure, new country coverage, or public-data maintenance can discuss **project sponsorship or partnership** with the maintainer.

Commercial licensing and sponsorship are separate: sponsorship supports the project; commercial rights require a written commercial license.

## Maintainer

**Mahdi Navaei** — [GitHub](https://github.com/MahdiNavaei)

For commercial licensing, partnerships, or project sponsorship, use the contact information published on the maintainer's GitHub profile.

---

Keywords: Europe visa sponsorship jobs, EU visa sponsorship jobs, relocation jobs Europe, non-EU developer jobs, AI jobs Europe, data jobs Europe, Blue Card jobs, Highly Skilled Migrant jobs, Skilled Worker sponsorship jobs.

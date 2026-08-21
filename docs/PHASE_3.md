# Phase 3 — Professional UI/UX Product Experience

Phase 3 turns the deterministic Phase 1–2 intelligence backend into **Career Radar**, a bilingual product experience for discovering European technology roles where relocation and sponsorship evidence can be inspected instead of guessed.

The frontend never recalculates eligibility or recommendation scores. Visa eligibility, candidate matching, ranking, company signals, reasons, and warnings remain backend-owned.

## Product architecture

```text
Next.js App Router
  ├── /[locale]                         landing page
  ├── /[locale]/dashboard               evidence-led Career Radar overview
  ├── /[locale]/jobs                    server-filtered/sorted/paginated discovery
  ├── /[locale]/jobs/[id]               vacancy evidence + candidate-specific match
  ├── /[locale]/companies               company intelligence index
  ├── /[locale]/companies/[id]          company signal profile + active roles
  ├── /[locale]/applications            saved jobs + application pipeline
  ├── /[locale]/onboarding              six-step candidate profile wizard/editor
  ├── /[locale]/profile                 candidate profile + recommendation anatomy
  ├── /[locale]/settings                theme/language/trust controls
  └── /[locale]/recommendations/[candidateId]/explain
```

`src/lib/api/client.ts` is the typed browser/API boundary and TanStack Query owns remote state. Filters and pagination are executed by the FastAPI backend. Personalized job discovery uses recommendation scores; generic discovery clearly labels its score as visa evidence rather than pretending it is a candidate match.

## Design system

The visual system uses an ink/paper base, indigo product accent, mint for positive evidence, amber for uncertainty, and rose for hard warnings. Reusable primitives cover cards, buttons, badges, inputs, selects, skeletons, score bars, empty/error states, charts, job cards, navigation, and responsive layouts.

Motion is restrained to navigation, entrance, and hover feedback. Core navigation and controls use semantic markup, visible focus states, accessible labels, and keyboard-friendly Radix primitives.

## Internationalization and typography

English (`/en`) is the default experience. Persian (`/fa`) is rendered as RTL **from the initial server HTML** using locale-specific root layouts; it is not converted to RTL after hydration.

Inter and Vazirmatn are loaded as real web fonts with preconnect hints. Persian dates, numbers, percentages, countries, job-family labels, navigation, filters, onboarding, settings, profile, dashboard, company pages, tracking controls, and score UI are localized.

Raw vacancy descriptions, matched evidence snippets, and backend-generated evidence/reason text intentionally preserve source wording. Career Radar does not machine-translate evidence because changing wording could alter its meaning or imply a stronger sponsorship claim than the source supports.

## Candidate intelligence UX

A candidate can:

- create and later edit the same persisted profile;
- browse personalized recommendations with real match-score filtering;
- sort personalized results by match, recency, or visa evidence;
- inspect a candidate-specific match for one vacancy;
- see matched and missing skills, reasons, warnings, and score components;
- inspect company-level visa friendliness signals separately from job-level eligibility.

Dashboard metrics are derived from actual data: recent matches/jobs use posting time, high-confidence matches use the complete fetched recommendation set, and the target-country card derives from recommendation strength with profile preferences as fallback.

## Saved jobs and application tracking

Phase 3 exposes the Phase 2 tracking contract through `/applications` and job-detail controls. State is persisted per `(candidate, job)` and supports:

- saved / unsaved;
- not applied;
- applied;
- interview;
- offer;
- rejected;
- withdrawn.

Migration `0003_candidate_job_tracking` creates the persistence table. The tracking API supports list/get/upsert/delete operations and the UI invalidates the relevant TanStack Query caches after changes.

## Backend contracts added for the product UI

In addition to the Phase 2 endpoints, the hardened product uses:

```http
PUT /api/v1/candidates/{candidate_id}
GET /api/v1/companies/{company_id}
GET /api/v1/recommendations/{candidate_id}/jobs/{job_id}
GET /api/v1/candidates/{candidate_id}/job-states
GET /api/v1/candidates/{candidate_id}/jobs/{job_id}/state
PUT /api/v1/candidates/{candidate_id}/jobs/{job_id}/state
DELETE /api/v1/candidates/{candidate_id}/jobs/{job_id}/state
```

Job and recommendation lists return `X-Total-Count` and support server-side filtering, sorting, limit, and offset pagination.

## Verification

Frontend quality gates:

```bash
cd apps/web
npm install
npm run lint
npm test
npm run build
npm run test:e2e
```

Playwright covers real locale switching and RTL, theme persistence, the complete six-step onboarding submission, dashboard arrival, personalized server filters/sorting/pagination, candidate-specific job matching, company intelligence, and recommendation explanations. Application tracking has its own E2E coverage.

The repository CI additionally runs Python compilation, Ruff, mypy, migration upgrade/downgrade smoke tests, backend tests with the coverage gate, and Docker builds on Python 3.11 and 3.12.

## Trust boundary

All visa and company scores are deterministic evidence summaries. They are not immigration advice and do not guarantee that an employer will sponsor a particular candidate or vacancy. Users should verify the employer's current policy before applying.

# Real-user E2E audit

Audit date: 2026-08-22  
Branch: `audit/real-user-e2e`  
Base: latest `main` at `575e992` (`v1.0.1`)

## Executive result

The normal Windows/browser journey is usable after the fixes in this branch. A fresh candidate can complete onboarding, persist a profile, see recommendations, edit the profile, open a real job, save it, record an application status, close and reopen the browser, and see the state again. English and Persian routes render, including RTL application tracking and mobile-sized layouts.

The audit also found and fixed one release-blocking ranking defect: the matcher calculated role similarity but the ranking engine ignored it. Visa/country/skill scores could therefore place unrelated mobile or frontend roles above an AI/ML candidate's shortlist. Role similarity is now a weighted ranking signal and personalized recommendations require at least `0.5` role similarity. The all-market Jobs page still exposes eligible technical roles intentionally; the dashboard shortlist no longer does.

This is not a claim of Europe-wide source completeness. The active catalog contains 15 explicitly configured public boards, 14 of which ingested successfully in this run. Clera's Ashby board returned HTTP 403 and is recorded as a failed source. Broader Europe coverage remains follow-up work.

## Real-user journey

The journey used a real Chromium browser against a live FastAPI instance and a SQLite copy populated by the configured public ATS connectors. The browser was not given mocked API responses.

Profile used:

- Name: Alex Morgan
- Target roles: Machine Learning Engineer, AI Engineer, MLOps Engineer
- Skills: Python, Machine Learning, Deep Learning, PyTorch, SQL, Docker, Kubernetes, AWS, MLOps, LLM, RAG, LangChain, FastAPI
- Experience: senior, 8 years
- Countries: Germany, Netherlands
- Visa support: required
- Relocation: preferred
- Remote: no preference

Observed outcomes:

| Journey | Result |
| --- | --- |
| Landing → onboarding | Passed in English. |
| Six-step onboarding | POST returned 201; candidate id persisted in local storage and database. |
| Dashboard | 14 eligible monitored opportunities; top recommendations were role-compatible DevOps/MLOps and Data Science roles. No iOS, Android, or frontend role appeared in the shortlist. |
| Profile | Roles, visa need, countries, experience, seniority, relocation, remote preference, and skills were visible. |
| Edit profile | PUT returned 200 and the updated candidate was read back successfully. |
| Search | Live personalized counts: Machine Learning 1, AI 4, Data Scientist 1, LLM 0. |
| Detail/apply | Opened N26's real “Senior Site Reliability Engineer - Infrastructure” detail page; apply URL was present: `https://n26.com/en-eu/careers/positions/7796233?gh_jid=7796233`. |
| Tracking | Three real jobs saved and assigned Rejected, Interview, and Applied states. |
| Restart | Persistent browser reopened with candidate id 2 and all three application states intact. |
| Persian/RTL | `html[dir=rtl]` was `rtl`; Persian labels, dates, numbers, and tracker states rendered. |
| Responsive | Screenshots captured at 1920×1080, 1440×900, 1366×768, 1280×720, and 390×844. |

Evidence scripts and screenshots are intentionally ignored build artifacts under `build/real-user-audit/`; they are reproducible from this branch and include request/response capture.

## Defects found and fixed

### P0: unrelated recommendations

Cause: `CandidateMatcher` produced `role_similarity`, but `RankingEngine.score()` weighted only visa, skill, experience, country, and company. The result was a misleading shortlist for role-specific users.

Fix:

- Added `role_score: 0.25` to `config/ranking.yaml`.
- Added role similarity to the deterministic ranking calculation and explanation weights.
- Added related-family matching for AI/ML, Data Science, MLOps, and DevOps/Cloud at `0.75` similarity.
- Added a personalized API shortlist gate at role similarity `>= 0.5`.
- Narrowed AI/ML title patterns to avoid classifying generic “AI governance” roles as AI engineering.
- Expanded onboarding roles and skills to the exact AI/ML choices used in the audit.

Regression coverage: `tests/test_real_user_ranking.py` checks ten relevant and ten unrelated titles, precision at 3/5/10, and Data Science family equivalence. The full backend suite passed.

### P1: profile visibility and metric ambiguity

The profile view did not expose experience, seniority, relocation, or remote preference, even though those values affected matching. Those fields are now visible and translated in English and Persian.

The dashboard's global eligible count was previously labelled “Visa-ready opportunities,” which could be read as a candidate-specific guarantee. It now says “Eligible in monitored sources,” with “All monitored sources” as its detail. The confidence metric now says “High-confidence personal matches.”

## Live source audit

The expanded run fetched 1,560 raw postings, classified 325 as supported technical roles, stored all 325 as active, and reconciled every successful source's technical count with its stored active count.

| Source | Provider | Raw | Technical | Stored active | Eligible | Unknown | Result |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| N26 | Greenhouse | 76 | 25 | 25 | 13 | 12 | pass |
| HelloFresh | Greenhouse | 400 | 30 | 30 | 0 | 30 | pass |
| Atolls | Greenhouse | 21 | 12 | 12 | 0 | 12 | pass |
| Canonical | Greenhouse | 303 | 73 | 73 | 0 | 73 | pass |
| GetYourGuide | Greenhouse | 55 | 8 | 8 | 0 | 8 | pass |
| trivago | Greenhouse | 10 | 1 | 1 | 1 | 0 | pass |
| Kalepa | Greenhouse | 24 | 10 | 10 | 0 | 10 | pass |
| Coinbase | Greenhouse | 173 | 58 | 58 | 0 | 58 | pass |
| PRISMA European Capacity Platform | Greenhouse | 2 | 1 | 1 | 0 | 1 | pass |
| Wise | Greenhouse | 19 | 0 | 0 | 0 | 0 | pass; no supported technical titles |
| GitLab | Greenhouse | 204 | 43 | 43 | 0 | 43 | pass |
| Moonfare | Greenhouse | 16 | 2 | 2 | 0 | 2 | pass |
| Contentful | Greenhouse | 8 | 0 | 0 | 0 | 0 | pass; no supported technical titles |
| Elastic | Greenhouse | 249 | 62 | 62 | 0 | 62 | pass |
| Clera | Ashby | 0 | 0 | 0 | 0 | 0 | HTTP 403; failure retained and not deactivated |

The 14 eligible postings all had positive evidence codes in the audit database. There were no rejected technical postings in this snapshot; 311 remained unknown, so the UI correctly does not present them as sponsor-confirmed.

The active eligible sample was concentrated in N26 Germany (13) and trivago Germany (1). That concentration is a data result, not a Europe-wide sponsorship conclusion.

## AI/ML audit

The AI/ML audit uses a title-based deterministic keyword screen so that the denominator is inspectable rather than inflated by incidental description mentions.

- Active technical jobs scanned: 325
- AI/ML-title jobs: 51
- Eligible: 1
- Unknown: 50
- Rejected: 0
- Posted in the last 24 hours: 2
- Posted in the last 7 days: 10
- Recommended to Alex Morgan: 1 — `Data Scientist - AI Search & Ranking`

The recommendation system is deterministic and explainable; there is no opaque ML model in this release. The current product should describe this as AI/ML role classification and matching intelligence, not as a trained recommendation model.

## Source expansion and maintenance strategy

The active catalog is explicit in [`config/sources.json`](../config/sources.json). A source is eligible for addition only when:

1. its public board URL is verified;
2. the connector returns a successful response without credentials;
3. raw-to-technical classification is measurable;
4. normalized IDs are unique within the source;
5. active stored rows reconcile to the successful technical feed;
6. eligibility output preserves `eligible`, `unknown`, and `rejected` instead of guessing; and
7. a failure marks the ingestion run failed without deactivating the source's previous rows.

The supported public ATS patterns should guide future discovery:

- [Greenhouse Job Board API](https://developer.greenhouse.io/job-board.html): public board-token jobs endpoint, with `content=true` when descriptions are needed.
- [Lever Postings API](https://github.com/lever/postings-api): public published postings endpoint; board slugs must be verified before catalog addition.
- [Ashby public job posting API](https://developers.ashbyhq.com/docs/public-job-posting-api): board-name endpoint; availability can be blocked by a board's access policy, as seen with Clera.
- [Workable XML feed](https://help.workable.com/hc/en-us/articles/360000689917-How-to-use-the-Workable-API): public board feed where available; authenticated APIs are not assumed.
- [Personio XML feed](https://support.personio.de/hc/en-us/articles/360000680785-How-to-use-the-Personio-XML-feed): account-specific public feed; account slugs must be discovered and health-checked.

Recommended operation is a small source-catalog job that health-checks every configured feed, records raw/technical/duplicate/stored/status counts, alerts on failures or unexpected zero technical output, and opens a review item for verified new boards. This is safer and more maintainable than broad scraping or treating a single ATS as “Europe-wide.”

## Validation performed

- `py -3.11 -m pytest -q`: 50 passed.
- `npm run test`: 3 passed.
- `npm run lint`: passed.
- `npm run build`: passed; 19 routes generated.
- Live ingestion: 14 successful sources plus one recorded HTTP 403 failure.
- Live API health: `{"status":"ok","version":"1.0.1"}`.
- Real Chromium journey: onboarding, profile, edit, search, detail, apply URL, tracking, restart, RTL, and responsive evidence.
- Hosted PR #6 gates: acceptance, performance/Lighthouse, Windows packaging, PostgreSQL, live-ingestion E2E, security, Python 3.11/3.12, and web/Playwright all passed.
- Downloaded v1.0.1's hosted Windows artifact, installed it into an isolated directory, and launched `CareerRadar.exe` through the normal no-argument path. The packaged runtime created its SQLite database, started FastAPI, and reached the bundled Next server at `127.0.0.1:43128` before the isolated process was cleaned up.

Still required before claiming broad public coverage: review/merge the branch and expand verified European source coverage. The release gates above are green; source breadth remains a product limitation rather than a validation failure.

# Phase 2 — Candidate Intelligence & Matching Engine

Phase 2 turns the Phase 1 eligible-job catalog into personalized, deterministic recommendations. The backend answers which jobs are worth an individual candidate's time and records the reasons and warnings behind each score.

## Architecture

```text
Candidate profile
    │
    ├── canonical skill aliases
    ├── target role families
    ├── experience and seniority
    ├── country / location preferences
    └── visa, relocation, and remote preferences
    │
    ▼
Job intelligence extraction
    │  required/preferred skills, minimum experience, seniority
    ▼
CandidateMatcher
    │  visa, skills, experience, role, country, company signals
    ▼
RankingEngine
    │  configurable weighted score
    ▼
Recommendation API
```

The implementation is local and deterministic. It does not call an LLM, paid AI API, embedding service, or external repository at runtime.

## Candidate profile

`Candidate` stores:

- target roles
- canonical skills
- years of experience
- seniority
- preferred countries
- visa requirement
- relocation preference
- remote preference
- excluded locations

Candidate input can use aliases. For example, `python3`, `Torch`, `GenAI`, and `K8s` are stored as `Python`, `PyTorch`, `LLM`, and `Kubernetes`.

## Skill ontology

`SkillOntology` loads the reviewed taxonomy from [`data/skills.yaml`](../data/skills.yaml). Each definition has a canonical name, category, and aliases. Extraction uses case-insensitive, boundary-aware regular expressions and returns stable, de-duplicated output. A built-in fallback keeps installed packages safe if the repository data file is unavailable.

The ontology currently covers programming, machine learning, cloud, infrastructure, frontend/backend, databases, data, DevOps, and observability skills. Unknown candidate-entered skills are preserved as labels; only known ontology skills are extracted from job text.

Job descriptions recognize preferred-skill markers such as `nice to have`, `preferred`, `bonus`, `plus`, and `desirable`. Skills outside those passages are treated as required. Existing Phase 1 jobs without persisted intelligence fields are analyzed at match time, so the migration is backwards-compatible.

## Matching

The matcher calculates:

- required skill coverage
- preferred skill coverage
- a 70/30 skill score from required/preferred coverage
- seniority match
- minimum-experience match
- target-role similarity using the Phase 1 role classifier
- country and location preference match
- candidate-specific visa eligibility
- company friendliness from Phase 1 evidence

Hard restrictions remain warnings and never become positive sponsorship evidence. A candidate who requires a visa receives a full visa score only for a Phase 1 `eligible` job; `unknown` receives a low score and `rejected` receives zero.

## Ranking

The default ranking weights are stored in [`config/ranking.yaml`](../config/ranking.yaml) and loaded through `RankingConfig`/`load_ranking_config`. Applications can still inject `RankingConfig` directly for tests or tenant-specific policies:

| Component | Weight |
|---|---:|
| Visa eligibility | 35% |
| Skill match | 30% |
| Experience match | 15% |
| Country preference | 10% |
| Company intelligence | 10% |

Every weight is validated as non-negative and the total must equal 100%. The final score is normalized to 0–100. Recommendations are sorted by total score, then posting date, then stable job id.

## Company intelligence

The company score starts from a conservative baseline and uses persisted Phase 1 signals:

Positive signals include recognized sponsor evidence, relocation support, international-candidate language, applications from abroad, and explicit visa/work-permit support.

Negative signals include no sponsorship, existing-work-rights requirements, EU/EEA-only restrictions, local-only hiring, and citizenship restrictions.

The score is a signal summary, not a legal guarantee. Vacancy-level evidence remains separate and auditable.

## Frontend API contract

The versioned endpoints are the stable Phase 3 interface. Both `/api/v1/...` and the short paths in the Phase 2 brief are available:

```http
POST /api/v1/candidates
GET  /api/v1/candidates/{candidate_id}
GET  /api/v1/recommendations/{candidate_id}
GET  /api/v1/recommendations/{candidate_id}/explain
```

Recommendation responses remain lists for backward compatibility. Each recommendation includes a complete `job` payload, grouped `scores` (`overall`, `visa`, `skill`, `experience`, `country`, and `company`, all 0–100), skill coverage, matched/missing skills, `reasons`, and `warnings`. Recommendation filters are `country`, `role`, and `min_score`; `limit` and `offset` provide simple pagination, and `X-Total-Count` reports the filtered result count. `include_unknown=true` is opt-in for research and audit use. The jobs endpoint keeps `status`, `country`, and `job_family` and also accepts the UI aliases `visa_status` and `category`.

Example item:

```json
{
  "job": {"id": 42, "title": "Senior AI Engineer"},
  "scores": {"overall": 92, "visa": 100, "skill": 90, "experience": 88, "country": 100, "company": 75},
  "reasons": ["The job passed the strict sponsorship eligibility gate."],
  "warnings": ["Missing required skills: Kubernetes."]
}
```

## Evaluation

`tests/fixtures/` contains a representative senior ML candidate, three jobs, and an expected ranking. Regression tests verify alias normalization, ranking order, missing-skill warnings, excluded locations, API serialization, pagination/filter behavior, configuration loading, demo seeding, and persisted profile fields.

## Demo usage

Run `python scripts/seed_demo.py` after installing the project. It creates three fictional candidates and three fictional European jobs. Every demo description contains `DEMO SAMPLE DATA ONLY`; the dataset is not evidence about real employers, vacancies, or sponsorship status. The script is idempotent for candidates and upserts the sample jobs.

This layer is ready for Phase 3 to build onboarding, search, job detail, and explanation views without duplicating backend scoring logic.

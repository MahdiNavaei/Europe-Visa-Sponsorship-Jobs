# Changelog

## 1.2.1 — 2026-08-27

- Fix the recommendation-score scale bug that underweighted positive visa/sponsorship
  evidence by treating a normalized 0..1 component as if it were already 0..100.
- Revisit already-ingested ATS sources automatically with the fair recurring freshness
  scheduler so new/changed/removed jobs can reach existing desktop installations.
- Add Software Engineering and additional common engineering role choices, and improve
  broad-to-specific software role matching without weakening non-technical role guards.
- Expand the deterministic skill ontology and replace the flat onboarding skill picker
  with searchable, grouped, role-prioritized choices while preserving existing profiles.
- Add user-feedback regressions for score normalization, role taxonomy, ontology coverage,
  recurring freshness behavior, and installed-client state preservation.

## 1.2.0 — 2026-08-26

- Enforce the European technical-market scope in catalog publication and import so
  US-only and other out-of-scope vacancies do not enter the default product catalog.
- Harden streamed catalog delivery with retryable transport handling, size/SHA-256,
  gzip/schema validation, atomic promotion, and preservation of the previous good cache.
- Remove pathological per-row catalog reconciliation and reuse deterministic analysis
  state to make full and incremental desktop synchronization practical.
- Complete real-data user-flow validation across onboarding, recommendations, job
  evidence, real Apply URLs, saved/applied state, persistence, Companies, Coverage,
  Persian RTL, and the packaged Windows runtime.
- Fix Job Detail translation labels, Persian recommendation explanations, freshness
  terminology, and final browser/asset issues found by headed production E2E testing.
- Publish the cleaned public repository under PolyForm Noncommercial 1.0.0 with
  separate commercial licensing while preserving the MIT permissions of earlier
  MIT-distributed versions.

## 1.1.4 — 2026-08-25

- Make the default browse and recommendation contract eligible-only; unknown jobs are
  available only through an explicit research filter.
- Harden sponsorship classification against questions, negation, and multilingual
  work-authorization restrictions.
- Correct catalog publication/import lifecycle, partial-source handling, freshness,
  bounded decompression, and Windows catalog lookup.
- Protect candidate data with per-profile bearer secrets and add local export/delete
  controls without publishing candidate state in market snapshots.
- Reduce API/UI over-fetching, expose evidence freshness/completeness, and strengthen
  URL, metadata, container, browser, and workflow security boundaries.
- Expand regression, migration, frontend, and release validation for the corrected
  product contract.

## 1.1.3

- Added durable source discovery, catalog delivery, Windows synchronization, and
  evidence-oriented product-truth improvements.

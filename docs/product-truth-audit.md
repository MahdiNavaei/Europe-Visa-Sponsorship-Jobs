# Product-truth audit matrix

Audit baseline: `ac2683f5650f6e68840a41a3771b9444c2f71918` (v1.1.3), branch
`fix/product-truth-continuous-data`. This is an implementation-routing record; the
release tags are not modified.

| Priority | Type | Confirmed surface | Root cause | Required correction | Regression evidence |
| --- | --- | --- | --- | --- | --- |
| P0 | architectural defect | Desktop launcher | First launch performs live registry ingestion before opening the UI; installed registry is static | Open local UI after migration and seed; sync a versioned central catalog in the background | launcher timing and offline-start tests |
| P0 | architectural defect | Scheduled workflows and desktop | Discovery/health state is runner-local and desktop has no central data channel | Durable registry + SHA-256 integrity-checked manifest and compressed catalog import | two-run persistence, manifest, client sync tests |
| P0 | confirmed bug | `ingestion/pipeline.py` | All fetched rows are filtered by title before persistence and missing jobs are deactivated after any successful-looking fetch | Persist classification inventory; use explicit completeness and deactivate only on complete fetch | classification/accounting and partial-fetch tests |
| P0 | data-quality defect | Eligibility and API | Job sponsorship, company registry status, and final eligibility are represented as one decision path | Persist/render independent job signal, company status, and final status with evidence polarity | sponsorship semantics tests |
| P1 | confirmed bug | Connectors | Several production connectors make one request; Teamtailor public mode parses one page | Provider-specific pagination/exhaustion contracts and explicit complete/partial state | deterministic connector fixtures |
| P1 | confirmed bug | Recommendations | Recommendation query caps the catalog at 500 newest jobs | Full-catalog bounded query and ranking; null country must not imply Europe | >500 recall test and ranking benchmark |
| P1 | confirmed bug | Companies | Company API has fixed limit and company detail has fixed job limit | Search, offset pagination, all-job aggregates, conservative identity | API pagination/aggregate tests |
| P1 | architectural defect | Runtime state | Global catalog and candidate state share one mutable job lifecycle without an atomic external snapshot protocol | Versioned catalog metadata, atomic staged import, rollback, and v1.1.3 migration coverage | update N/N+1/N+2 simulation |
| P1 | workflow defect | `daily-ingest.yml` | Workflow points at uncompressed sponsor CSV while shipped input is `.csv.gz` | Validate compressed production input and bootstrap the verified snapshot into an empty DB | release-input and bootstrap tests |
| P2 | UX defect | Dashboard, coverage, jobs, evidence | Unknowns, sync state, evidence polarity, country scope, and score labels are incomplete or misleading | Localized truthful states and sync metrics | frontend unit/browser assertions |
| P2 | reliability defect | Source lifecycle | Three transient failures can disable a source from normal retry selection | Distinguish permanent invalid from retryable failures and schedule retry | source recovery tests |
| P2 | performance risk | Catalog scale | ORM recommendation/company paths are bounded by arbitrary caps and lack delivery/import metrics | Indexed server-side pagination and measured 5k/10k/30k fixtures | performance benchmark |
| P3 | documentation defect | README and coverage artifacts | Existing docs describe static/bootstrap behavior as current truth | Regenerate measured coverage and document provider limitations/privacy boundary | docs consistency check |

## Audit conclusions

The highest-risk defects are coupled: a durable source registry without a durable
publish/import channel cannot reach installed clients, and a larger feed without row
accounting or completeness semantics can silently remove legitimate jobs. The first
implementation slice therefore establishes the data contract and atomic local sync
before broadening connector behavior or UI counts.

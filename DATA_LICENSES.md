# Data sources, terms, and attribution

Career Radar's software is source-available under the repository's
PolyForm Noncommercial License 1.0.0. That software license does not relicense
third-party job postings, company pages, government registers, or other upstream
content included in generated datasets.

## Job-board data

Job records are factual extracts from public employer ATS endpoints configured in
`config/sources.json` or admitted by the verified source registry. Copyright in job
descriptions remains with the relevant employer or publisher. Consumers must follow
the source site's terms, robots policy, retention requirements, and applicable law.
Career Radar stores source and application URLs so provenance is retained.

## Sponsor registers

`data/sponsors.csv.gz` is a normalized evidence index derived from official public
registers. The upstream authority remains authoritative and may impose its own reuse
terms. Registry presence is evidence, not legal advice and not a guarantee that a
particular role or candidate will be sponsored.

## Generated catalog snapshots

Project-owned code, schemas, transformations, and original authored material are
covered by the repository software license unless a file says otherwise. Generated
catalog manifests and normalized factual fields may also contain or refer to third-party
material whose original rights and terms remain in force.

Redistributors should preserve provenance, generation timestamps, eligibility evidence,
the repository's required notices, and this data notice. They must not present stale
snapshots as current vacancies.

No API keys, access tokens, candidate profiles, notes, or application tracking records
belong in published market-data snapshots. Publication validation must fail if secret
material is detected.

## Commercial use

The repository's public PolyForm license does not grant commercial-use rights in the
project-owned software. See `COMMERCIAL_LICENSE.md` for commercial licensing.
Third-party data rights remain separate and may require additional permission from the
relevant source regardless of any commercial license granted for Career Radar itself.

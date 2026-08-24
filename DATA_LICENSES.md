# Data sources, terms, and attribution

Career Radar's software is MIT-licensed. That license does not relicense third-party
job postings, company pages, or government registers included in generated datasets.

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

Catalog manifests and normalized factual fields produced by this project may be used
under the repository's MIT license only to the extent the project owns those fields.
Embedded third-party text and metadata retain their original rights and terms.
Redistributors should preserve provenance, generation timestamps, eligibility evidence,
and this notice, and should not present stale snapshots as current vacancies.

No API keys, access tokens, candidate profiles, notes, or application tracking records
belong in published market-data snapshots. Publication validation must fail if secret
material is detected.

# ATS Connectors

Career Radar intentionally prefers public first-party ATS feeds over scraping LinkedIn or other aggregators.

## Greenhouse

Public Job Board API:

```text
GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
```

Documentation:
https://developer.greenhouse.io/job-board.html

## Lever

Global:

```text
GET https://api.lever.co/v0/postings/{site}?mode=json
```

EU instance:

```text
GET https://api.eu.lever.co/v0/postings/{site}?mode=json
```

Documentation:
https://github.com/lever/postings-api

## Ashby

```text
GET https://api.ashbyhq.com/posting-api/job-board/{job_board_name}?includeCompensation=true
```

Documentation:
https://developers.ashbyhq.com/docs/public-job-posting-api

## Workable

```text
GET https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true
```

The connector requests details so the eligibility engine can inspect the full public description.

## Personio

```text
GET https://{company}.jobs.personio.de/xml?language=en
```

Personio is XML rather than JSON and has its own parser.

Documentation:
https://developer.personio.de/docs/retrieving-open-job-positions

## Connector policy

- Read public job feeds only.
- Do not submit applications.
- Do not bypass authentication or anti-bot controls.
- Fail loudly on malformed feeds.
- Keep parsing isolated from eligibility logic.

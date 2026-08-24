from __future__ import annotations

import json

from europe_visa_jobs.connectors.base import BaseConnector, ConnectorError
from europe_visa_jobs.schemas import ATSProvider, NormalizedJob
from europe_visa_jobs.utils import classify_role, html_to_text, infer_country


class TeamtailorConnector(BaseConnector):
    """Teamtailor's JSON:API requires a customer API token; public HTML JSON-LD is supported when present."""

    async def fetch_jobs(self) -> list[NormalizedJob]:
        token = self.source.metadata.get("api_token") if isinstance(self.source.metadata, dict) else None
        if token:
            rows: list[dict] = []
            next_url: str | None = self.endpoint("https://api.teamtailor.com/v1/jobs")
            while next_url:
                response = await self._get(next_url, headers={"Authorization": f"Bearer {token}", "X-Api-Version": "20240404"})
                try:
                    payload = response.json()
                    page = payload["data"]
                    if not isinstance(page, list):
                        raise TypeError
                    rows.extend(item for item in page if isinstance(item, dict))
                    next_url = (payload.get("links") or {}).get("next")
                except (ValueError, KeyError, TypeError, AttributeError) as exc:
                    raise ConnectorError("teamtailor: invalid API payload", category="invalid_response") from exc
            return [_job(self.source, item.get("attributes", item)) for item in rows if isinstance(item, dict)]
        self.completeness = "partial"
        response = await self._get(self.endpoint(f"https://{self.source.slug}.teamtailor.com/jobs"))
        jobs: list[NormalizedJob] = []
        marker = "application/ld+json"
        text = response.text
        for raw in text.split(marker)[1:]:
            fragment = raw.split(">", 1)[-1].split("</script>", 1)[0].strip()
            try:
                payload = json.loads(fragment)
            except json.JSONDecodeError:
                continue
            items = payload if isinstance(payload, list) else [payload]
            jobs.extend(_job(self.source, item) for item in items if isinstance(item, dict) and item.get("title"))
        if not jobs and "job" not in text.casefold():
            raise ConnectorError("teamtailor: public jobs page did not expose job data", category="unsupported_public_feed")
        return jobs


def _job(source, row: dict) -> NormalizedJob:
    location = row.get("jobLocation") or row.get("location") or ""
    if isinstance(location, dict):
        location = location.get("address", location)
    if isinstance(location, dict):
        location = ", ".join(str(location.get(key)) for key in ("addressLocality", "addressRegion", "addressCountry") if location.get(key))
    title = row.get("title") or "Untitled role"
    url = row.get("url") or row.get("applyUrl") or ""
    return NormalizedJob(
        external_id=str(row.get("identifier") or row.get("id") or url), provider=ATSProvider.TEAMTAILOR,
        source_slug=source.slug, company_name=source.company_name, title=title,
        description=html_to_text(row.get("description") or ""), location=str(location),
        country=infer_country(str(location), source.default_country), apply_url=url, job_url=url,
        job_family=classify_role(title), raw=row,
    )

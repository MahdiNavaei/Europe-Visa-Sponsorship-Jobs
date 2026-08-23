from __future__ import annotations

from europe_visa_jobs.connectors.base import BaseConnector, ConnectorError
from europe_visa_jobs.connectors.common import parse_datetime
from europe_visa_jobs.schemas import ATSProvider, NormalizedJob
from europe_visa_jobs.utils import classify_role, html_to_text, infer_country


class AshbyConnector(BaseConnector):
    async def fetch_jobs(self) -> list[NormalizedJob]:
        url = self.endpoint(f"https://api.ashbyhq.com/posting-api/job-board/{self.source.slug}")
        response = await self._get(url, params={"includeCompensation": "true"})
        try:
            payload = response.json()
            rows = payload["jobs"]
        except (ValueError, KeyError, TypeError) as exc:
            raise ConnectorError("ashby: invalid jobs payload") from exc

        jobs: list[NormalizedJob] = []
        for row in rows:
            if row.get("isListed") is False:
                continue
            location = row.get("location") or ""
            description = html_to_text(row.get("descriptionHtml") or row.get("description"))
            external_id = str(row.get("id") or row.get("jobUrl") or row.get("applyUrl"))
            jobs.append(
                NormalizedJob(
                    external_id=external_id,
                    provider=ATSProvider.ASHBY,
                    source_slug=self.source.slug,
                    company_name=self.source.company_name,
                    title=row.get("title") or "Untitled role",
                    description=description,
                    location=location,
                    country=infer_country(location, self.source.default_country),
                    department=row.get("department") or row.get("team"),
                    employment_type=row.get("employmentType"),
                    workplace_type=row.get("workplaceType"),
                    apply_url=row.get("applyUrl") or row.get("jobUrl") or "",
                    job_url=row.get("jobUrl"),
                    posted_at=parse_datetime(row.get("publishedAt")),
                    job_family=classify_role(row.get("title") or ""),
                    raw=row,
                )
            )
        return jobs

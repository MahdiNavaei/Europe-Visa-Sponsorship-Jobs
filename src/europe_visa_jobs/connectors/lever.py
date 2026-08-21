from __future__ import annotations

from europe_visa_jobs.connectors.base import BaseConnector, ConnectorError
from europe_visa_jobs.connectors.common import parse_datetime
from europe_visa_jobs.schemas import ATSProvider, NormalizedJob
from europe_visa_jobs.utils import classify_role, html_to_text, infer_country, normalize_whitespace


class LeverConnector(BaseConnector):
    async def fetch_jobs(self) -> list[NormalizedJob]:
        host = "api.eu.lever.co" if (self.source.region or "").casefold() == "eu" else "api.lever.co"
        url = f"https://{host}/v0/postings/{self.source.slug}"
        response = await self._get(url, params={"mode": "json"})
        try:
            rows = response.json()
            if not isinstance(rows, list):
                raise TypeError
        except (ValueError, TypeError) as exc:
            raise ConnectorError("lever: invalid jobs payload") from exc

        jobs: list[NormalizedJob] = []
        for row in rows:
            categories = row.get("categories") or {}
            location = categories.get("location") or ""
            description = row.get("descriptionPlain") or html_to_text(row.get("description"))
            additional = row.get("additionalPlain") or html_to_text(row.get("additional"))
            description = normalize_whitespace(f"{description} {additional}")
            jobs.append(
                NormalizedJob(
                    external_id=str(row.get("id") or row.get("hostedUrl")),
                    provider=ATSProvider.LEVER,
                    source_slug=self.source.slug,
                    company_name=self.source.company_name,
                    title=row.get("text") or "Untitled role",
                    description=description,
                    location=location,
                    country=infer_country(location, self.source.default_country),
                    department=categories.get("department") or categories.get("team"),
                    employment_type=categories.get("commitment"),
                    apply_url=row.get("applyUrl") or row.get("hostedUrl") or "",
                    job_url=row.get("hostedUrl"),
                    posted_at=parse_datetime(row.get("createdAt")),
                    job_family=classify_role(row.get("text") or ""),
                    raw=row,
                )
            )
        return jobs

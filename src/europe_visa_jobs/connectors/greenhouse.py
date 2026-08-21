from __future__ import annotations

from europe_visa_jobs.connectors.base import BaseConnector, ConnectorError
from europe_visa_jobs.connectors.common import parse_datetime
from europe_visa_jobs.schemas import ATSProvider, NormalizedJob
from europe_visa_jobs.utils import classify_role, html_to_text, infer_country


class GreenhouseConnector(BaseConnector):
    async def fetch_jobs(self) -> list[NormalizedJob]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{self.source.slug}/jobs"
        response = await self._get(url, params={"content": "true"})
        try:
            payload = response.json()
            rows = payload["jobs"]
        except (ValueError, KeyError, TypeError) as exc:
            raise ConnectorError("greenhouse: invalid jobs payload") from exc

        jobs: list[NormalizedJob] = []
        for row in rows:
            location = (row.get("location") or {}).get("name") or ""
            description = html_to_text(row.get("content"))
            jobs.append(
                NormalizedJob(
                    external_id=str(row["id"]),
                    provider=ATSProvider.GREENHOUSE,
                    source_slug=self.source.slug,
                    company_name=self.source.company_name,
                    title=row.get("title") or "Untitled role",
                    description=description,
                    location=location,
                    country=infer_country(location, self.source.default_country),
                    department=_first_name(row.get("departments")),
                    apply_url=row.get("absolute_url") or "",
                    job_url=row.get("absolute_url"),
                    posted_at=parse_datetime(row.get("updated_at")),
                    job_family=classify_role(row.get("title") or ""),
                    raw=row,
                )
            )
        return jobs


def _first_name(items: object) -> str | None:
    if not isinstance(items, list) or not items:
        return None
    first = items[0]
    return first.get("name") if isinstance(first, dict) else None

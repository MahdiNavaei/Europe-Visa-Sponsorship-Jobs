from __future__ import annotations

from europe_visa_jobs.connectors.base import BaseConnector, ConnectorError
from europe_visa_jobs.connectors.common import parse_datetime
from europe_visa_jobs.schemas import ATSProvider, NormalizedJob
from europe_visa_jobs.utils import classify_role, html_to_text, infer_country


class WorkableConnector(BaseConnector):
    async def fetch_jobs(self) -> list[NormalizedJob]:
        url = f"https://apply.workable.com/api/v1/widget/accounts/{self.source.slug}"
        response = await self._get(url, params={"details": "true"})
        try:
            payload = response.json()
            rows = payload["jobs"]
        except (ValueError, KeyError, TypeError) as exc:
            raise ConnectorError("workable: invalid jobs payload") from exc

        jobs: list[NormalizedJob] = []
        for row in rows:
            location = _location(row)
            description = html_to_text(row.get("full_description") or row.get("description"))
            jobs.append(
                NormalizedJob(
                    external_id=str(row.get("shortcode") or row.get("code") or row.get("url")),
                    provider=ATSProvider.WORKABLE,
                    source_slug=self.source.slug,
                    company_name=self.source.company_name,
                    title=row.get("title") or "Untitled role",
                    description=description,
                    location=location,
                    country=_country(row) or infer_country(location, self.source.default_country),
                    department=row.get("department"),
                    employment_type=row.get("employment_type"),
                    workplace_type=row.get("workplace_type"),
                    apply_url=row.get("application_url") or row.get("url") or row.get("shortlink") or "",
                    job_url=row.get("url") or row.get("shortlink"),
                    posted_at=parse_datetime(row.get("published_on") or row.get("created_at")),
                    job_family=classify_role(row.get("title") or ""),
                    raw=row,
                )
            )
        return jobs


def _country(row: dict[str, object]) -> str | None:
    country = row.get("country")
    if isinstance(country, str) and country:
        return country
    location = row.get("location")
    if isinstance(location, dict):
        value = location.get("country") or location.get("country_name")
        return str(value) if value else None
    return None


def _location(row: dict[str, object]) -> str:
    location = row.get("location")
    if isinstance(location, str):
        return location
    if isinstance(location, dict):
        parts = [location.get("city"), location.get("state"), location.get("country")]
        return ", ".join(str(item) for item in parts if item)
    parts = [row.get("city"), row.get("state"), row.get("country")]
    return ", ".join(str(item) for item in parts if item)

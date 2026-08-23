from __future__ import annotations

from europe_visa_jobs.connectors.base import BaseConnector, ConnectorError
from europe_visa_jobs.connectors.common import parse_datetime
from europe_visa_jobs.schemas import ATSProvider, NormalizedJob
from europe_visa_jobs.utils import classify_role, infer_country


class SmartRecruitersConnector(BaseConnector):
    async def fetch_jobs(self) -> list[NormalizedJob]:
        response = await self._get(self.endpoint(f"https://api.smartrecruiters.com/v1/companies/{self.source.slug}/postings"), params={"limit": 100})
        try:
            payload = response.json()
            rows = payload["content"]
            if not isinstance(rows, list):
                raise TypeError
        except (ValueError, KeyError, TypeError) as exc:
            raise ConnectorError("smartrecruiters: invalid postings payload", category="invalid_response") from exc
        return [_job(self.source, row) for row in rows if isinstance(row, dict)]


def _job(source, row: dict) -> NormalizedJob:
    location = row.get("location") or {}
    if isinstance(location, dict):
        location_text = ", ".join(str(location.get(key)) for key in ("city", "region", "country") if location.get(key))
        country = location.get("country")
    else:
        location_text, country = str(location), None
    ref = str(row.get("id") or row.get("uuid") or row.get("refNumber") or row.get("name"))
    url = row.get("ref") or f"https://jobs.smartrecruiters.com/{source.slug}/{ref}"
    title = row.get("name") or "Untitled role"
    return NormalizedJob(
        external_id=ref, provider=ATSProvider.SMARTRECRUITERS, source_slug=source.slug,
        company_name=source.company_name, title=title, description="", location=location_text,
        country=country or infer_country(location_text, source.default_country),
        department=row.get("department", {}).get("label") if isinstance(row.get("department"), dict) else None,
        employment_type=row.get("typeOfEmployment"), apply_url=url, job_url=url,
        posted_at=parse_datetime(row.get("releasedDate")), job_family=classify_role(title), raw=row,
    )

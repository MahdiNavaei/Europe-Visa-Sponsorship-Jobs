from __future__ import annotations

from europe_visa_jobs.connectors.base import BaseConnector, ConnectorError
from europe_visa_jobs.connectors.common import parse_datetime
from europe_visa_jobs.schemas import ATSProvider, NormalizedJob
from europe_visa_jobs.utils import classify_role, infer_country


class RecruiteeConnector(BaseConnector):
    """Public Recruitee offers feed; the provider exposes no sponsorship signal."""

    async def fetch_jobs(self) -> list[NormalizedJob]:
        response = await self._get(self.endpoint(f"https://{self.source.slug}.recruitee.com/api/offers/"))
        try:
            payload = response.json()
            rows = payload.get("offers", payload) if isinstance(payload, dict) else payload
            if not isinstance(rows, list):
                raise TypeError
        except (ValueError, TypeError, AttributeError) as exc:
            raise ConnectorError("recruitee: invalid offers payload", category="invalid_response") from exc
        return [_job(self.source, row) for row in rows if isinstance(row, dict)]


def _job(source, row: dict) -> NormalizedJob:
    location = row.get("location") or row.get("city") or ""
    location = location if isinstance(location, str) else ", ".join(str(v) for v in location.values() if v)
    title = row.get("title") or row.get("name") or "Untitled role"
    url = row.get("careers_url") or row.get("url") or row.get("offer_url") or ""
    return NormalizedJob(
        external_id=str(row.get("id") or row.get("slug") or url), provider=ATSProvider.RECRUITEE,
        source_slug=source.slug, company_name=source.company_name, title=title,
        description=row.get("description") or "", location=location,
        country=row.get("country") or infer_country(location, source.default_country),
        department=row.get("department"), employment_type=row.get("employment_type"),
        apply_url=url, job_url=url, posted_at=parse_datetime(row.get("created_at") or row.get("published_at")),
        job_family=classify_role(title), raw=row,
    )

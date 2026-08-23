from __future__ import annotations

from europe_visa_jobs.connectors.base import BaseConnector, ConnectorError
from europe_visa_jobs.connectors.common import parse_datetime
from europe_visa_jobs.schemas import ATSProvider, NormalizedJob
from europe_visa_jobs.utils import classify_role, infer_country


class WorkdayConnector(BaseConnector):
    """Workday is a boundary adapter: tenants require a tenant/site-specific POST contract."""

    async def fetch_jobs(self) -> list[NormalizedJob]:
        metadata = self.source.metadata if isinstance(self.source.metadata, dict) else {}
        endpoint = self.endpoint("")
        if not endpoint:
            raise ConnectorError("workday: tenant-specific cxs endpoint is required", category="unsupported_provider_boundary")
        response = await self.client.post(endpoint, json=metadata.get("query", {"appliedFacets": {}, "limit": 100}), headers={"User-Agent": "CareerRadar/1.0"})
        if response.status_code >= 400:
            raise ConnectorError(f"workday: HTTP {response.status_code}", status_code=response.status_code, category="http_error")
        try:
            rows = response.json()["jobPostings"]
        except (ValueError, KeyError, TypeError) as exc:
            raise ConnectorError("workday: invalid jobPostings payload", category="invalid_response") from exc
        return [_job(self.source, row) for row in rows if isinstance(row, dict)]


def _job(source, row: dict) -> NormalizedJob:
    title = row.get("title") or row.get("jobPostingTitle") or "Untitled role"
    location = row.get("locationsText") or row.get("location") or ""
    url = row.get("externalUrl") or row.get("jobUrl") or ""
    return NormalizedJob(
        external_id=str(row.get("jobPostingId") or row.get("bulletinId") or url), provider=ATSProvider.WORKDAY,
        source_slug=source.slug, company_name=source.company_name, title=title,
        description=row.get("jobDescription") or "", location=location,
        country=infer_country(location, source.default_country), apply_url=url, job_url=url,
        posted_at=parse_datetime(row.get("postedOn")), job_family=classify_role(title), raw=row,
    )

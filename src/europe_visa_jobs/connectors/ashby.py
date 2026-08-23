from __future__ import annotations

import json

from europe_visa_jobs.connectors.base import BaseConnector, ConnectorError
from europe_visa_jobs.connectors.common import parse_datetime
from europe_visa_jobs.schemas import ATSProvider, NormalizedJob
from europe_visa_jobs.utils import classify_role, html_to_text, infer_country


class AshbyConnector(BaseConnector):
    async def fetch_jobs(self) -> list[NormalizedJob]:
        url = self.endpoint(f"https://api.ashbyhq.com/posting-api/job-board/{self.source.slug}")
        try:
            response = await self._get(url, params={"includeCompensation": "true"})
            payload = response.json()
            rows = payload["jobs"]
        except ConnectorError as exc:
            if exc.status_code != 403:
                raise
            # The public API edge may challenge a data-center client while the
            # hosted board remains public. Its server-rendered app data contains
            # the same published postings and is the supported fallback used by
            # source validation.
            board_url = self.source.board_url or self.source.careers_url or f"https://jobs.ashbyhq.com/{self.source.slug}"
            response = await self._get(board_url)
            self.completeness = "partial"
            try:
                marker = "window.__appData = "
                start = response.text.index(marker) + len(marker)
                payload = json.loads(response.text[start : response.text.index(";", start)])
                rows = payload["jobBoard"]["jobPostings"]
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as parse_exc:
                raise ConnectorError("ashby: invalid hosted board payload", category="invalid_response") from parse_exc
        except (ValueError, KeyError, TypeError) as exc:
            raise ConnectorError("ashby: invalid jobs payload") from exc

        jobs: list[NormalizedJob] = []
        for row in rows:
            if row.get("isListed") is False:
                continue
            location = row.get("location") or row.get("locationName") or ""
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
                    posted_at=parse_datetime(row.get("publishedAt") or row.get("publishedDate")),
                    job_family=classify_role(row.get("title") or ""),
                    raw=row,
                )
            )
        return jobs

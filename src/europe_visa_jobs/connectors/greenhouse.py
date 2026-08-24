from __future__ import annotations

from europe_visa_jobs.connectors.base import BaseConnector, ConnectorError
from europe_visa_jobs.connectors.common import parse_datetime
from europe_visa_jobs.schemas import ATSProvider, NormalizedJob
from europe_visa_jobs.utils import classify_role, html_to_text, infer_country


class GreenhouseConnector(BaseConnector):
    async def fetch_jobs(self) -> list[NormalizedJob]:
        url = self.endpoint(f"https://boards-api.greenhouse.io/v1/boards/{self.source.slug}/jobs")
        rows: list[dict] = []
        page = 1
        while True:
            response = await self._get(url, params={"content": "true", "page": page})
            try:
                payload = response.json()
                batch = payload["jobs"]
                if not isinstance(batch, list):
                    raise TypeError
            except (ValueError, KeyError, TypeError) as exc:
                raise ConnectorError("greenhouse: invalid jobs payload") from exc
            rows.extend(item for item in batch if isinstance(item, dict))
            metadata = payload.get("meta") if isinstance(payload, dict) else None
            total = metadata.get("total") if isinstance(metadata, dict) else None
            if isinstance(total, int):
                self.reported_total = total
            if len(batch) < 100:
                break
            if not isinstance(total, int):
                # Some public boards return a 100-row response without the
                # provider's total. Do not probe an unbounded next page and
                # call it complete; preserve unseen jobs as a partial feed.
                self.completeness = "partial"
                break
            if len(rows) >= total:
                break
            page += 1

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
                    # Greenhouse's ``updated_at`` is a mutation timestamp, not
                    # the publication date.  Never present it as job freshness.
                    posted_at=parse_datetime(row.get("first_published") or row.get("published_at")),
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

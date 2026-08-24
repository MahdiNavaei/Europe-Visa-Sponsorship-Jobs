from __future__ import annotations

import asyncio
from typing import Any

from europe_visa_jobs.connectors.base import BaseConnector, ConnectorError
from europe_visa_jobs.connectors.common import parse_datetime
from europe_visa_jobs.schemas import ATSProvider, NormalizedJob
from europe_visa_jobs.utils import classify_role, html_to_text, infer_country


class SmartRecruitersConnector(BaseConnector):
    """Enumerate postings, then retrieve the public posting-detail contract."""

    detail_completeness = "complete"

    async def fetch_jobs(self) -> list[NormalizedJob]:
        url = self.endpoint(f"https://api.smartrecruiters.com/v1/companies/{self.source.slug}/postings")
        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            response = await self._get(url, params={"limit": 100, "offset": offset})
            try:
                payload = response.json()
                batch = payload["content"]
                if not isinstance(batch, list):
                    raise TypeError
            except (ValueError, KeyError, TypeError) as exc:
                raise ConnectorError(
                    "smartrecruiters: invalid postings payload",
                    category="invalid_response",
                ) from exc
            rows.extend(item for item in batch if isinstance(item, dict))
            total = payload.get("totalFound")
            if isinstance(total, int):
                self.reported_total = total
            if len(batch) < 100 or (isinstance(total, int) and len(rows) >= total):
                break
            if not isinstance(total, int):
                self.completeness = "partial"
                break
            offset += len(batch)

        semaphore = asyncio.Semaphore(8)

        async def enrich(row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
            ref = row.get("id") or row.get("uuid") or row.get("refNumber")
            if not ref:
                return row, None
            async with semaphore:
                try:
                    detail_response = await self._get(f"{url.rstrip('/')}/{ref}")
                    detail = detail_response.json()
                    if not isinstance(detail, dict) or not isinstance(detail.get("jobAd"), dict):
                        raise ValueError
                    return row, detail
                except (ConnectorError, ValueError, TypeError):
                    return row, None

        enriched = await asyncio.gather(*(enrich(row) for row in rows))
        missing_details = sum(detail is None for _, detail in enriched)
        if missing_details:
            self.detail_completeness = "missing" if missing_details == len(enriched) else "partial"
        return [_job(self.source, row, detail) for row, detail in enriched]


def _description(detail: dict[str, Any] | None) -> str:
    job_ad = detail.get("jobAd") if isinstance(detail, dict) else None
    sections = job_ad.get("sections") if isinstance(job_ad, dict) else None
    if not isinstance(sections, dict):
        return ""
    parts: list[str] = []
    for key in ("companyDescription", "jobDescription", "qualifications", "additionalInformation"):
        section = sections.get(key)
        value = section.get("text") if isinstance(section, dict) else section
        text = html_to_text(value)
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def _job(source, row: dict[str, Any], detail: dict[str, Any] | None = None) -> NormalizedJob:
    detail = detail or {}
    location = detail.get("location") or row.get("location") or {}
    if isinstance(location, dict):
        location_text = ", ".join(
            str(location.get(key)) for key in ("city", "region", "country") if location.get(key)
        )
        country = location.get("country")
    else:
        location_text, country = str(location), None
    ref = str(row.get("id") or row.get("uuid") or row.get("refNumber") or row.get("name"))
    url = detail.get("ref") or row.get("ref") or f"https://jobs.smartrecruiters.com/{source.slug}/{ref}"
    title = detail.get("name") or row.get("name") or "Untitled role"
    department = detail.get("department") or row.get("department")
    employment = detail.get("typeOfEmployment") or row.get("typeOfEmployment")
    return NormalizedJob(
        external_id=ref,
        provider=ATSProvider.SMARTRECRUITERS,
        source_slug=source.slug,
        company_name=source.company_name,
        title=title,
        description=_description(detail),
        location=location_text,
        country=country or infer_country(location_text, source.default_country),
        department=department.get("label") if isinstance(department, dict) else None,
        employment_type=employment.get("label") if isinstance(employment, dict) else employment,
        apply_url=url,
        job_url=url,
        posted_at=parse_datetime(detail.get("releasedDate") or row.get("releasedDate")),
        job_family=classify_role(title),
        raw={"summary": row, "detail": detail} if detail else row,
    )

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import unquote, urlsplit

from europe_visa_jobs.connectors.base import BaseConnector, ConnectorError
from europe_visa_jobs.connectors.common import parse_datetime
from europe_visa_jobs.schemas import ATSProvider, NormalizedJob
from europe_visa_jobs.utils import classify_role, html_to_text, infer_country


class WorkdayConnector(BaseConnector):
    """Adapter for a tenant/site-specific Workday CXS jobs endpoint."""

    completeness = "partial"
    detail_completeness = "complete"

    async def fetch_jobs(self) -> list[NormalizedJob]:
        metadata = self.source.metadata if isinstance(self.source.metadata, dict) else {}
        endpoint = self.endpoint("")
        if not endpoint:
            raise ConnectorError(
                "workday: tenant-specific cxs endpoint is required",
                category="unsupported_provider_boundary",
            )
        query = dict(metadata.get("query") or {"appliedFacets": {}, "limit": 100})
        limit = min(max(int(query.get("limit") or 100), 1), 100)
        query["limit"] = limit
        offset = max(int(query.get("offset") or 0), 0)
        rows: list[dict[str, Any]] = []
        total: int | None = None
        while True:
            query["offset"] = offset
            response = await self._post(endpoint, json=query)
            try:
                payload = response.json()
                batch = payload["jobPostings"]
                if not isinstance(batch, list):
                    raise TypeError
            except (ValueError, KeyError, TypeError) as exc:
                raise ConnectorError(
                    "workday: invalid jobPostings payload",
                    category="invalid_response",
                ) from exc
            rows.extend(item for item in batch if isinstance(item, dict))
            reported = payload.get("total")
            total = reported if isinstance(reported, int) else total
            if len(batch) < limit or (total is not None and len(rows) >= total):
                # A known total plus complete pagination is safe to deactivate
                # missing jobs. Without it, preserve the prior partial contract.
                if total is not None and len(rows) >= total:
                    self.completeness = "complete"
                    self.reported_total = total
                break
            if total is None:
                break
            offset += len(batch)

        detail_root = endpoint.rsplit("/jobs", 1)[0] if "/jobs" in endpoint else ""
        semaphore = asyncio.Semaphore(8)

        async def enrich(row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
            path = row.get("externalPath")
            detail_url = _detail_url(detail_root, path)
            if detail_url is None:
                return row, None
            async with semaphore:
                try:
                    response = await self._get(detail_url)
                    payload = response.json()
                    info = payload.get("jobPostingInfo") if isinstance(payload, dict) else None
                    if not isinstance(info, dict):
                        raise ValueError
                    return row, info
                except (ConnectorError, ValueError, TypeError):
                    return row, None

        enriched = await asyncio.gather(*(enrich(row) for row in rows))
        missing_details = sum(detail is None for _, detail in enriched)
        if missing_details:
            self.detail_completeness = "missing" if missing_details == len(enriched) else "partial"
        return [_job(self.source, row, detail) for row, detail in enriched]


def _detail_url(detail_root: str, external_path: object) -> str | None:
    """Build a same-CXS-root Workday detail URL from a strictly relative path."""
    if not detail_root or not isinstance(external_path, str):
        return None
    parsed = urlsplit(external_path)
    decoded_path = unquote(parsed.path)
    segments = decoded_path.split("/")
    if (
        parsed.scheme
        or parsed.netloc
        or parsed.query
        or parsed.fragment
        or not decoded_path.startswith("/")
        or decoded_path.startswith("//")
        or "\\" in decoded_path
        or ".." in segments
        or "job" not in segments
    ):
        return None
    return f"{detail_root.rstrip('/')}/{decoded_path.lstrip('/')}"


def _job(source, row: dict[str, Any], detail: dict[str, Any] | None = None) -> NormalizedJob:
    detail = detail or {}
    title = detail.get("title") or row.get("title") or row.get("jobPostingTitle") or "Untitled role"
    location = detail.get("location") or row.get("locationsText") or row.get("location") or ""
    url = detail.get("externalUrl") or row.get("externalUrl") or row.get("jobUrl") or ""
    description = html_to_text(detail.get("jobDescription") or row.get("jobDescription"))
    return NormalizedJob(
        external_id=str(
            detail.get("jobReqId")
            or row.get("jobPostingId")
            or row.get("bulletinId")
            or row.get("externalPath")
            or url
        ),
        provider=ATSProvider.WORKDAY,
        source_slug=source.slug,
        company_name=source.company_name,
        title=title,
        description=description,
        location=location,
        country=infer_country(location, source.default_country),
        apply_url=url,
        job_url=url,
        posted_at=parse_datetime(detail.get("postedOn") or row.get("postedOn")),
        job_family=classify_role(title),
        raw={"summary": row, "detail": detail} if detail else row,
    )

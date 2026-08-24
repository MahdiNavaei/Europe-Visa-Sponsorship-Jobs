from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from typing import Any

import httpx

from europe_visa_jobs.discovery.http import PublicFetchError, PublicResponse, fetch_public
from europe_visa_jobs.discovery.patterns import IdentifiedSource
from europe_visa_jobs.schemas import ATSProvider, SourceValidation


def _json(body: bytes) -> Any:
    try:
        return json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("response was not JSON") from exc


def _rows(provider: ATSProvider, payload: Any) -> tuple[list[Any], str | None]:
    if provider is ATSProvider.GREENHOUSE:
        if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
            raise ValueError("greenhouse payload has no jobs list")
        return payload["jobs"], (payload.get("board") or {}).get("name") if isinstance(payload.get("board"), dict) else None
    if provider is ATSProvider.ASHBY:
        if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
            raise ValueError("ashby payload has no jobs list")
        return payload["jobs"], payload.get("organizationName")
    if provider is ATSProvider.LEVER:
        if not isinstance(payload, list):
            raise ValueError("lever payload is not a jobs list")
        return payload, None
    if provider is ATSProvider.SMARTRECRUITERS:
        if not isinstance(payload, dict) or not isinstance(payload.get("content"), list):
            raise ValueError("smartrecruiters payload has no content list")
        return payload["content"], None
    if provider is ATSProvider.RECRUITEE:
        if isinstance(payload, dict) and isinstance(payload.get("offers"), list):
            return payload["offers"], None
        if isinstance(payload, list):
            return payload, None
        raise ValueError("recruitee payload has no offers list")
    if provider is ATSProvider.WORKABLE:
        if isinstance(payload, dict) and isinstance(payload.get("jobs"), list):
            return payload["jobs"], None
        if isinstance(payload, list):
            return payload, None
        raise ValueError("workable payload has no jobs list")
    raise ValueError(f"{provider} requires a provider-specific validator")


def _ashby_html_rows(body: bytes) -> tuple[list[Any], str | None]:
    """Read Ashby's server-rendered board state when its API edge blocks us."""
    text = body.decode("utf-8", "ignore")
    marker = "window.__appData = "
    start = text.find(marker)
    if start < 0:
        raise ValueError("ashby board HTML has no embedded app data")
    start += len(marker)
    end = text.find(";", start)
    if end < 0:
        raise ValueError("ashby board app data is not terminated")
    payload = _json(text[start:end].encode("utf-8"))
    board = payload.get("jobBoard") if isinstance(payload, dict) else None
    rows = board.get("jobPostings") if isinstance(board, dict) else None
    if not isinstance(rows, list):
        raise ValueError("ashby board HTML has no jobPostings list")
    organization = payload.get("organization") if isinstance(payload, dict) else None
    company = organization.get("name") if isinstance(organization, dict) else None
    return rows, company


async def validate_candidate(
    client: httpx.AsyncClient,
    candidate: IdentifiedSource,
    *,
    probe_only: bool = False,
) -> SourceValidation:
    endpoint = candidate.api_url or candidate.canonical_url
    try:
        if probe_only and candidate.provider not in {ATSProvider.WORKDAY, ATSProvider.WORKABLE, ATSProvider.ASHBY}:
            try:
                public = await fetch_public(client, endpoint, method="HEAD")
            except PublicFetchError as exc:
                # A few hosted career pages reject HEAD even though their GET
                # endpoint is public. Only fall back for method/transport-shaped
                # errors; preserve real 404/403/429 evidence.
                if exc.status_code not in {405, 501}:
                    raise
                public = await fetch_public(client, endpoint)
            return SourceValidation(
                valid=True,
                provider=candidate.provider,
                board_identifier=candidate.board_identifier,
                canonical_url=candidate.canonical_url,
                api_url=candidate.api_url,
                http_status=public.status_code,
                etag=public.headers.get("etag"),
                last_modified=public.headers.get("last-modified"),
                metadata={"duration_ms": public.duration_ms, "probe_only": True},
            )
        if candidate.provider is ATSProvider.WORKDAY:
            response = await client.post(endpoint, json={"appliedFacets": {}, "limit": 1}, timeout=30)
            if response.status_code >= 400:
                raise PublicFetchError(f"workday endpoint returned HTTP {response.status_code}", status_code=response.status_code, category="http_error")
            public = PublicResponse(response.status_code, dict(response.headers), response.content, 0)
        else:
            try:
                public = await fetch_public(client, endpoint, params={"content": "false"} if candidate.provider is ATSProvider.GREENHOUSE else None)
            except PublicFetchError as exc:
                if candidate.provider is not ATSProvider.ASHBY or exc.status_code != 403:
                    raise
                # Ashby's API is currently fronted by a Cloudflare policy that
                # blocks this public service, while the hosted board renders the
                # same public posting list in window.__appData.
                public = await fetch_public(client, candidate.canonical_url)
        company_name: str | None = None
        count = 0
        if candidate.provider is ATSProvider.PERSONIO:
            root = ET.fromstring(public.body)
            count = sum(1 for item in root.iter() if item.tag.rsplit("}", 1)[-1].casefold() == "position")
        elif candidate.provider is ATSProvider.TEAMTAILOR:
            if b"job" not in public.body.lower():
                raise ValueError("teamtailor response is not a recognizable careers page")
            count = public.body.lower().count(b"job")
        elif candidate.provider is ATSProvider.WORKDAY:
            payload = _json(public.body)
            if not isinstance(payload, dict) or not isinstance(payload.get("jobPostings"), list):
                raise ValueError("workday payload has no jobPostings list")
            count = len(payload["jobPostings"])
        elif candidate.provider is ATSProvider.ASHBY and public.headers.get("content-type", "").lower().find("text/html") >= 0:
            rows, company_name = _ashby_html_rows(public.body)
            count = len(rows)
        else:
            rows, company_name = _rows(candidate.provider, _json(public.body))
            count = len(rows)
        return SourceValidation(
            valid=True,
            provider=candidate.provider,
            board_identifier=candidate.board_identifier,
            canonical_url=candidate.canonical_url,
            api_url=candidate.api_url,
            company_name=company_name,
            job_count=count,
            http_status=public.status_code,
            etag=public.headers.get("etag"),
            last_modified=public.headers.get("last-modified"),
            metadata={"duration_ms": public.duration_ms, "not_modified": public.not_modified},
        )
    except PublicFetchError as exc:
        return SourceValidation(
            valid=False,
            provider=candidate.provider,
            board_identifier=candidate.board_identifier,
            canonical_url=candidate.canonical_url,
            api_url=candidate.api_url,
            http_status=exc.status_code,
            error_category=exc.category,
            failure_type=exc.category,
            error=str(exc),
            metadata={"retry_after_seconds": exc.retry_after_seconds}
            if exc.retry_after_seconds is not None
            else {},
        )
    except httpx.TimeoutException as exc:
        return SourceValidation(
            valid=False,
            provider=candidate.provider,
            board_identifier=candidate.board_identifier,
            canonical_url=candidate.canonical_url,
            api_url=candidate.api_url,
            error_category="timeout",
            failure_type="timeout",
            error=str(exc) or "provider request timed out",
        )
    except httpx.NetworkError as exc:
        return SourceValidation(
            valid=False,
            provider=candidate.provider,
            board_identifier=candidate.board_identifier,
            canonical_url=candidate.canonical_url,
            api_url=candidate.api_url,
            error_category="network",
            failure_type="network",
            error=str(exc) or "provider network error",
        )
    except (ValueError, ET.ParseError) as exc:
        return SourceValidation(
            valid=False,
            provider=candidate.provider,
            board_identifier=candidate.board_identifier,
            canonical_url=candidate.canonical_url,
            api_url=candidate.api_url,
            error_category="invalid_response",
            failure_type="invalid_response",
            error=str(exc),
        )

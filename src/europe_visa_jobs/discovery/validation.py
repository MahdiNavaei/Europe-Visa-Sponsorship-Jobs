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


async def validate_candidate(client: httpx.AsyncClient, candidate: IdentifiedSource) -> SourceValidation:
    endpoint = candidate.api_url or candidate.canonical_url
    try:
        if candidate.provider is ATSProvider.WORKDAY:
            response = await client.post(endpoint, json={"appliedFacets": {}, "limit": 1}, timeout=30)
            if response.status_code >= 400:
                raise PublicFetchError(f"workday endpoint returned HTTP {response.status_code}", status_code=response.status_code, category="http_error")
            public = PublicResponse(response.status_code, dict(response.headers), response.content, 0)
        else:
            public = await fetch_public(client, endpoint, params={"content": "false"} if candidate.provider is ATSProvider.GREENHOUSE else None)
        company_name: str | None = None
        count = 0
        if candidate.provider is ATSProvider.PERSONIO:
            root = ET.fromstring(public.body)
            count = len(root.findall(".//position"))
        elif candidate.provider is ATSProvider.TEAMTAILOR:
            if b"job" not in public.body.lower():
                raise ValueError("teamtailor response is not a recognizable careers page")
            count = public.body.lower().count(b"job")
        elif candidate.provider is ATSProvider.WORKDAY:
            payload = _json(public.body)
            if not isinstance(payload, dict) or not isinstance(payload.get("jobPostings"), list):
                raise ValueError("workday payload has no jobPostings list")
            count = len(payload["jobPostings"])
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
            error=str(exc),
        )
    except (ValueError, ET.ParseError) as exc:
        return SourceValidation(
            valid=False,
            provider=candidate.provider,
            board_identifier=candidate.board_identifier,
            canonical_url=candidate.canonical_url,
            api_url=candidate.api_url,
            error_category="invalid_response",
            error=str(exc),
        )

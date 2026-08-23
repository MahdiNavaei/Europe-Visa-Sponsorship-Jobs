from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

import httpx

from europe_visa_jobs.discovery.http import fetch_public
from europe_visa_jobs.discovery.patterns import identify_source_url
from europe_visa_jobs.schemas import ATSProvider, SourceCandidate

INDEX_DOMAINS: dict[ATSProvider, tuple[str, ...]] = {
    ATSProvider.GREENHOUSE: ("boards.greenhouse.io", "job-boards.greenhouse.io"),
    ATSProvider.LEVER: ("jobs.lever.co", "jobs.eu.lever.co"),
    ATSProvider.ASHBY: ("jobs.ashbyhq.com",),
    ATSProvider.WORKABLE: ("apply.workable.com",),
    ATSProvider.PERSONIO: ("jobs.personio.com", "jobs.personio.de"),
    ATSProvider.TEAMTAILOR: ("teamtailor.com",),
    ATSProvider.RECRUITEE: ("recruitee.com",),
    ATSProvider.SMARTRECRUITERS: ("jobs.smartrecruiters.com",),
    ATSProvider.WORKDAY: ("myworkdayjobs.com",),
}


def _candidate(url: str, method: str) -> SourceCandidate | None:
    identified = identify_source_url(url)
    return identified.candidate(discovery_method=method) if identified else None


async def wayback_candidates(
    client: httpx.AsyncClient,
    provider: ATSProvider,
    *,
    recent_days: int | None = None,
    max_rows: int | None = None,
) -> list[SourceCandidate]:
    """Query CDX for archived ATS URLs; results are candidates, never trusted sources."""
    discovered: dict[tuple[str, str], SourceCandidate] = {}
    for domain in INDEX_DOMAINS.get(provider, ()):
        params = {
            "url": f"*.{domain}/*" if domain not in {"boards.greenhouse.io", "jobs.lever.co", "jobs.eu.lever.co", "jobs.smartrecruiters.com"} else f"{domain}/*",
            "matchType": "domain" if domain in {"teamtailor.com", "recruitee.com", "jobs.personio.com", "jobs.personio.de", "myworkdayjobs.com"} else "prefix",
            "output": "json",
            "fl": "original",
            "filter": "statuscode:200",
            "collapse": "urlkey",
        }
        if recent_days is not None:
            params["from"] = (datetime.now(UTC) - timedelta(days=recent_days)).strftime("%Y%m%d")
        url = "https://web.archive.org/cdx/search/cdx"
        response = await fetch_public(client, url, params=params, retries=4)
        try:
            payload = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        rows = payload[1:] if isinstance(payload, list) and payload and isinstance(payload[0], list) else payload
        for row in rows or []:
            original = row[0] if isinstance(row, list) and row else row.get("original") if isinstance(row, dict) else None
            if not original:
                continue
            item = _candidate(original, "wayback_recent" if recent_days is not None else "wayback_cdx")
            if item:
                discovered[(item.provider.value, item.board_identifier)] = item
                if max_rows and len(discovered) >= max_rows:
                    return list(discovered.values())
    return list(discovered.values())


async def common_crawl_index(client: httpx.AsyncClient) -> str:
    response = await fetch_public(client, "https://index.commoncrawl.org/collinfo.json", retries=4)
    payload = json.loads(response.body.decode("utf-8"))
    if not payload or not isinstance(payload[0], dict) or not payload[0].get("cdx-api"):
        raise ValueError("Common Crawl returned no collection index")
    return str(payload[0]["cdx-api"])


async def common_crawl_candidates(
    client: httpx.AsyncClient,
    provider: ATSProvider,
    *,
    max_pages: int = 10,
    collection_api: str | None = None,
) -> list[SourceCandidate]:
    if collection_api is None:
        collection_api = await common_crawl_index(client)
    cdx = collection_api
    discovered: dict[tuple[str, str], SourceCandidate] = {}
    for domain in INDEX_DOMAINS.get(provider, ()):
        query = f"{cdx}?url={quote(domain + '/*')}&output=json&fl=url&filter=status:200"
        for page in range(max_pages):
            if page:
                import asyncio
                await asyncio.sleep(1.0)
            try:
                response = await fetch_public(client, f"{query}&page={page}", retries=4)
            except Exception:
                # Keep already harvested pages; a collection can reject a later page
                # token or become unavailable while the accumulated candidates remain useful.
                break
            if not response.body.strip():
                break
            for line in response.body.decode("utf-8", "ignore").splitlines():
                try:
                    original = json.loads(line).get("url")
                except json.JSONDecodeError:
                    continue
                item = _candidate(original or "", "common_crawl")
                if item:
                    discovered[(item.provider.value, item.board_identifier)] = item
    return list(discovered.values())


async def urlscan_candidates(client: httpx.AsyncClient, provider: ATSProvider) -> list[SourceCandidate]:
    discovered: dict[tuple[str, str], SourceCandidate] = {}
    for domain in INDEX_DOMAINS.get(provider, ()):
        url = f"https://urlscan.io/api/v1/search/?q=domain:{quote(domain)}&size=10000"
        try:
            response = await fetch_public(client, url, retries=2)
        except Exception:
            continue
        try:
            payload = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        for row in payload.get("results", []):
            page = row.get("page", {}) if isinstance(row, dict) else {}
            item = _candidate(page.get("url", ""), "urlscan_recent")
            if item:
                discovered[(item.provider.value, item.board_identifier)] = item
    return list(discovered.values())

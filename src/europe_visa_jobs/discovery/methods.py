from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

import httpx

from europe_visa_jobs.discovery.http import fetch_public
from europe_visa_jobs.discovery.patterns import identify_source_url, plausible_identifier
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
    if identified is None or not plausible_identifier(identified.provider, identified.board_identifier):
        return None
    return identified.candidate(discovery_method=method)


async def wayback_candidates(
    client: httpx.AsyncClient,
    provider: ATSProvider,
    *,
    recent_days: int | None = None,
    max_rows: int | None = None,
    stats: dict[str, int] | None = None,
) -> list[SourceCandidate]:
    """Query CDX for archived ATS URLs; results are candidates, never trusted sources."""
    discovered: dict[tuple[str, str], SourceCandidate] = {}
    for domain in INDEX_DOMAINS.get(provider, ()):
        params = {
            # Domain matching is materially broader than a prefix query for
            # provider hosts: it includes job-detail paths and both hosted-board
            # variants while the slug extractor keeps only the first segment.
            "url": f"{domain}/*",
            "matchType": "domain",
            "output": "json",
            "fl": "original",
            "filter": "statuscode:200",
            "collapse": "urlkey",
        }
        if recent_days is not None:
            params["from"] = (datetime.now(UTC) - timedelta(days=recent_days)).strftime("%Y%m%d")
        url = "https://web.archive.org/cdx/search/cdx"
        response = await fetch_public(client, url, params=params, retries=2, timeout=300)
        try:
            payload = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        rows = payload[1:] if isinstance(payload, list) and payload and isinstance(payload[0], list) else payload
        for row in rows or []:
            if stats is not None:
                stats["raw"] = stats.get("raw", 0) + 1
            original = row[0] if isinstance(row, list) and row else row.get("original") if isinstance(row, dict) else None
            if not original:
                if stats is not None:
                    stats["filtered"] = stats.get("filtered", 0) + 1
                continue
            item = _candidate(original, "wayback_recent" if recent_days is not None else "wayback_cdx")
            if item:
                discovered[(item.provider.value, item.board_identifier)] = item
                if stats is not None:
                    stats["accepted"] = stats.get("accepted", 0) + 1
                if max_rows and len(discovered) >= max_rows:
                    return list(discovered.values())
            elif stats is not None:
                stats["filtered"] = stats.get("filtered", 0) + 1
    return list(discovered.values())


async def common_crawl_index(client: httpx.AsyncClient) -> str:
    response = await fetch_public(client, "https://index.commoncrawl.org/collinfo.json", retries=4, timeout=120)
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
    stats: dict[str, int] | None = None,
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
                response = await fetch_public(client, f"{query}&page={page}", retries=4, timeout=120)
            except Exception:
                # Keep already harvested pages; a collection can reject a later page
                # token or become unavailable while the accumulated candidates remain useful.
                break
            if not response.body.strip():
                break
            for line in response.body.decode("utf-8", "ignore").splitlines():
                if stats is not None:
                    stats["raw"] = stats.get("raw", 0) + 1
                try:
                    original = json.loads(line).get("url")
                except json.JSONDecodeError:
                    if stats is not None:
                        stats["filtered"] = stats.get("filtered", 0) + 1
                    continue
                item = _candidate(original or "", "common_crawl")
                if item:
                    discovered[(item.provider.value, item.board_identifier)] = item
                    if stats is not None:
                        stats["accepted"] = stats.get("accepted", 0) + 1
                elif stats is not None:
                    stats["filtered"] = stats.get("filtered", 0) + 1
    return list(discovered.values())


async def urlscan_candidates(
    client: httpx.AsyncClient,
    provider: ATSProvider,
    stats: dict[str, int] | None = None,
    max_pages: int = 10,
) -> list[SourceCandidate]:
    discovered: dict[tuple[str, str], SourceCandidate] = {}
    for domain in INDEX_DOMAINS.get(provider, ()):
        cursor: str | None = None
        for page_number in range(max(1, max_pages)):
            if page_number:
                await asyncio.sleep(1.1)
            url = f"https://urlscan.io/api/v1/search/?q=page.domain%3A{quote(domain)}&size=10000"
            if cursor:
                url += f"&search_after={quote(cursor)}"
            try:
                response = await fetch_public(client, url, retries=2, timeout=60)
                payload = json.loads(response.body.decode("utf-8"))
            except Exception:
                break
            results = payload.get("results", []) if isinstance(payload, dict) else []
            for row in results:
                if stats is not None:
                    stats["raw"] = stats.get("raw", 0) + 1
                page = row.get("page", {}) if isinstance(row, dict) else {}
                item = _candidate(page.get("url", ""), "urlscan_recent")
                if item:
                    discovered[(item.provider.value, item.board_identifier)] = item
                    if stats is not None:
                        stats["accepted"] = stats.get("accepted", 0) + 1
                elif stats is not None:
                    stats["filtered"] = stats.get("filtered", 0) + 1
            if not payload.get("has_more") or not results:
                break
            sort = results[-1].get("sort") if isinstance(results[-1], dict) else None
            if not isinstance(sort, list) or len(sort) != 2:
                break
            cursor = f"{sort[0]},{sort[1]}"
    return list(discovered.values())

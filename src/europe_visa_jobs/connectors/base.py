from __future__ import annotations

import asyncio
import random
from abc import ABC, abstractmethod
from time import monotonic
from typing import Any

import httpx

from europe_visa_jobs.schemas import NormalizedJob, SourceConfig


class ConnectorError(RuntimeError):
    """Raised when a connector cannot retrieve or parse a public job feed."""

    def __init__(self, message: str, *, status_code: int | None = None, category: str = "connector") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.category = category


class ConnectorNotModified(ConnectorError):
    """A conditional request returned 304; the prior successful snapshot remains valid."""


class BaseConnector(ABC):
    def __init__(self, client: httpx.AsyncClient, source: SourceConfig) -> None:
        self.client = client
        self.source = source
        self.last_response_headers: dict[str, str] = {}
        self.last_fetch_duration_ms = 0

    def endpoint(self, fallback: str) -> str:
        return self.source.api_url or fallback

    @abstractmethod
    async def fetch_jobs(self) -> list[NormalizedJob]:
        raise NotImplementedError

    async def _get(self, url: str, **kwargs: Any) -> httpx.Response:
        headers = dict(kwargs.pop("headers", {}) or {})
        headers.setdefault("User-Agent", "CareerRadar/1.0 (+https://github.com/MahdiNavaei/Europe-Visa-Sponsorship-Jobs)")
        cache = self.source.metadata.get("cache", {}) if isinstance(self.source.metadata, dict) else {}
        if cache.get("etag"):
            headers["If-None-Match"] = cache["etag"]
        if cache.get("last_modified"):
            headers["If-Modified-Since"] = cache["last_modified"]
        for attempt in range(3):
            started = monotonic()
            try:
                response = await self.client.get(url, headers=headers, **kwargs)
                self.last_response_headers = dict(response.headers)
                self.last_fetch_duration_ms = int((monotonic() - started) * 1000)
                if response.status_code == 304:
                    raise ConnectorNotModified(f"{self.source.provider}: {url} was not modified", status_code=304, category="not_modified")
                if response.status_code < 400:
                    return response
                category = "rate_limited" if response.status_code == 429 else "blocked" if response.status_code in {401, 403} else "not_found" if response.status_code == 404 else "server_error" if response.status_code >= 500 else "http_error"
                if attempt == 2 or category in {"blocked", "not_found", "http_error"}:
                    raise ConnectorError(f"{self.source.provider}: failed to fetch {url}: HTTP {response.status_code}", status_code=response.status_code, category=category)
                await asyncio.sleep(min(2**attempt + random.uniform(0, 0.3), 30.0))
            except ConnectorError:
                raise
            except httpx.TimeoutException as exc:
                if attempt == 2:
                    raise ConnectorError(f"{self.source.provider}: timeout fetching {url}", category="timeout") from exc
                await asyncio.sleep(min(2**attempt + random.uniform(0, 0.3), 30.0))
            except httpx.NetworkError as exc:
                if attempt == 2:
                    raise ConnectorError(f"{self.source.provider}: network failure fetching {url}: {exc}", category="network") from exc
                await asyncio.sleep(min(2**attempt + random.uniform(0, 0.3), 30.0))
        raise ConnectorError(f"{self.source.provider}: failed to fetch {url}")

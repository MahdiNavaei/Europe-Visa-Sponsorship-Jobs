from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx

from europe_visa_jobs.schemas import NormalizedJob, SourceConfig


class ConnectorError(RuntimeError):
    """Raised when a connector cannot retrieve or parse a public job feed."""


class BaseConnector(ABC):
    def __init__(self, client: httpx.AsyncClient, source: SourceConfig) -> None:
        self.client = client
        self.source = source

    @abstractmethod
    async def fetch_jobs(self) -> list[NormalizedJob]:
        raise NotImplementedError

    async def _get(self, url: str, **kwargs: Any) -> httpx.Response:
        try:
            response = await self.client.get(url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPError as exc:  # pragma: no cover - exact subclasses tested through callers
            raise ConnectorError(f"{self.source.provider}: failed to fetch {url}: {exc}") from exc

from __future__ import annotations

import httpx
import pytest

from europe_visa_jobs.connectors.base import ConnectorError
from europe_visa_jobs.connectors.greenhouse import GreenhouseConnector
from europe_visa_jobs.schemas import SourceConfig


@pytest.mark.asyncio
async def test_connector_wraps_http_errors():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="nope", request=request)

    source = SourceConfig(provider="greenhouse", company_name="Acme", slug="acme")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ConnectorError, match="failed to fetch"):
            await GreenhouseConnector(client, source).fetch_jobs()


@pytest.mark.asyncio
async def test_greenhouse_rejects_invalid_payload():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"wrong": []}, request=request)

    source = SourceConfig(provider="greenhouse", company_name="Acme", slug="acme")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ConnectorError, match="invalid jobs payload"):
            await GreenhouseConnector(client, source).fetch_jobs()

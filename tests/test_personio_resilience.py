from __future__ import annotations

import httpx
import pytest

from europe_visa_jobs.connectors.personio import PersonioConnector
from europe_visa_jobs.discovery.patterns import identify_config, identify_source_url
from europe_visa_jobs.schemas import ATSProvider, SourceConfig


_XML = """<?xml version="1.0" encoding="UTF-8"?>
<positions>
  <position>
    <id>99</id>
    <name>Machine Learning Engineer</name>
    <office>Berlin</office>
    <department>AI</department>
    <employmentType>permanent</employmentType>
    <jobDescriptions>
      <jobDescription>
        <name>About</name>
        <value><![CDATA[<p>Visa sponsorship is available.</p>]]></value>
      </jobDescription>
    </jobDescriptions>
  </position>
</positions>
"""


def _public_dns(monkeypatch) -> None:
    monkeypatch.setattr(
        "europe_visa_jobs.utils.url_security.getaddrinfo",
        lambda host, port: [(2, 1, 6, "", ("93.184.216.34", 0))],
    )


def test_personio_discovery_requires_exact_tenant_host_and_preserves_region():
    result = identify_source_url("https://acme.jobs.personio.com/xml")
    assert result is not None
    assert result.provider is ATSProvider.PERSONIO
    assert result.board_identifier == "acme"
    assert result.api_url == "https://acme.jobs.personio.com/xml"
    assert result.metadata["region"] == "com"

    assert identify_source_url("https://www.vivy.jobs.personio.de/xml") is None


def test_personio_identify_config_rebuilds_provider_owned_endpoint():
    result = identify_config(
        SourceConfig(
            provider=ATSProvider.PERSONIO,
            company_name="Acme",
            slug="acme",
            region="com",
            api_url="https://stale.example.invalid/personio.xml",
        )
    )
    assert result.canonical_url == "https://acme.jobs.personio.com/"
    assert result.api_url == "https://acme.jobs.personio.com/xml"
    assert result.metadata["region"] == "com"


@pytest.mark.asyncio
async def test_personio_connector_ignores_stale_custom_api_url(monkeypatch):
    _public_dns(monkeypatch)
    seen: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(
            200,
            text=_XML,
            headers={"content-type": "application/xml"},
            request=request,
        )

    source = SourceConfig(
        provider=ATSProvider.PERSONIO,
        company_name="Acme",
        slug="acme",
        board_url="https://acme.jobs.personio.com/",
        api_url="https://stale.example.invalid/personio.xml",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        jobs = await PersonioConnector(client, source).fetch_jobs()

    assert len(jobs) == 1
    assert seen == ["https://acme.jobs.personio.com/xml?language=en"]
    assert jobs[0].job_url == "https://acme.jobs.personio.com/job/99"


@pytest.mark.asyncio
async def test_personio_connector_falls_back_between_provider_domains(monkeypatch):
    _public_dns(monkeypatch)
    seen_hosts: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_hosts.append(request.url.host)
        if request.url.host.endswith(".jobs.personio.de"):
            return httpx.Response(404, request=request)
        return httpx.Response(
            200,
            text=_XML,
            headers={"content-type": "application/xml"},
            request=request,
        )

    source = SourceConfig(
        provider=ATSProvider.PERSONIO,
        company_name="Acme",
        slug="acme",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        jobs = await PersonioConnector(client, source).fetch_jobs()

    assert seen_hosts == ["acme.jobs.personio.de", "acme.jobs.personio.com"]
    assert jobs[0].job_url == "https://acme.jobs.personio.com/job/99"

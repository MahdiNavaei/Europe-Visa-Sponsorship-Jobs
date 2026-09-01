from __future__ import annotations

import json

import httpx
import pytest

from europe_visa_jobs.connectors.ashby import AshbyConnector
from europe_visa_jobs.connectors.base import ConnectorError
from europe_visa_jobs.connectors.greenhouse import GreenhouseConnector
from europe_visa_jobs.connectors.lever import LeverConnector
from europe_visa_jobs.connectors.personio import PersonioConnector
from europe_visa_jobs.connectors.workable import WorkableConnector
from europe_visa_jobs.schemas import ATSProvider, JobFamily, SourceConfig


def client_for(payload: object, *, content_type: str = "application/json") -> httpx.AsyncClient:
    body = payload if isinstance(payload, str) else json.dumps(payload)

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=body, headers={"content-type": content_type}, request=request)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_greenhouse_connector_normalizes_job():
    source = SourceConfig(
        provider=ATSProvider.GREENHOUSE,
        company_name="Acme",
        slug="acme",
        default_country="Netherlands",
    )
    payload = {
        "jobs": [
            {
                "id": 123,
                "title": "Senior Machine Learning Engineer",
                "absolute_url": "https://boards.greenhouse.io/acme/jobs/123",
                "location": {"name": "Amsterdam, Netherlands"},
                "content": "<p>We provide visa sponsorship and relocation support.</p>",
                "departments": [{"name": "AI"}],
                "updated_at": "2026-08-20T10:00:00Z",
            }
        ]
    }
    async with client_for(payload) as client:
        jobs = await GreenhouseConnector(client, source).fetch_jobs()
    assert len(jobs) == 1
    assert jobs[0].external_id == "123"
    assert jobs[0].country == "Netherlands"
    assert jobs[0].department == "AI"
    assert jobs[0].job_family == JobFamily.AI_ML
    assert "visa sponsorship" in jobs[0].description
    assert jobs[0].posted_at is None


@pytest.mark.asyncio
async def test_connector_rejects_greenhouse_endpoint_outside_provider_allowlist():
    source = SourceConfig(
        provider=ATSProvider.GREENHOUSE,
        company_name="Acme",
        slug="acme",
        api_url="https://attacker.example/jobs",
    )
    async with client_for({"jobs": []}) as client:
        with pytest.raises(ConnectorError, match="provider allowlist"):
            await GreenhouseConnector(client, source).fetch_jobs()


@pytest.mark.asyncio
async def test_greenhouse_uses_explicit_publication_date_not_update_date():
    source = SourceConfig(provider="greenhouse", company_name="Acme", slug="acme", default_country="Germany")
    payload = {
        "jobs": [
            {
                "id": 124,
                "title": "Backend Engineer",
                "absolute_url": "https://boards.greenhouse.io/acme/jobs/124",
                "location": {"name": "Berlin, Germany"},
                "content": "Visa sponsorship is available.",
                "first_published": "2026-08-01T08:00:00Z",
                "updated_at": "2026-08-20T10:00:00Z",
            }
        ]
    }
    async with client_for(payload) as client:
        jobs = await GreenhouseConnector(client, source).fetch_jobs()
    assert jobs[0].posted_at is not None
    assert jobs[0].posted_at.day == 1


@pytest.mark.asyncio
async def test_lever_connector_uses_eu_endpoint_and_combines_description():
    seen_url = ""

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_url
        seen_url = str(request.url)
        payload = [
            {
                "id": "abc",
                "text": "Backend Engineer",
                "hostedUrl": "https://jobs.eu.lever.co/acme/abc",
                "applyUrl": "https://jobs.eu.lever.co/acme/abc/apply",
                "categories": {"location": "Berlin, Germany", "department": "Engineering", "commitment": "Full-time"},
                "descriptionPlain": "We offer work permit support.",
                "additionalPlain": "International candidates are welcome.",
                "createdAt": 1787216400000,
            }
        ]
        return httpx.Response(200, json=payload, request=request)

    source = SourceConfig(provider="lever", company_name="Acme", slug="acme", region="eu")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        jobs = await LeverConnector(client, source).fetch_jobs()
    assert "api.eu.lever.co" in seen_url
    assert jobs[0].country == "Germany"
    assert "International candidates" in jobs[0].description
    assert jobs[0].employment_type == "Full-time"


@pytest.mark.asyncio
async def test_ashby_connector_skips_unlisted_jobs():
    source = SourceConfig(provider="ashby", company_name="Acme", slug="acme", default_country="Sweden")
    payload = {
        "jobs": [
            {
                "id": "1",
                "title": "Data Scientist",
                "location": "Stockholm, Sweden",
                "descriptionHtml": "<p>Visa sponsorship available.</p>",
                "jobUrl": "https://jobs.ashbyhq.com/acme/1",
                "applyUrl": "https://jobs.ashbyhq.com/acme/1/application",
                "department": "Data",
                "isListed": True,
            },
            {
                "id": "2",
                "title": "Hidden Engineer",
                "location": "Stockholm",
                "jobUrl": "https://jobs.ashbyhq.com/acme/2",
                "isListed": False,
            },
        ]
    }
    async with client_for(payload) as client:
        jobs = await AshbyConnector(client, source).fetch_jobs()
    assert [job.external_id for job in jobs] == ["1"]
    assert jobs[0].job_family == JobFamily.DATA_SCIENCE


@pytest.mark.asyncio
async def test_workable_connector_reads_structured_location():
    source = SourceConfig(provider="workable", company_name="Acme", slug="acme")
    payload = {
        "jobs": [
            {
                "shortcode": "XYZ",
                "title": "Frontend Engineer",
                "location": {"city": "Dublin", "country": "Ireland"},
                "full_description": "<p>We provide immigration support.</p>",
                "application_url": "https://apply.workable.com/acme/j/XYZ/apply",
                "url": "https://apply.workable.com/acme/j/XYZ",
                "published_on": "2026-08-19",
                "employment_type": "Full-time",
                "workplace_type": "hybrid",
            }
        ]
    }
    async with client_for(payload) as client:
        jobs = await WorkableConnector(client, source).fetch_jobs()
    assert jobs[0].country == "Ireland"
    assert jobs[0].location == "Dublin, Ireland"
    assert jobs[0].workplace_type == "hybrid"


@pytest.mark.asyncio
async def test_personio_connector_parses_xml_descriptions():
    source = SourceConfig(
        provider="personio",
        company_name="Acme",
        slug="acme",
        default_country="Germany",
    )
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <positions>
      <position>
        <id>99</id><name>Platform Engineer</name><office>Berlin</office>
        <department>Engineering</department><employmentType>permanent</employmentType>
        <jobDescriptions>
          <jobDescription><name>About</name><value><![CDATA[<p>Visa sponsorship is available.</p>]]></value></jobDescription>
        </jobDescriptions>
      </position>
    </positions>"""
    async with client_for(xml, content_type="application/xml") as client:
        jobs = await PersonioConnector(client, source).fetch_jobs()
    assert jobs[0].external_id == "99"
    assert jobs[0].country == "Germany"
    assert jobs[0].job_family == JobFamily.DEVOPS_CLOUD
    assert "Visa sponsorship" in jobs[0].description


def _public_dns(monkeypatch) -> None:
    monkeypatch.setattr(
        "europe_visa_jobs.utils.url_security.getaddrinfo",
        lambda host, port: [(2, 1, 6, "", ("93.184.216.34", 0))],
    )


def test_personio_discovery_rejects_nested_archive_noise():
    from europe_visa_jobs.discovery.patterns import identify_source_url

    valid = identify_source_url("https://acme.jobs.personio.com/xml")
    assert valid is not None
    assert valid.provider is ATSProvider.PERSONIO
    assert valid.board_identifier == "acme"
    assert valid.api_url == "https://acme.jobs.personio.com/xml"
    assert valid.metadata["region"] == "com"
    assert identify_source_url("https://www.vivy.jobs.personio.de/xml") is None


def test_personio_config_rebuilds_provider_owned_endpoint():
    from europe_visa_jobs.discovery.patterns import identify_config

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
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <positions><position><id>99</id><name>Machine Learning Engineer</name>
    <office>Berlin</office><department>AI</department><employmentType>permanent</employmentType>
    <jobDescriptions><jobDescription><name>About</name>
    <value><![CDATA[<p>Visa sponsorship is available.</p>]]></value>
    </jobDescription></jobDescriptions></position></positions>"""

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(
            200,
            text=xml,
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
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <positions><position><id>99</id><name>Machine Learning Engineer</name>
    <office>Berlin</office><department>AI</department><employmentType>permanent</employmentType>
    <jobDescriptions><jobDescription><name>About</name>
    <value><![CDATA[<p>Visa sponsorship is available.</p>]]></value>
    </jobDescription></jobDescriptions></position></positions>"""

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_hosts.append(request.url.host)
        if request.url.host.endswith(".jobs.personio.de"):
            return httpx.Response(404, request=request)
        return httpx.Response(
            200,
            text=xml,
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

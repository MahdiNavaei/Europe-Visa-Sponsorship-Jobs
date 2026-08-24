from __future__ import annotations

import httpx
import pytest

from europe_visa_jobs.connectors.smartrecruiters import SmartRecruitersConnector
from europe_visa_jobs.connectors.workday import WorkdayConnector
from europe_visa_jobs.db.source_registry import SourceRegistry
from europe_visa_jobs.eligibility import EligibilityEngine
from europe_visa_jobs.ingestion.pipeline import ingest_source
from europe_visa_jobs.schemas import EligibilityStatus, SourceConfig


@pytest.mark.asyncio
async def test_smartrecruiters_fetches_public_job_ad_sections():
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/postings/abc"):
            return httpx.Response(
                200,
                json={
                    "id": "abc",
                    "name": "Platform Engineer",
                    "ref": "https://jobs.smartrecruiters.com/acme/abc",
                    "location": {"city": "Berlin", "country": "Germany"},
                    "jobAd": {
                        "sections": {
                            "jobDescription": {"text": "<p>We provide visa sponsorship.</p>"},
                            "qualifications": {"text": "<p>Python and Kubernetes.</p>"},
                        }
                    },
                },
                request=request,
            )
        return httpx.Response(
            200,
            json={
                "totalFound": 1,
                "content": [
                    {
                        "id": "abc",
                        "name": "Platform Engineer",
                        "location": {"city": "Berlin", "country": "Germany"},
                    }
                ],
            },
            request=request,
        )

    source = SourceConfig(provider="smartrecruiters", company_name="Acme", slug="acme")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        connector = SmartRecruitersConnector(client, source)
        jobs = await connector.fetch_jobs()

    assert connector.completeness == "complete"
    assert connector.detail_completeness == "complete"
    assert "visa sponsorship" in jobs[0].description
    assert "Kubernetes" in jobs[0].description
    assert EligibilityEngine().assess(jobs[0]).status is EligibilityStatus.ELIGIBLE


@pytest.mark.asyncio
async def test_smartrecruiters_failed_detail_is_truthful_and_not_eligible():
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/postings/abc"):
            return httpx.Response(404, request=request)
        return httpx.Response(
            200,
            json={
                "totalFound": 1,
                "content": [{"id": "abc", "name": "Platform Engineer"}],
            },
            request=request,
        )

    source = SourceConfig(provider="smartrecruiters", company_name="Acme", slug="acme")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        connector = SmartRecruitersConnector(client, source)
        jobs = await connector.fetch_jobs()

    assert connector.detail_completeness == "missing"
    assert jobs[0].description == ""
    assert EligibilityEngine().assess(jobs[0]).status is EligibilityStatus.UNKNOWN


@pytest.mark.asyncio
async def test_ingestion_persists_detail_completeness_separately(db_session):
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/postings/abc"):
            return httpx.Response(404, request=request)
        return httpx.Response(
            200,
            json={
                "totalFound": 1,
                "content": [{"id": "abc", "name": "Platform Engineer"}],
            },
            request=request,
        )

    source = SourceConfig(provider="smartrecruiters", company_name="Acme", slug="acme")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await ingest_source(db_session, source, client=client)

    persisted = SourceRegistry(db_session).get("smartrecruiters", "acme")
    assert persisted is not None
    assert persisted.source_metadata["enumeration_completeness"] == "complete"
    assert persisted.source_metadata["detail_completeness"] == "missing"


@pytest.mark.asyncio
async def test_workday_paginates_known_total_and_fetches_cxs_detail():
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "jobPostingInfo": {
                        "jobReqId": "REQ-1",
                        "title": "Backend Engineer",
                        "location": "Paris, France",
                        "externalUrl": "https://acme.wd1.myworkdayjobs.com/job/backend",
                        "jobDescription": "<p>Visa sponsorship is available.</p>",
                        "postedOn": "2026-08-20",
                    }
                },
                request=request,
            )
        return httpx.Response(
            200,
            json={
                "total": 1,
                "jobPostings": [
                    {
                        "jobPostingId": "REQ-1",
                        "title": "Backend Engineer",
                        "locationsText": "Paris, France",
                        "externalPath": "/en-US/job/backend",
                    }
                ],
            },
            request=request,
        )

    source = SourceConfig(
        provider="workday",
        company_name="Acme",
        slug="acme",
        api_url="https://acme.wd1.myworkdayjobs.com/wday/cxs/acme/site/jobs",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        connector = WorkdayConnector(client, source)
        jobs = await connector.fetch_jobs()

    assert connector.completeness == "complete"
    assert connector.detail_completeness == "complete"
    assert jobs[0].description == "Visa sponsorship is available."
    assert EligibilityEngine().assess(jobs[0]).status is EligibilityStatus.ELIGIBLE


@pytest.mark.asyncio
async def test_workday_summary_without_external_path_remains_partial_and_unknown():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"jobPostings": [{"jobPostingId": "REQ-2", "title": "Backend Engineer"}]},
            request=request,
        )

    source = SourceConfig(
        provider="workday",
        company_name="Acme",
        slug="acme",
        api_url="https://acme.wd1.myworkdayjobs.com/wday/cxs/acme/site/jobs",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        connector = WorkdayConnector(client, source)
        jobs = await connector.fetch_jobs()

    assert connector.completeness == "partial"
    assert connector.detail_completeness == "missing"
    assert EligibilityEngine().assess(jobs[0]).status is EligibilityStatus.UNKNOWN


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "external_path",
    [
        "https://attacker.example/job/steal",
        "//attacker.example/job/steal",
        "/en-US/job/../../admin",
        "/en-US/job/%2e%2e/%2e%2e/admin",
        "/en-US/job\\..\\admin",
    ],
)
async def test_workday_rejects_malicious_external_detail_paths(external_path: str):
    get_requests = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal get_requests
        if request.method == "GET":
            get_requests += 1
        return httpx.Response(
            200,
            json={
                "jobPostings": [
                    {
                        "jobPostingId": "REQ-3",
                        "title": "Backend Engineer",
                        "externalPath": external_path,
                    }
                ]
            },
            request=request,
        )

    source = SourceConfig(
        provider="workday",
        company_name="Acme",
        slug="acme",
        api_url="https://acme.wd1.myworkdayjobs.com/wday/cxs/acme/site/jobs",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        connector = WorkdayConnector(client, source)
        jobs = await connector.fetch_jobs()

    assert get_requests == 0
    assert connector.detail_completeness == "missing"
    assert EligibilityEngine().assess(jobs[0]).status is EligibilityStatus.UNKNOWN

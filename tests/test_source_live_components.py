from __future__ import annotations

import asyncio
import json

import httpx
import pytest

import europe_visa_jobs.ingestion.cli as ingestion_cli
from europe_visa_jobs.connectors.ashby import AshbyConnector
from europe_visa_jobs.connectors.recruitee import RecruiteeConnector
from europe_visa_jobs.connectors.smartrecruiters import SmartRecruitersConnector
from europe_visa_jobs.connectors.teamtailor import TeamtailorConnector
from europe_visa_jobs.connectors.workday import WorkdayConnector
from europe_visa_jobs.db.models import Candidate, Job
from europe_visa_jobs.discovery import methods
from europe_visa_jobs.discovery.http import PublicFetchError, PublicResponse, fetch_public
from europe_visa_jobs.discovery.orchestrator import discover_and_validate
from europe_visa_jobs.discovery.patterns import identify_config, identify_source_url
from europe_visa_jobs.discovery.validation import validate_candidate
from europe_visa_jobs.intelligence.matching import CandidateMatcher
from europe_visa_jobs.schemas import ATSProvider, SourceConfig, SourceValidation


def mock_client(payload, *, status=200, content_type="application/json"):
    async def handler(request: httpx.Request) -> httpx.Response:
        body = payload if isinstance(payload, str) else json.dumps(payload)
        return httpx.Response(status, text=body, headers={"content-type": content_type}, request=request)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_additional_provider_connectors_normalize_public_shapes():
    source = SourceConfig(provider=ATSProvider.RECRUITEE, company_name="Acme", slug="acme", default_country="Germany")
    async with mock_client({"offers": [{"id": 1, "title": "Backend Engineer", "location": "Berlin", "url": "https://acme.recruitee.com/o/1"}]}) as client:
        assert (await RecruiteeConnector(client, source).fetch_jobs())[0].country == "Germany"
    smart = SourceConfig(provider=ATSProvider.SMARTRECRUITERS, company_name="Acme", slug="acme")
    async with mock_client({"content": [{"id": "2", "name": "Data Scientist", "location": {"city": "Paris", "country": "France"}, "ref": "https://jobs.example/2"}]}) as client:
        assert (await SmartRecruitersConnector(client, smart).fetch_jobs())[0].country == "France"
    team = SourceConfig(provider=ATSProvider.TEAMTAILOR, company_name="Acme", slug="acme", metadata={"api_token": "token"})
    async with mock_client({"data": [{"id": "3", "attributes": {"title": "ML Engineer", "url": "https://example/3"}}]}) as client:
        assert (await TeamtailorConnector(client, team).fetch_jobs())[0].title == "ML Engineer"
    workday = SourceConfig(provider=ATSProvider.WORKDAY, company_name="Acme", slug="acme", api_url="https://workday.example/jobs")
    async with mock_client({"jobPostings": [{"jobPostingId": "4", "title": "Platform Engineer", "locationsText": "Amsterdam"}]}) as client:
        assert (await WorkdayConnector(client, workday).fetch_jobs())[0].external_id == "4"
    public_team = SourceConfig(provider=ATSProvider.TEAMTAILOR, company_name="Acme", slug="acme")
    html = '<div>job</div><script type="application/ld+json">{"title":"Software Engineer","identifier":"5","url":"https://example/5"}</script>'
    async with mock_client(html, content_type="text/html") as client:
        assert (await TeamtailorConnector(client, public_team).fetch_jobs())[0].external_id == "5"


@pytest.mark.asyncio
async def test_public_fetch_cache_retry_and_blocked(monkeypatch):
    async def no_sleep(_delay):
        return None

    monkeypatch.setattr("europe_visa_jobs.discovery.http.asyncio.sleep", no_sleep)
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, request=request)
        return httpx.Response(200, content=b"ok", headers={"etag": "x"}, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        response = await fetch_public(client, "https://example.test", retries=2)
        assert response.body == b"ok" and calls == 2
    async with mock_client("", status=304) as client:
        response = await fetch_public(client, "https://example.test", retries=1)
        assert response.not_modified
    async with mock_client("blocked", status=403) as client:
        with pytest.raises(PublicFetchError) as error:
            await fetch_public(client, "https://example.test", retries=1)
        assert error.value.category == "blocked"


@pytest.mark.asyncio
async def test_provider_validation_shapes():
    samples = [
        (ATSProvider.GREENHOUSE, {"jobs": [{"id": 1}]}),
        (ATSProvider.LEVER, [{"id": 1}]),
        (ATSProvider.ASHBY, {"jobs": [{"id": 1}]}),
        (ATSProvider.SMARTRECRUITERS, {"content": [{"id": 1}]}),
        (ATSProvider.RECRUITEE, {"offers": [{"id": 1}]}),
        (ATSProvider.WORKABLE, {"jobs": [{"id": 1}]}),
    ]
    for provider, payload in samples:
        candidate = identify_source_url({
            ATSProvider.GREENHOUSE: "https://boards.greenhouse.io/acme",
            ATSProvider.LEVER: "https://jobs.lever.co/acme",
            ATSProvider.ASHBY: "https://jobs.ashbyhq.com/acme",
            ATSProvider.SMARTRECRUITERS: "https://jobs.smartrecruiters.com/acme",
            ATSProvider.RECRUITEE: "https://acme.recruitee.com",
            ATSProvider.WORKABLE: "https://apply.workable.com/acme",
        }[provider])
        assert candidate is not None
        async with mock_client(payload) as client:
            result = await validate_candidate(client, candidate)
        assert result.valid and result.job_count == 1
    personio = identify_source_url("https://acme.jobs.personio.de/xml")
    assert personio is not None
    async with mock_client("<positions><position><id>1</id></position></positions>", content_type="application/xml") as client:
        assert (await validate_candidate(client, personio)).valid
    team = identify_source_url("https://acme.teamtailor.com/jobs")
    assert team is not None
    async with mock_client("<html>job listing</html>", content_type="text/html") as client:
        assert (await validate_candidate(client, team)).valid
    workday = identify_source_url("https://acme.wd1.myworkdayjobs.com/en-US/acme")
    assert workday is not None
    async with mock_client({"jobPostings": [{"title": "Engineer"}]}) as client:
        assert (await validate_candidate(client, workday)).valid
    async with mock_client("not-json") as client:
        invalid = await validate_candidate(client, identify_source_url("https://jobs.lever.co/acme"))
        assert not invalid.valid and invalid.error_category == "invalid_response"


@pytest.mark.asyncio
async def test_ashby_hosted_page_fallback_for_api_block():
    app_data = {
        "organization": {"name": "Acme"},
        "jobBoard": {"jobPostings": [{"id": "1", "title": "Engineer"}]},
    }
    html = f"window.__appData = {json.dumps(app_data)};"
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if "api.ashbyhq.com" in str(request.url):
            return httpx.Response(403, text="blocked", request=request)
        return httpx.Response(200, text=html, headers={"content-type": "text/html"}, request=request)

    candidate = identify_source_url("https://jobs.ashbyhq.com/acme")
    assert candidate is not None
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await validate_candidate(client, candidate)
    assert result.valid and result.job_count == 1 and calls == 2

    source = SourceConfig(
        provider=ATSProvider.ASHBY,
        company_name="Acme",
        slug="acme",
        board_url="https://jobs.ashbyhq.com/acme",
        api_url="https://api.ashbyhq.com/posting-api/job-board/acme",
    )
    calls = 0
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        jobs = await AshbyConnector(client, source).fetch_jobs()
    assert jobs[0].title == "Engineer"


@pytest.mark.asyncio
async def test_index_methods_and_orchestrator_are_additive(monkeypatch, db_session):
    async def fake_fetch(client, url, **kwargs):
        if "collinfo" in url:
            return PublicResponse(200, {}, b'[{"cdx-api":"https://cc.example/index"}]', 1)
        if "web.archive" in url:
            return PublicResponse(200, {}, json.dumps([["original"], ["https://boards.greenhouse.io/acme/jobs/1"]]).encode(), 1)
        if "urlscan" in url:
            return PublicResponse(200, {}, json.dumps({"results": [{"page": {"url": "https://boards.greenhouse.io/acme"}}]}).encode(), 1)
        return PublicResponse(200, {}, b'{"url":"https://boards.greenhouse.io/acme"}\n', 1)

    monkeypatch.setattr(methods, "fetch_public", fake_fetch)
    async with httpx.AsyncClient() as client:
        assert await methods.wayback_candidates(client, ATSProvider.GREENHOUSE, max_rows=2)
        assert await methods.common_crawl_candidates(client, ATSProvider.GREENHOUSE, max_pages=1)
        assert await methods.urlscan_candidates(client, ATSProvider.GREENHOUSE)

    page_calls = 0

    async def paged_urlscan(client, url, **kwargs):
        nonlocal page_calls
        page_calls += 1
        if "search_after=" in url:
            payload = {"results": [], "has_more": False}
        else:
            payload = {
                "results": [{"page": {"url": "https://boards.greenhouse.io/paged"}, "sort": [1, "cursor"]}],
                "has_more": True,
            }
        return PublicResponse(200, {}, json.dumps(payload).encode(), 1)

    monkeypatch.setattr(methods, "fetch_public", paged_urlscan)
    stats: dict[str, int] = {}
    async with httpx.AsyncClient() as client:
        assert await methods.urlscan_candidates(client, ATSProvider.GREENHOUSE, stats=stats, max_pages=2)
    assert page_calls == 4 and stats["raw"] == 2

    async def empty_index_fetch(client, url, **kwargs):
        return PublicResponse(200, {}, b"[]", 1)

    monkeypatch.setattr(methods, "fetch_public", empty_index_fetch)
    async with httpx.AsyncClient() as client:
        with pytest.raises(ValueError, match="no collection index"):
            await methods.common_crawl_index(client)

    async def fake_validate(client, candidate):
        return SourceValidation(valid=True, provider=candidate.provider, board_identifier=candidate.board_identifier, canonical_url=candidate.canonical_url, job_count=2, http_status=200)

    monkeypatch.setattr("europe_visa_jobs.discovery.orchestrator.load_sources", lambda path: [SourceConfig(provider="greenhouse", company_name="Acme", slug="acme")])
    monkeypatch.setattr("europe_visa_jobs.discovery.orchestrator.wayback_candidates", lambda *args, **kwargs: asyncio.sleep(0, result=[]))
    monkeypatch.setattr("europe_visa_jobs.discovery.orchestrator.common_crawl_candidates", lambda *args, **kwargs: asyncio.sleep(0, result=[]))
    monkeypatch.setattr("europe_visa_jobs.discovery.orchestrator.urlscan_candidates", lambda *args, **kwargs: asyncio.sleep(0, result=[]))
    monkeypatch.setattr("europe_visa_jobs.discovery.orchestrator.validate_candidate", fake_validate)
    monkeypatch.setattr(
        "europe_visa_jobs.discovery.orchestrator.get_settings",
        lambda: type("Settings", (), {"discovery_timeout_seconds": 2, "discovery_concurrency": 1, "discovery_common_crawl_max_pages": 1, "discovery_checkpoint_size": 1})(),
    )
    result = await discover_and_validate(db_session, providers={ATSProvider.GREENHOUSE}, methods={"manual"}, limit=1)
    assert result["validated_count"] == 1
    cached = await discover_and_validate(db_session, providers={ATSProvider.GREENHOUSE}, methods={"manual"}, limit=1)
    assert cached["candidate_count"] == 0 and cached["skipped_cached_count"] == 1


@pytest.mark.asyncio
async def test_orchestrator_default_universe_includes_all_provider_boundaries(monkeypatch, db_session):
    configs = [
        SourceConfig(provider=provider, company_name=provider.value, slug=f"{provider.value}-board", careers_url="https://careers.example/board")
        for provider in ATSProvider
    ]

    async def fake_validate(client, candidate):
        return SourceValidation(
            valid=True,
            provider=candidate.provider,
            board_identifier=candidate.board_identifier,
            canonical_url=candidate.canonical_url,
            job_count=0,
            http_status=200,
        )

    monkeypatch.setattr("europe_visa_jobs.discovery.orchestrator.load_sources", lambda path: configs)
    monkeypatch.setattr("europe_visa_jobs.discovery.orchestrator.validate_candidate", fake_validate)
    monkeypatch.setattr(
        "europe_visa_jobs.discovery.orchestrator.get_settings",
        lambda: type("Settings", (), {"discovery_timeout_seconds": 2, "discovery_concurrency": 2, "discovery_common_crawl_max_pages": 1, "discovery_checkpoint_size": 1})(),
    )
    result = await discover_and_validate(db_session, methods={"manual"}, limit=len(configs))
    assert result["candidate_count"] == len(ATSProvider)
    assert result["validated_count"] == len(ATSProvider)


def test_remaining_provider_patterns_and_config_fallbacks():
    urls = [
        "https://acme.teamtailor.com/jobs", "https://acme.recruitee.com", "https://acme.wd1.myworkdayjobs.com/en-US/acme",
        "https://apply.workable.com/acme", "https://acme.jobs.personio.com/xml", "https://boards-api.greenhouse.io/v1/boards/acme/jobs",
    ]
    assert all(identify_source_url(url) for url in urls)
    for provider in ATSProvider:
        config = SourceConfig(provider=provider, company_name="Acme", slug="acme", careers_url="https://careers.example/acme")
        assert identify_config(config).provider is provider


def test_remote_country_matching_respects_geography():
    candidate = Candidate(preferred_countries=["Germany"], excluded_locations=[])
    european = Job(location="Remote - EU", country=None)
    us_only = Job(location="Remote - US only", country=None)
    european_score, european_reasons, european_warnings = CandidateMatcher._country_match(candidate, european)
    us_score, _, us_warnings = CandidateMatcher._country_match(candidate, us_only)
    assert european_score > 0 and european_reasons and not european_warnings
    assert us_score == 0 and us_warnings


def test_source_cli_exposes_bounded_batch_and_force_options():
    args = ingestion_cli._parser().parse_args(
        ["sources", "discover", "--batch-size", "17", "--force", "--provider", "lever"]
    )
    assert args.batch_size == 17 and args.force and args.provider == ["lever"]


@pytest.mark.asyncio
async def test_retry_failed_cli_path(monkeypatch):
    class Settings:
        request_timeout_seconds = 1
        database_url = "sqlite:///tmp.db"
        ingestion_concurrency = 1

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    async def fake_ingest(session, source, *, client):
        return type("Run", (), {"fetched_count": 1, "stored_count": 1, "status": "success"})()

    monkeypatch.setattr(ingestion_cli, "get_settings", lambda: Settings())
    monkeypatch.setattr(ingestion_cli.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(ingestion_cli, "SessionLocal", lambda: Session())
    monkeypatch.setattr(ingestion_cli, "ingest_source", fake_ingest)
    source = SourceConfig(provider=ATSProvider.GREENHOUSE, company_name="Acme", slug="acme")
    await ingestion_cli._ingest_failed([source])

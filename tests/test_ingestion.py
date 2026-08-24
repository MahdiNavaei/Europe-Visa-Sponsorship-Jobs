from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import pytest

import europe_visa_jobs.ingestion.cli as ingestion_cli
import europe_visa_jobs.ingestion.pipeline as pipeline
from europe_visa_jobs.db.models import IngestionRun
from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.schemas import ATSProvider, NormalizedJob, SourceConfig


class FakeConnector:
    async def fetch_jobs(self):
        return [
            NormalizedJob(
                external_id="1",
                provider=ATSProvider.GREENHOUSE,
                source_slug="acme",
                company_name="Acme",
                title="Machine Learning Engineer",
                description="Visa sponsorship is available.",
                location="Berlin, Germany",
                country="Germany",
                apply_url="https://example.com/1",
            ),
            NormalizedJob(
                external_id="2",
                provider=ATSProvider.GREENHOUSE,
                source_slug="acme",
                company_name="Acme",
                title="Sales Manager",
                description="Visa sponsorship is available.",
                location="Berlin, Germany",
                country="Germany",
                apply_url="https://example.com/2",
            ),
        ]


def test_company_upsert_deduplicates_unknown_country(db_session):
    repo = Repository(db_session)
    first = repo.upsert_company("Acme GmbH", None, career_url="https://example.com/jobs")
    second = repo.upsert_company("Acme GmbH", None, sponsor_verified=True)

    assert first.id == second.id
    assert second.country is None
    assert second.country_key == ""
    assert second.sponsor_verified is True


@pytest.mark.asyncio
async def test_ingestion_filters_non_tech_roles_and_persists_assessment(db_session, monkeypatch):
    source = SourceConfig(provider="greenhouse", company_name="Acme", slug="acme", default_country="Germany")
    monkeypatch.setattr(pipeline, "build_connector", lambda client, source: FakeConnector())
    async with httpx.AsyncClient() as client:
        run = await pipeline.ingest_source(db_session, source, client=client)

    assert run.status == "success"
    assert run.fetched_count == 2
    assert run.stored_count == 1
    jobs = Repository(db_session).list_jobs()
    assert len(jobs) == 1
    assert jobs[0].title == "Machine Learning Engineer"


class FailingConnector:
    async def fetch_jobs(self):
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_ingestion_records_failure(db_session, monkeypatch):
    source = SourceConfig(provider="greenhouse", company_name="Acme", slug="acme")
    monkeypatch.setattr(pipeline, "build_connector", lambda client, source: FailingConnector())
    async with httpx.AsyncClient() as client:
        with pytest.raises(RuntimeError, match="boom"):
            await pipeline.ingest_source(db_session, source, client=client)
    runs = db_session.query(IngestionRun).all()
    assert len(runs) == 1
    assert runs[0].status == "failed"


@pytest.mark.asyncio
async def test_failed_refresh_does_not_deactivate_previous_jobs(db_session, monkeypatch):
    source = SourceConfig(provider="greenhouse", company_name="Acme", slug="acme", default_country="Germany")
    monkeypatch.setattr(pipeline, "build_connector", lambda client, source: FakeConnector())
    async with httpx.AsyncClient() as client:
        await pipeline.ingest_source(db_session, source, client=client)

    stored = Repository(db_session).list_jobs()
    assert len(stored) == 1
    assert stored[0].active is True

    monkeypatch.setattr(pipeline, "build_connector", lambda client, source: FailingConnector())
    async with httpx.AsyncClient() as client:
        with pytest.raises(RuntimeError, match="boom"):
            await pipeline.ingest_source(db_session, source, client=client)

    remaining = Repository(db_session).list_jobs()
    assert len(remaining) == 1
    assert remaining[0].active is True


@pytest.mark.asyncio
async def test_successful_refresh_closes_and_reactivates_jobs_without_duplicates(db_session, monkeypatch):
    source = SourceConfig(provider="greenhouse", company_name="Acme", slug="acme", default_country="Germany")
    snapshots = [
        ["1", "2"],
        ["1"],
        ["1", "2"],
    ]

    class SequencedConnector:
        async def fetch_jobs(self):
            ids = snapshots.pop(0)
            return [
                NormalizedJob(
                    external_id=external_id,
                    provider=ATSProvider.GREENHOUSE,
                    source_slug="acme",
                    company_name="Acme",
                    title="Backend Engineer",
                    description="Sponsorship policy is available.",
                    location="Berlin, Germany",
                    country="Germany",
                    apply_url=f"https://example.com/{external_id}",
                )
                for external_id in ids
            ]

    monkeypatch.setattr(pipeline, "build_connector", lambda client, source: SequencedConnector())
    repo = Repository(db_session)
    async with httpx.AsyncClient() as client:
        await pipeline.ingest_source(db_session, source, client=client)
        await pipeline.ingest_source(db_session, source, client=client)
        assert repo.get_job(2).active is False
        await pipeline.ingest_source(db_session, source, client=client)

    assert repo.count_jobs(status=None) == 2
    assert repo.get_job(2).active is True


class DummySessionContext:
    def __enter__(self):
        return object()

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyAsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_ingestion_batch_continues_after_one_source_fails(monkeypatch, tmp_path):
    sources = [
        SourceConfig(provider="greenhouse", company_name="Broken", slug="broken"),
        SourceConfig(provider="greenhouse", company_name="Healthy", slug="healthy"),
    ]
    processed: list[str] = []

    async def fake_ingest_source(session, source, *, client):
        del session, client
        processed.append(source.slug)
        if source.slug == "broken":
            raise RuntimeError("upstream timeout")
        return SimpleNamespace(fetched_count=3, stored_count=2, status="success")

    monkeypatch.setattr(ingestion_cli, "load_sources", lambda path: sources)
    monkeypatch.setattr(ingestion_cli, "get_settings", lambda: SimpleNamespace(request_timeout_seconds=1))
    monkeypatch.setattr(ingestion_cli, "SessionLocal", lambda: DummySessionContext())
    monkeypatch.setattr(ingestion_cli, "ingest_source", fake_ingest_source)
    monkeypatch.setattr(ingestion_cli.httpx, "AsyncClient", lambda **kwargs: DummyAsyncClient())

    with pytest.raises(RuntimeError, match="1 source\(s\) failed"):
        await ingestion_cli._ingest("unused.json")

    assert processed == ["broken", "healthy"]

    processed.clear()
    summary_path = tmp_path / "ingestion-summary.json"
    summary = await ingestion_cli._ingest(
        "unused.json",
        allow_partial=True,
        summary_file=str(summary_path),
    )
    assert processed == ["broken", "healthy"]
    assert summary == {
        "sources_total": 2,
        "sources_successful": 1,
        "sources_failed": 1,
        "failed_sources": ["greenhouse:broken"],
        "partial_success": True,
    }
    assert json.loads(summary_path.read_text()) == summary

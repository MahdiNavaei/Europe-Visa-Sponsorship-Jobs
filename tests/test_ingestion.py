from __future__ import annotations

import httpx
import pytest

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

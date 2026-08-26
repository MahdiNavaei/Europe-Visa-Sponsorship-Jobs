from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import europe_visa_jobs.ingestion.cli as ingestion_cli
import europe_visa_jobs.ingestion.pipeline as pipeline
from europe_visa_jobs.api.app import app
from europe_visa_jobs.catalog.delivery import publish_catalog, sync_catalog
from europe_visa_jobs.db.models import Base, CandidateJobState, Job
from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.db.session import get_db
from europe_visa_jobs.db.source_registry import SourceRegistry
from europe_visa_jobs.schemas import (
    ATSProvider,
    CandidateCreate,
    JobFamily,
    NormalizedJob,
    SourceConfig,
)

MANIFEST_URL = (
    "https://raw.githubusercontent.com/MahdiNavaei/Europe-Visa-Sponsorship-Jobs/"
    "market-data/data/catalog/latest.json"
)


def _job(external_id: str, *, title: str, description: str) -> NormalizedJob:
    return NormalizedJob(
        external_id=external_id,
        provider=ATSProvider.GREENHOUSE,
        source_slug="recurring-board",
        company_name="Recurring Board GmbH",
        title=title,
        description=description,
        location="Berlin, Germany",
        country="Germany",
        apply_url=f"https://boards.greenhouse.io/recurring-board/jobs/{external_id}",
        posted_at=datetime(2026, 8, 26, 8, 0, tzinfo=UTC),
        job_family=JobFamily.AI_ML,
    )


def _catalog_http_client(catalog_dir: Path) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        path = catalog_dir / Path(request.url.path).name
        if not path.is_file():
            return httpx.Response(404, request=request)
        body = path.read_bytes()
        return httpx.Response(
            200,
            content=body,
            headers={"Content-Length": str(len(body))},
            request=request,
        )

    return httpx.Client(transport=httpx.MockTransport(handler))


def _prepare_verified_source(factory) -> None:
    with factory() as session:
        source = SourceRegistry(session).import_config(
            SourceConfig(
                provider=ATSProvider.GREENHOUSE,
                company_name="Recurring Board GmbH",
                slug="recurring-board",
                default_country="Germany",
                enabled=True,
            )
        )
        source.enabled = True
        source.status = "healthy"
        source.validation_state = "verified"
        source.verified_at = datetime.now(UTC) - timedelta(days=30)
        session.commit()


def _make_due(factory) -> None:
    with factory() as session:
        source = SourceRegistry(session).get("greenhouse", "recurring-board")
        assert source is not None and source.last_ingested_at is not None
        source.last_ingested_at = datetime.now(UTC) - timedelta(hours=19)
        session.commit()


async def _run_due_ingestion(monkeypatch, factory, state: dict[str, object]) -> dict[str, object]:
    class FixtureConnector:
        detail_completeness = "complete"

        def __init__(self) -> None:
            self.completeness = str(state["completeness"])
            self.last_response_headers: dict[str, str] = {}
            self.last_fetch_duration_ms = 1

        async def fetch_jobs(self):
            state["fetches"] = int(state["fetches"]) + 1
            return list(state["jobs"])

    monkeypatch.setattr(pipeline, "build_connector", lambda client, source: FixtureConnector())
    monkeypatch.setattr(ingestion_cli, "SessionLocal", factory)
    monkeypatch.setattr(
        ingestion_cli,
        "get_settings",
        lambda: SimpleNamespace(
            request_timeout_seconds=1,
            ingestion_concurrency=1,
            ingestion_refresh_interval_hours=18,
            ingestion_refresh_stale_share=0.75,
        ),
    )
    return await ingestion_cli._ingest(
        None,
        registry_mode=True,
        due_for_refresh=True,
        limit=150,
    )


def _client_factory(path: Path):
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


@pytest.mark.asyncio
async def test_same_ingested_source_new_and_changed_job_reaches_existing_client(
    session_factory, tmp_path: Path, monkeypatch
) -> None:
    _prepare_verified_source(session_factory)
    state: dict[str, object] = {
        "jobs": [
            _job(
                "job-a",
                title="Machine Learning Engineer",
                description="Candidates must already have work authorization; visa sponsorship is not available.",
            )
        ],
        "completeness": "complete",
        "fetches": 0,
    }

    first_summary = await _run_due_ingestion(monkeypatch, session_factory, state)
    assert first_summary["sources_successful"] == 1
    with session_factory() as central:
        source = SourceRegistry(central).get("greenhouse", "recurring-board")
        assert source is not None and source.last_ingested_at is not None
        first = central.query(Job).filter_by(external_id="job-a").one()
        assert first.eligibility_status == "rejected"
        publish_catalog(central, tmp_path / "catalog", dataset_version="n")

    client_engine, client_factory = _client_factory(tmp_path / "existing-client.sqlite")
    with _catalog_http_client(tmp_path / "catalog") as http, client_factory() as client_session:
        sync_catalog(client_session, MANIFEST_URL, tmp_path / "cache", client=http)
        repo = Repository(client_session)
        candidate = repo.create_candidate(
            CandidateCreate(
                name="Existing User",
                target_roles=["Machine Learning Engineer"],
                skills=["Python"],
                preferred_countries=["Germany"],
            )
        )
        client_job = client_session.query(Job).filter_by(external_id="job-a").one()
        client_session.add(
            CandidateJobState(
                candidate_id=candidate.id,
                job_id=client_job.id,
                saved=True,
                application_status="applied",
                note="Keep this local note",
            )
        )
        client_session.commit()
        candidate_id = candidate.id

    _make_due(session_factory)
    state["jobs"] = [
        _job(
            "job-a",
            title="Senior Machine Learning Engineer",
            description="Visa sponsorship and relocation support are available. Python is required.",
        ),
        _job(
            "job-b",
            title="Machine Learning Platform Engineer",
            description="We provide visa sponsorship and relocation support. Python is required.",
        ),
    ]
    second_summary = await _run_due_ingestion(monkeypatch, session_factory, state)
    assert second_summary["selection_mode"] == "due_for_refresh"
    assert second_summary["sources_successful"] == 1
    assert state["fetches"] == 2

    with session_factory() as central:
        assert central.query(Job).filter_by(external_id="job-a").count() == 1
        changed = central.query(Job).filter_by(external_id="job-a").one()
        added = central.query(Job).filter_by(external_id="job-b").one()
        assert changed.title == "Senior Machine Learning Engineer"
        assert changed.eligibility_status == "eligible"
        assert added.eligibility_status == "eligible"
        publish_catalog(central, tmp_path / "catalog", dataset_version="n-plus-one")

    with _catalog_http_client(tmp_path / "catalog") as http, client_factory() as client_session:
        sync_catalog(client_session, MANIFEST_URL, tmp_path / "cache", client=http)
        candidate = Repository(client_session).get_candidate(candidate_id)
        assert candidate is not None and candidate.name == "Existing User"
        changed = client_session.query(Job).filter_by(external_id="job-a").one()
        added = client_session.query(Job).filter_by(external_id="job-b").one()
        assert changed.title == "Senior Machine Learning Engineer"
        assert changed.eligibility_status == "eligible"
        assert added.active and added.eligibility_status == "eligible"
        tracking = client_session.query(CandidateJobState).filter_by(job_id=changed.id).one()
        assert tracking.saved is True
        assert tracking.application_status == "applied"
        assert tracking.note == "Keep this local note"
        client_session.commit()

    def override_db():
        with client_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        api = TestClient(app)
        jobs = api.get("/api/v1/jobs", params={"query": "Machine Learning Platform"})
        assert jobs.status_code == 200
        assert [item["external_id"] for item in jobs.json()] == ["job-b"]
        recommendations = api.get(f"/api/v1/recommendations/{candidate_id}")
        assert recommendations.status_code == 200
        assert "job-b" in {item["job"]["external_id"] for item in recommendations.json()}
    finally:
        app.dependency_overrides.clear()
        client_engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("second_completeness", "expected_active"),
    [("complete", False), ("partial", True)],
)
async def test_due_refresh_preserves_provider_completeness_on_catalog_sync(
    session_factory,
    tmp_path: Path,
    monkeypatch,
    second_completeness: str,
    expected_active: bool,
) -> None:
    _prepare_verified_source(session_factory)
    state: dict[str, object] = {
        "jobs": [
            _job("job-a", title="Machine Learning Engineer", description="Visa sponsorship is available."),
            _job("job-b", title="Data Platform Engineer", description="Visa sponsorship is available."),
        ],
        "completeness": "complete",
        "fetches": 0,
    }
    await _run_due_ingestion(monkeypatch, session_factory, state)
    with session_factory() as central:
        publish_catalog(central, tmp_path / "catalog", dataset_version="n")

    client_engine, client_factory = _client_factory(
        tmp_path / f"client-{second_completeness}.sqlite"
    )
    with _catalog_http_client(tmp_path / "catalog") as http, client_factory() as client_session:
        sync_catalog(client_session, MANIFEST_URL, tmp_path / "cache", client=http)
        client_session.commit()
        assert client_session.query(Job).filter_by(external_id="job-b").one().active

    _make_due(session_factory)
    state["jobs"] = [
        _job("job-a", title="Machine Learning Engineer", description="Visa sponsorship is available.")
    ]
    state["completeness"] = second_completeness
    await _run_due_ingestion(monkeypatch, session_factory, state)
    assert state["fetches"] == 2
    with session_factory() as central:
        central_removed = central.query(Job).filter_by(external_id="job-b").one()
        assert central_removed.active is expected_active
        publish_catalog(central, tmp_path / "catalog", dataset_version="n-plus-one")

    with _catalog_http_client(tmp_path / "catalog") as http, client_factory() as client_session:
        sync_catalog(client_session, MANIFEST_URL, tmp_path / "cache", client=http)
        assert client_session.query(Job).filter_by(external_id="job-b").one().active is expected_active
        client_session.commit()
    client_engine.dispose()

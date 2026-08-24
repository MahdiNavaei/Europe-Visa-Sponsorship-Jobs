from __future__ import annotations

import gzip
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import europe_visa_jobs.catalog.delivery as delivery
from europe_visa_jobs.catalog.delivery import import_catalog, publish_catalog, sync_catalog
from europe_visa_jobs.db.models import Base, CandidateJobState, Job
from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.db.source_registry import SourceRegistry
from europe_visa_jobs.eligibility import EligibilityEngine
from europe_visa_jobs.schemas import (
    ATSProvider,
    CandidateCreate,
    JobFamily,
    NormalizedJob,
    SourceConfig,
)


def _job(external_id: str, title: str = "Backend Engineer") -> NormalizedJob:
    return NormalizedJob(
        external_id=external_id,
        provider=ATSProvider.GREENHOUSE,
        source_slug="acme",
        company_name="Acme",
        title=title,
        description="Visa sponsorship available.",
        location="Berlin, Germany",
        country="Germany",
        apply_url=f"https://example.com/{external_id}",
        job_family=JobFamily.BACKEND,
    )


def test_catalog_manifest_is_hash_verified_and_atomic(db_session, tmp_path: Path) -> None:
    repo = Repository(db_session)
    item = _job("one")
    item.posted_at = datetime.now(UTC)
    repo.upsert_job(item, EligibilityEngine().assess(item))
    SourceRegistry(db_session).import_config(SourceConfig(provider="greenhouse", company_name="Acme", slug="acme"))
    db_session.commit()
    manifest = publish_catalog(db_session, tmp_path, dataset_version="n1")
    assert manifest.sha256
    assert json.loads((tmp_path / "latest.json").read_text())['payload'] == "catalog-n1.json.gz"

    import_catalog(db_session, tmp_path / "latest.json")

    tampered = bytearray((tmp_path / manifest.payload).read_bytes())
    tampered[-1] ^= 1
    (tmp_path / manifest.payload).write_bytes(tampered)
    with pytest.raises(ValueError, match="hash mismatch"):
        import_catalog(db_session, tmp_path / "latest.json")


def test_catalog_import_preserves_candidate_state(session_factory, tmp_path: Path) -> None:
    with session_factory() as source_session:
        repo = Repository(source_session)
        job = repo.upsert_job(_job("one"), EligibilityEngine().assess(_job("one")))
        candidate = repo.create_candidate(__import__("europe_visa_jobs.schemas", fromlist=["CandidateCreate"]).CandidateCreate(name="Mahdi", target_roles=["Backend Engineer"]))
        from europe_visa_jobs.db.models import CandidateJobState
        source_session.add(CandidateJobState(candidate_id=candidate.id, job_id=job.id, note="keep", saved=True))
        source_session.commit()
        publish_catalog(source_session, tmp_path, dataset_version="n1")

    with session_factory() as client_session:
        candidate_repo = Repository(client_session)
        candidate = candidate_repo.create_candidate(__import__("europe_visa_jobs.schemas", fromlist=["CandidateCreate"]).CandidateCreate(name="Mahdi", target_roles=["Backend Engineer"]))
        import_catalog(client_session, tmp_path / "latest.json")
        assert client_session.get(type(candidate), candidate.id) is not None


def test_catalog_update_n_n_plus_one_n_plus_two_preserves_state_and_partial_jobs(session_factory, tmp_path: Path) -> None:
    client_engine = create_engine(f"sqlite:///{tmp_path / 'client.sqlite'}")
    Base.metadata.create_all(client_engine)
    client_factory = sessionmaker(bind=client_engine, class_=Session, expire_on_commit=False)
    with session_factory() as source_session:
        repo = Repository(source_session)
        first = repo.upsert_job(_job("one"), EligibilityEngine().assess(_job("one")))
        SourceRegistry(source_session).import_config(SourceConfig(provider="greenhouse", company_name="Acme", slug="acme"))
        source_session.commit()
        publish_catalog(source_session, tmp_path, dataset_version="n")

        repo.upsert_job(_job("two", title="Platform Engineer"), EligibilityEngine().assess(_job("two", title="Platform Engineer")))
        first.description = "Updated JD with visa sponsorship and relocation support."
        source_session.commit()
        publish_catalog(source_session, tmp_path, dataset_version="n1")

    with client_factory() as client_session:
        import_catalog(client_session, tmp_path / "latest.json")
        candidate = Repository(client_session).create_candidate(CandidateCreate(name="Mahdi", target_roles=["Backend Engineer"]))
        client_job = client_session.query(Job).filter_by(external_id="one").one()
        client_session.add(CandidateJobState(candidate_id=candidate.id, job_id=client_job.id, saved=True, note="keep"))
        client_session.commit()
        assert client_job.description.startswith("Updated JD")
        assert client_session.query(Job).filter_by(external_id="two").one()

    with session_factory() as source_session:
        source = SourceRegistry(source_session).get("greenhouse", "acme")
        assert source is not None
        source.source_metadata = {"enumeration_completeness": "partial"}
        source_session.query(Job).filter_by(external_id="one").update({"active": False})
        source_session.commit()
        publish_catalog(source_session, tmp_path, dataset_version="n2")

    with client_factory() as client_session:
        import_catalog(client_session, tmp_path / "latest.json")
        retained = client_session.query(Job).filter_by(external_id="one").one()
        state = client_session.query(CandidateJobState).filter_by(job_id=retained.id).one()
        assert retained.active
        assert state.note == "keep"
    client_engine.dispose()


@pytest.mark.parametrize("transition", ["complete_empty", "disabled", "removed"])
def test_catalog_authoritative_source_transitions_deactivate_stale_jobs(
    session_factory, tmp_path: Path, transition: str
) -> None:
    client_engine = create_engine(f"sqlite:///{tmp_path / f'client-{transition}.sqlite'}")
    Base.metadata.create_all(client_engine)
    client_factory = sessionmaker(bind=client_engine, class_=Session, expire_on_commit=False)
    with session_factory() as source_session:
        repo = Repository(source_session)
        repo.upsert_job(_job("one"), EligibilityEngine().assess(_job("one")))
        source = SourceRegistry(source_session).import_config(
            SourceConfig(provider="greenhouse", company_name="Acme", slug="acme")
        )
        source.enabled = True
        source.source_metadata = {"enumeration_completeness": "complete"}
        source_session.commit()
        publish_catalog(source_session, tmp_path, dataset_version="n")

    with client_factory() as client_session:
        import_catalog(client_session, tmp_path / "latest.json")
        client_session.commit()
        assert client_session.query(Job).filter_by(external_id="one").one().active

    with session_factory() as source_session:
        source = SourceRegistry(source_session).get("greenhouse", "acme")
        assert source is not None
        source_session.query(Job).filter_by(external_id="one").update({"active": False})
        if transition == "disabled":
            source.enabled = False
        elif transition == "removed":
            source_session.delete(source)
        source_session.commit()
        publish_catalog(source_session, tmp_path, dataset_version="n1")

    with client_factory() as client_session:
        import_catalog(client_session, tmp_path / "latest.json")
        assert not client_session.query(Job).filter_by(external_id="one").one().active
    client_engine.dispose()


def test_catalog_publication_redacts_nested_source_secrets(db_session, tmp_path: Path) -> None:
    source = SourceRegistry(db_session).import_config(
        SourceConfig(
            provider="greenhouse",
            company_name="Acme",
            slug="acme",
            metadata={
                "api_token": "never-publish",
                "nested": {
                    "client_secret": "also-private",
                    "signing_key": "private",
                    "cookie": "session=private",
                    "region": "eu",
                },
            },
        )
    )
    source.enabled = True
    source.verified_at = datetime(2026, 8, 23, 10, 0, tzinfo=UTC)
    source.last_success_at = datetime(2026, 8, 24, 10, 0, tzinfo=UTC)
    source.api_url = "https://user:pass@example.com/jobs?api_key=private&locale=en#token"
    db_session.commit()
    manifest = publish_catalog(db_session, tmp_path, dataset_version="redacted")
    payload = json.loads(gzip.decompress((tmp_path / manifest.payload).read_bytes()))
    metadata = payload["sources"][0]["source_metadata"]
    assert "api_token" not in metadata
    assert metadata["nested"] == {"region": "eu"}
    assert payload["sources"][0]["api_url"] == "https://example.com/jobs?locale=en"
    assert payload["sources"][0]["verified_at"] == "2026-08-23T10:00:00+00:00"
    assert payload["sources"][0]["last_success_at"] == "2026-08-24T10:00:00+00:00"


def test_catalog_round_trips_eligibility_assessment_freshness(session_factory, tmp_path: Path) -> None:
    assessed_at = datetime(2026, 8, 24, 8, 30, tzinfo=UTC)
    with session_factory() as source_session:
        source = SourceRegistry(source_session).import_config(
            SourceConfig(provider="greenhouse", company_name="Acme", slug="acme")
        )
        source.enabled = True
        assessment = EligibilityEngine().assess(_job("fresh"))
        assessment.assessed_at = assessed_at
        Repository(source_session).upsert_job(_job("fresh"), assessment)
        source_session.commit()
        publish_catalog(source_session, tmp_path, dataset_version="freshness")

    client_engine = create_engine(f"sqlite:///{tmp_path / 'freshness.sqlite'}")
    Base.metadata.create_all(client_engine)
    with Session(client_engine) as client_session:
        import_catalog(client_session, tmp_path / "latest.json")
        imported = client_session.query(Job).filter_by(external_id="fresh").one()
        value = imported.eligibility_assessed_at
        assert value is not None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        assert value == assessed_at
    client_engine.dispose()


def test_catalog_rejects_excessive_uncompressed_payload(db_session, tmp_path: Path) -> None:
    compressed = gzip.compress(b'{"schema_version":1,"sources":[],"jobs":[]}' + b" " * 1024)
    payload_name = "catalog-bomb.json.gz"
    (tmp_path / payload_name).write_bytes(compressed)
    manifest = delivery.CatalogManifest(
        schema_version=1,
        dataset_version="bomb",
        generated_at=datetime.now(UTC).isoformat(),
        source_registry_version="bomb",
        job_dataset_version="bomb",
        payload=payload_name,
        sha256=hashlib.sha256(compressed).hexdigest(),
        compressed_bytes=len(compressed),
    )
    (tmp_path / "latest.json").write_text(json.dumps(manifest.as_dict()))
    with pytest.raises(ValueError, match="expands beyond"):
        import_catalog(db_session, tmp_path / "latest.json", max_uncompressed_bytes=128)


def test_catalog_sync_downloads_manifest_and_payload(monkeypatch, db_session, tmp_path: Path) -> None:
    repo = Repository(db_session)
    repo.upsert_job(_job("one"), EligibilityEngine().assess(_job("one")))
    db_session.commit()
    manifest = publish_catalog(db_session, tmp_path, dataset_version="n2")
    manifest_bytes = (tmp_path / "latest.json").read_bytes()
    payload_bytes = (tmp_path / manifest.payload).read_bytes()

    class Response:
        def __init__(self, body: bytes):
            self.body = body
            self.headers = {"Content-Length": str(len(body))}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _size=-1):
            return self.body

    def open_url(request, timeout=15):
        del timeout
        return Response(manifest_bytes if str(request.full_url).endswith("latest.json") else payload_bytes)

    monkeypatch.setattr(delivery.urllib.request, "urlopen", open_url)
    imported = sync_catalog(db_session, "https://raw.githubusercontent.com/org/repo/market-data/latest.json", tmp_path / "cache")
    assert imported.dataset_version == "n2"


def test_catalog_sync_rejects_non_data_endpoint(db_session, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="allowed HTTPS"):
        sync_catalog(db_session, "http://example.invalid/latest.json", tmp_path)


def test_catalog_sync_allows_only_explicit_loopback_test_endpoint(monkeypatch, db_session, tmp_path: Path) -> None:
    monkeypatch.setenv("CAREERRADAR_ALLOW_LOCAL_CATALOG_TEST", "1")
    with pytest.raises((OSError, ValueError)):
        sync_catalog(db_session, "http://127.0.0.1:9/latest.json", tmp_path)


def test_catalog_rejects_schema_and_size_errors(db_session, tmp_path: Path) -> None:
    repo = Repository(db_session)
    repo.upsert_job(_job("one"), EligibilityEngine().assess(_job("one")))
    db_session.commit()
    manifest = publish_catalog(db_session, tmp_path, dataset_version="n3")
    latest = json.loads((tmp_path / "latest.json").read_text())
    latest["schema_version"] = 99
    (tmp_path / "latest.json").write_text(json.dumps(latest))
    with pytest.raises(ValueError, match="unsupported"):
        import_catalog(db_session, tmp_path / "latest.json")

    payload = gzip.compress(json.dumps({"schema_version": 99, "jobs": []}).encode())
    (tmp_path / manifest.payload).write_bytes(payload)
    latest["schema_version"] = 1
    latest["compressed_bytes"] = len(payload)
    latest["sha256"] = hashlib.sha256(payload).hexdigest()
    (tmp_path / "latest.json").write_text(json.dumps(latest))
    with pytest.raises(ValueError, match="size"):
        import_catalog(db_session, tmp_path / "latest.json", max_bytes=1)
    latest["compressed_bytes"] = len((tmp_path / manifest.payload).read_bytes())
    with pytest.raises(ValueError, match="schema"):
        import_catalog(db_session, tmp_path / "latest.json")


def test_catalog_atomic_write_cleans_temporary_file(monkeypatch, db_session, tmp_path: Path) -> None:
    def fail_replace(_temporary, _target):
        raise OSError("replace failed")

    monkeypatch.setattr(delivery.os, "replace", fail_replace)
    with pytest.raises(OSError, match="replace failed"):
        publish_catalog(db_session, tmp_path, dataset_version="n4")
    assert list(tmp_path.glob(".*")) == []


def test_catalog_sync_rejects_unsafe_payload_path(monkeypatch, db_session, tmp_path: Path) -> None:
    monkeypatch.setattr(delivery, "_read_bounded", lambda *_args: json.dumps({"payload": "../escape.gz"}).encode())
    with pytest.raises(ValueError, match="unsafe"):
        sync_catalog(db_session, "https://raw.githubusercontent.com/org/repo/latest.json", tmp_path)

from __future__ import annotations

import json
from pathlib import Path

import pytest

import europe_visa_jobs.catalog.delivery as delivery
from europe_visa_jobs.catalog.delivery import import_catalog, publish_catalog, sync_catalog
from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.eligibility import EligibilityEngine
from europe_visa_jobs.schemas import ATSProvider, JobFamily, NormalizedJob


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
    repo.upsert_job(_job("one"), EligibilityEngine().assess(_job("one")))
    db_session.commit()
    manifest = publish_catalog(db_session, tmp_path, dataset_version="n1")
    assert manifest.sha256
    assert json.loads((tmp_path / "latest.json").read_text())['payload'] == "catalog-n1.json.gz"

    (tmp_path / manifest.payload).write_bytes((tmp_path / manifest.payload).read_bytes() + b"tampered")
    with pytest.raises(ValueError, match=r"invalid|hash mismatch"):
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

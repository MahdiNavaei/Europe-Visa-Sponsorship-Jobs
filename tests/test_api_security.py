from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Request, Response
from fastapi.testclient import TestClient

from europe_visa_jobs.api.app import app
from europe_visa_jobs.api.security import (
    SlidingWindowRateLimiter,
    authorize_candidate,
    hash_candidate_token,
    issue_candidate_token,
)
from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.db.session import get_db
from europe_visa_jobs.eligibility import EligibilityEngine
from europe_visa_jobs.schemas import ATSProvider, NormalizedJob
from europe_visa_jobs.utils.url_security import UnsafeUrlError, validate_public_http_url

PROFILE = {
    "name": "Protected Candidate",
    "target_roles": ["Backend Engineer"],
    "skills": ["Python"],
    "years_of_experience": 4,
    "preferred_countries": ["Germany"],
    "visa_required": True,
}


def test_candidate_token_protects_profile_export_tracking_and_delete(session_factory):
    with session_factory() as session:
        job = Repository(session).upsert_job(
            NormalizedJob(
                external_id="protected-job",
                provider=ATSProvider.GREENHOUSE,
                source_slug="protected",
                company_name="Protected GmbH",
                title="Backend Engineer",
                description="Visa sponsorship is available.",
                location="Berlin, Germany",
                country="Germany",
                apply_url="https://example.com/jobs/protected",
            ),
            EligibilityEngine().assess(
                NormalizedJob(
                    external_id="protected-job",
                    provider=ATSProvider.GREENHOUSE,
                    source_slug="protected",
                    company_name="Protected GmbH",
                    title="Backend Engineer",
                    description="Visa sponsorship is available.",
                    location="Berlin, Germany",
                    country="Germany",
                    apply_url="https://example.com/jobs/protected",
                )
            ),
        )
        job_id = job.id
        session.commit()

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        created = client.post("/api/v1/candidates", json=PROFILE)
        assert created.status_code == 201
        payload = created.json()
        candidate_id = payload["id"]
        token = payload["access_token"]
        headers = {"X-Candidate-Token": token}

        assert client.get(f"/api/v1/candidates/{candidate_id}").status_code == 404
        assert client.get(f"/api/v1/candidates/{candidate_id}", headers={"X-Candidate-Token": "x" * 32}).status_code == 404
        assert client.get(f"/api/v1/candidates/{candidate_id}", headers=headers).status_code == 200

        state = client.put(
            f"/api/v1/candidates/{candidate_id}/jobs/{job_id}/state",
            headers=headers,
            json={"saved": True, "application_status": "applied", "note": "private note"},
        )
        assert state.status_code == 200
        exported = client.get(f"/api/v1/candidates/{candidate_id}/export", headers=headers)
        assert exported.status_code == 200
        serialized = exported.text.casefold()
        assert token.casefold() not in serialized
        assert "access_token_hash" not in serialized
        assert exported.json()["job_states"][0]["note"] == "private note"

        assert client.delete(f"/api/v1/candidates/{candidate_id}", headers=headers).status_code == 204
        assert client.get(f"/api/v1/candidates/{candidate_id}", headers=headers).status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_public_url_guard_rejects_local_targets_and_credentials():
    assert validate_public_http_url("https://jobs.example.com/openings") == "https://jobs.example.com/openings"
    for value in (
        "file:///etc/passwd",
        "http://localhost/admin",
        "http://127.0.0.1/admin",
        "http://169.254.169.254/latest/meta-data",
        "https://user:pass@example.com/private",
    ):
        try:
            validate_public_http_url(value)
        except UnsafeUrlError:
            pass
        else:
            raise AssertionError(f"unsafe URL was accepted: {value}")


def test_candidate_token_and_rate_limiter_are_deterministic(monkeypatch):
    token, digest = issue_candidate_token()
    assert len(token) >= 40
    assert digest == hash_candidate_token(token)
    assert len(digest) == 64

    ticks = iter((10.0, 10.1, 12.1))
    monkeypatch.setattr("europe_visa_jobs.api.security.time.monotonic", lambda: next(ticks))
    limiter = SlidingWindowRateLimiter(requests=1, window_seconds=2)
    assert limiter.check("peer") is True
    assert limiter.check("peer") is False
    assert limiter.check("peer") is True


@pytest.mark.parametrize("host", ["203.0.113.10", "not-an-ip"])
def test_legacy_candidate_is_not_authorized_from_non_loopback(host):
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/candidate",
            "headers": [],
            "client": (host, 1234),
            "scheme": "http",
            "server": ("example", 80),
            "query_string": b"",
        }
    )
    with pytest.raises(HTTPException) as exc:
        authorize_candidate(request, Response(), SimpleNamespace(access_token_hash=None))  # type: ignore[arg-type]
    assert exc.value.status_code == 404

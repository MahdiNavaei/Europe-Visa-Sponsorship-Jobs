from __future__ import annotations

import pytest

import europe_visa_jobs.utils.url_security as url_security
from europe_visa_jobs.utils.url_security import UnsafeUrlError, validate_public_http_url


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://localhost/admin",
        "http://127.0.0.1/admin",
        "http://169.254.169.254/latest/meta-data",
        "https://user:password@example.com/jobs",
    ],
)
def test_public_url_policy_rejects_local_and_credentialed_targets(url):
    with pytest.raises(UnsafeUrlError):
        validate_public_http_url(url)


def test_public_url_policy_rejects_hostname_resolving_private(monkeypatch):
    monkeypatch.setattr(
        url_security,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(2, 1, 6, "", ("10.10.0.5", 0))],
    )

    with pytest.raises(UnsafeUrlError, match="non-public"):
        validate_public_http_url("https://attacker.example/jobs")


def test_public_url_policy_accepts_public_resolution(monkeypatch):
    monkeypatch.setattr(
        url_security,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(2, 1, 6, "", ("93.184.216.34", 0))],
    )

    assert validate_public_http_url("https://example.com/jobs") == "https://example.com/jobs"

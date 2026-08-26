from __future__ import annotations

import gzip
import hashlib
import json

import pytest

from europe_visa_jobs.catalog import import_catalog, publish_catalog
from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.db.source_registry import SourceRegistry
from europe_visa_jobs.eligibility import EligibilityEngine
from europe_visa_jobs.schemas import JobFamily, NormalizedJob, SourceConfig
from europe_visa_jobs.utils.market import MarketScope, market_scope


@pytest.mark.parametrize(
    ("country", "location", "expected"),
    [
        ("Germany", "Berlin, Germany", MarketScope.SUPPORTED_COUNTRY),
        (None, "Remote - Europe", MarketScope.REMOTE_EUROPE),
        (None, "London, UK / New York, USA", MarketScope.SUPPORTED_COUNTRY),
        (None, "Remote worldwide", MarketScope.AMBIGUOUS_REMOTE),
        (None, "Remote - EMEA", MarketScope.AMBIGUOUS_REMOTE),
        (None, "Remote", MarketScope.AMBIGUOUS_REMOTE),
        (None, "United States", MarketScope.OUTSIDE_EUROPE),
        ("Canada", "Toronto, Canada", MarketScope.OUTSIDE_EUROPE),
        (None, None, MarketScope.UNKNOWN_LOCATION),
    ],
)
def test_market_scope_is_explicit_and_fail_closed(country, location, expected) -> None:
    assert market_scope(country, location) == expected


def test_publication_contains_only_european_technical_jobs(db_session, tmp_path) -> None:
    SourceRegistry(db_session).import_config(
        SourceConfig(provider="greenhouse", company_name="Acme", slug="acme")
    )
    repo = Repository(db_session)
    rows = [
        ("eu-tech", "Backend Engineer", "Berlin, Germany", "Germany"),
        ("us-tech", "Backend Engineer", "Austin, TX", None),
        ("global-tech", "Backend Engineer", "Remote worldwide", None),
        ("eu-sales", "Sales Executive", "Paris, France", "France"),
    ]
    for external_id, title, location, country in rows:
        job = NormalizedJob(
            external_id=external_id,
            provider="greenhouse",
            source_slug="acme",
            company_name="Acme",
            title=title,
            description="Visa sponsorship available.",
            location=location,
            country=country,
            apply_url=f"https://example.com/{external_id}",
            job_family=JobFamily.BACKEND,
        )
        repo.upsert_job(
            job,
            EligibilityEngine().assess(job),
            classification_status="nontechnical" if external_id == "eu-sales" else "technical",
        )
    db_session.commit()

    manifest = publish_catalog(db_session, tmp_path, dataset_version="scope")
    payload = json.loads(gzip.decompress((tmp_path / manifest.payload).read_bytes()))
    assert [row["external_id"] for row in payload["jobs"]] == ["eu-tech"]


def test_import_defensively_rejects_out_of_scope_rows(db_session, tmp_path) -> None:
    SourceRegistry(db_session).import_config(
        SourceConfig(provider="greenhouse", company_name="Acme", slug="acme")
    )
    repo = Repository(db_session)
    for external_id, location, country in [
        ("eu", "Berlin, Germany", "Germany"),
        ("us", "Austin, TX", None),
    ]:
        job = NormalizedJob(
            external_id=external_id,
            provider="greenhouse",
            source_slug="acme",
            company_name="Acme",
            title="Backend Engineer",
            description="Visa sponsorship available.",
            location=location,
            country=country,
            apply_url=f"https://example.com/{external_id}",
            job_family=JobFamily.BACKEND,
        )
        repo.upsert_job(job, EligibilityEngine().assess(job))
    db_session.commit()
    manifest = publish_catalog(db_session, tmp_path, dataset_version="scope-import")
    payload_path = tmp_path / manifest.payload
    payload = json.loads(gzip.decompress(payload_path.read_bytes()))
    # Simulate a legacy/contaminated publisher adding a US row.
    us = dict(payload["jobs"][0])
    us.update(external_id="us-injected", location="Austin, TX", country=None)
    payload["jobs"].append(us)
    compressed = gzip.compress(json.dumps(payload).encode())
    payload_path.write_bytes(compressed)
    latest = json.loads((tmp_path / "latest.json").read_text())
    latest["compressed_bytes"] = len(compressed)
    latest["sha256"] = hashlib.sha256(compressed).hexdigest()
    (tmp_path / "latest.json").write_text(json.dumps(latest))

    db_session.query(__import__("europe_visa_jobs.db.models", fromlist=["Job"]).Job).delete()
    db_session.flush()
    import_catalog(db_session, tmp_path / "latest.json")
    imported_ids = {item.external_id for item in db_session.query(__import__("europe_visa_jobs.db.models", fromlist=["Job"]).Job)}
    assert imported_ids == {"eu"}

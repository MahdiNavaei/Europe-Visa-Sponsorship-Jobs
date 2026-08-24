from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from scripts.build_sponsor_registry import (
    NL_REGISTER_URL,
    NL_REGISTRY_NAME,
    UK_PUBLICATION_URL,
    UK_REGISTRY_NAME,
    _dataset_bytes,
    netherlands_records,
    uk_records,
    validate_registry,
)


def test_official_source_parsers_and_deterministic_gzip():
    uk = (
        b"Organisation Name,Type & Rating\n"
        b"Acme Ltd,Worker (A rating)\n"
        b"Seasonal Ltd,Temporary Worker\n"
    )
    ind = b"<table><tr><th>Organisation</th></tr><tr><td>Acme B.V.</td><td>1234</td></tr></table>"
    records = [*uk_records(uk), *netherlands_records(ind)]
    assert {record[0] for record in records} == {"Acme Ltd", "Acme B.V."}
    assert _dataset_bytes(records, compressed=True) == _dataset_bytes(records, compressed=True)


def test_registry_validation_checks_freshness_hash_counts_and_provenance(tmp_path):
    records = [
        ("Acme Ltd", "United Kingdom", UK_REGISTRY_NAME, UK_PUBLICATION_URL),
        ("Acme B.V.", "Netherlands", NL_REGISTRY_NAME, NL_REGISTER_URL),
    ]
    dataset = tmp_path / "sponsors.csv.gz"
    payload = _dataset_bytes(records, compressed=True)
    dataset.write_bytes(payload)
    manifest_path = tmp_path / "sponsors.manifest.json"
    manifest = {
        "format": "career-radar-sponsor-registry/v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset_sha256": sha256(payload).hexdigest(),
        "record_count": 2,
        "country_counts": {"United Kingdom": 1, "Netherlands": 1},
        "sources": [
            {"url": UK_PUBLICATION_URL, "input_sha256": "a" * 64},
            {"url": NL_REGISTER_URL, "input_sha256": "b" * 64},
        ],
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    validated = validate_registry(
        dataset,
        manifest_path,
        max_age_days=1,
        minimum_uk=1,
        minimum_nl=1,
        require_input_hashes=True,
    )
    assert validated["record_count"] == 2

    manifest["dataset_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(RuntimeError, match="SHA-256"):
        validate_registry(
            dataset,
            manifest_path,
            max_age_days=1,
            minimum_uk=1,
            minimum_nl=1,
        )


def test_registry_validation_rejects_non_official_provenance(tmp_path):
    dataset = tmp_path / "sponsors.csv"
    dataset.write_text(
        "company_name,country,registry_name,source_url\n"
        "Acme Ltd,United Kingdom,UKVI Register of Licensed Sponsors (Workers),https://attacker.example\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "sponsors.manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="untrusted provenance"):
        validate_registry(dataset, manifest, max_age_days=1, minimum_uk=1, minimum_nl=0)

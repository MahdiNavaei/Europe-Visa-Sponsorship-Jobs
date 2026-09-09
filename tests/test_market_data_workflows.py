from __future__ import annotations

from pathlib import Path


def _workflow(name: str) -> str:
    root = Path(__file__).resolve().parents[1]
    return (root / ".github" / "workflows" / name).read_text(encoding="utf-8")


def test_all_market_data_writers_use_retrying_fetch_and_lease_protection():
    for name in ("daily-ingest.yml", "source-discovery.yml", "source-health.yml"):
        workflow = _workflow(name)
        assert "bash scripts/fetch_market_data.sh" in workflow
        assert "MARKET_DATA_BASE_SHA=" in workflow
        assert "git push --force-with-lease=" in workflow
        assert "git push --force origin HEAD:market-data" not in workflow
        assert "git fetch origin market-data || true" not in workflow


def test_every_market_data_writer_preserves_the_rolling_registry():
    for name in ("daily-ingest.yml", "source-discovery.yml", "source-health.yml"):
        workflow = _workflow(name)
        assert "source-registry.latest.json" in workflow
        assert "git add source-registry.latest.json" in workflow or (
            "git add data/state source-registry.latest.json" in workflow
        )

    daily = _workflow("daily-ingest.yml")
    assert "cp build/source-registry.latest.json source-registry.latest.json" in daily
    assert "git add source-registry.latest.json data/catalog data/state" in daily


def test_source_discovery_publishes_only_public_data_allowlist():
    workflow = _workflow("source-discovery.yml")
    assert "git read-tree --empty" in workflow
    assert "git add source-registry.latest.json" in workflow
    assert "git add data" in workflow
    assert "Refusing to publish unexpected market-data paths" in workflow
    assert "git add -A" not in workflow


def test_daily_state_migrates_legacy_blob_to_chunked_archive():
    workflow = _workflow("daily-ingest.yml")
    assert "daily.sqlite.gz.manifest.json" in workflow
    assert "branch_state_archive.py list-chunks" in workflow
    assert "branch_state_archive.py restore" in workflow
    assert "branch_state_archive.py pack" in workflow
    assert "--chunk-size-mib 48" in workflow
    assert "daily.sqlite.gz.part-*" in workflow
    assert "Restored legacy SQLite state" in workflow
    assert "rm -f data/state/daily.sqlite.gz" in workflow
    assert "Refusing to publish unexpected market-data paths" in workflow


def test_market_data_fetch_helper_never_silently_downgrades_network_failure():
    root = Path(__file__).resolve().parents[1]
    helper = (root / "scripts" / "fetch_market_data.sh").read_text(encoding="utf-8")
    assert "for attempt in 1 2 3" in helper
    assert "Unable to determine whether" in helper
    assert "exists but could not be fetched" in helper
    assert "|| true" not in helper

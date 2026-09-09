from pathlib import Path


def test_source_health_bootstraps_from_rolling_registry_snapshot():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "source-health.yml").read_text(
        encoding="utf-8"
    )

    assert "origin/market-data:source-registry.latest.json" in workflow
    assert "HEALTH_BOOTSTRAP_SNAPSHOT=build/source-registry.bootstrap.json" in workflow
    assert 'evj-ingest sources bootstrap --snapshot "$HEALTH_BOOTSTRAP_SNAPSHOT"' in workflow
    assert (
        'evj-ingest sources bootstrap --snapshot config/source-registry.snapshot.json'
        not in workflow
    )

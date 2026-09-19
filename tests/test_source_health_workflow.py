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


def test_recovery_is_explicit_in_all_scheduled_pipelines():
    root = Path(__file__).resolve().parents[1]
    health = (root / ".github/workflows/source-health.yml").read_text(encoding="utf-8")
    discovery = (root / ".github/workflows/source-discovery.yml").read_text(encoding="utf-8")
    ingestion = (root / ".github/workflows/daily-ingest.yml").read_text(encoding="utf-8")

    assert '"$HEALTH_BOOTSTRAP_SNAPSHOT" --allow-stale-snapshot' in health
    assert '"$DISCOVERY_BOOTSTRAP_SNAPSHOT" --allow-stale-snapshot' in discovery
    assert 'build/source-registry.latest.json --allow-stale-snapshot' in ingestion
    assert "maximum_snapshot_age=None," in ingestion


def test_bootstrap_cli_keeps_strict_validation_by_default():
    from europe_visa_jobs.ingestion.cli import _parser

    strict = _parser().parse_args(["sources", "bootstrap", "--snapshot", "registry.json"])
    recovery = _parser().parse_args(
        ["sources", "bootstrap", "--snapshot", "registry.json", "--allow-stale-snapshot"]
    )
    assert strict.allow_stale_snapshot is False
    assert recovery.allow_stale_snapshot is True

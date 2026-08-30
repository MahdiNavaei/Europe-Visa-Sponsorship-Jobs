from __future__ import annotations

import importlib.util
import json
from math import ceil
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_release_inputs.py"
_SPEC = importlib.util.spec_from_file_location("validate_release_inputs", _SCRIPT)
assert _SPEC and _SPEC.loader
validate_release_inputs = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(validate_release_inputs)

_SIGNING_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "windows_signing_mode.py"
_SIGNING_SPEC = importlib.util.spec_from_file_location("windows_signing_mode", _SIGNING_SCRIPT)
assert _SIGNING_SPEC and _SIGNING_SPEC.loader
windows_signing_mode = importlib.util.module_from_spec(_SIGNING_SPEC)
_SIGNING_SPEC.loader.exec_module(windows_signing_mode)


def test_release_version_sources_match():
    assert validate_release_inputs.validate(require_snapshot=False) == "1.2.1"


def test_release_validation_accepts_the_real_snapshot():
    assert validate_release_inputs.validate(require_snapshot=True) == "1.2.1"


def test_release_validation_can_require_sponsor_provenance_hashes(monkeypatch):
    called = {}

    def fake_validate_registry(*args, **kwargs):
        called["args"] = args
        called["kwargs"] = kwargs
        return {}

    monkeypatch.setattr(validate_release_inputs, "validate_registry", fake_validate_registry)
    assert validate_release_inputs.validate(require_snapshot=False, require_input_hashes=True) == "1.2.1"
    assert called["kwargs"]["require_input_hashes"] is True


def test_windows_signing_mode_truth_table():
    assert windows_signing_mode.resolve_signing_mode(None, None) == "UNSIGNED"
    assert windows_signing_mode.resolve_signing_mode("base64-pfx", "pfx-password") == "SIGNED"

    for certificate, password in (("base64-pfx", None), (None, "pfx-password")):
        try:
            windows_signing_mode.resolve_signing_mode(certificate, password)
        except ValueError as exc:
            assert str(exc) == (
                "Windows signing is partially configured. Both "
                "WINDOWS_CERTIFICATE_BASE64 and WINDOWS_CERTIFICATE_PASSWORD must be present, "
                "or both must be absent."
            )
        else:
            raise AssertionError("partial Windows signing configuration must fail")


def test_windows_workflow_surfaces_signing_mode_and_keeps_strict_signing():
    root = Path(__file__).resolve().parents[1]
    windows = (root / ".github" / "workflows" / "windows-package.yml").read_text(encoding="utf-8")
    assert "scripts/windows_signing_mode.py" in windows
    assert "release_mode: ${{ steps.signing.outputs.mode }}" in windows
    assert "Windows release mode: UNSIGNED" in windows
    assert "Windows release mode: SIGNED" in windows
    assert "Authenticode was skipped because no signing certificate is configured." in windows
    assert "if ($LASTEXITCODE -ne 0) { throw \"Launcher signing failed" in windows
    assert "if ($LASTEXITCODE -ne 0) { throw \"Installer signing failed" in windows
    assert "WINDOWS_RELEASE_MODE: ${{ needs.build-windows.outputs.release_mode }}" in windows


def _planned_ingestion_batch(
    source_count: int,
    *,
    refresh_interval_hours: int = 18,
    stale_share: float = 0.75,
    min_batch_size: int = 150,
    max_batch_size: int = 400,
    max_revisit_hours: int = 25,
) -> tuple[int, int, int]:
    queue_window_hours = max_revisit_hours - refresh_interval_hours
    required_recurring_slots = ceil(source_count / queue_window_hours)
    required_batch_size = max(min_batch_size, ceil(required_recurring_slots / stale_share))
    batch_size = min(required_batch_size, max_batch_size)
    recurring_slots = ceil(batch_size * stale_share)
    worst_case_hours = refresh_interval_hours + ceil(source_count / recurring_slots)
    return batch_size, required_batch_size, worst_case_hours


def test_scheduled_ingestion_capacity_regression_for_registry_growth():
    # The live durable registry reached 1,361 verified boards and used to make
    # the fixed 150-board workflow fail before ingesting anything. Keep that
    # scale as a regression case and verify the dynamic planner preserves the
    # documented 25-hour revisit target without exceeding the runner-safe cap.
    batch_size, required_batch_size, worst_case_hours = _planned_ingestion_batch(1361)
    assert required_batch_size == 260
    assert batch_size == 260
    assert worst_case_hours <= 25


def test_scheduled_workflows_use_durable_source_state_and_compressed_sponsors():
    root = Path(__file__).resolve().parents[1]
    daily = (root / ".github" / "workflows" / "daily-ingest.yml").read_text(encoding="utf-8")
    discovery = (root / ".github" / "workflows" / "source-discovery.yml").read_text(encoding="utf-8")
    health = (root / ".github" / "workflows" / "source-health.yml").read_text(encoding="utf-8")
    windows = (root / ".github" / "workflows" / "windows-package.yml").read_text(encoding="utf-8")
    assert "data/sponsors.csv.gz" in daily
    assert "source-registry.latest.json" in daily
    assert "SOURCE_STATE_DATABASE_URL" in discovery
    assert "Persist source registry on market-data branch" in discovery
    assert "sqlite:///./source-discovery.sqlite" not in discovery
    assert "sqlite:///./source-health.sqlite" not in health
    assert "validate_release_inputs.py --require-snapshot --require-input-hashes" in windows
    assert "windows_market_cycle_smoke.py" in windows
    assert 'git fetch --no-tags origin "refs/heads/market-data:refs/remotes/origin/market-data"' in windows
    assert '$hasCatalog = ($LASTEXITCODE -eq 0)' in windows
    assert 'if ($hasCatalog)' in windows
    assert 'CAREERRADAR_SMOKE_BOUNDED_CATALOG' in windows
    cycle_smoke = (root / "scripts" / "windows_market_cycle_smoke.py").read_text(encoding="utf-8")
    assert '"CAREERRADAR_SMOKE_BOUNDED_CATALOG": "1"' in cycle_smoke
    assert '--due-for-refresh --limit "$INGESTION_BATCH_SIZE"' in daily
    assert 'cron: "17 * * * *"' in daily
    assert 'INGESTION_REFRESH_INTERVAL_HOURS: "18"' in daily
    assert 'INGESTION_REFRESH_STALE_SHARE: "0.75"' in daily
    assert 'INGESTION_MIN_BATCH_SIZE: "150"' in daily
    assert 'INGESTION_MAX_BATCH_SIZE: "400"' in daily
    assert 'INGESTION_MAX_REVISIT_HOURS: "25"' in daily
    assert "required_batch_size" in daily
    assert "INGESTION_BATCH_SIZE=" in daily
    assert "Ingestion will continue" in daily

    snapshot = json.loads((root / "config" / "source-registry.snapshot.json").read_text(encoding="utf-8"))
    batch_size, required_batch_size, worst_case_hours = _planned_ingestion_batch(
        snapshot["verified_source_count"]
    )
    assert batch_size <= 400
    assert required_batch_size <= 400
    assert worst_case_hours <= 25

    assert "git read-tree --empty" in daily
    assert "git add data/catalog data/state" in daily
    assert "git add -A" not in daily
    assert "summary[\"sources_failed\"] and not summary[\"partial_success\"]" in daily

    # Source-level provider outages are expected operational degradation, not
    # GitHub Actions infrastructure failures. The health workflow must persist
    # evidence and warn without deliberately turning a completed retry batch red.
    assert "Report remaining source degradation" in health
    assert "Surface remaining retry failures" not in health
    assert "::warning::" in health
    assert "raise SystemExit" not in health

    # The health checkpoint is also a public-data branch. Keep transient runner
    # caches out of it while preserving both catalog and durable state.
    assert "git read-tree --empty" in health
    assert "git add data/state source-registry.latest.json" in health
    assert "git add data/catalog" in health
    assert "git add -A" not in health

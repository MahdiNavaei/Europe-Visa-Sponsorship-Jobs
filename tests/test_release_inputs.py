from __future__ import annotations

import importlib.util
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
    assert validate_release_inputs.validate(require_snapshot=False) == "1.1.4"


def test_release_validation_accepts_the_real_snapshot():
    assert validate_release_inputs.validate(require_snapshot=True) == "1.1.4"


def test_release_validation_can_require_sponsor_provenance_hashes(monkeypatch):
    called = {}

    def fake_validate_registry(*args, **kwargs):
        called["args"] = args
        called["kwargs"] = kwargs
        return {}

    monkeypatch.setattr(validate_release_inputs, "validate_registry", fake_validate_registry)
    assert validate_release_inputs.validate(require_snapshot=False, require_input_hashes=True) == "1.1.4"
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
    assert "--only-uningested --largest-first --limit 100" in daily
    assert "git read-tree --empty" in daily
    assert "git add data/catalog data/state" in daily
    assert "git add -A" not in daily
    assert "summary[\"sources_failed\"] and not summary[\"partial_success\"]" in daily

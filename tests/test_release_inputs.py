from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_release_inputs.py"
_SPEC = importlib.util.spec_from_file_location("validate_release_inputs", _SCRIPT)
assert _SPEC and _SPEC.loader
validate_release_inputs = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(validate_release_inputs)


def test_release_version_sources_match():
    assert validate_release_inputs.validate(require_snapshot=False) == "1.1.3"


def test_release_validation_accepts_the_real_snapshot():
    assert validate_release_inputs.validate(require_snapshot=True) == "1.1.3"


def test_scheduled_workflows_use_durable_source_state_and_compressed_sponsors():
    root = Path(__file__).resolve().parents[1]
    daily = (root / ".github" / "workflows" / "daily-ingest.yml").read_text(encoding="utf-8")
    discovery = (root / ".github" / "workflows" / "source-discovery.yml").read_text(encoding="utf-8")
    health = (root / ".github" / "workflows" / "source-health.yml").read_text(encoding="utf-8")
    assert "data/sponsors.csv.gz" in daily
    assert "source-registry.latest.json" in daily
    assert "SOURCE_STATE_DATABASE_URL" in discovery
    assert "Persist source registry on market-data branch" in discovery
    assert "sqlite:///./source-discovery.sqlite" not in discovery
    assert "sqlite:///./source-health.sqlite" not in health

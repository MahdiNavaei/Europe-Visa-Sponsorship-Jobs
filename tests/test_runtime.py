from __future__ import annotations

import sys
from pathlib import Path

from europe_visa_jobs.runtime import resource_path


def test_resource_path_uses_project_root_in_source_checkout() -> None:
    assert resource_path("config", "ranking.yaml").name == "ranking.yaml"
    assert resource_path("config", "ranking.yaml").is_file()


def test_resource_path_uses_pyinstaller_bundle(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert resource_path("config", "sources.json") == tmp_path / "config" / "sources.json"

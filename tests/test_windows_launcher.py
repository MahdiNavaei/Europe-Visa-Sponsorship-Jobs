from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


def load_launcher_module():
    path = Path(__file__).resolve().parents[1] / "packaging" / "windows" / "launcher.py"
    spec = importlib.util.spec_from_file_location("career_radar_windows_launcher", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeTclError(Exception):
    pass


class FakeRoot:
    def after(self, delay_ms: int, callback):
        assert delay_ms == 0
        callback()


def test_ui_dispatch_accepts_keyword_arguments() -> None:
    launcher = load_launcher_module()
    window = object.__new__(launcher.LauncherWindow)
    window.tk = SimpleNamespace(TclError=FakeTclError)
    window.root = FakeRoot()

    observed: dict[str, str] = {}

    def configure(*, state: str) -> None:
        observed["state"] = state

    window._ui(configure, state="normal")

    assert observed == {"state": "normal"}


def test_refresh_status_is_atomic_and_exposes_success_metadata(tmp_path: Path) -> None:
    launcher = load_launcher_module()
    launcher.mark_refresh_started(tmp_path)
    assert launcher.last_refresh_path(tmp_path).read_text(encoding="utf-8")

    launcher.mark_refreshed(
        tmp_path,
        manifest=SimpleNamespace(dataset_version="2026-08-24"),
        stats={"sources_loaded": 12, "total_jobs": 345},
    )
    payload = launcher.json.loads(launcher.last_refresh_path(tmp_path).read_text(encoding="utf-8"))
    assert payload["state"] == "success"
    assert payload["dataset_version"] == "2026-08-24"
    assert payload["sources_loaded"] == 12
    assert payload["jobs_loaded"] == 345
    assert not (tmp_path / "last-refresh.json.tmp").exists()


def test_refresh_start_preserves_last_successful_sync(tmp_path: Path) -> None:
    launcher = load_launcher_module()
    launcher.mark_refreshed(
        tmp_path,
        manifest=SimpleNamespace(dataset_version="2026-08-24"),
        stats={"sources_loaded": 12, "total_jobs": 345},
    )
    before = launcher.json.loads(launcher.last_refresh_path(tmp_path).read_text(encoding="utf-8"))

    launcher.mark_refresh_started(tmp_path)
    during = launcher.json.loads(launcher.last_refresh_path(tmp_path).read_text(encoding="utf-8"))

    assert during["state"] == "syncing"
    assert during["last_successful_sync"] == before["last_successful_sync"]
    assert during["dataset_version"] == "2026-08-24"
    assert during["error"] is None

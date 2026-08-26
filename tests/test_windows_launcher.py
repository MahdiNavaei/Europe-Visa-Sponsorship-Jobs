from __future__ import annotations

import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace


def load_launcher_module():
    path = Path(__file__).resolve().parents[1] / "packaging" / "windows" / "launcher.py"
    spec = importlib.util.spec_from_file_location("career_radar_windows_launcher", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_launcher_falls_back_when_preferred_ports_are_occupied(monkeypatch):
    launcher = load_launcher_module()

    class FakeSocket:
        attempts = 0

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def bind(self, address):
            if address[1] and FakeSocket.attempts < 2:
                FakeSocket.attempts += 1
                raise OSError("occupied")
            self.address = (address[0], 51000 + FakeSocket.attempts)
            FakeSocket.attempts += 1

        def getsockname(self):
            return self.address

    monkeypatch.setattr(launcher.socket, "socket", lambda *_args: FakeSocket())
    launcher.configure_available_ports()
    assert launcher.API_PORT != 43127
    assert launcher.WEB_PORT != 43128
    assert launcher.API_PORT != launcher.WEB_PORT
    assert str(launcher.API_PORT) in launcher.API_URL
    assert str(launcher.WEB_PORT) in launcher.WEB_URL


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
    assert payload["next_scheduled_sync"]
    assert payload["successful_sources"] is None
    assert payload["degraded_providers"] == []
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


def test_existing_install_refresh_due_uses_24_hour_interval(tmp_path: Path, monkeypatch) -> None:
    launcher = load_launcher_module()
    baseline = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
    launcher.last_refresh_path(tmp_path).write_text(
        launcher.json.dumps({"completed_at": baseline.isoformat()}),
        encoding="utf-8",
    )

    class FrozenDateTime(datetime):
        current = baseline + timedelta(hours=23, minutes=59)

        @classmethod
        def now(cls, tz=None):
            return cls.current if tz else cls.current.replace(tzinfo=None)

    monkeypatch.setattr(launcher, "datetime", FrozenDateTime)
    assert launcher.refresh_due(tmp_path) is False
    FrozenDateTime.current = baseline + timedelta(hours=24)
    assert launcher.refresh_due(tmp_path) is True


def test_bundled_recovery_is_reported_as_stale_not_success(tmp_path: Path) -> None:
    launcher = load_launcher_module()
    launcher.mark_refreshed(
        tmp_path,
        manifest=SimpleNamespace(dataset_version="live-v1"),
        stats={"total_jobs": 400},
    )
    successful_at = launcher.json.loads(
        launcher.last_refresh_path(tmp_path).read_text(encoding="utf-8")
    )["last_successful_sync"]

    launcher.mark_stale_fallback(
        tmp_path,
        RuntimeError("network unavailable"),
        manifest=SimpleNamespace(dataset_version="bundled-v0", generated_at="2026-08-01T00:00:00Z"),
        stats={"total_jobs": 300},
    )
    payload = launcher.json.loads(launcher.last_refresh_path(tmp_path).read_text(encoding="utf-8"))
    assert payload["state"] == "stale_fallback"
    assert payload["last_successful_sync"] == successful_at
    assert payload["dataset_version"] == "bundled-v0"
    assert payload["generated_at"] == "2026-08-01T00:00:00Z"
    assert payload["error"] == "network unavailable"

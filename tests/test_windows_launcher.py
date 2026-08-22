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

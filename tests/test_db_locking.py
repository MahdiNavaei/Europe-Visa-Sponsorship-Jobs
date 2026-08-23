from __future__ import annotations

import os

import pytest

from europe_visa_jobs.db.locking import _pid_is_running, database_write_lock


def test_sqlite_writer_lock_rejects_overlap(tmp_path):
    url = f"sqlite:///{(tmp_path / 'career-radar.db').as_posix()}"
    with database_write_lock(url), pytest.raises(RuntimeError, match="already writing"):  # noqa: SIM117 - nested acquisition is the behavior under test
        with database_write_lock(url):
            pass


def test_non_sqlite_database_does_not_take_local_file_lock():
    with database_write_lock("postgresql+psycopg://example.invalid/career_radar"):
        pass


def test_windows_style_stale_pid_error_is_not_treated_as_an_active_writer(monkeypatch):
    monkeypatch.setattr(os, "kill", lambda pid, signal: (_ for _ in ()).throw(OSError(87, "invalid parameter")))
    assert _pid_is_running(12345) is False

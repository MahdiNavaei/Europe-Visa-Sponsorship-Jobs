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


def test_stale_writer_lock_is_recovered(tmp_path, monkeypatch):
    database = tmp_path / "career-radar.db"
    lock = database.with_name(f"{database.name}.writer.lock")
    lock.write_text("987654", encoding="utf-8")
    monkeypatch.setattr(os, "kill", lambda pid, signal: (_ for _ in ()).throw(ProcessLookupError()))

    with database_write_lock(f"sqlite:///{database.as_posix()}"):
        assert lock.read_text(encoding="utf-8") == str(os.getpid())
    assert not lock.exists()


def test_malformed_writer_lock_is_recovered(tmp_path):
    database = tmp_path / "career-radar.db"
    lock = database.with_name(f"{database.name}.writer.lock")
    lock.write_text("not-a-pid", encoding="utf-8")

    with database_write_lock(f"sqlite:///{database.as_posix()}"):
        assert lock.exists()
    assert not lock.exists()

from __future__ import annotations

import os
import threading
import time

import pytest
from sqlalchemy import text

from europe_visa_jobs.db.locking import _pid_is_running, database_write_lock
from europe_visa_jobs.db.session import make_engine


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


def test_sqlite_connection_waits_for_a_short_background_refresh_lock(tmp_path):
    database = tmp_path / "career-radar.db"
    url = f"sqlite:///{database.as_posix()}"
    first = make_engine(url)
    second = make_engine(url)
    with first.begin() as connection:
        connection.execute(text("create table writes (value integer not null)"))

    errors: list[BaseException] = []
    with first.connect() as connection:
        connection.exec_driver_sql("BEGIN EXCLUSIVE")
        connection.execute(text("insert into writes values (1)"))

        def write_after_lock_release() -> None:
            try:
                with second.begin() as writer:
                    writer.execute(text("insert into writes values (2)"))
            except BaseException as error:  # pragma: no cover - assertion below reports it
                errors.append(error)

        thread = threading.Thread(target=write_after_lock_release)
        thread.start()
        time.sleep(0.2)
        connection.commit()
        thread.join(timeout=5)

    assert not thread.is_alive()
    assert errors == []
    with second.connect() as connection:
        assert connection.scalar(text("select count(*) from writes")) == 2
    first.dispose()
    second.dispose()

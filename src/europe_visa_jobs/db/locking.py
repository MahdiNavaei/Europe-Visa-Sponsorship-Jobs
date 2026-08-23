"""Cross-process writer lock for the local SQLite desktop database."""

from __future__ import annotations

import os
from contextlib import contextmanager, suppress
from pathlib import Path
from urllib.parse import unquote


def _pid_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        # Windows reports ERROR_INVALID_PARAMETER (WinError 87) rather than
        # ProcessLookupError when a stale PID is probed with signal 0.
        return False
    return True


@contextmanager
def database_write_lock(database_url: str):
    """Fail fast if another local process is already writing the same SQLite DB."""
    if not database_url.startswith("sqlite:///"):
        yield
        return
    db_path = Path(unquote(database_url.removeprefix("sqlite:///")))
    lock_path = db_path.with_name(f"{db_path.name}.writer.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(2):
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError as exc:
            try:
                owner = int(lock_path.read_text(encoding="utf-8").strip())
            except (OSError, ValueError):
                owner = -1
            if owner > 0 and _pid_is_running(owner):
                raise RuntimeError(
                    "another Career Radar refresh or source-discovery process is already writing this local database"
                ) from exc
            if attempt:
                raise RuntimeError("could not recover stale local database writer lock") from exc
            with suppress(FileNotFoundError):
                lock_path.unlink()
    else:  # pragma: no cover - the loop always breaks or raises
        raise RuntimeError("could not acquire local database writer lock")
    try:
        os.write(fd, str(os.getpid()).encode("ascii"))
        yield
    finally:
        os.close(fd)
        with suppress(FileNotFoundError):
            lock_path.unlink()

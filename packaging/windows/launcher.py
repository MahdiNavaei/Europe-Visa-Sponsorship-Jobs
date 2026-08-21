from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from datetime import UTC, datetime, timedelta
from pathlib import Path

APP_NAME = "Career Radar"
API_PORT = 43127
WEB_PORT = 43128
API_URL = f"http://127.0.0.1:{API_PORT}"
WEB_URL = f"http://127.0.0.1:{WEB_PORT}/en"
REFRESH_INTERVAL = timedelta(hours=24)
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def bundle_dir() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))


def install_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def app_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    path = Path(base) / "CareerRadar"
    path.mkdir(parents=True, exist_ok=True)
    (path / "logs").mkdir(parents=True, exist_ok=True)
    return path


def configure_runtime(data_dir: Path) -> Path:
    db_path = data_dir / "career-radar.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    os.environ["WEB_ORIGIN"] = f"http://127.0.0.1:{WEB_PORT}"
    os.environ.setdefault("LOG_LEVEL", "WARNING")
    return db_path


def redirect_stdio(data_dir: Path) -> None:
    if sys.stdout is not None and sys.stderr is not None:
        return
    log_path = data_dir / "logs" / "launcher.log"
    stream = open(log_path, "a", encoding="utf-8", buffering=1)
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream


def migrate_database() -> None:
    from alembic import command
    from alembic.config import Config

    config_path = bundle_dir() / "alembic.ini"
    migrations_path = bundle_dir() / "migrations"
    config = Config(str(config_path))
    config.set_main_option("script_location", str(migrations_path))
    command.upgrade(config, "head")


def http_ok(url: str, timeout: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 400
    except (OSError, urllib.error.URLError):
        return False


def wait_for(url: str, timeout: float = 45.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if http_ok(url):
            return
        time.sleep(0.35)
    raise RuntimeError(f"Timed out waiting for {url}")


def last_refresh_path(data_dir: Path) -> Path:
    return data_dir / "last-refresh.json"


def refresh_due(data_dir: Path) -> bool:
    path = last_refresh_path(data_dir)
    if not path.is_file():
        return True
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        refreshed = datetime.fromisoformat(str(payload["completed_at"]))
        if refreshed.tzinfo is None:
            refreshed = refreshed.replace(tzinfo=UTC)
        return datetime.now(UTC) - refreshed >= REFRESH_INTERVAL
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return True


def mark_refreshed(data_dir: Path) -> None:
    last_refresh_path(data_dir).write_text(
        json.dumps({"completed_at": datetime.now(UTC).isoformat()}, indent=2),
        encoding="utf-8",
    )


def refresh_jobs(data_dir: Path) -> None:
    from europe_visa_jobs.ingestion.cli import _ingest

    sources = bundle_dir() / "config" / "sources.json"
    asyncio.run(_ingest(str(sources)))
    mark_refreshed(data_dir)


class RuntimeServices:
    def __init__(self) -> None:
        self.api_server = None
        self.api_thread: threading.Thread | None = None
        self.web_process: subprocess.Popen[bytes] | None = None

    def start(self) -> None:
        import uvicorn
        from europe_visa_jobs.api.app import app

        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=API_PORT,
            log_level="warning",
            access_log=False,
            loop="asyncio",
            http="h11",
        )
        self.api_server = uvicorn.Server(config)
        self.api_thread = threading.Thread(target=self.api_server.run, daemon=True, name="career-radar-api")
        self.api_thread.start()
        wait_for(f"{API_URL}/health")

        root = install_dir()
        node = root / "runtime" / "node.exe"
        server_candidates = list((root / "web-standalone").glob("**/server.js"))
        if not node.is_file():
            raise RuntimeError(f"Bundled Node runtime was not found: {node}")
        if not server_candidates:
            raise RuntimeError("Bundled Next.js standalone server was not found.")
        server = next(
            (candidate for candidate in server_candidates if candidate.parent.name == "web"),
            server_candidates[0],
        )
        env = os.environ.copy()
        env.update(
            {
                "NODE_ENV": "production",
                "PORT": str(WEB_PORT),
                "HOSTNAME": "127.0.0.1",
            }
        )
        self.web_process = subprocess.Popen(
            [str(node), str(server)],
            cwd=str(server.parent),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
        wait_for(WEB_URL)

    def stop(self) -> None:
        if self.api_server is not None:
            self.api_server.should_exit = True
        if self.web_process is not None and self.web_process.poll() is None:
            self.web_process.terminate()
            try:
                self.web_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.web_process.kill()
        if self.api_thread is not None and self.api_thread.is_alive():
            self.api_thread.join(timeout=5)


def smoke_test(data_dir: Path) -> int:
    services = RuntimeServices()
    try:
        migrate_database()
        services.start()
        wait_for(f"{API_URL}/api/v1/jobs?limit=1")
        wait_for(WEB_URL)
        print("Career Radar self-contained Windows runtime smoke test passed.")
        return 0
    finally:
        services.stop()


class LauncherWindow:
    def __init__(self, data_dir: Path, first_run: bool) -> None:
        import tkinter as tk
        from tkinter import messagebox, ttk

        self.tk = tk
        self.messagebox = messagebox
        self.data_dir = data_dir
        self.first_run = first_run
        self.services = RuntimeServices()
        self.refreshing = False

        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("520x270")
        self.root.minsize(500, 260)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        container = ttk.Frame(self.root, padding=24)
        container.pack(fill="both", expand=True)
        ttk.Label(container, text="Career Radar", font=("Segoe UI", 19, "bold")).pack(anchor="w")
        ttk.Label(
            container,
            text="European visa-sponsorship job intelligence",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(2, 18))

        self.status = tk.StringVar(value="Starting local services…")
        ttk.Label(container, textvariable=self.status, wraplength=460).pack(anchor="w", pady=(0, 18))

        buttons = ttk.Frame(container)
        buttons.pack(fill="x")
        self.open_button = ttk.Button(buttons, text="Open Career Radar", command=self.open_app, state="disabled")
        self.open_button.pack(side="left")
        self.refresh_button = ttk.Button(buttons, text="Refresh jobs", command=self.start_refresh, state="disabled")
        self.refresh_button.pack(side="left", padx=10)
        ttk.Button(buttons, text="Exit", command=self.close).pack(side="right")

        ttk.Label(
            container,
            text=f"Local data: {data_dir}",
            foreground="#666666",
            font=("Segoe UI", 8),
        ).pack(anchor="w", pady=(24, 0))

    def run(self) -> None:
        threading.Thread(target=self._start_runtime, daemon=True, name="career-radar-startup").start()
        self.root.mainloop()

    def _ui(self, callback, *args) -> None:
        try:
            self.root.after(0, callback, *args)
        except self.tk.TclError:
            pass

    def _set_status(self, text: str) -> None:
        self.status.set(text)

    def _start_runtime(self) -> None:
        try:
            self._ui(self._set_status, "Preparing the local database…")
            migrate_database()
            self._ui(self._set_status, "Starting API and web app…")
            self.services.start()
            self._ui(self.open_button.configure, state="normal")
            self._ui(self.refresh_button.configure, state="normal")
            if self.first_run:
                self._ui(self._set_status, "First launch: fetching live European jobs. This can take a little while…")
                self._refresh_worker(open_after=True)
            else:
                self._ui(self._set_status, "Career Radar is running locally.")
                self._ui(self.open_app)
                if refresh_due(self.data_dir):
                    threading.Thread(target=self._refresh_worker, daemon=True, name="career-radar-refresh").start()
            self._ui(self._schedule_refresh)
        except Exception as exc:
            self._ui(self._startup_failed, str(exc))

    def _startup_failed(self, error: str) -> None:
        self.status.set("Career Radar could not start.")
        self.messagebox.showerror(APP_NAME, f"Career Radar could not start.\n\n{error}\n\nSee the launcher log for details.")

    def open_app(self) -> None:
        webbrowser.open(WEB_URL)

    def start_refresh(self) -> None:
        if self.refreshing:
            return
        threading.Thread(target=self._refresh_worker, daemon=True, name="career-radar-refresh").start()

    def _refresh_worker(self, open_after: bool = False) -> None:
        if self.refreshing:
            return
        self.refreshing = True
        self._ui(self.refresh_button.configure, state="disabled")
        self._ui(self._set_status, "Refreshing public ATS feeds…")
        try:
            refresh_jobs(self.data_dir)
            self._ui(self._set_status, "Jobs refreshed successfully. Career Radar is ready.")
        except Exception as exc:
            self._ui(self._set_status, "Career Radar is running, but one or more job feeds could not refresh.")
            print(f"Refresh warning: {exc}")
        finally:
            self.refreshing = False
            self._ui(self.refresh_button.configure, state="normal")
            if open_after:
                self._ui(self.open_app)

    def _schedule_refresh(self) -> None:
        self.root.after(int(REFRESH_INTERVAL.total_seconds() * 1000), self.start_refresh)

    def close(self) -> None:
        self.status.set("Stopping Career Radar…")
        self.services.stop()
        self.root.destroy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--refresh-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_dir = app_data_dir()
    redirect_stdio(data_dir)
    db_path = configure_runtime(data_dir)

    if args.smoke_test:
        return smoke_test(data_dir)
    if args.refresh_only:
        migrate_database()
        refresh_jobs(data_dir)
        return 0

    if http_ok(f"{API_URL}/health") and http_ok(WEB_URL):
        webbrowser.open(WEB_URL)
        return 0

    first_run = not db_path.exists()
    LauncherWindow(data_dir, first_run).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

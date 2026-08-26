from __future__ import annotations

import argparse
import ctypes
import json
import os
import sys
import time
from pathlib import Path

from sqlalchemy import event, func, select

from europe_visa_jobs.catalog import sync_catalog
from europe_visa_jobs.db.models import Job, Source
from europe_visa_jobs.db.session import SessionLocal


def peak_rss_mib() -> float:
    """Return the process peak resident/working-set size without extra dependencies."""
    if sys.platform == "win32":
        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("page_fault_count", ctypes.c_ulong),
                ("peak_working_set_size", ctypes.c_size_t),
                ("working_set_size", ctypes.c_size_t),
                ("quota_peak_paged_pool_usage", ctypes.c_size_t),
                ("quota_paged_pool_usage", ctypes.c_size_t),
                ("quota_peak_non_paged_pool_usage", ctypes.c_size_t),
                ("quota_non_paged_pool_usage", ctypes.c_size_t),
                ("pagefile_usage", ctypes.c_size_t),
                ("peak_pagefile_usage", ctypes.c_size_t),
            ]

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        libraries = ctypes.windll
        libraries.kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        libraries.psapi.GetProcessMemoryInfo.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ProcessMemoryCounters),
            ctypes.c_ulong,
        ]
        if not libraries.psapi.GetProcessMemoryInfo(
            libraries.kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
        ):
            raise ctypes.WinError()
        peak_bytes = counters.peak_working_set_size
    else:
        import resource

        peak_value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        peak_bytes = peak_value if sys.platform == "darwin" else peak_value * 1024
    return round(peak_bytes / (1024 * 1024), 1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the real Career Radar catalog launch gate")
    parser.add_argument("--manifest-url", required=True)
    parser.add_argument("--cache-dir", default="build/catalog-launch-cache")
    parser.add_argument("--report", default="build/catalog-launch-gate.json")
    args = parser.parse_args()

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    profile: dict[str, float | int | str] = {}
    statements = 0

    with SessionLocal() as session:
        bind = session.get_bind()

        @event.listens_for(bind, "before_cursor_execute")
        def count_statement(*_args) -> None:
            nonlocal statements
            statements += 1

        started = time.perf_counter()
        manifest = sync_catalog(
            session,
            args.manifest_url,
            args.cache_dir,
            profile=profile,
        )
        before_commit = time.perf_counter()
        session.commit()
        committed = time.perf_counter()
        active_filter = Job.active.is_(True)
        status_counts: dict[str | None, int] = {
            status: count
            for status, count in session.execute(
                select(Job.eligibility_status, func.count())
                .where(active_filter)
                .group_by(Job.eligibility_status)
            ).all()
        }
        active_jobs = session.scalar(
            select(func.count()).select_from(Job).where(active_filter)
        ) or 0
        result = {
            "runner": "github-hosted" if os.environ.get("GITHUB_ACTIONS") else "local",
            "dataset_version": manifest.dataset_version,
            "payload": manifest.payload,
            "compressed_bytes": manifest.compressed_bytes,
            "sha256": manifest.sha256,
            "sources": session.scalar(select(func.count()).select_from(Source)) or 0,
            "jobs": session.scalar(select(func.count()).select_from(Job)) or 0,
            "active_jobs": active_jobs,
            "european_jobs": active_jobs,
            "eligible": status_counts.get("eligible", 0),
            "unknown": status_counts.get("unknown", 0),
            "rejected": status_counts.get("rejected", 0),
            "sql_statements": statements,
            "peak_rss_mib": peak_rss_mib(),
            "commit_seconds": committed - before_commit,
            "total_seconds": committed - started,
            "profile": profile,
        }

    report_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

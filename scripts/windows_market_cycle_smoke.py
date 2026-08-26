"""Exercise two catalog updates through one installed Windows executable."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import tempfile
from datetime import UTC, datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from shutil import rmtree
from threading import Thread

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from europe_visa_jobs.catalog.delivery import publish_catalog
from europe_visa_jobs.db.models import Base, CandidateJobState, Job
from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.db.source_registry import SourceRegistry
from europe_visa_jobs.eligibility import EligibilityEngine
from europe_visa_jobs.schemas import (
    ATSProvider,
    CandidateCreate,
    JobFamily,
    NormalizedJob,
    SourceConfig,
)


def _job(external_id: str, title: str) -> NormalizedJob:
    return NormalizedJob(
        external_id=external_id,
        provider=ATSProvider.GREENHOUSE,
        source_slug="cycle-smoke",
        company_name="Cycle Smoke Co",
        title=title,
        description="Visa sponsorship is available.",
        location="Berlin, Germany",
        country="Germany",
        apply_url=f"https://boards.greenhouse.io/cycle-smoke/jobs/{external_id}",
        job_family=JobFamily.BACKEND,
    )


def _build_catalogs(root: Path) -> None:
    engine = create_engine(f"sqlite:///{(root / 'source.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        source = SourceRegistry(session).import_config(
            SourceConfig(
                provider=ATSProvider.GREENHOUSE,
                company_name="Cycle Smoke Co",
                slug="cycle-smoke",
            )
        )
        source.enabled = True
        source.status = "healthy"
        source.validation_state = "verified"
        source.verified_at = datetime.now(UTC)
        source.last_success_at = datetime.now(UTC)
        repo = Repository(session)
        first = repo.upsert_job(_job("one", "Backend Engineer"), EligibilityEngine().assess(_job("one", "Backend Engineer")))
        repo.upsert_job(_job("two", "Platform Engineer"), EligibilityEngine().assess(_job("two", "Platform Engineer")))
        session.commit()
        publish_catalog(session, root / "n", dataset_version="n")

        first.title = "Senior Backend Engineer"
        second = session.query(Job).filter_by(external_id="two").one()
        second.active = False
        third = _job("three", "Data Platform Engineer")
        repo.upsert_job(third, EligibilityEngine().assess(third))
        session.commit()
        publish_catalog(session, root / "n1", dataset_version="n1")
    engine.dispose()


def _run(executable: Path, data_dir: Path, manifest_url: str, *, require_bundle: bool) -> None:
    env = os.environ.copy()
    env.update(
        {
            "CAREERRADAR_DATA_DIR": str(data_dir),
            "CAREERRADAR_CATALOG_MANIFEST_URL": manifest_url,
            "CAREERRADAR_ALLOW_LOCAL_CATALOG_TEST": "1",
            "CAREERRADAR_SMOKE_SYNC": "1",
            # Validate the packaged durable catalog without bulk-importing it;
            # the downloaded N/N+1 fixtures below still exercise full import.
            "CAREERRADAR_SMOKE_BOUNDED_CATALOG": "1",
        }
    )
    if require_bundle:
        env["CAREERRADAR_REQUIRE_BUNDLED_CATALOG"] = "1"
    else:
        env.pop("CAREERRADAR_REQUIRE_BUNDLED_CATALOG", None)
    result = subprocess.run(
        [str(executable), "--smoke-test"],
        env=env,
        capture_output=True,
        text=True,
        timeout=240,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"installed Windows smoke cycle failed ({result.returncode})\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def _active_jobs(data_dir: Path) -> dict[str, tuple[str, int]]:
    with sqlite3.connect(data_dir / "career-radar.db") as connection:
        rows = connection.execute(
            "SELECT external_id, title, active FROM jobs WHERE source_slug = ?",
            ("cycle-smoke",),
        ).fetchall()
    return {str(external_id): (str(title), int(active)) for external_id, title, active in rows}


def _attach_local_state(data_dir: Path) -> int:
    engine = create_engine(f"sqlite:///{(data_dir / 'career-radar.db').as_posix()}")
    try:
        with Session(engine) as session:
            candidate = Repository(session).create_candidate(
                CandidateCreate(
                    name="Existing Installed User",
                    target_roles=["Backend Engineer"],
                    skills=["Python"],
                    preferred_countries=["Germany"],
                )
            )
            job = session.query(Job).filter_by(source_slug="cycle-smoke", external_id="one").one()
            session.add(
                CandidateJobState(
                    candidate_id=candidate.id,
                    job_id=job.id,
                    saved=True,
                    application_status="applied",
                    note="Persist across catalog refresh",
                )
            )
            session.commit()
            return candidate.id
    finally:
        engine.dispose()


def _assert_local_state(data_dir: Path, candidate_id: int) -> None:
    engine = create_engine(f"sqlite:///{(data_dir / 'career-radar.db').as_posix()}")
    try:
        with Session(engine) as session:
            candidate = Repository(session).get_candidate(candidate_id)
            if candidate is None or candidate.name != "Existing Installed User":
                raise RuntimeError("N+1 catalog sync did not preserve the installed candidate profile")
            changed_job = session.query(Job).filter_by(
                source_slug="cycle-smoke", external_id="one"
            ).one()
            tracking = session.query(CandidateJobState).filter_by(
                candidate_id=candidate_id, job_id=changed_job.id
            ).one()
            if not tracking.saved or tracking.application_status != "applied" or tracking.note != "Persist across catalog refresh":
                raise RuntimeError("N+1 catalog sync did not preserve Saved/Applied/notes state")
    finally:
        engine.dispose()


def run(executable: Path) -> None:
    root = Path(tempfile.mkdtemp(prefix="career-radar-market-cycle-"))
    _build_catalogs(root)
    handler = partial(SimpleHTTPRequestHandler, directory=str(root))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    data_dir = root / "installed-data"
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        _run(executable, data_dir, f"{base_url}/n/latest.json", require_bundle=True)
        first_state = json.loads((data_dir / "last-refresh.json").read_text(encoding="utf-8"))
        if first_state.get("state") != "success" or first_state.get("dataset_version") != "n":
            raise RuntimeError(f"first catalog cycle was not successful: {first_state!r}")
        first_jobs = _active_jobs(data_dir)
        if set(first_jobs) != {"one", "two"}:
            raise RuntimeError(f"N did not install the expected jobs: {first_jobs!r}")
        candidate_id = _attach_local_state(data_dir)

        _run(executable, data_dir, f"{base_url}/n1/latest.json", require_bundle=False)
        second_state = json.loads((data_dir / "last-refresh.json").read_text(encoding="utf-8"))
        if second_state.get("state") != "success" or second_state.get("dataset_version") != "n1":
            raise RuntimeError(f"second catalog cycle was not successful: {second_state!r}")
        second_jobs = _active_jobs(data_dir)
        if second_jobs.get("one") != ("Senior Backend Engineer", 1) or second_jobs.get("three", ("", 0))[1] != 1:
            raise RuntimeError(f"N+1 did not install the new/edited jobs: {second_jobs!r}")
        if second_jobs.get("two", ("", 1))[1] != 0:
            raise RuntimeError(f"N+1 did not close the removed job: {second_jobs!r}")
        _assert_local_state(data_dir, candidate_id)
        print("Windows installed runtime market-data cycles N -> N+1 passed without reinstall.")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        # Windows can release SQLite handles after the child exits; the hosted
        # runner is ephemeral, so failed best-effort cleanup must not fail the gate.
        rmtree(root, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", type=Path, required=True)
    args = parser.parse_args()
    run(args.exe)


if __name__ == "__main__":
    main()

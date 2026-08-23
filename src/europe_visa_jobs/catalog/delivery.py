from __future__ import annotations

import gzip
import hashlib
import json
import os
import tempfile
import urllib.parse
import urllib.request
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from europe_visa_jobs.db.models import Job, Source
from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.schemas import (
    EligibilityAssessment,
    EligibilityStatus,
    Evidence,
    EvidenceKind,
    JobFamily,
    NormalizedJob,
)

SCHEMA_VERSION = 1
MAX_COMPRESSED_BYTES = 256 * 1024 * 1024


@dataclass(frozen=True)
class CatalogManifest:
    schema_version: int
    dataset_version: str
    generated_at: str
    source_registry_version: str
    job_dataset_version: str
    payload: str
    sha256: str
    compressed_bytes: int

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def publish_catalog(session: Session, output_dir: str | Path, *, dataset_version: str) -> CatalogManifest:
    """Write a deterministic gzip snapshot and manifest using atomic replaces."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(UTC).isoformat()
    sources = [
        {key: getattr(item, key) for key in ("provider", "board_identifier", "company_name", "careers_url", "board_url", "api_url", "country_hint", "status", "enabled", "validation_state")}
        for item in session.scalars(select(Source).order_by(Source.id))
    ]
    jobs: list[dict[str, Any]] = []
    for item in session.scalars(select(Job).where(Job.active.is_(True)).order_by(Job.id)):
        jobs.append({
            key: getattr(item, key)
            for key in ("external_id", "provider", "source_slug", "company_name", "title", "description", "location", "country", "department", "employment_type", "workplace_type", "apply_url", "job_url", "posted_at", "job_family", "eligibility_status", "eligibility_score", "classification_status", "job_sponsorship_signal", "company_sponsor_status", "final_candidate_eligibility")
        })
        jobs[-1]["evidence"] = [
            {key: getattr(evidence, key) for key in ("kind", "code", "message", "weight", "matched_text", "source_url")}
            for evidence in item.evidence
        ]
    for row in jobs:
        if row["posted_at"] is not None:
            row["posted_at"] = row["posted_at"].isoformat()
    payload = {"schema_version": SCHEMA_VERSION, "dataset_version": dataset_version, "generated_at": generated, "source_registry_version": dataset_version, "job_dataset_version": dataset_version, "sources": sources, "jobs": jobs}
    raw = _json_bytes(payload)
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    digest = hashlib.sha256(compressed).hexdigest()
    filename = f"catalog-{dataset_version}.json.gz"
    _atomic_write(root / filename, compressed)
    manifest = CatalogManifest(SCHEMA_VERSION, dataset_version, generated, dataset_version, dataset_version, filename, digest, len(compressed))
    _atomic_write(root / "latest.json", _json_bytes(manifest.as_dict()))
    return manifest


def import_catalog(session: Session, manifest_path: str | Path, *, max_bytes: int = MAX_COMPRESSED_BYTES) -> CatalogManifest:
    """Verify a data-only snapshot and apply it in the caller's transaction."""
    manifest_data = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    manifest = CatalogManifest(**manifest_data)
    if manifest.schema_version != SCHEMA_VERSION or Path(manifest.payload).name != manifest.payload:
        raise ValueError("unsupported or unsafe catalog manifest")
    payload_path = Path(manifest_path).parent / manifest.payload
    if payload_path.stat().st_size > max_bytes or payload_path.stat().st_size != manifest.compressed_bytes:
        raise ValueError("catalog payload size is invalid")
    compressed = payload_path.read_bytes()
    if hashlib.sha256(compressed).hexdigest() != manifest.sha256:
        raise ValueError("catalog payload hash mismatch")
    payload = json.loads(gzip.decompress(compressed).decode("utf-8"))
    if payload.get("schema_version") != SCHEMA_VERSION or not isinstance(payload.get("jobs"), list):
        raise ValueError("catalog payload schema mismatch")
    for source in payload.get("sources", []):
        if source.get("provider") and source.get("board_identifier"):
            # Client source rows are deliberately additive; user-owned tracking
            # rows are never touched by catalog import.
            from europe_visa_jobs.db.source_registry import SourceRegistry
            from europe_visa_jobs.schemas import SourceConfig
            imported = SourceRegistry(session).import_config(SourceConfig(provider=source["provider"], company_name=source.get("company_name") or source["board_identifier"], slug=source["board_identifier"], default_country=source.get("country_hint"), careers_url=source.get("careers_url"), board_url=source.get("board_url"), api_url=source.get("api_url"), enabled=bool(source.get("enabled", True))))
            imported.status = str(source.get("status") or imported.status)
            imported.validation_state = str(source.get("validation_state") or imported.validation_state)
            imported.enabled = bool(source.get("enabled", imported.enabled))
    repo = Repository(session)
    seen: dict[tuple[str, str], set[str]] = {}
    for row in payload["jobs"]:
        family = JobFamily(row.get("job_family") or JobFamily.OTHER.value)
        job = NormalizedJob(external_id=str(row["external_id"]), provider=row["provider"], source_slug=row["source_slug"], company_name=row["company_name"], title=row["title"], description=row.get("description") or "", location=row.get("location") or "", country=row.get("country"), department=row.get("department"), employment_type=row.get("employment_type"), workplace_type=row.get("workplace_type"), apply_url=row["apply_url"], job_url=row.get("job_url"), posted_at=datetime.fromisoformat(row["posted_at"]) if row.get("posted_at") else None, job_family=family)
        status = EligibilityStatus(row.get("eligibility_status") or EligibilityStatus.UNKNOWN.value)
        assessment = EligibilityAssessment(
            status=status,
            score=int(row.get("eligibility_score") or 0),
            country=job.country,
            evidence=[Evidence(kind=EvidenceKind(item["kind"]), code=item["code"], message=item["message"], weight=int(item["weight"]), matched_text=item.get("matched_text"), source_url=item.get("source_url")) for item in row.get("evidence", [])],
        )
        stored = repo.upsert_job(job, assessment, classification_status=row.get("classification_status") or "classification_unknown")
        stored.job_sponsorship_signal = row.get("job_sponsorship_signal") or stored.job_sponsorship_signal
        stored.company_sponsor_status = row.get("company_sponsor_status") or stored.company_sponsor_status
        stored.final_candidate_eligibility = row.get("final_candidate_eligibility") or stored.final_candidate_eligibility
        seen.setdefault((row["provider"], row["source_slug"]), set()).add(str(row["external_id"]))
    for (provider, slug), ids in seen.items():
        repo.mark_source_jobs_inactive_except(provider, slug, ids)
    session.flush()
    return manifest


def sync_catalog(session: Session, manifest_url: str, cache_dir: str | Path) -> CatalogManifest:
    """Download and import a public data-only manifest with strict URL bounds."""
    parsed = urllib.parse.urlparse(manifest_url)
    if parsed.scheme != "https" or parsed.netloc not in {"raw.githubusercontent.com", "github.com"}:
        raise ValueError("catalog endpoint is not an allowed HTTPS data host")
    root = Path(cache_dir)
    root.mkdir(parents=True, exist_ok=True)
    manifest_bytes = _read_bounded(manifest_url, 64 * 1024)
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    payload_name = Path(str(manifest.get("payload", ""))).name
    if payload_name != manifest.get("payload") or not payload_name:
        raise ValueError("catalog payload path is unsafe")
    payload_url = urllib.parse.urljoin(manifest_url, payload_name)
    payload_bytes = _read_bounded(payload_url, MAX_COMPRESSED_BYTES)
    _atomic_write(root / "latest.json", manifest_bytes)
    _atomic_write(root / payload_name, payload_bytes)
    return import_catalog(session, root / "latest.json")


def _read_bounded(url: str, maximum: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "CareerRadar-catalog/1"})
    with urllib.request.urlopen(request, timeout=15) as response:
        length = int(response.headers.get("Content-Length") or 0)
        if length > maximum:
            raise ValueError("catalog response is too large")
        data = response.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError("catalog response is too large")
    return data


def _atomic_write(path: Path, data: bytes) -> None:
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        with suppress(OSError):
            os.unlink(temporary)
        raise

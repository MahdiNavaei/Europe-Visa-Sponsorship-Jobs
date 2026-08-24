from __future__ import annotations

import gzip
import hashlib
import io
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
MAX_UNCOMPRESSED_BYTES = 512 * 1024 * 1024
MAX_MANIFEST_BYTES = 64 * 1024
_SECRET_KEY_PARTS = (
    "token",
    "secret",
    "password",
    "credential",
    "authorization",
    "api_key",
    "apikey",
    "key",
    "cookie",
)


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


def _is_secret_key(key: object) -> bool:
    return any(part in str(key).casefold() for part in _SECRET_KEY_PARTS)


def _public_metadata(value: Any) -> Any:
    """Return catalog-safe metadata with credentials removed recursively."""
    if isinstance(value, dict):
        return {
            str(key): _public_metadata(item)
            for key, item in value.items()
            if not _is_secret_key(key)
        }
    if isinstance(value, list):
        return [_public_metadata(item) for item in value]
    return value


def _public_url(value: str | None) -> str | None:
    """Remove URL credentials and secret-shaped query parameters."""
    if not value:
        return value
    parsed = urllib.parse.urlsplit(value)
    hostname = parsed.hostname or ""
    netloc = hostname
    if parsed.port is not None:
        netloc = f"{hostname}:{parsed.port}"
    query = urllib.parse.urlencode(
        [(key, item) for key, item in urllib.parse.parse_qsl(parsed.query) if not _is_secret_key(key)]
    )
    return urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path, query, ""))


def _read_json_file_bounded(path: Path, maximum: int) -> Any:
    if path.stat().st_size > maximum:
        raise ValueError("catalog manifest is too large")
    return json.loads(path.read_text(encoding="utf-8"))


def _decompress_bounded(compressed: bytes, maximum: int = MAX_UNCOMPRESSED_BYTES) -> bytes:
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(compressed), mode="rb") as stream:
            raw = stream.read(maximum + 1)
    except (EOFError, OSError) as exc:
        raise ValueError("catalog payload is not valid gzip") from exc
    if len(raw) > maximum:
        raise ValueError("catalog payload expands beyond the allowed size")
    return raw


def publish_catalog(session: Session, output_dir: str | Path, *, dataset_version: str) -> CatalogManifest:
    """Write a deterministic gzip snapshot and manifest using atomic replaces."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(UTC).isoformat()
    source_items = list(session.scalars(select(Source).order_by(Source.id)))
    sources = [
        {key: getattr(item, key) for key in ("provider", "board_identifier", "company_name", "careers_url", "board_url", "api_url", "country_hint", "status", "enabled", "validation_state")}
        for item in source_items
    ]
    for source, source_item in zip(sources, source_items, strict=True):
        source["source_metadata"] = _public_metadata(source_item.source_metadata or {})
        for url_key in ("careers_url", "board_url", "api_url"):
            source[url_key] = _public_url(source[url_key])
        for timestamp_key in ("verified_at", "last_success_at", "last_health_check_at", "last_checked_at"):
            value = getattr(source_item, timestamp_key)
            source[timestamp_key] = value.isoformat() if value is not None else None
    enabled_source_keys = {
        (source_item.provider, source_item.board_identifier)
        for source_item in source_items
        if source_item.enabled
    }
    jobs: list[dict[str, Any]] = []
    for job_item in session.scalars(select(Job).where(Job.active.is_(True)).order_by(Job.id)):
        if (job_item.provider, job_item.source_slug) not in enabled_source_keys:
            continue
        jobs.append({
            key: getattr(job_item, key)
            for key in ("external_id", "provider", "source_slug", "company_name", "title", "description", "location", "country", "department", "employment_type", "workplace_type", "apply_url", "job_url", "posted_at", "job_family", "eligibility_status", "eligibility_score", "eligibility_assessed_at", "classification_status", "job_sponsorship_signal", "company_sponsor_status", "final_candidate_eligibility")
        })
        jobs[-1]["evidence"] = [
            {key: getattr(evidence_item, key) for key in ("kind", "code", "message", "weight", "matched_text", "source_url")}
            for evidence_item in job_item.evidence
        ]
    for row in jobs:
        if row["posted_at"] is not None:
            row["posted_at"] = row["posted_at"].isoformat()
        if row["eligibility_assessed_at"] is not None:
            row["eligibility_assessed_at"] = row["eligibility_assessed_at"].isoformat()
    payload = {"schema_version": SCHEMA_VERSION, "dataset_version": dataset_version, "generated_at": generated, "source_registry_version": dataset_version, "job_dataset_version": dataset_version, "sources": sources, "jobs": jobs}
    raw = _json_bytes(payload)
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    digest = hashlib.sha256(compressed).hexdigest()
    filename = f"catalog-{dataset_version}.json.gz"
    _atomic_write(root / filename, compressed)
    manifest = CatalogManifest(SCHEMA_VERSION, dataset_version, generated, dataset_version, dataset_version, filename, digest, len(compressed))
    _atomic_write(root / "latest.json", _json_bytes(manifest.as_dict()))
    return manifest


def import_catalog(
    session: Session,
    manifest_path: str | Path,
    *,
    max_bytes: int = MAX_COMPRESSED_BYTES,
    max_uncompressed_bytes: int = MAX_UNCOMPRESSED_BYTES,
) -> CatalogManifest:
    """Verify a data-only snapshot and apply it in the caller's transaction."""
    manifest_file = Path(manifest_path)
    manifest_data = _read_json_file_bounded(manifest_file, MAX_MANIFEST_BYTES)
    try:
        manifest = CatalogManifest(**manifest_data)
    except (TypeError, KeyError) as exc:
        raise ValueError("unsupported or unsafe catalog manifest") from exc
    if manifest.schema_version != SCHEMA_VERSION or Path(manifest.payload).name != manifest.payload:
        raise ValueError("unsupported or unsafe catalog manifest")
    payload_path = manifest_file.parent / manifest.payload
    if payload_path.stat().st_size > max_bytes or payload_path.stat().st_size != manifest.compressed_bytes:
        raise ValueError("catalog payload size is invalid")
    compressed = payload_path.read_bytes()
    if hashlib.sha256(compressed).hexdigest() != manifest.sha256:
        raise ValueError("catalog payload hash mismatch")
    try:
        payload = json.loads(_decompress_bounded(compressed, max_uncompressed_bytes).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("catalog payload is not valid JSON") from exc
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != SCHEMA_VERSION
        or not isinstance(payload.get("sources"), list)
        or not isinstance(payload.get("jobs"), list)
    ):
        raise ValueError("catalog payload schema mismatch")
    catalog_source_keys: set[tuple[str, str]] = set()
    for source in payload.get("sources", []):
        if source.get("provider") and source.get("board_identifier"):
            # Client source rows are deliberately additive; user-owned tracking
            # rows are never touched by catalog import.
            from europe_visa_jobs.db.source_registry import SourceRegistry
            from europe_visa_jobs.schemas import SourceConfig
            key = (str(source["provider"]), str(source["board_identifier"]))
            catalog_source_keys.add(key)
            metadata = {**(source.get("source_metadata") or {}), "catalog_managed": True}
            imported = SourceRegistry(session).import_config(SourceConfig(provider=source["provider"], company_name=source.get("company_name") or source["board_identifier"], slug=source["board_identifier"], default_country=source.get("country_hint"), careers_url=source.get("careers_url"), board_url=source.get("board_url"), api_url=source.get("api_url"), metadata=metadata, enabled=bool(source.get("enabled", True))))
            imported.status = str(source.get("status") or imported.status)
            imported.validation_state = str(source.get("validation_state") or imported.validation_state)
            imported.enabled = bool(source.get("enabled", imported.enabled))
            for timestamp_key in ("verified_at", "last_success_at", "last_health_check_at", "last_checked_at"):
                value = source.get(timestamp_key)
                setattr(imported, timestamp_key, datetime.fromisoformat(value) if value else None)
    repo = Repository(session)
    seen: dict[tuple[str, str], set[str]] = {}
    source_completeness = {
        (str(source.get("provider")), str(source.get("board_identifier"))): str(
            (source.get("source_metadata") or {}).get("enumeration_completeness", "complete")
        )
        for source in payload.get("sources", [])
        if source.get("provider") and source.get("board_identifier")
    }
    for row in payload["jobs"]:
        if (str(row.get("provider")), str(row.get("source_slug"))) not in catalog_source_keys:
            continue
        family = JobFamily(row.get("job_family") or JobFamily.OTHER.value)
        job = NormalizedJob(external_id=str(row["external_id"]), provider=row["provider"], source_slug=row["source_slug"], company_name=row["company_name"], title=row["title"], description=row.get("description") or "", location=row.get("location") or "", country=row.get("country"), department=row.get("department"), employment_type=row.get("employment_type"), workplace_type=row.get("workplace_type"), apply_url=row["apply_url"], job_url=row.get("job_url"), posted_at=datetime.fromisoformat(row["posted_at"]) if row.get("posted_at") else None, job_family=family)
        status = EligibilityStatus(row.get("eligibility_status") or EligibilityStatus.UNKNOWN.value)
        assessment = EligibilityAssessment(
            status=status,
            score=int(row.get("eligibility_score") or 0),
            country=job.country,
            assessed_at=(
                datetime.fromisoformat(row["eligibility_assessed_at"])
                if row.get("eligibility_assessed_at")
                else datetime.now(UTC)
            ),
            evidence=[Evidence(kind=EvidenceKind(item["kind"]), code=item["code"], message=item["message"], weight=int(item["weight"]), matched_text=item.get("matched_text"), source_url=item.get("source_url")) for item in row.get("evidence", [])],
        )
        stored = repo.upsert_job(job, assessment, classification_status=row.get("classification_status") or "classification_unknown")
        stored.job_sponsorship_signal = row.get("job_sponsorship_signal") or stored.job_sponsorship_signal
        stored.company_sponsor_status = row.get("company_sponsor_status") or stored.company_sponsor_status
        stored.final_candidate_eligibility = row.get("final_candidate_eligibility") or stored.final_candidate_eligibility
        seen.setdefault((row["provider"], row["source_slug"]), set()).add(str(row["external_id"]))
    # A complete enumeration is authoritative even when it contains zero jobs.
    # Disabled sources and catalog-managed sources removed from a later catalog
    # are also authoritative removals. Partial enumerations never deactivate a
    # previously known job.
    for source in session.scalars(select(Source)):
        key = (source.provider, source.board_identifier)
        is_catalog_managed = bool((source.source_metadata or {}).get("catalog_managed"))
        removed = is_catalog_managed and key not in catalog_source_keys
        disabled = key in catalog_source_keys and not source.enabled
        complete = key in catalog_source_keys and source_completeness.get(key, "complete") == "complete"
        if removed or disabled or complete:
            repo.mark_source_jobs_inactive_except(source.provider, source.board_identifier, seen.get(key, set()))
    session.flush()
    return manifest


def sync_catalog(session: Session, manifest_url: str, cache_dir: str | Path) -> CatalogManifest:
    """Download and import a public data-only manifest with strict URL bounds."""
    parsed = urllib.parse.urlparse(manifest_url)
    public_endpoint = parsed.scheme == "https" and parsed.netloc in {"raw.githubusercontent.com", "github.com"}
    local_test_endpoint = (
        os.environ.get("CAREERRADAR_ALLOW_LOCAL_CATALOG_TEST") == "1"
        and parsed.scheme == "http"
        and parsed.hostname in {"127.0.0.1", "localhost"}
    )
    if not public_endpoint and not local_test_endpoint:
        raise ValueError("catalog endpoint is not an allowed HTTPS data host")
    root = Path(cache_dir)
    root.mkdir(parents=True, exist_ok=True)
    manifest_bytes = _read_bounded(manifest_url, MAX_MANIFEST_BYTES)
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

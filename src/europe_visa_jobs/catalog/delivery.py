from __future__ import annotations

import gzip
import hashlib
import io
import json
import logging
import os
import tempfile
import time
import urllib.parse
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from europe_visa_jobs.db.models import Company, Job, JobEvidence, Source
from europe_visa_jobs.db.repository import canonicalize_apply_url
from europe_visa_jobs.intelligence.job_profile import analyze_job
from europe_visa_jobs.intelligence.ontology import SkillOntology
from europe_visa_jobs.schemas import (
    EligibilityAssessment,
    EligibilityStatus,
    Evidence,
    EvidenceKind,
    JobFamily,
    NormalizedJob,
)
from europe_visa_jobs.utils import company_name_quality, normalize_company_name, normalize_country
from europe_visa_jobs.utils.market import is_supported_market_job

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
_DOWNLOAD_CHUNK_BYTES = 128 * 1024
_TRANSIENT_HTTP_STATUSES = {408, 425, 429, 500, 502, 503, 504}
logger = logging.getLogger(__name__)


class CatalogDownloadError(RuntimeError):
    def __init__(self, phase: str, message: str, *, attempts: int, retriable: bool) -> None:
        self.phase = phase
        self.attempts = attempts
        self.retriable = retriable
        super().__init__(f"catalog {phase} failed after {attempts} attempt(s): {message}")


class _TruncatedDownload(OSError):
    pass


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


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(_DOWNLOAD_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_gzip_json_bounded(path: Path, maximum: int = MAX_UNCOMPRESSED_BYTES) -> Any:
    """Decode gzip JSON once into a bounded bytearray before parsing."""
    try:
        with gzip.open(path, "rb") as stream:
            decoded = bytearray()
            total = 0
            while True:
                chunk = stream.read(min(_DOWNLOAD_CHUNK_BYTES, maximum + 1 - total))
                if not chunk:
                    break
                total += len(chunk)
                if total > maximum:
                    raise ValueError("catalog payload expands beyond the allowed size")
                decoded.extend(chunk)
            return json.loads(decoded)
    except (EOFError, OSError) as exc:
        raise ValueError("catalog payload is not valid gzip") from exc


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
        if job_item.classification_status != "technical":
            continue
        if not is_supported_market_job(job_item.country, job_item.location):
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


def _load_catalog_payload(
    manifest_path: str | Path,
    *,
    max_bytes: int = MAX_COMPRESSED_BYTES,
    max_uncompressed_bytes: int = MAX_UNCOMPRESSED_BYTES,
) -> tuple[CatalogManifest, dict[str, Any]]:
    """Verify and decode a data-only snapshot without changing the database."""
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
    if _hash_file(payload_path) != manifest.sha256:
        raise ValueError("catalog payload hash mismatch")
    try:
        payload = _read_gzip_json_bounded(payload_path, max_uncompressed_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("catalog payload is not valid JSON") from exc
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != SCHEMA_VERSION
        or not isinstance(payload.get("sources"), list)
        or not isinstance(payload.get("jobs"), list)
    ):
        raise ValueError("catalog payload schema mismatch")
    return manifest, payload


def validate_catalog(
    manifest_path: str | Path,
    *,
    max_bytes: int = MAX_COMPRESSED_BYTES,
    max_uncompressed_bytes: int = MAX_UNCOMPRESSED_BYTES,
) -> CatalogManifest:
    """Validate a catalog snapshot without importing its rows into the database."""
    manifest, _ = _load_catalog_payload(
        manifest_path,
        max_bytes=max_bytes,
        max_uncompressed_bytes=max_uncompressed_bytes,
    )
    return manifest


def import_catalog(
    session: Session,
    manifest_path: str | Path,
    *,
    max_bytes: int = MAX_COMPRESSED_BYTES,
    max_uncompressed_bytes: int = MAX_UNCOMPRESSED_BYTES,
    profile: dict[str, float | int | str] | None = None,
    _loaded: tuple[CatalogManifest, dict[str, Any]] | None = None,
) -> CatalogManifest:
    """Verify a data-only snapshot and apply it in the caller's transaction."""
    import_started = time.perf_counter()
    if _loaded is None:
        manifest, payload = _load_catalog_payload(
            manifest_path,
            max_bytes=max_bytes,
            max_uncompressed_bytes=max_uncompressed_bytes,
        )
    else:
        manifest, payload = _loaded
    loaded_at = time.perf_counter()
    existing_sources = {
        (item.provider, item.board_identifier): item for item in session.scalars(select(Source))
    }
    catalog_source_keys: set[tuple[str, str]] = set()
    for source in payload.get("sources", []):
        if source.get("provider") and source.get("board_identifier"):
            # Client source rows are deliberately additive; user-owned tracking
            # rows are never touched by catalog import.
            key = (str(source["provider"]), str(source["board_identifier"]))
            catalog_source_keys.add(key)
            metadata = {**(source.get("source_metadata") or {}), "catalog_managed": True}
            imported = existing_sources.get(key)
            if imported is None:
                imported = Source(
                    provider=key[0],
                    board_identifier=key[1],
                    discovery_method="catalog_import",
                )
                session.add(imported)
                existing_sources[key] = imported
            company_name = str(source.get("company_name") or source["board_identifier"])
            imported.company_name = company_name
            imported.normalized_company_name = normalize_company_name(company_name)
            imported.careers_url = source.get("careers_url")
            imported.board_url = source.get("board_url")
            imported.api_url = source.get("api_url")
            imported.country_hint = (
                normalize_country(str(source["country_hint"]))
                if source.get("country_hint")
                else None
            )
            imported.source_metadata = metadata
            imported.status = str(source.get("status") or imported.status or "unverified")
            imported.validation_state = str(
                source.get("validation_state") or imported.validation_state or "discovered"
            )
            imported.enabled = bool(source.get("enabled", True))
            for timestamp_key in ("verified_at", "last_success_at", "last_health_check_at", "last_checked_at"):
                value = source.get(timestamp_key)
                setattr(imported, timestamp_key, datetime.fromisoformat(value) if value else None)
    session.flush()
    sources_at = time.perf_counter()
    seen: dict[tuple[str, str], set[str]] = {}
    source_completeness = {
        (str(source.get("provider")), str(source.get("board_identifier"))): str(
            (source.get("source_metadata") or {}).get("enumeration_completeness", "complete")
        )
        for source in payload.get("sources", [])
        if source.get("provider") and source.get("board_identifier")
    }
    prepared: list[tuple[dict[str, Any], NormalizedJob, EligibilityAssessment]] = []
    for row in payload["jobs"]:
        if (str(row.get("provider")), str(row.get("source_slug"))) not in catalog_source_keys:
            continue
        if str(row.get("classification_status")) != "technical":
            continue
        if not is_supported_market_job(row.get("country"), row.get("location")):
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
        prepared.append((row, job, assessment))
        seen.setdefault((row["provider"], row["source_slug"]), set()).add(str(row["external_id"]))
    prepared_at = time.perf_counter()

    companies = {
        (item.normalized_name, item.country_key): item
        for item in session.scalars(select(Company))
    }
    company_for_job: dict[tuple[str, str, str], Company] = {}
    for row, job, _assessment in prepared:
        quality = company_name_quality(job.company_name)
        normalized_name = normalize_company_name(job.company_name)
        if quality == "untrusted":
            digest = hashlib.sha256(job.company_name.casefold().encode("utf-8")).hexdigest()[:12]
            normalized_name = f"untrusted {normalized_name or 'employer'} {digest}"
        country_key = job.country or ""
        company_key = (normalized_name, country_key)
        company = companies.get(company_key)
        if company is None:
            company = Company(
                name=job.company_name,
                normalized_name=normalized_name,
                country=job.country,
                country_key=country_key,
            )
            session.add(company)
            companies[company_key] = company
        company.name = job.company_name
        company.sponsor_verified = row.get("company_sponsor_status") == "verified_registry"
        company.name_quality = quality
        company_for_job[(job.provider.value, job.source_slug, job.external_id)] = company
    session.flush()
    companies_at = time.perf_counter()

    existing_jobs = {
        (item.provider, item.source_slug, item.external_id): item
        for item in session.scalars(select(Job))
    }
    existing_jobs_at = time.perf_counter()
    now = datetime.now(UTC)
    skill_ontology = SkillOntology()
    new_job_mappings: list[dict[str, Any]] = []
    evidence_by_key: dict[tuple[str, str, str], list[Evidence]] = {}
    for row, job, assessment in prepared:
        job_key = (job.provider.value, job.source_slug, job.external_id)
        company = company_for_job[job_key]
        job_profile = analyze_job(
            job.title, job.description, job.job_family, ontology=skill_ontology
        )
        values: dict[str, Any] = {
            "company_id": company.id,
            "company_name": job.company_name,
            "title": job.title,
            "description": job.description,
            "location": job.location,
            "country": job.country,
            "department": job.department,
            "employment_type": job.employment_type,
            "workplace_type": job.workplace_type,
            "apply_url": job.apply_url,
            "job_url": job.job_url,
            "canonical_apply_url": canonicalize_apply_url(job.apply_url),
            "posted_at": job.posted_at,
            "job_family": job.job_family.value,
            "required_skills": job_profile.required_skills,
            "preferred_skills": job_profile.preferred_skills,
            "min_experience_years": job_profile.min_experience_years,
            "seniority": job_profile.seniority.value if job_profile.seniority else None,
            "eligibility_status": assessment.status.value,
            "eligibility_score": assessment.score,
            "eligibility_assessed_at": assessment.assessed_at,
            "classification_status": str(
                row.get("classification_status") or "classification_unknown"
            ),
            "job_sponsorship_signal": str(
                row.get("job_sponsorship_signal") or "not_mentioned"
            ),
            "company_sponsor_status": str(row.get("company_sponsor_status") or "not_found"),
            "final_candidate_eligibility": str(
                row.get("final_candidate_eligibility") or assessment.status.value
            ),
            "last_seen_at": now,
            "active": True,
        }
        stored = existing_jobs.get(job_key)
        if stored is None:
            new_job_mappings.append(
                {
                    **values,
                    "external_id": job.external_id,
                    "provider": job.provider.value,
                    "source_slug": job.source_slug,
                    "first_seen_at": now,
                }
            )
        else:
            for attribute, value in values.items():
                setattr(stored, attribute, value)
        evidence_by_key[job_key] = assessment.evidence
    if new_job_mappings:
        session.bulk_insert_mappings(Job, new_job_mappings)
    session.flush()
    existing_jobs = {
        (item.provider, item.source_slug, item.external_id): item
        for item in session.scalars(select(Job))
    }
    jobs_at = time.perf_counter()
    imported_ids = [existing_jobs[key].id for key in evidence_by_key]
    if imported_ids:
        session.execute(delete(JobEvidence).where(JobEvidence.job_id.in_(imported_ids)))
        evidence_mappings = [
            {
                "job_id": existing_jobs[key].id,
                "kind": item.kind.value,
                "code": item.code,
                "message": item.message,
                "weight": item.weight,
                "matched_text": item.matched_text,
                "source_url": item.source_url,
                "created_at": now,
            }
            for key, items in evidence_by_key.items()
            for item in items
        ]
        if evidence_mappings:
            session.bulk_insert_mappings(JobEvidence, evidence_mappings)
    evidence_at = time.perf_counter()
    # A complete enumeration is authoritative even when it contains zero jobs.
    # Disabled sources and catalog-managed sources removed from a later catalog
    # are also authoritative removals. Partial enumerations never deactivate a
    # previously known job.
    authoritative: dict[tuple[str, str], bool] = {}
    for key, source in existing_sources.items():
        key = (source.provider, source.board_identifier)
        is_catalog_managed = bool((source.source_metadata or {}).get("catalog_managed"))
        removed = is_catalog_managed and key not in catalog_source_keys
        disabled = key in catalog_source_keys and not source.enabled
        complete = key in catalog_source_keys and source_completeness.get(key, "complete") == "complete"
        authoritative[key] = removed or disabled or complete
    for stored_job in session.scalars(select(Job).where(Job.active.is_(True))):
        source_key = (stored_job.provider, stored_job.source_slug)
        if authoritative.get(source_key) and stored_job.external_id not in seen.get(
            source_key, set()
        ):
            stored_job.active = False
    session.flush()
    inactive_at = time.perf_counter()
    canonical_first: dict[tuple[int, str], Job] = {}
    for stored_job in session.scalars(
        select(Job).where(Job.active.is_(True)).order_by(Job.id)
    ):
        if not stored_job.canonical_apply_url:
            stored_job.duplicate_of_job_id = None
            continue
        duplicate_key = (stored_job.company_id, stored_job.canonical_apply_url)
        first = canonical_first.setdefault(duplicate_key, stored_job)
        stored_job.duplicate_of_job_id = first.id if first.id != stored_job.id else None
    session.flush()
    finished_at = time.perf_counter()
    if profile is not None:
        profile.update(
            {
                "dataset_version": manifest.dataset_version,
                "payload_jobs": len(payload["jobs"]),
                "payload_sources": len(payload.get("sources", [])),
                "imported_jobs": len(prepared),
                "decode_validation_seconds": loaded_at - import_started,
                "source_reconcile_seconds": sources_at - loaded_at,
                "eligibility_evidence_decode_seconds": prepared_at - sources_at,
                "company_lookup_reconcile_seconds": companies_at - prepared_at,
                "existing_job_lookup_seconds": existing_jobs_at - companies_at,
                "job_upsert_seconds": jobs_at - existing_jobs_at,
                "evidence_write_seconds": evidence_at - jobs_at,
                "inactive_reconcile_seconds": inactive_at - evidence_at,
                "duplicate_reconcile_seconds": finished_at - inactive_at,
                "import_total_seconds": finished_at - import_started,
            }
        )
    return manifest


def sync_catalog(
    session: Session,
    manifest_url: str,
    cache_dir: str | Path,
    *,
    client: httpx.Client | None = None,
    retries: int = 3,
    profile: dict[str, float | int | str] | None = None,
) -> CatalogManifest:
    """Stream, validate, and import a catalog while preserving the last good cache."""
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
    owned_client = client is None
    http = client or httpx.Client(
        headers={
            "User-Agent": "CareerRadar-catalog/1",
            "Accept-Encoding": "identity",
        },
        follow_redirects=True,
        timeout=httpx.Timeout(connect=10, read=45, write=15, pool=10),
    )
    try:
        sync_started = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix=".catalog-stage-", dir=root) as stage_value:
            stage = Path(stage_value)
            manifest_path = stage / "latest.json"
            _download_streamed(
                http,
                manifest_url,
                manifest_path,
                maximum=MAX_MANIFEST_BYTES,
                retries=retries,
                phase="manifest download",
            )
            manifest_downloaded_at = time.perf_counter()
            manifest_data = _read_json_file_bounded(manifest_path, MAX_MANIFEST_BYTES)
            try:
                declared = CatalogManifest(**manifest_data)
            except (TypeError, KeyError) as exc:
                raise ValueError("unsupported or unsafe catalog manifest") from exc
            payload_name = Path(declared.payload).name
            if payload_name != declared.payload or not payload_name:
                raise ValueError("catalog payload path is unsafe")
            if declared.compressed_bytes > MAX_COMPRESSED_BYTES:
                raise ValueError("catalog payload size is invalid")

            payload_path = stage / payload_name
            digest, actual_bytes = _download_streamed(
                http,
                urllib.parse.urljoin(manifest_url, payload_name),
                payload_path,
                maximum=MAX_COMPRESSED_BYTES,
                expected_bytes=declared.compressed_bytes,
                retries=retries,
                phase="payload download",
            )
            payload_downloaded_at = time.perf_counter()
            if actual_bytes != declared.compressed_bytes:
                raise ValueError("catalog payload size is invalid")
            if digest != declared.sha256:
                raise ValueError("catalog payload hash mismatch")

            loaded = _load_catalog_payload(manifest_path)
            validated_at = time.perf_counter()
            imported = import_catalog(session, manifest_path, profile=profile, _loaded=loaded)
            imported_at = time.perf_counter()
            # A versioned payload is promoted first; latest.json is the atomic
            # pointer and is replaced only after every validation/import passes.
            os.replace(payload_path, root / payload_name)
            os.replace(manifest_path, root / "latest.json")
            if profile is not None:
                profile.update(
                    {
                        "downloaded_bytes": actual_bytes,
                        "manifest_download_seconds": manifest_downloaded_at - sync_started,
                        "payload_download_seconds": payload_downloaded_at
                        - manifest_downloaded_at,
                        "pre_import_validation_seconds": validated_at - payload_downloaded_at,
                        "sync_import_seconds": imported_at - validated_at,
                        "sync_total_seconds": time.perf_counter() - sync_started,
                    }
                )
            return imported
    finally:
        if owned_client:
            http.close()


def _download_streamed(
    client: httpx.Client,
    url: str,
    destination: Path,
    *,
    maximum: int,
    retries: int,
    phase: str,
    expected_bytes: int | None = None,
) -> tuple[str, int]:
    if retries < 1:
        raise ValueError("retries must be at least one")
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        with suppress(OSError):
            destination.unlink()
        try:
            with client.stream("GET", url) as response:
                if response.status_code >= 400:
                    response.raise_for_status()
                # httpx yields decoded bytes. Content-Length describes the wire
                # representation and is comparable only for identity encoding.
                content_encoding = response.headers.get("Content-Encoding", "identity")
                raw_length = (
                    response.headers.get("Content-Length")
                    if content_encoding.casefold() in {"", "identity"}
                    else None
                )
                content_length = int(raw_length) if raw_length else None
                if content_length is not None and content_length > maximum:
                    raise ValueError("catalog response is too large")
                if (
                    expected_bytes is not None
                    and content_length is not None
                    and content_length != expected_bytes
                ):
                    raise ValueError("catalog response Content-Length is invalid")
                digest = hashlib.sha256()
                received = 0
                with destination.open("wb") as stream:
                    for chunk in response.iter_bytes(_DOWNLOAD_CHUNK_BYTES):
                        received += len(chunk)
                        if received > maximum:
                            raise ValueError("catalog response is too large")
                        stream.write(chunk)
                        digest.update(chunk)
                    stream.flush()
                    os.fsync(stream.fileno())
                if content_length is not None and received != content_length:
                    raise _TruncatedDownload(
                        f"catalog response is truncated: expected {content_length}, received {received}"
                    )
                if expected_bytes is not None and received != expected_bytes:
                    raise _TruncatedDownload(
                        f"catalog response is truncated: expected {expected_bytes}, received {received}"
                    )
                return digest.hexdigest(), received
        except ValueError:
            with suppress(OSError):
                destination.unlink()
            raise
        except httpx.HTTPStatusError as exc:
            last_error = exc
            retriable = exc.response.status_code in _TRANSIENT_HTTP_STATUSES
            if not retriable or attempt == retries:
                with suppress(OSError):
                    destination.unlink()
                raise CatalogDownloadError(
                    phase, str(exc), attempts=attempt, retriable=retriable
                ) from exc
        except (httpx.TimeoutException, httpx.NetworkError, _TruncatedDownload) as exc:
            last_error = exc
            if attempt == retries:
                with suppress(OSError):
                    destination.unlink()
                raise CatalogDownloadError(
                    phase, str(exc), attempts=attempt, retriable=True
                ) from exc
        logger.warning("catalog_download_retry", extra={"phase": phase, "attempt": attempt})
        time.sleep(0.25 * (2 ** (attempt - 1)))
    raise CatalogDownloadError(phase, str(last_error), attempts=retries, retriable=True)


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

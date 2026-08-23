"""Build and validate the desktop source-registry bootstrap artifact.

The artifact deliberately contains only boards proved live by this project's
own registry.  It is a portable snapshot of source metadata, never a scraped
third-party company list, and lets a Windows user begin with verified boards
without running an internet-wide discovery pass at first launch.
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from europe_visa_jobs.db.models import Source
from europe_visa_jobs.schemas import SourceConfig, SourceValidationState

SNAPSHOT_FORMAT = "career-radar-source-registry/v1"


class SnapshotValidationError(ValueError):
    """Raised when a packaged registry snapshot is unsafe to bootstrap."""


def _timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


def _source_record(source: Source) -> dict[str, Any]:
    metadata = dict(source.source_metadata or {})
    metadata["snapshot_health"] = {
        "validation_state": source.validation_state,
        "health_state": source.status,
        "last_checked_at": _timestamp(source.last_checked_at),
        "last_success_at": _timestamp(source.last_success_at),
        "last_failure_at": _timestamp(source.last_failure_at),
        "failure_category": source.last_error_category,
        "retry_after": _timestamp(source.retry_after),
        "http_status": source.last_http_status,
        "jobs_observed": source.raw_job_count,
    }
    return {
        "provider": source.provider,
        "company_name": source.company_name or source.board_identifier,
        "slug": source.board_identifier,
        "default_country": source.country_hint,
        "careers_url": source.careers_url,
        "board_url": source.board_url,
        "api_url": source.api_url,
        "discovery_method": "verified_registry_snapshot",
        "metadata": metadata,
        "manual_override": False,
        "enabled": True,
    }


def build_snapshot(sources: list[Source]) -> dict[str, Any]:
    """Return a deterministic JSON-safe snapshot of verified live boards."""
    # ``verified_at`` is historical evidence. A source can subsequently enter
    # pending/retry state, so a portable release artifact must include only
    # sources whose *current* health record still proves a successful check.
    verified = [
        source
        for source in sources
        if source.enabled
        and source.validation_state == SourceValidationState.VERIFIED.value
        and source.last_success_at is not None
    ]
    records = sorted((_source_record(source) for source in verified), key=lambda item: (item["provider"], item["slug"]))
    latest = max(
        (source.last_checked_at or source.last_success_at or source.verified_at for source in verified),
        default=None,
    )
    providers = Counter(str(record["provider"]) for record in records)
    return {
        "format": SNAPSHOT_FORMAT,
        # Derived from persisted validation data rather than wall-clock export
        # time, so rebuilding an unchanged registry produces identical bytes.
        "generated_at": _timestamp(latest),
        "verified_source_count": len(records),
        "provider_counts": dict(sorted(providers.items())),
        "sources": records,
    }


def validate_snapshot(payload: object, *, minimum_verified: int = 0) -> list[SourceConfig]:
    if not isinstance(payload, dict) or payload.get("format") != SNAPSHOT_FORMAT:
        raise SnapshotValidationError("registry snapshot has an unsupported format")
    if not isinstance(payload.get("generated_at"), str):
        raise SnapshotValidationError("registry snapshot has no generation timestamp")
    records = payload.get("sources")
    if not isinstance(records, list):
        raise SnapshotValidationError("registry snapshot has no source list")
    declared_count = payload.get("verified_source_count")
    if declared_count != len(records):
        raise SnapshotValidationError("registry snapshot source count does not match its contents")
    if len(records) < minimum_verified:
        raise SnapshotValidationError(
            f"registry snapshot has {len(records)} verified boards; at least {minimum_verified} are required"
        )

    configs: list[SourceConfig] = []
    seen: set[tuple[str, str]] = set()
    for record in records:
        try:
            config = SourceConfig.model_validate(record)
        except Exception as exc:  # Pydantic's detail is retained for operators.
            raise SnapshotValidationError(f"registry snapshot contains an invalid source: {exc}") from exc
        key = (config.provider.value, config.slug.casefold())
        if key in seen:
            raise SnapshotValidationError(f"registry snapshot contains duplicate board {key[0]}:{key[1]}")
        seen.add(key)
        health = config.metadata.get("snapshot_health")
        if not isinstance(health, dict) or health.get("validation_state") != "verified":
            raise SnapshotValidationError(f"registry snapshot board {key[0]}:{key[1]} lacks verified health evidence")
        if not health.get("last_success_at"):
            raise SnapshotValidationError(f"registry snapshot board {key[0]}:{key[1]} lacks a successful validation time")
        configs.append(config)
    return configs

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from pydantic import TypeAdapter

from europe_visa_jobs.discovery.snapshot import DEFAULT_MAX_SNAPSHOT_AGE, validate_snapshot
from europe_visa_jobs.schemas import SourceConfig

_SOURCE_LIST = TypeAdapter(list[SourceConfig])


def load_sources(
    path: str | Path,
    *,
    minimum_snapshot_sources: int = 0,
    maximum_snapshot_age: timedelta | None = DEFAULT_MAX_SNAPSHOT_AGE,
) -> list[SourceConfig]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return [
            item
            for item in validate_snapshot(
                data,
                minimum_verified=minimum_snapshot_sources,
                maximum_age=maximum_snapshot_age,
            )
            if item.enabled
        ]
    return [item for item in _SOURCE_LIST.validate_python(data) if item.enabled]

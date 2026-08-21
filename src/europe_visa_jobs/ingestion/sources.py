from __future__ import annotations

import json
from pathlib import Path

from pydantic import TypeAdapter

from europe_visa_jobs.schemas import SourceConfig

_SOURCE_LIST = TypeAdapter(list[SourceConfig])


def load_sources(path: str | Path) -> list[SourceConfig]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [item for item in _SOURCE_LIST.validate_python(data) if item.enabled]

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from europe_visa_jobs.connectors.common import parse_datetime
from europe_visa_jobs.ingestion.sources import load_sources


def test_parse_datetime_variants():
    assert parse_datetime(None) is None
    assert parse_datetime(1_787_216_400_000).tzinfo == UTC
    assert parse_datetime("2026-08-20T10:00:00Z") == datetime(2026, 8, 20, 10, 0, tzinfo=UTC)
    assert parse_datetime("not-a-date") is None
    existing = datetime(2026, 1, 1, tzinfo=UTC)
    assert parse_datetime(existing) is existing
    assert parse_datetime({"bad": "type"}) is None


def test_load_sources_filters_disabled(tmp_path: Path):
    path = tmp_path / "sources.json"
    path.write_text(
        """[
          {"provider":"greenhouse","company_name":"A","slug":"a","enabled":true},
          {"provider":"lever","company_name":"B","slug":"b","enabled":false}
        ]""",
        encoding="utf-8",
    )
    sources = load_sources(path)
    assert len(sources) == 1
    assert sources[0].slug == "a"

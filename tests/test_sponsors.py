from pathlib import Path

import pytest

from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.ingestion.sponsors import import_sponsor_csv


def test_import_sponsor_csv(db_session, tmp_path: Path):
    csv_path = tmp_path / "sponsors.csv"
    csv_path.write_text(
        "company_name,country,registry_name,source_url\nAcme B.V.,Netherlands,IND,https://ind.nl\n",
        encoding="utf-8",
    )
    assert import_sponsor_csv(db_session, csv_path) == 1
    assert Repository(db_session).find_sponsor_record("Acme", "Netherlands") is not None


def test_import_sponsor_csv_requires_schema(db_session, tmp_path: Path):
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("company_name,country\nAcme,Germany\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing sponsor CSV columns"):
        import_sponsor_csv(db_session, csv_path)

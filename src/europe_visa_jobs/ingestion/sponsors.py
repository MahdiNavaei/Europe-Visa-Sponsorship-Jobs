from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy.orm import Session

from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.schemas import CompanySponsorEvidence

_REQUIRED_COLUMNS = {"company_name", "country", "registry_name", "source_url"}


def import_sponsor_csv(session: Session, path: str | Path) -> int:
    repo = Repository(session)
    count = 0
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = _REQUIRED_COLUMNS - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"missing sponsor CSV columns: {', '.join(sorted(missing))}")
        for row in reader:
            repo.add_sponsor_record(
                CompanySponsorEvidence(
                    company_name=row["company_name"].strip(),
                    country=row["country"].strip(),
                    registry_name=row["registry_name"].strip(),
                    source_url=row["source_url"].strip(),
                )
            )
            count += 1
    session.commit()
    return count

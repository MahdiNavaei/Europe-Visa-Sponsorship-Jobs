from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from europe_visa_jobs.db.models import SponsorRecord
from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.schemas import CompanySponsorEvidence
from europe_visa_jobs.utils import normalize_company_name

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


def import_production_sponsor_evidence(session: Session, path: str | Path) -> int:
    """Load the package's official-evidence cache before job eligibility runs."""
    source = Path(path)
    if not source.is_file():
        raise RuntimeError(f"production sponsor-evidence asset is missing: {source}")
    existing = session.scalar(select(func.count()).select_from(SponsorRecord)) or 0
    if existing:
        return 0
    with source.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = _REQUIRED_COLUMNS - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"missing sponsor CSV columns: {', '.join(sorted(missing))}")
        observed_at = datetime.now(UTC)
        unique_rows: dict[tuple[str, str, str], dict[str, object]] = {}
        for row in reader:
            if not all(row.get(column) for column in _REQUIRED_COLUMNS):
                continue
            company_name = row["company_name"].strip()
            country = row["country"].strip()
            registry_name = row["registry_name"].strip()
            normalized_name = normalize_company_name(company_name)
            if not normalized_name:
                continue
            unique_rows[(normalized_name, country, registry_name)] = {
                "company_name": company_name,
                "normalized_name": normalized_name,
                "country": country,
                "registry_name": registry_name,
                "source_url": row["source_url"].strip(),
                "verified_at": observed_at,
            }
        rows = list(unique_rows.values())
    if not rows:
        raise RuntimeError("production sponsor-evidence asset contains no usable records")
    # The generator has already deduplicated source rows. Bulk insertion keeps
    # first launch practical even with the full official UKVI register.
    session.bulk_insert_mappings(SponsorRecord, rows)
    session.commit()
    return len(rows)

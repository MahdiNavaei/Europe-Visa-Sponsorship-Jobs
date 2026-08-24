from __future__ import annotations

import csv
import gzip
import re
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from europe_visa_jobs.db.models import Company, Job, JobEvidence, SponsorRecord
from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.eligibility.engine import EligibilityEngine
from europe_visa_jobs.eligibility.sponsor_registry import SponsorRegistryStore
from europe_visa_jobs.schemas import ATSProvider, CompanySponsorEvidence, JobFamily, NormalizedJob
from europe_visa_jobs.utils import company_name_quality, normalize_company_name

_REQUIRED_COLUMNS = {"company_name", "country", "registry_name", "source_url"}


def _row_aliases(row: dict[str, str], company_name: str) -> set[str]:
    aliases = {normalize_company_name(company_name)}
    for value in re.split(r"[;|]", row.get("aliases", "")):
        if normalized := normalize_company_name(value):
            aliases.add(normalized)
    match = re.search(r"(?:\btrading\s+as\b|\bt\s*/\s*a\b)\s+(.+)$", company_name, re.IGNORECASE)
    if match and (normalized := normalize_company_name(match.group(1))):
        aliases.add(normalized)
    return aliases


def _open_csv(path: Path):
    if path.suffix.lower() == ".gz":
        return gzip.open(path, mode="rt", encoding="utf-8-sig", newline="")
    return path.open(encoding="utf-8-sig", newline="")


def import_sponsor_csv(session: Session, path: str | Path) -> int:
    repo = Repository(session)
    count = 0
    with _open_csv(Path(path)) as handle:
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
    """Synchronize the official-evidence cache and repair dependent truth fields.

    The production file is an authoritative snapshot.  Importing a later snapshot
    therefore updates changed rows and removes entries that disappeared instead
    of treating the first import as permanent truth.
    """
    source = Path(path)
    if not source.is_file():
        raise RuntimeError(f"production sponsor-evidence asset is missing: {source}")
    with _open_csv(source) as handle:
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
            aliases = _row_aliases(row, company_name)
            if not aliases:
                continue
            for normalized_name in aliases:
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

    current_records = list(session.scalars(select(SponsorRecord)))
    current = {
        (item.normalized_name, item.country, item.registry_name): (
            item.company_name,
            item.source_url,
        )
        for item in current_records
    }
    incoming = {
        (str(item["normalized_name"]), str(item["country"]), str(item["registry_name"])): (
            str(item["company_name"]),
            str(item["source_url"]),
        )
        for item in rows
    }
    changed_keys = {
        key for key in current.keys() | incoming.keys() if current.get(key) != incoming.get(key)
    }
    if changed_keys:
        # A full replace is both simpler and safer than piecemeal deletion for an
        # authoritative snapshot; the transaction keeps readers from observing a
        # half-refreshed register.
        session.execute(delete(SponsorRecord))
        session.bulk_insert_mappings(SponsorRecord, rows)
        session.flush()

    _reconcile_registry_dependents(session, rows)
    session.commit()
    return len(changed_keys)


def _reconcile_registry_dependents(session: Session, rows: list[dict[str, object]]) -> None:
    """Make company/job truth agree with the current registry snapshot.

    This runs even when the file itself is unchanged.  That matters when a
    catalog was imported after the registry and its company rows have not yet
    been reconciled.
    """
    evidence_by_key: dict[tuple[str, str], CompanySponsorEvidence] = {}
    for row in rows:
        record = CompanySponsorEvidence(
            company_name=str(row["company_name"]),
            matching_name=str(row["normalized_name"]),
            country=str(row["country"]),
            registry_name=str(row["registry_name"]),
            source_url=str(row["source_url"]),
        )
        evidence_by_key[(str(row["normalized_name"]), record.country)] = record

    engine = EligibilityEngine(SponsorRegistryStore(evidence_by_key.values()))
    companies = list(session.scalars(select(Company)))
    jobs_by_company: dict[int, list[Job]] = {}
    for job in session.scalars(select(Job)):
        jobs_by_company.setdefault(job.company_id, []).append(job)
    for company in companies:
        key = (normalize_company_name(company.name), company.country or "")
        sponsor = evidence_by_key.get(key)
        verified = sponsor is not None and company_name_quality(company.name) == "verified"
        company.sponsor_verified = verified

        for job in jobs_by_company.get(company.id, []):
            job.company_sponsor_status = "verified_registry" if verified else "not_found"
            if job.classification_status != "technical":
                continue
            normalized_job = NormalizedJob(
                external_id=job.external_id,
                provider=ATSProvider(job.provider),
                source_slug=job.source_slug,
                company_name=job.company_name,
                title=job.title,
                description=job.description,
                location=job.location,
                country=job.country,
                department=job.department,
                employment_type=job.employment_type,
                workplace_type=job.workplace_type,
                apply_url=job.apply_url,
                job_url=job.job_url,
                posted_at=job.posted_at,
                job_family=JobFamily(job.job_family),
            )
            assessment = engine.assess(normalized_job)
            job.eligibility_status = assessment.status.value
            job.eligibility_score = assessment.score
            job.eligibility_assessed_at = assessment.assessed_at
            job.final_candidate_eligibility = assessment.status.value
            positive = any(item.kind.value == "job_positive" for item in assessment.evidence)
            negative = any(item.kind.value == "job_negative" for item in assessment.evidence)
            job.job_sponsorship_signal = (
                "conflicting"
                if positive and negative
                else "confirmed_yes"
                if positive
                else "confirmed_no"
                if negative
                else "not_mentioned"
            )
            job.evidence.clear()
            for item in assessment.evidence:
                job.evidence.append(
                    JobEvidence(
                        kind=item.kind.value,
                        code=item.code,
                        message=item.message,
                        weight=item.weight,
                        matched_text=item.matched_text,
                        source_url=item.source_url,
                    )
                )
    session.flush()

from __future__ import annotations

from europe_visa_jobs.db.models import SponsorRecord
from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.eligibility.engine import EligibilityEngine
from europe_visa_jobs.eligibility.sponsor_registry import SponsorRegistryStore
from europe_visa_jobs.ingestion.sponsors import import_production_sponsor_evidence
from europe_visa_jobs.schemas import ATSProvider, EligibilityStatus, NormalizedJob


def test_production_sponsor_import_is_bulk_and_idempotent(db_session, tmp_path):
    path = tmp_path / "sponsors.csv"
    path.write_text(
        "company_name,country,registry_name,source_url\n"
        "Acme Ltd,United Kingdom,UKVI,https://www.gov.uk/example\n"
        "Acme Ltd,United Kingdom,UKVI,https://www.gov.uk/example\n",
        encoding="utf-8",
    )
    assert import_production_sponsor_evidence(db_session, path) == 1
    assert db_session.query(SponsorRecord).count() == 1
    assert import_production_sponsor_evidence(db_session, path) == 0

    matching = NormalizedJob(
        external_id="job-1",
        provider=ATSProvider.GREENHOUSE,
        source_slug="acme",
        company_name="Acme Ltd",
        title="Backend Engineer",
        country="United Kingdom",
        apply_url="https://example.test/apply",
    )
    unrelated = matching.model_copy(update={"company_name": "Other Co", "country": "Germany"})
    records = Repository(db_session).sponsor_evidence_for_jobs([matching, unrelated])
    assert [record.company_name for record in records] == ["Acme Ltd"]


def test_production_sponsor_refresh_removes_stale_truth_and_reassesses_jobs(db_session, tmp_path):
    path = tmp_path / "sponsors.csv"
    path.write_text(
        "company_name,country,registry_name,source_url\n"
        "Acme Ltd,United Kingdom,UKVI,https://www.gov.uk/acme\n",
        encoding="utf-8",
    )
    assert import_production_sponsor_evidence(db_session, path) == 1

    normalized = NormalizedJob(
        external_id="job-refresh",
        provider=ATSProvider.GREENHOUSE,
        source_slug="acme",
        company_name="Acme Ltd",
        title="Backend Engineer",
        description="We welcome international applicants and offer relocation support.",
        country="United Kingdom",
        apply_url="https://example.test/apply-refresh",
    )
    repo = Repository(db_session)
    assessment = EligibilityEngine(SponsorRegistryStore(repo.sponsor_evidence())).assess(normalized)
    job = repo.upsert_job(normalized, assessment)
    db_session.commit()
    assert job.company.sponsor_verified is True
    assert job.eligibility_status == EligibilityStatus.ELIGIBLE.value

    path.write_text(
        "company_name,country,registry_name,source_url\n"
        "Other Ltd,United Kingdom,UKVI,https://www.gov.uk/other\n",
        encoding="utf-8",
    )
    assert import_production_sponsor_evidence(db_session, path) == 2
    db_session.refresh(job)
    db_session.refresh(job.company)
    assert job.company.sponsor_verified is False
    assert job.company_sponsor_status == "not_found"
    assert job.eligibility_status == EligibilityStatus.UNKNOWN.value


def test_unchanged_sponsor_snapshot_repairs_company_flags(db_session, tmp_path):
    path = tmp_path / "sponsors.csv"
    path.write_text(
        "company_name,country,registry_name,source_url\n"
        "Acme Ltd,United Kingdom,UKVI,https://www.gov.uk/acme\n",
        encoding="utf-8",
    )
    import_production_sponsor_evidence(db_session, path)
    company = Repository(db_session).upsert_company("Acme Ltd", "United Kingdom", sponsor_verified=False)
    db_session.commit()
    assert company.sponsor_verified is False

    assert import_production_sponsor_evidence(db_session, path) == 0
    db_session.refresh(company)
    assert company.sponsor_verified is True


def test_production_sponsor_import_matches_official_trading_alias(db_session, tmp_path):
    path = tmp_path / "sponsors.csv"
    path.write_text(
        "company_name,country,registry_name,source_url,aliases\n"
        "Acme Holdings Ltd trading as Bright Labs,United Kingdom,UKVI,https://www.gov.uk/acme,Bright AI\n",
        encoding="utf-8",
    )
    import_production_sponsor_evidence(db_session, path)
    repo = Repository(db_session)
    assert repo.find_sponsor_record("Bright Labs", "United Kingdom") is not None
    assert repo.find_sponsor_record("Bright AI", "United Kingdom") is not None
    job = NormalizedJob(
        external_id="alias-job",
        provider=ATSProvider.GREENHOUSE,
        source_slug="bright",
        company_name="Bright Labs",
        title="Backend Engineer",
        country="United Kingdom",
        apply_url="https://example.test/alias",
    )
    records = repo.sponsor_evidence_for_jobs([job])
    assert SponsorRegistryStore(records).find("Bright Labs", "United Kingdom") is not None

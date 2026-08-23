from __future__ import annotations

from europe_visa_jobs.db.models import SponsorRecord
from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.ingestion.sponsors import import_production_sponsor_evidence
from europe_visa_jobs.schemas import ATSProvider, NormalizedJob


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

from europe_visa_jobs.db.repository import Repository
from europe_visa_jobs.eligibility import EligibilityEngine
from europe_visa_jobs.schemas import (
    ATSProvider,
    CompanySponsorEvidence,
    EligibilityStatus,
    NormalizedJob,
)


def sample_job(external_id: str = "1") -> NormalizedJob:
    return NormalizedJob(
        external_id=external_id,
        provider=ATSProvider.GREENHOUSE,
        source_slug="acme",
        company_name="Acme",
        title="Backend Engineer",
        description="Visa sponsorship and relocation support are available.",
        location="Berlin, Germany",
        country="Germany",
        apply_url=f"https://example.com/{external_id}",
    )


def test_repository_upserts_job_and_replaces_evidence(db_session):
    repo = Repository(db_session)
    first = sample_job()
    assessment = EligibilityEngine().assess(first)
    stored = repo.upsert_job(first, assessment)
    db_session.commit()

    changed = sample_job()
    changed.title = "Senior Backend Engineer"
    stored_again = repo.upsert_job(changed, EligibilityEngine().assess(changed))
    db_session.commit()

    assert stored.id == stored_again.id
    assert repo.get_job(stored.id).title == "Senior Backend Engineer"
    assert repo.get_job(stored.id).eligibility_status == EligibilityStatus.ELIGIBLE.value
    assert len(repo.get_job(stored.id).evidence) > 0


def test_repository_marks_missing_source_jobs_inactive(db_session):
    repo = Repository(db_session)
    for external_id in ("1", "2"):
        item = sample_job(external_id)
        repo.upsert_job(item, EligibilityEngine().assess(item))
    repo.mark_source_jobs_inactive_except("greenhouse", "acme", {"2"})
    db_session.commit()

    assert repo.list_jobs(status=None)[0].external_id == "2"
    assert repo.get_job(1).active is False


def test_sponsor_record_normalized_lookup(db_session):
    repo = Repository(db_session)
    repo.add_sponsor_record(
        CompanySponsorEvidence(
            company_name="Acme B.V.",
            country="Netherlands",
            registry_name="IND",
            source_url="https://ind.nl",
        )
    )
    db_session.commit()
    assert repo.find_sponsor_record("Acme", "Netherlands") is not None

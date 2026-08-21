from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from europe_visa_jobs.db.models import Company, Job, JobEvidence, SponsorRecord
from europe_visa_jobs.schemas import (
    CompanySponsorEvidence,
    EligibilityAssessment,
    EligibilityStatus,
    NormalizedJob,
)
from europe_visa_jobs.utils import normalize_company_name


class Repository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_company(
        self,
        name: str,
        country: str | None,
        career_url: str | None = None,
        sponsor_verified: bool = False,
    ) -> Company:
        normalized = normalize_company_name(name)
        stmt = select(Company).where(
            Company.normalized_name == normalized,
            Company.country == country,
        )
        company = self.session.scalar(stmt)
        if company is None:
            company = Company(
                name=name,
                normalized_name=normalized,
                country=country,
                career_url=career_url,
                sponsor_verified=sponsor_verified,
            )
            self.session.add(company)
            self.session.flush()
        else:
            company.name = name
            company.career_url = career_url or company.career_url
            company.sponsor_verified = sponsor_verified or company.sponsor_verified
        return company

    def upsert_job(
        self,
        normalized_job: NormalizedJob,
        assessment: EligibilityAssessment,
        career_url: str | None = None,
    ) -> Job:
        sponsor = self.find_sponsor_record(normalized_job.company_name, normalized_job.country)
        company = self.upsert_company(
            normalized_job.company_name,
            normalized_job.country,
            career_url=career_url,
            sponsor_verified=sponsor is not None,
        )
        stmt = select(Job).where(
            Job.provider == normalized_job.provider.value,
            Job.source_slug == normalized_job.source_slug,
            Job.external_id == normalized_job.external_id,
        )
        job = self.session.scalar(stmt)
        if job is None:
            job = Job(
                company_id=company.id,
                external_id=normalized_job.external_id,
                provider=normalized_job.provider.value,
                source_slug=normalized_job.source_slug,
                company_name=normalized_job.company_name,
                title=normalized_job.title,
                description=normalized_job.description,
                location=normalized_job.location,
                country=normalized_job.country,
                department=normalized_job.department,
                employment_type=normalized_job.employment_type,
                workplace_type=normalized_job.workplace_type,
                apply_url=normalized_job.apply_url,
                job_url=normalized_job.job_url,
                posted_at=normalized_job.posted_at,
                job_family=normalized_job.job_family.value,
                eligibility_status=assessment.status.value,
                eligibility_score=assessment.score,
            )
            self.session.add(job)
            self.session.flush()
        else:
            job.company_id = company.id
            job.company_name = normalized_job.company_name
            job.title = normalized_job.title
            job.description = normalized_job.description
            job.location = normalized_job.location
            job.country = normalized_job.country
            job.department = normalized_job.department
            job.employment_type = normalized_job.employment_type
            job.workplace_type = normalized_job.workplace_type
            job.apply_url = normalized_job.apply_url
            job.job_url = normalized_job.job_url
            job.posted_at = normalized_job.posted_at
            job.job_family = normalized_job.job_family.value
            job.eligibility_status = assessment.status.value
            job.eligibility_score = assessment.score
            job.last_seen_at = datetime.now(UTC)
            job.active = True
            job.evidence.clear()
            self.session.flush()

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
        self.session.flush()
        return job

    def mark_source_jobs_inactive_except(
        self, provider: str, source_slug: str, seen_external_ids: set[str]
    ) -> int:
        stmt = select(Job).where(
            Job.provider == provider,
            Job.source_slug == source_slug,
            Job.active.is_(True),
        )
        changed = 0
        for job in self.session.scalars(stmt):
            if job.external_id not in seen_external_ids:
                job.active = False
                changed += 1
        self.session.flush()
        return changed

    def list_jobs(
        self,
        *,
        country: str | None = None,
        status: EligibilityStatus | None = EligibilityStatus.ELIGIBLE,
        job_family: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Job]:
        stmt = select(Job).where(Job.active.is_(True))
        if country:
            stmt = stmt.where(Job.country == country)
        if status:
            stmt = stmt.where(Job.eligibility_status == status.value)
        if job_family:
            stmt = stmt.where(Job.job_family == job_family)
        stmt = stmt.order_by(Job.posted_at.desc().nullslast(), Job.id.desc()).limit(limit).offset(offset)
        return list(self.session.scalars(stmt))

    def get_job(self, job_id: int) -> Job | None:
        return self.session.get(Job, job_id)

    def list_companies(self, *, country: str | None = None, limit: int = 100) -> list[Company]:
        stmt = select(Company)
        if country:
            stmt = stmt.where(Company.country == country)
        stmt = stmt.order_by(Company.name).limit(limit)
        return list(self.session.scalars(stmt))

    def add_sponsor_record(self, record: CompanySponsorEvidence) -> SponsorRecord:
        normalized = normalize_company_name(record.company_name)
        stmt = select(SponsorRecord).where(
            SponsorRecord.normalized_name == normalized,
            SponsorRecord.country == record.country,
            SponsorRecord.registry_name == record.registry_name,
        )
        existing = self.session.scalar(stmt)
        if existing:
            existing.company_name = record.company_name
            existing.source_url = record.source_url
            return existing
        item = SponsorRecord(
            company_name=record.company_name,
            normalized_name=normalized,
            country=record.country,
            registry_name=record.registry_name,
            source_url=record.source_url,
        )
        self.session.add(item)
        self.session.flush()
        return item

    def find_sponsor_record(self, company_name: str, country: str | None) -> SponsorRecord | None:
        if not country:
            return None
        normalized = normalize_company_name(company_name)
        return self.session.scalar(
            select(SponsorRecord).where(
                SponsorRecord.normalized_name == normalized,
                SponsorRecord.country == country,
            )
        )

    def sponsor_evidence(self) -> list[CompanySponsorEvidence]:
        records = self.session.scalars(select(SponsorRecord)).all()
        return [
            CompanySponsorEvidence(
                company_name=item.company_name,
                country=item.country,
                registry_name=item.registry_name,
                source_url=item.source_url,
            )
            for item in records
        ]

    def stats(self) -> dict[str, int]:
        def count_jobs(status: EligibilityStatus | None = None) -> int:
            stmt = select(func.count(Job.id)).where(Job.active.is_(True))
            if status:
                stmt = stmt.where(Job.eligibility_status == status.value)
            return int(self.session.scalar(stmt) or 0)

        return {
            "total_jobs": count_jobs(),
            "eligible_jobs": count_jobs(EligibilityStatus.ELIGIBLE),
            "rejected_jobs": count_jobs(EligibilityStatus.REJECTED),
            "unknown_jobs": count_jobs(EligibilityStatus.UNKNOWN),
            "companies": int(self.session.scalar(select(func.count(Company.id))) or 0),
        }

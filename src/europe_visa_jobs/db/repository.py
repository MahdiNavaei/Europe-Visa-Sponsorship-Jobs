from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from europe_visa_jobs.db.models import Candidate, Company, Job, JobEvidence, SponsorRecord
from europe_visa_jobs.intelligence.job_profile import analyze_job
from europe_visa_jobs.intelligence.ontology import SkillOntology
from europe_visa_jobs.schemas import (
    CandidateCreate,
    CompanySponsorEvidence,
    EligibilityAssessment,
    EligibilityStatus,
    JobFamily,
    NormalizedJob,
)
from europe_visa_jobs.utils import classify_role, normalize_company_name, normalize_country

_TRACKING_QUERY_KEYS = {"fbclid", "gclid", "ref", "source", "utm_campaign", "utm_medium", "utm_source", "utm_term"}


def _job_sponsorship_signal(assessment: EligibilityAssessment) -> str:
    positive = any(item.kind.value == "job_positive" for item in assessment.evidence)
    negative = any(item.kind.value == "job_negative" for item in assessment.evidence)
    if positive and negative:
        return "conflicting"
    if positive:
        return "confirmed_yes"
    if negative:
        return "confirmed_no"
    return "not_mentioned"


def canonicalize_apply_url(value: str | None) -> str | None:
    if not value:
        return None
    parts = urlsplit(value.strip())
    if not parts.netloc:
        return None
    query = urlencode([
        (key, item)
        for key, item in parse_qsl(parts.query, keep_blank_values=True)
        if key.casefold() not in _TRACKING_QUERY_KEYS
    ])
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.casefold() or "https", parts.netloc.casefold(), path, query, ""))


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
        classification_status: str = "technical",
    ) -> Job:
        sponsor = self.find_sponsor_record(normalized_job.company_name, normalized_job.country)
        company = self.upsert_company(
            normalized_job.company_name,
            normalized_job.country,
            career_url=career_url,
            sponsor_verified=sponsor is not None,
        )
        profile = analyze_job(normalized_job.title, normalized_job.description, normalized_job.job_family)
        canonical_apply_url = canonicalize_apply_url(normalized_job.apply_url)
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
                canonical_apply_url=canonical_apply_url,
                posted_at=normalized_job.posted_at,
                job_family=normalized_job.job_family.value,
                required_skills=profile.required_skills,
                preferred_skills=profile.preferred_skills,
                min_experience_years=profile.min_experience_years,
                seniority=profile.seniority.value if profile.seniority else None,
                eligibility_status=assessment.status.value,
                eligibility_score=assessment.score,
                classification_status=classification_status,
                job_sponsorship_signal=_job_sponsorship_signal(assessment),
                company_sponsor_status="verified_registry" if sponsor is not None else "not_found",
                final_candidate_eligibility=assessment.status.value,
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
            job.canonical_apply_url = canonical_apply_url
            job.posted_at = normalized_job.posted_at
            job.job_family = normalized_job.job_family.value
            job.required_skills = profile.required_skills
            job.preferred_skills = profile.preferred_skills
            job.min_experience_years = profile.min_experience_years
            job.seniority = profile.seniority.value if profile.seniority else None
            job.eligibility_status = assessment.status.value
            job.eligibility_score = assessment.score
            job.classification_status = classification_status
            job.job_sponsorship_signal = _job_sponsorship_signal(assessment)
            job.company_sponsor_status = "verified_registry" if sponsor is not None else "not_found"
            job.final_candidate_eligibility = assessment.status.value
            job.last_seen_at = datetime.now(UTC)
            job.active = True
            job.evidence.clear()
            self.session.flush()

        if canonical_apply_url:
            duplicate = self.session.scalar(
                select(Job)
                .where(
                    Job.canonical_apply_url == canonical_apply_url,
                    Job.id != job.id,
                    Job.active.is_(True),
                    Job.company_id == company.id,
                )
                .order_by(Job.id)
            )
            job.duplicate_of_job_id = duplicate.id if duplicate is not None else None

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
        company_id: int | None = None,
        query: str | None = None,
        min_eligibility_score: float | None = None,
        sort: str = "newest",
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
        if company_id is not None:
            stmt = stmt.where(Job.company_id == company_id)
        if query and query.strip():
            pattern = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    Job.title.ilike(pattern),
                    Job.company_name.ilike(pattern),
                    Job.description.ilike(pattern),
                )
            )
        if min_eligibility_score is not None:
            stmt = stmt.where(Job.eligibility_score >= min_eligibility_score)
        if sort == "visa":
            stmt = stmt.order_by(
                Job.eligibility_score.desc().nullslast(),
                Job.posted_at.desc().nullslast(),
                Job.id.desc(),
            )
        else:
            stmt = stmt.order_by(Job.posted_at.desc().nullslast(), Job.id.desc())
        stmt = stmt.limit(limit).offset(offset)
        return list(self.session.scalars(stmt))

    def count_jobs(
        self,
        *,
        country: str | None = None,
        status: EligibilityStatus | None = EligibilityStatus.ELIGIBLE,
        job_family: str | None = None,
        company_id: int | None = None,
        query: str | None = None,
        min_eligibility_score: float | None = None,
    ) -> int:
        stmt = select(func.count(Job.id)).where(Job.active.is_(True))
        if country:
            stmt = stmt.where(Job.country == country)
        if status:
            stmt = stmt.where(Job.eligibility_status == status.value)
        if job_family:
            stmt = stmt.where(Job.job_family == job_family)
        if company_id is not None:
            stmt = stmt.where(Job.company_id == company_id)
        if query and query.strip():
            pattern = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    Job.title.ilike(pattern),
                    Job.company_name.ilike(pattern),
                    Job.description.ilike(pattern),
                )
            )
        if min_eligibility_score is not None:
            stmt = stmt.where(Job.eligibility_score >= min_eligibility_score)
        return int(self.session.scalar(stmt) or 0)

    def list_recommendation_jobs(
        self,
        *,
        include_unknown: bool = False,
        limit: int | None = None,
        country: str | None = None,
        role: str | None = None,
        query: str | None = None,
    ) -> list[Job]:
        statuses = [EligibilityStatus.ELIGIBLE.value]
        if include_unknown:
            statuses.append(EligibilityStatus.UNKNOWN.value)
        stmt = (
            select(Job)
            .options(joinedload(Job.company), joinedload(Job.evidence))
            .where(Job.active.is_(True), Job.eligibility_status.in_(statuses))
        )
        if country:
            stmt = stmt.where(Job.country == country)
        if role:
            try:
                family = JobFamily(role)
            except ValueError:
                family = classify_role(role)
            if family is not JobFamily.OTHER:
                stmt = stmt.where(Job.job_family == family.value)
            else:
                stmt = stmt.where(or_(Job.title.ilike(f"%{role}%"), Job.job_family == role))
        if query and query.strip():
            pattern = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    Job.title.ilike(pattern),
                    Job.company_name.ilike(pattern),
                    Job.description.ilike(pattern),
                )
            )
        stmt = stmt.order_by(Job.posted_at.desc().nullslast(), Job.id.desc())
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.session.scalars(stmt).unique())

    def get_job(self, job_id: int) -> Job | None:
        stmt = (
            select(Job)
            .options(joinedload(Job.company), joinedload(Job.evidence))
            .where(Job.id == job_id)
        )
        return self.session.scalars(stmt).unique().first()

    def create_candidate(self, candidate: CandidateCreate) -> Candidate:
        ontology = SkillOntology()
        item = Candidate(
            name=candidate.name,
            target_roles=list(dict.fromkeys(candidate.target_roles)),
            skills=ontology.normalize_skills(candidate.skills),
            years_of_experience=candidate.years_of_experience,
            seniority=candidate.seniority.value if candidate.seniority else None,
            preferred_countries=list(dict.fromkeys(normalize_country(country) for country in candidate.preferred_countries)),
            visa_required=candidate.visa_required,
            relocation_preference=candidate.relocation_preference.value,
            remote_preference=candidate.remote_preference.value,
            excluded_locations=list(dict.fromkeys(item.strip() for item in candidate.excluded_locations)),
        )
        self.session.add(item)
        self.session.flush()
        return item

    def update_candidate(self, item: Candidate, candidate: CandidateCreate) -> Candidate:
        ontology = SkillOntology()
        item.name = candidate.name
        item.target_roles = list(dict.fromkeys(candidate.target_roles))
        item.skills = ontology.normalize_skills(candidate.skills)
        item.years_of_experience = candidate.years_of_experience
        item.seniority = candidate.seniority.value if candidate.seniority else None
        item.preferred_countries = list(
            dict.fromkeys(normalize_country(country) for country in candidate.preferred_countries)
        )
        item.visa_required = candidate.visa_required
        item.relocation_preference = candidate.relocation_preference.value
        item.remote_preference = candidate.remote_preference.value
        item.excluded_locations = list(dict.fromkeys(value.strip() for value in candidate.excluded_locations))
        item.updated_at = datetime.now(UTC)
        self.session.flush()
        return item

    def get_candidate(self, candidate_id: int) -> Candidate | None:
        return self.session.get(Candidate, candidate_id)

    def get_candidate_by_name(self, name: str) -> Candidate | None:
        return self.session.scalar(select(Candidate).where(Candidate.name == name))

    def list_companies(self, *, country: str | None = None, query: str | None = None, limit: int = 100, offset: int = 0) -> list[Company]:
        stmt = select(Company)
        if country:
            stmt = stmt.where(Company.country == country)
        if query and query.strip():
            stmt = stmt.where(Company.name.ilike(f"%{query.strip()}%"))
        stmt = stmt.order_by(Company.name).limit(limit).offset(offset)
        return list(self.session.scalars(stmt))

    def count_companies(self, *, country: str | None = None, query: str | None = None) -> int:
        stmt = select(func.count(Company.id))
        if country:
            stmt = stmt.where(Company.country == country)
        if query and query.strip():
            stmt = stmt.where(Company.name.ilike(f"%{query.strip()}%"))
        return int(self.session.scalar(stmt) or 0)

    def get_company(self, company_id: int) -> Company | None:
        return self.session.get(Company, company_id)

    def list_company_jobs(self, company_id: int, *, limit: int | None = 100, offset: int = 0) -> list[Job]:
        stmt = (
            select(Job)
            .options(joinedload(Job.company), joinedload(Job.evidence))
            .where(Job.company_id == company_id, Job.active.is_(True))
            .order_by(Job.posted_at.desc().nullslast(), Job.id.desc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        if offset:
            stmt = stmt.offset(offset)
        return list(self.session.scalars(stmt).unique())

    def count_company_jobs(self, company_id: int, *, eligibility_status: EligibilityStatus | None = None) -> int:
        stmt = select(func.count(Job.id)).where(Job.company_id == company_id, Job.active.is_(True))
        if eligibility_status is not None:
            stmt = stmt.where(Job.eligibility_status == eligibility_status.value)
        return int(self.session.scalar(stmt) or 0)

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

    def sponsor_evidence_for_jobs(self, jobs: list[NormalizedJob]) -> list[CompanySponsorEvidence]:
        """Read only evidence that can apply to the current source snapshot.

        A national sponsor register can contain hundreds of thousands of rows.
        Loading every row before every desktop refresh wastes memory and delays
        first results. Company/country lookup is indexed and preserves the same
        exact matching semantics as :meth:`sponsor_evidence`.
        """
        names = {normalize_company_name(job.company_name) for job in jobs if job.company_name}
        countries = {job.country for job in jobs if job.country}
        if not names or not countries:
            return []
        records = self.session.scalars(
            select(SponsorRecord).where(
                SponsorRecord.normalized_name.in_(names),
                SponsorRecord.country.in_(countries),
            )
        ).all()
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

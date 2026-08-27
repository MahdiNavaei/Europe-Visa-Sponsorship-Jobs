from __future__ import annotations

import re
from dataclasses import dataclass

from europe_visa_jobs.db.models import Candidate, Job
from europe_visa_jobs.intelligence.company import CompanyIntelligenceScorer
from europe_visa_jobs.intelligence.job_profile import JobProfile, analyze_job
from europe_visa_jobs.intelligence.ontology import SkillOntology
from europe_visa_jobs.schemas import EligibilityStatus, JobFamily, PreferenceLevel, SeniorityLevel
from europe_visa_jobs.utils.countries import normalize_country
from europe_visa_jobs.utils.locations import remote_scope
from europe_visa_jobs.utils.roles import classify_role


@dataclass(frozen=True)
class MatchResult:
    visa_score: float
    skill_score: float
    experience_score: float
    country_score: float
    company_score: float
    required_skill_coverage: float
    preferred_skill_coverage: float
    seniority_match: float
    role_similarity: float
    matched_skills: list[str]
    missing_skills: list[str]
    missing_preferred_skills: list[str]
    reasons: list[str]
    warnings: list[str]
    company_positive_signals: list[str]
    company_negative_signals: list[str]
    profile: JobProfile


_LEVEL_ORDER = {
    SeniorityLevel.INTERN: 0,
    SeniorityLevel.JUNIOR: 1,
    SeniorityLevel.MID: 2,
    SeniorityLevel.SENIOR: 3,
    SeniorityLevel.STAFF: 4,
    SeniorityLevel.LEAD: 4,
    SeniorityLevel.PRINCIPAL: 5,
    SeniorityLevel.DIRECTOR: 6,
}


class CandidateMatcher:
    def __init__(self, ontology: SkillOntology | None = None, company_scorer: CompanyIntelligenceScorer | None = None) -> None:
        self.ontology = ontology or SkillOntology()
        self.company_scorer = company_scorer or CompanyIntelligenceScorer()

    def match(self, candidate: Candidate, job: Job) -> MatchResult:
        profile = analyze_job(job.title, job.description, self._effective_job_family(job), ontology=self.ontology)
        # Persisted intelligence is authoritative when available, while old Phase-1 rows remain
        # fully matchable through the deterministic analyzer.
        if job.required_skills or job.preferred_skills or job.min_experience_years is not None or job.seniority:
            profile = JobProfile(list(job.required_skills), list(job.preferred_skills), job.min_experience_years, SeniorityLevel(job.seniority) if job.seniority else profile.seniority, profile.job_family)

        candidate_skills = {skill.casefold(): skill for skill in self.ontology.normalize_skills(candidate.skills)}
        required = self.ontology.normalize_skills(profile.required_skills)
        preferred = self.ontology.normalize_skills(profile.preferred_skills)
        matched_required = [skill for skill in required if skill.casefold() in candidate_skills]
        matched_preferred = [skill for skill in preferred if skill.casefold() in candidate_skills]
        missing = [skill for skill in required if skill.casefold() not in candidate_skills]
        missing_preferred = [skill for skill in preferred if skill.casefold() not in candidate_skills]
        required_coverage = self._coverage(len(matched_required), len(required))
        preferred_coverage = self._coverage(len(matched_preferred), len(preferred))
        if required and preferred:
            skill_score = 100 * (0.7 * required_coverage + 0.3 * preferred_coverage)
        elif required:
            skill_score = 100 * required_coverage
        elif preferred:
            skill_score = 100 * preferred_coverage
        else:
            # Missing requirements are unknown, not a perfect candidate match.
            skill_score = 50.0

        seniority_match = self._seniority_match(candidate.seniority, profile.seniority)
        experience_score = self._experience_match(
            candidate.years_of_experience,
            profile.min_experience_years,
            seniority_match,
            seniority_known=bool(candidate.seniority and profile.seniority),
        )
        role_similarity = self._role_similarity(candidate.target_roles, job.title, profile.job_family)
        country_score, country_reasons, country_warnings = self._country_match(candidate, job)
        visa_score, visa_reasons, visa_warnings = self._visa_match(candidate, job)
        company = self.company_scorer.score(job.company, job)

        reasons = list(country_reasons) + list(visa_reasons) + list(company.positive_signals)
        warnings = list(country_warnings) + list(visa_warnings) + list(company.negative_signals)
        if matched_required:
            reasons.append(f"Matched required skills: {', '.join(matched_required)}.")
        if missing:
            warnings.append(f"Missing required skills: {', '.join(missing)}.")
        if not required and not preferred:
            warnings.append("The vacancy did not publish enough skill requirements to assess skill fit.")
        if role_similarity >= 0.9:
            reasons.append("The role aligns with the candidate's target role family.")
        elif role_similarity < 0.5:
            warnings.append("The role is outside the candidate's target role family.")
        if seniority_match >= 0.9:
            reasons.append("The role seniority matches the candidate profile.")
        elif profile.seniority:
            warnings.append("The role seniority differs from the candidate profile.")
        if profile.min_experience_years is None and profile.seniority is None:
            warnings.append("The vacancy did not publish enough experience requirements to assess experience fit.")

        return MatchResult(
            visa_score=visa_score,
            skill_score=skill_score,
            experience_score=experience_score,
            country_score=country_score,
            company_score=company.score,
            required_skill_coverage=required_coverage,
            preferred_skill_coverage=preferred_coverage,
            seniority_match=seniority_match,
            role_similarity=role_similarity,
            matched_skills=matched_required + matched_preferred,
            missing_skills=missing,
            missing_preferred_skills=missing_preferred,
            reasons=self._unique(reasons),
            warnings=self._unique(warnings),
            company_positive_signals=company.positive_signals,
            company_negative_signals=company.negative_signals,
            profile=profile,
        )

    @staticmethod
    def _effective_job_family(job: Job) -> JobFamily | str:
        """Prefer the current title classifier over stale persisted labels.

        Older databases may contain a ``data_engineering`` or ``devops_cloud``
        label produced by a broad phrase match. Explicitly non-technical titles
        must not inherit that label during recommendation scoring.
        """
        classified = classify_role(job.title)
        if classified is not JobFamily.OTHER:
            return classified
        if re.search(r"\b(?:product|program|programme|project) manager\b|\bservice designer\b|\b(?:sales|marketing|recruiter)\b", job.title, re.IGNORECASE):
            return JobFamily.OTHER
        return job.job_family

    @staticmethod
    def _coverage(matched: int, total: int) -> float:
        return matched / total if total else 0.5

    @staticmethod
    def _seniority_match(candidate_level: SeniorityLevel | str | None, job_level: SeniorityLevel | None) -> float:
        if not candidate_level or not job_level:
            return 0.5
        candidate = SeniorityLevel(candidate_level)
        distance = abs(_LEVEL_ORDER[candidate] - _LEVEL_ORDER[job_level])
        return {0: 1.0, 1: 0.8, 2: 0.5}.get(distance, 0.25)

    @staticmethod
    def _experience_match(
        years: float,
        minimum: float | None,
        seniority_match: float,
        *,
        seniority_known: bool,
    ) -> float:
        if minimum is None:
            return 100 * seniority_match
        years_score = min(1.0, years / minimum)
        # When no job seniority was published, score the explicit experience
        # requirement by itself rather than injecting a synthetic perfect fit.
        if not seniority_known:
            return 100 * years_score
        return 100 * (0.7 * years_score + 0.3 * seniority_match)

    @staticmethod
    def _role_similarity(target_roles: list[str], title: str, family: JobFamily) -> float:
        if not target_roles:
            return 0.5
        title_lower = title.casefold()
        target_families = [classify_role(role) for role in target_roles]
        if family in target_families and family is not JobFamily.OTHER:
            return 1.0

        software_specializations = {
            JobFamily.BACKEND,
            JobFamily.FRONTEND,
            JobFamily.FULLSTACK,
            JobFamily.MOBILE,
            JobFamily.QA_AUTOMATION,
            JobFamily.SECURITY_ENGINEERING,
        }
        # "Software Engineering" is intentionally a broad target role. A user
        # choosing it should still strongly match a concrete backend/frontend/
        # full-stack/mobile vacancy instead of being treated as unrelated.
        if JobFamily.SOFTWARE_ENGINEERING in target_families and family in software_specializations:
            return 0.9
        if family is JobFamily.SOFTWARE_ENGINEERING and any(
            target in software_specializations for target in target_families
        ):
            return 0.85

        related_families = {
            JobFamily.AI_ML: {JobFamily.DATA_SCIENCE, JobFamily.MLOPS},
            JobFamily.DATA_SCIENCE: {JobFamily.AI_ML, JobFamily.MLOPS},
            JobFamily.MLOPS: {JobFamily.AI_ML, JobFamily.DATA_SCIENCE, JobFamily.DEVOPS_CLOUD},
            JobFamily.DEVOPS_CLOUD: {JobFamily.MLOPS, JobFamily.BACKEND},
            JobFamily.BACKEND: {JobFamily.FULLSTACK, JobFamily.DEVOPS_CLOUD},
            JobFamily.FRONTEND: {JobFamily.FULLSTACK},
            JobFamily.FULLSTACK: {JobFamily.BACKEND, JobFamily.FRONTEND},
        }
        if any(family in related_families.get(target, set()) for target in target_families):
            return 0.75
        if any(
            re.search(rf"(?<!\w){re.escape(role.casefold())}(?!\w)", title_lower)
            or re.search(rf"(?<!\w){re.escape(title_lower)}(?!\w)", role.casefold())
            for role in target_roles
        ):
            return 0.85
        return 0.2

    @staticmethod
    def _country_match(candidate: Candidate, job: Job) -> tuple[float, list[str], list[str]]:
        country = normalize_country(job.country) if job.country else None
        location = job.location.casefold()
        remote_geography = remote_scope(job.location)
        excluded = [value.casefold() for value in candidate.excluded_locations]
        if any(value in location or value == (country or "").casefold() for value in excluded):
            return 0.0, [], ["The job location is excluded by the candidate."]
        preferred = {normalize_country(value).casefold() for value in candidate.preferred_countries}
        if remote_geography == "us_only":
            return 0.0, [], ["The remote role is restricted to the United States/North America."]
        if remote_geography == "europe" and not country:
            country_score = 0.65 if not preferred else 0.75
        else:
            country_score = 1.0 if country and country.casefold() in preferred else (0.65 if not preferred else 0.35)
        reasons = [f"The job is in preferred country {country}."] if country and country.casefold() in preferred else []
        warnings = [] if reasons or not preferred else [f"The job country {country or 'unknown'} is not in the preferred countries."]
        if remote_geography == "europe" and not country:
            reasons.append("The remote role is explicitly limited to Europe/EEA markets.")
            warnings = []

        workplace = (job.workplace_type or "").casefold()
        is_remote = "remote" in workplace or "remote" in location
        if candidate.remote_preference == PreferenceLevel.REQUIRED and not is_remote:
            return 0.0, reasons, [*warnings, "The candidate requires remote work."]
        if candidate.remote_preference == PreferenceLevel.PREFERRED and is_remote:
            country_score = min(1.0, country_score + 0.1)
            reasons.append("Remote work matches the candidate preference.")
        if candidate.relocation_preference == PreferenceLevel.REQUIRED and country and country.casefold() not in preferred:
            warnings.append("Relocation is required but this country is not preferred.")
        return min(1.0, country_score), reasons, warnings

    @staticmethod
    def _visa_match(candidate: Candidate, job: Job) -> tuple[float, list[str], list[str]]:
        status = EligibilityStatus(job.eligibility_status) if job.eligibility_status else EligibilityStatus.UNKNOWN
        if candidate.visa_required:
            if status is EligibilityStatus.ELIGIBLE:
                return 1.0, ["The job passed the strict sponsorship eligibility gate."], []
            if status is EligibilityStatus.UNKNOWN:
                return 0.25, [], ["Sponsorship evidence is incomplete for a candidate who needs a visa."]
            return 0.0, [], ["The job failed the sponsorship eligibility gate."]
        if status is EligibilityStatus.REJECTED:
            return 0.25, [], ["The vacancy contains a work-authorization restriction."]
        return 1.0, ["The candidate does not require sponsorship."], []

    @staticmethod
    def _unique(values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))

from __future__ import annotations

import re

from europe_visa_jobs.schemas import JobFamily

ROLE_RULES: tuple[tuple[JobFamily, tuple[str, ...]], ...] = (
    (JobFamily.MLOPS, (r"\bmlops\b", r"machine learning platform", r"ml platform")),
    (
        JobFamily.AI_ML,
        (
            r"machine learning",
            r"\bml engineer",
            r"\bai\s*/\s*ml\b",
            r"\bai\s+(?:engineer|scientist|researcher|developer)\b",
            r"\b(?:edge|generative)\s+ai\b",
            r"artificial intelligence",
            r"\bnlp\b",
            r"computer vision",
            r"applied scientist",
            r"\bllm\b",
            r"deep learning",
            r"generative ai",
            r"\bgenai\b",
            r"\brag\b",
        ),
    ),
    # A bare "data platform" phrase also appears in non-technical product and
    # programme titles. Require an explicit technical role after the phrase.
    (JobFamily.DATA_ENGINEERING, (r"data engineer", r"analytics engineer", r"data platform\b.*\b(?:engineer|architect|developer)")),
    (JobFamily.DATA_SCIENCE, (r"data scientist", r"data science", r"decision scientist", r"decision science")),
    (JobFamily.FRONTEND, (r"front[ -]?end", r"frontend", r"react developer", r"ui engineer")),
    (JobFamily.BACKEND, (r"back[ -]?end", r"backend", r"server[- ]side")),
    (JobFamily.FULLSTACK, (r"full[ -]?stack", r"fullstack")),
    (JobFamily.MOBILE, (r"mobile engineer", r"android", r"ios engineer", r"flutter")),
    (JobFamily.DEVOPS_CLOUD, (r"devops", r"site reliability", r"\bsre\b", r"cloud engineer", r"\bplatform engineer\b", r"\binfrastructure engineer\b")),
    (JobFamily.QA_AUTOMATION, (r"qa automation", r"test automation", r"quality engineer", r"software test")),
    (JobFamily.SECURITY_ENGINEERING, (r"security engineer", r"application security", r"product security", r"cloud security")),
    (JobFamily.SOFTWARE_ENGINEERING, (r"software engineer", r"software developer", r"developer")),
)


def classify_role(title: str, department: str | None = None, description: str | None = None) -> JobFamily:
    lowered = f"{title} {department or ''}".casefold()
    # Generic "developer" is not enough evidence for a technical vacancy.
    # Keep common commercial roles auditable as nontechnical instead of allowing
    # a substring match to manufacture software jobs.
    if re.search(r"\b(?:business|sales|account|real estate)\s+developer\b", lowered):
        return JobFamily.OTHER
    if re.search(r"\b(?:sales|solutions)\s+engineer\b", lowered) and not re.search(
        r"\b(?:software|platform|data|cloud|systems|network|machine learning)\b", lowered
    ):
        return JobFamily.OTHER
    for family, patterns in ROLE_RULES:
        if any(re.search(pattern, lowered) for pattern in patterns):
            return family
    # Description is a secondary signal only. It can recover titles such as
    # "Platform Specialist" when the provider supplies a technical department,
    # without making a bare prose mention of "developer" classify a job.
    if description and re.search(r"\b(?:python|java|javascript|kubernetes|sql|machine learning|software development)\b", description.casefold()):
        return JobFamily.SOFTWARE_ENGINEERING
    return JobFamily.OTHER


def is_supported_tech_role(title: str, department: str | None = None, description: str | None = None) -> bool:
    return classify_role(title, department, description) is not JobFamily.OTHER

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
    (
        JobFamily.DATA_ENGINEERING,
        (
            r"data engineer(?:ing)?",
            r"analytics engineer(?:ing)?",
            r"data platform\b.*\b(?:engineer|engineering|architect|developer)",
        ),
    ),
    (JobFamily.DATA_SCIENCE, (r"data scientist", r"data science", r"decision scientist", r"decision science")),
    (JobFamily.FRONTEND, (r"front[ -]?end", r"frontend", r"react developer", r"ui engineer(?:ing)?")),
    (JobFamily.BACKEND, (r"back[ -]?end", r"backend", r"server[- ]side")),
    (JobFamily.FULLSTACK, (r"full[ -]?stack", r"fullstack")),
    (JobFamily.MOBILE, (r"mobile engineer(?:ing)?", r"android", r"ios engineer(?:ing)?", r"flutter")),
    (JobFamily.DEVOPS_CLOUD, (r"devops", r"site reliability", r"\bsre\b", r"cloud engineer(?:ing)?", r"\bplatform engineer(?:ing)?\b", r"\binfrastructure engineer(?:ing)?\b")),
    (JobFamily.QA_AUTOMATION, (r"qa automation", r"test automation", r"quality engineer(?:ing)?", r"software test")),
    (JobFamily.SECURITY_ENGINEERING, (r"security engineer(?:ing)?", r"application security", r"product security", r"cloud security")),
    (
        JobFamily.SOFTWARE_ENGINEERING,
        (
            r"software engineer(?:ing)?",
            r"software developer",
            r"software development",
            r"\bdeveloper\b",
        ),
    ),
)


def classify_role(title: str, department: str | None = None, description: str | None = None) -> JobFamily:
    lowered = f"{title} {department or ''}".casefold()
    # Explicit non-technical role shapes win before broad engineering/platform
    # phrases are evaluated. This prevents titles such as "Service Designer -
    # Platform Engineering" from becoming DevOps jobs.
    if re.search(r"\b(?:product|program|programme|project) manager\b|\bservice designer\b", lowered):
        return JobFamily.OTHER
    # Generic "developer" is not enough evidence for a technical vacancy when
    # it is explicitly a commercial/non-software role.
    if re.search(r"\b(?:business|sales|account|real estate)\s+developer\b", lowered):
        return JobFamily.OTHER
    if re.search(r"\b(?:sales|solutions)\s+engineer\b", lowered) and not re.search(
        r"\b(?:software|platform|data|cloud|systems|network|machine learning)\b", lowered
    ):
        return JobFamily.OTHER
    for family, patterns in ROLE_RULES:
        if any(re.search(pattern, lowered) for pattern in patterns):
            return family
    # Description may confirm an ambiguous technical-shaped title, but it must
    # not turn a Product Manager into an engineer just because prose mentions SQL.
    title_lower = title.casefold()
    department_lower = (department or "").casefold()
    technical_title = re.search(
        r"\b(?:platform|infrastructure|systems?|cloud|database|network|security|software|data)\b",
        title_lower,
    ) and re.search(
        r"\b(?:specialist|administrator|architect|consultant|engineer|engineering|developer)\b",
        title_lower,
    )
    technical_department_title = re.search(
        r"\b(?:engineering|technology|infrastructure|it|security|data)\b",
        department_lower,
    ) and re.search(r"\b(?:specialist|administrator|architect|engineer|engineering|developer)\b", title_lower)
    if (
        description
        and (technical_title or technical_department_title)
        and re.search(
            r"\b(?:python|java|javascript|kubernetes|sql|machine learning|software development)\b",
            description.casefold(),
        )
    ):
        return JobFamily.SOFTWARE_ENGINEERING
    return JobFamily.OTHER


def is_supported_tech_role(title: str, department: str | None = None, description: str | None = None) -> bool:
    return classify_role(title, department, description) is not JobFamily.OTHER

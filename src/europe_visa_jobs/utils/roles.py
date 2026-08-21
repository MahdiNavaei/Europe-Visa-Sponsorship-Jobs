from __future__ import annotations

import re

from europe_visa_jobs.schemas import JobFamily

ROLE_RULES: tuple[tuple[JobFamily, tuple[str, ...]], ...] = (
    (JobFamily.MLOPS, (r"\bmlops\b", r"machine learning platform", r"ml platform")),
    (JobFamily.AI_ML, (r"machine learning", r"\bml engineer", r"\bai engineer", r"artificial intelligence", r"\bnlp\b", r"computer vision", r"applied scientist", r"\bllm\b")),
    (JobFamily.DATA_ENGINEERING, (r"data engineer", r"analytics engineer", r"data platform")),
    (JobFamily.DATA_SCIENCE, (r"data scientist", r"decision scientist")),
    (JobFamily.FRONTEND, (r"front[ -]?end", r"frontend", r"react developer", r"ui engineer")),
    (JobFamily.BACKEND, (r"back[ -]?end", r"backend", r"server[- ]side")),
    (JobFamily.FULLSTACK, (r"full[ -]?stack", r"fullstack")),
    (JobFamily.MOBILE, (r"mobile engineer", r"android", r"ios engineer", r"flutter")),
    (JobFamily.DEVOPS_CLOUD, (r"devops", r"site reliability", r"\bsre\b", r"cloud engineer", r"platform engineer", r"infrastructure engineer")),
    (JobFamily.QA_AUTOMATION, (r"qa automation", r"test automation", r"quality engineer", r"software test")),
    (JobFamily.SOFTWARE_ENGINEERING, (r"software engineer", r"software developer", r"developer")),
)


def classify_role(title: str) -> JobFamily:
    lowered = title.casefold()
    for family, patterns in ROLE_RULES:
        if any(re.search(pattern, lowered) for pattern in patterns):
            return family
    return JobFamily.OTHER


def is_supported_tech_role(title: str) -> bool:
    return classify_role(title) is not JobFamily.OTHER

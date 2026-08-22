from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 5 * 1024 * 1024
SELF = Path("scripts/public_repo_audit.py")

FORBIDDEN_PARTS = {
    "node_modules",
    ".next",
    "playwright-report",
    "test-results",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
}
FORBIDDEN_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".pyc", ".pyo"}
ALLOWED_ENV_FILES = {".env.example", ".env.production.example"}

SECRET_PATTERNS: dict[str, re.Pattern[str]] = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "OpenAI-style key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
}
LOCAL_PATH_PATTERN = re.compile(r"(?:[A-Za-z]:\\Users\\|[A-Za-z]:\\Projects\\|/home/[^/]+/)")


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / item.decode() for item in result.stdout.split(b"\0") if item]


def audit() -> list[str]:
    failures: list[str] = []

    for path in tracked_files():
        relative = path.relative_to(ROOT)
        parts = set(relative.parts)

        if parts & FORBIDDEN_PARTS:
            failures.append(f"development artifact is tracked: {relative}")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            failures.append(f"local data/build file is tracked: {relative}")
        if path.name.startswith(".env") and path.name not in ALLOWED_ENV_FILES:
            failures.append(f"real environment file is tracked: {relative}")
        if path.exists() and path.stat().st_size > MAX_FILE_BYTES:
            failures.append(f"tracked file exceeds 5 MiB: {relative}")

        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        # The audit implementation necessarily contains the detection patterns themselves.
        if relative != SELF and LOCAL_PATH_PATTERN.search(content):
            failures.append(f"local absolute path found in: {relative}")

        if relative != SELF:
            for label, pattern in SECRET_PATTERNS.items():
                if pattern.search(content):
                    failures.append(f"possible {label} found in: {relative}")

    return sorted(set(failures))


def main() -> int:
    failures = audit()
    if failures:
        print("Public repository audit failed:")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("Public repository audit passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

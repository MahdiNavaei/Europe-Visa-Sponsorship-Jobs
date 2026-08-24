from __future__ import annotations

import html
import re
import unicodedata

from bs4 import BeautifulSoup


def html_to_text(value: str | None) -> str:
    if not value:
        return ""
    soup = BeautifulSoup(html.unescape(value), "html.parser")
    return " ".join(soup.stripped_strings)


def normalize_whitespace(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def normalize_company_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().replace("&", " and ")
    normalized = re.sub(
        r"\b(limited|ltd|gmbh|b\.v\.?|bv|n\.v\.?|nv|plc|incorporated|inc|llc|oy|ab|as|a/s|sa|sarl|se)\b",
        " ",
        normalized,
    )
    return re.sub(r"[^a-z0-9]+", " ", normalized).strip()


def company_name_quality(value: str | None) -> str:
    """Classify display-name trust without treating an ATS slug as an employer identity."""
    raw = normalize_whitespace(value)
    normalized = normalize_company_name(raw)
    if not normalized or len(normalized) < 3 or re.fullmatch(r"[0-9\s_-]+", raw or ""):
        return "untrusted"
    letters = sum(character.isalpha() for character in raw)
    digits = sum(character.isdigit() for character in raw)
    if digits > letters and digits >= 3:
        return "untrusted"
    compact = re.sub(r"[^a-z0-9]", "", raw.casefold())
    vowels = sum(character in "aeiouy" for character in compact)
    # Common ingestion garbage is a single opaque alphanumeric identifier
    # (for example ``12jlkfsk``), not an employer display name. Keep familiar
    # brands such as 1Password/3M outside this deliberately narrow rule.
    if (
        compact == raw.casefold()
        and len(compact) >= 7
        and digits >= 2
        and letters >= 4
        and vowels / letters <= 0.15
    ):
        return "untrusted"
    if raw.startswith(("http://", "https://")) or "@" in raw:
        return "untrusted"
    return "verified"

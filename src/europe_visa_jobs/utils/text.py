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

from __future__ import annotations

import re

COUNTRY_ALIASES: dict[str, tuple[str, ...]] = {
    "Netherlands": ("netherlands", "the netherlands", "holland"),
    "Germany": ("germany", "deutschland"),
    "United Kingdom": ("united kingdom", "uk", "u.k.", "great britain", "england", "scotland", "wales"),
    "Ireland": ("ireland",),
    "Sweden": ("sweden",),
    "Finland": ("finland",),
    "Denmark": ("denmark",),
    "Norway": ("norway",),
    "Austria": ("austria",),
    "France": ("france",),
    "Spain": ("spain",),
    "Portugal": ("portugal",),
    "Belgium": ("belgium",),
    "Estonia": ("estonia",),
    "Poland": ("poland",),
    "Czechia": ("czechia", "czech republic"),
    "Switzerland": ("switzerland",),
}

CITY_COUNTRY: dict[str, str] = {
    "amsterdam": "Netherlands",
    "rotterdam": "Netherlands",
    "utrecht": "Netherlands",
    "eindhoven": "Netherlands",
    "berlin": "Germany",
    "munich": "Germany",
    "hamburg": "Germany",
    "frankfurt": "Germany",
    "cologne": "Germany",
    "london": "United Kingdom",
    "manchester": "United Kingdom",
    "edinburgh": "United Kingdom",
    "dublin": "Ireland",
    "cork": "Ireland",
    "stockholm": "Sweden",
    "gothenburg": "Sweden",
    "helsinki": "Finland",
    "espoo": "Finland",
    "copenhagen": "Denmark",
    "aarhus": "Denmark",
}


def infer_country(location: str | None, default: str | None = None) -> str | None:
    if not location:
        return default
    lowered = location.casefold()
    for country, aliases in COUNTRY_ALIASES.items():
        for alias in aliases:
            if re.search(rf"(?<![\w]){re.escape(alias)}(?![\w])", lowered):
                return country
    for city, country in CITY_COUNTRY.items():
        if city in lowered:
            return country
    return default


def normalize_country(value: str) -> str:
    """Return the canonical country label when a known alias is supplied."""
    cleaned = re.sub(r"\s+", " ", value.strip()).casefold()
    for country, aliases in COUNTRY_ALIASES.items():
        if cleaned == country.casefold() or cleaned in {alias.casefold() for alias in aliases}:
            return country
    return value.strip()

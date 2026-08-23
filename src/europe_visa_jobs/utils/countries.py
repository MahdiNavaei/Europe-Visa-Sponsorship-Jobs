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
    # Additional credible European hiring markets. Keep geography explicit;
    # broad labels such as "international" or "EMEA" remain non-country
    # signals and are handled separately by remote_scope().
    "Italy": ("italy",),
    "Hungary": ("hungary",),
    "Greece": ("greece",),
    "Romania": ("romania",),
    "Lithuania": ("lithuania",),
    "Latvia": ("latvia",),
    "Croatia": ("croatia",),
    "Slovenia": ("slovenia",),
    "Slovakia": ("slovakia",),
    "Bulgaria": ("bulgaria",),
    "Luxembourg": ("luxembourg",),
    "Iceland": ("iceland",),
    "Serbia": ("serbia",),
    "Ukraine": ("ukraine",),
    "Moldova": ("moldova",),
    "Albania": ("albania",),
    "North Macedonia": ("north macedonia",),
    "Bosnia and Herzegovina": ("bosnia and herzegovina",),
    "Montenegro": ("montenegro",),
    "Kosovo": ("kosovo",),
    "Cyprus": ("cyprus",),
    "Malta": ("malta",),
}

EUROPEAN_COUNTRIES = frozenset(COUNTRY_ALIASES)

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
    "oslo": "Norway",
    "paris": "France",
    "lyon": "France",
    "madrid": "Spain",
    "barcelona": "Spain",
    "valencia": "Spain",
    "lisbon": "Portugal",
    "porto": "Portugal",
    "brussels": "Belgium",
    "antwerp": "Belgium",
    "tallinn": "Estonia",
    "warsaw": "Poland",
    "krakow": "Poland",
    "prague": "Czechia",
    "zurich": "Switzerland",
    "geneva": "Switzerland",
    "vienna": "Austria",
    "rome": "Italy",
    "milan": "Italy",
    "budapest": "Hungary",
    "athens": "Greece",
    "bucharest": "Romania",
    "cluj": "Romania",
    "vilnius": "Lithuania",
    "riga": "Latvia",
    "zagreb": "Croatia",
    "ljubljana": "Slovenia",
    "bratislava": "Slovakia",
    "sofia": "Bulgaria",
    "reykjavik": "Iceland",
    "belgrade": "Serbia",
    "kyiv": "Ukraine",
    "kiev": "Ukraine",
    "chisinau": "Moldova",
    "tirana": "Albania",
    "skopje": "North Macedonia",
    "sarajevo": "Bosnia and Herzegovina",
    "podgorica": "Montenegro",
    "pristina": "Kosovo",
    "nicosia": "Cyprus",
    "valletta": "Malta",
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

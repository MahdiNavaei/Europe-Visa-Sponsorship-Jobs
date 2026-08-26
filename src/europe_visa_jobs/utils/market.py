from __future__ import annotations

from enum import StrEnum

from europe_visa_jobs.utils.countries import (
    EUROPEAN_COUNTRIES,
    infer_country,
    normalize_country,
)
from europe_visa_jobs.utils.locations import remote_scope


class MarketScope(StrEnum):
    """The fail-closed scope decision for the default Career Radar catalog."""

    SUPPORTED_COUNTRY = "supported_country"
    REMOTE_EUROPE = "remote_europe"
    OUTSIDE_EUROPE = "outside_europe"
    AMBIGUOUS_REMOTE = "ambiguous_remote"
    UNKNOWN_LOCATION = "unknown_location"


def market_scope(country: str | None, location: str | None) -> MarketScope:
    """Classify a vacancy against the documented European product boundary.

    A known supported country or a multi-location string containing a supported
    European location is included. Only explicitly Europe-limited remote roles
    are included without a country. Global, EMEA, unspecified remote, unknown,
    and non-European locations fail closed.
    """
    if country and normalize_country(country) in EUROPEAN_COUNTRIES:
        return MarketScope.SUPPORTED_COUNTRY
    if infer_country(location) in EUROPEAN_COUNTRIES:
        return MarketScope.SUPPORTED_COUNTRY

    scope = remote_scope(location)
    if scope == "europe":
        return MarketScope.REMOTE_EUROPE
    if scope in {"emea", "worldwide", "unspecified", "us_only"}:
        return MarketScope.AMBIGUOUS_REMOTE
    if country or (location and location.strip()):
        return MarketScope.OUTSIDE_EUROPE
    return MarketScope.UNKNOWN_LOCATION


def is_supported_market_job(country: str | None, location: str | None) -> bool:
    return market_scope(country, location) in {
        MarketScope.SUPPORTED_COUNTRY,
        MarketScope.REMOTE_EUROPE,
    }

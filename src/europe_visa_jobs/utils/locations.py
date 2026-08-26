from __future__ import annotations


def remote_scope(location: str | None) -> str:
    """Classify remote geography without pretending a remote role has a city."""
    value = (location or "").casefold()
    if "remote" not in value:
        return "not_remote"
    if any(token in value for token in ("us only", "usa only", "united states", "north america")):
        return "us_only"
    # EMEA includes the Middle East and Africa, so it is not evidence of a
    # Europe/EEA restriction.
    if "emea" in value:
        return "emea"
    if any(token in value for token in ("worldwide", "global", "anywhere")):
        return "worldwide"
    if "europe" in value or "european union" in value or "eu" in value.split():
        return "europe"
    return "unspecified"

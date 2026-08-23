from __future__ import annotations


def remote_scope(location: str | None) -> str:
    """Classify remote geography without pretending a remote role has a city."""
    value = (location or "").casefold()
    if "remote" not in value:
        return "not_remote"
    if any(token in value for token in ("us only", "usa only", "united states", "north america")):
        return "us_only"
    if any(token in value for token in ("europe", "eu", "emea", "european union")):
        return "europe"
    if any(token in value for token in ("worldwide", "global", "anywhere")):
        return "worldwide"
    return "unspecified"

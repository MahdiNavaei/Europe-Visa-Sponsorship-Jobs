from __future__ import annotations

from collections.abc import Collection
from ipaddress import ip_address
from socket import gaierror, getaddrinfo
from urllib.parse import urljoin, urlsplit


class UnsafeUrlError(ValueError):
    pass


_PROVIDER_ALLOWED_HOSTS: dict[str, frozenset[str]] = {
    "greenhouse": frozenset({"boards-api.greenhouse.io"}),
    "lever": frozenset({"api.lever.co", "api.eu.lever.co"}),
    "ashby": frozenset({"api.ashbyhq.com", "jobs.ashbyhq.com"}),
    "workable": frozenset({"apply.workable.com"}),
    "personio": frozenset({"*.jobs.personio.com", "*.jobs.personio.de"}),
    "teamtailor": frozenset({"api.teamtailor.com", "*.teamtailor.com"}),
    "recruitee": frozenset({"*.recruitee.com"}),
    "smartrecruiters": frozenset({"api.smartrecruiters.com"}),
}


def provider_allowed_hosts(provider: str, configured_url: str | None = None) -> frozenset[str]:
    """Return the provider hosts that a connector is allowed to contact."""

    hosts = set(_PROVIDER_ALLOWED_HOSTS.get(provider.casefold(), frozenset()))
    if provider.casefold() == "workday" and configured_url:
        configured_host = urlsplit(configured_url).hostname
        if configured_host:
            hosts.add(configured_host.casefold().rstrip("."))
    return frozenset(hosts)


def _host_is_allowed(hostname: str, allowed_hosts: Collection[str]) -> bool:
    for allowed in allowed_hosts:
        normalized = allowed.casefold().rstrip(".")
        if normalized.startswith("*."):
            suffix = normalized[1:]
            if hostname.endswith(suffix) and hostname != suffix[1:]:
                return True
        elif hostname == normalized:
            return True
    return False


def validate_public_http_url(
    value: str,
    *,
    allowed_hosts: Collection[str] | None = None,
) -> str:
    """Reject URL forms that can directly target local infrastructure.

    Literal IPs, local hostnames, credentials, non-web schemes, unresolved DNS
    and non-public DNS answers are rejected here. Redirect hops must be passed
    through this function as well. Connector callers also provide a provider
    host allowlist so a source cannot become an arbitrary URL fetcher.
    """

    candidate = value.strip()
    parts = urlsplit(candidate)
    if parts.scheme.casefold() not in {"http", "https"} or not parts.hostname:
        raise UnsafeUrlError("only absolute http(s) URLs are allowed")
    if parts.username or parts.password:
        raise UnsafeUrlError("URL credentials are not allowed")
    hostname = parts.hostname.casefold().rstrip(".")
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith((".localhost", ".local", ".internal")):
        raise UnsafeUrlError("local hostnames are not allowed")
    if allowed_hosts is not None and not _host_is_allowed(hostname, allowed_hosts):
        raise UnsafeUrlError("hostname is outside the provider allowlist")
    try:
        addresses = {ip_address(item[4][0]) for item in getaddrinfo(hostname, None)}
    except gaierror:
        raise UnsafeUrlError("hostname DNS resolution failed") from None
    except ValueError:
        addresses = {ip_address(hostname)}
    if not addresses:
        raise UnsafeUrlError("hostname DNS resolution returned no addresses")
    if any(not address.is_global for address in addresses):
        raise UnsafeUrlError("hostname resolves to a non-public IP address")
    return candidate


def validated_redirect(
    current_url: str,
    location: str,
    *,
    allowed_hosts: Collection[str] | None = None,
) -> str:
    return validate_public_http_url(urljoin(current_url, location), allowed_hosts=allowed_hosts)

from __future__ import annotations

from ipaddress import ip_address
from socket import gaierror, getaddrinfo
from urllib.parse import urljoin, urlsplit


class UnsafeUrlError(ValueError):
    pass


def validate_public_http_url(value: str) -> str:
    """Reject URL forms that can directly target local infrastructure.

    Hostname DNS is intentionally resolved by the HTTP stack, but literal IPs,
    local hostnames, credentials and non-web schemes are rejected here. Redirect
    hops must be passed through this function as well.
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
    try:
        addresses = {ip_address(item[4][0]) for item in getaddrinfo(hostname, None)}
    except gaierror:
        # The HTTP request will provide the final transport error. Keeping
        # reserved test domains usable also lets MockTransport tests exercise
        # redirect policy without real DNS.
        addresses = set()
    except ValueError:
        addresses = {ip_address(hostname)}
    if any(not address.is_global for address in addresses):
        raise UnsafeUrlError("hostname resolves to a non-public IP address")
    return candidate


def validated_redirect(current_url: str, location: str) -> str:
    return validate_public_http_url(urljoin(current_url, location))

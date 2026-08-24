from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from time import monotonic
from typing import Any

import httpx

from europe_visa_jobs.settings import get_settings
from europe_visa_jobs.utils.url_security import (
    UnsafeUrlError,
    validate_public_http_url,
    validated_redirect,
)


@dataclass
class PublicResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes
    duration_ms: int
    not_modified: bool = False


class PublicFetchError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        category: str = "network",
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.category = category
        self.retry_after_seconds = retry_after_seconds


def _retryable(status: int | None, category: str) -> bool:
    return category in {"timeout", "network", "server_error", "rate_limited"} or status in {429, 500, 502, 503, 504}


def _delay(response: httpx.Response | None, attempt: int) -> float:
    if response is not None:
        value = response.headers.get("retry-after")
        if value:
            try:
                return min(float(value), 30.0)
            except ValueError:
                try:
                    retry_at = parsedate_to_datetime(value).timestamp()
                    return min(max(retry_at - time.time(), 0.0), 30.0)
                except (TypeError, ValueError, OverflowError):
                    pass
    return min((2**attempt) + random.uniform(0, 0.35), 30.0)


def _retry_after_seconds(response: httpx.Response | None) -> int | None:
    if response is None:
        return None
    value = response.headers.get("retry-after")
    if not value:
        return None
    try:
        return max(0, int(float(value)))
    except ValueError:
        try:
            return max(0, int(parsedate_to_datetime(value).timestamp() - time.time()))
        except (TypeError, ValueError, OverflowError):
            return None


async def fetch_public(
    client: httpx.AsyncClient,
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    etag: str | None = None,
    last_modified: str | None = None,
    retries: int | None = None,
    timeout: float | None = None,
) -> PublicResponse:
    settings = get_settings()
    attempts = retries if retries is not None else settings.discovery_retry_attempts
    request_headers = {
        "User-Agent": settings.discovery_user_agent,
        "Accept": "application/json, application/xml, text/xml, text/html;q=0.8, */*;q=0.1",
        **(headers or {}),
    }
    if etag:
        request_headers["If-None-Match"] = etag
    if last_modified:
        request_headers["If-Modified-Since"] = last_modified
    for attempt in range(max(attempts, 1)):
        started = monotonic()
        response: httpx.Response | None = None
        category = "network"
        try:
            current_url = validate_public_http_url(url)
            for _ in range(6):
                response = await client.request(
                    method,
                    current_url,
                    headers=request_headers,
                    params=params,
                    timeout=timeout,
                    follow_redirects=False,
                )
                if response.is_redirect and response.headers.get("location"):
                    current_url = validated_redirect(current_url, response.headers["location"])
                    continue
                break
            else:
                raise PublicFetchError(f"{url} exceeded redirect limit", category="redirect")
            duration_ms = int((monotonic() - started) * 1000)
            if response.status_code == 304:
                return PublicResponse(response.status_code, dict(response.headers), b"", duration_ms, True)
            if 200 <= response.status_code < 400:
                return PublicResponse(response.status_code, dict(response.headers), response.content, duration_ms)
            if response.status_code in {401, 403}:
                raise PublicFetchError(f"{url} returned HTTP {response.status_code}", status_code=response.status_code, category="blocked")
            if response.status_code == 404:
                raise PublicFetchError(f"{url} returned HTTP 404", status_code=404, category="not_found")
            if response.status_code == 429:
                category = "rate_limited"
            elif response.status_code >= 500:
                category = "server_error"
            else:
                category = "http_error"
            if attempt == attempts - 1:
                raise PublicFetchError(
                    f"{url} returned HTTP {response.status_code}",
                    status_code=response.status_code,
                    category=category,
                    retry_after_seconds=_retry_after_seconds(response),
                )
        except httpx.TimeoutException as exc:
            if attempt == attempts - 1:
                raise PublicFetchError(f"{url} timed out", category="timeout") from exc
        except httpx.NetworkError as exc:
            if attempt == attempts - 1:
                raise PublicFetchError(f"{url} network error: {exc}", category="network") from exc
        except UnsafeUrlError as exc:
            raise PublicFetchError(f"{url} is unsafe: {exc}", category="unsafe_url") from exc
        if _retryable(response.status_code if response else None, category):
            await asyncio.sleep(_delay(response, attempt))
    raise PublicFetchError(f"{url} failed after retries")

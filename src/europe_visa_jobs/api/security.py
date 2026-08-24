from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque
from ipaddress import ip_address
from threading import Lock

from fastapi import HTTPException, Request, Response

from europe_visa_jobs.db.models import Candidate

TOKEN_HEADER = "X-Candidate-Token"
LEGACY_WARNING = '299 CareerRadar "Legacy profile has no access token; recreate it before remote use"'


def issue_candidate_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hash_candidate_token(token)


def hash_candidate_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _is_loopback(request: Request) -> bool:
    host = request.client.host if request.client else ""
    if host == "testclient":  # Starlette's in-process TestClient; never a network peer.
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def authorize_candidate(request: Request, response: Response, candidate: Candidate) -> None:
    """Authorize access without leaking whether another candidate id exists.

    Old desktop databases predate per-profile tokens. They remain usable only
    through a real loopback connection and receive a deprecation warning.
    """

    if candidate.access_token_hash is None:
        if _is_loopback(request):
            response.headers["Warning"] = LEGACY_WARNING
            return
        raise HTTPException(status_code=404, detail="Candidate not found")
    token = request.headers.get(TOKEN_HEADER, "")
    supplied = hash_candidate_token(token) if token else ""
    if not token or not hmac.compare_digest(supplied, candidate.access_token_hash):
        raise HTTPException(status_code=404, detail="Candidate not found")


class SlidingWindowRateLimiter:
    """Small per-process guardrail for expensive and profile-mutating routes."""

    def __init__(self, *, requests: int, window_seconds: float) -> None:
        self.requests = requests
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.requests:
                return False
            events.append(now)
            return True

from __future__ import annotations

import json
import logging
import threading
from collections import Counter, defaultdict
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import RequestResponseEndpoint


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "method", "path", "status", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_structured_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("europe_visa_jobs")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(level.upper())
    logger.propagate = False


class RequestMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: Counter[tuple[str, str, int]] = Counter()
        self._duration_seconds: dict[tuple[str, str], float] = defaultdict(float)

    def observe(self, method: str, path: str, status: int, duration_seconds: float) -> None:
        with self._lock:
            self._requests[(method, path, status)] += 1
            self._duration_seconds[(method, path)] += duration_seconds

    def render(self) -> str:
        lines = [
            "# HELP career_radar_http_requests_total HTTP requests handled.",
            "# TYPE career_radar_http_requests_total counter",
        ]
        with self._lock:
            requests = sorted(self._requests.items())
            durations = sorted(self._duration_seconds.items())
        for (method, path, status), count in requests:
            labels = _labels(method=method, path=path, status=str(status))
            lines.append(f"career_radar_http_requests_total{{{labels}}} {count}")
        lines.extend(
            [
                "# HELP career_radar_http_request_duration_seconds_total Cumulative request time.",
                "# TYPE career_radar_http_request_duration_seconds_total counter",
            ]
        )
        for (method, path), duration in durations:
            labels = _labels(method=method, path=path)
            lines.append(
                f"career_radar_http_request_duration_seconds_total{{{labels}}} {duration:.6f}"
            )
        return "\n".join(lines) + "\n"


def _labels(**values: str) -> str:
    return ",".join(
        f'{key}="{value.replace(chr(92), chr(92) * 2).replace(chr(34), chr(92) + chr(34))}"'
        for key, value in values.items()
    )


async def observe_request(
    request: Request,
    call_next: RequestResponseEndpoint,
    metrics: RequestMetrics,
) -> Response:
    request_id = request.headers.get("X-Request-ID", "").strip()[:100] or uuid4().hex
    started = perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers.setdefault("X-Request-ID", request_id)
        return response
    finally:
        duration = perf_counter() - started
        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path)
        metrics.observe(request.method, path, status, duration)
        logging.getLogger("europe_visa_jobs.http").info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": path,
                "status": status,
                "duration_ms": round(duration * 1000, 2),
            },
        )

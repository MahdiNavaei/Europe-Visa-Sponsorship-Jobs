from __future__ import annotations

import logging

from europe_visa_jobs.api.observability import JsonFormatter, RequestMetrics


def test_json_formatter_and_metrics_escape_labels():
    formatter = JsonFormatter()
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "hello", (), None)
    record.request_id = "request-1"
    payload = formatter.format(record)
    assert '"message":"hello"' in payload
    assert '"request_id":"request-1"' in payload

    metrics = RequestMetrics()
    metrics.observe("GET", '/api/v1/jobs/"quoted"', 200, 0.125)
    rendered = metrics.render()
    assert "career_radar_http_requests_total" in rendered
    assert 'status="200"' in rendered
    assert '\\"quoted\\"' in rendered
    assert "0.125000" in rendered


def test_json_formatter_includes_exception():
    formatter = JsonFormatter()
    try:
        raise RuntimeError("safe failure")
    except RuntimeError:
        record = logging.LogRecord(
            "test",
            logging.ERROR,
            __file__,
            1,
            "failed",
            (),
            __import__("sys").exc_info(),
        )
    assert "RuntimeError: safe failure" in formatter.format(record)

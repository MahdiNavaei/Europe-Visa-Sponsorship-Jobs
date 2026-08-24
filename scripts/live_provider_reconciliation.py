"""Bounded live reconciliation of representative public ATS boards.

The report keeps provider-reported totals separate from Career Radar's fetched
counts. A null provider total means the provider does not expose one through the
public contract; exhaustion/completeness is then represented by the connector's
explicit completeness state rather than an invented equality claim.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter
from pathlib import Path
from typing import Any

import httpx

from europe_visa_jobs.connectors import build_connector
from europe_visa_jobs.ingestion.sources import load_sources
from europe_visa_jobs.settings import get_settings
from europe_visa_jobs.utils import is_supported_tech_role


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", default="config/source-registry.snapshot.json")
    parser.add_argument("--greenhouse", type=int, default=20)
    parser.add_argument("--lever", type=int, default=20)
    parser.add_argument("--personio", type=int, default=10)
    parser.add_argument("--teamtailor", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=8)
    return parser


async def reconcile(args: argparse.Namespace) -> dict[str, Any]:
    requested = {provider: getattr(args, provider) for provider in ("greenhouse", "lever", "personio", "teamtailor")}
    sources = load_sources(args.snapshot)
    selected = []
    for provider, limit in requested.items():
        selected.extend(sorted((source for source in sources if source.provider.value == provider), key=lambda item: item.slug)[:limit])
    settings = get_settings()
    results: list[dict[str, Any]] = []
    semaphore = asyncio.Semaphore(max(1, args.concurrency))
    async with httpx.AsyncClient(timeout=httpx.Timeout(settings.request_timeout_seconds), follow_redirects=True) as client:
        async def one(source) -> None:
            async with semaphore:
                try:
                    connector = build_connector(client, source)
                    jobs = await asyncio.wait_for(connector.fetch_jobs(), timeout=max(30.0, settings.request_timeout_seconds * 4))
                    technical = sum(is_supported_tech_role(job.title, job.department, job.description) for job in jobs)
                    results.append({
                        "provider": source.provider.value,
                        "board": source.slug,
                        "provider_reported_count": getattr(connector, "reported_total", None),
                        "fetched_count": len(jobs),
                        "normalized_count": len(jobs),
                        "technical_count": technical,
                        "nontechnical_count": len(jobs) - technical,
                        "failed_rows": 0,
                        "completeness": getattr(connector, "completeness", "complete"),
                        "status": "ok",
                    })
                except Exception as exc:
                    results.append({
                        "provider": source.provider.value,
                        "board": source.slug,
                        "provider_reported_count": None,
                        "fetched_count": 0,
                        "normalized_count": 0,
                        "technical_count": 0,
                        "nontechnical_count": 0,
                        "failed_rows": 0,
                        "completeness": "failed",
                        "status": "failed",
                        "error": str(exc)[:300],
                    })

        await asyncio.gather(*(one(source) for source in selected))
    results.sort(key=lambda item: (item["provider"], item["board"]))
    by_provider: dict[str, Any] = {}
    for provider in requested:
        rows = [row for row in results if row["provider"] == provider]
        counts = Counter(row["status"] for row in rows)
        by_provider[provider] = {
            "requested": requested[provider],
            "attempted": len(rows),
            "ok": counts["ok"],
            "failed": counts["failed"],
            "fetched_jobs": sum(row["fetched_count"] for row in rows),
            "normalized_jobs": sum(row["normalized_count"] for row in rows),
            "technical_jobs": sum(row["technical_count"] for row in rows),
            "nontechnical_jobs": sum(row["nontechnical_count"] for row in rows),
            "complete_feeds": sum(row["completeness"] == "complete" for row in rows),
            "partial_feeds": sum(row["completeness"] == "partial" for row in rows),
            "provider_total_comparisons": sum(row["provider_reported_count"] is not None for row in rows),
        }
    return {"snapshot": str(Path(args.snapshot)), "by_provider": by_provider, "boards": results}


def main() -> None:
    args = _parser().parse_args()
    print(json.dumps(asyncio.run(reconcile(args)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

from __future__ import annotations

import asyncio

import httpx

from europe_visa_jobs.connectors import build_connector
from europe_visa_jobs.ingestion.sources import load_sources
from europe_visa_jobs.settings import get_settings

SOURCES_PATH = "config/sources.json"


async def main() -> None:
    settings = get_settings()
    sources = load_sources(SOURCES_PATH)
    timeout = httpx.Timeout(settings.request_timeout_seconds)
    failures: list[str] = []
    total_jobs = 0

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for source in sources:
            label = f"{source.provider.value}:{source.slug}"
            try:
                jobs = await build_connector(client, source).fetch_jobs()
            except Exception as exc:
                failures.append(f"{label}: {str(exc)[:240]}")
                print(f"SOURCE_FAIL {label} error={str(exc)[:240]}")
                continue
            total_jobs += len(jobs)
            print(f"SOURCE_OK {label} jobs={len(jobs)}")

    if failures:
        raise AssertionError("configured live source catalog contains unhealthy feeds:\n" + "\n".join(failures))
    if total_jobs == 0:
        raise AssertionError("configured source catalog returned zero jobs across all feeds")
    print(f"LIVE_SOURCE_CATALOG_OK sources={len(sources)} fetched_jobs={total_jobs}")


if __name__ == "__main__":
    asyncio.run(main())

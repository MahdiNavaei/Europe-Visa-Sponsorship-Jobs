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
        semaphore = asyncio.Semaphore(max(1, min(settings.discovery_concurrency, 8)))

        async def validate(source):
            label = f"{source.provider.value}:{source.slug}"
            async with semaphore:
                try:
                    jobs = await asyncio.wait_for(
                        build_connector(client, source).fetch_jobs(),
                        timeout=max(30.0, settings.request_timeout_seconds * 4),
                    )
                except Exception as exc:
                    return label, 0, f"{label}: {str(exc)[:240]}"
                return label, len(jobs), None

        results = await asyncio.gather(*(validate(source) for source in sources))
        for label, count, error in results:
            if error:
                failures.append(error)
                print(f"SOURCE_FAIL {error}")
            else:
                total_jobs += count
                print(f"SOURCE_OK {label} jobs={count}")

    if failures:
        raise AssertionError("configured live source catalog contains unhealthy feeds:\n" + "\n".join(failures))
    if total_jobs == 0:
        raise AssertionError("configured source catalog returned zero jobs across all feeds")
    print(f"LIVE_SOURCE_CATALOG_OK sources={len(sources)} fetched_jobs={total_jobs}")


if __name__ == "__main__":
    asyncio.run(main())

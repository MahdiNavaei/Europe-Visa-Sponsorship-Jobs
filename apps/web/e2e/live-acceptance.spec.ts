import { expect, test } from "@playwright/test";

const liveApiUrl = process.env.LIVE_API_URL ?? "http://127.0.0.1:8000";

test.skip(!process.env.LIVE_E2E, "Set LIVE_E2E=1 to run against a live API and persisted ingestion database.");

test("live ingestion snapshot reaches coverage, job detail, and employer apply URL", async ({ page, request }) => {
  const coverageResponse = await request.get(`${liveApiUrl}/api/v1/coverage`);
  expect(coverageResponse.ok()).toBeTruthy();
  const coverage = await coverageResponse.json();
  expect(coverage.verified_sources).toBeGreaterThan(0);
  expect(coverage.raw_jobs_scanned).toBeGreaterThan(0);

  const jobsResponse = await request.get(`${liveApiUrl}/api/v1/jobs?status=unknown&limit=1`);
  expect(jobsResponse.ok()).toBeTruthy();
  const jobs = await jobsResponse.json();
  expect(jobs.length).toBeGreaterThan(0);
  const job = jobs[0];
  expect(job.apply_url).toMatch(/^https?:\/\//);
  const applyResponse = await request.get(job.apply_url, { maxRedirects: 5, timeout: 20_000 });
  expect(applyResponse.status()).toBeLessThan(400);

  await page.goto("/en/coverage");
  await expect(page.getByRole("heading", { name: "Verified European job coverage" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Source health diagnostics" })).toBeVisible();

  await page.goto(`/en/jobs/${job.id}`);
  await expect(page.getByRole("heading", { name: job.title })).toBeVisible();
  await expect(page.getByRole("link", { name: "Apply" }).first()).toHaveAttribute("href", job.apply_url);
});

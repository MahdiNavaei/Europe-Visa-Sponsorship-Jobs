import { expect, test } from "@playwright/test";

const liveApiUrl = process.env.LIVE_API_URL ?? "http://127.0.0.1:8000";

test.skip(!process.env.LIVE_E2E, "Set LIVE_E2E=1 to run against a real imported catalog.");

test("real catalog supports onboarding, tracking, persistence, and Persian RTL", async ({ page, request }) => {
  test.setTimeout(120_000);
  const consoleErrors: string[] = [];
  const failedRequests: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") {
      const location = message.location().url;
      consoleErrors.push(`${location || "unknown source"}: ${message.text()}`);
    }
  });
  page.on("requestfailed", (failed) => {
    const reason = failed.failure()?.errorText ?? "unknown";
    if (!reason.includes("ERR_ABORTED")) failedRequests.push(`${failed.url()}: ${reason}`);
  });

  await page.goto("/en/onboarding");
  await page.evaluate(() => localStorage.removeItem("career-radar-candidate"));
  await page.reload();
  await page.getByPlaceholder(/Samira/i).fill("Production Gate Candidate");
  await page.getByRole("button", { name: "Backend Engineering" }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Python", exact: true }).click();
  await page.getByRole("button", { name: "SQL", exact: true }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Senior", exact: true }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Germany", exact: true }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Yes, I need employer support" }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "I’m open to the right setup" }).click();
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/en\/dashboard$/);
  await expect(page.getByRole("heading", { name: "Your European career radar" })).toBeVisible();
  await page.screenshot({ path: "artifacts/ui/launch-gate-real-dashboard.png", fullPage: true });

  const jobsResponse = await request.get(`${liveApiUrl}/api/v1/jobs?status=unknown&limit=1`);
  expect(jobsResponse.ok()).toBeTruthy();
  const jobs = await jobsResponse.json();
  expect(jobs).toHaveLength(1);
  const job = jobs[0];

  await page.goto(`/en/jobs/${job.id}`);
  await expect(page.getByRole("heading", { name: job.title })).toBeVisible();
  await expect(page.getByRole("link", { name: "Apply" }).first()).toHaveAttribute("href", job.apply_url);
  await page.getByRole("button", { name: "Save job" }).click();
  await expect(page.getByRole("button", { name: "Saved" })).toBeVisible();
  await page.getByLabel("Application status").selectOption("applied");
  await expect(page.getByLabel("Application status")).toHaveValue("applied");
  await page.screenshot({ path: "artifacts/ui/launch-gate-real-detail.png", fullPage: true });

  await page.reload();
  await expect(page.getByRole("button", { name: "Saved" })).toBeVisible();
  await expect(page.getByLabel("Application status")).toHaveValue("applied");
  await page.goto("/en/applications");
  await expect(page.getByText(job.title).first()).toBeVisible();
  await page.goto("/en/companies");
  await expect(page.getByRole("heading", { name: "Signals behind the names" })).toBeVisible();
  await page.goto("/en/coverage");
  await expect(page.getByRole("heading", { name: "Verified European job coverage" })).toBeVisible();
  await expect(page.getByTestId("coverage-freshness")).toContainText("local catalog sync");
  await expect(page.getByTestId("coverage-freshness")).toContainText("source / ATS refresh");

  await page.goto(`/fa/jobs/${job.id}`);
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("heading", { name: job.title })).toBeVisible();
  const body = await page.locator("body").innerText();
  expect(body).not.toContain("detail.jobSignal");
  expect(body).not.toContain("detail.companySignal");
  expect(body).not.toContain("detail.finalEligibility");
  expect(body).toMatch(/[\u0600-\u06ff]/);
  await page.screenshot({ path: "artifacts/ui/launch-gate-persian-detail-final.png", fullPage: true });

  expect(consoleErrors).toEqual([]);
  expect(failedRequests).toEqual([]);
});

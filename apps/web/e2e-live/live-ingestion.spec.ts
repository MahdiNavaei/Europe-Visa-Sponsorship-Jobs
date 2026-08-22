import { expect, test } from "@playwright/test";

test("live ingested eligible jobs are visible in the real UI", async ({ page }) => {
  await page.goto("/en/jobs");

  // Do not assert copy here: this gate proves the live data path, not marketing text.
  // The job cards below can only exist if the production UI successfully consumed
  // the real FastAPI/PostgreSQL dataset populated from the public ATS feeds.
  const detailLinks = page.locator('a[href^="/en/jobs/"]');
  await expect.poll(async () => detailLinks.count(), { timeout: 20_000 }).toBeGreaterThan(0);

  const sourceCompany = page.getByText(/N26|trivago|Clera/i).first();
  await expect(sourceCompany).toBeVisible({ timeout: 20_000 });

  await detailLinks.first().click();
  await expect(page).toHaveURL(/\/en\/jobs\/\d+$/);

  const apply = page.getByRole("link", { name: /apply/i }).first();
  await expect(apply).toBeVisible();
  const href = await apply.getAttribute("href");
  expect(href).toMatch(/^https?:\/\//);
});

import { expect, test } from "@playwright/test";

test("live ingested eligible jobs are visible in the real UI", async ({ page }) => {
  await page.goto("/en/jobs");

  await expect(page.getByText("Visa verified opportunities").or(page.getByText("Personalized ranking"))).toBeVisible({ timeout: 20_000 });

  const detailLinks = page.locator('a[href^="/en/jobs/"]');
  await expect.poll(async () => detailLinks.count(), { timeout: 20_000 }).toBeGreaterThan(0);

  const sourceCompany = page.getByText(/N26|trivago|Clera/i).first();
  await expect(sourceCompany).toBeVisible({ timeout: 20_000 });

  const firstDetail = detailLinks.first();
  await firstDetail.click();
  await expect(page).toHaveURL(/\/en\/jobs\/\d+$/);

  const apply = page.getByRole("link", { name: /apply/i }).first();
  await expect(apply).toBeVisible();
  const href = await apply.getAttribute("href");
  expect(href).toMatch(/^https?:\/\//);
});

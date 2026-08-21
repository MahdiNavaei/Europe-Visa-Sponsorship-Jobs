import { expect, test, type Page, type Route } from "@playwright/test";

const job = {
  id: 7,
  company_id: 3,
  external_id: "demo-7",
  provider: "greenhouse",
  source_slug: "demo",
  company_name: "Northstar Labs",
  title: "Senior AI Engineer",
  description: "Visa sponsorship and relocation support are available. Required skills: Python and PyTorch.",
  location: "Berlin, Germany",
  country: "Germany",
  department: "AI",
  employment_type: "Full time",
  workplace_type: "Hybrid",
  apply_url: "https://example.invalid/apply",
  job_url: null,
  posted_at: "2026-08-21T12:00:00Z",
  job_family: "ai_ml",
  required_skills: ["Python", "PyTorch"],
  preferred_skills: ["Kubernetes"],
  min_experience_years: 4,
  seniority: "senior",
  eligibility_status: "eligible",
  eligibility_score: 94,
};

const candidate = {
  id: 11,
  name: "Samira Ahmadi",
  target_roles: ["AI / Machine Learning"],
  skills: ["Python", "PyTorch"],
  years_of_experience: 5,
  seniority: "senior",
  preferred_countries: ["Germany"],
  visa_required: true,
  relocation_preference: "preferred",
  remote_preference: "preferred",
  excluded_locations: [],
  created_at: "2026-08-21T12:00:00Z",
  updated_at: "2026-08-21T12:00:00Z",
};

const recommendation = {
  job_id: 7,
  scores: { overall: 94, visa: 100, skill: 92, experience: 90, country: 100, company: 80 },
  total_score: 94,
  visa_score: 100,
  skill_score: 92,
  skill_match: 0.92,
  experience_score: 90,
  country_score: 100,
  company_score: 80,
  required_skill_coverage: 1,
  preferred_skill_coverage: 0,
  seniority_match: 1,
  role_similarity: 0.9,
  matched_skills: ["Python", "PyTorch"],
  missing_skills: [],
  missing_preferred_skills: ["Kubernetes"],
  reasons: ["Strong Python match", "The job passed the strict sponsorship eligibility gate."],
  warnings: ["Missing preferred skill: Kubernetes."],
  explanation: ["Strong Python match", "Missing preferred skill: Kubernetes."],
  job,
};

function json(route: Route, body: unknown, status = 200, headers: Record<string, string> = {}) {
  return route.fulfill({
    status,
    body: JSON.stringify(body),
    headers: { "Content-Type": "application/json", ...headers },
  });
}

async function installDashboardApi(page: Page) {
  await page.addInitScript(() => {
    window.localStorage.setItem("career-radar-candidate", "11");
    window.localStorage.setItem("theme", "light");
  });

  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/v1/candidates/11") return json(route, candidate);
    if (path === "/api/v1/stats") return json(route, { total_jobs: 21, eligible_jobs: 18, rejected_jobs: 2, unknown_jobs: 1, companies: 8 });
    if (path === "/api/v1/recommendations/11") return json(route, [recommendation], 200, { "X-Total-Count": "1" });
    if (path === "/api/v1/jobs") return json(route, [job], 200, { "X-Total-Count": "1" });
    if (path === "/api/v1/countries") return json(route, { countries: ["Germany", "Netherlands", "Sweden"] });
    return json(route, { detail: `Unhandled visual snapshot route: ${path}` }, 404);
  });
}

async function capture(page: Page, path: string) {
  await page.screenshot({ path, fullPage: true, animations: "disabled" });
}

test.describe("showcase UI snapshots", () => {
  test.skip(({ browserName }) => browserName !== "chromium", "Canonical snapshot artifacts use Chromium");

  test.beforeEach(async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
  });

  test("captures English landing page", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto("/en");
    await expect(page.getByRole("heading", { name: /Find European jobs/i })).toBeVisible();
    await capture(page, "artifacts/ui/landing-en.png");
  });

  test("captures Persian RTL landing page", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto("/fa");
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    await capture(page, "artifacts/ui/landing-fa.png");
  });

  test("captures populated Career Radar dashboard", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await installDashboardApi(page);
    await page.goto("/en/dashboard");
    await expect(page.getByText("Senior AI Engineer")).toBeVisible();
    await capture(page, "artifacts/ui/dashboard-en.png");
  });

  test("captures mobile English landing page", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/en");
    await expect(page.getByRole("heading", { name: /Find European jobs/i })).toBeVisible();
    await capture(page, "artifacts/ui/landing-en-mobile.png");
  });

  test("captures mobile Career Radar dashboard", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await installDashboardApi(page);
    await page.goto("/en/dashboard");
    await expect(page.getByText("Senior AI Engineer")).toBeVisible();
    await capture(page, "artifacts/ui/dashboard-en-mobile.png");
  });
});

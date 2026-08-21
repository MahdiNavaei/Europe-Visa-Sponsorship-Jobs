import { expect, test, type Page, type Route } from "@playwright/test";

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

const job = {
  id: 7,
  company_id: 3,
  external_id: "demo-7",
  provider: "greenhouse",
  source_slug: "demo",
  company_name: "Northstar Labs",
  title: "Senior AI Engineer",
  description: "Visa sponsorship and relocation support are available.",
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
  reasons: ["Strong Python match"],
  warnings: ["Missing preferred skill: Kubernetes."],
  explanation: ["Strong Python match", "Missing preferred skill: Kubernetes."],
  job,
};

function json(route: Route, body: unknown, headers: Record<string, string> = {}) {
  return route.fulfill({
    status: 200,
    body: JSON.stringify(body),
    headers: { "Content-Type": "application/json", ...headers },
  });
}

async function installDashboardApi(page: Page) {
  await page.addInitScript(() => window.localStorage.setItem("career-radar-candidate", "11"));
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/v1/candidates/11") return json(route, candidate);
    if (path === "/api/v1/stats") return json(route, { total_jobs: 21, eligible_jobs: 18, rejected_jobs: 2, unknown_jobs: 1, companies: 8 });
    if (path === "/api/v1/recommendations/11") return json(route, [recommendation], { "X-Total-Count": "1" });
    if (path === "/api/v1/jobs") return json(route, [job], { "X-Total-Count": "1" });
    if (path === "/api/v1/countries") return json(route, { countries: ["Germany", "Netherlands", "Sweden"] });
    return route.fulfill({ status: 404, body: JSON.stringify({ detail: `Unhandled route: ${path}` }), headers: { "Content-Type": "application/json" } });
  });
}

async function auditDocument(page: Page) {
  const findings = await page.evaluate(() => {
    const text = (element: Element) => (element.textContent ?? "").trim();
    const accessibleName = (element: Element) =>
      element.getAttribute("aria-label") ||
      element.getAttribute("aria-labelledby") ||
      element.getAttribute("title") ||
      text(element);

    const unnamedButtons = Array.from(document.querySelectorAll("button")).filter((element) => !accessibleName(element));
    const unnamedLinks = Array.from(document.querySelectorAll("a[href]")).filter((element) => !accessibleName(element));
    const unlabeledControls = Array.from(document.querySelectorAll("input, select, textarea")).filter((element) => {
      const id = element.getAttribute("id");
      const labelled =
        element.getAttribute("aria-label") ||
        element.getAttribute("aria-labelledby") ||
        (id && document.querySelector(`label[for="${CSS.escape(id)}"]`)) ||
        element.closest("label");
      return !labelled;
    });
    const imagesWithoutAlt = Array.from(document.querySelectorAll("img")).filter((element) => !element.hasAttribute("alt"));
    const ids = Array.from(document.querySelectorAll("[id]")).map((element) => element.id);
    const duplicateIds = ids.filter((id, index) => id && ids.indexOf(id) !== index);
    const headings = Array.from(document.querySelectorAll("h1, h2, h3, h4, h5, h6")).map((element) => Number(element.tagName.slice(1)));
    const headingSkips = headings.filter((level, index) => index > 0 && level - headings[index - 1] > 1);

    return {
      unnamedButtons: unnamedButtons.length,
      unnamedLinks: unnamedLinks.length,
      unlabeledControls: unlabeledControls.length,
      imagesWithoutAlt: imagesWithoutAlt.length,
      duplicateIds: [...new Set(duplicateIds)],
      headingSkips,
      mainCount: document.querySelectorAll("main").length,
      h1Count: document.querySelectorAll("h1").length,
      horizontalOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    };
  });

  expect(findings.unnamedButtons).toBe(0);
  expect(findings.unnamedLinks).toBe(0);
  expect(findings.unlabeledControls).toBe(0);
  expect(findings.imagesWithoutAlt).toBe(0);
  expect(findings.duplicateIds).toEqual([]);
  expect(findings.headingSkips).toEqual([]);
  expect(findings.mainCount).toBe(1);
  expect(findings.h1Count).toBe(1);
  expect(findings.horizontalOverflow).toBeLessThanOrEqual(1);
}

test("English landing has accessible semantics and keyboard skip navigation", async ({ page }) => {
  await page.goto("/en");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  await auditDocument(page);

  const skip = page.getByRole("link", { name: "Skip to main content" });
  await skip.focus();
  await expect(skip).toBeFocused();
  await skip.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();
});

test("Persian landing exposes correct language, RTL and semantics", async ({ page }) => {
  await page.goto("/fa");
  await expect(page.locator("html")).toHaveAttribute("lang", "fa");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await auditDocument(page);
});

test("Career Radar remains accessible with populated data", async ({ page }) => {
  await installDashboardApi(page);
  await page.goto("/en/dashboard");
  await expect(page.getByText("Senior AI Engineer")).toBeVisible();
  await auditDocument(page);
});

test("landing and dashboard do not overflow a phone viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/en");
  await auditDocument(page);

  await installDashboardApi(page);
  await page.goto("/en/dashboard");
  await expect(page.getByText("Senior AI Engineer")).toBeVisible();
  await auditDocument(page);
});

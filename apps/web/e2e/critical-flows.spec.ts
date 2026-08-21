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

const company = {
  company: {
    id: 3,
    name: "Northstar Labs",
    normalized_name: "northstar labs",
    country: "Germany",
    career_url: "https://example.invalid/careers",
    sponsor_verified: true,
  },
  visa_friendliness_score: 87,
  positive_signals: ["Recognized sponsor evidence is on file.", "Relocation support is mentioned."],
  negative_signals: [],
  active_jobs: 1,
  eligible_jobs: 1,
  jobs: [job],
};

function json(route: Route, body: unknown, status = 200, headers: Record<string, string> = {}) {
  return route.fulfill({
    status,
    body: JSON.stringify(body),
    headers: { "Content-Type": "application/json", ...headers },
  });
}

async function installBaseApi(page: Page) {
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;

    if (request.method() === "POST" && path === "/api/v1/candidates") return json(route, candidate, 201);
    if (request.method() === "PUT" && path === "/api/v1/candidates/11") return json(route, candidate);
    if (path === "/api/v1/candidates/11") return json(route, candidate);
    if (path === "/api/v1/stats") return json(route, { total_jobs: 21, eligible_jobs: 18, rejected_jobs: 2, unknown_jobs: 1, companies: 8 });
    if (path === "/api/v1/countries") return json(route, { countries: ["Germany", "Netherlands", "Sweden"] });
    if (path === "/api/v1/jobs/7") {
      return json(route, {
        ...job,
        evidence: [
          {
            kind: "job_positive",
            code: "visa_sponsorship",
            message: "Visa sponsorship signal found",
            weight: 30,
            matched_text: "Visa sponsorship",
            source_url: null,
          },
        ],
      });
    }
    if (path === "/api/v1/companies/3") return json(route, company);
    if (path === "/api/v1/recommendations/11/jobs/7") return json(route, recommendation);
    if (path === "/api/v1/recommendations/11/explain") {
      return json(route, {
        candidate,
        weights: { visa: 0.35, skill: 0.3, experience: 0.15, country: 0.1, company: 0.1 },
        recommendations: [recommendation],
      });
    }
    if (path === "/api/v1/recommendations/11") {
      return json(route, [recommendation], 200, { "X-Total-Count": "1" });
    }
    if (path === "/api/v1/jobs") return json(route, [job], 200, { "X-Total-Count": "1" });

    return json(route, { detail: `Unhandled test route: ${request.method()} ${path}` }, 404);
  });
}

async function setCandidate(page: Page) {
  await page.addInitScript(() => window.localStorage.setItem("career-radar-candidate", "11"));
}

test("language switch performs a real English to Persian RTL navigation", async ({ page }) => {
  await page.goto("/en");
  await expect(page.getByRole("heading", { name: /Find European jobs/i })).toBeVisible();
  await page.getByRole("button", { name: "Switch language" }).click();
  await expect(page).toHaveURL(/\/fa$/);
  await expect(page.locator("html")).toHaveAttribute("lang", "fa");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("heading", { name: /فرصت‌هایی را پیدا کنید/ })).toBeVisible();
});

test("dark mode persists after navigation and reload", async ({ page }) => {
  await page.goto("/en");
  await page.evaluate(() => window.localStorage.setItem("theme", "light"));
  await page.reload();
  await expect(page.locator("html")).toHaveClass(/light/);
  await page.getByRole("button", { name: "Toggle theme" }).click();
  await expect.poll(() => page.evaluate(() => window.localStorage.getItem("theme"))).toBe("dark");
  await page.reload();
  await expect(page.locator("html")).toHaveClass(/dark/);
});

test("full six-step onboarding creates a candidate and lands on Career Radar", async ({ page }) => {
  test.setTimeout(60_000);
  let submitted: Record<string, unknown> | null = null;
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    if (request.method() === "POST" && path === "/api/v1/candidates") {
      submitted = request.postDataJSON() as Record<string, unknown>;
      return json(route, candidate, 201);
    }
    if (path === "/api/v1/candidates/11") return json(route, candidate);
    if (path === "/api/v1/stats") return json(route, { total_jobs: 1, eligible_jobs: 1, rejected_jobs: 0, unknown_jobs: 0, companies: 1 });
    if (path === "/api/v1/recommendations/11") return json(route, [recommendation], 200, { "X-Total-Count": "1" });
    if (path === "/api/v1/jobs") return json(route, [job], 200, { "X-Total-Count": "1" });
    if (path === "/api/v1/countries") return json(route, { countries: ["Germany"] });
    return json(route, { detail: `Unhandled test route: ${request.method()} ${path}` }, 404);
  });

  await page.goto("/en/onboarding");
  await page.evaluate(() => window.localStorage.removeItem("career-radar-candidate"));
  await page.reload();
  await page.getByPlaceholder(/Samira/i).fill("Samira Ahmadi");
  await page.getByRole("button", { name: "AI / Machine Learning" }).click();
  await page.getByRole("button", { name: "Continue" }).click();

  await page.getByRole("button", { name: "Python" }).click();
  await page.getByRole("button", { name: "PyTorch" }).click();
  await page.getByRole("button", { name: "Continue" }).click();

  await page.getByRole("button", { name: "Senior", exact: true }).click();
  await page.getByRole("button", { name: "Continue" }).click();

  await page.getByRole("button", { name: "Germany" }).click();
  await page.getByRole("button", { name: "Continue" }).click();

  await page.getByRole("button", { name: "Yes, I need employer support" }).click();
  await page.getByRole("button", { name: "Continue" }).click();

  await page.getByRole("button", { name: "Remote is important" }).click();
  const finish = page.locator('form button[type="submit"]');
  await expect(finish).toHaveText(/See my radar/);
  await finish.click();

  await expect(page).toHaveURL(/\/en\/dashboard$/);
  await expect(page.getByRole("heading", { name: "Your European career radar" })).toBeVisible();
  await expect.poll(() => page.evaluate(() => window.localStorage.getItem("career-radar-candidate"))).toBe("11");
  expect(submitted).toMatchObject({
    name: "Samira Ahmadi",
    seniority: "senior",
    target_roles: ["AI / Machine Learning"],
    skills: ["Python", "PyTorch"],
    preferred_countries: ["Germany"],
    visa_required: true,
    remote_preference: "preferred",
  });
});

test("personalized jobs send server filters, sorting and pagination parameters", async ({ page }) => {
  await setCandidate(page);
  let sawFilteredRequest = false;
  let sawNextPage = false;
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname === "/api/v1/countries") return json(route, { countries: ["Germany", "Netherlands"] });
    if (url.pathname === "/api/v1/recommendations/11") {
      const filtered =
        url.searchParams.get("country") === "Germany" &&
        url.searchParams.get("min_score") === "80" &&
        url.searchParams.get("sort") === "visa";
      if (filtered) sawFilteredRequest = true;
      const offset = Number(url.searchParams.get("offset") ?? 0);
      if (offset >= 20) sawNextPage = true;
      const pageJob = offset >= 20
        ? { ...job, id: 27, external_id: "demo-27", title: "AI Platform Engineer" }
        : filtered
          ? { ...job, title: "Filtered Senior AI Engineer" }
          : job;
      return json(route, [{ ...recommendation, job_id: pageJob.id, job: pageJob }], 200, { "X-Total-Count": "21" });
    }
    return json(route, { detail: "not needed" }, 404);
  });

  await page.goto("/en/jobs");
  await expect(page.getByText("Personalized ranking")).toBeVisible();
  await page.getByLabel("Country").selectOption("Germany");
  await page.getByLabel("Minimum match score").selectOption("80");
  await page.getByLabel("Sort").selectOption("visa");
  await expect.poll(() => sawFilteredRequest).toBe(true);
  await expect(page.getByText("Filtered Senior AI Engineer")).toBeVisible();

  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect.poll(() => sawNextPage).toBe(true);
  await expect(page.getByText("AI Platform Engineer")).toBeVisible();
});

test("job detail shows candidate-specific matching and links to company intelligence", async ({ page }) => {
  await setCandidate(page);
  await installBaseApi(page);
  await page.goto("/en/jobs/7");
  const main = page.getByRole("main");
  await expect(page.getByRole("heading", { name: "Senior AI Engineer" })).toBeVisible();
  await expect(main.getByText("Your match")).toBeVisible();
  await expect(main.getByText("Strong Python match").first()).toBeVisible();
  await expect(main.getByText("Matched skills")).toBeVisible();
  await expect(main.getByRole("link", { name: "Companies" })).toHaveAttribute("href", "/en/companies/3");
});

test("company detail exposes evidence-based company signals and active jobs", async ({ page }) => {
  await installBaseApi(page);
  await page.goto("/en/companies/3");
  await expect(page.getByRole("heading", { name: "Northstar Labs" })).toBeVisible();
  await expect(page.getByText("Visa friendliness")).toBeVisible();
  await expect(page.getByText("Recognized sponsor evidence is on file.")).toBeVisible();
  await expect(page.getByText("Senior AI Engineer")).toBeVisible();
});

test("recommendation explanation uses the candidate id from the route", async ({ page }) => {
  await installBaseApi(page);
  await page.goto("/en/recommendations/11/explain");
  await expect(page.getByRole("heading", { name: "Why these roles fit Samira Ahmadi" })).toBeVisible();
  await expect(page.getByText("Ranking weights")).toBeVisible();
  await expect(page.getByText("35%")).toBeVisible();
  await expect(page.getByText("Strong Python match").first()).toBeVisible();
});

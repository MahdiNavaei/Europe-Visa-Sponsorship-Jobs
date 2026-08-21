import { expect, test } from "@playwright/test";

test("landing page opens and language switch changes direction", async ({ page }) => {
  await page.goto("/en");
  await expect(page.getByRole("heading", { name: /Find European jobs/i })).toBeVisible();
  await page.goto("/fa");
  await expect(page.locator("html")).toHaveAttribute("lang", "fa");
  await expect(page.locator("[dir='rtl']").first()).toBeVisible();
});

test("jobs experience has filters and remains usable without the API", async ({ page }) => {
  await page.goto("/en/jobs");
  await expect(page.getByRole("heading", { name: /Discover your next move/i })).toBeVisible();
  await expect(page.getByPlaceholder(/Search roles/i)).toBeVisible();
  await expect(page.getByText(/Country/i).first()).toBeVisible();
});

test("dark mode toggle persists the preference", async ({ page }) => {
  await page.goto("/en");
  const toggle = page.getByRole("button", { name: "Toggle theme" });
  await expect(toggle).toBeVisible();
  await toggle.click();
  await expect.poll(() => page.evaluate(() => window.localStorage.getItem("theme"))).toBe("dark");
});

test("onboarding presents the profile-building flow", async ({ page }) => {
  const job = {
    id: 7, company_id: 3, external_id: "demo-7", provider: "greenhouse", source_slug: "demo", company_name: "Northstar Labs", title: "Senior AI Engineer", description: "Visa sponsorship and relocation support are available.", location: "Berlin, Germany", country: "Germany", department: null, employment_type: "Full time", workplace_type: "Hybrid", apply_url: "https://example.invalid/apply", job_url: null, posted_at: "2026-01-01T00:00:00Z", job_family: "ai_ml", required_skills: ["Python"], preferred_skills: [], min_experience_years: 4, seniority: "senior", eligibility_status: "eligible", eligibility_score: 94,
  };
  await page.addInitScript(({ fixture }) => { const originalFetch = window.fetch.bind(window); window.fetch = async (input, init) => { const url = new URL(typeof input === "string" ? input : input instanceof Request ? input.url : String(input), window.location.origin); if (url.pathname.endsWith("/jobs/7")) return new Response(JSON.stringify({ ...fixture, evidence: [] }), { headers: { "Content-Type": "application/json" } }); if (url.pathname.endsWith("/jobs")) return new Response(JSON.stringify([fixture]), { headers: { "Content-Type": "application/json" } }); return originalFetch(input, init); }; }, { fixture: job });
  const candidate = { id: 11, name: "Samira Ahmadi", target_roles: ["AI / Machine Learning"], skills: ["Python"], years_of_experience: 5, seniority: "senior", preferred_countries: ["Germany"], visa_required: true, relocation_preference: "preferred", remote_preference: "no_preference", excluded_locations: [], created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" };
  const recommendation = { job_id: 7, scores: { overall: 94, visa: 100, skill: 92, experience: 90, country: 100, company: 80 }, total_score: 94, visa_score: 100, skill_score: 92, skill_match: .92, experience_score: 90, country_score: 100, company_score: 80, required_skill_coverage: 1, preferred_skill_coverage: 0, seniority_match: 1, role_similarity: .9, matched_skills: ["Python"], missing_skills: [], missing_preferred_skills: [], reasons: ["Strong Python match"], warnings: [], explanation: ["Strong Python match"], job,
  };
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (!url.pathname.startsWith("/api/v1/")) return route.continue();
    if (route.request().method() === "POST" && url.pathname.endsWith("/candidates")) return route.fulfill({ json: candidate, status: 201 });
    if (url.pathname.endsWith("/stats")) return route.fulfill({ json: { total_jobs: 1, eligible_jobs: 1, rejected_jobs: 0, unknown_jobs: 0, companies: 1 } });
    if (url.pathname.endsWith("/countries")) return route.fulfill({ json: { countries: ["Germany"] } });
    if (url.pathname.includes("/recommendations/") && url.pathname.endsWith("/explain")) return route.fulfill({ json: { candidate, weights: { visa: .35, skill: .3, experience: .15, country: .1, company: .1 }, recommendations: [recommendation] } });
    if (url.pathname.includes("/recommendations/")) return route.fulfill({ json: [recommendation], headers: { "X-Total-Count": "1" } });
    if (url.pathname.endsWith("/jobs/7")) return route.fulfill({ json: { ...job, evidence: [{ kind: "job_positive", code: "sponsorship", message: "Visa sponsorship signal found", weight: 10, matched_text: "sponsorship", source_url: null }] } });
    if (url.pathname.endsWith("/jobs")) return route.fulfill({ json: [job] });
    return route.continue();
  });
  await page.goto("/en/onboarding");
  await page.getByPlaceholder(/Samira/i).fill("Samira Ahmadi");
  await page.getByRole("button", { name: "AI / Machine Learning" }).click();
  await expect(page.getByRole("button", { name: "Continue" })).toBeVisible();
});

test("job filters use the typed API surface", async ({ page }) => {
  const job = { id: 7, company_id: 3, external_id: "demo-7", provider: "greenhouse", source_slug: "demo", company_name: "Northstar Labs", title: "Senior AI Engineer", description: "Visa sponsorship.", location: "Berlin, Germany", country: "Germany", department: null, employment_type: "Full time", workplace_type: "Hybrid", apply_url: "https://example.invalid/apply", job_url: null, posted_at: "2026-01-01T00:00:00Z", job_family: "ai_ml", required_skills: ["Python"], preferred_skills: [], min_experience_years: 4, seniority: "senior", eligibility_status: "eligible", eligibility_score: 94 };
  await page.addInitScript(({ fixture }) => { const originalFetch = window.fetch.bind(window); window.fetch = async (input, init) => { const url = new URL(typeof input === "string" ? input : input instanceof Request ? input.url : String(input), window.location.origin); if (url.pathname.endsWith("/jobs/7")) return new Response(JSON.stringify({ ...fixture, evidence: [] }), { headers: { "Content-Type": "application/json" } }); if (url.pathname.endsWith("/jobs")) return new Response(JSON.stringify([fixture]), { headers: { "Content-Type": "application/json" } }); return originalFetch(input, init); }; }, { fixture: job });
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (!url.pathname.startsWith("/api/v1/jobs")) return route.continue();
    if (url.pathname.endsWith("/7")) return route.fulfill({ json: { ...job, evidence: [] } });
    return route.fulfill({ json: [job] });
  });
  await page.goto("/en/jobs");
  await page.getByLabel("Country").selectOption("Germany");
  await expect(page.getByLabel("Country")).toHaveValue("Germany");
});

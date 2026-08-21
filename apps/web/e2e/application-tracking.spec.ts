import { expect, test } from "@playwright/test";

const job = {
  id: 7,
  company_id: 3,
  external_id: "tracked-7",
  provider: "greenhouse",
  source_slug: "demo",
  company_name: "Northstar Labs",
  title: "Senior AI Engineer",
  description: "Visa sponsorship available.",
  location: "Berlin, Germany",
  country: "Germany",
  department: null,
  employment_type: "Full time",
  workplace_type: "Hybrid",
  apply_url: "https://example.invalid/apply",
  job_url: null,
  posted_at: "2026-08-21T12:00:00Z",
  job_family: "ai_ml",
  required_skills: ["Python"],
  preferred_skills: [],
  min_experience_years: 4,
  seniority: "senior",
  eligibility_status: "eligible",
  eligibility_score: 94,
};

const state = {
  id: 51,
  candidate_id: 11,
  job_id: 7,
  saved: true,
  application_status: "applied",
  note: null,
  created_at: "2026-08-21T12:00:00Z",
  updated_at: "2026-08-21T12:00:00Z",
  job,
};

test("application tracker renders persisted state and updates pipeline status", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("career-radar-candidate", "11"));
  let updatePayload: Record<string, unknown> | null = null;
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (request.method() === "GET" && url.pathname === "/api/v1/candidates/11/job-states") {
      return route.fulfill({ json: [state] });
    }
    if (request.method() === "PUT" && url.pathname === "/api/v1/candidates/11/jobs/7/state") {
      updatePayload = request.postDataJSON() as Record<string, unknown>;
      return route.fulfill({ json: { ...state, application_status: updatePayload.application_status } });
    }
    return route.fulfill({ status: 404, json: { detail: "Unhandled test request" } });
  });

  await page.goto("/en/applications");
  await expect(page.getByRole("heading", { name: "Saved jobs and applications" })).toBeVisible();
  await expect(page.getByText("Senior AI Engineer")).toBeVisible();
  await page.getByLabel("Application status").selectOption("interview");
  await expect.poll(() => updatePayload?.application_status).toBe("interview");
});

test("job detail can save an opportunity without inventing frontend state", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("career-radar-candidate", "11"));
  let saved = false;
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname === "/api/v1/jobs/7") return route.fulfill({ json: { ...job, evidence: [] } });
    if (url.pathname === "/api/v1/recommendations/11/jobs/7") {
      return route.fulfill({ json: { job_id: 7, scores: { overall: 90, visa: 100, skill: 90, experience: 90, country: 100, company: 80 }, total_score: 90, visa_score: 100, skill_score: 90, skill_match: .9, experience_score: 90, country_score: 100, company_score: 80, required_skill_coverage: 1, preferred_skill_coverage: 1, seniority_match: 1, role_similarity: 1, matched_skills: ["Python"], missing_skills: [], missing_preferred_skills: [], reasons: ["Strong match"], warnings: [], explanation: ["Strong match"], job } });
    }
    if (request.method() === "GET" && url.pathname === "/api/v1/candidates/11/jobs/7/state") return route.fulfill({ json: null });
    if (request.method() === "PUT" && url.pathname === "/api/v1/candidates/11/jobs/7/state") {
      const body = request.postDataJSON() as { saved: boolean; application_status: string };
      saved = body.saved;
      return route.fulfill({ json: { ...state, saved: body.saved, application_status: body.application_status } });
    }
    return route.fulfill({ status: 404, json: { detail: "Unhandled test request" } });
  });

  await page.goto("/en/jobs/7");
  await page.getByRole("button", { name: "Save job" }).click();
  await expect.poll(() => saved).toBe(true);
  await expect(page.getByRole("button", { name: "Saved" })).toBeVisible();
});

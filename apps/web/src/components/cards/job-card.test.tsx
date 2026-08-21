import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";
import { JobCard } from "@/components/cards/job-card";
import { messages } from "@/lib/i18n/messages";
import type { Job } from "@/lib/types";

const job: Job = { id: 1, company_id: 1, external_id: "one", provider: "greenhouse", source_slug: "demo", company_name: "Example Labs", title: "Senior AI Engineer", description: "Visa sponsorship support.", location: "Berlin, Germany", country: "Germany", department: null, employment_type: "Full time", workplace_type: "Hybrid", apply_url: "https://example.invalid/apply", job_url: null, posted_at: "2026-01-01T00:00:00Z", job_family: "ai_ml", required_skills: ["Python"], preferred_skills: [], min_experience_years: 5, seniority: "senior", eligibility_status: "eligible", eligibility_score: 92 };

describe("JobCard", () => {
  it("renders the role and evidence status", () => {
    render(<NextIntlClientProvider locale="en" messages={messages.en}><JobCard job={job} /></NextIntlClientProvider>);
    expect(screen.getByText("Senior AI Engineer")).toBeInTheDocument();
    expect(screen.getByText("Eligible")).toBeInTheDocument();
    expect(screen.getByText("View details")).toBeInTheDocument();
  });
});

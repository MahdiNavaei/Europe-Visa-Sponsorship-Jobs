import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CoveragePage } from "@/features/coverage/coverage-page";

vi.mock("@/lib/api/hooks", () => ({
  useCoverage: () => ({
    data: { verified_sources: 12, healthy_sources: 10, degraded_sources: 1, failing_sources: 1, blocked_sources: 0, active_jobs: 5000, european_technical_jobs: 4200, raw_jobs_scanned: 7000, ai_ml_jobs: 800, sources_scanned_latest_run: 12, configured_sources: 15, last_refresh_at: "2026-08-22T12:00:00Z", eligible_jobs: 120, unknown_jobs: 400, rejected_jobs: 8 },
    isLoading: false,
    isError: false,
  }),
  useSourceHealth: () => ({
    data: [
      { id: 1, provider: "greenhouse", board_identifier: "acme", company_name: "Acme", status: "healthy", enabled: true, manual_override: true, consecutive_failures: 0, raw_job_count: 100, technical_job_count: 90, active_job_count: 90, eligible_job_count: 10, unknown_job_count: 80, rejected_job_count: 0, last_http_status: 200, last_error_category: null, last_error: null },
      { id: 2, provider: "greenhouse", board_identifier: "gone", company_name: "Gone", status: "degraded", enabled: true, manual_override: false, consecutive_failures: 1, raw_job_count: 0, technical_job_count: 0, active_job_count: 0, eligible_job_count: 0, unknown_job_count: 0, rejected_job_count: 0, last_http_status: 404, last_error_category: "not_found", last_error: "not found" },
    ],
    isLoading: false,
    isError: false,
  }),
}));

vi.mock("next-intl", () => ({
  useLocale: () => "en",
  useTranslations: () => (key: string, values?: { count?: string; value?: string }) => {
    const messages: Record<string, string> = {
      eyebrow: "Source coverage",
      title: "Verified European job coverage",
      intro: "Only live, validated public ATS boards enter the monitored catalog.",
      verified: "Verified sources",
      healthy: "Healthy sources",
      review: "Needs review",
      activeJobs: "Active technical jobs",
      rawJobs: "Raw jobs scanned",
      aiMl: "AI / ML jobs",
      feeds: "Feeds checked",
      seeds: "Configured seeds",
      scope: `European technical jobs in this monitored catalog: ${values?.count ?? ""}.`,
      accounting: "Eligibility accounting",
      accountingBody: "These counts describe the monitored technical catalog.",
      eligible: "Eligible",
      unknown: "Unknown",
      rejected: "Rejected",
      diagnostics: "Source health diagnostics",
      diagnosticsBody: "Source health is shown by provider.",
      provider: "Provider",
      empty: "Empty",
      degraded: "Degraded",
      failingBlocked: "Failing / blocked",
      lastRefresh: `Last successful refresh: ${values?.value ?? ""}`,
      notRecorded: "not yet recorded",
    };
    return messages[key] ?? key;
  },
}));

describe("CoveragePage", () => {
  it("makes the measured scope and unknown opportunities visible", () => {
    render(<CoveragePage />);
    expect(screen.getByText("Verified European job coverage")).toBeInTheDocument();
    expect(screen.getByText("5,000")).toBeInTheDocument();
    expect(screen.getByText("400")).toBeInTheDocument();
    expect(screen.getByText("Eligibility accounting")).toBeInTheDocument();
    expect(screen.getByText("Source health diagnostics")).toBeInTheDocument();
    expect(screen.getByText("greenhouse")).toBeInTheDocument();
  });
});

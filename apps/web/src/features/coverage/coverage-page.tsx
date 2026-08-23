"use client";

import { useCoverage, useSourceHealth } from "@/lib/api/hooks";
import { formatNumber } from "@/lib/utils/format";
import { useLocale } from "next-intl";

export function CoveragePage() {
  const locale = useLocale();
  const coverage = useCoverage();
  const health = useSourceHealth();

  if (coverage.isLoading || health.isLoading) {
    return <main className="mx-auto max-w-5xl px-5 py-14">Loading coverage…</main>;
  }
  if (coverage.isError || health.isError || !coverage.data || !health.data) {
    return <main className="mx-auto max-w-5xl px-5 py-14">Coverage is currently unavailable.</main>;
  }

  const data = coverage.data;
  const review = data.degraded_sources + data.failing_sources + data.blocked_sources;
  const grouped = health.data.reduce<Record<string, Record<string, number>>>((groups, source) => {
    const provider = groups[source.provider] ?? {};
    provider[source.status] = (provider[source.status] ?? 0) + 1;
    groups[source.provider] = provider;
    return groups;
  }, {});
  const providers = Object.entries(grouped).sort(([left], [right]) => left.localeCompare(right));

  return (
    <main className="mx-auto max-w-5xl px-5 py-14 sm:px-8">
      <p className="text-xs font-bold uppercase tracking-[.14em] text-[var(--accent)]">Source coverage</p>
      <h1 className="mt-3 text-4xl font-black tracking-[-.05em] text-[var(--ink)]">Verified European job coverage</h1>
      <p className="mt-4 max-w-2xl text-[var(--muted)]">
        Only live, validated public ATS boards enter the monitored catalog. Unknown eligibility remains visible instead of being promoted to a positive claim.
      </p>
      <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Verified sources", data.verified_sources],
          ["Healthy sources", data.healthy_sources],
          ["Needs review", review],
          ["Active technical jobs", data.active_jobs],
        ].map(([label, value]) => (
          <div key={label} className="rounded-3xl border border-[var(--line)] bg-[var(--card)] p-6">
            <p className="text-sm text-[var(--muted)]">{label}</p>
            <p className="mt-2 text-3xl font-black text-[var(--ink)]">{formatNumber(Number(value), locale)}</p>
          </div>
        ))}
      </div>
      <p className="mt-4 text-sm text-[var(--muted)]">European technical jobs in this monitored catalog: <strong className="text-[var(--ink)]">{formatNumber(data.european_technical_jobs, locale)}</strong>. The active total includes worldwide boards because discovery is intentionally global.</p>
      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Raw jobs scanned", data.raw_jobs_scanned],
          ["AI / ML jobs", data.ai_ml_jobs],
          ["Feeds checked", data.sources_scanned_latest_run],
          ["Configured seeds", data.configured_sources],
        ].map(([label, value]) => (
          <div key={label} className="rounded-3xl border border-[var(--line)] bg-[var(--card)] p-5">
            <p className="text-sm text-[var(--muted)]">{label}</p>
            <p className="mt-1 text-2xl font-black text-[var(--ink)]">{formatNumber(Number(value), locale)}</p>
          </div>
        ))}
      </div>
      <div className="mt-8 rounded-3xl border border-[var(--line)] bg-[var(--card)] p-6">
        <h2 className="text-xl font-black text-[var(--ink)]">Eligibility accounting</h2>
        <p className="mt-2 text-sm text-[var(--muted)]">These counts describe the monitored technical catalog, not all European vacancies.</p>
        <div className="mt-5 grid gap-4 text-sm sm:grid-cols-3">
          <p><span className="text-[var(--muted)]">Eligible</span><strong className="mt-1 block text-lg text-[var(--ink)]">{formatNumber(data.eligible_jobs, locale)}</strong></p>
          <p><span className="text-[var(--muted)]">Unknown</span><strong className="mt-1 block text-lg text-[var(--ink)]">{formatNumber(data.unknown_jobs, locale)}</strong></p>
          <p><span className="text-[var(--muted)]">Rejected</span><strong className="mt-1 block text-lg text-[var(--ink)]">{formatNumber(data.rejected_jobs, locale)}</strong></p>
        </div>
      </div>
      <div className="mt-8 rounded-3xl border border-[var(--line)] bg-[var(--card)] p-6">
        <h2 className="text-xl font-black text-[var(--ink)]">Source health diagnostics</h2>
        <p className="mt-2 text-sm text-[var(--muted)]">Healthy, degraded, blocked, and failing boards are shown by provider so coverage limitations remain visible.</p>
        <div className="mt-5 overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead className="text-[var(--muted)]"><tr><th className="pb-3 font-medium">Provider</th><th className="pb-3 font-medium">Healthy</th><th className="pb-3 font-medium">Empty</th><th className="pb-3 font-medium">Degraded</th><th className="pb-3 font-medium">Failing / blocked</th></tr></thead>
            <tbody>{providers.map(([provider, statuses]) => <tr key={provider} className="border-t border-[var(--line)]"><th className="py-3 font-semibold capitalize text-[var(--ink)]">{provider}</th><td className="py-3 text-[var(--ink)]">{formatNumber(statuses.healthy ?? 0, locale)}</td><td className="py-3 text-[var(--ink)]">{formatNumber(statuses.empty ?? 0, locale)}</td><td className="py-3 text-[var(--ink)]">{formatNumber(statuses.degraded ?? 0, locale)}</td><td className="py-3 text-[var(--ink)]">{formatNumber((statuses.failing ?? 0) + (statuses.blocked ?? 0), locale)}</td></tr>)}</tbody>
          </table>
        </div>
        <p className="mt-5 text-sm text-[var(--muted)]">Last successful refresh: {data.last_refresh_at ? new Date(data.last_refresh_at).toLocaleString(locale) : "not yet recorded"}</p>
      </div>
    </main>
  );
}

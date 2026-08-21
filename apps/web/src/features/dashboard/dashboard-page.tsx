"use client";

import { ArrowUpRight, BarChart3, Building2, Globe2, ShieldCheck, Sparkles } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useMemo } from "react";
import { JobCard } from "@/components/cards/job-card";
import { StatCard } from "@/components/cards/stat-card";
import { PageHeading } from "@/components/common/page-heading";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useCandidate, useJobs, useRecommendations, useStats } from "@/lib/api/hooks";
import { RecommendationList } from "@/features/recommendations/recommendation-list";
import { useCandidateId } from "@/lib/utils/candidate";
import { formatCountry, formatNumber } from "@/lib/utils/format";

const DAY_MS = 24 * 60 * 60 * 1000;

export function DashboardPage() {
  const locale = useLocale();
  const t = useTranslations("dashboard");
  const c = useTranslations("common");
  const candidateId = useCandidateId();
  const { data: candidate } = useCandidate(candidateId);
  const { data: stats, isLoading: statsLoading, isError: statsError } = useStats();
  const { data: recommendations, isLoading: recLoading } = useRecommendations(candidateId, new URLSearchParams({ limit: "500" }));
  const { data: freshJobs, isLoading: jobsLoading } = useJobs(new URLSearchParams({ limit: "500" }));
  const signalJobs = candidateId ? recommendations?.map((item) => item.job) ?? [] : freshJobs ?? [];
  const newMatches = signalJobs.filter((job) => job.posted_at && Date.now() - new Date(job.posted_at).getTime() <= DAY_MS).length;
  const highConfidence = recommendations?.filter((item) => item.scores.overall >= 80).length ?? 0;
  const topCountry = useMemo(() => {
    if (recommendations?.length) {
      const weights = new Map<string, number>();
      for (const item of recommendations) {
        if (!item.job.country) continue;
        weights.set(item.job.country, (weights.get(item.job.country) ?? 0) + item.scores.overall);
      }
      const winner = [...weights.entries()].sort((a, b) => b[1] - a[1])[0]?.[0];
      if (winner) return formatCountry(winner, locale);
    }
    return candidate?.preferred_countries[0] ? formatCountry(candidate.preferred_countries[0], locale) : "—";
  }, [candidate?.preferred_countries, locale, recommendations]);
  const shownRecommendations = recommendations?.slice(0, 3);
  const shownFreshJobs = freshJobs?.slice(0, 3);
  const arrowClass = locale === "fa" ? "rotate-180" : "";
  return <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:px-10 lg:py-14"><PageHeading eyebrow="Career Radar" title={t("greeting")} description={t("intro")} action={<Button asChild variant="soft"><Link href={`/${locale}/${candidateId ? "profile" : "onboarding"}`}><Sparkles size={16} />{candidateId ? c("profile") : t("setupAction")}</Link></Button>} /><div className="mt-10 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><StatCard label={t("newMatches")} value={recLoading || jobsLoading ? "…" : formatNumber(newMatches, locale)} detail={t("last24h")} icon={BarChart3} /><StatCard label={t("eligible")} value={statsLoading ? "…" : statsError ? "—" : formatNumber(stats?.eligible_jobs ?? 0, locale)} detail={t("evidenceGate")} icon={ShieldCheck} tone="success" /><StatCard label={t("confidence")} value={!candidateId ? "—" : recLoading ? "…" : formatNumber(highConfidence, locale)} detail={t("personalized")} icon={Sparkles} /><StatCard label={t("target")} value={topCountry} detail={t("preferences")} icon={Globe2} tone="warning" /></div>{statsError && <div className="mt-6 rounded-2xl border border-[var(--amber)]/30 bg-[var(--amber-soft)] px-4 py-3 text-sm text-[var(--amber)]">{c("unavailable")} {t("apiHint")}</div>}<section className="mt-12"><div className="mb-5 flex items-end justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-[.14em] text-[var(--accent)]">{candidateId ? t("personalSignal") : t("exploreMarket")}</p><h2 className="mt-2 text-2xl font-black tracking-[-.04em] text-[var(--ink)]">{candidateId ? t("recommendations") : t("recent")}</h2></div><Link href={`/${locale}/jobs`} className="focus-ring flex items-center gap-1 text-sm font-bold text-[var(--accent)]">{t("viewAll")}<ArrowUpRight size={15} className={arrowClass} /></Link></div>{candidateId ? recLoading ? <div className="grid gap-4 lg:grid-cols-3"><Skeleton className="h-72" /><Skeleton className="h-72" /><Skeleton className="h-72" /></div> : shownRecommendations?.length ? <RecommendationList recommendations={shownRecommendations} explanationHref={`/${locale}/recommendations/${candidateId}/explain`} /> : <EmptyState title={c("noResults")} body={c("unavailable")} /> : jobsLoading ? <div className="grid gap-4 lg:grid-cols-3"><Skeleton className="h-64" /><Skeleton className="h-64" /><Skeleton className="h-64" /></div> : shownFreshJobs?.length ? <div className="grid gap-4 lg:grid-cols-3">{shownFreshJobs.map((job) => <JobCard key={job.id} job={job} />)}</div> : <EmptyState title={t("setup")} body={t("profileBody")} action={t("setupAction")} onAction={() => window.location.assign(`/${locale}/onboarding`)} />}</section><section className="mt-12 grid gap-4 lg:grid-cols-[1.2fr_.8fr]"><div className="rounded-3xl bg-[var(--ink)] p-7 text-[var(--paper)] sm:p-9"><div className="flex size-11 items-center justify-center rounded-2xl bg-white/10"><Building2 size={20} /></div><h2 className="mt-7 max-w-md text-2xl font-black tracking-[-.04em]">{t("evidenceTitle")}</h2><p className="mt-3 max-w-lg text-sm leading-7 text-white/60">{t("evidenceBody")}</p><Link href={`/${locale}/companies`} className="mt-7 inline-flex items-center gap-2 text-sm font-bold text-white">{t("companySignals")} <ArrowUpRight size={15} className={arrowClass} /></Link></div><div className="rounded-3xl border border-[var(--line)] bg-[var(--card)] p-7"><p className="text-xs font-bold uppercase tracking-[.14em] text-[var(--accent)]">{t("philosophy")}</p><p className="mt-6 text-xl font-black leading-snug tracking-[-.035em] text-[var(--ink)]">{t("unknownTitle")}</p><p className="mt-4 text-sm leading-6 text-[var(--muted)]">{t("unknownBody")}</p></div></section></div>;
}

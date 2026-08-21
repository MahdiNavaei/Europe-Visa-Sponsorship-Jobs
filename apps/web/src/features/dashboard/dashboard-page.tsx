"use client";

import { ArrowUpRight, BarChart3, Building2, Globe2, ShieldCheck, Sparkles } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { JobCard } from "@/components/cards/job-card";
import { StatCard } from "@/components/cards/stat-card";
import { PageHeading } from "@/components/common/page-heading";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useJobs, useRecommendations, useStats } from "@/lib/api/hooks";
import { RecommendationList } from "@/features/recommendations/recommendation-list";

export function DashboardPage() {
  const locale = useLocale();
  const t = useTranslations("dashboard");
  const c = useTranslations("common");
  const { data: stats, isLoading: statsLoading, isError: statsError } = useStats();
  const [candidateId, setCandidateId] = useState<number | null>(null);
  useEffect(() => { const value = window.localStorage.getItem("career-radar-candidate"); if (value) setCandidateId(Number(value)); }, []);
  const params = new URLSearchParams({ limit: "3" });
  const { data: recommendations, isLoading: recLoading } = useRecommendations(candidateId, new URLSearchParams({ limit: "3" }));
  const { data: freshJobs, isLoading: jobsLoading } = useJobs(params);
  const topCountry = candidateId ? undefined : "—";
  return <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:px-10 lg:py-14"><PageHeading eyebrow="Career Radar" title={t("greeting")} description={t("intro")} action={<Button asChild variant="soft"><Link href={`/${locale}/onboarding`}><Sparkles size={16} />{candidateId ? c("profile") : t("setupAction")}</Link></Button>} /><div className="mt-10 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><StatCard label={t("newMatches")} value={statsLoading ? "…" : statsError ? "—" : stats?.total_jobs ?? 0} detail="Active intelligence pool" icon={BarChart3} /><StatCard label={t("eligible")} value={statsLoading ? "…" : statsError ? "—" : stats?.eligible_jobs ?? 0} detail="Passed strict evidence gate" icon={ShieldCheck} tone="success" /><StatCard label={t("confidence")} value={candidateId ? (recLoading ? "…" : recommendations?.filter((item) => item.scores.overall >= 80).length ?? 0) : "—"} detail="Personalized to your profile" icon={Sparkles} /><StatCard label={t("target")} value={topCountry} detail="From your preferences" icon={Globe2} tone="warning" /></div>{statsError && <div className="mt-6 rounded-2xl border border-[var(--amber)]/30 bg-[var(--amber-soft)] px-4 py-3 text-sm text-[var(--amber)]">{c("unavailable")} Start the API on port 8000 to load live intelligence.</div>}<section className="mt-12"><div className="mb-5 flex items-end justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-[.14em] text-[var(--accent)]">{candidateId ? "Personal signal" : "Explore the market"}</p><h2 className="mt-2 text-2xl font-black tracking-[-.04em] text-[var(--ink)]">{candidateId ? t("recommendations") : t("recent")}</h2></div><Link href={`/${locale}/jobs`} className="focus-ring flex items-center gap-1 text-sm font-bold text-[var(--accent)]">{t("viewAll")}<ArrowUpRight size={15} /></Link></div>{candidateId ? recLoading ? <div className="grid gap-4 lg:grid-cols-3"><Skeleton className="h-72" /><Skeleton className="h-72" /><Skeleton className="h-72" /></div> : recommendations?.length ? <RecommendationList recommendations={recommendations} explanationHref={`/${locale}/recommendations/${candidateId}/explain`} /> : <EmptyState title={c("noResults")} body={c("unavailable")} /> : jobsLoading ? <div className="grid gap-4 lg:grid-cols-3"><Skeleton className="h-64" /><Skeleton className="h-64" /><Skeleton className="h-64" /></div> : freshJobs?.length ? <div className="grid gap-4 lg:grid-cols-3">{freshJobs.map((job) => <JobCard key={job.id} job={job} />)}</div> : <EmptyState title={t("setup")} body="Create your profile and connect the API to see roles selected for your goals." action={t("setupAction")} onAction={() => window.location.assign(`/${locale}/onboarding`)} />}</section><section className="mt-12 grid gap-4 lg:grid-cols-[1.2fr_.8fr]"><div className="rounded-3xl bg-[var(--ink)] p-7 text-[var(--paper)] sm:p-9"><div className="flex size-11 items-center justify-center rounded-2xl bg-white/10"><Building2 size={20} /></div><h2 className="mt-7 max-w-md text-2xl font-black tracking-[-.04em]">Evidence before enthusiasm.</h2><p className="mt-3 max-w-lg text-sm leading-7 text-white/60">Career Radar keeps sponsorship signals, country rules and your own profile in the same conversation.</p><Link href={`/${locale}/companies`} className="mt-7 inline-flex items-center gap-2 text-sm font-bold text-white">Explore company signals <ArrowUpRight size={15} /></Link></div><div className="rounded-3xl border border-[var(--line)] bg-[var(--card)] p-7"><p className="text-xs font-bold uppercase tracking-[.14em] text-[var(--accent)]">Data philosophy</p><p className="mt-6 text-xl font-black leading-snug tracking-[-.035em] text-[var(--ink)]">When the evidence is weak, the platform says so.</p><p className="mt-4 text-sm leading-6 text-[var(--muted)]">Unknown is better than a confident guess when relocation is on the line.</p></div></section></div>;
}

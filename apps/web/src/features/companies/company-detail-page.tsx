"use client";

import { ArrowLeft, ArrowRight, Building2, CheckCircle2, ExternalLink, ShieldCheck, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { JobCard } from "@/components/cards/job-card";
import { PageHeading } from "@/components/common/page-heading";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ScoreBar } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { useCompany } from "@/lib/api/hooks";
import { formatCountry, formatNumber, formatScore } from "@/lib/utils/format";

export function CompanyDetailPage({ id }: { id: number }) {
  const locale = useLocale();
  const t = useTranslations("companies");
  const c = useTranslations("common");
  const { data, isLoading, isError, refetch } = useCompany(id);
  const BackIcon = locale === "fa" ? ArrowRight : ArrowLeft;
  if (isLoading) return <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:px-10"><Skeleton className="h-12 w-1/2" /><Skeleton className="mt-8 h-96" /></div>;
  if (isError || !data) return <div className="mx-auto max-w-2xl px-5 py-20"><EmptyState title={c("unavailable")} body={t("unavailableBody")} action={c("tryAgain")} onAction={() => void refetch()} /></div>;
  const { company } = data;
  return <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:px-10 lg:py-14"><Link href={`/${locale}/companies`} className="focus-ring mb-8 inline-flex items-center gap-2 text-sm font-bold text-[var(--muted)] hover:text-[var(--accent)]"><BackIcon size={15} />{c("companies")}</Link><PageHeading eyebrow={t("detailEyebrow")} title={company.name} description={`${formatCountry(company.country, locale)} · ${company.sponsor_verified ? c("verified") : t("evidenceReview")}`} action={company.career_url ? <Button asChild variant="secondary"><a href={company.career_url} target="_blank" rel="noreferrer">{t("careerSite")}<ExternalLink size={15} /></a></Button> : undefined} /><div className="mt-10 grid gap-5 lg:grid-cols-[.85fr_1.15fr]"><Card className="overflow-hidden"><div className="bg-[var(--ink)] p-7 text-[var(--paper)]"><div className="flex items-center justify-between"><div><p className="text-xs font-bold uppercase tracking-[.14em] text-white/55">{t("friendliness")}</p><p className="mt-3 text-5xl font-black tracking-[-.07em]">{formatScore(data.visa_friendliness_score, locale)}</p></div><div className="grid size-12 place-items-center rounded-2xl bg-white/10 text-[var(--mint)]"><ShieldCheck size={23} /></div></div></div><CardContent className="pt-6"><ScoreBar value={data.visa_friendliness_score} color="success" /><div className="mt-7 grid grid-cols-2 gap-3"><Metric label={t("activeRoles")} value={formatNumber(data.active_jobs, locale)} /><Metric label={t("eligibleRoles")} value={formatNumber(data.eligible_jobs, locale)} /></div></CardContent></Card><div className="grid gap-5 sm:grid-cols-2"><SignalCard title={t("positive")} items={data.positive_signals} positive empty={t("noSignals")} /><SignalCard title={t("negative")} items={data.negative_signals} empty={t("noSignals")} /></div></div><section className="mt-12"><div className="mb-5 flex items-center gap-3"><Building2 size={18} className="text-[var(--accent)]" /><h2 className="text-2xl font-black tracking-[-.04em] text-[var(--ink)]">{t("openRoles")}</h2></div>{data.jobs.length ? <div className="grid gap-4 lg:grid-cols-2">{data.jobs.map((job) => <JobCard key={job.id} job={job} />)}</div> : <EmptyState title={c("noResults")} body={t("noSignals")} />}</section></div>;
}

function Metric({ label, value }: { label: string; value: string }) { return <div className="rounded-2xl bg-[var(--paper)] p-4"><p className="text-xs font-bold text-[var(--muted)]">{label}</p><p className="mt-2 text-2xl font-black text-[var(--ink)]">{value}</p></div>; }
function SignalCard({ title, items, positive = false, empty }: { title: string; items: string[]; positive?: boolean; empty: string }) { return <Card><CardHeader><CardTitle>{title}</CardTitle></CardHeader><CardContent><div className="space-y-3">{items.length ? items.map((item) => <p key={item} className="flex gap-2 text-sm leading-6 text-[var(--muted)]">{positive ? <CheckCircle2 size={16} className="mt-1 shrink-0 text-[var(--mint)]" /> : <TriangleAlert size={16} className="mt-1 shrink-0 text-[var(--amber)]" />}{item}</p>) : <p className="text-sm text-[var(--muted)]">{empty}</p>}</div></CardContent></Card>; }

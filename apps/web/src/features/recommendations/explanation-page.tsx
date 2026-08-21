"use client";

import { ArrowLeft, ArrowRight, CheckCircle2, Scale, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { JobCard } from "@/components/cards/job-card";
import { PageHeading } from "@/components/common/page-heading";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useRecommendationExplanation } from "@/lib/api/hooks";
import { formatNumber, formatScore, labelize } from "@/lib/utils/format";

export function ExplanationPage({ candidateId }: { candidateId: number }) {
  const locale = useLocale();
  const t = useTranslations("explanation");
  const scoreT = useTranslations("scores");
  const validCandidateId = Number.isFinite(candidateId) && candidateId > 0 ? candidateId : null;
  const { data, isLoading, isError } = useRecommendationExplanation(validCandidateId, new URLSearchParams({ limit: "50" }));
  const BackIcon = locale === "fa" ? ArrowRight : ArrowLeft;
  if (!validCandidateId) return <div className="mx-auto max-w-2xl px-5 py-20 sm:px-8"><EmptyState title={t("buildFirst")} body={t("buildBody")} /></div>;
  if (isLoading) return <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:px-10"><Skeleton className="h-14 w-1/2" /><Skeleton className="mt-8 h-72" /></div>;
  if (isError || !data) return <div className="mx-auto max-w-2xl px-5 py-20 sm:px-8"><EmptyState title={t("unavailable")} body={t("unavailableBody")} /></div>;
  const weightLabel = (key: string) => {
    if (key === "visa" || key === "skill" || key === "experience" || key === "country" || key === "company") return scoreT(key);
    return labelize(key.replace("_score", ""));
  };
  return <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:px-10 lg:py-14"><Link href={`/${locale}/dashboard`} className="focus-ring mb-8 inline-flex items-center gap-2 text-sm font-bold text-[var(--muted)] hover:text-[var(--accent)]"><BackIcon size={15} />{t("back")}</Link><PageHeading eyebrow={t("eyebrow")} title={t("title", { name: data.candidate.name })} description={t("description")} /><div className="mt-10 grid gap-5 lg:grid-cols-[.75fr_1.25fr]"><Card><CardHeader><CardTitle>{t("weights")}</CardTitle><Scale size={18} className="text-[var(--accent)]" /></CardHeader><CardContent><div className="space-y-4">{Object.entries(data.weights).map(([key, value]) => <div key={key} className="flex items-center justify-between gap-4"><span className="text-sm font-semibold text-[var(--muted)]">{weightLabel(key)}</span><Badge tone="accent">{formatScore(value * 100, locale)}</Badge></div>)}</div><div className="mt-7 border-t border-[var(--line)] pt-6"><p className="text-xs font-bold uppercase tracking-[.12em] text-[var(--muted)]">{t("profileLens")}</p><p className="mt-3 text-sm leading-6 text-[var(--ink)]">{t("profileSummary", { skills: formatNumber(data.candidate.skills.length, locale), years: formatNumber(data.candidate.years_of_experience, locale), countries: data.candidate.preferred_countries.length ? formatNumber(data.candidate.preferred_countries.length, locale) : t("openTargets") })}</p></div></CardContent></Card><div className="space-y-4">{data.recommendations.map((item) => <Card key={item.job_id}><CardContent className="pt-5"><JobCard job={item.job} recommendation={item} /><div className="mt-5 grid gap-3 border-t border-[var(--line)] pt-5 sm:grid-cols-2">{item.reasons.slice(0, 3).map((reason) => <p key={reason} className="flex gap-2 text-xs leading-5 text-[var(--muted)]"><CheckCircle2 size={14} className="mt-0.5 shrink-0 text-[var(--mint)]" />{reason}</p>)}{item.warnings.slice(0, 2).map((warning) => <p key={warning} className="flex gap-2 text-xs leading-5 text-[var(--muted)]"><TriangleAlert size={14} className="mt-0.5 shrink-0 text-[var(--amber)]" />{warning}</p>)}</div></CardContent></Card>)}</div></div></div>;
}

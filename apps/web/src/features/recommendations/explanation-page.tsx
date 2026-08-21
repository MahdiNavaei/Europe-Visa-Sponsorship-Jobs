"use client";

import { ArrowLeft, CheckCircle2, Scale, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useLocale } from "next-intl";
import { useEffect, useState } from "react";
import { JobCard } from "@/components/cards/job-card";
import { PageHeading } from "@/components/common/page-heading";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api/client";
import type { RecommendationExplanation } from "@/lib/types";

export function ExplanationPage() {
  const locale = useLocale();
  const [candidateId, setCandidateId] = useState<number | null>(null);
  const [data, setData] = useState<RecommendationExplanation | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => { const value = window.localStorage.getItem("career-radar-candidate"); if (!value) return; const id = Number(value); setCandidateId(id); void api.explainRecommendations(id, new URLSearchParams({ limit: "50" })).then(setData).catch(() => setError(true)); }, []);
  if (!candidateId) return <div className="mx-auto max-w-2xl px-5 py-20 sm:px-8"><EmptyState title="Build your profile first" body="The explanation view needs a candidate profile to compare against the live job index." action="Build profile" onAction={() => window.location.assign(`/${locale}/onboarding`)} /></div>;
  if (!data && !error) return <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:px-10"><Skeleton className="h-14 w-1/2" /><Skeleton className="mt-8 h-72" /></div>;
  if (error || !data) return <div className="mx-auto max-w-2xl px-5 py-20 sm:px-8"><EmptyState title="Explanation unavailable" body="The API could not return the recommendation evidence." /></div>;
  return <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:px-10 lg:py-14"><Link href={`/${locale}/dashboard`} className="focus-ring mb-8 inline-flex items-center gap-2 text-sm font-bold text-[var(--muted)] hover:text-[var(--accent)]"><ArrowLeft size={15} />Dashboard</Link><PageHeading eyebrow="Recommendation evidence" title={`Why these roles fit ${data.candidate.name}`} description="The ranking engine exposes the signals and trade-offs behind every recommendation." /><div className="mt-10 grid gap-5 lg:grid-cols-[.75fr_1.25fr]"><Card><CardHeader><CardTitle>Ranking weights</CardTitle><Scale size={18} className="text-[var(--accent)]" /></CardHeader><CardContent><div className="space-y-4">{Object.entries(data.weights).map(([key, value]) => <div key={key} className="flex items-center justify-between gap-4"><span className="text-sm font-semibold text-[var(--muted)]">{key.replace("_score", "").replaceAll("_", " ")}</span><Badge tone="accent">{Math.round(value * 100)}%</Badge></div>)}</div><div className="mt-7 border-t border-[var(--line)] pt-6"><p className="text-xs font-bold uppercase tracking-[.12em] text-[var(--muted)]">Profile lens</p><p className="mt-3 text-sm leading-6 text-[var(--ink)]">{data.candidate.skills.length} canonical skills · {data.candidate.years_of_experience} years · {data.candidate.preferred_countries.length || "Open"} target countries</p></div></CardContent></Card><div className="space-y-4">{data.recommendations.map((item) => <Card key={item.job_id}><CardContent className="pt-5"><JobCard job={item.job} recommendation={item} /><div className="mt-5 grid gap-3 border-t border-[var(--line)] pt-5 sm:grid-cols-2">{item.reasons.slice(0, 3).map((reason) => <p key={reason} className="flex gap-2 text-xs leading-5 text-[var(--muted)]"><CheckCircle2 size={14} className="mt-0.5 shrink-0 text-[var(--mint)]" />{reason}</p>)}{item.warnings.slice(0, 2).map((warning) => <p key={warning} className="flex gap-2 text-xs leading-5 text-[var(--muted)]"><TriangleAlert size={14} className="mt-0.5 shrink-0 text-[var(--amber)]" />{warning}</p>)}</div></CardContent></Card>)}</div></div></div>;
}

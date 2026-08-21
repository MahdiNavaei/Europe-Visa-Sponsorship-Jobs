"use client";

import { ArrowUpRight, BriefcaseBusiness, CheckCircle2, MapPin, Pencil, ShieldCheck, UserRound } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { ScoreBreakdown } from "@/components/charts/score-breakdown";
import { PageHeading } from "@/components/common/page-heading";
import { JobCard } from "@/components/cards/job-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useCandidate, useRecommendations } from "@/lib/api/hooks";
import { labelize } from "@/lib/utils/format";

export function ProfilePage() {
  const locale = useLocale();
  const c = useTranslations("common");
  const [candidateId, setCandidateId] = useState<number | null>(null);
  useEffect(() => { const value = window.localStorage.getItem("career-radar-candidate"); if (value) setCandidateId(Number(value)); }, []);
  const { data: candidate, isLoading } = useCandidate(candidateId);
  const { data: recommendations } = useRecommendations(candidateId, new URLSearchParams({ limit: "3" }));
  if (isLoading) return <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:px-10"><Skeleton className="h-12 w-1/2" /><Skeleton className="mt-8 h-80" /></div>;
  if (!candidate) return <div className="mx-auto max-w-2xl px-5 py-20 sm:px-8"><EmptyState title="Your profile is waiting" body="Build a profile once and Career Radar will keep your priorities close to every recommendation." action={c("onboarding")} onAction={() => window.location.assign(`/${locale}/onboarding`)} /></div>;
  const best = recommendations?.[0];
  return <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:px-10 lg:py-14"><PageHeading eyebrow="Personal signal" title={candidate.name} description="Your profile is the lens behind every recommendation." action={<Button asChild variant="secondary"><Link href={`/${locale}/onboarding`}><Pencil size={15} />Edit profile</Link></Button>} /><div className="mt-10 grid gap-5 lg:grid-cols-[.8fr_1.2fr]"><Card><CardHeader><CardTitle>{c("profile")}</CardTitle><div className="grid size-10 place-items-center rounded-xl bg-[var(--accent-soft)] text-[var(--accent)]"><UserRound size={18} /></div></CardHeader><CardContent><div className="space-y-5"><ProfileLine icon={BriefcaseBusiness} label="Target roles" value={candidate.target_roles.join(" · ")} /><ProfileLine icon={ShieldCheck} label="Visa support" value={candidate.visa_required ? "Employer support needed" : "Work authorization in place"} /><ProfileLine icon={MapPin} label="Preferred countries" value={candidate.preferred_countries.length ? candidate.preferred_countries.join(" · ") : "Open to Europe"} /></div><div className="mt-7 border-t border-[var(--line)] pt-5"><p className="text-xs font-bold uppercase tracking-[.12em] text-[var(--muted)]">Skills</p><div className="mt-3 flex flex-wrap gap-2">{candidate.skills.length ? candidate.skills.map((skill) => <Badge key={skill} tone="accent">{skill}</Badge>) : <span className="text-sm text-[var(--muted)]">Add skills to sharpen your match.</span>}</div></div></CardContent></Card><Card><CardHeader><div><CardTitle>Recommendation anatomy</CardTitle><p className="mt-1 text-xs text-[var(--muted)]">Scores come from the backend intelligence engine.</p></div>{best && <Badge tone="success"><CheckCircle2 size={12} />{Math.round(best.scores.overall)}% best match</Badge>}</CardHeader><CardContent>{best ? <><ScoreBreakdown scores={best.scores} /><Link href={`/${locale}/jobs/${best.job_id}`} className="mt-2 flex items-center justify-between rounded-xl bg-[var(--paper)] px-4 py-3 text-sm font-bold text-[var(--accent)]">{best.job.title}<ArrowUpRight size={15} /></Link></> : <p className="py-12 text-center text-sm text-[var(--muted)]">Recommendations will appear after the API returns eligible roles.</p>}</CardContent></Card></div><section className="mt-12"><div className="mb-5 flex items-end justify-between"><div><p className="text-xs font-bold uppercase tracking-[.14em] text-[var(--accent)]">Shortlist</p><h2 className="mt-2 text-2xl font-black tracking-[-.04em] text-[var(--ink)]">Your strongest signals</h2></div><Link href={`/${locale}/jobs`} className="text-sm font-bold text-[var(--accent)]">{c("jobs")}</Link></div>{recommendations?.length ? <div className="grid gap-4 lg:grid-cols-3">{recommendations.map((item) => <JobCard key={item.job_id} job={item.job} recommendation={item} />)}</div> : <EmptyState title="No recommendations yet" body="The API will rank eligible opportunities against your profile." />}</section></div>;
}

function ProfileLine({ icon: Icon, label, value }: { icon: typeof BriefcaseBusiness; label: string; value: string }) { return <div className="flex gap-3"><Icon size={16} className="mt-0.5 text-[var(--accent)]" /><div><p className="text-xs font-bold uppercase tracking-[.11em] text-[var(--muted)]">{label}</p><p className="mt-1 text-sm font-semibold leading-6 text-[var(--ink)]">{value}</p></div></div>; }

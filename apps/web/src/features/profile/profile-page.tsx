"use client";

import { ArrowUpRight, BriefcaseBusiness, CheckCircle2, MapPin, Pencil, ShieldCheck, UserRound } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { ScoreBreakdown } from "@/components/charts/score-breakdown";
import { PageHeading } from "@/components/common/page-heading";
import { JobCard } from "@/components/cards/job-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useCandidate, useRecommendations } from "@/lib/api/hooks";
import { useCandidateId } from "@/lib/utils/candidate";
import { formatCountry, formatScore } from "@/lib/utils/format";

function formatPreference(value: string | null, locale: string) {
  if (!value) return "—";
  const labels = locale === "fa"
    ? { required: "الزامی", preferred: "ترجیحی", no_preference: "بدون ترجیح" }
    : { required: "Required", preferred: "Preferred", no_preference: "No preference" };
  return labels[value as keyof typeof labels] ?? value.replaceAll("_", " ");
}

function formatSeniority(value: string | null, locale: string) {
  if (!value) return "—";
  const fa = { intern: "کارآموز", junior: "جونیور", mid: "میانی", senior: "سینیور", staff: "استف", lead: "لید", principal: "پرینسیپال", director: "مدیر" };
  return locale === "fa" ? fa[value as keyof typeof fa] ?? value : value.charAt(0).toUpperCase() + value.slice(1);
}

export function ProfilePage() {
  const locale = useLocale();
  const c = useTranslations("common");
  const t = useTranslations("profile");
  const router = useRouter();
  const candidateId = useCandidateId();
  const { data: candidate, isLoading } = useCandidate(candidateId);
  const { data: recommendations } = useRecommendations(candidateId, new URLSearchParams({ limit: "3" }));

  if (isLoading) return <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8"><Skeleton className="h-12 w-1/2" /><Skeleton className="mt-8 h-80" /></div>;
  if (!candidate) return <div className="mx-auto max-w-2xl px-5 py-20 sm:px-8"><EmptyState title={t("waiting")} body={t("waitingBody")} action={c("onboarding")} onAction={() => router.push(`/${locale}/onboarding`)} /></div>;

  const best = recommendations?.[0];
  return (
    <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:px-10 lg:py-14">
      <PageHeading eyebrow={t("eyebrow")} title={candidate.name} description={t("description")} action={<Button asChild variant="secondary"><Link href={`/${locale}/onboarding`}><Pencil size={15} />{t("edit")}</Link></Button>} />
      <div className="mt-10 grid gap-5 lg:grid-cols-[.8fr_1.2fr]">
        <Card>
          <CardHeader><CardTitle>{c("profile")}</CardTitle><div className="grid size-10 place-items-center rounded-xl bg-[var(--accent-soft)] text-[var(--accent)]"><UserRound size={18} /></div></CardHeader>
          <CardContent>
            <div className="space-y-5">
              <ProfileLine icon={BriefcaseBusiness} label={t("targetRoles")} value={candidate.target_roles.join(" · ")} />
              <ProfileLine icon={ShieldCheck} label={t("visaSupport")} value={candidate.visa_required ? t("employerNeeded") : t("authorized")} />
              <ProfileLine icon={MapPin} label={t("preferredCountries")} value={candidate.preferred_countries.length ? candidate.preferred_countries.map((item) => formatCountry(item, locale)).join(" · ") : t("openEurope")} />
              <ProfileLine icon={BriefcaseBusiness} label={t("experience")} value={`${candidate.years_of_experience} ${t("years")}`} />
              <ProfileLine icon={UserRound} label={t("seniority")} value={formatSeniority(candidate.seniority, locale)} />
              <ProfileLine icon={MapPin} label={t("relocation")} value={formatPreference(candidate.relocation_preference, locale)} />
              <ProfileLine icon={MapPin} label={t("remote")} value={formatPreference(candidate.remote_preference, locale)} />
            </div>
            <div className="mt-7 border-t border-[var(--line)] pt-5"><p className="text-xs font-bold uppercase tracking-[.12em] text-[var(--muted)]">{t("skills")}</p><div className="mt-3 flex flex-wrap gap-2">{candidate.skills.length ? candidate.skills.map((skill) => <Badge key={skill} tone="accent">{skill}</Badge>) : <span className="text-sm text-[var(--muted)]">{t("addSkills")}</span>}</div></div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><div><CardTitle>{t("anatomy")}</CardTitle><p className="mt-1 text-xs text-[var(--muted)]">{t("anatomyBody")}</p></div>{best && <Badge tone="success"><CheckCircle2 size={12} />{formatScore(best.scores.overall, locale)} {t("bestMatch")}</Badge>}</CardHeader>
          <CardContent>{best ? <><ScoreBreakdown scores={best.scores} /><Link href={`/${locale}/jobs/${best.job_id}`} className="mt-2 flex items-center justify-between rounded-xl bg-[var(--paper)] px-4 py-3 text-sm font-bold text-[var(--accent)]">{best.job.title}<ArrowUpRight size={15} className={locale === "fa" ? "rotate-180" : ""} /></Link></> : <p className="py-12 text-center text-sm text-[var(--muted)]">{t("noRecommendations")}</p>}</CardContent>
        </Card>
      </div>
      <section className="mt-12"><div className="mb-5 flex items-end justify-between"><div><p className="text-xs font-bold uppercase tracking-[.14em] text-[var(--accent)]">{t("shortlist")}</p><h2 className="mt-2 text-2xl font-black tracking-[-.04em] text-[var(--ink)]">{t("strongest")}</h2></div><Link href={`/${locale}/jobs`} className="text-sm font-bold text-[var(--accent)]">{c("jobs")}</Link></div>{recommendations?.length ? <div className="grid gap-4 lg:grid-cols-3">{recommendations.map((item) => <JobCard key={item.job_id} job={item.job} recommendation={item} />)}</div> : <EmptyState title={t("noneTitle")} body={t("noneBody")} />}</section>
    </div>
  );
}

function ProfileLine({ icon: Icon, label, value }: { icon: typeof BriefcaseBusiness; label: string; value: string }) {
  return <div className="flex gap-3"><Icon size={16} className="mt-0.5 text-[var(--accent)]" /><div><p className="text-xs font-bold uppercase tracking-[.11em] text-[var(--muted)]">{label}</p><p className="mt-1 text-sm font-semibold leading-6 text-[var(--ink)]">{value}</p></div></div>;
}

"use client";

import { ArrowUpRight, Building2, CheckCircle2, MapPin, ShieldCheck, Sparkles, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ScoreBadge, ScoreBar } from "@/components/ui/progress";
import type { Job, Recommendation } from "@/lib/types";
import { formatCountry, formatDate, formatJobFamily, formatScore, formatStatus } from "@/lib/utils/format";
import { localizeRecommendationReason } from "@/lib/i18n/recommendation-reasons";

export function JobCard({ job, recommendation }: { job: Job; recommendation?: Recommendation }) {
  const locale = useLocale();
  const common = useTranslations("common");
  const card = useTranslations("card");
  const reasonT = useTranslations("recommendationReasons");
  const score = recommendation?.scores.overall ?? job.eligibility_score;
  const visa = recommendation?.scores.visa ?? job.eligibility_score;

  return (
    <Card className="group overflow-hidden transition duration-300 hover:-translate-y-1 hover:border-[var(--accent)] hover:shadow-[var(--shadow-card)]">
      <div className="p-5 sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex min-w-0 flex-1 gap-3">
            <div className="grid size-11 shrink-0 place-items-center rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)]"><Building2 size={19} /></div>
            <div className="min-w-0 flex-1">
              <h3 className="line-clamp-2 text-base font-black leading-snug tracking-[-.025em] text-[var(--ink)] sm:text-lg">{job.title}</h3>
              <p className="mt-1 truncate text-sm font-medium text-[var(--muted)]">{job.company_name}</p>
            </div>
          </div>
          <ScoreBadge value={score} label={recommendation ? card("yourMatch") : card("visaScore")} tone={recommendation ? "accent" : "success"} />
        </div>

        <div className="mt-5 flex flex-wrap gap-2">
          <Badge tone={job.eligibility_status === "eligible" ? "success" : job.eligibility_status === "unknown" ? "warning" : "danger"}>
            <ShieldCheck size={12} />
            {job.eligibility_status === "eligible" ? common("eligible") : formatStatus(job.eligibility_status, locale)}
          </Badge>
          <Badge><MapPin size={12} />{formatCountry(job.country ?? job.location, locale)}</Badge>
          <Badge tone="neutral">{formatJobFamily(job.job_family, locale)}</Badge>
        </div>

        {recommendation ? (
          <div className="mt-5 grid gap-3 rounded-2xl bg-[var(--paper)] p-4 sm:grid-cols-2">
            <div>
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-[var(--muted)]">{card("visaCompatibility")}</span>
                <span className="font-bold text-[var(--ink)]">{formatScore(visa, locale)}</span>
              </div>
              <div className="mt-2"><ScoreBar value={visa} color="success" /></div>
            </div>
            <div>
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-[var(--muted)]">{card("skillAlignment")}</span>
                <span className="font-bold text-[var(--ink)]">{formatScore(recommendation.scores.skill, locale)}</span>
              </div>
              <div className="mt-2"><ScoreBar value={recommendation.scores.skill} /></div>
            </div>
          </div>
        ) : (
          <p className="mt-5 line-clamp-2 text-sm leading-6 text-[var(--muted)]">{job.description || card("fallback")}</p>
        )}

        <div className="mt-5 flex items-center justify-between gap-3 border-t border-[var(--line)] pt-4">
          <div className="flex min-w-0 flex-wrap gap-x-4 gap-y-1 text-xs text-[var(--muted)]">
            <span className="flex items-center gap-1.5"><Sparkles size={13} className="text-[var(--accent)]" />{formatDate(job.posted_at, locale)}</span>
            {job.workplace_type && <span>{job.workplace_type}</span>}
          </div>
          <Button asChild variant="ghost" size="sm">
            <Link href={`/${locale}/jobs/${job.id}`}>{common("viewDetails")}<ArrowUpRight size={15} className={locale === "fa" ? "rotate-180" : ""} /></Link>
          </Button>
        </div>

        {recommendation && (recommendation.reasons.length > 0 || recommendation.warnings.length > 0) && (
          <div className="mt-4 space-y-2">
            {recommendation.reasons.slice(0, 2).map((reason) => (
              <p key={reason} className="flex gap-2 text-xs leading-5 text-[var(--muted)]"><CheckCircle2 size={14} className="mt-0.5 shrink-0 text-[var(--mint)]" />{localizeRecommendationReason(reason, locale, reasonT)}</p>
            ))}
            {recommendation.warnings.slice(0, 1).map((warning) => (
              <p key={warning} className="flex gap-2 text-xs leading-5 text-[var(--muted)]"><TriangleAlert size={14} className="mt-0.5 shrink-0 text-[var(--amber)]" />{localizeRecommendationReason(warning, locale, reasonT)}</p>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}

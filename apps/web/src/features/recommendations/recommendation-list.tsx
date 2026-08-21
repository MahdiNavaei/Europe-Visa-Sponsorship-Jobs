"use client";

import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { JobCard } from "@/components/cards/job-card";
import type { Recommendation } from "@/lib/types";
import { cn } from "@/lib/utils/cn";

export function RecommendationList({ recommendations, explanationHref }: { recommendations: Recommendation[]; explanationHref?: string }) {
  const locale = useLocale();
  const t = useTranslations("explanation");
  const gridClass = recommendations.length === 1
    ? "grid max-w-2xl gap-4"
    : recommendations.length === 2
      ? "grid gap-4 lg:grid-cols-2"
      : "grid gap-4 lg:grid-cols-3";

  return (
    <div>
      <div className={cn(gridClass)}>
        {recommendations.map((item) => <JobCard key={item.job_id} job={item.job} recommendation={item} />)}
      </div>
      {explanationHref && (
        <Link href={explanationHref} className="mt-5 inline-flex items-center gap-2 text-sm font-bold text-[var(--accent)]">
          {t("eyebrow")}
          <ArrowUpRight size={15} className={locale === "fa" ? "rotate-180" : ""} />
        </Link>
      )}
    </div>
  );
}

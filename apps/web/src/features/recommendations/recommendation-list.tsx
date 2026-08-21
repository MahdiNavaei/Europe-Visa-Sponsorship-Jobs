import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { useLocale } from "next-intl";
import type { Recommendation } from "@/lib/types";
import { JobCard } from "@/components/cards/job-card";

export function RecommendationList({ recommendations, explanationHref }: { recommendations: Recommendation[]; explanationHref?: string }) {
  const locale = useLocale();
  return <div><div className="grid gap-4 lg:grid-cols-3">{recommendations.map((item) => <JobCard key={item.job_id} job={item.job} recommendation={item} />)}</div>{explanationHref && <Link href={explanationHref} className="mt-5 inline-flex items-center gap-2 text-sm font-bold text-[var(--accent)]">See the full explanation <ArrowUpRight size={15} /></Link>}</div>;
}

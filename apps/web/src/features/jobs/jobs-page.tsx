"use client";

import { Filter, Search, SlidersHorizontal, X } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useMemo, useState } from "react";
import { JobCard } from "@/components/cards/job-card";
import { PageHeading } from "@/components/common/page-heading";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useCountries, useJobs } from "@/lib/api/hooks";
import type { JobFamily } from "@/lib/types";
import { labelize } from "@/lib/utils/format";

const categories: JobFamily[] = ["ai_ml", "backend", "frontend", "data_science", "data_engineering", "devops_cloud", "software_engineering"];

export function JobsPage() {
  const locale = useLocale();
  const t = useTranslations("jobs");
  const c = useTranslations("common");
  const [query, setQuery] = useState("");
  const [country, setCountry] = useState("");
  const [category, setCategory] = useState("");
  const [visa, setVisa] = useState<"" | "eligible" | "unknown">("");
  const [minScore, setMinScore] = useState("");
  const params = useMemo(() => { const value = new URLSearchParams({ limit: "500", offset: "0" }); if (country) value.set("country", country); if (category) value.set("category", category); if (visa) value.set("visa_status", visa); return value; }, [category, country, visa]);
  const { data: jobs, isLoading, isError, refetch } = useJobs(params);
  const { data: countries } = useCountries();
  const filtered = useMemo(() => jobs?.filter((job) => { const text = `${job.title} ${job.company_name} ${job.description} ${job.required_skills.join(" ")}`.toLowerCase(); const matchesText = !query || text.includes(query.toLowerCase()); const matchesScore = !minScore || (job.eligibility_score ?? 0) >= Number(minScore); return matchesText && matchesScore; }) ?? [], [jobs, minScore, query]);
  const reset = () => { setQuery(""); setCountry(""); setCategory(""); setVisa(""); setMinScore(""); };
  return <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:px-10 lg:py-14"><PageHeading eyebrow="Opportunity index" title={t("title")} description={t("subtitle")} action={<Badge tone="accent"><Filter size={13} />{filtered.length} {t("results")}</Badge>} /><div className="mt-10 grid gap-6 lg:grid-cols-[270px_1fr]"><aside className="h-fit rounded-3xl border border-[var(--line)] bg-[var(--card)] p-5 lg:sticky lg:top-24"><div className="flex items-center justify-between"><div className="flex items-center gap-2 text-sm font-black text-[var(--ink)]"><SlidersHorizontal size={16} className="text-[var(--accent)]" />{t("search")}</div><button className="focus-ring text-xs font-bold text-[var(--accent)]" onClick={reset}>{t("reset")}</button></div><div className="mt-5 space-y-4"><label className="block"><span className="mb-2 block text-xs font-bold text-[var(--muted)]">{t("query")}</span><div className="relative"><Search size={16} className="absolute start-3 top-3 text-[var(--muted)]" /><Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("query")} className="ps-9" /></div></label><label className="block"><span className="mb-2 block text-xs font-bold text-[var(--muted)]">{t("country")}</span><Select value={country} onChange={(event) => setCountry(event.target.value)}><option value="">{t("all")}</option>{(countries?.countries ?? ["Germany", "Netherlands", "Sweden", "Denmark", "Ireland", "Finland", "United Kingdom"]).map((item) => <option key={item} value={item}>{item}</option>)}</Select></label><label className="block"><span className="mb-2 block text-xs font-bold text-[var(--muted)]">{t("category")}</span><Select value={category} onChange={(event) => setCategory(event.target.value)}><option value="">{t("all")}</option>{categories.map((item) => <option key={item} value={item}>{labelize(item)}</option>)}</Select></label><label className="block"><span className="mb-2 block text-xs font-bold text-[var(--muted)]">{t("visa")}</span><Select value={visa} onChange={(event) => setVisa(event.target.value as typeof visa)}><option value="">{t("all")}</option><option value="eligible">{c("eligible")}</option><option value="unknown">{c("unknown")}</option></Select></label><label className="block"><span className="mb-2 block text-xs font-bold text-[var(--muted)]">Match score</span><Select value={minScore} onChange={(event) => setMinScore(event.target.value)}><option value="">Any score</option><option value="70">70%+</option><option value="80">80%+</option><option value="90">90%+</option></Select></label></div></aside><section aria-live="polite">{isLoading ? <div className="grid gap-4 xl:grid-cols-2"><Skeleton className="h-72" /><Skeleton className="h-72" /><Skeleton className="h-72" /><Skeleton className="h-72" /></div> : isError ? <EmptyState title={c("unavailable")} body="Start the FastAPI service at http://localhost:8000, then try again." action={c("tryAgain")} onAction={() => void refetch()} /> : filtered.length === 0 ? <EmptyState title={c("noResults")} body="Try widening the country, category or score filters." action={t("reset")} onAction={reset} /> : <div className="grid gap-4 xl:grid-cols-2">{filtered.map((job) => <JobCard key={job.id} job={job} />)}</div>}{filtered.length > 0 && <div className="mt-6 flex items-center justify-between rounded-2xl border border-[var(--line)] bg-[var(--card)] px-4 py-3 text-xs text-[var(--muted)]"><span>Showing {filtered.length} {t("results")}</span>{(query || country || category || visa || minScore) && <button className="focus-ring flex items-center gap-1 font-bold text-[var(--accent)]" onClick={reset}><X size={13} />{t("reset")}</button>}</div>}</section></div></div>;
}

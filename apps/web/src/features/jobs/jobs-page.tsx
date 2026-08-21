"use client";

import { Filter, Search, SlidersHorizontal, X } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { JobCard } from "@/components/cards/job-card";
import { PageHeading } from "@/components/common/page-heading";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useCountries, useJobsPage, useRecommendationsPage } from "@/lib/api/hooks";
import type { JobFamily } from "@/lib/types";
import { useCandidateId } from "@/lib/utils/candidate";
import { formatCountry, formatJobFamily, formatNumber, formatScore } from "@/lib/utils/format";

const categories: JobFamily[] = ["ai_ml", "backend", "frontend", "data_science", "data_engineering", "devops_cloud", "software_engineering"];
const PAGE_SIZE = 20;

export function JobsPage() {
  const locale = useLocale();
  const t = useTranslations("jobs");
  const c = useTranslations("common");
  const candidateId = useCandidateId();
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query);
  const [country, setCountry] = useState("");
  const [category, setCategory] = useState("");
  const [sponsorship, setSponsorship] = useState<"" | "unknown">("");
  const [minScore, setMinScore] = useState("");
  const [sort, setSort] = useState<"match" | "newest" | "visa">("match");
  const [page, setPage] = useState(1);
  useEffect(() => { if (!candidateId && sort === "match") setSort("newest"); }, [candidateId, sort]);
  useEffect(() => setPage(1), [deferredQuery, country, category, sponsorship, minScore, sort, candidateId]);
  const offset = (page - 1) * PAGE_SIZE;
  const genericParams = useMemo(() => {
    const value = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset), sort: sort === "visa" ? "visa" : "newest" });
    if (country) value.set("country", country);
    if (category) value.set("category", category);
    if (sponsorship === "unknown") value.set("visa_status", "unknown");
    if (deferredQuery.trim()) value.set("query", deferredQuery.trim());
    if (minScore) value.set("min_visa_score", minScore);
    return value;
  }, [category, country, deferredQuery, minScore, offset, sort, sponsorship]);
  const recommendationParams = useMemo(() => {
    const value = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset), sort });
    if (country) value.set("country", country);
    if (category) value.set("role", category);
    if (sponsorship === "unknown") value.set("include_unknown", "true");
    if (deferredQuery.trim()) value.set("query", deferredQuery.trim());
    if (minScore) value.set("min_score", minScore);
    return value;
  }, [category, country, deferredQuery, minScore, offset, sort, sponsorship]);
  const generic = useJobsPage(genericParams, candidateId === null);
  const personalized = useRecommendationsPage(candidateId, recommendationParams);
  const { data: countries } = useCountries();
  const active = candidateId ? personalized : generic;
  const total = active.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  useEffect(() => { if (page > totalPages) setPage(totalPages); }, [page, totalPages]);
  const reset = () => { setQuery(""); setCountry(""); setCategory(""); setSponsorship(""); setMinScore(""); setSort(candidateId ? "match" : "newest"); setPage(1); };
  const items = candidateId ? personalized.data?.items ?? [] : generic.data?.items ?? [];
  const sortLabel = locale === "fa" ? "مرتب‌سازی" : "Sort";
  const sortMatch = locale === "fa" ? "بهترین تطابق" : "Best match";
  const sortNewest = locale === "fa" ? "جدیدترین" : "Newest";
  const sortVisa = locale === "fa" ? "بالاترین امتیاز ویزا" : "Highest visa score";
  return <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:px-10 lg:py-14"><PageHeading eyebrow={t("eyebrow")} title={t("title")} description={t("subtitle")} action={<div className="flex flex-wrap items-center gap-2"><Badge tone={candidateId ? "accent" : "neutral"}>{candidateId ? t("personalized") : t("generic")}</Badge><Badge tone="accent"><Filter size={13} />{formatNumber(total, locale)} {t("results")}</Badge></div>} /><div className="mt-4 text-xs text-[var(--muted)]">{!candidateId && t("buildForMatch")}</div><div className="mt-8 grid gap-6 lg:grid-cols-[270px_1fr]"><aside className="h-fit rounded-3xl border border-[var(--line)] bg-[var(--card)] p-5 lg:sticky lg:top-24"><div className="flex items-center justify-between"><div className="flex items-center gap-2 text-sm font-black text-[var(--ink)]"><SlidersHorizontal size={16} className="text-[var(--accent)]" />{t("search")}</div><button className="focus-ring text-xs font-bold text-[var(--accent)]" onClick={reset}>{t("reset")}</button></div><div className="mt-5 space-y-4"><label className="block"><span className="mb-2 block text-xs font-bold text-[var(--muted)]">{t("query")}</span><div className="relative"><Search size={16} className="absolute start-3 top-3 text-[var(--muted)]" /><Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("query")} className="ps-9" /></div></label><label className="block"><span className="mb-2 block text-xs font-bold text-[var(--muted)]">{t("country")}</span><Select aria-label={t("country")} value={country} onChange={(event) => setCountry(event.target.value)}><option value="">{t("all")}</option>{(countries?.countries ?? ["Germany", "Netherlands", "Sweden", "Denmark", "Ireland", "Finland", "United Kingdom"]).map((item) => <option key={item} value={item}>{formatCountry(item, locale)}</option>)}</Select></label><label className="block"><span className="mb-2 block text-xs font-bold text-[var(--muted)]">{t("category")}</span><Select aria-label={t("category")} value={category} onChange={(event) => setCategory(event.target.value)}><option value="">{t("all")}</option>{categories.map((item) => <option key={item} value={item}>{formatJobFamily(item, locale)}</option>)}</Select></label><label className="block"><span className="mb-2 block text-xs font-bold text-[var(--muted)]">{t("sponsorship")}</span><Select aria-label={t("sponsorship")} value={sponsorship} onChange={(event) => setSponsorship(event.target.value as typeof sponsorship)}><option value="">{t("eligibleOnly")}</option><option value="unknown">{candidateId ? t("includeUnknown") : c("unknown")}</option></Select></label><label className="block"><span className="mb-2 block text-xs font-bold text-[var(--muted)]">{candidateId ? t("matchScore") : t("visaScore")}</span><Select aria-label={candidateId ? t("matchScore") : t("visaScore")} value={minScore} onChange={(event) => setMinScore(event.target.value)}><option value="">{t("anyScore")}</option>{[70, 80, 90].map((value) => <option key={value} value={value}>{formatScore(value, locale)}+</option>)}</Select></label><label className="block"><span className="mb-2 block text-xs font-bold text-[var(--muted)]">{sortLabel}</span><Select aria-label={sortLabel} value={sort} onChange={(event) => setSort(event.target.value as typeof sort)}>{candidateId && <option value="match">{sortMatch}</option>}<option value="newest">{sortNewest}</option><option value="visa">{sortVisa}</option></Select></label></div></aside><section aria-live="polite">{active.isLoading ? <div className="grid gap-4 xl:grid-cols-2"><Skeleton className="h-72" /><Skeleton className="h-72" /><Skeleton className="h-72" /><Skeleton className="h-72" /></div> : active.isError ? <EmptyState title={c("unavailable")} body={t("apiError")} action={c("tryAgain")} onAction={() => void active.refetch()} /> : items.length === 0 ? <EmptyState title={c("noResults")} body={t("widen")} action={t("reset")} onAction={reset} /> : <div className="grid gap-4 xl:grid-cols-2">{candidateId ? personalized.data?.items.map((item) => <JobCard key={item.job_id} job={item.job} recommendation={item} />) : generic.data?.items.map((job) => <JobCard key={job.id} job={job} />)}</div>}{total > 0 && <div className="mt-6 flex flex-col items-center justify-between gap-3 rounded-2xl border border-[var(--line)] bg-[var(--card)] px-4 py-3 text-xs text-[var(--muted)] sm:flex-row"><span>{t("showing")} {formatNumber(Math.min(offset + 1, total), locale)}–{formatNumber(Math.min(offset + PAGE_SIZE, total), locale)} / {formatNumber(total, locale)}</span><div className="flex items-center gap-2"><Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>{locale === "fa" ? "→" : "←"}</Button><span className="min-w-20 text-center font-bold text-[var(--ink)]">{formatNumber(page, locale)} / {formatNumber(totalPages, locale)}</span><Button variant="secondary" size="sm" disabled={page >= totalPages} onClick={() => setPage((value) => Math.min(totalPages, value + 1))}>{locale === "fa" ? "←" : "→"}</Button></div>{(query || country || category || sponsorship || minScore) && <button className="focus-ring flex items-center gap-1 font-bold text-[var(--accent)]" onClick={reset}><X size={13} />{t("reset")}</button>}</div>}</section></div></div>;
}

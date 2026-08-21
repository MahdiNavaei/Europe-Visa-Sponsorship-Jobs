"use client";

import { BookmarkCheck, ExternalLink, Trash2 } from "lucide-react";
import Link from "next/link";
import { useLocale } from "next-intl";
import { PageHeading } from "@/components/common/page-heading";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useDeleteJobState, useJobStates, useUpdateJobState } from "@/lib/api/hooks";
import type { ApplicationStatus, CandidateJobState } from "@/lib/types";
import { useCandidateId } from "@/lib/utils/candidate";
import { formatCountry, formatDate } from "@/lib/utils/format";

const statuses: ApplicationStatus[] = ["not_applied", "applied", "interview", "offer", "rejected", "withdrawn"];
const statusLabels = {
  en: { not_applied: "Not applied", applied: "Applied", interview: "Interview", offer: "Offer", rejected: "Rejected", withdrawn: "Withdrawn" },
  fa: { not_applied: "هنوز اقدام نشده", applied: "ارسال درخواست", interview: "مصاحبه", offer: "پیشنهاد همکاری", rejected: "رد شده", withdrawn: "انصراف" },
} as const;

export function ApplicationsPage() {
  const locale = useLocale() as "en" | "fa";
  const candidateId = useCandidateId();
  const { data, isLoading, isError, refetch } = useJobStates(candidateId);
  const update = useUpdateJobState();
  const remove = useDeleteJobState();
  const copy = locale === "fa" ? {
    eyebrow: "پیگیری مسیر درخواست",
    title: "فرصت‌های ذخیره‌شده و درخواست‌ها",
    description: "فرصت‌هایی را که ارزش پیگیری دارند کنار هم نگه دارید و وضعیت هر درخواست را ثبت کنید.",
    build: "ابتدا پروفایل بسازید",
    buildBody: "برای ذخیره فرصت و پیگیری درخواست‌ها به یک پروفایل نیاز دارید.",
    empty: "هنوز فرصتی ذخیره نشده",
    emptyBody: "از صفحه هر فرصت می‌توانید آن را ذخیره کنید یا وضعیت درخواست را تغییر دهید.",
    unavailable: "اطلاعات پیگیری در دسترس نیست.",
    saved: "ذخیره‌شده",
    remove: "حذف از پیگیری",
    details: "جزئیات فرصت",
  } : {
    eyebrow: "Application pipeline",
    title: "Saved jobs and applications",
    description: "Keep promising opportunities together and record where each application stands.",
    build: "Build your profile first",
    buildBody: "A candidate profile is required to save jobs and track applications.",
    empty: "Nothing saved yet",
    emptyBody: "Save a role or update its application status from the job detail page.",
    unavailable: "Application tracking is unavailable.",
    saved: "Saved",
    remove: "Remove from tracking",
    details: "Job details",
  };
  if (!candidateId) return <div className="mx-auto max-w-2xl px-5 py-20"><EmptyState title={copy.build} body={copy.buildBody} /></div>;
  return <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:px-10 lg:py-14"><PageHeading eyebrow={copy.eyebrow} title={copy.title} description={copy.description} /><div className="mt-10">{isLoading ? <div className="space-y-4"><Skeleton className="h-36" /><Skeleton className="h-36" /></div> : isError ? <EmptyState title={copy.unavailable} body={copy.unavailable} action={locale === "fa" ? "تلاش دوباره" : "Try again"} onAction={() => void refetch()} /> : !data?.length ? <EmptyState title={copy.empty} body={copy.emptyBody} /> : <div className="space-y-4">{data.map((state) => <TrackingCard key={state.id} state={state} locale={locale} copy={copy} onStatus={(application_status) => update.mutate({ candidateId, jobId: state.job_id, input: { saved: state.saved, application_status, note: state.note } })} onRemove={() => remove.mutate({ candidateId, jobId: state.job_id })} />)}</div>}</div></div>;
}

function TrackingCard({ state, locale, copy, onStatus, onRemove }: { state: CandidateJobState; locale: "en" | "fa"; copy: { saved: string; remove: string; details: string }; onStatus: (status: ApplicationStatus) => void; onRemove: () => void }) {
  return <Card className="p-5 sm:p-6"><div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-center"><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><Badge tone="accent"><BookmarkCheck size={12} />{copy.saved}</Badge><Badge>{statusLabels[locale][state.application_status]}</Badge></div><h2 className="mt-3 text-xl font-black text-[var(--ink)]">{state.job.title}</h2><p className="mt-1 text-sm text-[var(--muted)]">{state.job.company_name} · {formatCountry(state.job.country, locale)} · {formatDate(state.job.posted_at, locale)}</p></div><div className="flex flex-wrap items-center gap-2"><Select aria-label={locale === "fa" ? "وضعیت درخواست" : "Application status"} className="w-44" value={state.application_status} onChange={(event) => onStatus(event.target.value as ApplicationStatus)}>{statuses.map((status) => <option key={status} value={status}>{statusLabels[locale][status]}</option>)}</Select><Button asChild variant="secondary"><Link href={`/${locale}/jobs/${state.job_id}`}>{copy.details}<ExternalLink size={14} /></Link></Button><Button aria-label={copy.remove} variant="ghost" onClick={onRemove}><Trash2 size={15} /></Button></div></div></Card>;
}

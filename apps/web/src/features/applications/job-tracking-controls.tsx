"use client";

import { Bookmark, BookmarkCheck, LoaderCircle } from "lucide-react";
import Link from "next/link";
import { useLocale } from "next-intl";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { useJobState, useUpdateJobState } from "@/lib/api/hooks";
import type { ApplicationStatus } from "@/lib/types";

const statuses: ApplicationStatus[] = ["not_applied", "applied", "interview", "offer", "rejected", "withdrawn"];
const labels = {
  en: { not_applied: "Not applied", applied: "Applied", interview: "Interview", offer: "Offer", rejected: "Rejected", withdrawn: "Withdrawn" },
  fa: { not_applied: "هنوز اقدام نشده", applied: "ارسال درخواست", interview: "مصاحبه", offer: "پیشنهاد همکاری", rejected: "رد شده", withdrawn: "انصراف" },
} as const;

export function JobTrackingControls({ candidateId, jobId }: { candidateId: number | null; jobId: number }) {
  const locale = useLocale() as "en" | "fa";
  const { data: state, isLoading } = useJobState(candidateId, jobId);
  const update = useUpdateJobState();
  const copy = locale === "fa" ? {
    title: "پیگیری این فرصت",
    body: "این فرصت را ذخیره کنید و وضعیت درخواست خود را به‌روز نگه دارید.",
    save: "ذخیره فرصت",
    saved: "ذخیره‌شده",
    status: "وضعیت درخواست",
    build: "برای پیگیری، پروفایل بسازید",
  } : {
    title: "Track this opportunity",
    body: "Save this role and keep your application status up to date.",
    save: "Save job",
    saved: "Saved",
    status: "Application status",
    build: "Build a profile to track it",
  };
  if (!candidateId) return <Card><CardHeader><CardTitle>{copy.title}</CardTitle></CardHeader><CardContent><p className="text-sm leading-6 text-[var(--muted)]">{copy.body}</p><Button asChild variant="secondary" className="mt-4"><Link href={`/${locale}/onboarding`}>{copy.build}</Link></Button></CardContent></Card>;
  if (isLoading) return <Card className="p-6"><LoaderCircle size={18} className="animate-spin text-[var(--accent)]" /></Card>;
  const status = state?.application_status ?? "not_applied";
  const save = () => update.mutate({ candidateId, jobId, input: { saved: !state?.saved, application_status: status, note: state?.note } });
  const setStatus = (application_status: ApplicationStatus) => update.mutate({ candidateId, jobId, input: { saved: true, application_status, note: state?.note } });
  return <Card><CardHeader><div><CardTitle>{copy.title}</CardTitle><p className="mt-1 text-xs text-[var(--muted)]">{copy.body}</p></div></CardHeader><CardContent><Button type="button" variant={state?.saved ? "soft" : "secondary"} className="w-full" disabled={update.isPending} onClick={save}>{state?.saved ? <BookmarkCheck size={16} /> : <Bookmark size={16} />}{state?.saved ? copy.saved : copy.save}</Button><label className="mt-4 block"><span className="mb-2 block text-xs font-bold text-[var(--muted)]">{copy.status}</span><Select aria-label={copy.status} value={status} disabled={update.isPending} onChange={(event) => setStatus(event.target.value as ApplicationStatus)}>{statuses.map((item) => <option key={item} value={item}>{labels[locale][item]}</option>)}</Select></label></CardContent></Card>;
}

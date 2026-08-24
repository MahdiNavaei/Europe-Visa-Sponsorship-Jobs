"use client";

import { Download, Languages, Moon, ShieldCheck, Sun, Trash2 } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { usePathname, useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { PageHeading } from "@/components/common/page-heading";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useDeleteCandidate, useExportCandidate } from "@/lib/api/hooks";
import { clearCandidateId, useCandidateId } from "@/lib/utils/candidate";

export function SettingsPage() {
  const locale = useLocale();
  const c = useTranslations("common");
  const t = useTranslations("settings");
  const router = useRouter();
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const candidateId = useCandidateId();
  const exportProfile = useExportCandidate();
  const deleteProfile = useDeleteCandidate();
  const switchLocale = (next: "en" | "fa") => router.push(pathname.replace(/^\/(en|fa)/, `/${next}`));
  const downloadProfile = async () => {
    if (!candidateId) return;
    const data = await exportProfile.mutateAsync(candidateId);
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "career-radar-profile.json";
    anchor.click();
    URL.revokeObjectURL(url);
  };
  const eraseProfile = async () => {
    if (!candidateId || !window.confirm(t("deleteConfirm"))) return;
    await deleteProfile.mutateAsync(candidateId);
    clearCandidateId();
    router.push(`/${locale}/onboarding`);
  };
  return <div className="mx-auto max-w-4xl px-5 py-10 sm:px-8 lg:px-10 lg:py-14"><PageHeading eyebrow={t("eyebrow")} title={c("settings")} description={t("description")} /><div className="mt-10 space-y-5"><Card><CardHeader><CardTitle>{t("appearance")}</CardTitle></CardHeader><CardContent><div className="flex flex-wrap gap-3"><Button variant={theme === "light" ? "soft" : "secondary"} onClick={() => setTheme("light")}><Sun size={16} />{t("light")}</Button><Button variant={theme === "dark" ? "soft" : "secondary"} onClick={() => setTheme("dark")}><Moon size={16} />{t("dark")}</Button><Button variant={theme === "system" ? "soft" : "secondary"} onClick={() => setTheme("system")}>{t("system")}</Button></div></CardContent></Card><Card><CardHeader><CardTitle>{t("language")}</CardTitle></CardHeader><CardContent><div className="flex flex-wrap gap-3"><Button variant={locale === "en" ? "soft" : "secondary"} onClick={() => switchLocale("en")}><Languages size={16} />English · LTR</Button><Button variant={locale === "fa" ? "soft" : "secondary"} onClick={() => switchLocale("fa")}><Languages size={16} />فارسی · RTL</Button></div></CardContent></Card><Card><CardHeader><CardTitle>{t("trust")}</CardTitle></CardHeader><CardContent><p className="flex gap-3 text-sm leading-7 text-[var(--muted)]"><ShieldCheck className="mt-1 shrink-0 text-[var(--mint)]" size={17} />{t("trustBody")}</p>{candidateId && <div className="mt-5 flex flex-wrap gap-3"><Button variant="secondary" disabled={exportProfile.isPending} onClick={() => void downloadProfile()}><Download size={16} />{t("export")}</Button><Button variant="secondary" disabled={deleteProfile.isPending} onClick={() => void eraseProfile()}><Trash2 size={16} />{t("delete")}</Button></div>}</CardContent></Card></div></div>;
}

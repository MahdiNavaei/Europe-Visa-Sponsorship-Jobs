"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { AnimatePresence, motion } from "framer-motion";
import { BriefcaseBusiness, Building2, ChevronDown, Compass, Languages, Menu, Moon, Settings, Sparkles, Sun, UserRound, X } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import type { Locale } from "@/lib/i18n/messages";
import { cn } from "@/lib/utils/cn";

const links = [
  { href: "/dashboard", key: "dashboard", icon: Compass },
  { href: "/jobs", key: "jobs", icon: BriefcaseBusiness },
  { href: "/companies", key: "companies", icon: Building2 },
  { href: "/profile", key: "profile", icon: UserRound },
] as const;

function ThemeToggle() {
  const { setTheme } = useTheme();
  const [isDark, setIsDark] = useState(false);
  const toggle = () => { const nextDark = !document.documentElement.classList.contains("dark"); const nextTheme = nextDark ? "dark" : "light"; setTheme(nextTheme); window.localStorage.setItem("theme", nextTheme); setIsDark(nextDark); window.setTimeout(() => document.documentElement.classList.toggle("dark", nextDark), 0); };
  return <button aria-label="Toggle theme" className="focus-ring rounded-xl p-2.5 text-[var(--muted)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent)]" onClick={toggle} title="Toggle theme">{isDark ? <Sun size={17} /> : <Moon size={17} />}</button>;
}

function LanguageToggle({ locale }: { locale: Locale }) {
  const router = useRouter();
  const pathname = usePathname();
  const nextLocale = locale === "en" ? "fa" : "en";
  const nextPath = pathname.replace(/^\/(en|fa)/, `/${nextLocale}`) || `/${nextLocale}`;
  return <button aria-label="Switch language" className="focus-ring hidden items-center gap-2 rounded-xl px-3 py-2 text-xs font-bold text-[var(--muted)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent)] sm:flex" onClick={() => router.push(nextPath)}><Languages size={15} />{locale === "en" ? "فارسی" : "English"}</button>;
}

function Sidebar({ locale, mobile = false, onNavigate }: { locale: Locale; mobile?: boolean; onNavigate?: () => void }) {
  const t = useTranslations("common");
  const pathname = usePathname();
  return <nav className={cn("flex flex-col", mobile ? "p-5" : "sticky top-0 h-screen border-e border-[var(--line)] px-4 py-6")} aria-label="Primary navigation">
    <div className="mb-10 flex items-center gap-3 px-2"><div className="grid size-9 place-items-center rounded-xl bg-[var(--accent)] text-white shadow-[0_8px_20px_rgba(91,92,226,.25)]"><Sparkles size={17} /></div><div><p className="text-sm font-black tracking-[-.03em] text-[var(--ink)]">{t("product")}</p><p className="text-[10px] font-medium text-[var(--muted)]">{t("tagline")}</p></div></div>
    <div className="space-y-1">
      {links.map(({ href, key, icon: Icon }) => {
        const target = `/${locale}${href}`;
        const active = pathname === target || pathname.startsWith(`${target}/`);
        return <a key={key} href={target} onClick={onNavigate} className={cn("focus-ring flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold transition", active ? "bg-[var(--accent-soft)] text-[var(--accent-strong)]" : "text-[var(--muted)] hover:bg-[var(--line)]/50 hover:text-[var(--ink)]")}><Icon size={17} strokeWidth={active ? 2.4 : 1.8} />{t(key)}</a>;
      })}
    </div>
    <div className="mt-auto space-y-1"><a href={`/${locale}/onboarding`} onClick={onNavigate} className="focus-ring flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold text-[var(--muted)] transition hover:bg-[var(--line)]/50 hover:text-[var(--ink)]"><Sparkles size={17} />{t("onboarding")}</a><a href={`/${locale}/settings`} onClick={onNavigate} className="focus-ring flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold text-[var(--muted)] transition hover:bg-[var(--line)]/50 hover:text-[var(--ink)]"><Settings size={17} />{t("settings")}</a></div>
  </nav>;
}

export function AppShell({ locale, children }: { locale: Locale; children: React.ReactNode }) {
  const t = useTranslations("common");
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  if (pathname === `/${locale}`) return <div className="min-h-screen"><header className="absolute inset-x-0 top-0 z-20"><div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-5 sm:px-8 lg:px-10"><div className="flex items-center gap-3"><div className="grid size-9 place-items-center rounded-xl bg-[var(--accent)] text-white"><Sparkles size={17} /></div><span className="text-sm font-black tracking-[-.03em] text-[var(--ink)]">{t("product")}</span></div><div className="flex items-center gap-1"><LanguageToggle locale={locale} /><ThemeToggle /><Button asChild variant="soft" size="sm" className="ms-2 hidden sm:inline-flex"><a href={`/${locale}/dashboard`}>{t("dashboard")}</a></Button></div></div></header><main>{children}</main></div>;
  return <div className="min-h-screen bg-[var(--paper)]"><aside className="fixed inset-y-0 start-0 z-30 hidden w-64 bg-[var(--paper)] lg:block"><Sidebar locale={locale} /></aside><Dialog.Root open={open} onOpenChange={setOpen}><Dialog.Trigger asChild><button aria-label="Open navigation" className="focus-ring fixed start-4 top-4 z-40 rounded-xl border border-[var(--line)] bg-[var(--card)] p-2.5 text-[var(--ink)] shadow-sm lg:hidden"><Menu size={19} /></button></Dialog.Trigger><Dialog.Portal><AnimatePresence>{open && <Dialog.Overlay asChild forceMount><motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-40 bg-black/35" /></Dialog.Overlay>} {open && <Dialog.Content asChild forceMount><motion.aside initial={{ x: locale === "fa" ? "100%" : "-100%" }} animate={{ x: 0 }} exit={{ x: locale === "fa" ? "100%" : "-100%" }} className="fixed inset-y-0 start-0 z-50 w-72 bg-[var(--paper)] shadow-2xl"><Dialog.Close asChild><button aria-label="Close navigation" className="focus-ring absolute end-4 top-4 rounded-xl p-2 text-[var(--muted)]"><X size={18} /></button></Dialog.Close><Sidebar locale={locale} mobile onNavigate={() => setOpen(false)} /></motion.aside></Dialog.Content>}</AnimatePresence></Dialog.Portal></Dialog.Root><div className="lg:ps-64"><header className="sticky top-0 z-20 border-b border-[var(--line)] bg-[var(--paper)]/85 backdrop-blur-xl"><div className="flex h-[72px] items-center justify-between gap-4 px-5 sm:px-8"><div className="flex items-center gap-3 lg:hidden"><div className="ms-12 grid size-8 place-items-center rounded-lg bg-[var(--accent)] text-white"><Sparkles size={15} /></div><span className="text-sm font-black text-[var(--ink)]">{t("product")}</span></div><div className="hidden lg:block" /><div className="flex items-center gap-1"><LanguageToggle locale={locale} /><ThemeToggle /><div className="ms-2 hidden items-center gap-2 border-s border-[var(--line)] ps-3 sm:flex"><div className="grid size-8 place-items-center rounded-full bg-[var(--accent-soft)] text-xs font-black text-[var(--accent-strong)]">CR</div><ChevronDown size={14} className="text-[var(--muted)]" /></div></div></div></header><main className="min-h-[calc(100vh-72px)]">{children}</main></div></div>;
}

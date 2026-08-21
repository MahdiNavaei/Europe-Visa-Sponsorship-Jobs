"use client";

import { Languages, Moon, ShieldCheck, Sun } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { usePathname, useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { PageHeading } from "@/components/common/page-heading";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function SettingsPage() {
  const locale = useLocale();
  const c = useTranslations("common");
  const router = useRouter();
  const pathname = usePathname();
  const { resolvedTheme, setTheme } = useTheme();
  const switchLocale = (next: "en" | "fa") => router.push(pathname.replace(/^\/(en|fa)/, `/${next}`));
  return <div className="mx-auto max-w-4xl px-5 py-10 sm:px-8 lg:px-10 lg:py-14"><PageHeading eyebrow="Workspace" title={c("settings")} description="Tune the way Career Radar feels and reads." /><div className="mt-10 space-y-5"><Card><CardHeader><CardTitle>Appearance</CardTitle></CardHeader><CardContent><div className="flex flex-wrap gap-3"><Button variant={resolvedTheme === "light" ? "soft" : "secondary"} onClick={() => setTheme("light")}><Sun size={16} />Light</Button><Button variant={resolvedTheme === "dark" ? "soft" : "secondary"} onClick={() => setTheme("dark")}><Moon size={16} />Dark</Button><Button variant={resolvedTheme === "system" ? "soft" : "secondary"} onClick={() => setTheme("system")}>System</Button></div></CardContent></Card><Card><CardHeader><CardTitle>Language and direction</CardTitle></CardHeader><CardContent><div className="flex flex-wrap gap-3"><Button variant={locale === "en" ? "soft" : "secondary"} onClick={() => switchLocale("en")}><Languages size={16} />English · LTR</Button><Button variant={locale === "fa" ? "soft" : "secondary"} onClick={() => switchLocale("fa")}><Languages size={16} />فارسی · RTL</Button></div></CardContent></Card><Card><CardHeader><CardTitle>Trust and privacy</CardTitle></CardHeader><CardContent><p className="flex gap-3 text-sm leading-7 text-[var(--muted)]"><ShieldCheck className="mt-1 shrink-0 text-[var(--mint)]" size={17} />Your candidate identifier is stored locally in this browser. Career Radar does not add an LLM or external AI service to the matching flow.</p></CardContent></Card></div></div>;
}

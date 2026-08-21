"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useLocale, useTranslations } from "next-intl";
import type { RecommendationScores } from "@/lib/types";
import { formatScore } from "@/lib/utils/format";

export function ScoreBreakdown({ scores }: { scores: RecommendationScores }) {
  const locale = useLocale();
  const t = useTranslations("scores");
  const data = [
    { label: t("visa"), score: scores.visa },
    { label: t("skill"), score: scores.skill },
    { label: t("experience"), score: scores.experience },
    { label: t("country"), score: scores.country },
    { label: t("company"), score: scores.company },
  ];
  return <div className="h-64 w-full" dir={locale === "fa" ? "rtl" : "ltr"}><ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{ top: 10, right: 4, left: -24, bottom: 0 }}><CartesianGrid vertical={false} stroke="var(--line)" strokeDasharray="3 3" /><XAxis dataKey="label" reversed={locale === "fa"} axisLine={false} tickLine={false} tick={{ fill: "var(--muted)", fontSize: 10 }} /><YAxis orientation={locale === "fa" ? "right" : "left"} domain={[0, 100]} axisLine={false} tickLine={false} tick={{ fill: "var(--muted)", fontSize: 10 }} /><Tooltip cursor={{ fill: "var(--accent-soft)" }} contentStyle={{ borderRadius: 12, border: "1px solid var(--line)", background: "var(--card)", color: "var(--ink)", fontSize: 12 }} formatter={(value) => [formatScore(Number(value), locale), t("score")]} /><Bar dataKey="score" fill="var(--accent)" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div>;
}

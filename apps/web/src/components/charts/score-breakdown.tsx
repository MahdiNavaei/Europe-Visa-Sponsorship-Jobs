"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { RecommendationScores } from "@/lib/types";

export function ScoreBreakdown({ scores }: { scores: RecommendationScores }) {
  const data = [{ label: "Visa", score: scores.visa }, { label: "Skills", score: scores.skill }, { label: "Experience", score: scores.experience }, { label: "Country", score: scores.country }, { label: "Company", score: scores.company }];
  return <div className="h-64 w-full"><ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{ top: 10, right: 4, left: -24, bottom: 0 }}><CartesianGrid vertical={false} stroke="var(--line)" strokeDasharray="3 3" /><XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fill: "var(--muted)", fontSize: 10 }} /><YAxis domain={[0, 100]} axisLine={false} tickLine={false} tick={{ fill: "var(--muted)", fontSize: 10 }} /><Tooltip cursor={{ fill: "var(--accent-soft)" }} contentStyle={{ borderRadius: 12, border: "1px solid var(--line)", background: "var(--card)", color: "var(--ink)", fontSize: 12 }} formatter={(value) => [`${value}%`, "Score"]} /><Bar dataKey="score" fill="var(--accent)" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div>;
}

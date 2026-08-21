import { cn } from "@/lib/utils/cn";

export function ScoreBar({ value, color = "accent" }: { value: number | null | undefined; color?: "accent" | "success" | "warning" }) {
  const colors = { accent: "bg-[var(--accent)]", success: "bg-[var(--mint)]", warning: "bg-[var(--amber)]" };
  return <div className="h-2 overflow-hidden rounded-full bg-[var(--line)]"><div className={cn("h-full rounded-full transition-all", colors[color])} style={{ width: `${Math.max(0, Math.min(100, value ?? 0))}%` }} /></div>;
}

export function ScoreBadge({ value, label = "Match", tone = "accent" }: { value: number | null | undefined; label?: string; tone?: "accent" | "success" | "warning" }) {
  const color = tone === "success" ? "text-[var(--mint)]" : tone === "warning" ? "text-[var(--amber)]" : "text-[var(--accent-strong)]";
  return <div className="text-end"><p className={cn("text-2xl font-black tracking-[-.06em]", color)}>{value === null || value === undefined ? "—" : `${Math.round(value)}%`}</p><p className="text-[10px] font-bold uppercase tracking-[.12em] text-[var(--muted)]">{label}</p></div>;
}

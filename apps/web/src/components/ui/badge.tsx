import { cn } from "@/lib/utils/cn";

export function Badge({ children, tone = "neutral", className }: { children: React.ReactNode; tone?: "neutral" | "success" | "warning" | "danger" | "accent"; className?: string }) {
  const tones = { neutral: "bg-[var(--line)]/60 text-[var(--muted)]", success: "bg-[var(--mint-soft)] text-[var(--mint)]", warning: "bg-[var(--amber-soft)] text-[var(--amber)]", danger: "bg-[var(--rose-soft)] text-[var(--rose)]", accent: "bg-[var(--accent-soft)] text-[var(--accent-strong)]" };
  return <span className={cn("inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-bold uppercase tracking-[.08em]", tones[tone], className)}>{children}</span>;
}

import type { LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/card";

export function StatCard({ label, value, detail, icon: Icon, tone = "accent" }: { label: string; value: string | number; detail: string; icon: LucideIcon; tone?: "accent" | "success" | "warning" | "neutral" }) {
  const colors = { accent: "bg-[var(--accent-soft)] text-[var(--accent)]", success: "bg-[var(--mint-soft)] text-[var(--mint)]", warning: "bg-[var(--amber-soft)] text-[var(--amber)]", neutral: "bg-[var(--line)]/60 text-[var(--muted)]" };
  return <Card className="p-5"><div className="flex items-start justify-between gap-3"><div><p className="text-xs font-semibold text-[var(--muted)]">{label}</p><p className="mt-3 text-3xl font-black tracking-[-.06em] text-[var(--ink)]">{value}</p><p className="mt-2 text-xs text-[var(--muted)]">{detail}</p></div><div className={`grid size-10 place-items-center rounded-xl ${colors[tone]}`}><Icon size={18} /></div></div></Card>;
}

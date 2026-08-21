import { SearchX } from "lucide-react";
import { Button } from "@/components/ui/button";

export function EmptyState({ title, body, action, onAction }: { title: string; body: string; action?: string; onAction?: () => void }) {
  return <div className="flex min-h-56 flex-col items-center justify-center rounded-3xl border border-dashed border-[var(--line)] bg-[var(--card)] p-8 text-center"><div className="mb-4 rounded-2xl bg-[var(--accent-soft)] p-3 text-[var(--accent)]"><SearchX size={20} /></div><h3 className="font-bold text-[var(--ink)]">{title}</h3><p className="mt-2 max-w-sm text-sm leading-6 text-[var(--muted)]">{body}</p>{action && <Button className="mt-5" variant="soft" size="sm" onClick={onAction}>{action}</Button>}</div>;
}

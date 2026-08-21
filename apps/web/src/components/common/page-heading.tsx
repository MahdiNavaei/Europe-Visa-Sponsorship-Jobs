import type { LucideIcon } from "lucide-react";

export function PageHeading({ eyebrow, title, description, icon: Icon, action }: { eyebrow?: string; title: string; description?: string; icon?: LucideIcon; action?: React.ReactNode }) {
  return <div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-end"><div>{eyebrow && <p className="text-xs font-bold uppercase tracking-[.16em] text-[var(--accent)]">{eyebrow}</p>}<div className="mt-2 flex items-center gap-3">{Icon && <div className="hidden size-11 place-items-center rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)] sm:grid"><Icon size={19} /></div>}<h1 className="display text-4xl font-black text-[var(--ink)] sm:text-5xl">{title}</h1></div>{description && <p className="mt-4 max-w-2xl text-sm leading-7 text-[var(--muted)] sm:text-base">{description}</p>}</div>{action}</div>;
}

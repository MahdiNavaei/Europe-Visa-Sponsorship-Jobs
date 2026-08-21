import { cn } from "@/lib/utils/cn";

export function Select({ className, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn("focus-ring h-11 w-full appearance-none rounded-xl border border-[var(--line)] bg-[var(--card)] px-3.5 text-sm text-[var(--ink)] outline-none focus:border-[var(--accent)]", className)} {...props} />;
}

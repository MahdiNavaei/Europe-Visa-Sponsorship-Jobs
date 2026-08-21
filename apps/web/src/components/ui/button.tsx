import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils/cn";

const buttonVariants = cva("focus-ring inline-flex items-center justify-center gap-2 rounded-xl text-sm font-semibold transition active:scale-[.98] disabled:pointer-events-none disabled:opacity-45", {
  variants: {
    variant: {
      primary: "bg-[var(--accent)] px-4 py-2.5 text-white shadow-[0_8px_20px_rgba(91,92,226,.22)] hover:bg-[var(--accent-strong)]",
      secondary: "border border-[var(--line)] bg-[var(--card)] px-4 py-2.5 text-[var(--ink)] hover:border-[var(--accent)] hover:text-[var(--accent)]",
      ghost: "px-3 py-2 text-[var(--muted)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent-strong)]",
      soft: "bg-[var(--accent-soft)] px-4 py-2.5 text-[var(--accent-strong)] hover:brightness-95",
      danger: "bg-[var(--rose-soft)] px-4 py-2.5 text-[var(--rose)] hover:brightness-95",
    },
    size: { sm: "h-9", md: "h-11", lg: "h-13 px-5 text-base" },
  },
  defaultVariants: { variant: "primary", size: "md" },
});

export function Button({ className, variant, size, asChild = false, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : "button";
  return <Comp className={cn(buttonVariants({ variant, size, className }))} {...props} />;
}

export { buttonVariants };

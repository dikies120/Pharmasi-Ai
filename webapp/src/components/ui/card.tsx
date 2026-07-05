import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils/cn";

type CardProps = HTMLAttributes<HTMLDivElement>;

export function Card({ className, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-surface-border bg-surface p-6 shadow-sm",
        className,
      )}
      {...props}
    />
  );
}

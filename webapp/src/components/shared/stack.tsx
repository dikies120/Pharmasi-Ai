import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils/cn";

type StackGap = "sm" | "md" | "lg";

type StackProps = HTMLAttributes<HTMLDivElement> & {
  gap?: StackGap;
};

const gapClasses: Record<StackGap, string> = {
  sm: "gap-3",
  md: "gap-5",
  lg: "gap-8",
};

export function Stack({ gap = "md", className, ...props }: StackProps) {
  return (
    <div className={cn("flex flex-col", gapClasses[gap], className)} {...props} />
  );
}

"use client";

import { cn } from "@/lib/utils";

/** Shared left-column width — matches DatahashLogoMark size="sm" (h-7 w-7). */
export const AGENT_LEADING_CLASS = "h-7 w-7 shrink-0";

export function AgentRow({
  leading,
  children,
  className,
  bodyClassName,
}: {
  leading: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <div className={cn("flex max-w-[85%] items-start gap-3", className)}>
      <div className={cn(AGENT_LEADING_CLASS, "flex items-center justify-center")}>
        {leading}
      </div>
      <div className={cn("min-w-0 flex-1", bodyClassName)}>{children}</div>
    </div>
  );
}

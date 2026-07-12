"use client";

import { DatahashLogoMark } from "@/components/ui/datahash-logo-mark";
import { cn } from "@/lib/utils";

export function AgentTextBubble({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex max-w-[85%] items-start gap-3", className)}>
      <DatahashLogoMark size="sm" />
      <div className="min-w-0 flex-1 rounded-2xl border border-[var(--border)] bg-[var(--card)] px-5 py-4 text-sm text-[var(--foreground)] shadow-sm">
        {children}
      </div>
    </div>
  );
}

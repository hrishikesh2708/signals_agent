"use client";

import { AgentRow } from "./agent-row";
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
    <AgentRow
      className={className}
      leading={<DatahashLogoMark size="sm" />}
      bodyClassName="rounded-2xl border border-[var(--border)] bg-[var(--card)] px-5 py-4 text-sm text-[var(--foreground)] shadow-sm"
    >
      {children}
    </AgentRow>
  );
}

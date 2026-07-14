"use client";

import { AgentRow } from "./agent-row";
import type { StepCompleteMessage } from "@/lib/parse-agent-message";

export function StepCompleteCard({ data }: { data: StepCompleteMessage }) {
  return (
    <AgentRow leading={null} bodyClassName="px-5">
      <div className="flex items-start gap-2.5">
        <span className="mt-0.5 inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-blue-600 text-[9px] leading-none font-bold text-white">
          ✓
        </span>
        <div className="min-w-0 space-y-0.5">
          <p className="text-sm font-medium text-[var(--foreground)]">
            {data.message}
          </p>
          {data.detail && (
            <p className="text-xs text-[var(--muted-foreground)]">{data.detail}</p>
          )}
        </div>
      </div>
    </AgentRow>
  );
}

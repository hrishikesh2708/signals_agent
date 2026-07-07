"use client";

import type { StepCompleteMessage } from "@/lib/parse-agent-message";

export function StepCompleteCard({ data }: { data: StepCompleteMessage }) {
  return (
    <div className="flex max-w-[85%] items-start gap-2.5">
      <span className="mt-0.5 inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-green-600 text-[9px] leading-none font-bold text-white">
        ✓
      </span>

      <div className="space-y-0.5">
        <p className="text-sm font-medium text-[var(--foreground)]">
          {data.message}
        </p>
        {data.detail && (
          <p className="text-xs text-[var(--muted-foreground)]">{data.detail}</p>
        )}
      </div>
    </div>
  );
}

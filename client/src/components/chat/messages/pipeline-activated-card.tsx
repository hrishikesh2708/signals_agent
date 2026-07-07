"use client";

import { Card, CardContent } from "@/components/ui/card";
import type { PipelineActivatedMessage } from "@/lib/parse-agent-message";

export function PipelineActivatedCard({
  data,
}: {
  data: PipelineActivatedMessage;
}) {
  return (
    <Card className="w-full max-w-lg overflow-hidden border-[var(--border)] bg-[var(--card)] shadow-sm">
      <div className="flex">
        <div className="w-1 shrink-0 bg-green-500" />

        <CardContent className="flex-1 space-y-2 p-4">
          <div className="flex items-center gap-2">
            <span className="inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-green-600 text-[9px] leading-none font-bold text-white">
              ✓
            </span>
            <p className="text-sm font-semibold text-[var(--foreground)]">
              Pipeline activated
            </p>
          </div>

          {data.pipeline_name && (
            <p className="text-xs font-medium text-[var(--muted-foreground)]">
              {data.pipeline_name}
            </p>
          )}

          <div className="flex flex-wrap items-center gap-1.5 text-sm text-[var(--foreground)]">
            <span className="font-medium">
              {data.source_label} · {data.source_object}
            </span>
            <span className="text-[var(--muted-foreground)]">→</span>
            <span className="font-medium">{data.channels.join(", ")}</span>
          </div>

          <p className="text-xs text-[var(--muted-foreground)]">
            {data.mapped_fields} of {data.total_fields} fields mapped · live
          </p>
        </CardContent>
      </div>
    </Card>
  );
}

"use client";

import { Card, CardContent } from "@/components/ui/card";
import type { SchemaSummaryMessage } from "@/lib/parse-agent-message";

export function SchemaSummaryCard({ data }: { data: SchemaSummaryMessage }) {
  const shown = data.sample_fields?.slice(0, 6) ?? [];
  const overflow = (data.sample_fields?.length ?? 0) - shown.length;

  return (
    <Card className="w-full max-w-lg border-[var(--border)] bg-[var(--card)] shadow-sm">
      <CardContent className="space-y-3 p-4">
        <div>
          <p className="text-[10px] font-semibold tracking-widest text-[var(--muted-foreground)] uppercase">
            Schema discovered
          </p>
          <p className="mt-1 text-sm font-semibold text-[var(--foreground)]">
            {data.source_label} · {data.source_object}
          </p>
        </div>

        <div className="flex gap-6">
          <div>
            <p className="text-2xl font-bold text-[var(--foreground)] tabular-nums">
              {data.total_fields}
            </p>
            <p className="mt-0.5 text-[10px] font-medium tracking-wider text-[var(--muted-foreground)] uppercase">
              Total fields
            </p>
          </div>
          <div>
            <p className="text-2xl font-bold text-blue-600 tabular-nums dark:text-blue-400">
              {data.required_fields}
            </p>
            <p className="mt-0.5 text-[10px] font-medium tracking-wider text-[var(--muted-foreground)] uppercase">
              Required
            </p>
          </div>
        </div>

        {shown.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {shown.map((f) => (
              <span
                key={f}
                className="rounded-md border border-[var(--border)] bg-[var(--muted)] px-2 py-0.5 font-mono text-xs text-[var(--foreground)]"
              >
                {f}
              </span>
            ))}
            {overflow > 0 && (
              <span className="self-center text-xs text-[var(--muted-foreground)]">
                +{overflow} more
              </span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

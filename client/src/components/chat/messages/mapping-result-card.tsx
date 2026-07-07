"use client";

import { Card, CardContent } from "@/components/ui/card";
import type {
  MappingCompleteMessage,
  MappingField,
} from "@/lib/parse-agent-message";

export function MappingResultCard({ data }: { data: MappingCompleteMessage }) {
  const mappings: MappingField[] = data.mappings ?? [];
  const { total, auto_approved, human_reviewed } = data.stats;
  const channelLabel = data.channels?.length
    ? data.channels.join(", ")
    : "Canonical";
  const routeLabel = `${data.source_label} ${data.source_object} → ${channelLabel}`;

  return (
    <Card className="w-full max-w-lg border-[var(--border)] bg-[var(--card)] shadow-sm">
      <CardContent className="space-y-3 p-4">
        <div>
          <p className="text-[10px] font-semibold tracking-widest text-[var(--muted-foreground)] uppercase">
            {routeLabel}
          </p>
          <p className="mt-1 text-xs text-[var(--muted-foreground)]">
            {total} fields mapped
            {auto_approved > 0 && ` · ${auto_approved} auto-approved`}
            {human_reviewed > 0 && ` · ${human_reviewed} reviewed by you`}
          </p>
        </div>

        <div className="space-y-2">
          {mappings.map((m) => (
            <div key={m.source_field} className="flex items-center gap-2">
              <div className="min-w-0 flex-1 truncate rounded-xl border border-[var(--border)] bg-[var(--background)] px-4 py-2.5 text-sm text-[var(--foreground)]">
                {m.source_field}
              </div>

              <span className="shrink-0 text-sm text-[var(--muted-foreground)]">
                →
              </span>

              <div className="min-w-0 flex-1 truncate rounded-xl border border-[var(--border)] bg-[var(--background)] px-4 py-2.5 text-sm text-[var(--foreground)]">
                {m.destination_field ?? "—"}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

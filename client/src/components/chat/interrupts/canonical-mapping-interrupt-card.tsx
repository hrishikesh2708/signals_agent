"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { InterruptCardProps } from "@/components/chat/interrupts/interrupt-card-props";
import type {
  SelectOption,
  CanonicalMappingRow,
  ChannelConnectionStatus,
  MappingDestination,
  MappingReviewRow,
  UnresolvedField,
} from "@/lib/interrupt-types";
import { MappingStatusDot } from "@/components/chat/interrupts/mapping-status-dot";

export function CanonicalMappingInterruptCard({ payload, onApprove }: InterruptCardProps) {
  const rows = (payload.canonical_rows ?? []) as CanonicalMappingRow[];
  const sourceFields = (payload.source_fields ?? []) as string[];
  const infoText = payload.info_text;

  // Track user overrides: canonical_field → chosen source_field
  const [overrides, setOverrides] = useState<Record<string, string>>(() =>
    Object.fromEntries(rows.map((r) => [r.canonical_field, r.source_field ?? ""])),
  );

  const hasUnresolved = rows.some(
    (r) => r.status === "needs_input" || r.status === "missing",
  );

  function handleApprove() {
    const updatedRows = rows.map((r) => ({
      ...r,
      source_field: overrides[r.canonical_field] ?? r.source_field,
    }));
    onApprove({ approved: true, rows: updatedRows });
  }

  return (
    <Card className="border-[var(--border)] bg-[var(--card)]">
      <CardContent className="p-4 space-y-3">
        {/* Header label */}
        <p className="text-[10px] font-semibold tracking-widest text-[var(--muted-foreground)] uppercase">
          What Signals needs ← Your Salesforce field
        </p>

        {/* Rows */}
        <div className="space-y-2">
          {rows.map((row) => {
            const currentValue = overrides[row.canonical_field] ?? "";
            return (
              <div
                key={row.canonical_field}
                className="flex items-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2.5"
              >
                <MappingStatusDot status={row.status} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-[var(--foreground)] leading-tight">
                    {row.canonical_field}
                  </p>
                  {row.description && (
                    <p className={`text-xs mt-0.5 leading-tight ${
                      row.status === "needs_input" || row.status === "missing"
                        ? "text-amber-600 dark:text-amber-400"
                        : "text-[var(--muted-foreground)]"
                    }`}>
                      {row.description}
                    </p>
                  )}
                </div>
                <span className="text-[var(--muted-foreground)] text-xs shrink-0">←</span>

                {/* Source field — dropdown if options provided, read-only pill otherwise */}
                {sourceFields.length > 0 ? (
                  <select
                    value={currentValue}
                    onChange={(e) =>
                      setOverrides((prev) => ({ ...prev, [row.canonical_field]: e.target.value }))
                    }
                    className="w-44 shrink-0 h-8 rounded-md border border-[var(--border)] bg-[var(--background)] px-2 text-sm text-[var(--foreground)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)] cursor-pointer"
                  >
                    {!sourceFields.includes(currentValue) && currentValue && (
                      <option value={currentValue}>{currentValue}</option>
                    )}
                    {!currentValue && (
                      <option value="" disabled>Select field…</option>
                    )}
                    {sourceFields.map((f) => (
                      <option key={f} value={f}>{f}</option>
                    ))}
                  </select>
                ) : (
                  <div className="w-44 shrink-0 flex items-center h-8 px-2.5 rounded-md border border-[var(--border)] bg-[var(--card)] text-sm text-[var(--foreground)] truncate">
                    {currentValue || (
                      <span className="text-[var(--muted-foreground)] italic text-xs">not mapped</span>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Info bar */}
        {infoText && (
          <div className="rounded-lg border border-blue-200 dark:border-blue-800/60 bg-blue-500/5 px-3 py-2">
            <p className="text-xs text-blue-700 dark:text-blue-400 leading-relaxed">{infoText}</p>
          </div>
        )}

        {/* Single CTA */}
        <Button
          type="button"
          className="w-full"
          onClick={handleApprove}
        >
          {hasUnresolved ? "Continue" : "Looks good — continue"}
        </Button>
      </CardContent>
    </Card>
  );
}

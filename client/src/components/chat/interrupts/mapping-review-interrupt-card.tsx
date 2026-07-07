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
import { PLATFORM_COLORS, SOURCE_FIELD_SELECT_CLASS } from "@/components/chat/interrupts/platform-colors";

export function MappingReviewInterruptCard({ payload, onApprove, onReject }: InterruptCardProps) {
  const destinations = (payload.destinations ?? []) as MappingDestination[];
  const rows = (payload.rows ?? []) as MappingReviewRow[];
  const sourceFields = (payload.source_fields ?? []) as string[];
  const isSingle = destinations.length <= 1;
  const dest = destinations[0];

  // Track user-overridden source fields per row index
  const [sourceOverrides, setSourceOverrides] = useState<Record<number, string>>({});

  function getSourceField(row: MappingReviewRow, i: number) {
    return sourceOverrides[i] ?? row.source_field;
  }

  const needsAction = rows.reduce((n, row) => {
    return n + Object.values(row.cells ?? {}).filter(
      (c) => c.status === "needs_input" || c.status === "missing",
    ).length;
  }, 0);

  function handleApprove() {
    const updatedRows = rows.map((row, i) => ({
      ...row,
      source_field: getSourceField(row, i),
    }));
    onApprove({ approved: true, rows: updatedRows });
  }

  // Shared source field dropdown
  function SourceDropdown({ row, index }: { row: MappingReviewRow; index: number }) {
    const value = getSourceField(row, index);
    if (sourceFields.length === 0) {
      // No options provided — read-only pill
      return (
        <div className="h-9 flex-1 flex items-center px-3 rounded-lg border border-[var(--border)] bg-[var(--background)] text-sm text-[var(--foreground)] min-w-0 truncate">
          {value}
        </div>
      );
    }
    return (
      <select
        value={value}
        onChange={(e) => setSourceOverrides((prev) => ({ ...prev, [index]: e.target.value }))}
        className={SOURCE_FIELD_SELECT_CLASS}
      >
        {!sourceFields.includes(value) && (
          <option value={value}>{value}</option>
        )}
        {sourceFields.map((f) => (
          <option key={f} value={f}>{f}</option>
        ))}
      </select>
    );
  }

  return (
    <Card className="border-[var(--border)] bg-[var(--card)]">
      <CardContent className="p-4 space-y-3">
        {/* Header label */}
        <p className="text-[10px] font-semibold tracking-widest text-[var(--muted-foreground)] uppercase">
          {payload.source_object}
          {isSingle && dest ? ` → ${dest.label}` : ""}
        </p>

        {isSingle ? (
          // ── Single destination: source dropdown → dest pill + dot ──────────
          <div className="space-y-2">
            {rows.map((row, i) => {
              const cell = dest ? row.cells[dest.id] : Object.values(row.cells)[0];
              return (
                <div key={i} className="flex items-center gap-2">
                  <SourceDropdown row={row} index={i} />
                  <span className="text-[var(--muted-foreground)] text-xs shrink-0">→</span>
                  <div className="flex-1 flex items-center h-9 px-3 rounded-lg border border-[var(--border)] bg-[var(--background)] text-sm text-[var(--foreground)] min-w-0 truncate">
                    {cell?.field ?? "—"}
                  </div>
                  <MappingStatusDot status={cell?.status ?? ""} />
                </div>
              );
            })}
          </div>
        ) : (
          // ── Multi destination: grid table with source dropdowns ────────────
          <div className="rounded-lg border border-[var(--border)] overflow-hidden">
            <div
              className="grid border-b border-[var(--border)] bg-[var(--secondary)]"
              style={{ gridTemplateColumns: `1.2fr ${destinations.map(() => "1fr").join(" ")}` }}
            >
              <div className="px-3 py-2 text-xs font-medium text-[var(--muted-foreground)]">
                {payload.source_object ?? "Source field"}
              </div>
              {destinations.map((d) => (
                <div key={d.id} className="px-3 py-2 flex items-center gap-1.5 border-l border-[var(--border)]">
                  <span
                    className="h-3.5 w-3.5 rounded-sm shrink-0"
                    style={{ backgroundColor: d.color ?? PLATFORM_COLORS[d.id] ?? "#888" }}
                  />
                  <span className="text-xs font-medium text-[var(--foreground)] truncate">{d.label}</span>
                </div>
              ))}
            </div>
            {rows.map((row, i) => (
              <div
                key={i}
                className="grid border-b border-[var(--border)] last:border-0 hover:bg-[var(--secondary)]/40 transition-colors"
                style={{ gridTemplateColumns: `1.2fr ${destinations.map(() => "1fr").join(" ")}` }}
              >
                <div className="px-3 py-2.5">
                  <SourceDropdown row={row} index={i} />
                </div>
                {destinations.map((d) => {
                  const cell = row.cells[d.id];
                  const isNotRequired = !cell || cell.status === "not_required";
                  return (
                    <div key={d.id} className="px-3 py-2.5 flex items-center gap-2 border-l border-[var(--border)]">
                      {isNotRequired ? (
                        <span className="text-xs text-[var(--muted-foreground)]/60 italic">— not required —</span>
                      ) : (
                        <>
                          <MappingStatusDot status={cell.status} />
                          <span className="text-sm text-[var(--foreground)] truncate">{cell.field ?? "—"}</span>
                        </>
                      )}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        )}

        {/* Legend */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          {[
            { color: "bg-green-500", label: "mapped & confident" },
            { color: "bg-amber-500", label: "needs your input" },
            { color: "bg-red-500",   label: "missing" },
          ].map(({ color, label }) => (
            <span key={label} className="flex items-center gap-1 text-[10px] font-medium tracking-wider text-[var(--muted-foreground)] uppercase">
              <span className={`h-2 w-2 rounded-full ${color}`} />
              {label}
            </span>
          ))}
          {!isSingle && (
            <span className="text-[10px] text-[var(--muted-foreground)]">
              · Shared rows map once → all destinations
            </span>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <Button type="button" className="flex-1" onClick={handleApprove}>
            {needsAction > 0 ? `Resolve ${needsAction} field${needsAction !== 1 ? "s" : ""}` : "Approve mapping"}
          </Button>
          <Button type="button" variant="outline" className="flex-1" onClick={() => onReject("edit_mapping")}>
            Edit mapping
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

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

type FieldResolution =
  | { type: "constant"; value: string }
  | { type: "field"; source_field: string };

export function ResolveFieldsInterruptCard({ payload, onApprove, onReject }: InterruptCardProps) {
  const isResolved = payload.resolve_status === "resolved";
  const fields = (payload.unresolved_fields ?? []) as UnresolvedField[];
  const sourceFields = (payload.source_fields ?? []) as string[];
  const destinationLabel = payload.destination_label ?? "destination";

  // Per-field resolution state — null = still pending
  const [resolutions, setResolutions] = useState<Record<string, FieldResolution | null>>({});
  // Which field currently has the inline dropdown open
  const [mappingField, setMappingField] = useState<string | null>(null);

  function resolve(field: string, resolution: FieldResolution) {
    setResolutions((prev) => ({ ...prev, [field]: resolution }));
    setMappingField(null);
  }

  function clearResolution(field: string) {
    setResolutions((prev) => ({ ...prev, [field]: null }));
  }

  function handleSubmit() {
    const resolvedList = fields
      .map((f) => {
        const r = resolutions[f.field];
        if (!r) return null;
        return r.type === "constant"
          ? { field: f.field, action: "set_constant", value: r.value }
          : { field: f.field, action: "map_field", source_field: r.source_field };
      })
      .filter(Boolean);
    onApprove({ action: "submit", resolutions: resolvedList });
  }

  const resolvedCount = fields.filter((f) => resolutions[f.field]).length;

  const inlineChip = (label: string, onClick: () => void) => (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center rounded border border-[var(--border)] bg-[var(--background)] px-2 py-0.5 text-xs text-[var(--foreground)] hover:bg-[var(--secondary)] transition-colors cursor-pointer"
    >
      {label}
    </button>
  );

  // ── Resolved state ────────────────────────────────────────────────────────
  if (isResolved) {
    return (
      <Card className="border-[var(--border)] bg-[var(--card)] overflow-hidden shadow-sm">
        <CardContent className="p-3">
          <p className="text-[10px] font-semibold tracking-widest text-[var(--muted-foreground)] uppercase mb-3">
            Fields resolved
          </p>
          <div className="flex rounded-md border border-[var(--border)]/60 overflow-hidden mb-3">
            <div className="w-1 shrink-0 bg-green-500" />
            <div className="px-4 py-3 space-y-0.5 flex-1 bg-green-500/[0.03]">
              <p className="text-sm font-semibold text-[var(--foreground)]">
                All required {destinationLabel} fields resolved
              </p>
              {payload.summary_text && (
                <p className="text-sm text-[var(--muted-foreground)] leading-relaxed">
                  {payload.summary_text}
                </p>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            <Button type="button" className="flex-1" onClick={() => onApprove({ action: "confirm" })}>
              Confirm mapping
            </Button>
            <Button type="button" variant="outline" className="flex-1" onClick={() => onReject("edit")}>
              Edit a field
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  // ── Has issues state ──────────────────────────────────────────────────────
  return (
    <Card className="border-[var(--border)] bg-[var(--card)] overflow-hidden shadow-sm">
      <CardContent className="p-3 space-y-3">
        <p className="text-[10px] font-semibold tracking-widest text-[var(--muted-foreground)] uppercase">
          Unresolved fields
        </p>

        <div className="space-y-2">
          {fields.map((f) => {
            const resolution = resolutions[f.field];
            const isFieldResolved = !!resolution;

            return (
              <div key={f.field} className="flex rounded-md border border-[var(--border)]/60 overflow-hidden">
                {/* Left accent — amber if pending, green if resolved */}
                <div className={`w-1 shrink-0 ${isFieldResolved ? "bg-green-500" : "bg-amber-500"}`} />

                <div className={`px-4 py-3 space-y-2 flex-1 ${isFieldResolved ? "bg-green-500/[0.03]" : "bg-amber-500/[0.03]"}`}>
                  <p className="text-sm font-semibold text-[var(--foreground)]">
                    {f.field}
                    {!isFieldResolved && (
                      <span className="ml-1.5 text-xs font-normal text-amber-600 dark:text-amber-400">
                        ({f.required ? "required" : "optional"}, unmapped)
                      </span>
                    )}
                  </p>

                  {isFieldResolved ? (
                    // ── Resolved inline state ──────────────────────────────
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-green-600 dark:text-green-400 font-medium">
                        {resolution.type === "constant"
                          ? `Constant: ${resolution.value}`
                          : `Mapped to: ${resolution.source_field}`}
                      </span>
                      <button
                        type="button"
                        onClick={() => clearResolution(f.field)}
                        className="text-xs text-[var(--muted-foreground)] hover:text-[var(--foreground)] underline transition-colors"
                      >
                        change
                      </button>
                    </div>
                  ) : mappingField === f.field ? (
                    // ── Inline field picker ────────────────────────────────
                    <div className="flex items-center gap-2">
                      <select
                        autoFocus
                        defaultValue=""
                        onChange={(e) => {
                          if (!e.target.value) return;
                          resolve(f.field, { type: "field", source_field: e.target.value });
                        }}
                        className="flex-1 h-8 rounded-md border border-[var(--border)] bg-[var(--background)] px-2 text-sm text-[var(--foreground)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                      >
                        <option value="" disabled>Select a field…</option>
                        {sourceFields.map((sf) => (
                          <option key={sf} value={sf}>{sf}</option>
                        ))}
                      </select>
                      <button
                        type="button"
                        onClick={() => setMappingField(null)}
                        className="text-xs text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    // ── Action chips ───────────────────────────────────────
                    <div className="flex flex-wrap gap-2">
                      {f.suggested_constant && inlineChip(
                        `Set constant: ${f.suggested_constant}`,
                        () => resolve(f.field, { type: "constant", value: f.suggested_constant! }),
                      )}
                      {f.suggested_source_field && inlineChip(
                        `Map to: ${f.suggested_source_field}`,
                        () => resolve(f.field, { type: "field", source_field: f.suggested_source_field! }),
                      )}
                      {inlineChip("Map a field", () => setMappingField(f.field))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Submit all resolutions at once */}
        <Button
          type="button"
          className="w-full"
          disabled={resolvedCount === 0}
          onClick={handleSubmit}
        >
          {resolvedCount === 0
            ? "Resolve fields above to continue"
            : resolvedCount === fields.length
            ? "Continue — all fields resolved"
            : `Continue with ${resolvedCount} of ${fields.length} resolved`}
        </Button>
      </CardContent>
    </Card>
  );
}

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

export function SelectChannelsInterruptCard({ payload, onApprove }: InterruptCardProps) {
  const options = (payload.options ?? []) as SelectOption[];
  const min = payload.min_select ?? 1;

  // default_selected can be a string or string[]
  const defaultIds = Array.isArray(payload.default_selected)
    ? payload.default_selected
    : payload.default_selected
    ? [payload.default_selected]
    : [];
  const validDefaultIds = defaultIds.filter((id) =>
    options.some((o) => o.id === id && o.enabled !== false),
  );

  const [selected, setSelected] = useState<Set<string>>(new Set(validDefaultIds));

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  const canContinue = selected.size >= min;
  const selectedLabels = options
    .filter((o) => selected.has(o.id))
    .map((o) => o.label)
    .join(", ");

  return (
    <Card className="border-[var(--border)] bg-[var(--card)]">
      <CardContent className="p-4 space-y-4">
        {/* Section label — message/hint rendered as chat bubbles in headless-chat */}
        <p className="text-[10px] font-semibold tracking-widest text-[var(--muted-foreground)] uppercase">
          {(payload.title as string | undefined) || "Ad platforms"}
        </p>

        <div className="flex flex-wrap gap-2">
          {options.map((opt) => {
            const isEnabled = opt.enabled !== false;
            const isSelected = selected.has(opt.id);

            return (
              <button
                key={opt.id}
                type="button"
                disabled={!isEnabled}
                onClick={() => isEnabled && toggle(opt.id)}
                style={{ borderRadius: isSelected ? "8px" : "9999px" }}
                className={[
                  "inline-flex items-center gap-2 border px-3 py-1.5 text-sm font-medium",
                  "transition-all duration-300 ease-in-out",
                  isEnabled ? "cursor-pointer" : "cursor-not-allowed opacity-35",
                  isSelected
                    ? "border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--primary)]"
                    : "border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] hover:border-[var(--primary)]/40 hover:bg-[var(--secondary)]",
                ].join(" ")}
              >
                {/* Checkbox indicator */}
                <span className={[
                  "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border text-[10px]",
                  isSelected
                    ? "border-[var(--primary)] bg-[var(--primary)] text-white"
                    : "border-[var(--muted-foreground)]/50 bg-transparent text-transparent",
                ].join(" ")}>
                  ✓
                </span>
                {opt.label}
                {!isEnabled && (
                  <span className="text-[10px] text-[var(--muted-foreground)] opacity-70">soon</span>
                )}
              </button>
            );
          })}
        </div>

        {selected.size > 0 && (
          <p className="text-xs text-[var(--muted-foreground)] truncate">
            {selectedLabels}
          </p>
        )}

        <Button
          type="button"
          disabled={!canContinue}
          onClick={() => onApprove({ selected: Array.from(selected) })}
          className="w-full"
        >
          {canContinue
            ? `Continue with ${selected.size} channel${selected.size !== 1 ? "s" : ""}`
            : `Select at least ${min} channel${min !== 1 ? "s" : ""}`}
        </Button>
      </CardContent>
    </Card>
  );
}

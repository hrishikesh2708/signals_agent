"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { InterruptCardProps } from "@/components/chat/interrupts/interrupt-card-props";
import type { SelectOption } from "@/lib/interrupt-types";

export function IntentClarifyInterruptCard({ payload, onApprove }: InterruptCardProps) {
  const options = (payload.options ?? []) as SelectOption[];
  const multi = payload.multi === true;
  const title = payload.title || "Make a selection";
  const subtitle = payload.subtitle;

  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  function selectSingle(id: string) {
    setSelectedIds([id]);
  }

  function toggleMulti(id: string) {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }

  const canContinue = selectedIds.length > 0;
  const selectedLabels = options
    .filter((o) => selectedIds.includes(o.id))
    .map((o) => o.label)
    .join(", ");

  function handleContinue() {
    if (!canContinue) return;
    if (multi) {
      onApprove({ selected: selectedIds });
      return;
    }
    onApprove({ selected: selectedIds[0] });
  }

  return (
    <Card className="border-[var(--border)] bg-[var(--card)]">
      <CardContent className="p-4 space-y-4">
        <div className="space-y-1">
          <p className="text-[10px] font-semibold tracking-widest text-[var(--muted-foreground)] uppercase">
            {title}
          </p>
          {subtitle ? (
            <p className="text-sm text-[var(--muted-foreground)]">{subtitle}</p>
          ) : null}
        </div>

        <div className="flex flex-wrap gap-2">
          {options.map((opt) => {
            const isEnabled = opt.enabled !== false;
            const isSelected = selectedIds.includes(opt.id);

            return (
              <button
                key={opt.id}
                type="button"
                disabled={!isEnabled}
                title={opt.description}
                onClick={() => {
                  if (!isEnabled) return;
                  if (multi) toggleMulti(opt.id);
                  else selectSingle(opt.id);
                }}
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
                <span
                  className={[
                    "flex h-4 w-4 shrink-0 items-center justify-center border transition-all duration-300",
                    multi ? "rounded-[4px]" : "rounded-full",
                    isSelected
                      ? "border-[var(--primary)] bg-[var(--primary)] text-white"
                      : "border-[var(--muted-foreground)]/50 bg-transparent text-transparent",
                  ].join(" ")}
                >
                  {multi ? (
                    <span className="text-[10px]">✓</span>
                  ) : (
                    isSelected && <span className="h-1.5 w-1.5 rounded-full bg-white" />
                  )}
                </span>
                {opt.label}
                {!isEnabled && (
                  <span className="text-[10px] text-[var(--muted-foreground)] opacity-70">
                    soon
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {multi && selectedIds.length > 0 && (
          <p className="text-xs text-[var(--muted-foreground)] truncate">{selectedLabels}</p>
        )}

        <Button
          type="button"
          disabled={!canContinue}
          onClick={handleContinue}
          className="w-full"
        >
          {canContinue
            ? multi
              ? `Continue with ${selectedIds.length} selected`
              : `Continue with ${selectedLabels || selectedIds[0]}`
            : "Select an option"}
        </Button>
      </CardContent>
    </Card>
  );
}

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

export function SelectSourceInterruptCard({ payload, onApprove }: InterruptCardProps) {
  const options = (payload.options ?? []) as SelectOption[];
  const enabledOptions = options.filter((o) => o.enabled !== false);

  // Backend sends recommended (= the LLM-inferred or already-valid source id)
  const recommended = (payload.recommended as string | undefined) || "";

  // Normalize default_selected — may be string | string[]
  const rawDefault = Array.isArray(payload.default_selected)
    ? payload.default_selected[0]
    : payload.default_selected;
  const defaultId =
    rawDefault && enabledOptions.some((o) => o.id === rawDefault)
      ? rawDefault
      : enabledOptions[0]?.id ?? "";

  const [selected, setSelected] = useState<string>(defaultId);

  return (
    <Card className="border-[var(--border)] bg-[var(--card)]">
      <CardContent className="p-4 space-y-4">
        {/* Section label — message/hint rendered as chat bubbles in headless-chat */}
        <p className="text-[10px] font-semibold tracking-widest text-[var(--muted-foreground)] uppercase">
          {(payload.title as string | undefined) || "Data source"}
        </p>

        <div className="flex flex-wrap gap-2">
          {options.map((opt) => {
            const isEnabled = opt.enabled !== false;
            const isSelected = selected === opt.id;
            const isSuggested = !!recommended && opt.id === recommended;

            return (
              <button
                key={opt.id}
                type="button"
                disabled={!isEnabled}
                onClick={() => isEnabled && setSelected(opt.id)}
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
                {/* Radio indicator */}
                <span className={[
                  "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border transition-all duration-300",
                  isSelected
                    ? "border-[var(--primary)] bg-[var(--primary)]"
                    : "border-[var(--muted-foreground)]/50 bg-transparent",
                ].join(" ")}>
                  {isSelected && (
                    <span className="h-1.5 w-1.5 rounded-full bg-white" />
                  )}
                </span>
                {opt.label}
                {isSuggested && (
                  <span className={[
                    "text-[10px] font-medium transition-colors duration-300",
                    isSelected ? "text-[var(--primary)]/70" : "text-[var(--muted-foreground)]",
                  ].join(" ")}>
                    suggested
                  </span>
                )}
                {!isEnabled && (
                  <span className="text-[10px] text-[var(--muted-foreground)] opacity-70">soon</span>
                )}
              </button>
            );
          })}
        </div>

        <Button
          type="button"
          disabled={!selected}
          onClick={() => onApprove({ selected })}
          className="w-full"
        >
          {selected
            ? `Continue with ${options.find((o) => o.id === selected)?.label ?? selected}`
            : "Select a source"}
        </Button>
      </CardContent>
    </Card>
  );
}

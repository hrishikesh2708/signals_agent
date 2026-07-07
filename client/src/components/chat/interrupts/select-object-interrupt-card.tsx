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

export function SelectObjectInterruptCard({ payload, onApprove }: InterruptCardProps) {
  const rawOptions = payload.options ?? [];

  // Backend sends recommended (and default_selected = recommended).
  // payload.requested is not used for the normal gather_object flow.
  const recommended =
    (payload.recommended as string | undefined) ||
    (Array.isArray(payload.default_selected)
      ? payload.default_selected[0]
      : payload.default_selected) ||
    "";

  // Normalise options to strings — backend may send string[] or SelectOption[]
  const allObjects = rawOptions.map((o) => (typeof o === "string" ? o : (o as SelectOption).id));

  // Backend already orders: recommended first, alternatives next, then rest.
  // If recommended isn't first, move it there so the UI matches the PRD.
  const suggested = recommended
    ? (allObjects.find((o) => o.toLowerCase() === recommended.toLowerCase()) ?? "")
    : allObjects[0] ?? "";
  const rest = allObjects.filter((o) => o !== suggested);
  const objects = suggested ? [suggested, ...rest] : allObjects;

  const [selected, setSelected] = useState<string>(suggested || allObjects[0] || "");

  return (
    <Card className="border-[var(--border)] bg-[var(--card)]">
      <CardContent className="p-4 space-y-4">
        {/* Section label — message/hint rendered as chat bubbles in headless-chat */}
        <p className="text-[10px] font-semibold tracking-widest text-[var(--muted-foreground)] uppercase">
          {(payload.title as string | undefined) || "Salesforce object"}
        </p>

        <div className="flex flex-wrap gap-2">
          {objects.map((obj) => {
            const isSelected = selected === obj;
            // Show "suggested" badge on the backend-recommended option
            const isSuggested = obj === suggested && !!recommended;

            return (
              <button
                key={obj}
                type="button"
                onClick={() => setSelected(obj)}
                style={{ borderRadius: isSelected ? "8px" : "9999px" }}
                className={[
                  "inline-flex items-center gap-2 border px-3 py-1.5 text-sm font-medium",
                  "transition-all duration-300 ease-in-out cursor-pointer",
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
                  {isSelected && <span className="h-1.5 w-1.5 rounded-full bg-white" />}
                </span>

                {obj}

                {isSuggested && (
                  <span className={[
                    "text-[10px] font-medium transition-colors duration-300",
                    isSelected ? "text-[var(--primary)]/70" : "text-[var(--muted-foreground)]",
                  ].join(" ")}>
                    suggested
                  </span>
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
          {selected ? `Continue with ${selected}` : "Select an object"}
        </Button>
      </CardContent>
    </Card>
  );
}

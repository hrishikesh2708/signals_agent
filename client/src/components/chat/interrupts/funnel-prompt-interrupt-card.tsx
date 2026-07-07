"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { InterruptCardProps } from "@/components/chat/interrupts/interrupt-card-props";

type PicklistFieldOption = { name: string; label: string };

export function FunnelPromptInterruptCard({ payload, onApprove }: InterruptCardProps) {
  const picklistFields = (payload.picklist_fields ?? []) as PicklistFieldOption[];
  const suggested = (payload.suggested_trigger_field as string | undefined) ?? picklistFields[0]?.name ?? "";
  const infoText = payload.info_text as string | undefined;

  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [triggerField, setTriggerField] = useState<string>(suggested);

  return (
    <Card className="border-[var(--border)] bg-[var(--card)] overflow-hidden shadow-sm">
      <CardContent className="p-4 space-y-4">
        <p className="text-[10px] font-semibold tracking-widest text-[var(--muted-foreground)] uppercase">
          Funnel setup
        </p>

        {infoText && (
          <div className="rounded-lg border border-blue-200 dark:border-blue-800/60 bg-blue-500/5 px-3 py-2">
            <p className="text-xs text-blue-700 dark:text-blue-400 leading-relaxed">{infoText}</p>
          </div>
        )}

        {/* Enable / skip toggle */}
        <div className="flex gap-2">
          {[
            { value: true,  label: "Yes, set up funnel" },
            { value: false, label: "Skip for now" },
          ].map(({ value, label }) => {
            const isSelected = enabled === value;
            return (
              <button
                key={String(value)}
                type="button"
                onClick={() => setEnabled(value)}
                style={{ borderRadius: isSelected ? "8px" : "9999px" }}
                className={[
                  "flex-1 inline-flex items-center justify-center gap-2 border px-3 py-2 text-sm font-medium",
                  "transition-all duration-300 ease-in-out cursor-pointer",
                  isSelected
                    ? "border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--primary)]"
                    : "border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] hover:border-[var(--primary)]/40",
                ].join(" ")}
              >
                <span className={[
                  "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border transition-all",
                  isSelected
                    ? "border-[var(--primary)] bg-[var(--primary)]"
                    : "border-[var(--muted-foreground)]/50",
                ].join(" ")}>
                  {isSelected && <span className="h-1.5 w-1.5 rounded-full bg-white" />}
                </span>
                {label}
              </button>
            );
          })}
        </div>

        {/* Trigger field picker — only shown when enabled */}
        {enabled && picklistFields.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-[var(--muted-foreground)]">Stage trigger field</p>
            <select
              value={triggerField}
              onChange={(e) => setTriggerField(e.target.value)}
              className="w-full h-9 rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 text-sm text-[var(--foreground)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)] cursor-pointer"
            >
              {picklistFields.map((f) => (
                <option key={f.name} value={f.name}>
                  {f.label || f.name}
                  {f.name === suggested ? " (suggested)" : ""}
                </option>
              ))}
            </select>
          </div>
        )}

        <Button
          type="button"
          className="w-full"
          disabled={enabled === null}
          onClick={() => onApprove({ enabled: enabled ?? false, trigger_field: enabled ? triggerField : null })}
        >
          {enabled === null ? "Choose an option above" : enabled ? "Continue with funnel" : "Skip funnel"}
        </Button>
      </CardContent>
    </Card>
  );
}

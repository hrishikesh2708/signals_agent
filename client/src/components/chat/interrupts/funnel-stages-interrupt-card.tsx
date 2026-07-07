"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { InterruptCardProps } from "@/components/chat/interrupts/interrupt-card-props";

type FunnelStageRow = {
  stage_name: string;
  trigger_value: string;
  time_field: string;
  value_field: string;
  per_destination: Record<string, { event_name: string }>;
};

export function FunnelStagesInterruptCard({ payload, onApprove }: InterruptCardProps) {
  const triggerField = payload.trigger_field as string | undefined ?? "Stage";
  const suggestedStages = (payload.suggested_stages ?? []) as Array<{
    stage_name: string; trigger_value: string; time_field?: string; value_field?: string;
    per_destination?: Record<string, unknown>;
  }>;
  const datetimeFields = (payload.datetime_fields ?? []) as string[];
  const numericFields  = (payload.numeric_fields  ?? []) as string[];
  const activeDestinations = (payload.active_destinations ?? []) as string[];
  const infoText = payload.info_text as string | undefined;

  const [stages, setStages] = useState<FunnelStageRow[]>(() =>
    suggestedStages.map((s) => ({
      stage_name:      s.stage_name ?? s.trigger_value ?? "",
      trigger_value:   s.trigger_value ?? "",
      time_field:      s.time_field ?? "",
      value_field:     s.value_field ?? "",
      per_destination: activeDestinations.reduce<Record<string, { event_name: string }>>((acc, d) => {
        acc[d] = { event_name: "" };
        return acc;
      }, {}),
    })),
  );

  function updateStage<K extends keyof FunnelStageRow>(i: number, key: K, value: FunnelStageRow[K]) {
    setStages((prev) => prev.map((s, idx) => idx === i ? { ...s, [key]: value } : s));
  }

  function updateDestEventName(i: number, dest: string, eventName: string) {
    setStages((prev) =>
      prev.map((s, idx) =>
        idx === i
          ? { ...s, per_destination: { ...s.per_destination, [dest]: { event_name: eventName } } }
          : s,
      ),
    );
  }

  const hasStages = stages.length > 0;

  return (
    <Card className="border-[var(--border)] bg-[var(--card)] overflow-hidden shadow-sm">
      <CardContent className="p-4 space-y-4">
        <p className="text-[10px] font-semibold tracking-widest text-[var(--muted-foreground)] uppercase">
          Funnel stages — {triggerField}
        </p>

        {infoText && (
          <div className="rounded-lg border border-blue-200 dark:border-blue-800/60 bg-blue-500/5 px-3 py-2">
            <p className="text-xs text-blue-700 dark:text-blue-400 leading-relaxed">{infoText}</p>
          </div>
        )}

        {hasStages ? (
          <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
            {stages.map((stage, i) => (
              <div key={i} className="rounded-lg border border-[var(--border)] bg-[var(--background)] p-3 space-y-2">
                {/* Stage name + trigger value header */}
                <div className="flex items-center gap-2">
                  <span className="h-5 w-5 shrink-0 rounded-full bg-[var(--primary)]/10 text-[var(--primary)] text-xs font-bold flex items-center justify-center">
                    {i + 1}
                  </span>
                  <input
                    type="text"
                    value={stage.stage_name}
                    onChange={(e) => updateStage(i, "stage_name", e.target.value)}
                    placeholder="Stage name"
                    className="flex-1 h-8 rounded-md border border-[var(--border)] bg-[var(--card)] px-2 text-sm text-[var(--foreground)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                  />
                  <span className="text-[10px] text-[var(--muted-foreground)] bg-[var(--secondary)] px-2 py-0.5 rounded-full shrink-0">
                    {stage.trigger_value}
                  </span>
                </div>

                {/* Optional fields row */}
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <p className="text-[10px] text-[var(--muted-foreground)] mb-0.5">Time field</p>
                    <select
                      value={stage.time_field}
                      onChange={(e) => updateStage(i, "time_field", e.target.value)}
                      className="w-full h-7 rounded-md border border-[var(--border)] bg-[var(--background)] px-2 text-xs text-[var(--foreground)] focus:outline-none cursor-pointer"
                    >
                      <option value="">None</option>
                      {datetimeFields.map((f) => <option key={f} value={f}>{f}</option>)}
                    </select>
                  </div>
                  <div>
                    <p className="text-[10px] text-[var(--muted-foreground)] mb-0.5">Value field</p>
                    <select
                      value={stage.value_field}
                      onChange={(e) => updateStage(i, "value_field", e.target.value)}
                      className="w-full h-7 rounded-md border border-[var(--border)] bg-[var(--background)] px-2 text-xs text-[var(--foreground)] focus:outline-none cursor-pointer"
                    >
                      <option value="">None</option>
                      {numericFields.map((f) => <option key={f} value={f}>{f}</option>)}
                    </select>
                  </div>
                </div>

                {/* Per-destination event name */}
                {activeDestinations.length > 0 && (
                  <div className="space-y-1">
                    <p className="text-[10px] text-[var(--muted-foreground)]">Event name per destination</p>
                    {activeDestinations.map((dest) => (
                      <div key={dest} className="flex items-center gap-2">
                        <span className="text-xs text-[var(--muted-foreground)] w-24 shrink-0 truncate">{dest}</span>
                        <input
                          type="text"
                          value={stage.per_destination[dest]?.event_name ?? ""}
                          onChange={(e) => updateDestEventName(i, dest, e.target.value)}
                          placeholder="e.g. Purchase"
                          className="flex-1 h-7 rounded-md border border-[var(--border)] bg-[var(--card)] px-2 text-xs text-[var(--foreground)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                        />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-[var(--muted-foreground)] italic">
            No stage values found in schema. Add them manually if needed.
          </p>
        )}

        <Button
          type="button"
          className="w-full"
          disabled={stages.some((s) => !s.stage_name.trim())}
          onClick={() =>
            onApprove({
              stages: stages.map((s) => ({
                stage_name:      s.stage_name.trim(),
                trigger_value:   s.trigger_value,
                time_field:      s.time_field || null,
                value_field:     s.value_field || null,
                per_destination: s.per_destination,
              })),
            })
          }
        >
          {stages.length === 0
            ? "Continue without stages"
            : `Confirm ${stages.length} stage${stages.length !== 1 ? "s" : ""}`}
        </Button>
      </CardContent>
    </Card>
  );
}

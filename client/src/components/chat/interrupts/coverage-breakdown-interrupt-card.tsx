"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { InterruptCardProps } from "@/components/chat/interrupts/interrupt-card-props";

export function CoverageBreakdownInterruptCard({ payload, onApprove, onReject }: InterruptCardProps) {
  const destinations = (payload.destinations_breakdown ?? payload.destinations ?? []) as Array<{
    destination: string; coverage_pct: number; match_keys_covered: string[];
    match_keys_missing: string[]; status: string; required_count: number; mapped_count: number;
  }>;
  const overallPct = (payload.overall_pct as number | undefined) ?? 0;

  return (
    <Card className="border-[var(--border)] bg-[var(--card)] overflow-hidden shadow-sm">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-[10px] font-semibold tracking-widest text-[var(--muted-foreground)] uppercase">
            Coverage breakdown
          </p>
          <span className={`text-sm font-semibold ${overallPct >= 80 ? "text-green-600 dark:text-green-400" : overallPct >= 50 ? "text-amber-600 dark:text-amber-400" : "text-red-500"}`}>
            {overallPct.toFixed(0)}% overall
          </span>
        </div>

        <div className="space-y-2">
          {destinations.map((dest) => {
            const pct = dest.coverage_pct;
            const barColor = pct >= 80 ? "bg-green-500" : pct >= 50 ? "bg-amber-500" : "bg-red-500";
            return (
              <div key={dest.destination} className="rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2.5 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-[var(--foreground)]">
                    {dest.destination.replace(/_/g, " ").toUpperCase()}
                  </span>
                  <span className={`text-xs font-semibold ${dest.status === "ready" ? "text-green-600 dark:text-green-400" : "text-amber-600 dark:text-amber-400"}`}>
                    {pct.toFixed(0)}% — {dest.mapped_count}/{dest.required_count} fields
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-[var(--secondary)] overflow-hidden">
                  <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: `${pct}%` }} />
                </div>
                {dest.match_keys_missing.length > 0 && (
                  <p className="text-xs text-amber-600 dark:text-amber-400">
                    Missing match keys: {dest.match_keys_missing.join(", ")}
                  </p>
                )}
                {dest.match_keys_covered.length > 0 && dest.match_keys_missing.length === 0 && (
                  <p className="text-xs text-green-600 dark:text-green-400">
                    All match keys covered: {dest.match_keys_covered.join(", ")}
                  </p>
                )}
              </div>
            );
          })}
        </div>

        <div className="flex gap-2">
          <Button type="button" className="flex-1" onClick={() => onApprove({ acknowledged: true })}>
            Continue
          </Button>
          <Button type="button" variant="outline" className="flex-1" onClick={() => onReject("fix_mapping")}>
            Fix mapping
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

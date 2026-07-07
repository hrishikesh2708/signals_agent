"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { InterruptCardProps } from "@/components/chat/interrupts/interrupt-card-props";

export function CanonicalNeedsInterruptCard({ payload, onApprove }: InterruptCardProps) {
  const needs = (payload.needs ?? []) as Array<{
    canonical_key: string; label: string; reason: string; status: string; required: boolean;
  }>;
  const missing = needs.filter((n) => n.status === "missing");
  const mapped = needs.filter((n) => n.status === "mapped");

  return (
    <Card className="border-[var(--border)] bg-[var(--card)]">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-[10px] font-semibold tracking-widest text-[var(--muted-foreground)] uppercase">
            What Signals needs
          </p>
          <span className="text-xs text-[var(--muted-foreground)]">
            {mapped.length}/{needs.length} mapped
          </span>
        </div>

        <div className="space-y-1.5">
          {needs.map((n) => (
            <div
              key={n.canonical_key}
              className={`flex items-start gap-2.5 rounded-lg border px-3 py-2 ${
                n.status === "mapped"
                  ? "border-green-200 dark:border-green-800/50 bg-green-500/5"
                  : n.required
                  ? "border-red-200 dark:border-red-800/50 bg-red-500/5"
                  : "border-[var(--border)] bg-[var(--background)]"
              }`}
            >
              <span className={`mt-1 h-2 w-2 rounded-full shrink-0 ${
                n.status === "mapped" ? "bg-green-500" : n.required ? "bg-red-500" : "bg-amber-500"
              }`} />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-[var(--foreground)]">{n.label}</p>
                {n.reason && (
                  <p className="text-xs text-[var(--muted-foreground)] leading-relaxed">{n.reason}</p>
                )}
              </div>
              <span className={`shrink-0 text-xs font-medium ${
                n.status === "mapped" ? "text-green-600 dark:text-green-400" : "text-[var(--muted-foreground)]"
              }`}>
                {n.status === "mapped" ? "mapped" : n.required ? "required" : "optional"}
              </span>
            </div>
          ))}
        </div>

        <Button
          type="button"
          className="w-full"
          onClick={() => onApprove({ acknowledged: true })}
        >
          {missing.length === 0 ? "All fields mapped — continue" : `Continue with ${missing.length} unmapped`}
        </Button>
      </CardContent>
    </Card>
  );
}

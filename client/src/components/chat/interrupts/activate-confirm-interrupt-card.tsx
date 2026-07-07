"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { InterruptCardProps } from "@/components/chat/interrupts/interrupt-card-props";

export function ActivateConfirmInterruptCard({ payload, onApprove, onReject }: InterruptCardProps) {
  const validation   = payload.validation   as { title: string; checks: string[] } | undefined;
  const summaryCard  = payload.summary_card as { title: string; lines: string[]  } | undefined;
  const confirmLabel   = payload.confirm_label   ?? "Activate";
  const secondaryLabel = payload.secondary_label ?? "Review matrix";

  return (
    <Card className="border-[var(--border)] bg-[var(--card)] overflow-hidden shadow-sm">
      <CardContent className="p-3 space-y-3">
        <p className="text-[10px] font-semibold tracking-widest text-[var(--muted-foreground)] uppercase">
          Activate pipeline
        </p>

        {/* Validation block — green left border */}
        {validation ? (
          <div className="flex rounded-md border border-[var(--border)]/60 overflow-hidden">
            <div className="w-1 shrink-0 bg-green-500" />
            <div className="px-4 py-3 flex-1 space-y-1 bg-green-500/[0.03]">
              <p className="text-sm font-semibold text-[var(--foreground)]">{validation.title}</p>
              {validation.checks.map((check, i) => (
                <p key={i} className="text-sm text-[var(--muted-foreground)]">{check}</p>
              ))}
            </div>
          </div>
        ) : null}

        {/* Summary card — plain border */}
        {summaryCard ? (
          <div className="rounded-md border border-[var(--border)] px-4 py-3 space-y-1">
            <p className="text-sm font-semibold text-[var(--foreground)]">{summaryCard.title}</p>
            {summaryCard.lines.map((line, i) => (
              <p key={i} className="text-sm text-[var(--muted-foreground)]">{line}</p>
            ))}
          </div>
        ) : null}

        {/* CTA */}
        <div className="flex gap-2 pt-1">
          <Button
            type="button"
            className="flex-1"
            onClick={() => onApprove({ action: "activate" })}
          >
            {confirmLabel}
          </Button>
          <Button
            type="button"
            variant="outline"
            className="flex-1"
            onClick={() => onReject("review_matrix")}
          >
            {secondaryLabel}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

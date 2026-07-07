"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { InterruptCardProps } from "@/components/chat/interrupts/interrupt-card-props";

export function ValidationErrorsInterruptCard({ payload, onApprove }: InterruptCardProps) {
  const errors   = (payload.errors   ?? []) as string[];
  const warnings = (payload.warnings ?? []) as string[];
  const infoText = payload.info_text as string | undefined;
  const hasErrors = errors.length > 0;

  return (
    <Card className="border-[var(--border)] bg-[var(--card)] overflow-hidden shadow-sm">
      <CardContent className="p-4 space-y-3">
        <p className="text-[10px] font-semibold tracking-widest text-[var(--muted-foreground)] uppercase">
          Validation issues
        </p>

        {/* Errors — red */}
        {errors.length > 0 && (
          <div className="flex rounded-md border border-[var(--border)]/60 overflow-hidden">
            <div className="w-1 shrink-0 bg-red-500" />
            <div className="px-4 py-3 flex-1 bg-red-500/[0.03] space-y-1.5">
              <p className="text-xs font-semibold text-red-600 dark:text-red-400 uppercase tracking-wide">
                {errors.length} error{errors.length !== 1 ? "s" : ""}
              </p>
              {errors.map((e, i) => (
                <p key={i} className="text-sm text-[var(--foreground)] leading-snug">{e}</p>
              ))}
            </div>
          </div>
        )}

        {/* Warnings — amber */}
        {warnings.length > 0 && (
          <div className="flex rounded-md border border-[var(--border)]/60 overflow-hidden">
            <div className="w-1 shrink-0 bg-amber-500" />
            <div className="px-4 py-3 flex-1 bg-amber-500/[0.03] space-y-1.5">
              <p className="text-xs font-semibold text-amber-600 dark:text-amber-400 uppercase tracking-wide">
                {warnings.length} warning{warnings.length !== 1 ? "s" : ""}
              </p>
              {warnings.map((w, i) => (
                <p key={i} className="text-sm text-[var(--muted-foreground)] leading-snug">{w}</p>
              ))}
            </div>
          </div>
        )}

        {infoText && (
          <p className="text-xs text-[var(--muted-foreground)]">{infoText}</p>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          <Button
            type="button"
            className="flex-1"
            onClick={() => onApprove({ action: "edit_mapping" })}
          >
            Fix mapping
          </Button>
          <Button
            type="button"
            variant="outline"
            className="flex-1"
            onClick={() => onApprove({ action: "retry" })}
          >
            Retry
          </Button>
        </div>
        {hasErrors && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="w-full text-xs text-[var(--muted-foreground)] border border-dashed border-[var(--border)] hover:border-amber-400 hover:text-amber-500"
            onClick={() => onApprove({ action: "skip_errors" })}
          >
            Skip errors and proceed anyway
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

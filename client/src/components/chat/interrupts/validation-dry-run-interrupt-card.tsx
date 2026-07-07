"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { InterruptCardProps } from "@/components/chat/interrupts/interrupt-card-props";

export function ValidationDryRunInterruptCard({ payload, onApprove }: InterruptCardProps) {
  const checks = (payload.checks ?? []) as Array<{
    name: string; passed: boolean; severity: string; message: string;
    sample_payload?: Record<string, unknown>;
  }>;
  const overallPassed = payload.overall_passed as boolean | undefined;
  const infoText = payload.info_text as string | undefined;
  const [expanded, setExpanded] = useState<string | null>(null);

  const errors = checks.filter((c) => !c.passed && c.severity === "error");

  return (
    <Card className="border-[var(--border)] bg-[var(--card)] overflow-hidden shadow-sm">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-[10px] font-semibold tracking-widest text-[var(--muted-foreground)] uppercase">
            Validation results
          </p>
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
            overallPassed
              ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
              : "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400"
          }`}>
            {overallPassed ? "Passed" : `${errors.length} issue${errors.length !== 1 ? "s" : ""}`}
          </span>
        </div>

        {infoText && (
          <p className="text-xs text-[var(--muted-foreground)]">{infoText}</p>
        )}

        <div className="space-y-1.5">
          {checks.map((check) => {
            const isExpanded = expanded === check.name;
            const hasSample = check.sample_payload && Object.keys(check.sample_payload).length > 0;
            const accent =
              check.passed ? "border-green-200 dark:border-green-800/50 bg-green-500/[0.03]" :
              check.severity === "error" ? "border-red-200 dark:border-red-800/50 bg-red-500/[0.03]" :
              "border-amber-200 dark:border-amber-800/50 bg-amber-500/[0.03]";
            const dot =
              check.passed ? "bg-green-500" :
              check.severity === "error" ? "bg-red-500" : "bg-amber-500";

            return (
              <div key={check.name} className={`rounded-lg border overflow-hidden ${accent}`}>
                <button
                  type="button"
                  className="w-full flex items-start gap-2.5 px-3 py-2 text-left cursor-pointer"
                  onClick={() => hasSample && setExpanded(isExpanded ? null : check.name)}
                >
                  <span className={`mt-1.5 h-2 w-2 rounded-full shrink-0 ${dot}`} />
                  <span className="flex-1 text-sm text-[var(--foreground)] leading-snug">{check.message}</span>
                  {hasSample && (
                    <span className="text-[10px] text-[var(--muted-foreground)] shrink-0 mt-0.5">
                      {isExpanded ? "hide" : "sample"}
                    </span>
                  )}
                </button>
                {isExpanded && hasSample && (
                  <div className="border-t border-[var(--border)]/50 px-3 py-2 bg-[var(--background)]">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--muted-foreground)] mb-1.5">
                      Sample payload (masked)
                    </p>
                    <pre className="text-xs text-[var(--foreground)] overflow-x-auto whitespace-pre-wrap break-all">
                      {JSON.stringify(check.sample_payload, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div className="flex gap-2">
          <Button type="button" className="flex-1" onClick={() => onApprove({ action: "edit_mapping" })}>
            Fix mapping
          </Button>
          <Button type="button" variant="outline" className="flex-1" onClick={() => onApprove({ action: "retry" })}>
            Retry
          </Button>
        </div>
        {errors.length > 0 && (
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

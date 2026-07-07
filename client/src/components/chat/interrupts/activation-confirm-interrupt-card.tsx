"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { InterruptCardProps } from "@/components/chat/interrupts/interrupt-card-props";

export function ActivationConfirmInterruptCard({ payload, onApprove, onReject }: InterruptCardProps) {
  const token          = (payload.token          as string | undefined) ?? "";
  const summary        = (payload.summary        as string[] | undefined) ?? [];
  const infoText       = (payload.info_text      as string | undefined);
  const confirmLabel   = (payload.confirm_label  as string | undefined) ?? "Activate";
  const secondaryLabel = (payload.secondary_label as string | undefined) ?? "Go back";

  const [input, setInput] = useState("");
  const matches = input.trim() === token;

  return (
    <Card className="border-[var(--border)] bg-[var(--card)] overflow-hidden shadow-sm">
      <CardContent className="p-4 space-y-4">
        <p className="text-[10px] font-semibold tracking-widest text-[var(--muted-foreground)] uppercase">
          Confirm activation
        </p>

        {/* Summary block — green left border */}
        {summary.length > 0 && (
          <div className="flex rounded-md border border-[var(--border)]/60 overflow-hidden">
            <div className="w-1 shrink-0 bg-green-500" />
            <div className="px-4 py-3 flex-1 bg-green-500/[0.03] space-y-1">
              {summary.map((line, i) => (
                <p key={i} className="text-sm text-[var(--foreground)] leading-snug">{line}</p>
              ))}
            </div>
          </div>
        )}

        {/* Confirmation token — monospace, prominent */}
        <div className="rounded-lg border border-[var(--border)] bg-[var(--secondary)] px-4 py-3 space-y-1">
          <p className="text-[10px] font-semibold text-[var(--muted-foreground)] uppercase tracking-widest">
            Confirmation code
          </p>
          <p className="font-mono text-sm font-semibold text-[var(--foreground)] select-all break-all">
            {token}
          </p>
        </div>

        {infoText && (
          <p className="text-xs text-[var(--muted-foreground)]">{infoText}</p>
        )}

        {/* Token input */}
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type the code above to confirm…"
          className={[
            "w-full h-9 rounded-lg border px-3 text-sm font-mono bg-[var(--background)] text-[var(--foreground)]",
            "focus:outline-none focus:ring-1 transition-colors",
            input && !matches
              ? "border-red-400 focus:ring-red-400"
              : matches
              ? "border-green-500 focus:ring-green-500"
              : "border-[var(--border)] focus:ring-[var(--primary)]",
          ].join(" ")}
        />

        {input && !matches && (
          <p className="text-xs text-red-500 -mt-2">Code does not match — check for typos.</p>
        )}

        <div className="flex gap-2">
          <Button
            type="button"
            className="flex-1"
            disabled={!matches}
            onClick={() => onApprove({ token: input.trim() })}
          >
            {matches ? confirmLabel : "Enter code to activate"}
          </Button>
          <Button
            type="button"
            variant="outline"
            className="flex-1"
            onClick={() => onReject("go_back")}
          >
            {secondaryLabel}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

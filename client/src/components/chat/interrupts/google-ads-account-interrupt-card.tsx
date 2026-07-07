"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { InterruptCardProps } from "@/components/chat/interrupts/interrupt-card-props";

export function GoogleAdsAccountInterruptCard({ payload, onApprove }: InterruptCardProps) {
  const accounts = (payload.accounts ?? []) as Array<{ value: string; label: string }>;
  const infoText = payload.info_text as string | undefined;
  const [selected, setSelected] = useState<string>(accounts[0]?.value ?? "");
  const selectedAccount = accounts.find((a) => a.value === selected);

  return (
    <Card className="border-[var(--border)] bg-[var(--card)]">
      <CardContent className="p-4 space-y-4">
        <p className="text-[10px] font-semibold tracking-widest text-[var(--muted-foreground)] uppercase">
          Google Ads account
        </p>
        {infoText && (
          <div className="rounded-lg border border-blue-200 dark:border-blue-800/60 bg-blue-500/5 px-3 py-2">
            <p className="text-xs text-blue-700 dark:text-blue-400">{infoText}</p>
          </div>
        )}
        {accounts.length === 0 ? (
          <p className="text-sm text-[var(--muted-foreground)] italic">No Google Ads accounts found.</p>
        ) : (
          <div className="space-y-2">
            {accounts.map((acc) => {
              const isSelected = selected === acc.value;
              return (
                <button
                  key={acc.value}
                  type="button"
                  onClick={() => setSelected(acc.value)}
                  style={{ borderRadius: isSelected ? "8px" : "9999px" }}
                  className={[
                    "w-full inline-flex items-center gap-2 border px-3 py-2 text-sm font-medium text-left",
                    "transition-all duration-300 cursor-pointer",
                    isSelected
                      ? "border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--primary)]"
                      : "border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] hover:bg-[var(--secondary)]",
                  ].join(" ")}
                >
                  <span className={[
                    "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border transition-all",
                    isSelected ? "border-[var(--primary)] bg-[var(--primary)]" : "border-[var(--muted-foreground)]/50",
                  ].join(" ")}>
                    {isSelected && <span className="h-1.5 w-1.5 rounded-full bg-white" />}
                  </span>
                  <div className="min-w-0">
                    <p className="truncate">{acc.label}</p>
                    <p className="text-xs text-[var(--muted-foreground)] truncate">{acc.value}</p>
                  </div>
                </button>
              );
            })}
          </div>
        )}
        <Button
          type="button"
          className="w-full"
          disabled={!selected}
          onClick={() => onApprove({ account_id: selected, account_label: selectedAccount?.label ?? selected })}
        >
          {selected ? `Use account ${selectedAccount?.label ?? selected}` : "Select an account"}
        </Button>
      </CardContent>
    </Card>
  );
}

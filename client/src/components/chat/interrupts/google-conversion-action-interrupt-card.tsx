"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { InterruptCardProps } from "@/components/chat/interrupts/interrupt-card-props";

export function GoogleConversionActionInterruptCard({ payload, onApprove }: InterruptCardProps) {
  const actions = (payload.conversion_actions ?? []) as Array<{ value: string; label: string }>;
  const accountId = payload.account_id as string | undefined;
  const [selected, setSelected] = useState<string>(actions[0]?.value ?? "");
  const selectedAction = actions.find((a) => a.value === selected);

  return (
    <Card className="border-[var(--border)] bg-[var(--card)]">
      <CardContent className="p-4 space-y-4">
        <p className="text-[10px] font-semibold tracking-widest text-[var(--muted-foreground)] uppercase">
          Conversion action
        </p>
        {accountId && (
          <p className="text-xs text-[var(--muted-foreground)]">Account: {accountId}</p>
        )}
        {actions.length === 0 ? (
          <p className="text-sm text-[var(--muted-foreground)] italic">No conversion actions found.</p>
        ) : (
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            className="w-full h-9 rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 text-sm text-[var(--foreground)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)] cursor-pointer"
          >
            {!selected && <option value="" disabled>Select a conversion action…</option>}
            {actions.map((a) => (
              <option key={a.value} value={a.value}>{a.label}</option>
            ))}
          </select>
        )}
        <Button
          type="button"
          className="w-full"
          disabled={!selected}
          onClick={() => onApprove({ conversion_action: selected, conversion_action_label: selectedAction?.label ?? selected })}
        >
          {selected ? `Use ${selectedAction?.label ?? selected}` : "Select a conversion action"}
        </Button>
      </CardContent>
    </Card>
  );
}

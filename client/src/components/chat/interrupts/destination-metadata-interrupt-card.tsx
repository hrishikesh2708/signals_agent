"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { InterruptCardProps } from "@/components/chat/interrupts/interrupt-card-props";

export function DestinationMetadataInterruptCard({ payload, onApprove }: InterruptCardProps) {
  const destLabel = (payload.destination_label as string | undefined) ?? "destination";
  const fields = (payload.fields ?? []) as Array<{
    name: string; label: string; placeholder?: string; required?: boolean;
  }>;

  const [values, setValues] = useState<Record<string, string>>(
    Object.fromEntries(fields.map((f) => [f.name, ""]))
  );

  const requiredFilled = fields
    .filter((f) => f.required)
    .every((f) => (values[f.name] || "").trim().length > 0);

  return (
    <Card className="border-[var(--border)] bg-[var(--card)]">
      <CardContent className="p-4 space-y-4">
        <p className="text-[10px] font-semibold tracking-widest text-[var(--muted-foreground)] uppercase">
          {destLabel} setup
        </p>

        <div className="space-y-3">
          {fields.map((f) => (
            <div key={f.name} className="space-y-1">
              <label className="text-xs font-medium text-[var(--foreground)]">
                {f.label}
                {f.required && <span className="text-red-500 ml-0.5">*</span>}
              </label>
              <input
                type="text"
                value={values[f.name] ?? ""}
                onChange={(e) => setValues((prev) => ({ ...prev, [f.name]: e.target.value }))}
                placeholder={f.placeholder ?? `Enter ${f.label.toLowerCase()}…`}
                className="w-full h-9 rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 text-sm text-[var(--foreground)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
              />
            </div>
          ))}
        </div>

        <Button
          type="button"
          className="w-full"
          disabled={!requiredFilled}
          onClick={() => onApprove({ metadata: values })}
        >
          {requiredFilled ? `Save ${destLabel} settings` : "Fill required fields above"}
        </Button>
      </CardContent>
    </Card>
  );
}

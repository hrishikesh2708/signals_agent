"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { InterruptCardProps } from "@/components/chat/interrupts/interrupt-card-props";

export function MappingMatrixInterruptCard({ payload, onApprove, onReject }: InterruptCardProps) {
  const rows = (payload.rows ?? []) as Array<{
    canonical_key: string; label: string; source_field: string | null;
    status: string; cells: Record<string, { field: string | null; status: string }>;
  }>;
  const destinations = (payload.destinations ?? []) as Array<{ id: string; label: string }>;
  const sourceFields = (payload.source_fields ?? []) as string[];

  const [overrides, setOverrides] = useState<Record<string, string>>(() =>
    Object.fromEntries(rows.map((r) => [r.canonical_key, r.source_field ?? ""]))
  );

  function setField(canonicalKey: string, value: string) {
    setOverrides((prev) => ({ ...prev, [canonicalKey]: value }));
  }

  const missingRequired = rows.filter(
    (r) => r.status === "missing" && !overrides[r.canonical_key]
  ).length;

  function handleApprove() {
    const updatedRows = rows.map((r) => ({
      ...r,
      source_field: overrides[r.canonical_key] || r.source_field,
    }));
    onApprove({ rows: updatedRows });
  }

  const statusDot = (status: string) => {
    const cls =
      status === "mapped"      ? "bg-green-500" :
      status === "needs_input" ? "bg-amber-500" :
      status === "missing"     ? "bg-red-500"   : "bg-[var(--muted-foreground)]/30";
    return <span className={`h-2 w-2 rounded-full shrink-0 inline-block ${cls}`} />;
  };

  return (
    <Card className="border-[var(--border)] bg-[var(--card)]">
      <CardContent className="p-4 space-y-3">
        <p className="text-[10px] font-semibold tracking-widest text-[var(--muted-foreground)] uppercase">
          Mapping matrix
        </p>

        <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
          <table className="w-full text-sm" style={{ tableLayout: "fixed" }}>
            <thead>
              <tr className="bg-[var(--secondary)]">
                <th className="px-3 py-2 text-left text-xs font-medium text-[var(--muted-foreground)] w-36">
                  What Signals needs
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium text-[var(--muted-foreground)] w-44 border-l border-[var(--border)]">
                  Your SF field
                </th>
                {destinations.map((d) => (
                  <th key={d.id} className="px-3 py-2 text-left text-xs font-medium text-[var(--muted-foreground)] border-l border-[var(--border)] w-28">
                    {d.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => {
                const currentSource = overrides[row.canonical_key] ?? "";
                return (
                  <tr key={row.canonical_key} className={`border-t border-[var(--border)] ${i % 2 === 0 ? "" : "bg-[var(--secondary)]/30"}`}>
                    <td className="px-3 py-2.5">
                      <div className="flex items-center gap-1.5">
                        {statusDot(overrides[row.canonical_key] ? "mapped" : row.status)}
                        <span className="text-xs font-medium text-[var(--foreground)] truncate">{row.label}</span>
                      </div>
                    </td>
                    <td className="px-3 py-2 border-l border-[var(--border)]">
                      {sourceFields.length > 0 ? (
                        <select
                          value={currentSource}
                          onChange={(e) => setField(row.canonical_key, e.target.value)}
                          className="w-full h-7 rounded border border-[var(--border)] bg-[var(--background)] px-2 text-xs text-[var(--foreground)] focus:outline-none cursor-pointer"
                        >
                          <option value="">— not mapped —</option>
                          {sourceFields.map((f) => <option key={f} value={f}>{f}</option>)}
                        </select>
                      ) : (
                        <span className="text-xs text-[var(--foreground)] truncate">{currentSource || "—"}</span>
                      )}
                    </td>
                    {destinations.map((d) => {
                      const cell = row.cells[d.id];
                      return (
                        <td key={d.id} className="px-3 py-2 border-l border-[var(--border)]">
                          <div className="flex items-center gap-1.5">
                            {cell ? statusDot(currentSource ? "mapped" : cell.status) : null}
                            <span className="text-xs text-[var(--muted-foreground)] truncate">
                              {cell?.field ?? (cell ? "—" : "n/a")}
                            </span>
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="flex flex-wrap gap-x-4 gap-y-1">
          {[
            { color: "bg-green-500", label: "mapped" },
            { color: "bg-amber-500", label: "needs input" },
            { color: "bg-red-500",   label: "missing (required)" },
          ].map(({ color, label }) => (
            <span key={label} className="flex items-center gap-1 text-[10px] text-[var(--muted-foreground)] uppercase tracking-wider">
              <span className={`h-2 w-2 rounded-full ${color}`} /> {label}
            </span>
          ))}
        </div>

        <div className="flex gap-2">
          <Button type="button" className="flex-1" onClick={handleApprove}>
            {missingRequired > 0
              ? `Continue with ${missingRequired} field${missingRequired !== 1 ? "s" : ""} unmapped`
              : "Approve mapping"}
          </Button>
          <Button type="button" variant="outline" className="flex-1" onClick={() => onReject("edit_manual")}>
            Edit manually
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

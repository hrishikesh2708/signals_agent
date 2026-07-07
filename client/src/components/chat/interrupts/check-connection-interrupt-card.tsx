"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { InterruptCardProps } from "@/components/chat/interrupts/interrupt-card-props";

type ConnectionStatusConfig = {
  bar: string;
  tint: string;
  primaryBtn: string;
  secondaryLabel: string;
};

const CONNECTION_STATUS: Record<string, ConnectionStatusConfig> = {
  not_connected: {
    bar:         "bg-red-500",
    tint:        "bg-red-500/[0.03]",
    primaryBtn:  "",
    secondaryLabel: "Use a different source",
  },
  expired: {
    bar:         "bg-amber-500",
    tint:        "bg-amber-500/[0.03]",
    primaryBtn:  "bg-amber-500 hover:bg-amber-600 text-white border-amber-500",
    secondaryLabel: "Use a different source",
  },
  connected: {
    bar:         "bg-green-500",
    tint:        "bg-green-500/[0.03]",
    primaryBtn:  "bg-green-600 hover:bg-green-700 text-white border-green-600",
    secondaryLabel: "Use a different source",
  },
};

export function CheckConnectionInterruptCard({ payload, onApprove, onReject }: InterruptCardProps) {
  const status = payload.connection_status ?? "not_connected";
  const cfg = CONNECTION_STATUS[status] ?? CONNECTION_STATUS.not_connected;
  const isConnected = status === "connected";
  const sourceLabel = payload.source_label ?? "Source";

  return (
    <Card className="border-[var(--border)] bg-[var(--card)] overflow-hidden shadow-sm">
      <CardContent className="p-3">
        {/* Info block with status-coloured left border */}
        <div className="flex rounded-md border border-[var(--border)]/60 overflow-hidden mb-3">
          <div className={`w-1 shrink-0 ${cfg.bar}`} />
          <div className={`px-4 py-3 space-y-0.5 flex-1 ${cfg.tint}`}>
            <p className="text-sm font-semibold text-[var(--foreground)]">
              {sourceLabel}
            </p>
            {payload.account_detail && (
              <p className="text-xs font-medium text-[var(--muted-foreground)]">
                {payload.account_detail}
              </p>
            )}
            <p className="text-sm text-[var(--muted-foreground)] leading-relaxed">
              {payload.message}
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <Button
            type="button"
            className={`flex-1 ${cfg.primaryBtn}`}
            onClick={() => onApprove({ action: isConnected ? "confirm" : "connect" })}
          >
            {isConnected ? "Continue" : `Connect ${sourceLabel}`}
          </Button>
          {/* Secondary only shown when not already connected */}
          {!isConnected && (
            <Button
              type="button"
              variant="outline"
              className="flex-1"
              onClick={() => onReject("change_source")}
            >
              {cfg.secondaryLabel}
            </Button>
          )}
        </div>



      </CardContent>
    </Card>
  );
}

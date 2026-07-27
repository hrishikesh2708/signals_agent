"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { InterruptCardProps } from "@/components/chat/interrupts/interrupt-card-props";
import { connectSourceViaOAuth } from "@/lib/oauth-popup";

export function SourceConnectionInterruptCard({ payload, onApprove }: InterruptCardProps) {
  const sourceLabel = payload.source_label ?? "Source";
  const projectName = payload.project_name ?? "this project";
  const sourceId = payload.source_id as string | undefined;
  const projectId = payload.project_id as string | undefined;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleConnect() {
    if (!sourceId || !projectId) {
      setError("Missing source or project context.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await connectSourceViaOAuth(sourceId, projectId);
      if (result.success) {
        onApprove({ action: "connected", source_id: sourceId });
      } else {
        setError(result.error);
        setLoading(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
      setLoading(false);
    }
  }

  return (
    <Card className="border-[var(--border)] bg-[var(--card)] overflow-hidden shadow-sm">
      <CardContent className="p-3">
        <div className="flex rounded-md border border-[var(--border)]/60 overflow-hidden mb-3">
          <div className="w-1 shrink-0 bg-red-500" />
          <div className="px-4 py-3 space-y-0.5 flex-1 bg-red-500/[0.03]">
            <p className="text-sm font-semibold text-[var(--foreground)]">{sourceLabel}</p>
            <p className="text-sm text-[var(--muted-foreground)] leading-relaxed whitespace-pre-line">
              {`No active connection found for project ${projectName}\nI'll open the secure connect screen — your credentials\nstay on Datahash's existing authentication flow.`}
            </p>
            {error && (
              <p className="text-xs text-red-600 dark:text-red-400 mt-1">{error}</p>
            )}
          </div>
        </div>

        <div className="flex gap-2">
          <Button
            type="button"
            className="flex-1"
            disabled={loading}
            onClick={handleConnect}
          >
            {loading ? "Opening…" : `Connect ${sourceLabel}`}
          </Button>
          <Button type="button" variant="outline" className="flex-1" disabled>
            Use different source
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

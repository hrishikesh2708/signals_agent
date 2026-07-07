"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { InterruptCardProps } from "@/components/chat/interrupts/interrupt-card-props";
import { api } from "@/lib/api";

export function ConnectSourceInterruptCard({ payload, sessionId, onApprove }: InterruptCardProps) {
  const sourceLabel  = payload.source_label  ?? "Source";
  const connectorSlug = payload.connector_slug as string | undefined;
  const projectId    = payload.project_id    as string | undefined;
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);

  async function handleConnect() {
    if (!connectorSlug || !projectId) {
      setError("Missing connector or project context.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const { auth_url } = await api.authorizeConnection(connectorSlug, projectId, sessionId);

      // Open OAuth popup and wait for postMessage from callback
      const popup = window.open(auth_url, "oauth_popup", "width=600,height=700");
      if (!popup) {
        setError("Popup was blocked. Please allow popups for this site.");
        setLoading(false);
        return;
      }

      function onMessage(event: MessageEvent) {
        if (event.data?.type !== "oauth_complete") return;
        window.removeEventListener("message", onMessage);
        if (event.data.success) {
          onApprove({ action: "connected", connector_slug: connectorSlug });
        } else {
          setError(event.data.error ?? "Connection failed. Please try again.");
          setLoading(false);
        }
      }
      window.addEventListener("message", onMessage);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
      setLoading(false);
    }
  }

  return (
    <Card className="border-[var(--border)] bg-[var(--card)] overflow-hidden shadow-sm">
      <CardContent className="p-3">
        {/* Info block with red left border */}
        <div className="flex rounded-md border border-[var(--border)]/60 overflow-hidden mb-3">
          <div className="w-1 shrink-0 bg-red-500" />
          <div className="px-4 py-3 space-y-0.5 flex-1 bg-red-500/[0.03]">
            <p className="text-sm font-semibold text-[var(--foreground)]">{sourceLabel}</p>
            <p className="text-sm text-[var(--muted-foreground)] leading-relaxed">
              {(payload.message as string | undefined) ?? `Connect your ${sourceLabel} account to continue.`}
            </p>
            {error && (
              <p className="text-xs text-red-600 dark:text-red-400 mt-1">{error}</p>
            )}
          </div>
        </div>

        <Button
          type="button"
          className="w-full"
          disabled={loading}
          onClick={handleConnect}
        >
          {loading ? "Opening…" : `Connect ${sourceLabel}`}
        </Button>
      </CardContent>
    </Card>
  );
}

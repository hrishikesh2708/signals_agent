"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { InterruptCardProps } from "@/components/chat/interrupts/interrupt-card-props";
import type {
  SelectOption,
  CanonicalMappingRow,
  ChannelConnectionStatus,
  MappingDestination,
  MappingReviewRow,
  UnresolvedField,
} from "@/lib/interrupt-types";
import { api } from "@/lib/api";
import { CHANNEL_AVATAR_COLORS, MOCK_ONLY_SLUGS, META_SLUGS } from "@/components/chat/interrupts/platform-colors";

export function CheckChannelsInterruptCard({ payload, sessionId, onApprove }: InterruptCardProps) {
  const channels = (payload.channels ?? []) as ChannelConnectionStatus[];
  const pendingChannel = channels.find((ch) => ch.status !== "connected" && ch.status !== "skipped");
  const allSettled = !pendingChannel;

  const [connecting, setConnecting] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Mock metadata form state (for Meta)
  const [mockFormFor, setMockFormFor] = useState<string | null>(null);
  const [pixelId, setPixelId] = useState("123456789012345");
  const [adAccountId, setAdAccountId] = useState("act_mock_123");

  async function handleConnect(ch: ChannelConnectionStatus) {
    const connectorSlug = (ch as Record<string, unknown>).connector_slug as string | undefined ?? ch.id;
    const projectId = (ch as Record<string, unknown>).project_id as string | undefined;

    if (!connectorSlug || !projectId) {
      setErrors((e) => ({ ...e, [ch.id]: "Missing connector or project context." }));
      return;
    }

    setConnecting(ch.id);
    setErrors((e) => ({ ...e, [ch.id]: "" }));

    try {
      const { auth_url } = await api.authorizeConnection(connectorSlug, projectId, sessionId);
      const popup = window.open(auth_url, "oauth_popup", "width=600,height=700");
      if (!popup) {
        setErrors((e) => ({ ...e, [ch.id]: "Popup blocked — please allow popups and retry." }));
        setConnecting(null);
        return;
      }
      function onMessage(event: MessageEvent) {
        if (event.data?.type !== "oauth_complete") return;
        window.removeEventListener("message", onMessage);
        if (event.data.success) {
          onApprove({ action: "connected", platform_id: ch.id });
        } else {
          setErrors((ev) => ({ ...ev, [ch.id]: event.data.error ?? "Connection failed — please retry." }));
          setConnecting(null);
        }
      }
      window.addEventListener("message", onMessage);
    } catch (err) {
      setErrors((e) => ({ ...e, [ch.id]: err instanceof Error ? err.message : "Unexpected error" }));
      setConnecting(null);
    }
  }

  async function handleMockConnect(ch: ChannelConnectionStatus, overrides?: { pixelId?: string; adAccountId?: string }) {
    const connectorSlug = (ch as Record<string, unknown>).connector_slug as string | undefined ?? ch.id;
    const projectId = (ch as Record<string, unknown>).project_id as string | undefined;
    if (!connectorSlug || !projectId) return;

    setConnecting(ch.id);
    setMockFormFor(null);
    setErrors((e) => ({ ...e, [ch.id]: "" }));

    try {
      const body: Record<string, string> = {};
      if (overrides?.pixelId) body.pixel_id = overrides.pixelId;
      if (overrides?.adAccountId) body.ad_account_id = overrides.adAccountId;

      await api.mockConnectConnection(connectorSlug, projectId, body);
      onApprove({ action: "connected", platform_id: ch.id });
    } catch (err) {
      setErrors((e) => ({ ...e, [ch.id]: err instanceof Error ? err.message : "Mock connect failed" }));
      setConnecting(null);
    }
  }

  return (
    <Card className="border-[var(--border)] bg-[var(--card)]">
      <CardContent className="p-4 space-y-4">
        <p className="text-[10px] font-semibold tracking-widest text-[var(--muted-foreground)] uppercase">
          Destinations for this integration
        </p>

        <div className="space-y-2">
          {channels.map((ch) => {
            const isConnected = ch.status === "connected";
            const isSkipped = ch.status === "skipped";
            const isLoading = connecting === ch.id;
            const isMockOnly = MOCK_ONLY_SLUGS.has(ch.id) || MOCK_ONLY_SLUGS.has(
              (ch as Record<string, unknown>).connector_slug as string ?? ""
            );
            const avatarColor = CHANNEL_AVATAR_COLORS[ch.id] ?? "#6B7280";
            const initial = ch.label.charAt(0).toUpperCase();
            const showMetaForm = mockFormFor === ch.id;

            return (
              <div
                key={ch.id}
                className="rounded-xl border border-[var(--border)] bg-[var(--background)] overflow-hidden"
              >
                <div className="flex items-center gap-3 px-4 py-3">
                  {/* Platform avatar */}
                  <div
                    className="h-9 w-9 shrink-0 rounded-lg flex items-center justify-center text-white text-sm font-bold"
                    style={{ backgroundColor: avatarColor }}
                  >
                    {initial}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-[var(--foreground)]">{ch.label}</p>
                    {ch.detail && (
                      <p className="text-xs text-[var(--muted-foreground)] truncate">{ch.detail}</p>
                    )}
                    {isMockOnly && !isConnected && !isSkipped && (
                      <p className="text-[10px] text-amber-600 dark:text-amber-400 mt-0.5">
                        No live credentials — mock connect available
                      </p>
                    )}
                    {errors[ch.id] && (
                      <p className="text-xs text-red-500 mt-0.5">{errors[ch.id]}</p>
                    )}
                  </div>

                  {/* Status badge or action buttons */}
                  {isConnected ? (
                    <span className="shrink-0 rounded-full border border-green-500 px-3 py-1 text-xs font-medium text-green-600 dark:text-green-400">
                      Connected
                    </span>
                  ) : isSkipped ? (
                    <span className="shrink-0 rounded-full border border-[var(--border)] px-3 py-1 text-xs font-medium text-[var(--muted-foreground)]">
                      Skipped
                    </span>
                  ) : isMockOnly ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="shrink-0 border-amber-400 text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-950/30"
                      disabled={isLoading || connecting !== null}
                      onClick={() => {
                        if (META_SLUGS.has(ch.id) || META_SLUGS.has(
                          (ch as Record<string, unknown>).connector_slug as string ?? ""
                        )) {
                          setMockFormFor(showMetaForm ? null : ch.id);
                        } else {
                          void handleMockConnect(ch);
                        }
                      }}
                    >
                      {isLoading ? "Connecting…" : "Mock connect"}
                    </Button>
                  ) : (
                    <Button
                      type="button"
                      size="sm"
                      className="shrink-0"
                      disabled={isLoading || connecting !== null}
                      onClick={() => handleConnect(ch)}
                    >
                      {isLoading ? "Opening…" : "Connect"}
                    </Button>
                  )}
                </div>

                {/* Meta metadata form — shown inline when "Mock connect" clicked */}
                {showMetaForm && (
                  <div className="border-t border-[var(--border)] bg-[var(--secondary)]/40 px-4 py-3 space-y-3">
                    <p className="text-xs font-medium text-[var(--foreground)]">
                      Meta mock credentials
                    </p>
                    <div className="space-y-2">
                      <div>
                        <label className="text-[10px] font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                          Pixel ID
                        </label>
                        <input
                          type="text"
                          value={pixelId}
                          onChange={(e) => setPixelId(e.target.value)}
                          className="mt-1 w-full h-8 rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 text-sm text-[var(--foreground)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                          placeholder="123456789012345"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                          Ad Account ID
                        </label>
                        <input
                          type="text"
                          value={adAccountId}
                          onChange={(e) => setAdAccountId(e.target.value)}
                          className="mt-1 w-full h-8 rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 text-sm text-[var(--foreground)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                          placeholder="act_mock_123"
                        />
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        size="sm"
                        className="flex-1"
                        disabled={!pixelId.trim() || connecting !== null}
                        onClick={() => {
                          const ch = channels.find((c) => c.id === mockFormFor);
                          if (ch) void handleMockConnect(ch, { pixelId: pixelId.trim(), adAccountId: adAccountId.trim() });
                        }}
                      >
                        Save &amp; connect
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        className="flex-1"
                        onClick={() => setMockFormFor(null)}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Primary CTA */}
        {allSettled ? (
          <Button
            type="button"
            className="w-full bg-green-600 hover:bg-green-700 text-white"
            onClick={() => onApprove({ action: "confirm_all" })}
          >
            All settled — continue
          </Button>
        ) : (
          <div className="flex gap-2">
            <Button
              type="button"
              className="flex-1"
              disabled={connecting !== null}
              onClick={() => {
                if (!pendingChannel) return;
                const isMock = MOCK_ONLY_SLUGS.has(pendingChannel.id);
                if (isMock && META_SLUGS.has(pendingChannel.id)) {
                  setMockFormFor(pendingChannel.id);
                } else if (isMock) {
                  void handleMockConnect(pendingChannel);
                } else {
                  void handleConnect(pendingChannel);
                }
              }}
            >
              {connecting ? "Connecting…" : `Connect ${pendingChannel?.label ?? ""}`}
            </Button>
            <Button
              type="button"
              variant="outline"
              className="flex-1"
              disabled={connecting !== null}
              onClick={() => pendingChannel && onApprove({ action: "skip", platform_id: pendingChannel.id })}
            >
              Skip for now
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

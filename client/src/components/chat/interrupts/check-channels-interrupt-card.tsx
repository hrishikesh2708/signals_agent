"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { InterruptCardProps } from "@/components/chat/interrupts/interrupt-card-props";
import type { ChannelConnectionStatus } from "@/lib/interrupt-types";
import { api } from "@/lib/api";
import { connectDestinationViaOAuth } from "@/lib/oauth-popup";
import {
  CHANNEL_AVATAR_COLORS,
  GOOGLE_SLUGS,
  META_SLUGS,
} from "@/components/chat/interrupts/platform-colors";

function isMetaSlug(ch: ChannelConnectionStatus): boolean {
  const slug = ch.connector_slug ?? ch.id;
  return META_SLUGS.has(ch.id) || META_SLUGS.has(slug);
}

function isGoogleSlug(ch: ChannelConnectionStatus): boolean {
  const slug = ch.connector_slug ?? ch.id;
  return GOOGLE_SLUGS.has(ch.id) || GOOGLE_SLUGS.has(slug);
}

export function CheckChannelsInterruptCard({ payload, onApprove }: InterruptCardProps) {
  const channels = (payload.channels ?? []) as ChannelConnectionStatus[];
  const pendingChannel = channels.find(
    (ch) => ch.status !== "connected" && ch.status !== "skipped",
  );
  const connectedCount = channels.filter((ch) => ch.status === "connected").length;
  const allSettled = !pendingChannel;
  const canConfirm = allSettled && connectedCount >= 1;

  const [connecting, setConnecting] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [mockFormFor, setMockFormFor] = useState<string | null>(null);

  // Meta mock fields
  const [pixelId, setPixelId] = useState("123456789012345");
  const [accessToken, setAccessToken] = useState("");

  // Google mock fields
  const [refreshToken, setRefreshToken] = useState("");

  function connectorAndProject(ch: ChannelConnectionStatus): {
    connectorSlug: string;
    projectId: string;
  } | null {
    const connectorSlug = ch.connector_slug ?? ch.id;
    const projectId = ch.project_id;
    if (!connectorSlug || !projectId) return null;
    return { connectorSlug, projectId };
  }

  async function handleConnect(ch: ChannelConnectionStatus) {
    const ctx = connectorAndProject(ch);
    if (!ctx) {
      setErrors((e) => ({ ...e, [ch.id]: "Missing connector or project context." }));
      return;
    }

    setConnecting(ch.id);
    setErrors((e) => ({ ...e, [ch.id]: "" }));
    setMockFormFor(null);

    try {
      const result = await connectDestinationViaOAuth(ctx.connectorSlug, ctx.projectId);
      if (result.success) {
        onApprove({ action: "connected", platform_id: ch.id });
      } else {
        setErrors((e) => ({ ...e, [ch.id]: result.error }));
        setConnecting(null);
      }
    } catch (err) {
      setErrors((e) => ({
        ...e,
        [ch.id]: err instanceof Error ? err.message : "Unexpected error",
      }));
      setConnecting(null);
    }
  }

  async function handleMockConnect(
    ch: ChannelConnectionStatus,
    body: Record<string, string>,
  ) {
    const ctx = connectorAndProject(ch);
    if (!ctx) {
      setErrors((e) => ({ ...e, [ch.id]: "Missing connector or project context." }));
      return;
    }

    setConnecting(ch.id);
    setMockFormFor(null);
    setErrors((e) => ({ ...e, [ch.id]: "" }));

    try {
      await api.mockConnectDestination(ctx.connectorSlug, ctx.projectId, body);
      onApprove({ action: "connected", platform_id: ch.id });
    } catch (err) {
      setErrors((e) => ({
        ...e,
        [ch.id]: err instanceof Error ? err.message : "Mock connect failed",
      }));
      setConnecting(null);
    }
  }

  function openMockForm(ch: ChannelConnectionStatus) {
    setMockFormFor((current) => (current === ch.id ? null : ch.id));
    setErrors((e) => ({ ...e, [ch.id]: "" }));
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
            const avatarColor = CHANNEL_AVATAR_COLORS[ch.id] ?? "#6B7280";
            const initial = ch.label.charAt(0).toUpperCase();
            const showMockForm = mockFormFor === ch.id;
            const meta = isMetaSlug(ch);
            const google = isGoogleSlug(ch);

            return (
              <div
                key={ch.id}
                className="rounded-xl border border-[var(--border)] bg-[var(--background)] overflow-hidden"
              >
                <div className="flex items-center gap-3 px-4 py-3">
                  <div
                    className="h-9 w-9 shrink-0 rounded-lg flex items-center justify-center text-white text-sm font-bold"
                    style={{ backgroundColor: avatarColor }}
                  >
                    {initial}
                  </div>

                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-[var(--foreground)]">{ch.label}</p>
                    {ch.detail && (
                      <p className="text-xs text-[var(--muted-foreground)] truncate">{ch.detail}</p>
                    )}
                    {errors[ch.id] && (
                      <p className="text-xs text-red-500 mt-0.5">{errors[ch.id]}</p>
                    )}
                  </div>

                  {isConnected ? (
                    <span className="shrink-0 rounded-full border border-green-500 px-3 py-1 text-xs font-medium text-green-600 dark:text-green-400">
                      Connected
                    </span>
                  ) : isSkipped ? (
                    <span className="shrink-0 rounded-full border border-[var(--border)] px-3 py-1 text-xs font-medium text-[var(--muted-foreground)]">
                      Skipped
                    </span>
                  ) : (
                    <div className="flex shrink-0 gap-2">
                      <Button
                        type="button"
                        size="sm"
                        disabled={isLoading || connecting !== null}
                        onClick={() => void handleConnect(ch)}
                      >
                        {isLoading ? "Opening…" : "Connect"}
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        disabled={isLoading || connecting !== null}
                        onClick={() => openMockForm(ch)}
                      >
                        Mock
                      </Button>
                    </div>
                  )}
                </div>

                {showMockForm && meta && (
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
                          Meta access token
                        </label>
                        <input
                          type="password"
                          value={accessToken}
                          onChange={(e) => setAccessToken(e.target.value)}
                          className="mt-1 w-full h-8 rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 text-sm text-[var(--foreground)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                          placeholder="EAAB…"
                        />
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        size="sm"
                        className="flex-1"
                        disabled={
                          !pixelId.trim() || !accessToken.trim() || connecting !== null
                        }
                        onClick={() => {
                          void handleMockConnect(ch, {
                            pixel_id: pixelId.trim(),
                            access_token: accessToken.trim(),
                          });
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

                {showMockForm && google && (
                  <div className="border-t border-[var(--border)] bg-[var(--secondary)]/40 px-4 py-3 space-y-3">
                    <p className="text-xs font-medium text-[var(--foreground)]">
                      Google mock credentials
                    </p>
                    <div>
                      <label className="text-[10px] font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                        Refresh token
                      </label>
                      <input
                        type="password"
                        value={refreshToken}
                        onChange={(e) => setRefreshToken(e.target.value)}
                        className="mt-1 w-full h-8 rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 text-sm text-[var(--foreground)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                        placeholder="1//…"
                      />
                    </div>
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        size="sm"
                        className="flex-1"
                        disabled={!refreshToken.trim() || connecting !== null}
                        onClick={() => {
                          void handleMockConnect(ch, {
                            refresh_token: refreshToken.trim(),
                          });
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

                {showMockForm && !meta && !google && (
                  <div className="border-t border-[var(--border)] bg-[var(--secondary)]/40 px-4 py-3">
                    <p className="text-xs text-[var(--muted-foreground)]">
                      Mock connect is not configured for this destination.
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {canConfirm ? (
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
              disabled={connecting !== null || !pendingChannel}
              onClick={() => {
                if (!pendingChannel) return;
                void handleConnect(pendingChannel);
              }}
            >
              {connecting
                ? "Connecting…"
                : `Connect ${pendingChannel?.label ?? ""}`}
            </Button>
            <Button
              type="button"
              variant="outline"
              className="flex-1"
              disabled={connecting !== null || !pendingChannel}
              onClick={() =>
                pendingChannel &&
                onApprove({ action: "skip", platform_id: pendingChannel.id })
              }
            >
              Skip for now
            </Button>
          </div>
        )}

        {allSettled && connectedCount === 0 && (
          <p className="text-xs text-amber-600 dark:text-amber-400">
            Connect at least one destination to continue. Skipped destinations stay deferred.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

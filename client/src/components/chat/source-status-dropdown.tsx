"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useProject } from "@/components/project/project-context";
import { api } from "@/lib/api";
import { connectSourceViaOAuth } from "@/lib/oauth-popup";
import { cn } from "@/lib/utils";

const SOURCES = [
  { id: "salesforce", label: "Salesforce" },
  { id: "hubspot", label: "HubSpot" },
  { id: "zoho", label: "Zoho CRM" },
] as const;

type SourceId = (typeof SOURCES)[number]["id"];

type StatusMap = Partial<Record<SourceId, boolean>>;

export function SourceStatusDropdown() {
  const { project } = useProject();
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [statuses, setStatuses] = useState<StatusMap>({});
  const [loading, setLoading] = useState(false);
  const [connectingId, setConnectingId] = useState<SourceId | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshStatuses = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const results = await Promise.all(
        SOURCES.map(async (source) => {
          const status = await api.getSourceConnectionStatus(
            source.id,
            project.id,
          );
          return [source.id, status.connected] as const;
        }),
      );
      setStatuses(Object.fromEntries(results));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load status");
    } finally {
      setLoading(false);
    }
  }, [project.id]);

  useEffect(() => {
    if (!open) return;
    void refreshStatuses();
  }, [open, refreshStatuses]);

  useEffect(() => {
    if (!open) return;

    function onPointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }

    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  async function handleConnect(sourceId: SourceId) {
    if (connectingId) return;

    setConnectingId(sourceId);
    setError(null);

    try {
      const result = await connectSourceViaOAuth(sourceId, project.id);
      if (result.success) {
        await refreshStatuses();
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setConnectingId(null);
    }
  }

  const connectedCount = SOURCES.filter((s) => statuses[s.id] === true).length;
  const knownCount = SOURCES.filter((s) => statuses[s.id] !== undefined).length;

  return (
    <div ref={rootRef} className="relative">
      <Button
        type="button"
        variant="outline"
        size="sm"
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((prev) => !prev)}
      >
        Sources
        {knownCount > 0 ? (
          <span className="text-[var(--muted-foreground)]">
            {connectedCount}/{SOURCES.length}
          </span>
        ) : null}
      </Button>

      {open ? (
        <div
          role="menu"
          className="absolute right-0 z-50 mt-1.5 w-56 overflow-hidden rounded-[var(--radius)] border border-[var(--border)] bg-[var(--background)] shadow-md"
        >
          <div className="border-b border-[var(--border)] px-3 py-2">
            <p className="text-xs text-[var(--muted-foreground)]">
              Project connections
            </p>
          </div>

          {loading && Object.keys(statuses).length === 0 ? (
            <div className="flex items-center gap-2 px-3 py-3 text-sm text-[var(--muted-foreground)]">
              <Spinner size="sm" />
              Checking…
            </div>
          ) : (
            <ul className="py-1">
              {SOURCES.map((source) => {
                const connected = statuses[source.id] === true;
                const isConnecting = connectingId === source.id;
                const statusKnown = statuses[source.id] !== undefined;

                return (
                  <li key={source.id}>
                    <button
                      type="button"
                      role="menuitem"
                      disabled={!!connectingId}
                      onClick={() => {
                        void handleConnect(source.id);
                      }}
                      className={cn(
                        "flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm transition-colors cursor-pointer hover:bg-[var(--secondary)]",
                        connectingId && !isConnecting && "opacity-50",
                      )}
                    >
                      <span
                        aria-hidden
                        className={cn(
                          "h-2 w-2 shrink-0 rounded-full",
                          !statusKnown && "bg-[var(--muted-foreground)]/40",
                          statusKnown && connected && "bg-green-500",
                          statusKnown && !connected && "bg-red-500",
                        )}
                      />
                      <span className="min-w-0 flex-1 truncate font-medium">
                        {source.label}
                      </span>
                      {isConnecting ? (
                        <Spinner size="sm" />
                      ) : connected ? (
                        <span className="text-xs text-[var(--muted-foreground)]">
                          Connected
                        </span>
                      ) : (
                        <span className="text-xs text-[var(--muted-foreground)]">
                          Connect
                        </span>
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}

          {error ? (
            <p className="border-t border-[var(--border)] px-3 py-2 text-xs text-red-600 dark:text-red-400">
              {error}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

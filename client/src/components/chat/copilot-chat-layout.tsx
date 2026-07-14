"use client";

import { useCallback, useLayoutEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { DatahashLogoMark } from "@/components/ui/datahash-logo-mark";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const NEAR_BOTTOM_PX = 80;

export type ChatScrollApi = {
  /** Scroll to bottom if the user is already near the bottom (or force). */
  stickToBottom: (force?: boolean) => void;
};

export function CopilotChatLayout({
  children,
  draft = "",
  onDraftChange,
  onSubmit,
  inputDisabled = false,
  inputPlaceholder = "Message Signals Copilot…",
  projectName,
  headerActions,
  banner,
  footerExtra,
  stepInfo,
  scrollApiRef,
}: {
  children?: React.ReactNode;
  draft?: string;
  onDraftChange?: (value: string) => void;
  onSubmit?: (e: React.FormEvent) => void;
  inputDisabled?: boolean;
  inputPlaceholder?: string;
  projectName?: string;
  headerActions?: React.ReactNode;
  banner?: React.ReactNode;
  footerExtra?: React.ReactNode;
  stepInfo?: { step: number; total: number; label: string } | null;
  scrollApiRef?: React.MutableRefObject<ChatScrollApi | null>;
}) {
  const scrollerRef = useRef<HTMLDivElement>(null);
  const pinnedToBottomRef = useRef(true);

  const stickToBottom = useCallback((force = false) => {
    const el = scrollerRef.current;
    if (!el) return;
    if (!force && !pinnedToBottomRef.current) return;

    pinnedToBottomRef.current = true;
    requestAnimationFrame(() => {
      const node = scrollerRef.current;
      if (!node) return;
      node.scrollTop = node.scrollHeight;
    });
  }, []);

  const onScrollerScroll = useCallback(() => {
    const el = scrollerRef.current;
    if (!el) return;
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
    pinnedToBottomRef.current = distance <= NEAR_BOTTOM_PX;
  }, []);

  useLayoutEffect(() => {
    if (!scrollApiRef) return;
    scrollApiRef.current = { stickToBottom };
    return () => {
      scrollApiRef.current = null;
    };
  }, [scrollApiRef, stickToBottom]);

  const stepSubtitle = stepInfo
    ? `Step ${stepInfo.step} of ${stepInfo.total} · ${stepInfo.label}`
    : "Ready to set up your pipeline";

  return (
    <div className="flex h-full min-h-0 flex-col bg-[var(--background)]">
      <header className="shrink-0 border-b border-[var(--border)]">
        <div className="mx-auto flex w-full max-w-4xl items-center justify-between gap-4 px-6 py-4">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <DatahashLogoMark size="md" />
            <div className="min-w-0">
              <h1 className="truncate text-lg font-semibold text-[var(--foreground)]">
                Signals Setup Copilot
              </h1>
              <p className="text-sm text-[var(--muted-foreground)] transition-all duration-300">
                {stepSubtitle}
              </p>
            </div>
          </div>
          {(headerActions || projectName) ? (
            <div className="ml-auto flex shrink-0 items-center gap-4">
              {headerActions}
              {projectName ? (
                <div className="text-right">
                  <p className="text-xs text-[var(--muted-foreground)]">Project</p>
                  <p
                    className="max-w-[12rem] truncate text-sm font-medium text-[var(--foreground)] sm:max-w-[16rem]"
                    title={projectName}
                  >
                    {projectName}
                  </p>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </header>

      {banner ? (
        <div className="shrink-0 border-b border-[var(--border)] bg-[var(--secondary)]/40 px-6 py-2">
          <div className="mx-auto max-w-4xl text-sm text-[var(--muted-foreground)]">
            {banner}
          </div>
        </div>
      ) : null}

      <div
        ref={scrollerRef}
        className="flex-1 overflow-y-auto"
        onScroll={onScrollerScroll}
      >
        <div className="mx-auto w-full max-w-4xl space-y-4 px-6 py-4">
          {children ?? (
            <p className="text-sm text-[var(--muted-foreground)]">
              Try: &quot;Map my Salesforce leads to Meta ads.&quot;
            </p>
          )}
        </div>
      </div>

      <footer className="shrink-0 border-t border-[var(--border)]">
        <div className="mx-auto w-full max-w-4xl space-y-3 px-6 py-4">
          {footerExtra}
          <form
            onSubmit={onSubmit}
            className="flex gap-2"
          >
            <Input
              value={draft}
              onChange={(e) => onDraftChange?.(e.target.value)}
              placeholder={inputPlaceholder}
              disabled={inputDisabled}
              className="flex-1"
            />
            <Button
              type="submit"
              disabled={inputDisabled || !draft.trim()}
            >
              ↑
            </Button>
          </form>
        </div>
      </footer>
    </div>
  );
}

export function CopilotOfflineBanner({
  message,
  className,
}: {
  message: string;
  className?: string;
}) {
  return (
    <p className={cn("text-sm", className)}>
      <span className="font-medium text-[var(--foreground)]">Preview mode.</span>{" "}
      {message}
    </p>
  );
}

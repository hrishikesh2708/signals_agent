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

function ProjectChip({
  projectName,
  onSwitchProject,
  disabled = false,
}: {
  projectName: string;
  onSwitchProject?: () => void;
  disabled?: boolean;
}) {
  const body = (
    <>
      <span className="text-xs leading-none text-[var(--muted-foreground)]">
        Project
      </span>
      <span className="flex min-w-0 items-center gap-1.5">
        <span
          className="max-w-[10rem] truncate text-sm font-medium text-[var(--foreground)] sm:max-w-[14rem]"
          title={projectName}
        >
          {projectName}
        </span>
        {onSwitchProject ? (
          <svg
            aria-hidden
            viewBox="0 0 12 12"
            className="h-3 w-3 shrink-0 text-[var(--muted-foreground)]"
          >
            <path
              d="M2.5 4.5 6 8l3.5-3.5"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        ) : null}
      </span>
    </>
  );

  const chipClass = cn(
    "flex min-w-0 flex-col items-start gap-1 rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-left",
    onSwitchProject &&
      "transition-colors hover:bg-[var(--secondary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]",
    onSwitchProject && disabled && "pointer-events-none opacity-50",
  );

  if (onSwitchProject) {
    return (
      <button
        type="button"
        className={chipClass}
        onClick={onSwitchProject}
        disabled={disabled}
        aria-label={`Switch project (current: ${projectName})`}
      >
        {body}
      </button>
    );
  }

  return <div className={chipClass}>{body}</div>;
}

export function CopilotChatLayout({
  children,
  draft = "",
  onDraftChange,
  onSubmit,
  inputDisabled = false,
  inputPlaceholder = "Message Signals Copilot…",
  projectName,
  onSwitchProject,
  projectSwitchDisabled = false,
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
  onSwitchProject?: () => void;
  projectSwitchDisabled?: boolean;
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
            <div className="ml-auto flex shrink-0 items-center gap-2">
              {headerActions}
              {projectName ? (
                <ProjectChip
                  projectName={projectName}
                  onSwitchProject={onSwitchProject}
                  disabled={projectSwitchDisabled}
                />
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

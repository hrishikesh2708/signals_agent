"use client";

import { cn } from "@/lib/utils";

export function SidebarFooter({ collapsed }: { collapsed: boolean }) {
  if (collapsed) {
    return (
      <div className="flex flex-col items-center gap-2 border-t border-[var(--border)] px-2 py-3">
        <span
          title="Signals dev"
          className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--secondary)] text-xs font-medium text-[var(--secondary-foreground)]"
        >
          S
        </span>
      </div>
    );
  }

  return (
    <div className={cn("border-t border-[var(--border)] px-3 py-3")}>
      <p className="text-xs text-[var(--muted-foreground)]">
        Dev sandboxes available in the sidebar while auth is pending.
      </p>
    </div>
  );
}

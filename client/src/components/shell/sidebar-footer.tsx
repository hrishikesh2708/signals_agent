"use client";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/contexts/auth-context";
import { clearProject } from "@/lib/project-storage";
import { clearSession } from "@/lib/session-storage";
import { cn } from "@/lib/utils";

function userDisplayName(email?: string, name?: string): string {
  if (email) return email;
  if (name) return name;
  return "Signed in";
}

function userInitial(email?: string, name?: string): string {
  const source = email ?? name ?? "?";
  return source.charAt(0).toUpperCase();
}

export function SidebarFooter({ collapsed }: { collapsed: boolean }) {
  const router = useRouter();
  const { user, loading, logout } = useAuth();

  const displayName = userDisplayName(user?.email, user?.name);

  async function onLogout() {
    try {
      await logout();
    } finally {
      clearSession();
      clearProject();
      router.replace("/login");
    }
  }

  if (collapsed) {
    return (
      <div className="flex flex-col items-center gap-2 border-t border-[var(--border)] px-2 py-3">
        <span
          title={displayName}
          className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--secondary)] text-xs font-medium text-[var(--secondary-foreground)]"
        >
          {loading ? "…" : userInitial(user?.email, user?.name)}
        </span>
        <Button
          variant="ghost"
          size="icon"
          onClick={onLogout}
          aria-label="Sign out"
          className="h-8 w-8"
          title="Sign out"
        >
          ⎋
        </Button>
      </div>
    );
  }

  return (
    <div className={cn("border-t border-[var(--border)] px-3 py-3")}>
      <div className="mb-3 min-w-0">
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-[var(--muted-foreground)]">
            <Spinner size="sm" />
            Loading…
          </div>
        ) : (
          <>
            <p className="truncate text-sm font-medium text-[var(--foreground)]">
              {displayName}
            </p>
            {user?.name && user.email ? (
              <p className="truncate text-xs text-[var(--muted-foreground)]">
                {user.name}
              </p>
            ) : null}
          </>
        )}
      </div>
      <Button variant="outline" size="sm" onClick={onLogout} className="w-full">
        Sign out
      </Button>
    </div>
  );
}

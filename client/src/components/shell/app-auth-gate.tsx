"use client";

import { usePathname } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/contexts/auth-context";

function AuthLoadingState({ message }: { message: string }) {
  return (
    <div className="flex h-full min-h-[50vh] items-center justify-center gap-2 text-sm text-[var(--muted-foreground)]">
      <Spinner size="sm" />
      {message}
    </div>
  );
}

/**
 * Client-side backup for app routes — redirects to login when the session
 * cookie is missing or /api/auth/me returns no user.
 */
export function AppAuthGate({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { user, loading } = useAuth();

  useEffect(() => {
    if (loading || user) return;

    const next = pathname && pathname.startsWith("/") ? pathname : "/chat";
    const loginUrl = `/login?next=${encodeURIComponent(next)}`;
    window.location.replace(loginUrl);
  }, [loading, user, pathname]);

  if (loading) {
    return <AuthLoadingState message="Loading…" />;
  }

  if (!user) {
    return <AuthLoadingState message="Redirecting to sign in…" />;
  }

  return children;
}

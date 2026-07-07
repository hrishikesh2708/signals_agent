"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/contexts/auth-context";

/**
 * Client-side backup for app routes — redirects to login when the session
 * cookie is missing or /api/auth/me returns no user.
 */
export function AppAuthGate({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, loading } = useAuth();

  useEffect(() => {
    if (!loading && !user) {
      const next = pathname && pathname.startsWith("/") ? pathname : "/chat";
      router.replace(`/login?next=${encodeURIComponent(next)}`);
    }
  }, [loading, user, pathname, router]);

  if (loading) {
    return (
      <div className="flex h-full min-h-[50vh] items-center justify-center gap-2 text-sm text-[var(--muted-foreground)]">
        <Spinner size="sm" />
        Loading…
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return children;
}

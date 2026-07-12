import { Suspense } from "react";

import { LoginForm } from "@/components/auth/login-form";
import { Spinner } from "@/components/ui/spinner";

function LoginLoadingFallback() {
  return (
    <div className="flex min-h-[12rem] items-center justify-center gap-2 text-sm text-[var(--muted-foreground)]">
      <Spinner size="sm" />
      Loading…
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginLoadingFallback />}>
      <LoginForm />
    </Suspense>
  );
}

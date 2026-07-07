import { AppAuthGate } from "@/components/shell/app-auth-gate";
import { ShellLayout } from "@/components/shell/shell-layout";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AppAuthGate>
      <ShellLayout>{children}</ShellLayout>
    </AppAuthGate>
  );
}

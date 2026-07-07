"use client";

export function MappingStatusDot({ status }: { status: string }) {
  const cls =
    status === "confident"   ? "bg-green-500" :
    status === "needs_input" ? "bg-amber-500" :
    status === "missing"     ? "bg-red-500"   : "";
  if (!cls) return null;
  return <span className={`h-2.5 w-2.5 rounded-full shrink-0 inline-block ${cls}`} />;
}

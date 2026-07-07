"use client";

import { Card, CardContent } from "@/components/ui/card";
import type { ErrorMessage } from "@/lib/parse-agent-message";

export function ErrorCard({ data }: { data: ErrorMessage }) {
  return (
    <Card className="w-full max-w-lg overflow-hidden border-[var(--border)] bg-[var(--card)] shadow-sm">
      <div className="flex">
        <div className="w-1 shrink-0 bg-red-500" />

        <CardContent className="flex-1 space-y-1 p-4">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-semibold tracking-widest text-red-600 uppercase dark:text-red-400">
              Error
            </span>
          </div>
          <p className="text-sm font-semibold text-[var(--foreground)]">
            {data.title}
          </p>
          <p className="text-sm text-[var(--muted-foreground)]">{data.message}</p>
        </CardContent>
      </div>
    </Card>
  );
}

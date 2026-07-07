"use client";

import type { ThinkingMessage } from "@/lib/parse-agent-message";

export function ThinkingCard({ data }: { data: ThinkingMessage }) {
  return (
    <div className="flex max-w-[85%] items-center gap-3">
      <div className="flex shrink-0 items-center gap-[3px]">
        {[0, 150, 300].map((delay) => (
          <span
            key={delay}
            className="h-[5px] w-[5px] animate-bounce rounded-full bg-[var(--muted-foreground)]/50"
            style={{ animationDelay: `${delay}ms` }}
          />
        ))}
      </div>

      <p className="text-sm leading-snug italic text-[var(--muted-foreground)]">
        {data.message}
      </p>

      {data.step !== undefined && data.total_steps !== undefined && (
        <span className="ml-auto shrink-0 rounded-full border border-[var(--border)] bg-[var(--muted)] px-2 py-0.5 text-[10px] font-medium text-[var(--muted-foreground)]">
          {data.step}/{data.total_steps}
        </span>
      )}
    </div>
  );
}

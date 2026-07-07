/**
 * ╔══════════════════════════════════════════════════════════════════════════╗
 * ║  DEV PREVIEW — DELETE THIS FILE when the agent is ready to emit         ║
 * ║  real `on_interrupt` events via CopilotKit.                             ║
 * ║                                                                         ║
 * ║  Route: /interrupt-dev                                                  ║
 * ║  Shows all interrupt card variants in sequence with mock data           ║
 * ║  so you can iterate on UI without a live agent.                         ║
 * ╚══════════════════════════════════════════════════════════════════════════╝
 *
 * BACKEND CONTRACT — what your LangGraph agent should emit for each type:
 *
 * interrupt("on_interrupt", {
 *
 *   // 1 — pick ad platforms (multi-select)
 *   type: "select_channels",
 *   options: [{ id, label, enabled }],   // enabled: false = "coming soon"
 *   min_select?: 1,
 *   default_selected?: string[],          // pre-selected IDs
 *   // → resume: { selected: string[] }
 *
 *   // 2 — pick CRM (single-select)
 *   type: "select_source",
 *   options: [{ id, label, enabled }],   // enabled: false = "coming soon"
 *   default_selected?: string,            // pre-selected ID
 *   // → resume: { selected: string }
 *
 *   // 3 — check source connection (3 variants)
 *   type: "check_connection",
 *   source_label: string,                 // e.g. "Salesforce"
 *   connection_status: "not_connected" | "expired" | "connected",
 *   message: string,                      // status description (stays in payload)
 *   account_detail?: string,              // e.g. "Acme Corp · john@acme.com" — connected only
 *   // → resume: onApprove({ action: "connect" }) | onReject("change_source")
 *
 *   // (remaining interrupts documented below each mock in FE-5 commits)
 * })
 *
 * Resume response shape (returned via command.resume):
 *   select_channels    → { selected: string[] }
 *   select_source      → { selected: string }
 *   check_connection   → { action: "connect" } | reject("change_source")
 *   select_object      → { selected: string }
 *   check_channels     → { action: "confirm_all" | "connect" | "skip", platform_id?: string }
 *   mapping_review     → { approved: true, rows: [...] } | { approved: false }
 *   canonical_mapping  → { approved: true } | { approved: true, skip_hints: true }
 *   resolve_fields     → { action: "submit", resolutions: [...] } OR { action: "confirm" }
 *   activate_confirm   → { action: "activate" } | reject("review_matrix")
 *   confirm_run        → { approved: true, reason?: "..." } | { approved: false, reason?: "..." }
 *   generic            → { approved: true, reason?: "..." } | { approved: false, reason?: "..." }
 */

"use client";

type Stage = {
  label: string;
  tag: string;
  node: React.ReactNode;
};

const STAGES: Stage[] = [];

export default function InterruptDevPage() {
  return (
    <div className="h-full overflow-y-auto bg-[var(--background)] px-6 py-8">
      <div className="mx-auto mb-8 max-w-2xl rounded-lg border border-dashed border-red-400/60 bg-red-500/5 px-4 py-3">
        <p className="text-sm font-semibold text-red-600 dark:text-red-400">
          DEV PREVIEW — delete{" "}
          <code className="font-mono">src/app/(app)/interrupt-dev/</code> when
          your agent emits real interrupts
        </p>
        <p className="mt-1 text-xs text-[var(--muted-foreground)]">
          Interrupt card gallery — add components in FE-5.x commits. Backend
          contract documented in the page file.
        </p>
      </div>

      <div className="mx-auto max-w-2xl space-y-10">
        {STAGES.length === 0 ? (
          <p className="text-sm text-[var(--muted-foreground)]">
            No interrupt cards yet. Stages appear here as FE-5 components land.
          </p>
        ) : (
          STAGES.map((stage, index) => (
            <section key={`${stage.tag}-${index}`}>
              <div className="mb-3 flex items-center gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--secondary)] text-xs font-bold text-[var(--foreground)]">
                  {index + 1}
                </span>
                <div>
                  <p className="text-sm font-semibold text-[var(--foreground)]">
                    {stage.label}
                  </p>
                  <code className="text-xs text-[var(--muted-foreground)]">
                    type: &quot;{stage.tag}&quot;
                  </code>
                </div>
              </div>

              <div className="flex flex-col gap-2">{stage.node}</div>
            </section>
          ))
        )}
      </div>
    </div>
  );
}

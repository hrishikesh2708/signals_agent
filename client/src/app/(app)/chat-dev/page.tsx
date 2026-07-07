/**
 * ╔══════════════════════════════════════════════════════════════════════════╗
 * ║  DEV PREVIEW — DELETE THIS FILE when the agent emits real messages.     ║
 * ║                                                                         ║
 * ║  Route: /chat-dev                                                       ║
 * ║  Shows all chat message components (existing + new) with mock data      ║
 * ║  so you can iterate on UI without a live agent.                         ║
 * ╚══════════════════════════════════════════════════════════════════════════╝
 *
 * BACKEND CONTRACT — what your LangGraph agent should emit for each type:
 *
 * Agent messages are regular assistant messages containing a JSON string:
 *
 *   // Thinking / in-progress
 *   { "type": "thinking", "message": "Analyzing your Salesforce schema…", "step": 1, "total_steps": 4 }
 *
 *   // Step confirmed
 *   { "type": "step_complete", "message": "Meta + Google selected as destinations", "detail": "Optional sub-text" }
 *
 *   // CRM schema discovered
 *   { "type": "schema_summary", "source_label": "Salesforce", "source_object": "Opportunity",
 *     "total_fields": 47, "required_fields": 12, "sample_fields": ["Email", "Phone", ...] }
 *
 *   // Pipeline live
 *   { "type": "pipeline_activated", "pipeline_name": "Acme Prod — Opp → Meta + Google",
 *     "source_label": "Salesforce", "source_object": "Opportunity",
 *     "channels": ["Meta CAPI", "Google Offline"], "total_fields": 47, "mapped_fields": 44 }
 *
 *   // Error
 *   { "type": "error", "title": "Connection failed", "message": "Could not reach Salesforce API." }
 *
 *   // Warning
 *   { "type": "warning", "title": "3 fields unmapped", "message": "You'll review these in the next step." }
 *
 *   // Intent acknowledged (existing)
 *   { "type": "intent_ack", "run_mode": "Offline conversion",
 *     "sources": ["Salesforce"], "source_object": ["Opportunity"], "channels": ["Meta", "Google"] }
 *
 *   // Agent event (existing)
 *   { "type": "agent_event", "message": "...",
 *     "status": "in_progress"|"done", "step_index": 2, "step_total": 9, "event"?: "schema_fetched" }
 *
 *   // Mapping complete (existing)
 *   { "type": "mapping_complete", "summary": "...", "source_label": "Salesforce",
 *     "source_object": "Opportunity", "channels": ["Meta CAPI"],
 *     "mappings": [...], "stats": { "total": 10, "auto_approved": 8, "human_reviewed": 2 } }
 *     // channels: [] = canonical layer mapping
 */

"use client";

type Section = { label: string; tag: string; node: React.ReactNode };

const SECTIONS: Section[] = [];

export default function ChatDevPage() {
  return (
    <div className="h-full overflow-y-auto bg-[var(--background)] px-6 py-8">
      <div className="mx-auto mb-8 max-w-2xl rounded-lg border border-dashed border-red-400/60 bg-red-500/5 px-4 py-3">
        <p className="text-sm font-semibold text-red-600 dark:text-red-400">
          DEV PREVIEW — delete{" "}
          <code className="font-mono">src/app/(app)/chat-dev/</code> when your
          agent emits real messages
        </p>
        <p className="mt-1 text-xs text-[var(--muted-foreground)]">
          Message card gallery — add components in FE-4.x commits. Backend
          contract documented in the page file.
        </p>
      </div>

      <div className="mx-auto max-w-2xl space-y-10">
        {SECTIONS.length === 0 ? (
          <p className="text-sm text-[var(--muted-foreground)]">
            No message cards yet. Sections appear here as FE-4 components land.
          </p>
        ) : (
          SECTIONS.map((section, index) => (
            <section key={`${section.tag}-${index}`}>
              <div className="mb-3 flex items-center gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--secondary)] text-xs font-bold text-[var(--foreground)]">
                  {index + 1}
                </span>
                <div>
                  <p className="text-sm font-semibold text-[var(--foreground)]">
                    {section.label}
                  </p>
                  <code className="text-xs text-[var(--muted-foreground)]">
                    type: &quot;{section.tag}&quot;
                  </code>
                </div>
              </div>

              <div className="flex flex-col gap-2">{section.node}</div>
            </section>
          ))
        )}
      </div>
    </div>
  );
}

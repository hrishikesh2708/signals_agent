/**
 * ╔══════════════════════════════════════════════════════════════════════════╗
 * ║  DEV PREVIEW — DELETE THIS FILE when the agent is ready to emit         ║
 * ║  real `on_interrupt` events via CopilotKit.                             ║
 * ║                                                                         ║
 * ║  Route: /interrupt-dev                                                  ║
 * ║  Top: intent_clarify gallery (source / signal_type / channels).         ║
 * ║  Below: remaining interrupt card previews.                              ║
 * ╚══════════════════════════════════════════════════════════════════════════╝
 *
 * Live clarify contract (`build_clarify_payload`):
 *   type: "intent_clarify"
 *   field: "source" | "signal_type" | "channels"
 *   title, subtitle, required, multi
 *   options: [{ id, label, enabled, description? }]
 *   context, attempt, max_attempts
 *   → resume: { selected: "<id>" } | { selected: ["id", ...] }
 */

"use client";

import { useState } from "react";
import { HitlApprovalCard } from "@/components/chat/interrupts/hitl-approval-card";
import type { ApprovalInterruptPayload } from "@/lib/interrupt-types";
import { loadStoredSessionId } from "@/lib/session-storage";

// ── intent_clarify mocks (BE-shaped) ───────────────────────────────────────

const MOCK_CLARIFY_SOURCE: ApprovalInterruptPayload = {
  type: "intent_clarify",
  field: "source",
  title: "Select a data source",
  subtitle: "Choose which CRM or data source to connect.",
  required: true,
  multi: false,
  options: [
    { id: "salesforce", label: "Salesforce", enabled: true },
    { id: "hubspot", label: "HubSpot", enabled: true },
    { id: "zoho", label: "Zoho CRM", enabled: true },
  ],
  context: { source: null, signal_type: null, channels: [] },
  attempt: 1,
  max_attempts: 3,
};

const MOCK_CLARIFY_SIGNAL_TYPE: ApprovalInterruptPayload = {
  type: "intent_clarify",
  field: "signal_type",
  title: "Confirm the signal type",
  subtitle: "v1 supports offline conversions — confirm before choosing destinations.",
  required: true,
  multi: false,
  options: [
    { id: "offline_conversion", label: "Offline Conversion", enabled: true },
    { id: "web_conversion", label: "Web Conversion", enabled: false, description: "Not available" },
    { id: "lead_conversion", label: "Lead Conversion", enabled: false, description: "Not available" },
    { id: "audience", label: "Audience", enabled: true },
  ],
  context: { source: "salesforce", signal_type: null, channels: [] },
  attempt: 1,
  max_attempts: 3,
};

const MOCK_CLARIFY_CHANNELS: ApprovalInterruptPayload = {
  type: "intent_clarify",
  field: "channels",
  title: "Select ad destinations",
  subtitle: "Choose which ad platforms should receive this data.",
  required: true,
  multi: true,
  options: [
    { id: "meta", label: "Meta", enabled: true },
    { id: "google", label: "Google", enabled: true },
  ],
  context: { source: "salesforce", signal_type: "offline_conversion", channels: [] },
  attempt: 1,
  max_attempts: 3,
};

const CLARIFY_MOCKS: { label: string; field: string; payload: ApprovalInterruptPayload }[] = [
  { label: "Source", field: "source", payload: MOCK_CLARIFY_SOURCE },
  { label: "Signal type", field: "signal_type", payload: MOCK_CLARIFY_SIGNAL_TYPE },
  { label: "Channels", field: "channels", payload: MOCK_CLARIFY_CHANNELS },
];

// ── Legacy mocks (demoted) ─────────────────────────────────────────────────

// ── select_object (legacy) ────────────────────────────────────────────────
const MOCK_SELECT_OBJECT: ApprovalInterruptPayload = {
  type: "select_object",
  requested: "opportunity",
  options: ["Opportunity", "Lead", "Contact", "Account", "Campaign", "CampaignMember"],
};


const SF_OPPORTUNITY_FIELDS = [
  "Contact.Email", "Contact.Phone", "Amount", "CloseDate",
  "StageName", "StageName=Closed Won", "GCLID", "AnnualRevenue",
  "AccountId", "OwnerId", "LeadSource", "— constant —",
];

// ── 6. mapping_review (2 variants) ───────────────────────────────────────
// Agent sends a plain chat message first, then fires this interrupt.
// source_fields powers the per-row source dropdown — send the full object field list.
// cells keyed by destination id; status drives the colour dot.
//
// Inbound:  { type, source_object, source_fields, destinations, rows }
// Outbound: { approved: true, rows: MappingReviewRow[] }   // rows with user overrides
//           onReject("edit_mapping")

// Variant A — single destination, one needs_input
const MOCK_MAPPING_REVIEW_SINGLE: ApprovalInterruptPayload = {
  type: "mapping_review",
  source_object: "Salesforce Opportunity",
  source_fields: SF_OPPORTUNITY_FIELDS,
  destinations: [{ id: "meta_capi", label: "Meta CRM CAPI" }],
  rows: [
    { source_field: "Contact.Email",       cells: { meta_capi: { field: "email (hashed)", status: "confident"   } } },
    { source_field: "Contact.Phone",       cells: { meta_capi: { field: "phone (hashed)", status: "confident"   } } },
    { source_field: "StageName=Closed Won",cells: { meta_capi: { field: "event_name",     status: "confident"   } } },
    { source_field: "CloseDate",           cells: { meta_capi: { field: "event_time",     status: "confident"   } } },
    { source_field: "Amount",              cells: { meta_capi: { field: "value",           status: "confident"   } } },
    { source_field: "— constant: USD —",   cells: { meta_capi: { field: "currency",        status: "needs_input" } } },
  ],
};

// Variant B — multi destination, mixed statuses + not_required cells
const MOCK_MAPPING_REVIEW_MULTI: ApprovalInterruptPayload = {
  type: "mapping_review",
  source_object: "Salesforce Opportunity",
  source_fields: SF_OPPORTUNITY_FIELDS,
  destinations: [
    { id: "meta_capi",      label: "Meta CRM CAPI"  },
    { id: "google_offline", label: "Google Offline"  },
  ],
  rows: [
    { source_field: "Contact.Email",       cells: { meta_capi: { field: "email (hashed)",           status: "confident"   }, google_offline: { field: "email (hashed)",          status: "confident"   } } },
    { source_field: "Contact.Phone",       cells: { meta_capi: { field: "phone (hashed)",           status: "confident"   }, google_offline: { field: "phone (hashed)",          status: "confident"   } } },
    { source_field: "Amount",              cells: { meta_capi: { field: "value",                    status: "confident"   }, google_offline: { field: "conversion value",        status: "confident"   } } },
    { source_field: "CloseDate",           cells: { meta_capi: { field: "event_time",               status: "confident"   }, google_offline: { field: "conversion_time",         status: "confident"   } } },
    { source_field: "StageName=Closed Won",cells: { meta_capi: { field: "event_name",               status: "confident"   }, google_offline: { field: "conversion action — pick", status: "needs_input" } } },
    { source_field: "— constant: USD —",   cells: { meta_capi: { field: "currency",                 status: "confident"   }, google_offline: { field: "currency",                status: "confident"   } } },
    { source_field: "GCLID (if present)",  cells: { meta_capi: { field: null,                       status: "not_required" }, google_offline: { field: "gclid",                 status: "needs_input" } } },
  ],
};

// ── 7. canonical_mapping ─────────────────────────────────────────────────
// Agent sends a plain chat message first, then fires this interrupt.
// source_fields powers the per-row dropdown — send the full object field list.
// info_text stays in payload — static inline explainer shown at the bottom.
//
// Inbound:  { type, canonical_rows, source_fields, info_text? }
// Outbound: { approved: true, rows: CanonicalMappingRow[] }  // with user overrides
const MOCK_CANONICAL_MAPPING: ApprovalInterruptPayload = {
  type: "canonical_mapping",
  source_fields: SF_OPPORTUNITY_FIELDS,
  canonical_rows: [
    { canonical_field: "Email",            description: "Required · all 5 destinations",                   status: "confident",   source_field: "Contact.Email"          },
    { canonical_field: "Phone",            description: "Recommended · all 5 · lifts match rate",          status: "confident",   source_field: "Contact.Phone"          },
    { canonical_field: "Conversion value", description: "Required · all 5",                                status: "confident",   source_field: "Amount"                 },
    { canonical_field: "Currency",         description: "Required · all 5",                                status: "confident",   source_field: "Constant: USD"          },
    { canonical_field: "Conversion time",  description: "Required · all 5",                                status: "confident",   source_field: "CloseDate"              },
    { canonical_field: "Conversion event", description: "Required · all 5 · Google needs an action match", status: "needs_input", source_field: "StageName = Closed Won" },
    { canonical_field: "Click ID (GCLID)", description: "Google & Microsoft only · matches the ad click",  status: "needs_input", source_field: "GCLID"                  },
  ],
  info_text: "Signals sends these to Meta, Google, TikTok, Snapchat & LinkedIn automatically — per-platform field names are handled for you.",
};


// ── 3. check_connection (3 variants) ─────────────────────────────────────
// message stays in the interrupt payload — it's status data, not intro text.
// account_detail is only sent when connection_status === "connected".
//
// Inbound:  { type, source_label, connection_status, message, account_detail? }
// Outbound: onApprove({ action: "connect" })   — connect / reconnect / continue
//           onReject("change_source")           — only shown when not connected
const MOCK_CHECK_CONNECTION_NONE: ApprovalInterruptPayload = {
  type: "check_connection",
  source_label: "Salesforce",
  connection_status: "not_connected",
  message:
    "No active connection found for project Acme Prod. I'll open the secure connect screen — your credentials stay on Datahash's existing authentication flow.",
};

const MOCK_CHECK_CONNECTION_EXPIRED: ApprovalInterruptPayload = {
  type: "check_connection",
  source_label: "Salesforce",
  connection_status: "expired",
  message:
    "Your Salesforce connection for project Acme Prod has expired. Reconnect to continue — your credentials stay on Datahash's existing authentication flow.",
};

const MOCK_CHECK_CONNECTION_OK: ApprovalInterruptPayload = {
  type: "check_connection",
  source_label: "Salesforce",
  connection_status: "connected",
  account_detail: "Acme Corp · john@acme.com",
  message:
    "Active connection found. The agent will use this to fetch your Salesforce schema.",
};

// ── 5. check_channels (3 variants) ───────────────────────────────────────
// Agent sends a plain chat message first, then fires this interrupt.
// detail should always be present when connected (shows which account).
//
// Inbound:  { type, channels: ChannelConnectionStatus[] }
// Outbound: { action: "connect" | "skip" | "confirm_all", platform_id?: string }

// Variant A — some pending
const MOCK_CHECK_CHANNELS_MIXED: ApprovalInterruptPayload = {
  type: "check_channels",
  channels: [
    { id: "meta",   label: "Meta",   status: "connected",     detail: "Acme Business Manager · CRM CAPI ready" },
    { id: "google", label: "Google", status: "not_connected", detail: "No active connection · Offline Conversions" },
  ],
};

// Variant B — one expired
const MOCK_CHECK_CHANNELS_EXPIRED: ApprovalInterruptPayload = {
  type: "check_channels",
  channels: [
    { id: "meta",     label: "Meta",     status: "connected", detail: "Acme Business Manager · CRM CAPI ready" },
    { id: "tiktok",   label: "TikTok",   status: "expired",   detail: "Token expired 3 days ago · Events API" },
    { id: "linkedin", label: "LinkedIn", status: "connected", detail: "Acme Corp Page · Conversions API ready" },
  ],
};

// Variant C — all connected → green "All connected — continue" CTA
const MOCK_CHECK_CHANNELS_ALL_CONNECTED: ApprovalInterruptPayload = {
  type: "check_channels",
  channels: [
    { id: "meta",   label: "Meta",   status: "connected", detail: "Acme Business Manager · CRM CAPI ready" },
    { id: "google", label: "Google", status: "connected", detail: "Acme Ads · Offline Conversions ready" },
  ],
};

// ── 9. activate_confirm ───────────────────────────────────────────────────
// Inbound:  { type, validation?, summary_card?, confirm_label?, secondary_label? }
//   validation: green left-bar block with title + checks[]
//   summary_card: plain border block with title + lines[]
// Outbound: onApprove({ action: "activate" }) | onReject("review_matrix")
const MOCK_ACTIVATE_CONFIRM: ApprovalInterruptPayload = {
  type: "activate_confirm",
  validation: {
    title: "Validation passed — Meta + Google",
    checks: [
      "Source reachable · both credentials valid",
      "All required fields mapped across both destinations",
      "Sample payload well-formed for each Conversion API",
    ],
  },
  summary_card: {
    title: "Salesforce Opportunities → Meta + Google (one pipeline)",
    lines: [
      "Offline conversions · email/phone hashed · value=Amount, currency=USD",
      "Shared mapping reused; Google conversion action set to Closed Won",
      "Data flows forward from activation (no backfill in this setup).",
    ],
  },
  confirm_label: "Activate both",
  secondary_label: "Review matrix",
};

// ── 8 resolve_fields (has_issues) ──────────────────────────────────────────
// Inbound:  { type, resolve_status, destination_label, source_fields, unresolved_fields }
// Outbound: { action: "submit", resolutions: [{ field, action, value? | source_field? }] }
//   action per field: "set_constant" (value=…) | "map_field" (source_field=…)
// Agent re-fires this interrupt if more unresolved fields remain.
const MOCK_RESOLVE_FIELDS_ISSUES: ApprovalInterruptPayload = {
  type: "resolve_fields",
  resolve_status: "has_issues",
  destination_label: "Meta",
  source_fields: SF_OPPORTUNITY_FIELDS,
  unresolved_fields: [
    { field: "currency", required: true, suggested_constant: "USD" },
    { field: "stage_name", required: true, suggested_source_field: "StageName" },
    { field: "conversion_event", required: false },
  ],
};

const MOCK_RESOLVE_FIELDS_RESOLVED: ApprovalInterruptPayload = {
  type: "resolve_fields",
  resolve_status: "resolved",
  destination_label: "Meta",
  summary_text: "email, phone → hashed before sending. value=Amount, currency=USD",
};


const LEGACY_STAGES: { label: string; tag: string; payload: ApprovalInterruptPayload }[] = [
  { label: "Legacy — Select object",             tag: "select_object",    payload: MOCK_SELECT_OBJECT            },
  { label: "Check connection (not connected)",   tag: "check_connection", payload: MOCK_CHECK_CONNECTION_NONE    },
  { label: "Check connection (expired)",         tag: "check_connection", payload: MOCK_CHECK_CONNECTION_EXPIRED },
  { label: "Check connection (connected)",       tag: "check_connection", payload: MOCK_CHECK_CONNECTION_OK      },
  { label: "Check channels (mixed)",             tag: "check_channels",   payload: MOCK_CHECK_CHANNELS_MIXED         },
  { label: "Check channels (with expired)",      tag: "check_channels",   payload: MOCK_CHECK_CHANNELS_EXPIRED       },
  { label: "Check channels (all connected)",     tag: "check_channels",   payload: MOCK_CHECK_CHANNELS_ALL_CONNECTED },
  { label: "Mapping review (single dest)",       tag: "mapping_review",   payload: MOCK_MAPPING_REVIEW_SINGLE   },
  { label: "Mapping review (multi dest)",        tag: "mapping_review",   payload: MOCK_MAPPING_REVIEW_MULTI    },
  { label: "Canonical mapping",                  tag: "canonical_mapping",payload: MOCK_CANONICAL_MAPPING       },
  { label: "Resolve fields (has issues)",        tag: "resolve_fields",   payload: MOCK_RESOLVE_FIELDS_ISSUES   },
  { label: "Resolve fields (resolved)",          tag: "resolve_fields",   payload: MOCK_RESOLVE_FIELDS_RESOLVED },
  { label: "Activate confirm",                   tag: "activate_confirm", payload: MOCK_ACTIVATE_CONFIRM        },
];

// ── Preview page ───────────────────────────────────────────────────────────

export default function InterruptDevPage() {
  const [responses, setResponses] = useState<Record<string, unknown>>({});

  function handleApprove(key: string, response: unknown) {
    setResponses((prev) => ({ ...prev, [key]: { action: "approved", response } }));
  }

  function handleReject(key: string, reason?: string) {
    setResponses((prev) => ({ ...prev, [key]: { action: "rejected", reason } }));
  }

  const sessionId = loadStoredSessionId() ?? "dev-preview-session";

  return (
    <div className="h-full overflow-y-auto bg-[var(--background)] px-6 py-8">
      <div className="mx-auto mb-8 max-w-2xl rounded-lg border border-dashed border-red-400/60 bg-red-500/5 px-4 py-3">
        <p className="text-sm font-semibold text-red-600 dark:text-red-400">
          DEV PREVIEW — delete <code className="font-mono">src/app/(app)/interrupt-dev/</code> when your agent emits real interrupts
        </p>
        <p className="mt-1 text-xs text-[var(--muted-foreground)]">
          Top gallery: live <code className="font-mono">intent_clarify</code> shapes. Other interrupt cards below.
        </p>
      </div>

      <div className="mx-auto max-w-2xl space-y-10">
        <div className="space-y-1">
          <p className="text-sm font-semibold text-[var(--foreground)]">intent_clarify</p>
          <p className="text-xs text-[var(--muted-foreground)]">
            source → signal_type → channels · resume {"{ selected }"}
          </p>
        </div>

        {CLARIFY_MOCKS.map((mock) => {
          const key = `clarify-${mock.field}`;
          const result = responses[key];
          return (
            <section key={key}>
              <div className="mb-3">
                <p className="text-sm font-semibold text-[var(--foreground)]">{mock.label}</p>
                <code className="text-xs text-[var(--muted-foreground)]">
                  type: &quot;intent_clarify&quot; · field: &quot;{mock.field}&quot;
                </code>
              </div>
              <HitlApprovalCard
                payload={mock.payload}
                sessionId={sessionId}
                onApprove={(response) => handleApprove(key, response)}
                onReject={(reason) => handleReject(key, reason)}
              />
              {result ? (
                <pre className="mt-2 rounded-md border border-[var(--border)] bg-[var(--secondary)] p-3 text-xs text-[var(--foreground)] overflow-x-auto">
                  {JSON.stringify(result, null, 2)}
                </pre>
              ) : null}
            </section>
          );
        })}

        <div className="border-t border-[var(--border)] pt-8 space-y-1">
          <p className="text-sm font-semibold text-[var(--muted-foreground)]">Other interrupts</p>
          <p className="text-xs text-[var(--muted-foreground)]">
            select_object remains for preview; source/channels clarifications use intent_clarify above.
          </p>
        </div>

        {LEGACY_STAGES.map((stage, index) => {
          const key = `legacy-${index}-${stage.tag}`;
          const result = responses[key];
          return (
            <section key={key} className="opacity-70">
              <div className="mb-3 flex items-center gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--secondary)] text-xs font-bold text-[var(--muted-foreground)]">
                  {index + 1}
                </span>
                <div>
                  <p className="text-sm font-semibold text-[var(--muted-foreground)]">{stage.label}</p>
                  <code className="text-xs text-[var(--muted-foreground)]">type: &quot;{stage.tag}&quot;</code>
                </div>
              </div>
              <HitlApprovalCard
                payload={stage.payload}
                sessionId={sessionId}
                onApprove={(response) => handleApprove(key, response)}
                onReject={(reason) => handleReject(key, reason)}
              />
              {result ? (
                <pre className="mt-2 rounded-md border border-[var(--border)] bg-[var(--secondary)] p-3 text-xs text-[var(--foreground)] overflow-x-auto">
                  {JSON.stringify(result, null, 2)}
                </pre>
              ) : null}
            </section>
          );
        })}
      </div>
    </div>
  );
}

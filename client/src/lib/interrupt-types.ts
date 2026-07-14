export type SelectOption = {
  id: string;
  label: string;
  enabled?: boolean;
  description?: string;
};

/** Clarify interrupt field — mirrors backend IntentOpenQuestion. */
export type IntentClarifyField = "source" | "signal_type" | "channels";

export type MappingDestination = {
  id: string;
  label: string;
  color?: string;
};

export type MappingCell = {
  field: string | null;
  status: string;
};

export type MappingReviewRow = {
  source_field: string;
  cells: Record<string, MappingCell>;
};

export type UnresolvedField = {
  field: string;
  required: boolean;
  suggested_constant?: string;
  suggested_source_field?: string;
};

export type ChannelConnectionStatus = {
  id: string;
  label: string;
  status: string;
  detail?: string;
  connector_slug?: string;
  project_id?: string;
};

export type CanonicalMappingRow = {
  canonical_field: string;
  description?: string;
  status: string;
  source_field?: string;
};

/**
 * Backend interrupt contract — what CopilotKit streams as `on_interrupt`.
 */
export type ApprovalInterruptPayload = {
  type?: string;
  phase?: string;
  /** Clarify field for `intent_clarify` interrupts */
  field?: IntentClarifyField;
  default_selected?: string | string[];
  proposal?: string;
  source_object?: string;
  options?: SelectOption[] | string[];
  requested?: string;
  min_select?: number;
  max_select?: number;
  /** Multi-select picker (e.g. channels clarify) */
  multi?: boolean;
  title?: string;
  /** Supporting copy under title (intent_clarify) */
  subtitle?: string;
  message?: string;
  hint?: string;
  required?: boolean;
  context?: Record<string, unknown>;
  attempt?: number;
  max_attempts?: number;
  recommended?: string;
  confidence?: string;
  source_label?: string;
  connection_status?: string;
  account_detail?: string;
  destinations?: MappingDestination[];
  rows?: MappingReviewRow[] | Array<{
    canonical_key: string;
    label: string;
    source_field: string | null;
    status: string;
    cells: Record<string, { field: string | null; status: string }>;
  }>;
  source_fields?: string[];
  canonical_rows?: CanonicalMappingRow[];
  info_text?: string;
  resolve_status?: string;
  unresolved_fields?: UnresolvedField[];
  summary_text?: string;
  destination_label?: string;
  channels?: ChannelConnectionStatus[];
  validation?: { title: string; checks: string[] };
  summary_card?: { title: string; lines: string[] };
  confirm_label?: string;
  secondary_label?: string;
  connector_slug?: string;
  project_id?: string;
  picklist_fields?: Array<{ name: string; label: string }>;
  suggested_trigger_field?: string;
  trigger_field?: string;
  available_stage_values?: string[];
  suggested_stages?: Array<{
    stage_name: string;
    trigger_value: string;
    time_field?: string;
    value_field?: string;
    per_destination?: Record<string, unknown>;
  }>;
  datetime_fields?: string[];
  numeric_fields?: string[];
  active_destinations?: string[];
  errors?: string[];
  warnings?: string[];
  token?: string;
  summary?: string[];
  accounts?: Array<{ value: string; label: string }>;
  conversion_actions?: Array<{ value: string; label: string }>;
  account_id?: string;
  destinations_breakdown?: Array<{
    destination: string;
    coverage_pct: number;
    match_keys_covered: string[];
    match_keys_missing: string[];
    status: string;
    required_count: number;
    mapped_count: number;
  }>;
  overall_pct?: number;
  needs?: Array<{
    canonical_key: string;
    label: string;
    reason: string;
    status: string;
    required: boolean;
  }>;
  checks?: Array<{
    name: string;
    passed: boolean;
    severity: string;
    message: string;
    sample_payload?: Record<string, unknown>;
  }>;
  overall_passed?: boolean;
  destination?: string;
  fields?: Array<{
    name: string;
    label: string;
    placeholder?: string;
    required?: boolean;
  }>;
};

export type InterruptEvent = {
  name: string;
  value: ApprovalInterruptPayload;
};

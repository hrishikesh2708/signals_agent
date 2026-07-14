"use client";

import { AgentEventLine } from "./agent-event-line";
import { AgentTextBubble } from "./agent-text-bubble";
import { ErrorCard } from "./error-card";
import { IntentAckCard } from "../interrupts/intent-ack-card";
import { MappingResultCard } from "./mapping-result-card";
import { PipelineActivatedCard } from "./pipeline-activated-card";
import { SchemaSummaryCard } from "./schema-summary-card";
import { StepCompleteCard } from "./step-complete-card";
import { ThinkingCard } from "./thinking-card";
import { WarningCard } from "./warning-card";
import { parseAgentMessage } from "@/lib/parse-agent-message";

export function AgentMessageBubble({
  content,
}: {
  content: unknown;
  priorAssistantContents?: unknown[];
}) {
  const parsed = parseAgentMessage(content);

  switch (parsed.kind) {
    case "mapping_complete":
      return <MappingResultCard data={parsed.data} />;

    case "intent_ack":
      return <IntentAckCard data={parsed.data} />;

    case "agent_event":
      if (parsed.data.status === "confirmed") {
        return (
          <StepCompleteCard
            data={{ type: "step_complete", message: parsed.data.message }}
          />
        );
      }
      return <AgentEventLine data={parsed.data} />;

    case "thinking":
      return <ThinkingCard data={parsed.data} />;

    case "step_complete":
      return <StepCompleteCard data={parsed.data} />;

    case "schema_summary":
      return <SchemaSummaryCard data={parsed.data} />;

    case "pipeline_activated":
      return <PipelineActivatedCard data={parsed.data} />;

    case "error":
      return <ErrorCard data={parsed.data} />;

    case "warning":
      return <WarningCard data={parsed.data} />;

    case "clarification":
      return (
        <AgentTextBubble>
          <p className="whitespace-pre-wrap">{parsed.data.message}</p>
        </AgentTextBubble>
      );

    case "clarification_resolved":
      return (
        <StepCompleteCard
          data={{ type: "step_complete", message: parsed.data.message }}
        />
      );

    case "intent_summary": {
      const d = parsed.data;
      const details = d.details ?? {};
      const ackData = {
        type: "intent_ack" as const,
        run_mode: details.signal_display
          ? details.signal_display
              .replace(/_/g, " ")
              .replace(/\b\w/g, (c) => c.toUpperCase())
          : undefined,
        sources: details.source_label ? [details.source_label] : undefined,
        source_object: details.source_object
          ? [details.source_object]
          : undefined,
        channels: details.destination_labels?.length
          ? details.destination_labels
          : undefined,
      };
      return (
        <div className="max-w-[85%] space-y-3">
          <AgentTextBubble className="max-w-none">
            <p className="whitespace-pre-wrap">{d.message}</p>
          </AgentTextBubble>
          <div className="flex items-start gap-3">
            <div className="h-7 w-7 shrink-0" aria-hidden />
            <IntentAckCard data={ackData} />
          </div>
        </div>
      );
    }

    case "intent_status": {
      const { type, message, corrected_fields } = parsed.data;
      if (type === "intent_reset") {
        return (
          <AgentTextBubble>
            <p className="whitespace-pre-wrap">{message}</p>
          </AgentTextBubble>
        );
      }
      const detail =
        corrected_fields && corrected_fields.length > 0
          ? `Updated: ${corrected_fields.map((f) => f.replace(/_/g, " ")).join(", ")}`
          : undefined;
      return (
        <StepCompleteCard
          data={{ type: "step_complete", message, detail }}
        />
      );
    }

    case "text":
      if (!parsed.text) return null;
      return (
        <AgentTextBubble>
          <p className="whitespace-pre-wrap">{parsed.text}</p>
        </AgentTextBubble>
      );

    default: {
      const _exhaustive: never = parsed;
      return _exhaustive;
    }
  }
}

"use client";

import { CHAT_AGENT_ID } from "@/lib/chat-constants";
import type { InterruptEvent } from "@/lib/interrupt-types";
import { normalizeInterruptPayload } from "@/lib/normalize-interrupt-payload";
import { useAgent, useCopilotKit } from "@copilotkit/react-core/v2";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

export { normalizeInterruptPayload } from "@/lib/normalize-interrupt-payload";

export const INTERRUPT_EVENT_NAME = "on_interrupt";

export function useHeadlessInterrupt() {
  const { copilotkit } = useCopilotKit();
  const { agent } = useAgent({ agentId: CHAT_AGENT_ID });
  const [pending, setPending] = useState<InterruptEvent | null>(null);
  const stagedRef = useRef<InterruptEvent | null>(null);
  const rawInterruptRef = useRef<unknown>(null);

  useEffect(() => {
    const sub = agent.subscribe({
      onCustomEvent: ({ event }) => {
        if (event.name === INTERRUPT_EVENT_NAME) {
          rawInterruptRef.current = event.value;
          stagedRef.current = {
            name: event.name,
            value: normalizeInterruptPayload(event.value),
          };
        }
      },
      onRunStartedEvent: () => {
        stagedRef.current = null;
        rawInterruptRef.current = null;
        setPending(null);
      },
      onRunFinalized: () => {
        if (stagedRef.current) {
          setPending(stagedRef.current);
          stagedRef.current = null;
        }
      },
      onRunFailed: ({ error }) => {
        stagedRef.current = null;
        rawInterruptRef.current = null;
        console.error("Agent run failed after interrupt:", error);
      },
      onRunErrorEvent: ({ event }) => {
        console.error("Agent run error:", event.message);
      },
    });
    return () => sub.unsubscribe();
  }, [agent]);

  const clear = useCallback(() => {
    stagedRef.current = null;
    rawInterruptRef.current = null;
    setPending(null);
  }, []);

  const resolve = useCallback(
    (response: unknown) => {
      const snapshot = pending;
      setPending(null);
      void copilotkit
        .runAgent({
          agent,
          forwardedProps: {
            command: {
              resume: response,
              interruptEvent: rawInterruptRef.current ?? snapshot?.value,
            },
          },
        })
        .catch((error) => {
          console.error("Failed to resume agent after HITL:", error);
        });
    },
    [agent, copilotkit, pending],
  );

  return useMemo(
    () => ({ pending, resolve, clear }),
    [pending, resolve, clear],
  );
}

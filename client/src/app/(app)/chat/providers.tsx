"use client";

import "@copilotkit/react-core/v2/styles.css";

import { CopilotKit } from "@copilotkit/react-core/v2";

import { copilot } from "@/lib/api";

/**
 * Wraps the chat in a CopilotKit provider.
 * Auth and project headers are added when BFF routes land.
 */
export function ChatProviders({
  threadId,
  children,
}: {
  threadId: string;
  children: React.ReactNode;
}) {
  return (
    <CopilotKit
      runtimeUrl={copilot.runtimeUrl()}
      agent={copilot.agentId}
      threadId={threadId}
      useSingleEndpoint
      enableInspector={false}
    >
      {children}
    </CopilotKit>
  );
}

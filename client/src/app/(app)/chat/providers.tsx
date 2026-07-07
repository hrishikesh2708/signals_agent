"use client";

import "@copilotkit/react-core/v2/styles.css";

import { CopilotKit } from "@copilotkit/react-core/v2";
import { useMemo } from "react";

import { copilot } from "@/lib/api";
import { readProjectIdFromCookie } from "@/lib/project-storage";

/**
 * Wraps the chat in a CopilotKit provider.
 * - Authorization: session-scoped JWT for the backend
 * - X-Project-Id: active project from the dh_project_id cookie
 */
export function ChatProviders({
  threadId,
  sessionToken,
  children,
}: {
  threadId: string;
  sessionToken: string;
  children: React.ReactNode;
}) {
  const headers = useMemo(() => {
    const projectId = readProjectIdFromCookie();
    return {
      Authorization: `Bearer ${sessionToken}`,
      ...(projectId ? { "X-Project-Id": projectId } : {}),
    };
  }, [sessionToken]);

  return (
    <CopilotKit
      runtimeUrl={copilot.runtimeUrl()}
      agent={copilot.agentId}
      threadId={threadId}
      useSingleEndpoint
      enableInspector={false}
      headers={headers}
    >
      {children}
    </CopilotKit>
  );
}

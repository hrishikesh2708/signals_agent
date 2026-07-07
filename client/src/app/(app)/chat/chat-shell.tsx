"use client";

import { useEffect, useState } from "react";

import { ChatProviders } from "@/app/(app)/chat/providers";
import {
  CopilotChatLayout,
  CopilotOfflineBanner,
} from "@/components/chat/copilot-chat-layout";
import { HeadlessChat } from "@/components/chat/headless-chat";
import { Spinner } from "@/components/ui/spinner";
import {
  createLocalSession,
  type StoredChatSession,
} from "@/lib/session-storage";

/**
 * Bootstraps a local CopilotKit thread id, then mounts HeadlessChat.
 * Server-backed session tokens are wired in when auth endpoints exist.
 */
export function ChatShell() {
  const [session, setSession] = useState<StoredChatSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      setSession(createLocalSession());
    } catch (err) {
      setError(err instanceof Error ? err.message : "session_create_failed");
    } finally {
      setLoading(false);
    }
  }, []);

  if (loading) {
    return (
      <CopilotChatLayout
        inputDisabled
        banner={
          <div className="flex items-center gap-2">
            <Spinner size="sm" />
            Preparing chat session…
          </div>
        }
      />
    );
  }

  if (error || !session) {
    return (
      <CopilotChatLayout
        inputDisabled
        inputPlaceholder="Connect backend session to start chatting"
        banner={
          <CopilotOfflineBanner
            message={`Session could not be created (${error ?? "unknown error"}). Check that the backend is running.`}
          />
        }
      />
    );
  }

  return (
    <ChatProviders threadId={session.session_id}>
      <HeadlessChat sessionId={session.session_id} />
    </ChatProviders>
  );
}

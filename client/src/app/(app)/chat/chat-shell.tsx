"use client";

import { useCallback, useEffect, useState } from "react";

import { ChatProviders } from "@/app/(app)/chat/providers";
import {
  CopilotChatLayout,
  CopilotOfflineBanner,
} from "@/components/chat/copilot-chat-layout";
import { HeadlessChat } from "@/components/chat/headless-chat";
import { ProjectProvider } from "@/components/project/project-context";
import { ProjectSelector } from "@/components/project/project-selector";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import { loadStoredProject } from "@/lib/project-storage";
import {
  jwtExpiresAt,
  loadStoredSession,
  storeSession,
  type StoredChatSession,
} from "@/lib/session-storage";
import type { ProjectResponse } from "@/lib/types";

/**
 * Auth → inline project gate → server session bootstrap → HeadlessChat.
 * Project selection stays inside /chat (no separate /project route).
 */
export function ChatShell() {
  const { loading: authLoading } = useAuth();
  const [projectHydrated, setProjectHydrated] = useState(false);
  const [activeProject, setActiveProject] = useState<ProjectResponse | null>(null);
  const [session, setSession] = useState<StoredChatSession | null>(null);
  const [sessionLoading, setSessionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setActiveProject(loadStoredProject());
    setProjectHydrated(true);
  }, []);

  const handleProjectSelect = useCallback((project: ProjectResponse) => {
    setError(null);
    setSession(null);
    setActiveProject(project);
  }, []);

  useEffect(() => {
    if (authLoading || !projectHydrated || !activeProject) return;

    const project = activeProject;
    let cancelled = false;

    async function bootstrapSession() {
      setSessionLoading(true);
      setError(null);

      try {
        const existing = loadStoredSession();
        if (existing?.access_token) {
          if (!cancelled) {
            setSession(existing);
            setSessionLoading(false);
          }
          return;
        }

        const created = await api.createSession({ project_id: project.id });
        const next: StoredChatSession = {
          session_id: created.session_id,
          access_token: created.token,
          expires_at: jwtExpiresAt(created.token),
        };
        storeSession(next);
        if (!cancelled) {
          setSession(next);
          setSessionLoading(false);
        }
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 401) return;
        setError(err instanceof Error ? err.message : "session_create_failed");
        setSessionLoading(false);
      }
    }

    void bootstrapSession();
    return () => {
      cancelled = true;
    };
  }, [authLoading, projectHydrated, activeProject]);

  if (authLoading || !projectHydrated) {
    return (
      <CopilotChatLayout
        inputDisabled
        banner={
          <div className="flex items-center gap-2">
            <Spinner size="sm" />
            Loading…
          </div>
        }
      />
    );
  }

  if (!activeProject) {
    return (
      <CopilotChatLayout
        inputDisabled
        inputPlaceholder="Select a project to start chatting"
      >
        <div className="flex justify-center py-12">
          <ProjectSelector onSelect={handleProjectSelect} />
        </div>
      </CopilotChatLayout>
    );
  }

  if (sessionLoading || !session) {
    return (
      <CopilotChatLayout
        inputDisabled
        projectName={activeProject.name}
        banner={
          <div className="flex items-center gap-2">
            <Spinner size="sm" />
            Preparing chat session…
          </div>
        }
      />
    );
  }

  if (error) {
    return (
      <CopilotChatLayout
        inputDisabled
        projectName={activeProject.name}
        inputPlaceholder="Connect backend session to start chatting"
        banner={
          <CopilotOfflineBanner
            message={`Session could not be created (${error}). Check that the backend is running.`}
          />
        }
      />
    );
  }

  return (
    <ProjectProvider project={activeProject}>
      <ChatProviders threadId={session.session_id}>
        <HeadlessChat
          projectName={activeProject.name}
          sessionId={session.session_id}
        />
      </ChatProviders>
    </ProjectProvider>
  );
}

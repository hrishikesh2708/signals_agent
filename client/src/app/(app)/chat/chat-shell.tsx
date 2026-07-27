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
import { ApiError } from "@/lib/api";
import { clearProject, loadStoredProject } from "@/lib/project-storage";
import {
  clearSession,
  createServerSession,
  type StoredChatSession,
} from "@/lib/session-storage";
import type { ProjectResponse } from "@/lib/types";

/**
 * Auth → inline project gate → server session bootstrap → HeadlessChat.
 * Project selection stays inside /chat (no separate /project route).
 */
export function ChatShell() {
  const { user, loading: authLoading } = useAuth();
  const [projectHydrated, setProjectHydrated] = useState(false);
  const [activeProject, setActiveProject] = useState<ProjectResponse | null>(null);
  const [session, setSession] = useState<StoredChatSession | null>(null);
  const [sessionLoading, setSessionLoading] = useState(false);
  const [newChatLoading, setNewChatLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const userId = user?.id;

  useEffect(() => {
    if (authLoading) return;

    if (!userId) {
      clearSession();
      clearProject();
      setActiveProject(null);
      setProjectHydrated(true);
      return;
    }

    const stored = loadStoredProject();
    if (!stored || stored.user_id !== userId) {
      clearSession();
      clearProject();
      setActiveProject(null);
    } else {
      setActiveProject(stored);
    }
    setProjectHydrated(true);
  }, [authLoading, userId]);

  const handleProjectSelect = useCallback((project: ProjectResponse) => {
    setError(null);
    clearSession();
    setSession(null);
    setActiveProject(project);
  }, []);

  const handleSwitchProject = useCallback(() => {
    setError(null);
    clearSession();
    clearProject();
    setSession(null);
    setActiveProject(null);
  }, []);

  const handleNewChat = useCallback(async () => {
    if (!user || !activeProject || newChatLoading) return;

    setNewChatLoading(true);
    setError(null);

    try {
      clearSession();
      const next = await createServerSession(activeProject.id, {
        userId: user.id,
        forceNew: true,
      });
      setSession(next);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return;
      setError(err instanceof Error ? err.message : "session_create_failed");
    } finally {
      setNewChatLoading(false);
    }
  }, [user, activeProject, newChatLoading]);

  useEffect(() => {
    if (authLoading || !user || !projectHydrated || !activeProject) return;

    const project = activeProject;
    const userId = user.id;
    let cancelled = false;

    async function bootstrapSession() {
      setSessionLoading(true);
      setError(null);

      try {
        const next = await createServerSession(project.id, { userId });
        if (!cancelled) {
          setSession(next);
          setSessionLoading(false);
        }
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 401) {
          setSessionLoading(false);
          return;
        }
        setError(err instanceof Error ? err.message : "session_create_failed");
        setSessionLoading(false);
      }
    }

    void bootstrapSession();
    return () => {
      cancelled = true;
    };
  }, [authLoading, user, projectHydrated, activeProject]);

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
      <ChatProviders
        key={session.session_id}
        threadId={session.session_id}
        sessionToken={session.access_token}
      >
        <HeadlessChat
          projectName={activeProject.name}
          sessionId={session.session_id}
          onNewChat={handleNewChat}
          onSwitchProject={handleSwitchProject}
          newChatLoading={newChatLoading}
        />
      </ChatProviders>
    </ProjectProvider>
  );
}

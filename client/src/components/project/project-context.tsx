"use client";

import {
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { ProjectResponse } from "@/lib/types";

interface ProjectContextValue {
  project: ProjectResponse;
}

const ProjectContext = createContext<ProjectContextValue | null>(null);

export function ProjectProvider({
  project,
  children,
}: {
  project: ProjectResponse;
  children: ReactNode;
}) {
  const [current] = useState<ProjectResponse>(project);
  const value = useMemo(() => ({ project: current }), [current]);
  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>;
}

export function useProject() {
  const ctx = useContext(ProjectContext);
  if (!ctx) throw new Error("useProject must be used within ProjectProvider");
  return ctx;
}

import type { ProjectResponse } from "@/lib/types";

const PROJECT_STORAGE_KEY = "dh_active_project";
export const PROJECT_ID_COOKIE = "dh_project_id";

function isValidProject(value: unknown): value is ProjectResponse {
  if (!value || typeof value !== "object") return false;
  const p = value as ProjectResponse;
  return typeof p.id === "string" && p.id.length > 0 && typeof p.name === "string";
}

export function loadStoredProject(): ProjectResponse | null {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(PROJECT_STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!isValidProject(parsed)) {
      window.sessionStorage.removeItem(PROJECT_STORAGE_KEY);
      return null;
    }
    return parsed;
  } catch {
    window.sessionStorage.removeItem(PROJECT_STORAGE_KEY);
    return null;
  }
}

export function storeProject(project: ProjectResponse): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(PROJECT_STORAGE_KEY, JSON.stringify(project));
  document.cookie = `${PROJECT_ID_COOKIE}=${encodeURIComponent(project.id)}; path=/; SameSite=lax`;
}

export function clearStoredProject(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(PROJECT_STORAGE_KEY);
  document.cookie = `${PROJECT_ID_COOKIE}=; path=/; max-age=0`;
}

/** Alias for switch-project flows. */
export const clearProject = clearStoredProject;

export function readProjectIdFromCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(
    new RegExp(`(?:^|; )${PROJECT_ID_COOKIE}=([^;]*)`),
  );
  return match ? decodeURIComponent(match[1]) : null;
}

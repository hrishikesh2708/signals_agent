import type { UserResponse } from "./types";

const AUTH_USER_KEY = "dh_auth_user";

function isValidUser(value: unknown): value is UserResponse {
  if (!value || typeof value !== "object") return false;
  const user = value as UserResponse;
  return (
    typeof user.id === "string" &&
    user.id.length > 0 &&
    typeof user.email === "string" &&
    typeof user.name === "string"
  );
}

/** Cached user from the last successful `/api/auth/me` (client-only). */
export function loadStoredUser(): UserResponse | null {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(AUTH_USER_KEY);
  if (!raw) return null;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!isValidUser(parsed)) {
      window.sessionStorage.removeItem(AUTH_USER_KEY);
      return null;
    }
    return parsed;
  } catch {
    window.sessionStorage.removeItem(AUTH_USER_KEY);
    return null;
  }
}

export function storeUser(user: UserResponse): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
}

export function clearStoredUser(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(AUTH_USER_KEY);
}

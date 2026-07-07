const CHAT_SESSION_KEY = "dh_chat_session";

export interface StoredChatSession {
  session_id: string;
  access_token: string;
  expires_at: number;
}

const SESSION_TTL_SECONDS = 60 * 60 * 24 * 7;

export function loadStoredSession(): StoredChatSession | null {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(CHAT_SESSION_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as StoredChatSession;
    if (parsed.expires_at * 1000 < Date.now()) {
      window.sessionStorage.removeItem(CHAT_SESSION_KEY);
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function storeSession(session: StoredChatSession): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(CHAT_SESSION_KEY, JSON.stringify(session));
}

/** Active chat session id from sessionStorage (set by chat-shell on bootstrap). */
export function loadStoredSessionId(): string | null {
  const session = loadStoredSession();
  return session?.session_id ?? null;
}

export function createLocalSession(): StoredChatSession {
  const existing = loadStoredSession();
  if (existing) return existing;

  const session: StoredChatSession = {
    session_id: crypto.randomUUID(),
    access_token: "",
    expires_at: Math.floor(Date.now() / 1000) + SESSION_TTL_SECONDS,
  };
  storeSession(session);
  return session;
}

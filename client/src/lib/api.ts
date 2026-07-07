import { parseApiErrorBody } from "./api-errors";
import type { HealthResponse } from "./types";

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
}

const DEFAULT_API_URL = "http://localhost:8000";

function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL;
}

function buildUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${apiBaseUrl()}${normalized}`;
}

/**
 * Low-level HTTP helper. Components and pages should use `api` / `copilot`
 * exports instead of calling this directly.
 */
async function request<T = unknown>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { body, headers, ...rest } = options;

  const finalHeaders: Record<string, string> = {
    Accept: "application/json",
    ...(headers as Record<string, string> | undefined),
  };

  let serializedBody: BodyInit | undefined;
  if (body !== undefined) {
    if (
      body instanceof FormData ||
      body instanceof URLSearchParams ||
      body instanceof Blob ||
      typeof body === "string"
    ) {
      serializedBody = body as BodyInit;
    } else {
      serializedBody = JSON.stringify(body);
      finalHeaders["Content-Type"] ??= "application/json";
    }
  }

  const res = await fetch(buildUrl(path), {
    ...rest,
    headers: finalHeaders,
    body: serializedBody,
  });

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  let parsed: unknown = null;
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = text;
    }
  }

  if (!res.ok) {
    const { message } = parseApiErrorBody(parsed, `request_failed_${res.status}`);
    throw new ApiError(message, res.status, parsed);
  }

  return parsed as T;
}

/** Same-origin BFF routes under `app/api/` (not the LangGraph backend). */
async function bffRequest<T = unknown>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { body, headers, ...rest } = options;

  const finalHeaders: Record<string, string> = {
    Accept: "application/json",
    ...(headers as Record<string, string> | undefined),
  };

  let serializedBody: BodyInit | undefined;
  if (body !== undefined) {
    if (
      body instanceof FormData ||
      body instanceof URLSearchParams ||
      body instanceof Blob ||
      typeof body === "string"
    ) {
      serializedBody = body as BodyInit;
    } else {
      serializedBody = JSON.stringify(body);
      finalHeaders["Content-Type"] ??= "application/json";
    }
  }

  const normalized = path.startsWith("/") ? path : `/${path}`;
  const res = await fetch(normalized, {
    ...rest,
    headers: finalHeaders,
    body: serializedBody,
  });

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  let parsed: unknown = null;
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = text;
    }
  }

  if (!res.ok) {
    const { message } = parseApiErrorBody(parsed, `request_failed_${res.status}`);
    throw new ApiError(message, res.status, parsed);
  }

  return parsed as T;
}

export interface AuthorizeConnectionResponse {
  auth_url: string;
  state: string;
}

/** REST surface — add auth, projects, connections per server milestone. */
export const api = {
  health: () => request<HealthResponse>("/health"),

  /** Start OAuth for a connector via the Next.js BFF (forwards JWT + session id). */
  authorizeConnection: (
    connectorSlug: string,
    projectId: string,
    sessionId: string,
  ): Promise<AuthorizeConnectionResponse> =>
    bffRequest<AuthorizeConnectionResponse>(
      `/api/connections/${connectorSlug}?project_id=${encodeURIComponent(projectId)}`,
      {
        method: "POST",
        headers: { "X-Session-Id": sessionId },
      },
    ),

  /** Mock-connect a destination when live OAuth credentials are unavailable. */
  mockConnectConnection: (
    connectorSlug: string,
    projectId: string,
    body: Record<string, string>,
  ): Promise<void> =>
    bffRequest<void>(
      `/api/connections/${connectorSlug}?project_id=${encodeURIComponent(projectId)}`,
      {
        method: "PATCH",
        body,
      },
    ),
};

/** CopilotKit runtime config — single source of truth for agent wiring. */
export const copilot = {
  /** Trailing slash avoids redirect races during CopilotKit /info discovery. */
  runtimeUrl: () => `${apiBaseUrl()}/api/copilotkit/`,
  agentId: "signals_agent" as const,
};

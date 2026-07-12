import { parseApiErrorBody } from "./api-errors";
import type {
  AgentSessionResponse,
  AuthMeResponse,
  AuthSuccessResponse,
  HealthResponse,
  LoginRequest,
  ProjectCreate,
  ProjectListResponse,
  ProjectResponse,
  RegisterRequest,
  SessionCreate,
  SessionResponse,
  TokenResponse,
  UserResponse,
} from "./types";

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
  /** Sends `Authorization: Bearer <token>`. */
  bearerToken?: string;
  /** Sends `X-Project-Id` header (session-scoped calls). */
  projectId?: string;
  /** When false, a 401 does not redirect to /login (use for login/register). */
  redirectOnUnauthorized?: boolean;
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

function buildAuthHeaders(options: RequestOptions): Record<string, string> {
  const headers: Record<string, string> = {};
  if (options.bearerToken) {
    headers.Authorization = `Bearer ${options.bearerToken}`;
  }
  if (options.projectId) {
    headers["X-Project-Id"] = options.projectId;
  }
  return headers;
}

async function parseResponse<T>(res: Response): Promise<T> {
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

/**
 * Low-level HTTP helper for direct LangGraph backend calls.
 * Components and pages should use `api` / `copilot` exports instead of calling this directly.
 */
async function request<T = unknown>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const {
    body,
    headers,
    bearerToken,
    projectId,
    redirectOnUnauthorized: _redirectOnUnauthorized,
    ...rest
  } = options;

  const finalHeaders: Record<string, string> = {
    Accept: "application/json",
    ...buildAuthHeaders({ bearerToken, projectId }),
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

  return parseResponse<T>(res);
}

/** Same-origin BFF routes under `app/api/` (not the LangGraph backend). */
async function bffRequest<T = unknown>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const {
    body,
    headers,
    bearerToken,
    projectId,
    redirectOnUnauthorized = true,
    credentials = "include",
    ...rest
  } = options;

  const finalHeaders: Record<string, string> = {
    Accept: "application/json",
    ...buildAuthHeaders({ bearerToken, projectId }),
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
    credentials,
    headers: finalHeaders,
    body: serializedBody,
  });

  if (
    res.status === 401 &&
    redirectOnUnauthorized &&
    typeof window !== "undefined"
  ) {
    window.location.href = "/login";
    throw new ApiError("unauthorized", 401, null);
  }

  return parseResponse<T>(res);
}

export interface AuthorizeConnectionResponse {
  auth_url: string;
  state: string;
}

/** REST surface — auth and projects use the Next.js BFF; health hits the backend directly. */
export const api = {
  health: () => request<HealthResponse>("/health"),

  // --- Auth (BFF; user JWT in httpOnly cookie) ---

  login: (body: LoginRequest) =>
    bffRequest<AuthSuccessResponse>("/api/auth/login", {
      method: "POST",
      body,
      redirectOnUnauthorized: false,
    }),

  register: (body: RegisterRequest) =>
    bffRequest<AuthSuccessResponse>("/api/auth/register", {
      method: "POST",
      body,
      redirectOnUnauthorized: false,
    }),

  logout: () =>
    bffRequest<AuthSuccessResponse>("/api/auth/logout", {
      method: "POST",
      redirectOnUnauthorized: false,
    }),

  me: (options?: Pick<RequestOptions, "redirectOnUnauthorized">) =>
    bffRequest<AuthMeResponse>("/api/auth/me", options),

  // --- Projects (BFF; user JWT forwarded from cookie) ---

  listProjects: () => bffRequest<ProjectListResponse>("/api/projects"),

  createProject: (body: ProjectCreate) =>
    bffRequest<ProjectResponse>("/api/projects", {
      method: "POST",
      body,
    }),

  getProject: (projectId: string) =>
    bffRequest<ProjectResponse>(`/api/projects/${encodeURIComponent(projectId)}`),

  deleteProject: (projectId: string) =>
    bffRequest<void>(`/api/projects/${encodeURIComponent(projectId)}`, {
      method: "DELETE",
    }),

  // --- Sessions (BFF create; session Bearer for /session/me) ---

  createSession: (body: SessionCreate) =>
    bffRequest<SessionResponse>("/api/auth/session", {
      method: "POST",
      body,
    }),

  sessionMe: (sessionToken: string) =>
    bffRequest<AgentSessionResponse>("/api/auth/session/me", {
      bearerToken: sessionToken,
    }),

  // --- Connections (BFF; session id header) ---

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
  runtimeUrl: () => `${apiBaseUrl()}/api/v1/copilotkit/`,
  agentId: "signals_agent" as const,
};

// Re-export commonly used types for convenience at call sites.
export type {
  AgentSessionResponse,
  AuthMeResponse,
  LoginRequest,
  ProjectCreate,
  ProjectResponse,
  RegisterRequest,
  SessionCreate,
  SessionResponse,
  TokenResponse,
  UserResponse,
};

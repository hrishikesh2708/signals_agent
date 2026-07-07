/**
 * Server-side BFF (Backend-For-Frontend) helper.
 * Used only in Next.js Route Handlers — never imported client-side.
 *
 * Reads the httpOnly JWT cookie and forwards requests to FastAPI
 * with the Authorization header, so the browser never touches the token
 * or the backend URL directly.
 */
import { cookies } from "next/headers";

import { JWT_COOKIE } from "@/lib/auth";

const BACKEND_URL =
  process.env.BACKEND_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000";

export function backendBaseUrl(): string {
  return BACKEND_URL;
}

export async function backendFetch(
  path: string,
  init: RequestInit & { noAuth?: boolean; authorization?: string } = {},
): Promise<Response> {
  const { noAuth, authorization, headers: initHeaders, ...rest } = init;

  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(initHeaders as Record<string, string> | undefined),
  };

  if (authorization) {
    headers.Authorization = authorization;
  } else if (!noAuth) {
    const store = await cookies();
    const token = store.get(JWT_COOKIE)?.value;
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  return fetch(`${BACKEND_URL}/api/v1${path}`, {
    ...rest,
    headers,
    cache: "no-store",
  });
}

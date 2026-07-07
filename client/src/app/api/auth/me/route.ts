import { NextResponse } from "next/server";
import { cookies } from "next/headers";

import { parseApiErrorBody } from "@/lib/api-errors";
import { JWT_COOKIE } from "@/lib/auth";
import { backendFetch } from "@/lib/bff";
import { PROJECT_ID_COOKIE } from "@/lib/project-storage";
import type { UserResponse } from "@/lib/types";

function clearAuthCookies(response: NextResponse): NextResponse {
  response.cookies.set(JWT_COOKIE, "", { path: "/", maxAge: 0 });
  response.cookies.set(PROJECT_ID_COOKIE, "", { path: "/", maxAge: 0 });
  return response;
}

export async function GET() {
  const store = await cookies();
  const token = store.get(JWT_COOKIE)?.value;
  if (!token) {
    return NextResponse.json({ user: null }, { status: 401 });
  }

  const res = await backendFetch("/auth/me");

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
    if (res.status === 401) {
      return clearAuthCookies(
        NextResponse.json({ user: null }, { status: 401 }),
      );
    }
    const { message } = parseApiErrorBody(parsed, "request_failed");
    return NextResponse.json({ detail: message }, { status: res.status });
  }

  return NextResponse.json({ user: parsed as UserResponse });
}

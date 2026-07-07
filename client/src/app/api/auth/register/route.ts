import { NextResponse } from "next/server";

import { parseApiErrorBody } from "@/lib/api-errors";
import { JWT_COOKIE, jwtCookieOptions } from "@/lib/auth";
import { backendFetch } from "@/lib/bff";
import type { TokenResponse } from "@/lib/types";

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: "invalid_request_body" }, { status: 400 });
  }

  const res = await backendFetch("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    noAuth: true,
  });

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
    const { message, fieldErrors } = parseApiErrorBody(parsed, "register_failed");
    return NextResponse.json(
      { detail: message, errors: fieldErrors },
      { status: res.status },
    );
  }

  const token = parsed as TokenResponse;
  if (!token?.access_token) {
    return NextResponse.json(
      { detail: "invalid_backend_response" },
      { status: 502 },
    );
  }

  const response = NextResponse.json({ success: true }, { status: res.status });
  response.cookies.set(
    JWT_COOKIE,
    token.access_token,
    jwtCookieOptions(token.access_token),
  );
  return response;
}

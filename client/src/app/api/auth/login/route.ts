import { NextResponse } from "next/server";

import { parseApiErrorBody } from "@/lib/api-errors";
import { JWT_COOKIE, jwtCookieOptions } from "@/lib/auth";
import { backendBaseUrl } from "@/lib/bff";
import type { TokenResponse } from "@/lib/types";

interface LoginBody {
  email?: string;
  password?: string;
}

export async function POST(request: Request) {
  let body: LoginBody;
  try {
    body = (await request.json()) as LoginBody;
  } catch {
    return NextResponse.json(
      { detail: "invalid_request_body" },
      { status: 400 },
    );
  }

  const { email, password } = body;
  if (!email || !password) {
    return NextResponse.json(
      { detail: "email_and_password_required" },
      { status: 400 },
    );
  }

  const backendRes = await fetch(`${backendBaseUrl()}/api/v1/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({ email, password }),
    cache: "no-store",
  });

  const text = await backendRes.text();
  let parsed: unknown = null;
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = text;
    }
  }

  if (!backendRes.ok) {
    const { message, fieldErrors } = parseApiErrorBody(parsed, "login_failed");
    return NextResponse.json(
      { detail: message, errors: fieldErrors },
      { status: backendRes.status },
    );
  }

  const token = parsed as TokenResponse;
  if (!token?.access_token) {
    return NextResponse.json(
      { detail: "invalid_backend_response" },
      { status: 502 },
    );
  }

  const response = NextResponse.json({ success: true });
  response.cookies.set(JWT_COOKIE, token.access_token, jwtCookieOptions(token.access_token));
  return response;
}

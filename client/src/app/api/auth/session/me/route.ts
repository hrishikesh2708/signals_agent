import { NextResponse } from "next/server";

import { parseApiErrorBody } from "@/lib/api-errors";
import { backendFetch } from "@/lib/bff";

export async function GET(request: Request) {
  const authorization = request.headers.get("Authorization");
  if (!authorization) {
    return NextResponse.json({ detail: "unauthorized" }, { status: 401 });
  }

  const res = await backendFetch("/auth/session/me", {
    authorization,
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
    const { message } = parseApiErrorBody(parsed, "request_failed");
    return NextResponse.json({ detail: message }, { status: res.status });
  }

  return NextResponse.json(parsed);
}

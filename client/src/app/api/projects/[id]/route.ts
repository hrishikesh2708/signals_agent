import { NextResponse } from "next/server";

import { parseApiErrorBody } from "@/lib/api-errors";
import { backendFetch } from "@/lib/bff";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const res = await backendFetch(`/projects/${id}`);

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
    const { message } = parseApiErrorBody(parsed, "project_fetch_failed");
    return NextResponse.json({ detail: message }, { status: res.status });
  }

  return NextResponse.json(parsed);
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const res = await backendFetch(`/projects/${id}`, { method: "DELETE" });

  if (res.status === 204) {
    return new NextResponse(null, { status: 204 });
  }

  const text = await res.text();
  let parsed: unknown = null;
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = text;
    }
  }

  const { message } = parseApiErrorBody(parsed, "project_delete_failed");
  return NextResponse.json({ detail: message }, { status: res.status });
}

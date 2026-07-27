import { NextResponse } from "next/server";

import { parseApiErrorBody } from "@/lib/api-errors";
import { backendFetch } from "@/lib/bff";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ destination_id: string }> },
) {
  const { destination_id } = await params;
  const url = new URL(request.url);
  const projectId = url.searchParams.get("project_id");
  if (!projectId) {
    return NextResponse.json({ detail: "project_id is required" }, { status: 400 });
  }

  let body: unknown = {};
  try {
    body = await request.json();
  } catch {
    body = {};
  }

  const res = await backendFetch(
    `/connections/destinations/${encodeURIComponent(destination_id)}/mock-connect?project_id=${encodeURIComponent(projectId)}`,
    {
      method: "POST",
      apiPrefix: "",
      body: JSON.stringify(body ?? {}),
      headers: { "Content-Type": "application/json" },
    },
  );

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
    const { message } = parseApiErrorBody(parsed, "destination_mock_connect_failed");
    return NextResponse.json({ detail: message }, { status: res.status });
  }

  return NextResponse.json(parsed, { status: res.status });
}

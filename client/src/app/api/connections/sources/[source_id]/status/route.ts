import { NextResponse } from "next/server";

import { parseApiErrorBody } from "@/lib/api-errors";
import { backendFetch } from "@/lib/bff";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ source_id: string }> },
) {
  const { source_id } = await params;
  const url = new URL(request.url);
  const projectId = url.searchParams.get("project_id");
  if (!projectId) {
    return NextResponse.json({ detail: "project_id is required" }, { status: 400 });
  }

  const res = await backendFetch(
    `/connections/sources/${encodeURIComponent(source_id)}/status?project_id=${encodeURIComponent(projectId)}`,
    { method: "GET", apiPrefix: "" },
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
    const { message } = parseApiErrorBody(parsed, "source_status_failed");
    return NextResponse.json({ detail: message }, { status: res.status });
  }

  return NextResponse.json(parsed);
}

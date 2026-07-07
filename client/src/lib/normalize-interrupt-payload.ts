import { parseJson } from "@copilotkit/shared";
import type { ApprovalInterruptPayload } from "@/lib/interrupt-types";

export function normalizeInterruptPayload(raw: unknown): ApprovalInterruptPayload {
  let payload: unknown = raw;
  if (typeof payload === "string") {
    payload = parseJson(payload, payload);
  }
  if (payload && typeof payload === "object" && !Array.isArray(payload)) {
    const obj = payload as Record<string, unknown>;
    if (!obj.type && obj.value && typeof obj.value === "object" && !Array.isArray(obj.value)) {
      payload = obj.value;
    }
    return payload as ApprovalInterruptPayload;
  }
  return (typeof raw === "object" && raw !== null && !Array.isArray(raw)
    ? raw
    : {}) as ApprovalInterruptPayload;
}

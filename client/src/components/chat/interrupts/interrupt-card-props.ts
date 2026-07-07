import type { ApprovalInterruptPayload } from "@/lib/interrupt-types";

export interface InterruptCardProps {
  payload: ApprovalInterruptPayload;
  sessionId: string;
  onApprove: (response: unknown) => void;
  onReject: (reason?: string) => void;
}

/** @deprecated Use InterruptCardProps — kept for live chat wiring compatibility. */
export type HitlApprovalCardProps = InterruptCardProps;

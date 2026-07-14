"use client";

import { normalizeInterruptPayload } from "@/lib/normalize-interrupt-payload";
import type { InterruptCardProps } from "@/components/chat/interrupts/interrupt-card-props";
import { ActivateConfirmInterruptCard } from "@/components/chat/interrupts/activate-confirm-interrupt-card";
import { ActivationConfirmInterruptCard } from "@/components/chat/interrupts/activation-confirm-interrupt-card";
import { CanonicalMappingInterruptCard } from "@/components/chat/interrupts/canonical-mapping-interrupt-card";
import { CanonicalNeedsInterruptCard } from "@/components/chat/interrupts/canonical-needs-interrupt-card";
import { CheckChannelsInterruptCard } from "@/components/chat/interrupts/check-channels-interrupt-card";
import { CheckConnectionInterruptCard } from "@/components/chat/interrupts/check-connection-interrupt-card";
import { ConnectSourceInterruptCard } from "@/components/chat/interrupts/connect-source-interrupt-card";
import { CoverageBreakdownInterruptCard } from "@/components/chat/interrupts/coverage-breakdown-interrupt-card";
import { DestinationMetadataInterruptCard } from "@/components/chat/interrupts/destination-metadata-interrupt-card";
import { FunnelPromptInterruptCard } from "@/components/chat/interrupts/funnel-prompt-interrupt-card";
import { FunnelStagesInterruptCard } from "@/components/chat/interrupts/funnel-stages-interrupt-card";
import { GoogleAdsAccountInterruptCard } from "@/components/chat/interrupts/google-ads-account-interrupt-card";
import { GoogleConversionActionInterruptCard } from "@/components/chat/interrupts/google-conversion-action-interrupt-card";
import { IntentClarifyInterruptCard } from "@/components/chat/interrupts/intent-clarify-interrupt-card";
import { MappingMatrixInterruptCard } from "@/components/chat/interrupts/mapping-matrix-interrupt-card";
import { MappingReviewInterruptCard } from "@/components/chat/interrupts/mapping-review-interrupt-card";
import { ResolveFieldsInterruptCard } from "@/components/chat/interrupts/resolve-fields-interrupt-card";
import { SelectObjectInterruptCard } from "@/components/chat/interrupts/select-object-interrupt-card";
import { ValidationDryRunInterruptCard } from "@/components/chat/interrupts/validation-dry-run-interrupt-card";
import { ValidationErrorsInterruptCard } from "@/components/chat/interrupts/validation-errors-interrupt-card";

export type { InterruptCardProps, HitlApprovalCardProps } from "@/components/chat/interrupts/interrupt-card-props";

export function HitlApprovalCard(props: InterruptCardProps) {
  const payload = normalizeInterruptPayload(props.payload);
  const cardProps = { ...props, payload };

  switch (payload.type) {
    case "intent_clarify":
      return <IntentClarifyInterruptCard {...cardProps} />;
    case "connect_source":
      return <ConnectSourceInterruptCard {...cardProps} />;
    case "check_connection":
      return <CheckConnectionInterruptCard {...cardProps} />;
    case "select_object":
      return <SelectObjectInterruptCard {...cardProps} />;
    case "check_channels":
      return <CheckChannelsInterruptCard {...cardProps} />;
    case "mapping_review":
      return <MappingReviewInterruptCard {...cardProps} />;
    case "canonical_mapping":
      return <CanonicalMappingInterruptCard {...cardProps} />;
    case "resolve_fields":
      return <ResolveFieldsInterruptCard {...cardProps} />;
    case "activate_confirm":
      return <ActivateConfirmInterruptCard {...cardProps} />;
    case "funnel_prompt":
      return <FunnelPromptInterruptCard {...cardProps} />;
    case "funnel_stages":
      return <FunnelStagesInterruptCard {...cardProps} />;
    case "validation_errors":
      return <ValidationErrorsInterruptCard {...cardProps} />;
    case "activation_confirm":
      return <ActivationConfirmInterruptCard {...cardProps} />;
    case "mapping_matrix":
      return <MappingMatrixInterruptCard {...cardProps} />;
    case "google_ads_account":
      return <GoogleAdsAccountInterruptCard {...cardProps} />;
    case "google_conversion_action":
      return <GoogleConversionActionInterruptCard {...cardProps} />;
    case "coverage_breakdown":
      return <CoverageBreakdownInterruptCard {...cardProps} />;
    case "canonical_needs":
      return <CanonicalNeedsInterruptCard {...cardProps} />;
    case "validation_dry_run":
      return <ValidationDryRunInterruptCard {...cardProps} />;
    case "destination_metadata":
      return <DestinationMetadataInterruptCard {...cardProps} />;
    default:
      return null;
  }
}

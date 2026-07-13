from __future__ import annotations

from typing import Mapping

from app.destinations.registry import get_destination_registry
from app.graph.state import CONFIDENCE_THRESHOLD, MatchedToken, ScopePhase
from app.graph.validators.common import connector_to_platform, dedupe, get_lookup
from app.internal.signal_type import (
    get_active_signal_type_ids,
    get_signal_type,
)
from app.sources.registry import get_source_registry


def sanitize_scope_hints(
    raw_tokens: list[object],
    text: str = "",
) -> tuple[list[MatchedToken], list[str]]:
    """Validate rich matched_tokens; infer catalog from id; platforms = product_groups."""
    del text  # kept for call-site compatibility; platforms come from product_group ids only
    source_registry = get_source_registry()
    destination_registry = get_destination_registry()
    active_signal_ids = get_active_signal_type_ids()
    signal_by_id = {signal.id: signal for signal in get_signal_type().signal_types}

    product_groups = {
        entry.product_group
        for entry in destination_registry.list_destinations()
        if entry.product_group
    }
    group_labels: dict[str, set[str]] = {}
    for entry in destination_registry.list_destinations():
        if entry.product_group:
            group_labels.setdefault(entry.product_group, set()).add(entry.short_label)

    matched: list[MatchedToken] = []
    seen: set[str] = set()

    for item in raw_tokens:
        if not isinstance(item, dict):
            continue

        raw = item.get("raw")
        token_id = item.get("id")
        if not isinstance(raw, str) or not isinstance(token_id, str):
            continue
        token_id = token_id.strip()
        if not token_id:
            continue

        try:
            confidence = float(item.get("confidence", 0.0))
        except (TypeError, ValueError):
            continue
        if confidence < CONFIDENCE_THRESHOLD:
            continue

        display_name: str | None = None
        canonical_id: str | None = None

        if token_id in source_registry.source_ids:
            source = source_registry.get_source(token_id)
            if source is None:
                continue
            canonical_id = token_id
            display_name = source.display_name
        elif token_id in product_groups:
            canonical_id = token_id
            labels = group_labels.get(canonical_id, set())
            display_name = next(iter(labels)) if len(labels) == 1 else canonical_id.title()
        elif token_id in destination_registry.destination_ids:
            mapped = connector_to_platform(token_id)
            if mapped is None or mapped not in product_groups:
                continue
            canonical_id = mapped
            labels = group_labels.get(canonical_id, set())
            display_name = next(iter(labels)) if len(labels) == 1 else canonical_id.title()
        elif token_id in active_signal_ids:
            signal = signal_by_id.get(token_id)
            if signal is None:
                continue
            canonical_id = token_id
            display_name = signal.display_name
        else:
            continue

        if canonical_id in seen:
            continue
        seen.add(canonical_id)

        matched.append(
            {
                "raw": raw,
                "id": canonical_id,
                "display_name": display_name,
                "confidence": confidence,
            }
        )

    mentioned_platforms = dedupe(
        [token["id"] for token in matched if token["id"] in product_groups]
    )
    return matched, mentioned_platforms


def matched_token_ids(scope: ScopePhase | Mapping[str, object] | None) -> list[str]:
    """Adapter: rich scope tokens → flat id list for intent validators (Step 2 bridge)."""
    if not scope:
        return []
    tokens = scope.get("matched_tokens") or []
    if not isinstance(tokens, list):
        return []
    ids: list[str] = []
    for token in tokens:
        if isinstance(token, dict):
            token_id = token.get("id")
            if isinstance(token_id, str):
                ids.append(token_id)
    return ids


def validate_scope_json(raw: dict | None, latest_text: str = "") -> ScopePhase:
    fallback: ScopePhase = {
        "status": "out_of_scope",
        "reply_kind": "redirect",
        "matched_tokens": [],
        "mentioned_platforms": [],
    }
    if not isinstance(raw, dict):
        return fallback

    status = raw.get("status")
    reply_kind = raw.get("reply_kind")
    raw_tokens = raw.get("matched_tokens")

    if status not in ("in_scope", "out_of_scope"):
        return fallback
    if reply_kind not in ("ack", "greeting", "redirect"):
        return fallback

    if status == "in_scope" and reply_kind != "ack":
        reply_kind = "ack"
    if status == "out_of_scope" and reply_kind == "ack":
        reply_kind = "redirect"

    if not isinstance(raw_tokens, list):
        raw_tokens = []

    matched_tokens, mentioned_platforms = sanitize_scope_hints(raw_tokens, latest_text)

    return {
        "status": status,
        "reply_kind": reply_kind,
        "matched_tokens": matched_tokens,
        "mentioned_platforms": mentioned_platforms,
    }


def normalize_matched_tokens(tokens: list[str]) -> list[str]:
    return get_lookup().normalize_tokens(tokens)

from __future__ import annotations

import json
from typing import Any, Literal

ChannelStatus = Literal["connected", "skipped", "not_connected"]


def build_check_channels_payload(
    *,
    channels: list[dict[str, Any]],
) -> dict[str, Any]:
    """HITL payload for the check_channels interrupt card."""
    return {
        "type": "check_channels",
        "channels": channels,
    }


def format_check_channels_ack(*, connected_labels: list[str]) -> str:
    """Build step_complete JSON after destinations are settled."""
    if not connected_labels:
        message = "Destinations ready"
    elif len(connected_labels) == 1:
        message = f"{connected_labels[0]} connected"
    else:
        message = f"{', '.join(connected_labels)} connected"
    return json.dumps({"type": "step_complete", "message": message})


def parse_check_channels_resume(
    resume: Any,
) -> tuple[str | None, str | None]:
    """Return ``(action, platform_id)`` from interrupt resume.

    Actions: ``connected`` | ``skip`` | ``confirm_all``.
    """
    if not isinstance(resume, dict):
        return None, None
    action = resume.get("action")
    if not isinstance(action, str) or action not in {"connected", "skip", "confirm_all"}:
        return None, None
    platform_id = resume.get("platform_id")
    if platform_id is not None and not isinstance(platform_id, str):
        return None, None
    if action in {"connected", "skip"} and not platform_id:
        return None, None
    return action, platform_id


def all_settled(statuses: dict[str, str]) -> bool:
    if not statuses:
        return False
    return all(status in {"connected", "skipped"} for status in statuses.values())


def has_connected(statuses: dict[str, str]) -> bool:
    return any(status == "connected" for status in statuses.values())

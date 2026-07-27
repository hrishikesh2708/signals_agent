from __future__ import annotations

import json
from typing import Any


def build_source_connection_payload(
    *,
    source_id: str,
    source_label: str,
    project_id: str,
    project_name: str,
) -> dict[str, str]:
    """Static HITL payload for the source_connection interrupt card."""
    return {
        "type": "source_connection",
        "source_label": source_label,
        "project_name": project_name,
        "source_id": source_id,
        "project_id": project_id,
    }


def format_source_connection_ack(source_label: str) -> str:
    """Build step_complete JSON after a usable source connection (message only)."""
    return json.dumps(
        {"type": "step_complete", "message": f"{source_label} connected"}
    )


def parse_source_connection_resume(resume: Any) -> dict[str, Any] | None:
    """Accept ``{ action: \"connected\", source_id? }`` from the interrupt card."""
    if not isinstance(resume, dict):
        return None
    if resume.get("action") != "connected":
        return None
    return resume

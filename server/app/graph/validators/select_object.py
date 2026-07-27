from __future__ import annotations

import json
from typing import Any


def validate_recommended(recommended: object, options: list[str]) -> str | None:
    """Return recommended only when it is an exact member of options."""
    if not isinstance(recommended, str) or not recommended:
        return None
    if recommended in options:
        return recommended
    return None


def build_select_object_payload(
    *,
    options: list[str],
    recommended: str | None,
    source_id: str,
) -> dict[str, Any]:
    """Static HITL payload for the select_object interrupt card."""
    payload: dict[str, Any] = {
        "type": "select_object",
        "title": "Select object",
        "options": list(options),
        "source_id": source_id,
    }
    if recommended is not None:
        payload["recommended"] = recommended
        payload["default_selected"] = recommended
    return payload


def format_select_object_ask(*, source_label: str, project_name: str | None) -> str:
    """First Visit A bubble — connection ack + object question."""
    name = project_name or "this project"
    return (
        f"{source_label} is connected as {name}. "
        "Which object holds the conversions you want to send?"
    )


def format_select_object_ack(object_name: str) -> str:
    """Build step_complete JSON after the user selects an object."""
    return json.dumps(
        {
            "type": "step_complete",
            "message": f"{object_name} selected as source object",
        }
    )


def parse_select_object_resume(resume: Any, options: list[str]) -> str | None:
    """Accept ``{ selected: \"<object>\" }`` when selected ∈ options."""
    if not isinstance(resume, dict):
        return None
    selected = resume.get("selected")
    if not isinstance(selected, str) or not selected:
        return None
    if selected not in options:
        return None
    return selected

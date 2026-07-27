from __future__ import annotations

from uuid import UUID

from langchain_core.messages import AIMessage
from langgraph.types import interrupt
from sqlalchemy import select

from app.database import async_session_factory
from app.destinations import get_destination
from app.graph.handlers.check_channels import compose_check_channels_messages
from app.graph.llm import get_llm
from app.graph.state import DestinationsPhase, SignalsState
from app.graph.validators.check_channels import (
    all_settled,
    build_check_channels_payload,
    format_check_channels_ack,
    has_connected,
    parse_check_channels_resume,
)
from app.models.connections import DestinationConnection


async def _connected_destination_ids(project_id: UUID, destination_ids: list[str]) -> set[str]:
    if not destination_ids:
        return set()
    async with async_session_factory() as db:
        result = await db.execute(
            select(DestinationConnection.destination_type).where(
                DestinationConnection.project_id == project_id,
                DestinationConnection.destination_type.in_(destination_ids),
            )
        )
        return {row[0] for row in result.all()}


def _build_statuses(
    destination_ids: list[str],
    *,
    connected: set[str],
    skipped: set[str],
) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for dest_id in destination_ids:
        if dest_id in skipped:
            statuses[dest_id] = "skipped"
        elif dest_id in connected:
            statuses[dest_id] = "connected"
        else:
            statuses[dest_id] = "not_connected"
    return statuses


def _channel_entries(
    destination_ids: list[str],
    statuses: dict[str, str],
    *,
    project_id: str,
) -> list[dict]:
    channels: list[dict] = []
    for dest_id in destination_ids:
        dest = get_destination(dest_id)
        label = dest.short_label if dest is not None else dest_id
        detail = dest.detail if dest is not None else ""
        status = statuses.get(dest_id, "not_connected")
        if status == "connected" and detail:
            entry_detail = detail
        elif status == "skipped":
            entry_detail = "Skipped for now"
        elif detail:
            entry_detail = f"No active connection · {detail}"
        else:
            entry_detail = "No active connection"
        channels.append(
            {
                "id": dest_id,
                "label": label,
                "status": status,
                "detail": entry_detail,
                "connector_slug": dest_id,
                "project_id": project_id,
            }
        )
    return channels


def _labels(destination_ids: list[str]) -> list[str]:
    labels: list[str] = []
    for dest_id in destination_ids:
        dest = get_destination(dest_id)
        labels.append(dest.short_label if dest is not None else dest_id)
    return labels


def _connected_labels(statuses: dict[str, str]) -> list[str]:
    labels: list[str] = []
    for dest_id, status in statuses.items():
        if status != "connected":
            continue
        dest = get_destination(dest_id)
        labels.append(dest.short_label if dest is not None else dest_id)
    return labels


def _pending_phase(
    *,
    destination_ids: list[str],
    statuses: dict[str, str],
    skipped: list[str],
    channels_hitl_prompted: bool,
) -> DestinationsPhase:
    return {
        "destination_ids": list(destination_ids),
        "statuses": dict(statuses),
        "skipped": list(skipped),
        "status": "pending",
        "channels_hitl_prompted": channels_hitl_prompted,
    }


def _complete_phase(
    *,
    destination_ids: list[str],
    statuses: dict[str, str],
    skipped: list[str],
) -> DestinationsPhase:
    return {
        "destination_ids": list(destination_ids),
        "statuses": dict(statuses),
        "skipped": list(skipped),
        "status": "complete",
        "channels_hitl_prompted": False,
    }


async def check_channels_node(state: SignalsState) -> dict:
    """Connect/skip destinations until all settled with ≥1 connected.

    Visit A: LLM intro messages + ``channels_hitl_prompted``.
    Visit B+: ``check_channels`` HITL; resume updates skip/DB re-check.
    """
    source = state.get("source")
    if not source or not source.get("object_name"):
        return {}

    intent = state.get("intent") or {}
    destination_ids = list(intent.get("destinations") or [])
    if not destination_ids:
        return {
            "messages": [
                AIMessage(
                    content=(
                        "I couldn't find any destinations for this integration. "
                        "Please confirm your channels and try again."
                    )
                )
            ]
        }

    project_id_raw = state.get("project_id")
    if not project_id_raw:
        return {
            "messages": [
                AIMessage(
                    content=(
                        "I need an active project to check destination connections. "
                        "Please select a project and try again."
                    )
                )
            ]
        }

    try:
        project_id = UUID(str(project_id_raw))
    except ValueError:
        return {
            "messages": [
                AIMessage(content="I couldn't verify destinations for this project.")
            ]
        }

    phase = state.get("destinations")
    skipped = list((phase or {}).get("skipped") or [])
    skipped_set = set(skipped)

    connected = await _connected_destination_ids(project_id, destination_ids)
    statuses = _build_statuses(
        destination_ids,
        connected=connected,
        skipped=skipped_set,
    )
    labels = _labels(destination_ids)
    first_pending_id = next(
        (dest_id for dest_id in destination_ids if statuses.get(dest_id) == "not_connected"),
        None,
    )
    first_pending_label = None
    if first_pending_id is not None:
        dest = get_destination(first_pending_id)
        first_pending_label = dest.short_label if dest is not None else first_pending_id

    # Visit A: LLM intro + next-connect messages.
    if not (phase or {}).get("channels_hitl_prompted", False):
        llm = get_llm()
        intro, next_line = await compose_check_channels_messages(
            llm,
            destination_labels=labels,
            first_pending_label=first_pending_label,
        )
        return {
            "destinations": _pending_phase(
                destination_ids=destination_ids,
                statuses=statuses,
                skipped=skipped,
                channels_hitl_prompted=True,
            ),
            "messages": [
                AIMessage(content=intro),
                AIMessage(content=next_line),
            ],
        }

    # Already complete — idempotent.
    if all_settled(statuses) and has_connected(statuses):
        return {
            "destinations": _complete_phase(
                destination_ids=destination_ids,
                statuses=statuses,
                skipped=skipped,
            ),
            "messages": [
                AIMessage(
                    content=format_check_channels_ack(
                        connected_labels=_connected_labels(statuses)
                    )
                )
            ],
        }

    # All skipped without a connection — block and re-interrupt after a nudge.
    if all_settled(statuses) and not has_connected(statuses):
        resume = interrupt(
            build_check_channels_payload(
                channels=_channel_entries(
                    destination_ids,
                    statuses,
                    project_id=str(project_id),
                )
            )
        )
        action, platform_id = parse_check_channels_resume(resume)
        messages = [
            AIMessage(
                content=(
                    "Connect at least one destination to continue. "
                    "You can skip the others after one is connected."
                )
            )
        ]
        if action == "skip" and platform_id and platform_id in destination_ids:
            if platform_id not in skipped_set:
                skipped.append(platform_id)
            return {
                "destinations": _pending_phase(
                    destination_ids=destination_ids,
                    statuses=statuses,
                    skipped=skipped,
                    channels_hitl_prompted=True,
                ),
                "messages": messages,
            }
        # connected / confirm_all / invalid — loop; DB will be re-read next visit
        return {
            "destinations": _pending_phase(
                destination_ids=destination_ids,
                statuses=statuses,
                skipped=skipped,
                channels_hitl_prompted=True,
            ),
            "messages": messages,
        }

    resume = interrupt(
        build_check_channels_payload(
            channels=_channel_entries(
                destination_ids,
                statuses,
                project_id=str(project_id),
            )
        )
    )
    action, platform_id = parse_check_channels_resume(resume)

    if action == "skip" and platform_id and platform_id in destination_ids:
        if platform_id not in skipped_set:
            skipped.append(platform_id)
        skipped_set = set(skipped)
        connected = await _connected_destination_ids(project_id, destination_ids)
        statuses = _build_statuses(
            destination_ids,
            connected=connected,
            skipped=skipped_set,
        )
        if all_settled(statuses) and has_connected(statuses):
            return {
                "destinations": _complete_phase(
                    destination_ids=destination_ids,
                    statuses=statuses,
                    skipped=skipped,
                ),
                "messages": [
                    AIMessage(
                        content=format_check_channels_ack(
                            connected_labels=_connected_labels(statuses)
                        )
                    )
                ],
            }
        if all_settled(statuses) and not has_connected(statuses):
            return {
                "destinations": _pending_phase(
                    destination_ids=destination_ids,
                    statuses=statuses,
                    skipped=skipped,
                    channels_hitl_prompted=True,
                ),
                "messages": [
                    AIMessage(
                        content=(
                            "Connect at least one destination to continue. "
                            "You can skip the others after one is connected."
                        )
                    )
                ],
            }
        return {
            "destinations": _pending_phase(
                destination_ids=destination_ids,
                statuses=statuses,
                skipped=skipped,
                channels_hitl_prompted=True,
            ),
        }

    # connected / confirm_all — re-read DB and settle if ready
    connected = await _connected_destination_ids(project_id, destination_ids)
    statuses = _build_statuses(
        destination_ids,
        connected=connected,
        skipped=skipped_set,
    )
    if all_settled(statuses) and has_connected(statuses):
        return {
            "destinations": _complete_phase(
                destination_ids=destination_ids,
                statuses=statuses,
                skipped=skipped,
            ),
            "messages": [
                AIMessage(
                    content=format_check_channels_ack(
                        connected_labels=_connected_labels(statuses)
                    )
                )
            ],
        }

    if action == "confirm_all" and not has_connected(statuses):
        return {
            "destinations": _pending_phase(
                destination_ids=destination_ids,
                statuses=statuses,
                skipped=skipped,
                channels_hitl_prompted=True,
            ),
            "messages": [
                AIMessage(
                    content=(
                        "Connect at least one destination to continue. "
                        "You can skip the others after one is connected."
                    )
                )
            ],
        }

    return {
        "destinations": _pending_phase(
            destination_ids=destination_ids,
            statuses=statuses,
            skipped=skipped,
            channels_hitl_prompted=True,
        ),
    }

from __future__ import annotations

from uuid import UUID

from langchain_core.messages import AIMessage
from langgraph.types import interrupt

from app.graph.handlers.select_object import compose_object_suggestion
from app.graph.llm import get_llm
from app.graph.state import SignalsState, SourcePhase
from app.graph.validators.select_object import (
    build_select_object_payload,
    format_select_object_ack,
    format_select_object_ask,
    parse_select_object_resume,
)
from app.services.source_describe import object_exists_via_describe
from app.sources import get_source


async def select_object_node(state: SignalsState) -> dict:
    """Ask (LLM suggest) then interrupt (static picker) for CRM object selection.

    Visit A: connection ask (+ optional rationale) with ``object_hitl_prompted``.
    Visit B: ``select_object`` HITL; on resume validate via describe then step_complete.
    """
    source = state.get("source")
    if not source or source.get("status") != "connected":
        return {}

    source_id = source["source_id"]
    catalog = get_source(source_id)
    options = list(catalog.objects_common) if catalog is not None else []
    if not options:
        return {
            "messages": [
                AIMessage(
                    content=(
                        "I couldn't find any eligible objects for this source. "
                        "Please check the source configuration and try again."
                    )
                )
            ]
        }

    # Visit A: ask messages + optional LLM recommendation.
    if not source.get("object_hitl_prompted", False):
        llm = get_llm()
        intent = state.get("intent") or {}
        recommended, rationale = await compose_object_suggestion(
            llm,
            source_label=source["source_label"],
            signal_type=intent.get("signal_type"),
            project_name=source.get("project_name"),
            options=options,
        )

        ask = format_select_object_ask(
            source_label=source["source_label"],
            project_name=source.get("project_name"),
        )
        content = f"{ask}\n\n{rationale}" if rationale else ask

        updated: SourcePhase = {
            **source,
            "recommended_object": recommended,
            "object_hitl_prompted": True,
            "object_name": None,
        }
        return {"source": updated, "messages": [AIMessage(content=content)]}

    # Visit B: static picker interrupt → YAML + describe validate → step_complete.
    recommended = source.get("recommended_object")
    if recommended is not None and recommended not in options:
        recommended = None

    resume = interrupt(
        build_select_object_payload(
            options=options,
            recommended=recommended,
            source_id=source_id,
        )
    )
    selected = parse_select_object_resume(resume, options)
    if selected is None:
        return {
            "messages": [
                AIMessage(
                    content=(
                        "That object isn't available for this source. "
                        "Please pick one from the list."
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
                        "I couldn't verify that object without an active project. "
                        "Please pick again after selecting a project."
                    )
                )
            ]
        }

    try:
        project_id = UUID(str(project_id_raw))
    except ValueError:
        return {
            "messages": [
                AIMessage(
                    content=(
                        "I couldn't verify that object for this project. "
                        "Please pick one from the list."
                    )
                )
            ]
        }

    exists = await object_exists_via_describe(project_id, source_id, selected)
    if not exists:
        return {
            "messages": [
                AIMessage(
                    content=(
                        f"I couldn't confirm {selected} in your connected account. "
                        "Please pick another object from the list."
                    )
                )
            ]
        }

    updated_source: SourcePhase = {
        **source,
        "object_name": selected,
        "object_hitl_prompted": False,
    }
    return {
        "source": updated_source,
        "messages": [AIMessage(content=format_select_object_ack(selected))],
    }

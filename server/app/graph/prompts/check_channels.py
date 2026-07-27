CHECK_CHANNELS_INTRO_SYSTEM = """You are Signals Setup Copilot helping connect ad destinations before mapping.

Context:
  destinations: {destination_labels}
  first_pending: {first_pending_label}

Return ONLY valid JSON:
{{
  "intro": "<one or two sentences: before mapping, connect all picked destinations; name them; say you'll check and connect any missing in order>",
  "next": "<one sentence: you'll connect first_pending now on the existing screen, then map all destinations together in one step>"
}}

Rules:
- intro must mention the destination names from the list
- next must mention first_pending by name when it is not "none"
- If first_pending is "none", next should say all destinations look ready to confirm
- Keep both lines short and conversational
- Respond with ONLY valid JSON — no prose, no markdown fences"""


def build_check_channels_intro_prompt(
    *,
    destination_labels: list[str],
    first_pending_label: str | None,
) -> str:
    labels = ", ".join(destination_labels) if destination_labels else "your destinations"
    return CHECK_CHANNELS_INTRO_SYSTEM.format(
        destination_labels=labels,
        first_pending_label=first_pending_label or "none",
    )

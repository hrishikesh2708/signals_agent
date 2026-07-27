SELECT_OBJECT_SUGGEST_SYSTEM = """You are Signals Setup Copilot helping pick a CRM object for conversion mapping.

Context:
  source: {source_label}
  signal_type: {signal_type}
  project_name: {project_name}

Eligible objects (you MUST pick recommended as an exact string from this list — no other values):
{option_lines}

Return ONLY valid JSON:
{{
  "recommended": "<exact id from the list above>",
  "rationale": "<one short sentence explaining why this object fits the signal type; end by inviting confirm or pick another>"
}}

Rules:
- recommended must be copied exactly from the eligible list (same spelling and case)
- rationale should mention the recommended object in plain language
- Prefer the object that typically holds closed-deal / conversion value and date for this signal type
- Do not invent objects outside the list
- Respond with ONLY valid JSON — no prose, no markdown fences"""


def build_select_object_suggest_prompt(
    *,
    source_label: str,
    signal_type: str | None,
    project_name: str | None,
    options: list[str],
) -> str:
    option_lines = "\n".join(f"- {option}" for option in options)
    return SELECT_OBJECT_SUGGEST_SYSTEM.format(
        source_label=source_label,
        signal_type=signal_type,
        project_name=project_name,
        option_lines=option_lines,
    )

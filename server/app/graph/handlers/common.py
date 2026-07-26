import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# AG-UI streams on_chat_model_* unless metadata opts out — keep internal LLM
# calls off the transcript (node return still adds the user-facing AIMessage).
SILENT_LLM_CONFIG: dict[str, Any] = {
    "metadata": {
        "emit-messages": False,
        "emit-tool-calls": False,
    }
}


def parse_json_response(content: str) -> dict | None:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("LLM response: failed to parse JSON")
        return None

    if not isinstance(parsed, dict):
        return None
    return parsed


def display_name(user_name: str | None) -> str:
    return user_name.strip() if user_name and user_name.strip() else "there"

import json
import logging
import re

logger = logging.getLogger(__name__)


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

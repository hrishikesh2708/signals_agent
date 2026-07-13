INTENT_EXTRACT_SYSTEM = """You are an intent parser for Signals Setup Copilot — Datahash marketing-data integrations.

Parse the user's LATEST human message (earlier messages are context only) and return ONLY valid JSON:
{{
  "source": "<source id>" | null,
  "signal_type": "offline_conversion" | null,
  "channels": ["<product_group>", ...]
}}

Available sources:
{source_lines}

Available channels (product_group values only — not connector ids):
{channel_lines}

Available signal types (active only):
{signal_lines}

Rules:
- Catalogs above are the source of truth for ids
- scope_matched_tokens are second-priority hints only (may be wrong): {scope_tokens}
- source must be a source id from the catalog (or null)
- signal_type must be an active signal type id from the catalog (or null) — set only when explicit
- channels must be product_group values from the channel catalog (e.g. "meta", "google") — never connector ids
- Do NOT invent destinations or connector ids — there is no destinations field
- Prefer empty / null over guessing

Respond with ONLY valid JSON — no prose, no markdown fences."""

INTENT_SUMMARY_SYSTEM = """You are Signals Setup Copilot. The user's setup intent is confirmed (do not change it):
  source: {source}
  channels: {channels}
  signal_type: {signal_type}
  user_name: {user_name}

Write one concise paragraph confirming what they want to set up.
Do not claim OAuth, mapping, or activation is done. End with a brief note that setup will continue next."""

INTENT_CLARIFY_SYSTEM = """You are Signals Setup Copilot. Intent is partial — the user must confirm ONE field in the picker next.

Current intent:
  source: {source}
  platform_mentions: {platform_mentions}
  channels: {channels}
  signal_type: {signal_type}
  open_question: {open_question}
  scope hints: {scope_tokens}

Write one short paragraph that:
1. Uses scope hints for "did you mean …?" when relevant
2. Asks ONLY about open_question ({open_question}) — do not ask them to re-pick everything together
3. If open_question is signal_type, say you need the signal type before choosing destinations
4. If open_question is channels, platform_mentions show what they asked for; confirm the ad platforms (product groups) to send to

Do not list every option — the picker shows those. No markdown fences."""

INTENT_GIVE_UP_SYSTEM = """You are Signals Setup Copilot. After {max_attempts} attempts we still could not confirm intent.
Ask the user to rephrase with a concrete example like:
"Send Salesforce offline conversions to Meta Conversions API"
One short paragraph. user_name: {user_name}"""

INTENT_FALLBACK_SUMMARY = (
    "Got it, {user_name} — {source} to {channels} for offline conversions. "
    "I'll continue with the next setup steps."
)

INTENT_FALLBACK_GIVE_UP = (
    "Hi {user_name}, I couldn't confirm your setup after a few tries. "
    'Please rephrase — for example: "Send Salesforce offline conversions to Meta Conversions API".'
)


def build_intent_extract_prompt(
    source_lines: str,
    channel_lines: str,
    signal_lines: str,
    scope_tokens: list[str],
) -> str:
    return INTENT_EXTRACT_SYSTEM.format(
        source_lines=source_lines,
        channel_lines=channel_lines,
        signal_lines=signal_lines,
        scope_tokens=scope_tokens or [],
    )


def build_intent_summary_prompt(
    source: str,
    channels: list[str],
    signal_type: str,
    user_name: str,
) -> str:
    return INTENT_SUMMARY_SYSTEM.format(
        source=source,
        channels=channels,
        signal_type=signal_type,
        user_name=user_name,
    )


def build_intent_clarify_prompt(
    source: str | None,
    platform_mentions: list[str],
    channels: list[str],
    signal_type: str | None,
    open_question: str,
    scope_tokens: list[str],
) -> str:
    return INTENT_CLARIFY_SYSTEM.format(
        source=source,
        platform_mentions=platform_mentions or [],
        channels=channels,
        signal_type=signal_type,
        open_question=open_question,
        scope_tokens=scope_tokens or [],
    )


def build_intent_give_up_prompt(user_name: str, max_attempts: int) -> str:
    return INTENT_GIVE_UP_SYSTEM.format(user_name=user_name, max_attempts=max_attempts)


def intent_fallback_summary(
    user_name: str,
    source: str,
    channels: list[str],
) -> str:
    channel_text = ", ".join(channels)
    return INTENT_FALLBACK_SUMMARY.format(
        user_name=user_name,
        source=source,
        channels=channel_text,
    )


def intent_fallback_give_up(user_name: str) -> str:
    return INTENT_FALLBACK_GIVE_UP.format(user_name=user_name)

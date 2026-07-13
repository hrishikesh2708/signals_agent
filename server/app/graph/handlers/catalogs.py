from app.destinations import get_destination_registry
from app.internal.signal_type import get_signal_type
from app.sources import get_source_registry


def format_source_lines() -> str:
    lines = [
        f'  "{source.id}"  ({source.display_name})'
        for source in get_source_registry().list_sources()
    ]
    return "\n".join(lines) or "  (none)"


def format_channel_lines() -> str:
    """Slim channel catalog (product_group + short_label only) — no connector ids."""
    lines: list[str] = []
    seen: set[str] = set()
    for entry in get_destination_registry().list_destinations():
        if not entry.product_group:
            continue
        key = f"{entry.product_group}|{entry.short_label}"
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"  product_group={entry.product_group}  short_label={entry.short_label}")
    return "\n".join(lines) or "  (none)"


def format_signal_type_lines() -> str:
    """Active signal types only — id + display_name for classify prompts."""
    lines = [
        f'  "{signal.id}"  ({signal.display_name})'
        for signal in get_signal_type().signal_types
        if signal.active
    ]
    return "\n".join(lines) or "  (none)"

from __future__ import annotations
from collections.abc import Mapping, Sequence


def normalized_actor_name(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.strip().casefold().split())
    return cleaned or None


def actor_name_keys(actors: Sequence[Mapping[str, object]]) -> set[str]:
    """Extract normalized actor name keys from serialized Event.actors items."""
    keys: set[str] = set()
    for actor in actors:
        key = normalized_actor_name(actor.get("name"))
        if key is not None:
            keys.add(key)
    return keys


def format_actor_label(actor: Mapping[str, object]) -> str:
    """Format one Event.actors dictionary into a compact prompt token."""
    raw_name = actor.get("name")
    name = " ".join(raw_name.split()) if isinstance(raw_name, str) else ""
    if not name:
        return ""
    meta = [
        str(val).strip().upper()
        for key in ("kind", "role", "country_code")
        if isinstance((val := actor.get(key)), str) and str(val).strip()
    ]
    return f"{name} ({'/'.join(meta)})" if meta else name

"""Strict parsing for provider evidence-audit responses."""

import json


def support_is_verified(raw: str) -> bool:
    try:
        verdict = json.loads(
            raw.strip().removeprefix("```json").removesuffix("```").strip()
        )
    except (ValueError, TypeError):
        return False
    # Python considers 1 == True; provider output must contain a JSON boolean.
    return (
        isinstance(verdict, dict)
        and set(verdict) == {"supported"}
        and verdict["supported"] is True
    )

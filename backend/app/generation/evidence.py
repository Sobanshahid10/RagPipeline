"""Strict parsing for provider evidence-audit responses."""

import json


def parse_support_audit(raw: str) -> tuple[bool, list[str]]:
    """Parse a verdict with actionable feedback, failing closed on invalid output."""
    verdict = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
    if not isinstance(verdict, dict) or type(verdict.get("supported")) is not bool:
        raise ValueError("Invalid source-support verdict")
    if set(verdict) == {"supported"}:
        return verdict["supported"], []
    if set(verdict) != {"supported", "unsupported_claims"}:
        raise ValueError("Invalid source-support fields")
    claims = verdict["unsupported_claims"]
    if (not isinstance(claims, list) or len(claims) > 20
            or any(not isinstance(c, str) or not c.strip() or len(c) > 2000 for c in claims)
            or (verdict["supported"] and claims)
            or (not verdict["supported"] and not claims)):
        raise ValueError("Inconsistent source-support verdict")
    return verdict["supported"], claims


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

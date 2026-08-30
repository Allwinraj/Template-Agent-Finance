from __future__ import annotations

"""
Agent ID normalization — use-case agnostic.

Accepts any reasonable agent reference ("A1", "a1", "A1 Capture", "A4 Validate")
and returns the canonical registry ID ("A1".."A6"). Unknown agents are reported
instead of silently crashing a run.
"""

VALID_AGENT_IDS = {"A1", "A2", "A3", "A4", "A5", "A6"}


def normalize_agent_id(value) -> str | None:
    """Map any agent reference to its canonical ID, or None if unknown."""
    if not isinstance(value, str):
        return None
    token = value.strip().split()[0].upper().rstrip(":,")
    return token if token in VALID_AGENT_IDS else None


def normalize_agent_list(values) -> tuple[list, list]:
    """
    Normalize a list of agent references.
    Returns (agent_ids, unknown) — preserving order, dropping duplicates.
    """
    ids: list = []
    unknown: list = []
    for v in values or []:
        aid = normalize_agent_id(v)
        if aid is None:
            unknown.append(v)
        elif aid not in ids:
            ids.append(aid)
    return ids, unknown

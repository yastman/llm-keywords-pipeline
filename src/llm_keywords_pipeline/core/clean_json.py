"""Keyword groups of a ``_clean.json`` file.

The canonical ``keywords`` is a dict of groups (primary/secondary/supporting/commercial);
old files keep a flat list. Readers go through these helpers so both forms read the same
and every keyword entry comes back as stored (``intent`` and other fields kept).
core/models.Category also adapts both forms, but it rebuilds entries as Keyword models and
drops their other fields, so it does not fit readers that write the file back.
"""

from __future__ import annotations

from typing import Any

# Group name of an old flat ``keywords`` list
FLAT_GROUP = ""


def keyword_groups(data: dict[str, Any]) -> dict[str, list[dict]]:
    """Return {group: entries}; a flat list comes back as {FLAT_GROUP: entries}.

    A missing ``keywords`` gives {}; a group whose value is not a list is skipped.
    The entries are the file's own dicts, so editing them edits ``data``.
    """
    raw = data.get("keywords")
    if isinstance(raw, dict):
        return {group: items for group, items in raw.items() if isinstance(items, list)}
    if isinstance(raw, list):
        return {FLAT_GROUP: raw}
    return {}


def keyword_entries(data: dict[str, Any]) -> list[dict]:
    """All keyword entries: ``primary`` first, then the other groups in file order.

    Callers take entry [0] as the main keyword, so ``primary`` leads whatever its JSON position.
    """
    groups = keyword_groups(data)
    rest = [kw for group, items in groups.items() if group != "primary" for kw in items]
    return [*groups.get("primary", []), *rest]


def refresh_stats_totals(data: dict[str, Any]) -> None:
    """Recompute ``stats`` totals from the keyword entries (as restore_csv writes them).

    ``total_volume`` is the sum of keyword volumes; ``after``, when the key exists, is the
    keyword entry count. A file without a ``stats`` dict gets none added.
    """
    stats = data.get("stats")
    if isinstance(stats, dict):
        entries = keyword_entries(data)
        stats["total_volume"] = sum(kw.get("volume", 0) for kw in entries)
        if "after" in stats:
            stats["after"] = len(entries)


def set_keyword_groups(data: dict[str, Any], groups: dict[str, list[dict]]) -> None:
    """Write groups back in the shape keyword_groups read: flat list or dict of groups."""
    if list(groups) == [FLAT_GROUP]:
        data["keywords"] = groups[FLAT_GROUP]
    else:
        data["keywords"] = groups

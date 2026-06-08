"""The private mirror: one IC's own rework and thrash. NEVER ranked.

The wall lives here as a structural fact: every function takes a single
author_id (a str) and returns a single-subject result. There is no function
that accepts a collection of authors or returns a ranked list. test_wall.py
asserts this stays true.
"""
from __future__ import annotations

from ..schema import Dataset

_NO_SESSION = "thrash not computable from seat-weekly spend (needs session-grain spend)"


def _require_single_author(author_id) -> None:
    if not isinstance(author_id, str):
        raise TypeError("mirror metrics take a single author_id (str), not a collection")


def rework_ratio(ds: Dataset, author_id: str) -> float | None:
    """Count-based proxy: outcome events on this author's changes / their merged changes.

    Proxies the post's effort ratio; labeled as a proxy in output. None if the
    author merged nothing.
    """
    _require_single_author(author_id)
    mine = ds.merged_change[ds.merged_change["author_id"] == author_id]
    n_merged = len(mine)
    if n_merged == 0:
        return None
    my_ids = set(mine["change_id"])
    n_events = ds.outcome_event["change_id"].isin(my_ids).sum()
    return float(n_events) / n_merged


def thrash_ratio(ds: Dataset, author_id: str, with_reason: bool = False):
    """Non-merged session spend / total session spend for one IC.

    Conditionally computable: requires SessionSpend. Returns None (and a reason,
    if with_reason) when session-grain spend is unavailable.
    """
    _require_single_author(author_id)
    if ds.session_spend is None:
        return (None, _NO_SESSION) if with_reason else None
    mine = ds.session_spend[ds.session_spend["author_id"] == author_id]
    total = float(mine["dollars"].sum())
    if total == 0:
        return (None, "no session spend for author") if with_reason else None
    non_merged = float(mine.loc[~mine["merged"], "dollars"].sum())
    ratio = non_merged / total
    return (ratio, "") if with_reason else ratio


def mirror(ds: Dataset, author_id: str) -> dict:
    """One IC's private mirror. Single subject by construction."""
    _require_single_author(author_id)
    thrash, reason = thrash_ratio(ds, author_id, with_reason=True)
    return {
        "author_id": author_id,
        "rework_ratio": rework_ratio(ds, author_id),
        "rework_ratio_note": "count-based proxy for post-merge effort",
        "thrash_ratio": thrash,
        "thrash_note": reason,
    }

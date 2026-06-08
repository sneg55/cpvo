"""Review tax: human review-minutes per AI-heavy change vs human-authored (team, money)."""
from __future__ import annotations

from ..schema import Dataset


def review_tax(ds: Dataset) -> dict | None:
    """Mean review_minutes for AI-heavy vs human changes. None if no ReviewRecord."""
    if ds.review_record is None or len(ds.review_record) == 0:
        return None
    rr = ds.review_record
    ai = rr.loc[rr["is_ai_heavy"], "review_minutes"]
    human = rr.loc[~rr["is_ai_heavy"], "review_minutes"]
    ai_mean = float(ai.mean()) if len(ai) else None
    human_mean = float(human.mean()) if len(human) else None
    ratio = (ai_mean / human_mean) if (ai_mean and human_mean) else None
    return {"ai_heavy_mean": ai_mean, "human_mean": human_mean, "ratio": ratio}

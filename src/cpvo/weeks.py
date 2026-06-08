"""ISO-week bucketing and production-settlement helpers."""
from __future__ import annotations

import pandas as pd


def iso_week(value) -> str:
    """Return ISO-week label 'YYYY-Www' for a date-like value."""
    ts = pd.Timestamp(value)
    iso = ts.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def is_settled(merged_at, as_of, n_days: int) -> bool:
    """True if a change has had at least n_days in production as of `as_of`."""
    delta = pd.Timestamp(as_of) - pd.Timestamp(merged_at)
    return delta.days >= n_days

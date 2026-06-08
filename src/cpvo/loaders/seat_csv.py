"""Load seat-week spend from a CSV export. Seat-week is the only cost grain."""
from __future__ import annotations

import pandas as pd

from ..schema import SEAT_SPEND_COLS, validate_columns


def load_seat_spend(path: str) -> pd.DataFrame:
    """Read a seat-spend CSV with columns: seat_id, tool, iso_week, dollars."""
    df = pd.read_csv(path)
    validate_columns(df, SEAT_SPEND_COLS, "SeatSpend")
    df = df[SEAT_SPEND_COLS].copy()
    df["dollars"] = df["dollars"].astype(float)
    return df

"""Canonical tables and the Dataset container every loader emits."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

OUTCOME_KINDS = {"revert", "hotfix_72h", "ticket_reopened"}

SEAT_SPEND_COLS = ["seat_id", "tool", "iso_week", "dollars"]
SEAT_AUTHOR_COLS = ["seat_id", "author_id"]
AUTHOR_COLS = ["author_id", "team", "seniority"]
MERGED_CHANGE_COLS = [
    "change_id", "author_id", "iso_week_merged", "merged_at", "repo", "is_ai_heavy",
]
OUTCOME_EVENT_COLS = ["change_id", "kind", "occurred_at"]
REVIEW_RECORD_COLS = ["change_id", "reviewer_id", "review_minutes", "is_ai_heavy"]
SESSION_SPEND_COLS = ["author_id", "session_id", "iso_week", "dollars", "merged"]


def validate_columns(df: pd.DataFrame, cols: list[str], name: str) -> None:
    """Raise ValueError if df is missing any required column."""
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{name} missing columns: {missing}")


@dataclass
class Dataset:
    """All canonical tables for one analysis window. Optional tables may be None."""
    seat_spend: pd.DataFrame        # SEAT_SPEND_COLS  (seat-week cost — only cost source)
    seat_author: pd.DataFrame       # SEAT_AUTHOR_COLS (seat → author join backbone)
    author: pd.DataFrame            # AUTHOR_COLS      (author → team, seniority)
    merged_change: pd.DataFrame     # MERGED_CHANGE_COLS
    outcome_event: pd.DataFrame     # OUTCOME_EVENT_COLS
    review_record: pd.DataFrame | None = None     # REVIEW_RECORD_COLS
    session_spend: pd.DataFrame | None = None     # SESSION_SPEND_COLS (thrash)

    def validate(self) -> None:
        validate_columns(self.seat_spend, SEAT_SPEND_COLS, "SeatSpend")
        validate_columns(self.seat_author, SEAT_AUTHOR_COLS, "SeatAuthor")
        validate_columns(self.author, AUTHOR_COLS, "Author")
        validate_columns(self.merged_change, MERGED_CHANGE_COLS, "MergedChange")
        validate_columns(self.outcome_event, OUTCOME_EVENT_COLS, "OutcomeEvent")
        if self.review_record is not None:
            validate_columns(self.review_record, REVIEW_RECORD_COLS, "ReviewRecord")
        if self.session_spend is not None:
            validate_columns(self.session_spend, SESSION_SPEND_COLS, "SessionSpend")

"""Tiny hand-built Dataset for engine tests. All numbers chosen to be hand-checkable.

Teams:
  alpha (AI-heavy): authors a1, a2
  beta  (AI-light): author  b1

Merged changes (as_of = 2026-02-01, n_days = 14 -> all settled):
  c1 a1 alpha  merged 2026-01-01  ai   -> verified (no events)
  c2 a1 alpha  merged 2026-01-02  ai   -> FAILED (revert)
  c3 a2 alpha  merged 2026-01-03  ai   -> verified
  c4 b1 beta   merged 2026-01-04  human-> verified
  c5 b1 beta   merged 2026-01-05  human-> FAILED (hotfix_72h)

Outcome weights:
  alpha: verified {c1,c3}=2, failed {c2}=1 -> weight 1
  beta:  verified {c4}=1,    failed {c5}=1 -> weight 0

Seat spend (USD, iso week 2026-W01):
  alpha seats: a1=$100, a2=$50  -> alpha team spend 150
  beta  seats: b1=$20            -> beta team spend  20
  alpha CPVO = 150 / 1 = 150 ; beta CPVO = 20 / 0 -> None (undefined)
"""
import pandas as pd
import pytest
from cpvo.schema import Dataset

AS_OF = "2026-02-01"


@pytest.fixture
def tiny() -> Dataset:
    seat_spend = pd.DataFrame([
        ["s_a1", "cursor", "2026-W01", 100.0],
        ["s_a2", "cursor", "2026-W01", 50.0],
        ["s_b1", "copilot", "2026-W01", 20.0],
    ], columns=["seat_id", "tool", "iso_week", "dollars"])

    seat_author = pd.DataFrame([
        ["s_a1", "a1"], ["s_a2", "a2"], ["s_b1", "b1"],
    ], columns=["seat_id", "author_id"])

    author = pd.DataFrame([
        ["a1", "alpha", "senior"],
        ["a2", "alpha", "mid"],
        ["b1", "beta", "senior"],
    ], columns=["author_id", "team", "seniority"])

    merged_change = pd.DataFrame([
        ["c1", "a1", "2026-W01", "2026-01-01", "repo", True],
        ["c2", "a1", "2026-W01", "2026-01-02", "repo", True],
        ["c3", "a2", "2026-W01", "2026-01-03", "repo", True],
        ["c4", "b1", "2026-W01", "2026-01-04", "repo", False],
        ["c5", "b1", "2026-W01", "2026-01-05", "repo", False],
    ], columns=["change_id", "author_id", "iso_week_merged", "merged_at", "repo", "is_ai_heavy"])

    outcome_event = pd.DataFrame([
        ["c2", "revert", "2026-01-03"],
        ["c5", "hotfix_72h", "2026-01-06"],
    ], columns=["change_id", "kind", "occurred_at"])

    review_record = pd.DataFrame([
        ["c1", "rev", 60, True],
        ["c3", "rev", 40, True],   # ai-heavy mean = 50
        ["c4", "rev", 20, False],  # human mean = 20
    ], columns=["change_id", "reviewer_id", "review_minutes", "is_ai_heavy"])

    session_spend = pd.DataFrame([
        # a1: merged $120, non-merged $40 -> thrash 40/160 = 0.25
        ["a1", "sess1", "2026-W01", 120.0, True],
        ["a1", "sess2", "2026-W01", 40.0, False],
        # a2: all merged -> thrash 0.0
        ["a2", "sess3", "2026-W01", 50.0, True],
    ], columns=["author_id", "session_id", "iso_week", "dollars", "merged"])

    return Dataset(
        seat_spend=seat_spend, seat_author=seat_author, author=author,
        merged_change=merged_change, outcome_event=outcome_event,
        review_record=review_record, session_spend=session_spend,
    )

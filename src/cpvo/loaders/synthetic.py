"""Seeded narrative fixture generator. ALL DATA IS ILLUSTRATIVE / SYNTHETIC.

Tells three team stories and several contributor stories so each metric lights
up. Round numbers on purpose; nothing here is a real-world measurement.
"""
from __future__ import annotations

import random

import pandas as pd

from ..schema import Dataset

WEEKS = [f"2026-W{w:02d}" for w in range(1, 13)]      # 12 ISO weeks
AS_OF = "2026-04-15"                                    # all 12 weeks settled by here
SYNTHETIC = True

# (author_id, team, seniority, weekly_seat_dollars, tool)
_AUTHORS = [
    # Atlas (AI-heavy): healthy median, long expensive tail (a_waste1/a_waste2)
    ("a_lead", "Atlas", "senior", 90, "cursor"),
    ("a_solid", "Atlas", "mid", 80, "cursor"),
    ("a_waste1", "Atlas", "mid", 200, "cursor"),         # high burn, low outcome, stuck
    ("a_waste2", "Atlas", "junior", 180, "claude_code"),  # high burn, fast slop
    # Borealis (AI-heavy): whole distribution drifts up
    ("b_one", "Borealis", "senior", 70, "cursor"),
    ("b_two", "Borealis", "mid", 70, "claude_code"),
    ("b_three", "Borealis", "junior", 60, "cursor"),
    # Cardinal (AI-light): low spend, comparable outcomes, better stability
    ("c_one", "Cardinal", "senior", 20, "copilot"),
    ("c_two", "Cardinal", "mid", 15, "copilot"),
    ("c_three", "Cardinal", "junior", 10, "copilot"),
]


def _merged_at(week_idx: int, rng: random.Random) -> str:
    base = pd.Timestamp("2026-01-05") + pd.Timedelta(weeks=week_idx)
    return (base + pd.Timedelta(days=rng.randint(0, 4))).strftime("%Y-%m-%d")


def generate(seed: int = 42, weeks: int = 12) -> Dataset:
    rng = random.Random(seed)
    weeks_list = WEEKS[:weeks]

    seat_rows, seat_author_rows, author_rows = [], [], []
    merged_rows, event_rows, review_rows, session_rows = [], [], [], []
    cid = 0

    for author_id, team, seniority, base_dollars, tool in _AUTHORS:
        author_rows.append([author_id, team, seniority])
        seat_id = f"seat_{author_id}"
        seat_author_rows.append([seat_id, author_id])
        is_ai = team in ("Atlas", "Borealis")

        for wi, wk in enumerate(weeks_list):
            # Borealis spend drifts up over the window
            drift = 1.0 + (0.06 * wi if team == "Borealis" else 0.0)
            dollars = round(base_dollars * drift)
            seat_rows.append([seat_id, tool, wk, float(dollars)])

            # outcomes per author per week
            if author_id == "a_waste1":      # stuck: few merges, heavy non-merged sessions
                n_changes = rng.choice([0, 1, 1])
            elif author_id == "a_waste2":    # fast slop: ships, then fails
                n_changes = rng.choice([2, 3])
            else:
                n_changes = rng.choice([2, 2, 3])

            for _ in range(n_changes):
                cid += 1
                change_id = f"ch{cid}"
                merged_rows.append([change_id, author_id, wk, _merged_at(wi, rng), "monorepo", is_ai])
                # failure injection
                if author_id == "a_waste2":
                    fail = rng.random() < 0.45      # high rework
                elif team == "Cardinal":
                    fail = rng.random() < 0.08      # most stable
                elif team == "Borealis":
                    fail = rng.random() < 0.18
                else:                                # Atlas baseline
                    fail = rng.random() < 0.15
                if fail:
                    kind = rng.choice(["revert", "hotfix_72h", "ticket_reopened"])
                    event_rows.append([change_id, kind, _merged_at(wi, rng)])
                # review tax: AI-heavy changes cost more reviewer minutes
                minutes = rng.randint(45, 90) if is_ai else rng.randint(15, 35)
                review_rows.append([change_id, "reviewer", minutes, is_ai])

            # session spend (for thrash). a_waste1 burns lots that never merges.
            if author_id == "a_waste1":
                session_rows.append([author_id, f"{author_id}-{wk}-m", wk, float(round(dollars * 0.4)), True])
                session_rows.append([author_id, f"{author_id}-{wk}-x", wk, float(round(dollars * 0.6)), False])
            else:
                merged_frac = 0.85 if team == "Cardinal" else 0.75
                session_rows.append([author_id, f"{author_id}-{wk}-m", wk, float(round(dollars * merged_frac)), True])
                session_rows.append([author_id, f"{author_id}-{wk}-x", wk, float(round(dollars * (1 - merged_frac))), False])

    ds = Dataset(
        seat_spend=pd.DataFrame(seat_rows, columns=["seat_id", "tool", "iso_week", "dollars"]),
        seat_author=pd.DataFrame(seat_author_rows, columns=["seat_id", "author_id"]),
        author=pd.DataFrame(author_rows, columns=["author_id", "team", "seniority"]),
        merged_change=pd.DataFrame(merged_rows, columns=["change_id", "author_id", "iso_week_merged", "merged_at", "repo", "is_ai_heavy"]),
        outcome_event=pd.DataFrame(event_rows, columns=["change_id", "kind", "occurred_at"]),
        review_record=pd.DataFrame(review_rows, columns=["change_id", "reviewer_id", "review_minutes", "is_ai_heavy"]),
        session_spend=pd.DataFrame(session_rows, columns=["author_id", "session_id", "iso_week", "dollars", "merged"]),
    )
    return ds


if __name__ == "__main__":  # pragma: no cover
    import os
    ds = generate(seed=7)
    os.makedirs("fixtures/synthetic", exist_ok=True)
    for name in ["seat_spend", "seat_author", "author", "merged_change",
                 "outcome_event", "review_record", "session_spend"]:
        getattr(ds, name).to_csv(f"fixtures/synthetic/{name}.csv", index=False)
    print("wrote fixtures/synthetic/*.csv")

# CPVO Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `cpvo`, a public Python reference harness that computes cost per verified outcome from AI-tool spend joined to git outcomes, with the two-level wall (private IC mirror vs. team budget altitude) enforced in code.

**Architecture:** Layered pipeline — `loaders/` normalize any source into a canonical `Dataset`, pure `engine/` functions compute metrics over it, `render/` emits CLI tables/JSON and a static HTML/SVG dashboard. The wall is enforced by the *absence* of any leaderboard code path; `test_wall.py` regression-protects it.

**Tech Stack:** Python 3.13, pandas, requests (GitHub adapter), PyYAML (seat→author mapping), pytest. No chart library — the dashboard is hand-built inline SVG.

**Spec:** `../../../../sawinyh.com/beneficial-binary/docs/superpowers/specs/2026-06-08-cpvo-harness-design.md` (also mirrored conceptually here).

**Schema refinement vs. spec:** The spec lists five canonical tables. This plan adds two to make CPVO-per-team and thrash computable: an `Author(author_id, team, seniority)` dimension (team attribution + cohort seniority control) and an optional `SessionSpend(author_id, session_id, iso_week, dollars, merged)` table (session-grain spend that thrash requires). Seat-week `SeatSpend` remains the *only* cost source for CPVO; per-PR cost stays unrepresentable.

---

## File structure

```
cpvo/
├── pyproject.toml                  # package metadata, deps, console_scripts: cpvo
├── README.md                       # pitch, quickstart, links to the post
├── LICENSE                         # MIT
├── .gitignore
├── src/cpvo/
│   ├── __init__.py
│   ├── schema.py                   # canonical tables + Dataset container + validation
│   ├── weeks.py                    # ISO-week helpers + settled/as_of logic
│   ├── loaders/
│   │   ├── __init__.py
│   │   ├── synthetic.py            # seeded narrative fixture generator
│   │   ├── seat_csv.py             # seat-spend CSV → SeatSpend
│   │   ├── mapping.py              # seat→author YAML → SeatAuthor
│   │   ├── github.py               # GitHub PR/commit/revert → tables (pure transform + thin fetch)
│   │   └── gitlab.py               # documented stub
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── outcomes.py             # verified_changes, outcome_weight[_by]
│   │   ├── cpvo.py                 # team spend join, weekly_team_cpvo, cpvo_summary
│   │   ├── mirror.py               # rework_ratio, thrash_ratio, mirror (single IC only)
│   │   ├── review_tax.py           # review_tax
│   │   └── cohort.py               # cohort_compare with caveats + min-outcome gate
│   ├── render/
│   │   ├── __init__.py
│   │   ├── tokens.py               # design tokens ported from the blog + WATERMARK
│   │   ├── cli.py                  # text tables + JSON
│   │   └── dashboard.py            # static HTML/SVG report
│   └── cli.py                      # argparse entry, 5 subcommands
├── fixtures/synthetic/             # synthetic Dataset dumped as CSV (generated, input shape)
└── tests/
    ├── conftest.py                 # tiny hand-built Dataset fixtures
    ├── test_schema.py
    ├── test_weeks.py
    ├── test_outcomes.py
    ├── test_cpvo.py
    ├── test_mirror.py
    ├── test_review_tax.py
    ├── test_cohort.py
    ├── test_synthetic.py
    ├── test_seat_csv.py
    ├── test_mapping.py
    ├── test_github.py
    └── test_wall.py                # conscience test
```

---

## Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `src/cpvo/__init__.py`, `src/cpvo/loaders/__init__.py`, `src/cpvo/engine/__init__.py`, `src/cpvo/render/__init__.py`, `tests/__init__.py` (omit), `LICENSE`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "cpvo"
version = "0.1.0"
description = "Cost per verified outcome: a reference harness for measuring AI dev-tool spend against outcomes that survive production."
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
dependencies = ["pandas>=2.0", "requests>=2.31", "PyYAML>=6.0"]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
cpvo = "cpvo.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 2: Write `.gitignore`**

```gitignore
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
build/
dist/
.venv/
venv/
fixtures/synthetic/*.csv
dashboard.html
```

- [ ] **Step 3: Write `LICENSE`** (MIT, copyright holder "sneg55", year 2026). Use the standard MIT text.

- [ ] **Step 4: Create empty package init files**

`src/cpvo/__init__.py`:
```python
"""cpvo — cost per verified outcome reference harness."""

__version__ = "0.1.0"
```
`src/cpvo/loaders/__init__.py`, `src/cpvo/engine/__init__.py`, `src/cpvo/render/__init__.py`: each a single line `"""<subpackage>."""`.

- [ ] **Step 5: Create venv and install dev**

Run:
```bash
cd /Users/sneg55/Documents/GitHub/cpvo
python3 -m venv .venv
.venv/bin/pip install -q -e ".[dev]"
.venv/bin/pytest -q
```
Expected: pytest runs, "no tests ran" (exit 5) — acceptable at this point.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: scaffold cpvo package (pyproject, license, package skeleton)"
```

---

## Task 2: ISO-week helpers (`weeks.py`)

**Files:**
- Create: `src/cpvo/weeks.py`
- Test: `tests/test_weeks.py`

- [ ] **Step 1: Write the failing test**

`tests/test_weeks.py`:
```python
import pandas as pd
from cpvo.weeks import iso_week, is_settled

def test_iso_week_formats_year_and_week():
    assert iso_week("2026-01-05") == "2026-W02"
    assert iso_week(pd.Timestamp("2026-01-01")) == "2026-W01"

def test_is_settled_true_when_older_than_n_days():
    assert is_settled("2026-01-01", as_of="2026-01-20", n_days=14) is True

def test_is_settled_false_when_within_window():
    assert is_settled("2026-01-15", as_of="2026-01-20", n_days=14) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_weeks.py -q`
Expected: FAIL (ModuleNotFoundError: cpvo.weeks)

- [ ] **Step 3: Implement**

`src/cpvo/weeks.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_weeks.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cpvo/weeks.py tests/test_weeks.py
git commit -m "feat: ISO-week and settlement helpers"
```

---

## Task 3: Canonical schema (`schema.py`)

**Files:**
- Create: `src/cpvo/schema.py`
- Test: `tests/test_schema.py`

- [ ] **Step 1: Write the failing test**

`tests/test_schema.py`:
```python
import pandas as pd
import pytest
from cpvo.schema import Dataset, validate_columns, OUTCOME_KINDS, SEAT_SPEND_COLS

def test_validate_columns_passes_with_exact_columns():
    df = pd.DataFrame({c: [] for c in SEAT_SPEND_COLS})
    validate_columns(df, SEAT_SPEND_COLS, "SeatSpend")  # no raise

def test_validate_columns_raises_on_missing():
    df = pd.DataFrame({"seat_id": []})
    with pytest.raises(ValueError, match="SeatSpend.*missing"):
        validate_columns(df, SEAT_SPEND_COLS, "SeatSpend")

def test_outcome_kinds_are_the_closed_set():
    assert OUTCOME_KINDS == {"revert", "hotfix_72h", "ticket_reopened"}

def test_dataset_optional_tables_default_none():
    ds = Dataset(
        seat_spend=pd.DataFrame(),
        seat_author=pd.DataFrame(),
        author=pd.DataFrame(),
        merged_change=pd.DataFrame(),
        outcome_event=pd.DataFrame(),
    )
    assert ds.review_record is None
    assert ds.session_spend is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_schema.py -q`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement**

`src/cpvo/schema.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_schema.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cpvo/schema.py tests/test_schema.py
git commit -m "feat: canonical schema and Dataset container"
```

---

## Task 4: Shared test fixtures (`conftest.py`)

**Files:**
- Create: `tests/conftest.py`

This builds a tiny hand-computable Dataset reused across engine tests. Known values are documented inline so later tasks can assert against them.

- [ ] **Step 1: Write `tests/conftest.py`**

```python
"""Tiny hand-built Dataset for engine tests. All numbers chosen to be hand-checkable.

Teams:
  alpha (AI-heavy): authors a1, a2
  beta  (AI-light): author  b1

Merged changes (as_of = 2026-02-01, n_days = 14 → all settled):
  c1 a1 alpha  merged 2026-01-01  ai   -> verified (no events)
  c2 a1 alpha  merged 2026-01-02  ai   -> FAILED (revert)
  c3 a2 alpha  merged 2026-01-03  ai   -> verified
  c4 b1 beta   merged 2026-01-04  human-> verified
  c5 b1 beta   merged 2026-01-05  human-> FAILED (hotfix_72h)

Outcome weights:
  alpha: verified {c1,c3}=2, failed {c2}=1 -> weight 1
  beta:  verified {c4}=1,    failed {c5}=1 -> weight 0

Seat spend (USD, iso weeks 2026-W01):
  alpha seats: a1=$100, a2=$50  -> alpha team spend 150
  beta  seats: b1=$20            -> beta team spend  20
  alpha CPVO = 150 / 1 = 150 ; beta CPVO = 20 / 0 -> inf-guard
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
```

- [ ] **Step 2: Commit**

```bash
git add tests/conftest.py
git commit -m "test: shared hand-checkable Dataset fixture"
```

---

## Task 5: Outcomes engine (`engine/outcomes.py`)

**Files:**
- Create: `src/cpvo/engine/outcomes.py`
- Test: `tests/test_outcomes.py`

- [ ] **Step 1: Write the failing test**

`tests/test_outcomes.py`:
```python
from cpvo.engine.outcomes import verified_changes, outcome_weight, outcome_weight_by
from tests.conftest import AS_OF

def test_verified_flags(tiny):
    vc = verified_changes(tiny, n_days=14, as_of=AS_OF).set_index("change_id")
    assert bool(vc.loc["c1", "verified"]) is True
    assert bool(vc.loc["c2", "failed"]) is True
    assert bool(vc.loc["c2", "verified"]) is False

def test_total_outcome_weight(tiny):
    # verified {c1,c3,c4}=3, failed {c2,c5}=2 -> 1
    assert outcome_weight(tiny, n_days=14, as_of=AS_OF) == 1

def test_outcome_weight_by_team(tiny):
    w = outcome_weight_by(tiny, by="team", n_days=14, as_of=AS_OF).set_index("team")["outcome_weight"]
    assert w.loc["alpha"] == 1   # verified 2, failed 1
    assert w.loc["beta"] == 0    # verified 1, failed 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_outcomes.py -q`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement**

`src/cpvo/engine/outcomes.py`:
```python
"""Verified-outcome and outcome-weight metrics (team altitude, money)."""
from __future__ import annotations

import pandas as pd

from ..schema import Dataset
from ..weeks import is_settled


def verified_changes(ds: Dataset, n_days: int = 14, as_of: str | None = None) -> pd.DataFrame:
    """Annotate merged_change with settled/failed/verified booleans.

    A change FAILED if any OutcomeEvent (revert / hotfix_72h / ticket_reopened)
    targets it. A change is VERIFIED if it is settled (>= n_days old) and not failed.
    Unsettled changes are neither verified nor failed (pending) and do not count.
    """
    mc = ds.merged_change.copy()
    if as_of is None:
        as_of = pd.to_datetime(mc["merged_at"]).max()
    failed_ids = set(ds.outcome_event["change_id"])
    mc["failed"] = mc["change_id"].isin(failed_ids)
    mc["settled"] = mc["merged_at"].apply(lambda d: is_settled(d, as_of, n_days))
    mc["verified"] = mc["settled"] & ~mc["failed"]
    return mc


def outcome_weight(ds: Dataset, n_days: int = 14, as_of: str | None = None) -> int:
    """Net count: settled-verified minus settled-failed, whole dataset."""
    vc = verified_changes(ds, n_days, as_of)
    return int(vc["verified"].sum() - (vc["settled"] & vc["failed"]).sum())


def outcome_weight_by(ds: Dataset, by: str = "team", n_days: int = 14,
                      as_of: str | None = None) -> pd.DataFrame:
    """Outcome weight grouped by an Author dimension column (default team)."""
    vc = verified_changes(ds, n_days, as_of)
    vc = vc.merge(ds.author[["author_id", by]], on="author_id", how="left")
    vc["net"] = vc["verified"].astype(int) - (vc["settled"] & vc["failed"]).astype(int)
    out = vc.groupby(by, as_index=False)["net"].sum()
    return out.rename(columns={"net": "outcome_weight"})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_outcomes.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cpvo/engine/outcomes.py tests/test_outcomes.py
git commit -m "feat: outcomes engine (verified changes, outcome weight)"
```

---

## Task 6: CPVO engine (`engine/cpvo.py`)

**Files:**
- Create: `src/cpvo/engine/cpvo.py`
- Test: `tests/test_cpvo.py`

- [ ] **Step 1: Write the failing test**

`tests/test_cpvo.py`:
```python
import math
from cpvo.engine.cpvo import team_spend_by_week, cpvo_summary
from tests.conftest import AS_OF

def test_team_spend_joins_seats_to_team(tiny):
    s = team_spend_by_week(tiny).set_index("team")["dollars"]
    assert s.loc["alpha"] == 150.0   # a1 100 + a2 50
    assert s.loc["beta"] == 20.0

def test_cpvo_summary_overall(tiny):
    summ = cpvo_summary(tiny, n_days=14, as_of=AS_OF).set_index("team")
    assert summ.loc["alpha", "spend"] == 150.0
    assert summ.loc["alpha", "outcome_weight"] == 1
    assert summ.loc["alpha", "cpvo"] == 150.0
    # beta weight 0 -> cpvo is None (undefined), never inf or a fake number
    assert summ.loc["beta", "cpvo"] is None or math.isnan(summ.loc["beta", "cpvo"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_cpvo.py -q`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement**

`src/cpvo/engine/cpvo.py`:
```python
"""Team CPVO: seat-week spend joined to outcome weight (team altitude, money)."""
from __future__ import annotations

import pandas as pd

from ..schema import Dataset
from .outcomes import outcome_weight_by, verified_changes


def _spend_with_team(ds: Dataset) -> pd.DataFrame:
    """SeatSpend joined seat→author→team. The seat-to-author backbone."""
    s = ds.seat_spend.merge(ds.seat_author, on="seat_id", how="left")
    s = s.merge(ds.author[["author_id", "team"]], on="author_id", how="left")
    return s


def team_spend_by_week(ds: Dataset) -> pd.DataFrame:
    """Total seat-week dollars per team per ISO week."""
    s = _spend_with_team(ds)
    out = s.groupby(["team", "iso_week"], as_index=False)["dollars"].sum()
    return out


def weekly_team_cpvo(ds: Dataset, n_days: int = 14, as_of: str | None = None) -> pd.DataFrame:
    """Per team per week: spend, outcome_weight, weekly cpvo (None when weight <= 0)."""
    spend = team_spend_by_week(ds).rename(columns={"dollars": "spend"})
    vc = verified_changes(ds, n_days, as_of)
    vc = vc.merge(ds.author[["author_id", "team"]], on="author_id", how="left")
    vc["net"] = vc["verified"].astype(int) - (vc["settled"] & vc["failed"]).astype(int)
    weight = vc.groupby(["team", "iso_week_merged"], as_index=False)["net"].sum()
    weight = weight.rename(columns={"iso_week_merged": "iso_week", "net": "outcome_weight"})
    out = spend.merge(weight, on=["team", "iso_week"], how="left")
    out["outcome_weight"] = out["outcome_weight"].fillna(0).astype(int)
    out["cpvo"] = [
        (sp / w) if w > 0 else None
        for sp, w in zip(out["spend"], out["outcome_weight"])
    ]
    return out


def cpvo_summary(ds: Dataset, n_days: int = 14, as_of: str | None = None) -> pd.DataFrame:
    """Overall CPVO per team plus distribution shape across weeks.

    Columns: team, spend, outcome_weight, cpvo (overall, None if weight<=0),
             median_weekly_cpvo, p90_weekly_cpvo (the expensive tail).
    """
    spend = team_spend_by_week(ds).groupby("team", as_index=False)["dollars"].sum()
    spend = spend.rename(columns={"dollars": "spend"})
    weight = outcome_weight_by(ds, by="team", n_days=n_days, as_of=as_of)
    weekly = weekly_team_cpvo(ds, n_days, as_of)

    rows = []
    for team in spend["team"]:
        sp = float(spend.loc[spend.team == team, "spend"].iloc[0])
        w = int(weight.loc[weight.team == team, "outcome_weight"].iloc[0]) if (weight.team == team).any() else 0
        wk = weekly.loc[(weekly.team == team) & weekly["cpvo"].notna(), "cpvo"]
        rows.append({
            "team": team,
            "spend": sp,
            "outcome_weight": w,
            "cpvo": (sp / w) if w > 0 else None,
            "median_weekly_cpvo": float(wk.median()) if len(wk) else None,
            "p90_weekly_cpvo": float(wk.quantile(0.9)) if len(wk) else None,
        })
    return pd.DataFrame(rows)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_cpvo.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cpvo/engine/cpvo.py tests/test_cpvo.py
git commit -m "feat: team CPVO engine with weekly distribution"
```

---

## Task 7: Mirror engine (`engine/mirror.py`) — the wall

**Files:**
- Create: `src/cpvo/engine/mirror.py`
- Test: `tests/test_mirror.py`

This module is single-IC only by construction. Every public function takes one `author_id: str` and returns a single-subject result. There is deliberately no batch/ranking function.

- [ ] **Step 1: Write the failing test**

`tests/test_mirror.py`:
```python
import pytest
from cpvo.engine.mirror import rework_ratio, thrash_ratio, mirror

def test_rework_ratio(tiny):
    # a1 authored c1,c2; events on a1's changes: c2 revert -> 1 event / 2 merged = 0.5
    assert rework_ratio(tiny, "a1") == 0.5

def test_thrash_ratio_uses_session_spend(tiny):
    # a1: non-merged 40 / total 160 = 0.25
    assert thrash_ratio(tiny, "a1") == 0.25

def test_thrash_none_without_session_spend(tiny):
    tiny.session_spend = None
    val, reason = thrash_ratio(tiny, "a1", with_reason=True)
    assert val is None
    assert "not computable" in reason

def test_mirror_is_single_subject(tiny):
    m = mirror(tiny, "a1")
    assert m["author_id"] == "a1"
    assert m["rework_ratio"] == 0.5
    assert m["thrash_ratio"] == 0.25

def test_mirror_rejects_non_string_author(tiny):
    with pytest.raises(TypeError, match="single author_id"):
        mirror(tiny, ["a1", "a2"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_mirror.py -q`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement**

`src/cpvo/engine/mirror.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_mirror.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cpvo/engine/mirror.py tests/test_mirror.py
git commit -m "feat: private mirror engine (single-IC rework + thrash)"
```

---

## Task 8: Review tax engine (`engine/review_tax.py`)

**Files:**
- Create: `src/cpvo/engine/review_tax.py`
- Test: `tests/test_review_tax.py`

- [ ] **Step 1: Write the failing test**

`tests/test_review_tax.py`:
```python
from cpvo.engine.review_tax import review_tax

def test_review_tax_ratio(tiny):
    r = review_tax(tiny)
    assert r["ai_heavy_mean"] == 50.0   # (60+40)/2
    assert r["human_mean"] == 20.0
    assert r["ratio"] == 2.5

def test_review_tax_none_without_records(tiny):
    tiny.review_record = None
    assert review_tax(tiny) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_review_tax.py -q`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement**

`src/cpvo/engine/review_tax.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_review_tax.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cpvo/engine/review_tax.py tests/test_review_tax.py
git commit -m "feat: review tax engine"
```

---

## Task 9: Cohort engine (`engine/cohort.py`)

**Files:**
- Create: `src/cpvo/engine/cohort.py`
- Test: `tests/test_cohort.py`

- [ ] **Step 1: Write the failing test**

`tests/test_cohort.py`:
```python
from cpvo.engine.cohort import cohort_compare
from tests.conftest import AS_OF

def test_cohort_gates_on_min_outcomes(tiny):
    # alpha weight 1, beta weight 0 -> both below min_outcomes=20 -> no verdict
    res = cohort_compare(tiny, "alpha", "beta", n_days=14, as_of=AS_OF, min_outcomes=20)
    assert res["verdict"] is None
    assert "too few outcomes" in res["verdict_reason"]

def test_cohort_reports_two_axes_and_caveats(tiny):
    res = cohort_compare(tiny, "alpha", "beta", n_days=14, as_of=AS_OF, min_outcomes=1)
    assert set(res["ai_heavy"]) >= {"team", "outcome_weight", "fail_rate", "spend", "cpvo"}
    assert res["ai_heavy"]["team"] == "alpha"
    assert res["ai_light"]["team"] == "beta"
    assert any("selection bias" in c.lower() for c in res["caveats"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_cohort.py -q`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement**

`src/cpvo/engine/cohort.py`:
```python
"""Cohort comparison: AI-heavy vs AI-light on outcome AND stability (budget altitude)."""
from __future__ import annotations

from ..schema import Dataset
from .cpvo import cpvo_summary
from .outcomes import verified_changes

CAVEATS = [
    "Selection bias: best (or most desperate) engineers may have adopted AI first.",
    "Small denominators: a handful of outcomes is noise, not signal.",
    "Skill-ceiling (METR): experts may gain where novices lose; the average hides both.",
    "Surface area: greenfield vs legacy confounds any speed comparison.",
]


def _team_stats(ds: Dataset, team: str, n_days: int, as_of: str | None) -> dict:
    vc = verified_changes(ds, n_days, as_of).merge(
        ds.author[["author_id", "team"]], on="author_id", how="left")
    tvc = vc[vc["team"] == team]
    settled = tvc["settled"].sum()
    failed = (tvc["settled"] & tvc["failed"]).sum()
    weight = int(tvc["verified"].sum() - failed)
    summ = cpvo_summary(ds, n_days, as_of).set_index("team")
    spend = float(summ.loc[team, "spend"]) if team in summ.index else 0.0
    cpvo = summ.loc[team, "cpvo"] if team in summ.index else None
    return {
        "team": team,
        "outcome_weight": weight,
        "fail_rate": (float(failed) / settled) if settled else None,
        "spend": spend,
        "cpvo": cpvo,
    }


def cohort_compare(ds: Dataset, ai_heavy: str, ai_light: str, n_days: int = 14,
                   as_of: str | None = None, min_outcomes: int = 20) -> dict:
    """Two-axis comparison with confounder caveats and a min-denominator gate."""
    heavy = _team_stats(ds, ai_heavy, n_days, as_of)
    light = _team_stats(ds, ai_light, n_days, as_of)
    verdict = "ready to read (still observe caveats)"
    verdict_reason = ""
    if heavy["outcome_weight"] < min_outcomes or light["outcome_weight"] < min_outcomes:
        verdict = None
        verdict_reason = (
            f"too few outcomes (min {min_outcomes}); "
            f"{ai_heavy}={heavy['outcome_weight']}, {ai_light}={light['outcome_weight']}"
        )
    return {
        "ai_heavy": heavy,
        "ai_light": light,
        "caveats": list(CAVEATS),
        "verdict": verdict,
        "verdict_reason": verdict_reason,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_cohort.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cpvo/engine/cohort.py tests/test_cohort.py
git commit -m "feat: cohort comparison with caveats and min-outcome gate"
```

---

## Task 10: Synthetic loader (`loaders/synthetic.py`)

**Files:**
- Create: `src/cpvo/loaders/synthetic.py`
- Test: `tests/test_synthetic.py`

Generates the narrative fixtures (Atlas tail / Borealis drift / Cardinal cohort + the contributor stories), deterministically from a seed. Uses `random.Random(seed)` only — no wall-clock, fully reproducible.

- [ ] **Step 1: Write the failing test**

`tests/test_synthetic.py`:
```python
from cpvo.loaders.synthetic import generate, AS_OF
from cpvo.engine.cpvo import cpvo_summary
from cpvo.engine.mirror import thrash_ratio

def test_generate_is_deterministic():
    a = generate(seed=7)
    b = generate(seed=7)
    assert a.merged_change.equals(b.merged_change)
    assert a.seat_spend.equals(b.seat_spend)

def test_dataset_validates():
    generate(seed=7).validate()  # no raise

def test_three_teams_present():
    ds = generate(seed=7)
    assert set(ds.author["team"]) == {"Atlas", "Borealis", "Cardinal"}

def test_atlas_has_a_high_burn_low_outcome_contributor():
    # at least one Atlas author has thrash defined and elevated
    ds = generate(seed=7)
    atlas = ds.author.loc[ds.author.team == "Atlas", "author_id"]
    thrashes = [thrash_ratio(ds, a) for a in atlas]
    thrashes = [t for t in thrashes if t is not None]
    assert max(thrashes) >= 0.3

def test_cardinal_is_ai_light_lower_cpvo_pressure():
    ds = generate(seed=7)
    summ = cpvo_summary(ds, n_days=14, as_of=AS_OF).set_index("team")
    # Cardinal spends less than Atlas overall
    assert summ.loc["Cardinal", "spend"] < summ.loc["Atlas", "spend"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_synthetic.py -q`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement**

`src/cpvo/loaders/synthetic.py`:
```python
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
    ("a_waste1", "Atlas", "mid", 200, "cursor"),   # high burn, low outcome, stuck
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
```

> Note: if `test_atlas_has_a_high_burn_low_outcome_contributor` or `test_cardinal_*` fails because of seed-dependent randomness, adjust the failure probabilities or the `a_waste1` session split — they are tuned, not sacred. The deterministic and validation tests must pass as written.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_synthetic.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cpvo/loaders/synthetic.py tests/test_synthetic.py
git commit -m "feat: synthetic narrative fixture generator"
```

---

## Task 11: Seat-CSV and mapping loaders

**Files:**
- Create: `src/cpvo/loaders/seat_csv.py`, `src/cpvo/loaders/mapping.py`
- Test: `tests/test_seat_csv.py`, `tests/test_mapping.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_seat_csv.py`:
```python
from cpvo.loaders.seat_csv import load_seat_spend

def test_load_seat_spend(tmp_path):
    p = tmp_path / "spend.csv"
    p.write_text("seat_id,tool,iso_week,dollars\ns1,cursor,2026-W01,100\n")
    df = load_seat_spend(str(p))
    assert list(df.columns) == ["seat_id", "tool", "iso_week", "dollars"]
    assert df.loc[0, "dollars"] == 100.0
```

`tests/test_mapping.py`:
```python
from cpvo.loaders.mapping import load_mapping

def test_load_mapping(tmp_path):
    p = tmp_path / "map.yaml"
    p.write_text("s1: a1\ns2: a1\ns3: b1\n")
    df = load_mapping(str(p))
    assert set(df.columns) == {"seat_id", "author_id"}
    assert len(df) == 3
    assert df.loc[df.seat_id == "s2", "author_id"].iloc[0] == "a1"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_seat_csv.py tests/test_mapping.py -q`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement**

`src/cpvo/loaders/seat_csv.py`:
```python
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
```

`src/cpvo/loaders/mapping.py`:
```python
"""Load the seat→author mapping (the join backbone) from YAML {seat_id: author_id}."""
from __future__ import annotations

import pandas as pd
import yaml


def load_mapping(path: str) -> pd.DataFrame:
    """Read a YAML mapping of seat_id -> author_id into a SeatAuthor frame."""
    with open(path) as fh:
        raw = yaml.safe_load(fh) or {}
    rows = [[seat, author] for seat, author in raw.items()]
    return pd.DataFrame(rows, columns=["seat_id", "author_id"])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_seat_csv.py tests/test_mapping.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cpvo/loaders/seat_csv.py src/cpvo/loaders/mapping.py tests/test_seat_csv.py tests/test_mapping.py
git commit -m "feat: seat-CSV and seat->author mapping loaders"
```

---

## Task 12: GitHub loader (`loaders/github.py`) + GitLab stub

**Files:**
- Create: `src/cpvo/loaders/github.py`, `src/cpvo/loaders/gitlab.py`
- Test: `tests/test_github.py`

The GitHub adapter splits into a **pure transform** (raw PR dicts → tables, fully unit-tested) and a thin **fetch** wrapper (requests) that isn't unit-tested. A revert is detected by a PR/commit title starting with `Revert "` or carrying a `hotfix` label.

- [ ] **Step 1: Write the failing test**

`tests/test_github.py`:
```python
from cpvo.loaders.github import build_changes_from_prs

def test_build_changes_from_prs():
    prs = [
        {"number": 1, "user": "a1", "merged_at": "2026-01-01T10:00:00Z", "title": "feat: x", "labels": []},
        {"number": 2, "user": "a1", "merged_at": "2026-01-02T10:00:00Z", "title": 'Revert "feat: x"', "labels": []},
        {"number": 3, "user": "b1", "merged_at": "2026-01-03T10:00:00Z", "title": "fix: y", "labels": ["hotfix"]},
    ]
    changes, events = build_changes_from_prs(prs, repo="org/repo", ai_authors={"a1"})

    crow = changes.set_index("change_id")
    assert crow.loc["org/repo#1", "iso_week_merged"] == "2026-W01"
    assert bool(crow.loc["org/repo#1", "is_ai_heavy"]) is True
    assert bool(crow.loc["org/repo#3", "is_ai_heavy"]) is False

    kinds = dict(zip(events["change_id"], events["kind"]))
    assert kinds["org/repo#2"] == "revert"
    assert kinds["org/repo#3"] == "hotfix_72h"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_github.py -q`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement**

`src/cpvo/loaders/github.py`:
```python
"""GitHub adapter: merged PRs → MergedChange + OutcomeEvent.

Pure transform (build_changes_from_prs) is unit-tested. fetch_merged_prs is a
thin requests wrapper documented but not unit-tested. This adapter provides PR
and revert/hotfix signals only; it does NOT provide per-PR cost — cost comes
solely from seat-week spend.
"""
from __future__ import annotations

import pandas as pd

from ..weeks import iso_week


def build_changes_from_prs(prs: list[dict], repo: str, ai_authors: set[str]):
    """Transform raw merged-PR dicts into (MergedChange, OutcomeEvent) frames.

    Each pr dict: {number, user, merged_at (ISO8601), title, labels: [str]}.
    Revert detected by title prefix 'Revert "'; hotfix by a 'hotfix' label.
    """
    change_rows, event_rows = [], []
    for pr in prs:
        cid = f"{repo}#{pr['number']}"
        merged_at = pd.Timestamp(pr["merged_at"]).strftime("%Y-%m-%d")
        change_rows.append([
            cid, pr["user"], iso_week(pr["merged_at"]), merged_at, repo,
            pr["user"] in ai_authors,
        ])
        title = pr.get("title", "")
        labels = set(pr.get("labels", []))
        if title.startswith('Revert "'):
            event_rows.append([cid, "revert", merged_at])
        elif "hotfix" in labels:
            event_rows.append([cid, "hotfix_72h", merged_at])

    changes = pd.DataFrame(change_rows, columns=[
        "change_id", "author_id", "iso_week_merged", "merged_at", "repo", "is_ai_heavy"])
    events = pd.DataFrame(event_rows, columns=["change_id", "kind", "occurred_at"])
    return changes, events


def fetch_merged_prs(repo: str, token: str, since: str | None = None) -> list[dict]:  # pragma: no cover
    """Fetch merged PRs from the GitHub REST API. Thin wrapper; not unit-tested.

    Returns dicts shaped for build_changes_from_prs.
    """
    import requests

    out, page = [], 1
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    while True:
        resp = requests.get(
            f"https://api.github.com/repos/{repo}/pulls",
            params={"state": "closed", "per_page": 100, "page": page},
            headers=headers, timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        for pr in batch:
            if not pr.get("merged_at"):
                continue
            if since and pr["merged_at"] < since:
                continue
            out.append({
                "number": pr["number"],
                "user": (pr.get("user") or {}).get("login", "unknown"),
                "merged_at": pr["merged_at"],
                "title": pr.get("title", ""),
                "labels": [l["name"] for l in pr.get("labels", [])],
            })
        page += 1
    return out
```

`src/cpvo/loaders/gitlab.py`:
```python
"""GitLab adapter — documented stub.

The GitHub adapter (loaders/github.py) proves the pattern: fetch merged MRs,
map author + merged_at, detect revert/hotfix signals, emit MergedChange and
OutcomeEvent. A GitLab implementation would mirror it against the GitLab MR API.
Not implemented in v1 on purpose — see the plan's "out of scope".
"""
from __future__ import annotations


def fetch_merged_mrs(project: str, token: str):  # pragma: no cover
    raise NotImplementedError(
        "GitLab adapter is a v1 stub. Mirror loaders/github.py against the "
        "GitLab merge-requests API to implement."
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_github.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cpvo/loaders/github.py src/cpvo/loaders/gitlab.py tests/test_github.py
git commit -m "feat: GitHub PR adapter (pure transform + fetch) and GitLab stub"
```

---

## Task 13: Render tokens + CLI formatter (`render/tokens.py`, `render/cli.py`)

**Files:**
- Create: `src/cpvo/render/tokens.py`, `src/cpvo/render/cli.py`
- Test: extend `tests/test_cpvo.py` is not appropriate; create `tests/test_render_cli.py`

- [ ] **Step 1: Write the failing test**

`tests/test_render_cli.py`:
```python
from cpvo.loaders.synthetic import generate, AS_OF
from cpvo.render.cli import render_team_text, render_mirror_text, WATERMARK

def test_team_text_has_watermark_and_no_individual_names():
    ds = generate(seed=7)
    text = render_team_text(ds, n_days=14, as_of=AS_OF)
    assert WATERMARK in text
    assert "Atlas" in text
    # team report must NOT print individual author ids
    for author_id in ds.author["author_id"]:
        assert author_id not in text

def test_mirror_text_is_single_subject():
    ds = generate(seed=7)
    text = render_mirror_text(ds, "a_waste1")
    assert "a_waste1" in text
    assert "not a scoreboard" in text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_render_cli.py -q`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement**

`src/cpvo/render/tokens.py`:
```python
"""Design tokens ported from the sawinyh blog chart system + shared watermark."""

WATERMARK = "[ILLUSTRATIVE — synthetic data]"

COLORS = {
    "teal": "#5de4db",
    "amber": "#ffcf56",
    "rose": "#ff6b8a",
    "slate": "#a0aab8",
    "text": "#eae8e4",
    "muted": "#7a7a8a",
    "grid": "#2a2a34",
    "bg": "#1a1a24",
    "deepBg": "#14141c",
}
FONT = "Arial, Helvetica, sans-serif"
```

`src/cpvo/render/cli.py`:
```python
"""Text-table + JSON rendering. Team path never names individuals; mirror is 1 IC."""
from __future__ import annotations

import json

from ..engine.cohort import cohort_compare
from ..engine.cpvo import cpvo_summary
from ..engine.mirror import mirror
from ..engine.review_tax import review_tax
from ..schema import Dataset
from .tokens import WATERMARK


def _fmt(v, money=False):
    if v is None:
        return "n/a"
    return f"${v:,.0f}" if money else f"{v:.2f}"


def render_team_text(ds: Dataset, n_days: int = 14, as_of: str | None = None) -> str:
    """Team-altitude report: CPVO distribution + review tax. No individual names."""
    summ = cpvo_summary(ds, n_days, as_of)
    lines = [WATERMARK, "", "TEAM ALTITUDE — where budget decisions live", ""]
    lines.append(f"{'team':<10} {'spend':>10} {'weight':>8} {'cpvo':>10} {'median/wk':>10} {'p90/wk':>10}")
    for _, r in summ.iterrows():
        lines.append(
            f"{r['team']:<10} {_fmt(r['spend'], money=True):>10} {int(r['outcome_weight']):>8} "
            f"{_fmt(r['cpvo'], money=True):>10} {_fmt(r['median_weekly_cpvo'], money=True):>10} "
            f"{_fmt(r['p90_weekly_cpvo'], money=True):>10}"
        )
    rt = review_tax(ds)
    lines += ["", "Review tax:"]
    if rt is None:
        lines.append("  not computable (no review records)")
    else:
        lines.append(
            f"  AI-heavy {_fmt(rt['ai_heavy_mean'])} min vs human {_fmt(rt['human_mean'])} min "
            f"-> {_fmt(rt['ratio'])}x"
        )
    return "\n".join(lines)


def render_team_json(ds: Dataset, n_days: int = 14, as_of: str | None = None) -> str:
    summ = cpvo_summary(ds, n_days, as_of)
    return json.dumps({
        "watermark": WATERMARK,
        "teams": summ.to_dict(orient="records"),
        "review_tax": review_tax(ds),
    }, indent=2, default=str)


def render_mirror_text(ds: Dataset, author_id: str) -> str:
    """Private mirror for ONE IC. Carries the for-you-not-a-scoreboard preamble."""
    m = mirror(ds, author_id)
    return "\n".join([
        WATERMARK,
        "",
        "PRIVATE MIRROR — for your own self-correction, not a scoreboard.",
        "These numbers are never ranked against anyone else.",
        "",
        f"  author:        {m['author_id']}",
        f"  rework ratio:  {_fmt(m['rework_ratio'])}  ({m['rework_ratio_note']})",
        f"  thrash ratio:  {_fmt(m['thrash_ratio'])}"
        + (f"  ({m['thrash_note']})" if m["thrash_note"] else ""),
    ])


def render_cohort_text(ds: Dataset, ai_heavy: str, ai_light: str,
                       n_days: int = 14, as_of: str | None = None,
                       min_outcomes: int = 20) -> str:
    res = cohort_compare(ds, ai_heavy, ai_light, n_days, as_of, min_outcomes)
    lines = [WATERMARK, "", "BUDGET ALTITUDE — cohort comparison (two axes)", ""]
    for side in ("ai_heavy", "ai_light"):
        s = res[side]
        lines.append(
            f"  {side:<9} {s['team']:<10} weight={s['outcome_weight']:>4} "
            f"fail_rate={_fmt(s['fail_rate'])} spend={_fmt(s['spend'], money=True)} "
            f"cpvo={_fmt(s['cpvo'], money=True)}"
        )
    lines += ["", "Verdict:"]
    lines.append(f"  {res['verdict'] or 'NO VERDICT — ' + res['verdict_reason']}")
    lines += ["", "Read like a skeptic:"]
    lines += [f"  - {c}" for c in res["caveats"]]
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_render_cli.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cpvo/render/tokens.py src/cpvo/render/cli.py tests/test_render_cli.py
git commit -m "feat: CLI text/JSON renderers (team, mirror, cohort)"
```

---

## Task 14: Dashboard renderer (`render/dashboard.py`)

**Files:**
- Create: `src/cpvo/render/dashboard.py`
- Test: `tests/test_dashboard.py`

Builds a self-contained HTML string with inline SVG. Four team cuts above a literal wall divider, one IC mirror below. We test structure/markers, not pixels.

- [ ] **Step 1: Write the failing test**

`tests/test_dashboard.py`:
```python
from cpvo.loaders.synthetic import generate, AS_OF
from cpvo.render.dashboard import render_dashboard

def test_dashboard_has_wall_and_watermark_and_four_cuts():
    ds = generate(seed=7)
    html = render_dashboard(ds, mirror_author="a_waste1", n_days=14, as_of=AS_OF)
    assert "<html" in html and "</html>" in html
    assert "ILLUSTRATIVE" in html
    assert "nothing below is ever ranked" in html.lower()
    for title in ["Spend / team / week", "Outcome weight / team / week",
                  "Team CPVO trend", "Rework-ratio trend"]:
        assert title in html
    # exactly one mirror subject below the wall
    wall_split = html.lower().split("nothing below is ever ranked", 1)[1]
    assert "a_waste1" in wall_split
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_dashboard.py -q`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement**

`src/cpvo/render/dashboard.py`:
```python
"""Static HTML/SVG starter dashboard: four team cuts above the wall, one IC mirror below."""
from __future__ import annotations

import pandas as pd

from ..engine.cpvo import team_spend_by_week, weekly_team_cpvo
from ..engine.mirror import mirror
from ..engine.outcomes import verified_changes
from ..schema import Dataset
from .tokens import COLORS, FONT, WATERMARK

W, H, PAD = 460, 200, 40


def _line_svg(title: str, series: dict[str, list[tuple[str, float]]]) -> str:
    """One small multi-line chart. series: {label: [(week, value)]}."""
    weeks = sorted({wk for pts in series.values() for wk, _ in pts})
    xs = {wk: PAD + i * (W - 2 * PAD) / max(1, len(weeks) - 1) for i, wk in enumerate(weeks)}
    all_vals = [v for pts in series.values() for _, v in pts if v is not None] or [0, 1]
    vmax = max(all_vals) or 1
    palette = [COLORS["teal"], COLORS["amber"], COLORS["rose"], COLORS["slate"]]

    def y(v):
        return H - PAD - (v / vmax) * (H - 2 * PAD)

    parts = [
        f'<rect width="{W}" height="{H}" rx="4" fill="{COLORS["bg"]}"/>',
        f'<text x="{PAD//2}" y="24" fill="{COLORS["text"]}" '
        f'font-family="{FONT}" font-size="14">{title}</text>',
    ]
    for idx, (label, pts) in enumerate(series.items()):
        color = palette[idx % len(palette)]
        pts = [(wk, v) for wk, v in pts if v is not None]
        if not pts:
            continue
        d = " ".join(
            f"{'M' if i == 0 else 'L'}{xs[wk]:.1f},{y(v):.1f}" for i, (wk, v) in enumerate(pts)
        )
        parts.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2"/>')
        parts.append(
            f'<text x="{W-PAD}" y="{y(pts[-1][1]):.1f}" fill="{color}" '
            f'font-family="{FONT}" font-size="11" text-anchor="end">{label}</text>'
        )
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{"".join(parts)}</svg>'


def _series_by_team(df: pd.DataFrame, value_col: str) -> dict:
    out = {}
    for team, g in df.groupby("team"):
        out[team] = list(zip(g["iso_week"], g[value_col]))
    return out


def render_dashboard(ds: Dataset, mirror_author: str, n_days: int = 14,
                     as_of: str | None = None) -> str:
    spend = team_spend_by_week(ds).sort_values(["team", "iso_week"])
    weekly = weekly_team_cpvo(ds, n_days, as_of).sort_values(["team", "iso_week"])

    # outcome weight per team per week
    vc = verified_changes(ds, n_days, as_of).merge(
        ds.author[["author_id", "team"]], on="author_id", how="left")
    vc["net"] = vc["verified"].astype(int) - (vc["settled"] & vc["failed"]).astype(int)
    ow = vc.groupby(["team", "iso_week_merged"], as_index=False)["net"].sum().rename(
        columns={"iso_week_merged": "iso_week", "net": "weight"})

    # rework-ratio trend per team per week (team aggregate of events/merges)
    ev_ids = set(ds.outcome_event["change_id"])
    mc = ds.merged_change.merge(ds.author[["author_id", "team"]], on="author_id", how="left")
    mc["has_event"] = mc["change_id"].isin(ev_ids).astype(int)
    rw = mc.groupby(["team", "iso_week_merged"], as_index=False).agg(
        events=("has_event", "sum"), merges=("change_id", "count"))
    rw["rework"] = rw["events"] / rw["merges"].clip(lower=1)
    rw = rw.rename(columns={"iso_week_merged": "iso_week"})

    cut1 = _line_svg("Spend / team / week", _series_by_team(spend, "dollars"))
    cut2 = _line_svg("Outcome weight / team / week", _series_by_team(ow, "weight"))
    cut3 = _line_svg("Team CPVO trend", _series_by_team(weekly, "cpvo"))
    cut4 = _line_svg("Rework-ratio trend", _series_by_team(rw, "rework"))

    m = mirror(ds, mirror_author)
    bg, deep, text, muted, rose = (COLORS["bg"], COLORS["deepBg"], COLORS["text"],
                                   COLORS["muted"], COLORS["rose"])
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>CPVO starter dashboard</title>
<style>
 body {{ background:{deep}; color:{text}; font-family:{FONT}; margin:0; padding:32px; }}
 .wm {{ color:{COLORS['amber']}; font-size:13px; letter-spacing:1px; }}
 h1 {{ font-size:20px; font-weight:600; }}
 h2 {{ font-size:14px; color:{muted}; text-transform:uppercase; letter-spacing:1px; }}
 .grid {{ display:grid; grid-template-columns:repeat(2, {W}px); gap:16px; }}
 .wall {{ border:0; border-top:2px dashed {rose}; margin:32px 0 8px; }}
 .wall-label {{ color:{rose}; font-size:13px; }}
 .mirror {{ background:{bg}; border-radius:6px; padding:16px; max-width:{2*W+16}px; }}
 .mirror .note {{ color:{muted}; font-size:12px; }}
</style></head>
<body>
 <div class="wm">{WATERMARK}</div>
 <h1>CPVO starter dashboard · 12 weeks</h1>
 <h2>Team altitude — where budget decisions live</h2>
 <div class="grid">{cut1}{cut2}{cut3}{cut4}</div>
 <hr class="wall"><div class="wall-label">THE WALL — nothing below is ever ranked</div>
 <h2>Private mirror — visible only to the individual</h2>
 <div class="mirror">
   <div><strong>{m['author_id']}</strong></div>
   <div>rework ratio: {('%.2f' % m['rework_ratio']) if m['rework_ratio'] is not None else 'n/a'}
        <span class="note">({m['rework_ratio_note']})</span></div>
   <div>thrash ratio: {('%.2f' % m['thrash_ratio']) if m['thrash_ratio'] is not None else 'n/a'}
        <span class="note">{m['thrash_note']}</span></div>
   <div class="note">For self-correction, not a scoreboard.</div>
 </div>
</body></html>"""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_dashboard.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cpvo/render/dashboard.py tests/test_dashboard.py
git commit -m "feat: static HTML/SVG starter dashboard with the wall divider"
```

---

## Task 15: CLI entry (`cli.py`)

**Files:**
- Create: `src/cpvo/cli.py`
- Test: `tests/test_cli.py`

Five subcommands. `--source` defaults to `synthetic`. `mirror` takes exactly one `--author`. No `rank`/`leaderboard` subcommand exists.

- [ ] **Step 1: Write the failing test**

`tests/test_cli.py`:
```python
from cpvo.cli import build_parser, main

def test_parser_subcommands_exact_set():
    parser = build_parser()
    sub = [a for a in parser._subparsers._group_actions[0].choices]
    assert set(sub) == {"demo", "team", "mirror", "cohort", "dashboard"}
    assert "rank" not in sub and "leaderboard" not in sub

def test_mirror_requires_single_author(capsys):
    # argparse --author takes one value; passing the flag once is the only shape
    rc = main(["mirror", "--author", "a_waste1"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "a_waste1" in out
    assert "scoreboard" in out.lower()

def test_demo_runs_and_watermarks(capsys):
    rc = main(["demo"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "ILLUSTRATIVE" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_cli.py -q`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement**

`src/cpvo/cli.py`:
```python
"""cpvo command-line entry. The wall is enforced at the boundary:
no rank/leaderboard subcommand exists, and `mirror` takes a single --author.
"""
from __future__ import annotations

import argparse
import sys

from .loaders.synthetic import AS_OF as SYNTH_AS_OF
from .loaders.synthetic import generate
from .render.cli import (render_cohort_text, render_mirror_text,
                         render_team_json, render_team_text)
from .render.dashboard import render_dashboard


def _load(args):
    """Resolve a Dataset from --source. Only synthetic is wired for v1 CLI.

    Real sources (github/csv) require config beyond v1 flags; the loaders exist
    and are documented, but the demo path is synthetic. Honest about that here.
    """
    if getattr(args, "source", "synthetic") == "synthetic":
        return generate(seed=7), SYNTH_AS_OF
    raise SystemExit(
        f"source '{args.source}' loaders exist (cpvo.loaders) but are not wired "
        "into the v1 CLI; use them programmatically. CLI demo uses --source synthetic."
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cpvo", description="Cost per verified outcome harness.")
    sub = p.add_subparsers(dest="command", required=True)

    def add_common(sp):
        sp.add_argument("--source", default="synthetic", choices=["synthetic", "github", "csv"])
        sp.add_argument("--n-days", type=int, default=14)

    sp_demo = sub.add_parser("demo", help="Run the full synthetic walkthrough.")
    add_common(sp_demo)

    sp_team = sub.add_parser("team", help="Team-altitude CPVO report.")
    add_common(sp_team)
    sp_team.add_argument("--json", action="store_true")

    sp_mirror = sub.add_parser("mirror", help="One IC's private mirror.")
    add_common(sp_mirror)
    sp_mirror.add_argument("--author", required=True, help="A SINGLE author id.")

    sp_cohort = sub.add_parser("cohort", help="AI-heavy vs AI-light comparison.")
    add_common(sp_cohort)
    sp_cohort.add_argument("--ai-heavy", required=True)
    sp_cohort.add_argument("--ai-light", required=True)
    sp_cohort.add_argument("--min-outcomes", type=int, default=20)

    sp_dash = sub.add_parser("dashboard", help="Render the static HTML/SVG dashboard.")
    add_common(sp_dash)
    sp_dash.add_argument("--out", default="dashboard.html")
    sp_dash.add_argument("--mirror-author", default="a_waste1")

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    ds, as_of = _load(args)

    if args.command == "demo":
        print(render_team_text(ds, args.n_days, as_of))
        print()
        print(render_cohort_text(ds, "Atlas", "Cardinal", args.n_days, as_of, min_outcomes=20))
        print()
        print(render_mirror_text(ds, "a_waste1"))
        return 0

    if args.command == "team":
        print(render_team_json(ds, args.n_days, as_of) if args.json
              else render_team_text(ds, args.n_days, as_of))
        return 0

    if args.command == "mirror":
        print(render_mirror_text(ds, args.author))
        return 0

    if args.command == "cohort":
        print(render_cohort_text(ds, args.ai_heavy, args.ai_light, args.n_days, as_of,
                                 args.min_outcomes))
        return 0

    if args.command == "dashboard":
        html = render_dashboard(ds, mirror_author=args.mirror_author,
                                n_days=args.n_days, as_of=as_of)
        with open(args.out, "w") as fh:
            fh.write(html)
        print(f"wrote {args.out}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_cli.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/cpvo/cli.py tests/test_cli.py
git commit -m "feat: cpvo CLI entry with five subcommands"
```

---

## Task 16: The conscience test (`test_wall.py`)

**Files:**
- Create: `tests/test_wall.py`

Asserts the wall holds structurally and regression-protects it.

- [ ] **Step 1: Write the test (this one should PASS immediately — it asserts existing structure)**

`tests/test_wall.py`:
```python
"""The wall: contributor numbers are a private mirror, never ranked. These tests
fail if anyone later adds a leaderboard code path."""
import inspect
import pytest

import cpvo.engine.mirror as mirror_mod
from cpvo.cli import build_parser
from cpvo.engine.mirror import mirror
from cpvo.loaders.synthetic import generate


def test_no_ranking_words_in_mirror_module_api():
    public = [n for n in dir(mirror_mod) if not n.startswith("_")]
    for name in public:
        assert "rank" not in name.lower()
        assert "leaderboard" not in name.lower()
        assert "top" not in name.lower()


def test_mirror_functions_take_single_str_author():
    sig = inspect.signature(mirror)
    params = list(sig.parameters)
    assert params[1] == "author_id"
    ds = generate(seed=7)
    with pytest.raises(TypeError):
        mirror(ds, ["a_lead", "a_solid"])  # collection rejected


def test_cli_has_no_rank_or_leaderboard_command():
    parser = build_parser()
    choices = set(parser._subparsers._group_actions[0].choices)
    assert "rank" not in choices
    assert "leaderboard" not in choices
    assert "mirror" in choices  # the only per-IC surface


def test_team_renderer_does_not_emit_author_ids():
    from cpvo.render.cli import render_team_text
    from cpvo.loaders.synthetic import AS_OF
    ds = generate(seed=7)
    text = render_team_text(ds, n_days=14, as_of=AS_OF)
    for author_id in ds.author["author_id"]:
        assert author_id not in text
```

- [ ] **Step 2: Run the test**

Run: `.venv/bin/pytest tests/test_wall.py -q`
Expected: PASS (4 passed)

- [ ] **Step 3: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_wall.py
git commit -m "test: the wall conscience test (no leaderboard code path)"
```

---

## Task 17: README, fixtures dump, smoke run, push

**Files:**
- Create: `README.md`
- Create (generated): `fixtures/synthetic/*.csv`

- [ ] **Step 1: Write `README.md`**

Content must include: one-paragraph pitch tying to the post; the install + `cpvo demo` quickstart; an explanation of the two-level wall and why there's no leaderboard; the honesty notes (weekly seat-to-author grain, no per-PR cost, thrash conditional); a clearly-labeled note that the bundled dataset is synthetic/illustrative; and a link to https://sawinyh.com/blog/measuring-ai-spend-not-value/. Keep it tight (~120 lines max).

- [ ] **Step 2: Add a fixtures-dump helper invocation**

Add a `__main__` block to `src/cpvo/loaders/synthetic.py` that writes each table to `fixtures/synthetic/<table>.csv` so readers can see input shape:
```python
if __name__ == "__main__":  # pragma: no cover
    import os
    ds = generate(seed=7)
    os.makedirs("fixtures/synthetic", exist_ok=True)
    for name in ["seat_spend", "seat_author", "author", "merged_change",
                 "outcome_event", "review_record", "session_spend"]:
        getattr(ds, name).to_csv(f"fixtures/synthetic/{name}.csv", index=False)
    print("wrote fixtures/synthetic/*.csv")
```
Run: `.venv/bin/python -m cpvo.loaders.synthetic`
Expected: writes 7 CSVs. (These are gitignored; they're a convenience, regenerable.)

- [ ] **Step 3: Smoke-run the CLI end to end**

Run:
```bash
.venv/bin/cpvo demo | head -40
.venv/bin/cpvo team --json | head -20
.venv/bin/cpvo dashboard --out /tmp/cpvo.html && echo "dashboard ok"
```
Expected: demo prints team report + cohort + mirror, all watermarked; JSON parses; dashboard writes.

- [ ] **Step 4: Commit and push**

```bash
git add README.md src/cpvo/loaders/synthetic.py
git commit -m "docs: README + synthetic fixtures dump helper"
git push -u origin main
```
Expected: pushes to https://github.com/sneg55/cpvo

---

## Self-review notes (author)

- **Spec coverage:** schema (T3), all five metrics + thrash-conditional (T5–T9), synthetic narrative (T10), seat-CSV + GitHub adapters (T11–T12), CLI five subcommands (T15), dashboard four-cuts-plus-mirror (T14), the wall enforced + conscience test (T7, T15, T16), watermarking everywhere (T10/T13/T14). Covered.
- **Schema delta vs spec:** Author + SessionSpend tables added (noted at top); reconcile the spec's schema section after the build.
- **Type consistency:** `Dataset` field names, `outcome_weight`/`cpvo`/`mirror` signatures, `WATERMARK`, and column-name lists are consistent across tasks. `mirror(ds, author_id: str)` rejects collections in both T7 and T16. `as_of`/`n_days` threaded uniformly.
- **No placeholders:** every code step is complete and runnable. The only stub is the deliberate GitLab adapter (documented, in scope decision).

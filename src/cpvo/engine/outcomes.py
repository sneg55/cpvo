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

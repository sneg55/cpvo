"""Team CPVO: seat-week spend joined to outcome weight (team altitude, money)."""
from __future__ import annotations

import pandas as pd

from ..schema import Dataset
from .outcomes import outcome_weight_by, verified_changes


def _spend_with_team(ds: Dataset) -> pd.DataFrame:
    """SeatSpend joined seat->author->team. The seat-to-author backbone."""
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

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

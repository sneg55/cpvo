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

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
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}">{"".join(parts)}</svg>')


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
    rework_str = ("%.2f" % m["rework_ratio"]) if m["rework_ratio"] is not None else "n/a"
    thrash_str = ("%.2f" % m["thrash_ratio"]) if m["thrash_ratio"] is not None else "n/a"
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
 <h2>Team altitude - where budget decisions live</h2>
 <div class="grid">{cut1}{cut2}{cut3}{cut4}</div>
 <hr class="wall"><div class="wall-label">THE WALL - nothing below is ever ranked</div>
 <h2>Private mirror - visible only to the individual</h2>
 <div class="mirror">
   <div><strong>{m['author_id']}</strong></div>
   <div>rework ratio: {rework_str}
        <span class="note">({m['rework_ratio_note']})</span></div>
   <div>thrash ratio: {thrash_str}
        <span class="note">{m['thrash_note']}</span></div>
   <div class="note">For self-correction, not a scoreboard.</div>
 </div>
</body></html>"""

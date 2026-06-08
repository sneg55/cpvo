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

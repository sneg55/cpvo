# cpvo — cost per verified outcome

A small reference harness for the question every engineering org now dreads:
**we spend a lot on AI dev tools — is it working?**

The only number most teams can defend is the invoice, and the invoice tells you
nothing about value. `cpvo` changes the unit. It joins AI-tool **spend** to the
**outcomes that survived production** and reports cost per verified outcome —
plus the failure shapes (rework, thrash, review tax) that raw spend hides.

It is the companion code to the essay
**[You're Measuring AI Spend, Not AI Value](https://sawinyh.com/blog/measuring-ai-spend-not-value/)**.
Clone it, run `cpvo demo`, and see the method on synthetic data in one command.

> The bundled dataset is **synthetic and illustrative** — every output is
> watermarked `[ILLUSTRATIVE — synthetic data]`. None of the figures are real
> measurements; they exist to demonstrate the metric.

## Quickstart

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/cpvo demo                 # full walkthrough on synthetic data
.venv/bin/cpvo dashboard --out cpvo.html   # the "four cuts + private mirror" dashboard
.venv/bin/pytest -q                 # 39 tests, including the wall conscience test
```

`cpvo demo` prints something like:

```
TEAM ALTITUDE — where budget decisions live

team            spend   weight       cpvo  median/wk     p90/wk
Atlas          $6,600       52       $127       $110       $192
Borealis       $3,192       57        $56        $52        $66
Cardinal         $540       57         $9         $9        $21

Review tax:
  AI-heavy 68 min vs human 24 min -> 2.87x
```

Atlas isn't a disaster — it has a healthy-ish median and a **long expensive tail**
(p90 $192 vs median $110) worth investigating. Cardinal is the AI-light cohort:
far less spend, comparable outcome weight, lower fail rate. That's the honest
shape of the question, not "AI good / AI bad".

## The metric

A **verified outcome** is a merged change that shipped and *stayed shipped* —
it survives N days (default 14) with no revert, no 72-hour hotfix, no reopened
ticket. **Outcome weight** is the net count: survivors minus failures. There is
no subjective "importance" score — the only weighting is the objective survival
test, because importance is infinitely gameable.

**Cost per verified outcome** = team seat-week dollars ÷ team outcome weight.

## The two-level wall (enforced in code)

The load-bearing rule from the essay: **contributor numbers are a private
mirror, never ranked; money decisions live at team altitude.** This repo
enforces that *structurally*, not with a disclaimer:

- `cpvo mirror --author <id>` reports **one** IC's own rework and thrash. It
  refuses a list of authors.
- `cpvo team` / `cpvo dashboard` aggregate to team only and never print
  individual author ids.
- There is **no** `rank` or `leaderboard` command, and no function anywhere
  returns a ranked per-contributor list. `tests/test_wall.py` asserts this and
  fails the build if anyone adds one.

The leaderboard the essay warns about is, by design, unspellable here.

## Honesty constraints

This harness is deliberately coarse where the data is coarse:

- **Weekly seat-to-author grain, never per-PR cost.** Per-PR AI attribution
  doesn't exist today; the schema makes it *unrepresentable* so you can't build
  a beautiful dashboard on guesswork.
- **Thrash is conditionally computable.** It needs session/branch-grain spend.
  The synthetic data ships it; real exports that only have seat-weekly spend get
  an honest `"thrash not computable"` instead of a fabricated number.
- **Cohort comparison gates on a minimum denominator** and prints its
  confounders (selection bias, small denominators, skill-ceiling) next to the
  result. An honest null beats a vanity chart.

## Commands

| Command | Altitude | What it does |
|---------|----------|--------------|
| `cpvo demo` | all | Full synthetic walkthrough |
| `cpvo team [--json]` | team / money | CPVO distribution + trend + review tax |
| `cpvo mirror --author <id>` | IC / private | One contributor's rework + thrash |
| `cpvo cohort --ai-heavy <t> --ai-light <t>` | budget | Two-axis comparison + caveats |
| `cpvo dashboard --out f.html` | — | Static HTML/SVG: four team cuts + walled mirror |

## Bring your own data

The CLI demo runs on synthetic data. The loaders for real sources exist and are
documented — use them programmatically:

- `cpvo.loaders.seat_csv.load_seat_spend(path)` — seat-week spend CSV
- `cpvo.loaders.mapping.load_mapping(path)` — `seat_id: author_id` YAML
- `cpvo.loaders.github.fetch_merged_prs(repo, token)` + `build_changes_from_prs(...)`
  — PR / revert / hotfix history (no per-PR cost; cost stays seat-week)
- `cpvo.loaders.gitlab` — documented stub; mirror the GitHub adapter

Assemble a `cpvo.schema.Dataset` from these and pass it to the `cpvo.engine`
functions. Every loader declares the grain its source actually provides; metrics
that aren't computable from your sources are skipped honestly.

## Architecture

```
loaders/  →  canonical Dataset  →  engine/ (pure)  →  render/ (cli + dashboard)
```

Loaders are the only source-specific code; everything downstream speaks the
canonical schema. See `docs/superpowers/plans/` for the full design and
implementation plan.

## License

MIT.

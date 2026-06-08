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

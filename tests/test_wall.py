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

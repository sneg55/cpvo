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

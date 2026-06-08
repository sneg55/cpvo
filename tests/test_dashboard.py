from cpvo.loaders.synthetic import generate, AS_OF
from cpvo.render.dashboard import render_dashboard


def test_dashboard_has_wall_and_watermark_and_four_cuts():
    ds = generate(seed=7)
    html = render_dashboard(ds, mirror_author="a_waste1", n_days=14, as_of=AS_OF)
    assert "<html" in html and "</html>" in html
    assert "ILLUSTRATIVE" in html
    assert "nothing below is ever ranked" in html.lower()
    for title in ["Spend / team / week", "Outcome weight / team / week",
                  "Team CPVO trend", "Rework-ratio trend"]:
        assert title in html
    # exactly one mirror subject below the wall
    wall_split = html.lower().split("nothing below is ever ranked", 1)[1]
    assert "a_waste1" in wall_split

from cpvo.engine.review_tax import review_tax


def test_review_tax_ratio(tiny):
    r = review_tax(tiny)
    assert r["ai_heavy_mean"] == 50.0   # (60+40)/2
    assert r["human_mean"] == 20.0
    assert r["ratio"] == 2.5


def test_review_tax_none_without_records(tiny):
    tiny.review_record = None
    assert review_tax(tiny) is None

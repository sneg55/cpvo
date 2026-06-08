import pytest
from cpvo.engine.mirror import rework_ratio, thrash_ratio, mirror


def test_rework_ratio(tiny):
    # a1 authored c1,c2; events on a1's changes: c2 revert -> 1 event / 2 merged = 0.5
    assert rework_ratio(tiny, "a1") == 0.5


def test_thrash_ratio_uses_session_spend(tiny):
    # a1: non-merged 40 / total 160 = 0.25
    assert thrash_ratio(tiny, "a1") == 0.25


def test_thrash_none_without_session_spend(tiny):
    tiny.session_spend = None
    val, reason = thrash_ratio(tiny, "a1", with_reason=True)
    assert val is None
    assert "not computable" in reason


def test_mirror_is_single_subject(tiny):
    m = mirror(tiny, "a1")
    assert m["author_id"] == "a1"
    assert m["rework_ratio"] == 0.5
    assert m["thrash_ratio"] == 0.25


def test_mirror_rejects_non_string_author(tiny):
    with pytest.raises(TypeError, match="single author_id"):
        mirror(tiny, ["a1", "a2"])

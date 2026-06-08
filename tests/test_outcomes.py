from cpvo.engine.outcomes import verified_changes, outcome_weight, outcome_weight_by
from tests.conftest import AS_OF


def test_verified_flags(tiny):
    vc = verified_changes(tiny, n_days=14, as_of=AS_OF).set_index("change_id")
    assert bool(vc.loc["c1", "verified"]) is True
    assert bool(vc.loc["c2", "failed"]) is True
    assert bool(vc.loc["c2", "verified"]) is False


def test_total_outcome_weight(tiny):
    # verified {c1,c3,c4}=3, failed {c2,c5}=2 -> 1
    assert outcome_weight(tiny, n_days=14, as_of=AS_OF) == 1


def test_outcome_weight_by_team(tiny):
    w = outcome_weight_by(tiny, by="team", n_days=14, as_of=AS_OF).set_index("team")["outcome_weight"]
    assert w.loc["alpha"] == 1   # verified 2, failed 1
    assert w.loc["beta"] == 0    # verified 1, failed 1

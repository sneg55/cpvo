import math
from cpvo.engine.cpvo import team_spend_by_week, cpvo_summary
from tests.conftest import AS_OF


def test_team_spend_joins_seats_to_team(tiny):
    s = team_spend_by_week(tiny).set_index("team")["dollars"]
    assert s.loc["alpha"] == 150.0   # a1 100 + a2 50
    assert s.loc["beta"] == 20.0


def test_cpvo_summary_overall(tiny):
    summ = cpvo_summary(tiny, n_days=14, as_of=AS_OF).set_index("team")
    assert summ.loc["alpha", "spend"] == 150.0
    assert summ.loc["alpha", "outcome_weight"] == 1
    assert summ.loc["alpha", "cpvo"] == 150.0
    # beta weight 0 -> cpvo is None (undefined), never inf or a fake number
    assert summ.loc["beta", "cpvo"] is None or math.isnan(summ.loc["beta", "cpvo"])

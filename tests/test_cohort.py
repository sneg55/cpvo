from cpvo.engine.cohort import cohort_compare
from tests.conftest import AS_OF


def test_cohort_gates_on_min_outcomes(tiny):
    # alpha weight 1, beta weight 0 -> both below min_outcomes=20 -> no verdict
    res = cohort_compare(tiny, "alpha", "beta", n_days=14, as_of=AS_OF, min_outcomes=20)
    assert res["verdict"] is None
    assert "too few outcomes" in res["verdict_reason"]


def test_cohort_reports_two_axes_and_caveats(tiny):
    res = cohort_compare(tiny, "alpha", "beta", n_days=14, as_of=AS_OF, min_outcomes=1)
    assert set(res["ai_heavy"]) >= {"team", "outcome_weight", "fail_rate", "spend", "cpvo"}
    assert res["ai_heavy"]["team"] == "alpha"
    assert res["ai_light"]["team"] == "beta"
    assert any("selection bias" in c.lower() for c in res["caveats"])

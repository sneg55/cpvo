import pandas as pd
from cpvo.weeks import iso_week, is_settled


def test_iso_week_formats_year_and_week():
    assert iso_week("2026-01-05") == "2026-W02"
    assert iso_week(pd.Timestamp("2026-01-01")) == "2026-W01"


def test_is_settled_true_when_older_than_n_days():
    assert is_settled("2026-01-01", as_of="2026-01-20", n_days=14) is True


def test_is_settled_false_when_within_window():
    assert is_settled("2026-01-15", as_of="2026-01-20", n_days=14) is False

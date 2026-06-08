import pandas as pd
import pytest
from cpvo.schema import Dataset, validate_columns, OUTCOME_KINDS, SEAT_SPEND_COLS


def test_validate_columns_passes_with_exact_columns():
    df = pd.DataFrame({c: [] for c in SEAT_SPEND_COLS})
    validate_columns(df, SEAT_SPEND_COLS, "SeatSpend")  # no raise


def test_validate_columns_raises_on_missing():
    df = pd.DataFrame({"seat_id": []})
    with pytest.raises(ValueError, match="SeatSpend.*missing"):
        validate_columns(df, SEAT_SPEND_COLS, "SeatSpend")


def test_outcome_kinds_are_the_closed_set():
    assert OUTCOME_KINDS == {"revert", "hotfix_72h", "ticket_reopened"}


def test_dataset_optional_tables_default_none():
    ds = Dataset(
        seat_spend=pd.DataFrame(),
        seat_author=pd.DataFrame(),
        author=pd.DataFrame(),
        merged_change=pd.DataFrame(),
        outcome_event=pd.DataFrame(),
    )
    assert ds.review_record is None
    assert ds.session_spend is None

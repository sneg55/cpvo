from cpvo.loaders.seat_csv import load_seat_spend


def test_load_seat_spend(tmp_path):
    p = tmp_path / "spend.csv"
    p.write_text("seat_id,tool,iso_week,dollars\ns1,cursor,2026-W01,100\n")
    df = load_seat_spend(str(p))
    assert list(df.columns) == ["seat_id", "tool", "iso_week", "dollars"]
    assert df.loc[0, "dollars"] == 100.0

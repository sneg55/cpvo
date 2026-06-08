from cpvo.loaders.mapping import load_mapping


def test_load_mapping(tmp_path):
    p = tmp_path / "map.yaml"
    p.write_text("s1: a1\ns2: a1\ns3: b1\n")
    df = load_mapping(str(p))
    assert set(df.columns) == {"seat_id", "author_id"}
    assert len(df) == 3
    assert df.loc[df.seat_id == "s2", "author_id"].iloc[0] == "a1"

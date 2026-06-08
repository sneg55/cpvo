from cpvo.loaders.synthetic import generate, AS_OF
from cpvo.engine.cpvo import cpvo_summary
from cpvo.engine.mirror import thrash_ratio


def test_generate_is_deterministic():
    a = generate(seed=7)
    b = generate(seed=7)
    assert a.merged_change.equals(b.merged_change)
    assert a.seat_spend.equals(b.seat_spend)


def test_dataset_validates():
    generate(seed=7).validate()  # no raise


def test_three_teams_present():
    ds = generate(seed=7)
    assert set(ds.author["team"]) == {"Atlas", "Borealis", "Cardinal"}


def test_atlas_has_a_high_burn_low_outcome_contributor():
    # at least one Atlas author has thrash defined and elevated
    ds = generate(seed=7)
    atlas = ds.author.loc[ds.author.team == "Atlas", "author_id"]
    thrashes = [thrash_ratio(ds, a) for a in atlas]
    thrashes = [t for t in thrashes if t is not None]
    assert max(thrashes) >= 0.3


def test_cardinal_is_ai_light_lower_cpvo_pressure():
    ds = generate(seed=7)
    summ = cpvo_summary(ds, n_days=14, as_of=AS_OF).set_index("team")
    # Cardinal spends less than Atlas overall
    assert summ.loc["Cardinal", "spend"] < summ.loc["Atlas", "spend"]

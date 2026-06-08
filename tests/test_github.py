from cpvo.loaders.github import build_changes_from_prs


def test_build_changes_from_prs():
    prs = [
        {"number": 1, "user": "a1", "merged_at": "2026-01-01T10:00:00Z", "title": "feat: x", "labels": []},
        {"number": 2, "user": "a1", "merged_at": "2026-01-02T10:00:00Z", "title": 'Revert "feat: x"', "labels": []},
        {"number": 3, "user": "b1", "merged_at": "2026-01-03T10:00:00Z", "title": "fix: y", "labels": ["hotfix"]},
    ]
    changes, events = build_changes_from_prs(prs, repo="org/repo", ai_authors={"a1"})

    crow = changes.set_index("change_id")
    assert crow.loc["org/repo#1", "iso_week_merged"] == "2026-W01"
    assert bool(crow.loc["org/repo#1", "is_ai_heavy"]) is True
    assert bool(crow.loc["org/repo#3", "is_ai_heavy"]) is False

    kinds = dict(zip(events["change_id"], events["kind"]))
    assert kinds["org/repo#2"] == "revert"
    assert kinds["org/repo#3"] == "hotfix_72h"

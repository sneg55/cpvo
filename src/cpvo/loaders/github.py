"""GitHub adapter: merged PRs -> MergedChange + OutcomeEvent.

Pure transform (build_changes_from_prs) is unit-tested. fetch_merged_prs is a
thin requests wrapper documented but not unit-tested. This adapter provides PR
and revert/hotfix signals only; it does NOT provide per-PR cost — cost comes
solely from seat-week spend.
"""
from __future__ import annotations

import pandas as pd

from ..weeks import iso_week


def build_changes_from_prs(prs: list[dict], repo: str, ai_authors: set[str]):
    """Transform raw merged-PR dicts into (MergedChange, OutcomeEvent) frames.

    Each pr dict: {number, user, merged_at (ISO8601), title, labels: [str]}.
    Revert detected by title prefix 'Revert "'; hotfix by a 'hotfix' label.
    """
    change_rows, event_rows = [], []
    for pr in prs:
        cid = f"{repo}#{pr['number']}"
        merged_at = pd.Timestamp(pr["merged_at"]).strftime("%Y-%m-%d")
        change_rows.append([
            cid, pr["user"], iso_week(pr["merged_at"]), merged_at, repo,
            pr["user"] in ai_authors,
        ])
        title = pr.get("title", "")
        labels = set(pr.get("labels", []))
        if title.startswith('Revert "'):
            event_rows.append([cid, "revert", merged_at])
        elif "hotfix" in labels:
            event_rows.append([cid, "hotfix_72h", merged_at])

    changes = pd.DataFrame(change_rows, columns=[
        "change_id", "author_id", "iso_week_merged", "merged_at", "repo", "is_ai_heavy"])
    events = pd.DataFrame(event_rows, columns=["change_id", "kind", "occurred_at"])
    return changes, events


def fetch_merged_prs(repo: str, token: str, since: str | None = None) -> list[dict]:  # pragma: no cover
    """Fetch merged PRs from the GitHub REST API. Thin wrapper; not unit-tested.

    Returns dicts shaped for build_changes_from_prs.
    """
    import requests

    out, page = [], 1
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    while True:
        resp = requests.get(
            f"https://api.github.com/repos/{repo}/pulls",
            params={"state": "closed", "per_page": 100, "page": page},
            headers=headers, timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        for pr in batch:
            if not pr.get("merged_at"):
                continue
            if since and pr["merged_at"] < since:
                continue
            out.append({
                "number": pr["number"],
                "user": (pr.get("user") or {}).get("login", "unknown"),
                "merged_at": pr["merged_at"],
                "title": pr.get("title", ""),
                "labels": [l["name"] for l in pr.get("labels", [])],
            })
        page += 1
    return out

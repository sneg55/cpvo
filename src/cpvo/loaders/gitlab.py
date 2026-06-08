"""GitLab adapter — documented stub.

The GitHub adapter (loaders/github.py) proves the pattern: fetch merged MRs,
map author + merged_at, detect revert/hotfix signals, emit MergedChange and
OutcomeEvent. A GitLab implementation would mirror it against the GitLab MR API.
Not implemented in v1 on purpose — see the plan's "out of scope".
"""
from __future__ import annotations


def fetch_merged_mrs(project: str, token: str):  # pragma: no cover
    raise NotImplementedError(
        "GitLab adapter is a v1 stub. Mirror loaders/github.py against the "
        "GitLab merge-requests API to implement."
    )

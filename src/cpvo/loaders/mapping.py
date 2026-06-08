"""Load the seat->author mapping (the join backbone) from YAML {seat_id: author_id}."""
from __future__ import annotations

import pandas as pd
import yaml


def load_mapping(path: str) -> pd.DataFrame:
    """Read a YAML mapping of seat_id -> author_id into a SeatAuthor frame."""
    with open(path) as fh:
        raw = yaml.safe_load(fh) or {}
    rows = [[seat, author] for seat, author in raw.items()]
    return pd.DataFrame(rows, columns=["seat_id", "author_id"])

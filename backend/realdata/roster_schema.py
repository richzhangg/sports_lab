"""
Roster data contract.

Any roster source — the pilot scraper, a mentor-supplied CSV, or a future full
scrape — must produce rows matching ROSTER_COLUMNS. `build.py` consumes only
this schema, so swapping in new roster data never touches the modeling code.

One row = one player-season.
"""
from __future__ import annotations
import pandas as pd

ROSTER_COLUMNS = [
    "season",          # int, the roster year (e.g. 2024 for the 2023-24 season)
    "player_name",     # str
    "gender",          # "M" | "W"
    "school",          # str, institution name
    "conference",      # str, e.g. "ACC", "Big Ten"
    "division",        # str, always "D1" here
    "hometown_raw",    # str, verbatim hometown as published ("City, ST" or intl.)
    "source_url",      # str, the exact page the row was read from
]

TEMPLATE_ROWS = [
    {
        "season": 2024, "player_name": "Jane Doe", "gender": "W",
        "school": "Example University", "conference": "ACC", "division": "D1",
        "hometown_raw": "Winston-Salem, NC", "source_url": "https://example.edu/roster",
    },
    {
        "season": 2024, "player_name": "John Roe", "gender": "M",
        "school": "Example University", "conference": "ACC", "division": "D1",
        "hometown_raw": "Munich, Germany", "source_url": "https://example.edu/roster",
    },
]


def validate(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in ROSTER_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"roster is missing required columns: {missing}")
    out = df[ROSTER_COLUMNS].copy()
    out["season"] = pd.to_numeric(out["season"], errors="coerce").astype("Int64")
    for c in ("player_name", "school", "hometown_raw"):
        out[c] = out[c].astype(str).str.strip()
    out["gender"] = (out["gender"].astype(str).str.upper().str[0]
                     .map({"M": "M", "W": "W", "F": "W"}))
    out = out[out["player_name"].str.len() > 0]
    out = out.drop_duplicates(subset=["season", "player_name", "school"])
    return out.reset_index(drop=True)


def write_template(path: str) -> None:
    pd.DataFrame(TEMPLATE_ROWS, columns=ROSTER_COLUMNS).to_csv(path, index=False)


if __name__ == "__main__":
    from .paths import ROSTER_TEMPLATE

    write_template(ROSTER_TEMPLATE)
    print(f"wrote {ROSTER_TEMPLATE}")

"""
Run the D1 tennis roster scrape and write:
  data/real/rosters_pilot.csv            one row per player-season
  data/real/roster_scrape_coverage.csv   method + count per school/sport/season

Schools are scraped concurrently (thread pool); every row records its source_url.
Rows are de-duplicated per (season, player_name, school).
"""
from __future__ import annotations
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FTimeout, as_completed

import pandas as pd

from ..paths import REAL, ROSTERS_PILOT
from ..roster_schema import ROSTER_COLUMNS, validate
from .schools import SCHOOLS, SPORTS, SEASONS
from .sidearm import fetch_roster

MAX_WORKERS = 12
DEADLINE_S = 420  # stop waiting on stragglers after this; write what finished


def _scrape_school(sc: dict) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    cov: list[dict] = []
    for sport in SPORTS:
        for year, label in SEASONS.items():
            try:
                r, method = fetch_roster(
                    host=sc["host"], sport_slug=sport, season_label=label,
                    season_year=year, school=sc["school"], conference=sc["conference"],
                )
            except Exception as e:  # noqa: BLE001
                r, method = [], f"error:{type(e).__name__}"
            cov.append({"school": sc["school"], "conference": sc["conference"],
                        "host": sc["host"], "sport": sport, "season": year,
                        "method": method, "n_players": len(r)})
            rows.extend(r)
            time.sleep(0.4)
    return rows, cov


def run(only: set[str] | None = None, merge: bool = False) -> None:
    """only: restrict to these school names. merge: keep existing rows for other schools."""
    targets = [s for s in SCHOOLS if not only or s["school"] in only]
    all_rows: list[dict] = []
    coverage: list[dict] = []
    done = 0
    ex = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    futs = {ex.submit(_scrape_school, sc): sc for sc in targets}
    try:
        for fut in as_completed(futs, timeout=DEADLINE_S):
            sc = futs[fut]
            rows, cov = fut.result()
            all_rows.extend(rows)
            coverage.extend(cov)
            done += 1
            got = sum(c["n_players"] for c in cov)
            print(f"  [{done:>3}/{len(targets)}] {sc['conference']:<14} {sc['school']:<22} {got} player-seasons")
    except FTimeout:
        stragglers = [futs[f]["school"] for f in futs if not f.done()]
        print(f"  deadline hit — {len(stragglers)} straggler(s) skipped: {stragglers}")
    ex.shutdown(wait=False, cancel_futures=True)

    df = (validate(pd.DataFrame(all_rows, columns=ROSTER_COLUMNS)) if all_rows
          else pd.DataFrame(columns=ROSTER_COLUMNS))
    cov = pd.DataFrame(coverage)
    cov_path = f"{REAL}/roster_scrape_coverage.csv"

    if merge and only:
        import os
        if os.path.exists(ROSTERS_PILOT):
            prev = pd.read_csv(ROSTERS_PILOT)
            df = pd.concat([prev[~prev["school"].isin(only)], df], ignore_index=True)
            df = validate(df)
        if os.path.exists(cov_path):
            pcov = pd.read_csv(cov_path)
            cov = pd.concat([pcov[~pcov["school"].isin(only)], cov], ignore_index=True)

    df.to_csv(ROSTERS_PILOT, index=False)
    cov.to_csv(cov_path, index=False)

    print("\n=== coverage ===")
    print(f"total player-seasons: {len(df)}")
    if len(df):
        print(df.groupby(["conference", "season"])["player_name"].count().unstack(fill_value=0).to_string())
        print(f"\nschools with ≥1 row: {df['school'].nunique()}/{len(SCHOOLS)}")
        print(f"school-sport-seasons with data: {(cov.n_players > 0).sum()}/{len(cov)}")
        print("methods:", cov.method.value_counts().to_dict())
        zero = sorted(set(c["school"] for c in coverage) - set(df["school"]))
        if zero:
            print(f"\nno data ({len(zero)}): {', '.join(zero)}")
    print(f"\nwrote {ROSTERS_PILOT}\nwrote {cov_path}")


if __name__ == "__main__":
    run()

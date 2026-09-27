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

MAX_WORKERS = 16
DEADLINE_S = 2400  # stop waiting on stragglers after this; write what finished
CURRENT_SEASON = max(SEASONS)  # the season fetched with no label -> the site's real "now"


def _drop_non_archival_seasons(df: pd.DataFrame) -> pd.DataFrame:
    """Some SIDEARM sites silently ignore the season suffix/query and just serve
    the live roster no matter what year you ask for. A real historical roster
    can't be near-identical to the CURRENT roster once a couple of years of
    eligibility turnover have passed — so if a school+sport's "season" name-set
    lands within 60% overlap of its current-season set at 3+ *different* older
    seasons, that program's site isn't actually archiving seasons: keep only its
    current-season row and drop the rest rather than record fabricated history.
    """
    if df.empty or "season" not in df.columns:
        return df
    sets = (df.groupby(["school", "gender", "season"])["player_name"]
            .apply(lambda s: frozenset(s)))
    flagged: dict[tuple, int] = {}
    for (school, gender, season), names in sets.items():
        gap = CURRENT_SEASON - season
        if gap < 2 or not names:
            continue
        key = (school, gender)
        base = sets.get((school, gender, CURRENT_SEASON))
        if not base:
            continue
        jac = len(base & names) / len(base | names)
        if jac > 0.6:
            flagged[key] = flagged.get(key, 0) + 1
    non_archival = {k for k, v in flagged.items() if v >= 3}
    if non_archival:
        drop = df.apply(
            lambda r: (r["school"], r["gender"]) in non_archival and r["season"] != CURRENT_SEASON,
            axis=1,
        )
        print(f"  {len(non_archival)} school/sport site(s) don't actually vary by season "
              f"(serve the current roster regardless) — dropping {int(drop.sum())} "
              "fabricated-looking historical rows, keeping only their current season.")
        df = df[~drop].reset_index(drop=True)
    return df


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
    df = _drop_non_archival_seasons(df)
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

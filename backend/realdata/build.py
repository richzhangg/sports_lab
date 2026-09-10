"""
Assemble the final county-year research panel from the component tables:

    county_master  (universe)       geo.py       — no key
    census_acs     (predictors)     census_acs.py — FREE Census API key
    tennis_courts  (predictor)      osm_tennis.py — no key
    rosters_pilot  (outcome)        scrape/       — no key

Output: data/real/real_dataset.csv  (+ real_dataset_provenance.json)

Panel definition
----------------
Rows: every U.S. county with ACS data  ×  every roster season scraped.
Outcome d1_players: number of scraped ACC+Big-Ten tennis players whose
hometown geocodes to that county that season (0 where none).
Predictors for roster season Y use the ACS 5-year vintage (Y-1), clamped to
the range of vintages actually downloaded. Tennis-court counts are a single
current OSM snapshot applied to every season.

LIMITATION (documented, not hidden): the pilot roster covers only ACC + Big Ten
programs, so d1_players is representation *within those conferences*, not all of
Division I. Swap in a full roster CSV (same schema) to lift this.
"""
from __future__ import annotations
import json

import pandas as pd

from .paths import (CENSUS_ACS, COUNTY_MASTER, REAL_DATASET, ROSTERS_GEOCODED,
                    ROSTERS_PILOT, TENNIS_COURTS)
from .geocode import geocode_series

PROV = REAL_DATASET.replace(".csv", "_provenance.json")


def build() -> pd.DataFrame:
    import os

    for p in (COUNTY_MASTER, CENSUS_ACS, ROSTERS_PILOT):
        if not os.path.exists(p):
            raise FileNotFoundError(
                f"missing {os.path.basename(p)} — run the pipeline steps first "
                f"(see realdata/README or `python -m realdata.pipeline`)"
            )

    counties = pd.read_csv(COUNTY_MASTER, dtype={"county_fips": str})
    acs = pd.read_csv(CENSUS_ACS, dtype={"county_fips": str})
    rosters = pd.read_csv(ROSTERS_PILOT)

    acs_years = sorted(acs["year"].unique())
    roster_years = sorted(int(y) for y in rosters["season"].dropna().unique())

    # --- geocode hometowns -> counties -------------------------------------
    gc = geocode_series(rosters["hometown_raw"])
    rosters = pd.concat(
        [rosters.reset_index(drop=True),
         gc[["county_fips", "county_name", "state", "match"]].rename(columns={"state": "geo_state"})],
        axis=1,
    )
    matched = rosters.dropna(subset=["county_fips"])
    match_stats = rosters["match"].value_counts().to_dict()
    # one row per player-season with its resolved county — powers player search
    # and the interactive map without re-geocoding at request time.
    rosters.drop(columns=["source_url", "division"], errors="ignore").to_csv(
        ROSTERS_GEOCODED, index=False
    )

    counts = (matched.groupby(["county_fips", "season"]).size()
              .reset_index(name="d1_players").rename(columns={"season": "year"}))

    # --- tennis courts (static snapshot) ---------------------------------
    if os.path.exists(TENNIS_COURTS):
        courts = pd.read_csv(TENNIS_COURTS, dtype={"county_fips": str})
    else:
        courts = pd.DataFrame(columns=["county_fips", "tennis_courts"])

    # --- assemble panel: counties x roster_years ------------------------
    frames = []
    for ry in roster_years:
        vintage = min(max(ry - 1, acs_years[0]), acs_years[-1])
        a = acs[acs["year"] == vintage].drop(columns=["year"])
        panel = counties.merge(a, on="county_fips", how="inner")
        panel["year"] = ry
        panel["acs_vintage"] = vintage
        panel = panel.merge(courts, on="county_fips", how="left")
        panel["tennis_courts"] = panel["tennis_courts"].fillna(0)
        panel = panel.merge(counts[counts.year == ry].drop(columns=["year"]),
                            on="county_fips", how="left")
        panel["d1_players"] = panel["d1_players"].fillna(0).astype(int)
        frames.append(panel)

    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["population", "median_income", "poverty_rate", "pct_bachelors"])
    df = df[df["population"] > 0]

    df["tennis_courts_per_100k"] = df["tennis_courts"] / df["population"] * 100_000
    df["d1_rate_per_100k"] = df["d1_players"] / df["population"] * 100_000

    # Winsorize heavy-tailed predictors at the 99th percentile. Micro-counties
    # (Loving County, TX: pop 54) otherwise produce per-capita rates that blow up
    # any standardized model. Capping, not dropping, keeps every county in.
    for _c in ("tennis_courts_per_100k", "pop_density"):
        _cap = float(df[_c].quantile(0.99))
        df[_c] = df[_c].clip(upper=_cap)

    df["community_id"] = df["county_fips"]
    df["community_name"] = df["county_name"].str.replace(r" County$", "", regex=True) + ", " + df["state"]

    cols = ["community_id", "community_name", "state", "year", "population",
            "median_income", "poverty_rate", "pct_bachelors",
            "tennis_courts_per_100k", "pop_density", "d1_players", "d1_rate_per_100k",
            "acs_vintage"]
    df = df[cols].sort_values(["year", "community_id"]).reset_index(drop=True)
    df.to_csv(REAL_DATASET, index=False)

    n_schools = int(rosters["school"].nunique())
    confs = sorted(rosters["conference"].dropna().unique().tolist())
    prov = {
        "built_at": pd.Timestamp.utcnow().isoformat(),
        "n_rows": len(df),
        "n_counties": int(df["community_id"].nunique()),
        "roster_years": roster_years,
        "acs_vintages_used": sorted(df["acs_vintage"].unique().tolist()),
        "acs_vintages_available": acs_years,
        "roster_source": (f"Scrape of public team roster pages — {n_schools} NCAA Division I "
                          f"men's & women's tennis programs across {len(confs)} conferences"),
        "roster_conferences": confs,
        "roster_schools": n_schools,
        "roster_player_seasons": int(len(rosters)),
        "roster_geocode_matches": match_stats,
        "roster_geocoded_ok": int(len(matched)),
        "roster_international_or_unresolved": int(len(rosters) - len(matched)),
        "total_d1_players_placed": int(df["d1_players"].sum()),
        "counties_with_players": int((df.groupby("community_id")["d1_players"].sum() > 0).sum()),
        "tennis_courts_total_osm": int(courts["tennis_courts"].sum()) if len(courts) else 0,
        "sources": {
            "socioeconomic": ("U.S. Census Bureau, American Community Survey 5-year — "
                              + ("ACS API" if os.environ.get("CENSUS_API_KEY", "").strip()
                                 else "public Summary File bulk files (www2.census.gov)")),
            "geography": "U.S. Census Bureau 2023 Gazetteer + TIGER/Line cb_2023 counties",
            "tennis_access": "OpenStreetMap via Overpass API (sport=tennis), © OSM contributors, ODbL",
            "rosters": f"Public NCAA Division I tennis team roster pages ({n_schools} programs)",
        },
        "limitations": [
            f"Outcome = NCAA Division I tennis players on the {n_schools} programs the scraper "
            "could read (of ~300 D1 programs); it undercounts true D1 representation for "
            "counties whose players attend the ~30 schools not covered.",
            "Predictors use ACS 5-year vintage (roster_year - 1); tennis courts are "
            "a single current OSM snapshot.",
            f"{int(len(rosters) - len(matched))} of {len(rosters)} player-seasons have an "
            "international or unresolved hometown and are not placed in a U.S. county.",
        ],
    }
    def _plain(o):
        if hasattr(o, "item"):
            return o.item()
        raise TypeError(o)

    with open(PROV, "w") as fh:
        json.dump(prov, fh, indent=2, default=_plain)

    print(f"wrote {REAL_DATASET}  ({len(df)} county-years, "
          f"{df['community_id'].nunique()} counties, years {roster_years})")
    print(f"  D1 players placed into counties: {int(df['d1_players'].sum())}")
    print(f"  geocode match breakdown: {match_stats}")
    print(f"wrote {PROV}")
    return df


if __name__ == "__main__":
    build()

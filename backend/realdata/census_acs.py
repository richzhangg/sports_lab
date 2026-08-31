"""
American Community Survey (ACS 5-year) socioeconomic predictors, per county-year.

Two fetch paths, same output:
  * with a CENSUS_API_KEY  -> the ACS API (any vintage 2019-2023)
  * without a key          -> census_acs_bulk.py, the public Summary File flat
                              files (keyless; vintages 2022 & 2023)

Get a free key at https://api.census.gov/data/key_signup.html (optional) and put
it in backend/.env as CENSUS_API_KEY=xxxxx.

Output: data/real/census_acs_counties.csv with columns
  county_fips, year, population, median_income, poverty_rate,
  pct_bachelors, pop_density
"""
from __future__ import annotations

import pandas as pd
import requests

from .paths import CENSUS_ACS, CENSUS_API_KEY, COUNTY_MASTER

# variable -> ACS table code
VARS = {
    "median_income": "B19013_001E",
    "pop_total": "B01003_001E",
    "pov_universe": "B17001_001E",
    "pov_below": "B17001_002E",
    "edu_total": "B15003_001E",
    "edu_bach": "B15003_022E",
    "edu_mast": "B15003_023E",
    "edu_prof": "B15003_024E",
    "edu_doct": "B15003_025E",
}

DEFAULT_YEARS = [2019, 2020, 2021, 2022, 2023]


class MissingCensusKey(RuntimeError):
    pass


def _fetch_year(year: int, key: str) -> pd.DataFrame:
    get = ",".join(["NAME", *VARS.values()])
    url = f"https://api.census.gov/data/{year}/acs/acs5"
    r = requests.get(
        url,
        params={"get": get, "for": "county:*", "key": key},
        timeout=120,
        headers={"User-Agent": "sports-opportunity-lab/0.1"},
    )
    if r.status_code == 404:
        raise FileNotFoundError(year)
    r.raise_for_status()
    rows = r.json()
    df = pd.DataFrame(rows[1:], columns=rows[0])
    inv = {v: k for k, v in VARS.items()}
    df = df.rename(columns=inv)
    for c in VARS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["county_fips"] = df["state"].str.zfill(2) + df["county"].str.zfill(3)
    df["year"] = year
    df["population"] = df["pop_total"]
    df["poverty_rate"] = (df["pov_below"] / df["pov_universe"] * 100).where(df["pov_universe"] > 0)
    df["pct_bachelors"] = (
        (df[["edu_bach", "edu_mast", "edu_prof", "edu_doct"]].sum(axis=1) / df["edu_total"] * 100)
        .where(df["edu_total"] > 0)
    )
    # ACS uses large negative sentinels for "not available"
    df.loc[df["median_income"] < 0, "median_income"] = pd.NA
    return df[["county_fips", "year", "population", "median_income", "poverty_rate", "pct_bachelors"]]


def build(years: list[int] | None = None, force: bool = False) -> pd.DataFrame:
    import os

    if not force and os.path.exists(CENSUS_ACS):
        print("  ACS table already built (use --force to rebuild)")
        return pd.read_csv(CENSUS_ACS, dtype={"county_fips": str})

    if not CENSUS_API_KEY:
        print("  no CENSUS_API_KEY set — using the keyless Summary File bulk loader")
        from . import census_acs_bulk

        return census_acs_bulk.build(years=years, force=force)

    years = years or DEFAULT_YEARS
    frames = []
    for y in years:
        try:
            print(f"  fetching ACS 5-year {y} …")
            frames.append(_fetch_year(y, CENSUS_API_KEY))
        except FileNotFoundError:
            print(f"    ACS5 {y} not published yet — skipping")
    if not frames:
        raise RuntimeError("no ACS years could be fetched")

    acs = pd.concat(frames, ignore_index=True)
    land = pd.read_csv(COUNTY_MASTER, dtype={"county_fips": str})[["county_fips", "land_area_sqmi"]]
    acs = acs.merge(land, on="county_fips", how="left")
    acs["pop_density"] = acs["population"] / acs["land_area_sqmi"].replace(0, pd.NA)
    acs = acs.drop(columns=["land_area_sqmi"])
    acs.to_csv(CENSUS_ACS, index=False)
    print(f"  wrote {CENSUS_ACS}  ({len(acs)} county-years, {acs['year'].nunique()} years)")
    return acs


if __name__ == "__main__":
    import sys

    build(force="--force" in sys.argv)

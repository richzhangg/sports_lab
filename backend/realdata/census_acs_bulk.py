"""
Keyless ACS 5-year loader — reads the Census Bureau's public **table-based
Summary File** flat files instead of the API. No API key, no registration.

Source: https://www2.census.gov/programs-surveys/acs/summary_file/{year}/table-based-SF/
Format: one pipe-delimited `.dat` per detail table, whole nation, columns
        GEO_ID | {TABLE}_E001 | {TABLE}_M001 | {TABLE}_E002 | ...
County rows have GEO_ID = "0500000US" + 5-digit county FIPS.

Only 2022 and 2023 vintages are supported here (earlier years use the messy
legacy sequence-based format). That is sufficient for the pilot, whose roster
years are 2023-2026 and which uses ACS vintage = roster_year - 1 clamped to the
available range.

Produces the SAME output as census_acs.py:
  data/real/census_acs_counties.csv
  county_fips, year, population, median_income, poverty_rate, pct_bachelors, pop_density

~235 MB per vintage is downloaded once and cached in data/cache/.
"""
from __future__ import annotations
import os

import pandas as pd
import requests

from .paths import CACHE, CENSUS_ACS, COUNTY_MASTER

BASE = "https://www2.census.gov/programs-surveys/acs/summary_file/{y}/table-based-SF/data/5YRData/acsdt5y{y}-{t}.dat"
SUPPORTED_YEARS = [2022, 2023]

# table -> estimate cells we need (E = estimate column suffix)
NEEDED = {
    "b19013": ["B19013_E001"],                                   # median household income
    "b01003": ["B01003_E001"],                                   # total population
    "b17001": ["B17001_E001", "B17001_E002"],                    # poverty universe / below poverty
    "b15003": ["B15003_E001", "B15003_E022", "B15003_E023",      # 25+ total / bachelor / master
               "B15003_E024", "B15003_E025"],                    #   / professional / doctorate
}
COUNTY_PREFIX = "0500000US"
# ACS "not available" sentinels
_BAD = {-666666666, -999999999, -888888888, -222222222, -333333333, -555555555}


def _download(year: int, table: str) -> str:
    path = os.path.join(CACHE, f"acsdt5y{year}-{table}.dat")
    if os.path.exists(path) and os.path.getsize(path) > 10_000:
        return path
    url = BASE.format(y=year, t=table)
    print(f"    downloading {url.rsplit('/', 1)[-1]} (~one-time)")
    with requests.get(url, stream=True, timeout=600,
                      headers={"User-Agent": "sports-opportunity-lab/0.1"}) as r:
        r.raise_for_status()
        tmp = path + ".part"
        with open(tmp, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
        os.replace(tmp, path)
    return path


def _read_table(year: int, table: str) -> pd.DataFrame:
    path = _download(year, table)
    want = set(NEEDED[table]) | {"GEO_ID"}
    df = pd.read_csv(path, sep="|", dtype=str, usecols=lambda c: c in want)
    df = df[df["GEO_ID"].str.startswith(COUNTY_PREFIX)]
    df["county_fips"] = df["GEO_ID"].str.slice(len(COUNTY_PREFIX)).str.zfill(5)
    for col in NEEDED[table]:
        v = pd.to_numeric(df[col], errors="coerce")
        v = v.where(~v.isin(_BAD))
        df[col] = v
    return df.drop(columns=["GEO_ID"]).set_index("county_fips")


def _build_year(year: int) -> pd.DataFrame:
    parts = [_read_table(year, t) for t in NEEDED]
    m = pd.concat(parts, axis=1).reset_index()
    m["year"] = year
    m["population"] = m["B01003_E001"]
    m["median_income"] = m["B19013_E001"].where(m["B19013_E001"] > 0)
    m["poverty_rate"] = (m["B17001_E002"] / m["B17001_E001"] * 100).where(m["B17001_E001"] > 0)
    edu = m[["B15003_E022", "B15003_E023", "B15003_E024", "B15003_E025"]].sum(axis=1)
    m["pct_bachelors"] = (edu / m["B15003_E001"] * 100).where(m["B15003_E001"] > 0)
    return m[["county_fips", "year", "population", "median_income", "poverty_rate", "pct_bachelors"]]


def build(years: list[int] | None = None, force: bool = False) -> pd.DataFrame:
    if not force and os.path.exists(CENSUS_ACS):
        print("  ACS table already built (use --force to rebuild)")
        return pd.read_csv(CENSUS_ACS, dtype={"county_fips": str})

    years = [y for y in (years or SUPPORTED_YEARS) if y in SUPPORTED_YEARS]
    if not years:
        years = SUPPORTED_YEARS
    print(f"  keyless ACS bulk loader — vintages {years}")

    acs = pd.concat([_build_year(y) for y in years], ignore_index=True)
    land = pd.read_csv(COUNTY_MASTER, dtype={"county_fips": str})[["county_fips", "land_area_sqmi"]]
    acs = acs.merge(land, on="county_fips", how="left")
    acs["pop_density"] = acs["population"] / acs["land_area_sqmi"].replace(0, pd.NA)
    acs = acs.drop(columns=["land_area_sqmi"])
    acs.to_csv(CENSUS_ACS, index=False)
    print(f"  wrote {CENSUS_ACS}  ({len(acs)} county-years, vintages {years})")
    return acs


if __name__ == "__main__":
    import sys

    build(force="--force" in sys.argv)

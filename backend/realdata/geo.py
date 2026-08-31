"""
Geographic backbone (no API key required).

Builds two tables from official U.S. Census static files:

  county_master.csv     one row per U.S. county:
                        county_fips, county_name, state, land_area_sqmi, lat, lon
  city_county_xwalk.csv one row per Census "place":
                        city_key, city_name, state, county_fips, county_name
                        (place point spatially joined to the county polygon)

Sources (downloaded once into data/cache/, ODbL/public domain):
  - 2023 Gazetteer county file
  - 2023 Gazetteer place file
  - cb_2023_us_county_500k TIGER/Line generalized county shapefile
"""
from __future__ import annotations
import io
import zipfile

import pandas as pd
import requests

from .paths import CACHE, COUNTY_MASTER, CITY_COUNTY_XWALK
import os

GAZ_BASE = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer"
GAZ_COUNTY = f"{GAZ_BASE}/2023_Gaz_counties_national.zip"
GAZ_PLACE = f"{GAZ_BASE}/2023_Gaz_place_national.zip"
GAZ_COUSUB = f"{GAZ_BASE}/2023_Gaz_cousubs_national.zip"  # townships / MCDs (New England etc.)
TIGER_COUNTY = "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip"

# NYC boroughs and other populated areas that are not Census "places"
MANUAL_XWALK = [
    # city_key, city_name, state, county_fips, county_name
    ("new york", "New York", "NY", "36061", "New York"),
    ("manhattan", "Manhattan", "NY", "36061", "New York"),
    ("brooklyn", "Brooklyn", "NY", "36047", "Kings"),
    ("queens", "Queens", "NY", "36081", "Queens"),
    ("bronx", "Bronx", "NY", "36005", "Bronx"),
    ("the bronx", "The Bronx", "NY", "36005", "Bronx"),
    ("staten island", "Staten Island", "NY", "36085", "Richmond"),
]

STATE_FIPS_TO_USPS = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT",
    "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL",
    "18": "IN", "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD",
    "25": "MA", "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT", "31": "NE",
    "32": "NV", "33": "NH", "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
    "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA", "54": "WV",
    "55": "WI", "56": "WY", "72": "PR",
}


def _download(url: str) -> bytes:
    fname = os.path.join(CACHE, url.rsplit("/", 1)[-1])
    if os.path.exists(fname) and os.path.getsize(fname) > 0:
        with open(fname, "rb") as fh:
            return fh.read()
    print(f"  downloading {url}")
    r = requests.get(url, timeout=120, headers={"User-Agent": "sports-opportunity-lab/0.1"})
    r.raise_for_status()
    with open(fname, "wb") as fh:
        fh.write(r.content)
    return r.content


def normalize_city(name: str) -> str:
    s = (name or "").strip().lower()
    for a, b in (("saint ", "st "), ("st. ", "st "), ("ft. ", "ft "), ("fort ", "ft "), ("mount ", "mt ")):
        s = s.replace(a, b)
    return " ".join(s.split())


def _gaz_counties() -> pd.DataFrame:
    raw = _download(GAZ_COUNTY)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        with z.open(z.namelist()[0]) as fh:
            df = pd.read_csv(fh, sep="\t", dtype={"GEOID": str}, encoding="latin-1")
    df.columns = [c.strip() for c in df.columns]
    df["county_fips"] = df["GEOID"].str.zfill(5)
    df["state"] = df["USPS"].str.upper()
    df["county_name"] = df["NAME"].str.strip()
    df["land_area_sqmi"] = pd.to_numeric(df["ALAND_SQMI"], errors="coerce")
    df["lat"] = pd.to_numeric(df["INTPTLAT"], errors="coerce")
    df["lon"] = pd.to_numeric(df["INTPTLONG"], errors="coerce")
    return df[["county_fips", "county_name", "state", "land_area_sqmi", "lat", "lon"]]


_LSAD_RE = (r"\s+(city|town|township|village|borough|municipality|CDP|"
            r"comunidad|zona urbana|\(balance\))$")


def _gaz_named(url: str) -> pd.DataFrame:
    raw = _download(url)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        with z.open(z.namelist()[0]) as fh:
            df = pd.read_csv(fh, sep="\t", dtype={"GEOID": str}, encoding="latin-1")
    df.columns = [c.strip() for c in df.columns]
    df["state"] = df["USPS"].str.upper()
    df["city_name"] = df["NAME"].str.replace(_LSAD_RE, "", regex=True).str.strip()
    df["lat"] = pd.to_numeric(df["INTPTLAT"], errors="coerce")
    df["lon"] = pd.to_numeric(df["INTPTLONG"], errors="coerce")
    return df[["city_name", "state", "lat", "lon"]].dropna(subset=["lat", "lon"])


def _gaz_places() -> pd.DataFrame:
    # places first (preferred), then county subdivisions to cover township states
    return pd.concat([_gaz_named(GAZ_PLACE), _gaz_named(GAZ_COUSUB)], ignore_index=True)


def build(force: bool = False) -> None:
    import geopandas as gpd

    if not force and os.path.exists(COUNTY_MASTER) and os.path.exists(CITY_COUNTY_XWALK):
        print("  geo tables already built (use --force to rebuild)")
        return

    counties = _gaz_counties()
    counties.to_csv(COUNTY_MASTER, index=False)
    print(f"  wrote {COUNTY_MASTER}  ({len(counties)} counties)")

    places = _gaz_places()

    raw = _download(TIGER_COUNTY)
    cache_shp = os.path.join(CACHE, "cb_2023_us_county_500k")
    if not os.path.isdir(cache_shp):
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            z.extractall(cache_shp)
    shp = next(f for f in os.listdir(cache_shp) if f.endswith(".shp"))
    cgdf = gpd.read_file(os.path.join(cache_shp, shp))[["GEOID", "NAME", "geometry"]].to_crs(4326)
    cgdf = cgdf.rename(columns={"GEOID": "county_fips", "NAME": "county_name"})

    pgdf = gpd.GeoDataFrame(
        places, geometry=gpd.points_from_xy(places.lon, places.lat), crs=4326
    )
    joined = gpd.sjoin(pgdf, cgdf, how="left", predicate="within")
    unmatched = joined[joined["county_fips"].isna()].drop(columns=["index_right", "county_fips", "county_name"])
    if len(unmatched):
        proj = 5070  # NAD83 / CONUS Albers — planar, for correct nearest distances
        near = gpd.sjoin_nearest(
            gpd.GeoDataFrame(unmatched, geometry=unmatched.geometry, crs=4326).to_crs(proj),
            cgdf.to_crs(proj), how="left",
        ).to_crs(4326)
        joined = pd.concat([joined[joined["county_fips"].notna()], near], ignore_index=True)
    joined = joined.dropna(subset=["county_fips"])
    joined["city_key"] = joined["city_name"].map(normalize_city)

    manual = pd.DataFrame(MANUAL_XWALK, columns=["city_key", "city_name", "state", "county_fips", "county_name"])
    xwalk = (
        pd.concat([manual, joined[["city_key", "city_name", "state", "county_fips", "county_name"]]],
                  ignore_index=True)
        .drop_duplicates(subset=["city_key", "state"])          # manual rows win (listed first)
        .sort_values(["state", "city_key"])
    )
    xwalk.to_csv(CITY_COUNTY_XWALK, index=False)
    print(f"  wrote {CITY_COUNTY_XWALK}  ({len(xwalk)} city→county rows)")


if __name__ == "__main__":
    import sys

    build(force="--force" in sys.argv)

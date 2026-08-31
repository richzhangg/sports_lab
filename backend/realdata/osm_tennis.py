"""
Tennis-facility access proxy from OpenStreetMap (no API key; data © OSM, ODbL).

For each U.S. state we ask the Overpass API for every feature tagged
sport=tennis (courts, clubs, complexes), take its centroid, then spatially
join the points to county polygons and count per county.

Output: data/real/tennis_courts_by_county.csv
  county_fips, tennis_courts
Counties with no OSM tennis feature get 0 in the final panel build.
"""
from __future__ import annotations
import os
import time

import pandas as pd
import requests

from .geo import STATE_FIPS_TO_USPS
from .paths import CACHE, TENNIS_COURTS

OVERPASS = "https://overpass-api.de/api/interpreter"


def _query_state(usps: str, tries: int = 4) -> list[dict]:
    q = f"""
    [out:json][timeout:180];
    area["boundary"="administrative"]["admin_level"="4"]["ISO3166-2"="US-{usps}"]->.s;
    nwr["sport"~"tennis"](area.s);
    out center;
    """
    for attempt in range(tries):
        try:
            r = requests.post(OVERPASS, data={"data": q}, timeout=200,
                              headers={"User-Agent": "sports-opportunity-lab/0.1"})
            if r.status_code in (429, 504):
                time.sleep(20 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json().get("elements", [])
        except requests.RequestException:
            time.sleep(15 * (attempt + 1))
    print(f"    {usps}: giving up after {tries} tries")
    return []


def _points(elements: list[dict]) -> pd.DataFrame:
    recs = []
    for e in elements:
        lat = e.get("lat") or (e.get("center") or {}).get("lat")
        lon = e.get("lon") or (e.get("center") or {}).get("lon")
        if lat is not None and lon is not None:
            recs.append({"lat": lat, "lon": lon})
    return pd.DataFrame(recs)


def _query_us(tries: int = 3) -> list[dict]:
    q = ('[out:json][timeout:270];area["ISO3166-1"="US"][admin_level=2]->.us;'
         'nwr["sport"="tennis"](area.us);out center;')
    for attempt in range(tries):
        try:
            r = requests.post(OVERPASS, data={"data": q}, timeout=300,
                              headers={"User-Agent": "sports-opportunity-lab/0.1"})
            if r.status_code in (429, 504):
                time.sleep(30 * (attempt + 1)); continue
            r.raise_for_status()
            return r.json().get("elements", [])
        except requests.RequestException:
            time.sleep(20 * (attempt + 1))
    return []


def build(force: bool = False) -> pd.DataFrame:
    if not force and os.path.exists(TENNIS_COURTS):
        print("  tennis table already built (use --force to rebuild)")
        return pd.read_csv(TENNIS_COURTS, dtype={"county_fips": str})

    import geopandas as gpd

    raw_cache = os.path.join(CACHE, "osm_tennis_points.csv")
    us_json = os.path.join(CACHE, "osm_us_tennis.json")
    if os.path.exists(raw_cache) and not force:
        pts = pd.read_csv(raw_cache)
    elif os.path.exists(us_json) and not force:
        import json
        pts = _points(json.load(open(us_json)).get("elements", []))
        pts.to_csv(raw_cache, index=False)
    else:
        els = _query_us()
        if els:
            pts = _points(els)
            pts.to_csv(raw_cache, index=False)
        else:
            all_pts = []
            for usps in sorted(set(STATE_FIPS_TO_USPS.values())):
                if usps == "PR":
                    continue
                p = _points(_query_state(usps))
                print(f"    {usps}: {len(p)} tennis features")
                all_pts.append(p)
                time.sleep(3)
            pts = pd.concat(all_pts, ignore_index=True)
            pts.to_csv(raw_cache, index=False)

    cache_shp = os.path.join(CACHE, "cb_2023_us_county_500k")
    shp = next(f for f in os.listdir(cache_shp) if f.endswith(".shp"))
    cgdf = gpd.read_file(os.path.join(cache_shp, shp))[["GEOID", "geometry"]].to_crs(4326)
    cgdf = cgdf.rename(columns={"GEOID": "county_fips"})

    pgdf = gpd.GeoDataFrame(pts, geometry=gpd.points_from_xy(pts.lon, pts.lat), crs=4326)
    joined = gpd.sjoin(pgdf, cgdf, how="inner", predicate="within")
    counts = (
        joined.groupby("county_fips").size().reset_index(name="tennis_courts").sort_values("tennis_courts", ascending=False)
    )
    counts.to_csv(TENNIS_COURTS, index=False)
    print(f"  wrote {TENNIS_COURTS}  ({len(counts)} counties with ≥1 facility, "
          f"{int(counts['tennis_courts'].sum())} facilities total)")
    return counts


if __name__ == "__main__":
    import sys

    build(force="--force" in sys.argv)

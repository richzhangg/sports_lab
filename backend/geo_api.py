"""
Lightweight geographic payload for the landing-page visualization.

  - county centroids (lat/lon) + the D1 player count for the most recent
    roster year, from the built research dataset
  - a heavily simplified US state-outline GeoJSON (dissolved from the cached
    TIGER county shapefile) so the client can draw a recognisable US map with
    no external tile/atlas dependency

Cached to data/real/geo_payload.json after the first build.
"""
from __future__ import annotations

import json
import os

import pandas as pd

from realdata.paths import CACHE, REAL

GEO_JSON = os.path.join(REAL, "geo_payload.json")
COUNTY_MASTER = os.path.join(REAL, "county_master.csv")
REAL_DATASET = os.path.join(REAL, "real_dataset.csv")

# contiguous-US state FIPS to keep the map tidy (drop AK/HI/PR territories)
_DROP_STATE_FIPS = {"02", "15", "60", "66", "69", "72", "78"}


def _build_states_outline() -> dict:
    import geopandas as gpd

    shp = os.path.join(CACHE, "cb_2023_us_county_500k", "cb_2023_us_county_500k.shp")
    if not os.path.exists(shp):
        shp = os.path.join(CACHE, "cb_2023_us_county_500k.shp")
    gdf = gpd.read_file(shp)[["STATEFP", "geometry"]]
    gdf = gdf[~gdf["STATEFP"].isin(_DROP_STATE_FIPS)]
    states = gdf.dissolve(by="STATEFP", as_index=False)
    states["geometry"] = states.geometry.simplify(0.02, preserve_topology=True)
    states = states.to_crs(4326)
    return json.loads(states.to_json())


def _available_years() -> list[int]:
    if not os.path.exists(REAL_DATASET):
        return []
    return sorted(int(y) for y in pd.read_csv(REAL_DATASET, usecols=["year"])["year"].unique())


def _payload_for_year(year: int | None) -> dict:
    cm = pd.read_csv(COUNTY_MASTER, dtype={"county_fips": str})
    years = _available_years()

    if years:
        df = pd.read_csv(REAL_DATASET, dtype={"community_id": str})
        year = year if year in years else max(years)
        d = df[df["year"] == year][["community_id", "d1_players"]]
        merged = cm.merge(d, left_on="county_fips", right_on="community_id", how="left")
        merged["d1_players"] = merged["d1_players"].fillna(0).astype(int)
    else:
        merged = cm.copy()
        merged["d1_players"] = 0
        year = None

    merged = merged[~merged["county_fips"].str.slice(0, 2).isin(_DROP_STATE_FIPS)]
    merged = merged.dropna(subset=["lat", "lon"])
    return {
        "year": year,
        "years": years,
        "max_players": int(merged["d1_players"].max()) if len(merged) else 0,
        "total_players": int(merged["d1_players"].sum()),
        "counties": [
            {
                "fips": r.county_fips,
                "name": f"{r.county_name}, {r.state}",
                "lat": round(float(r.lat), 4),
                "lon": round(float(r.lon), 4),
                "players": int(r.d1_players),
            }
            for r in merged.itertuples()
        ],
    }


def build(force: bool = False, year: int | None = None) -> dict:
    """Default (latest) year is cached to geo_payload.json; other years compute fresh."""
    years = _available_years()
    latest = max(years) if years else None
    if year is None or year == latest:
        if not force and os.path.exists(GEO_JSON):
            with open(GEO_JSON) as fh:
                payload = json.load(fh)
            payload.setdefault("years", years)  # backfill for older cache files
            return payload
        payload = _payload_for_year(latest)
        with open(GEO_JSON, "w") as fh:
            json.dump(payload, fh)
        return payload
    return _payload_for_year(year)


if __name__ == "__main__":
    p = build(force=True)
    print(f"counties={len(p['counties'])}  year={p['year']}  years={p['years']}  max={p['max_players']}")

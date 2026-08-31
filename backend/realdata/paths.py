"""Shared filesystem locations for the real-data pipeline."""
import os

try:  # load backend/.env if present
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except Exception:
    pass

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BACKEND, "data")
CACHE = os.path.join(DATA, "cache")          # downloaded source files (gitignored)
REAL = os.path.join(DATA, "real")            # built research tables

for _d in (CACHE, REAL):
    os.makedirs(_d, exist_ok=True)

# built artefacts
COUNTY_MASTER = os.path.join(REAL, "county_master.csv")        # FIPS, name, state, land area
CITY_COUNTY_XWALK = os.path.join(REAL, "city_county_xwalk.csv")  # city/state -> county FIPS
CENSUS_ACS = os.path.join(REAL, "census_acs_counties.csv")     # ACS predictors per county-year
TENNIS_COURTS = os.path.join(REAL, "tennis_courts_by_county.csv")
ROSTERS_PILOT = os.path.join(REAL, "rosters_pilot.csv")        # scraped ACC+Big Ten rosters
ROSTER_TEMPLATE = os.path.join(REAL, "roster_import_template.csv")
REAL_DATASET = os.path.join(REAL, "real_dataset.csv")          # final county-year panel

CENSUS_API_KEY = os.environ.get("CENSUS_API_KEY", "").strip()

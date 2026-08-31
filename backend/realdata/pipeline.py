"""
One-command build of the real research dataset.

    cd backend && ./venv/bin/python -m realdata.pipeline [--force] [--skip-scrape] [--skip-osm]

Steps (each is independently cached):
    1. geo         Census Gazetteer + TIGER  -> county_master, city_county_xwalk   (no key)
    2. census_acs  ACS 5-year per county via the public Summary File bulk files     (no key)
    3. osm_tennis  OpenStreetMap tennis facilities per county                        (no key, slow)
    4. rosters     pilot ACC + Big Ten tennis roster scrape                          (no key)
    5. build       assemble county-year panel -> data/real/real_dataset.csv

No API keys or accounts are needed. Step 2 downloads ~235 MB per ACS vintage
(2022 & 2023) once. If you set CENSUS_API_KEY in backend/.env it uses the ACS API
instead (smaller download, more vintages) but this is entirely optional.
"""
from __future__ import annotations
import sys


def main(argv: list[str]) -> None:
    force = "--force" in argv
    from . import geo, census_acs, osm_tennis, build
    from .roster_schema import write_template
    from .paths import ROSTER_TEMPLATE

    print("[1/5] geographic backbone")
    geo.build(force=force)

    print("[2/5] Census ACS predictors (keyless bulk loader unless CENSUS_API_KEY is set)")
    census_acs.build(force=force)

    if "--skip-osm" not in argv:
        print("[3/5] OpenStreetMap tennis facilities (this can take several minutes)")
        osm_tennis.build(force=force)
    else:
        print("[3/5] skipped (--skip-osm)")

    if "--skip-scrape" not in argv:
        print("[4/5] pilot roster scrape (ACC + Big Ten)")
        from .scrape.run_pilot import run as run_scrape
        run_scrape()
    else:
        print("[4/5] skipped (--skip-scrape)")

    write_template(ROSTER_TEMPLATE)
    print(f"      roster import template -> {ROSTER_TEMPLATE}")

    print("[5/5] assemble panel")
    try:
        build.build()
        print("\n✓ real_dataset.csv built. Restart the API with SPORTS_LAB_SOURCE=real "
              "(or just restart — real data is used automatically when present).")
    except FileNotFoundError as e:
        print(f"\n  ✗ cannot assemble yet: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])

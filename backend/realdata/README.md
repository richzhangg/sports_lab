# Real research dataset pipeline

Builds `data/real/real_dataset.csv` — a **U.S. county × roster-season panel** —
from public sources, behind the same `DataSource` interface the demo data uses.
The modeling code and API never change.

## Quick start

```bash
cd backend
./venv/bin/python -m realdata.pipeline
```

No keys or accounts. Then restart the API — real data is served automatically
when `real_dataset.csv` exists (or force it with `SPORTS_LAB_SOURCE=real` / `=demo`).

Flags: `--force` (rebuild all), `--skip-osm`, `--skip-scrape`.

## Steps & sources

| Step | Module | Source | Key? |
|---|---|---|---|
| 1 geographic backbone | `geo.py` | Census 2023 Gazetteer (counties + places + county subdivisions) + TIGER/Line | no |
| 2 socioeconomic predictors | `census_acs_bulk.py` | Census **ACS 5-year** public Summary File flat files (`www2.census.gov`) | no |
| 3 tennis access | `osm_tennis.py` | OpenStreetMap `sport=tennis` via Overpass (ODbL) | no |
| 4 outcome (rosters) | `scrape/` | Public ACC + Big Ten team roster pages (pilot) | no |
| 5 assemble panel | `build.py` | — | — |

`census_acs.py` uses the ACS **API** instead if `CENSUS_API_KEY` is set in
`backend/.env` (optional — smaller download, vintages 2019-2023). The keyless
bulk loader covers vintages 2022 & 2023, which is what the pilot needs.

## Panel definition

- **Rows:** every U.S. county with ACS data × every roster season scraped (2023–2026).
- **`d1_players`:** count of scraped ACC + Big Ten tennis players whose published
  hometown geocodes to that county that season (0 where none). Hometown → county
  via an offline Census-gazetteer crosswalk with a fuzzy fallback; international
  players are excluded and counted in the provenance file.
- **Predictors** for roster season *Y* use ACS 5-year vintage *Y − 1* (clamped to
  downloaded vintages). Tennis-court counts are one current OSM snapshot.
- Provenance (row counts, geocode match rates, vintages, limitations) is written
  to `data/real/real_dataset_provenance.json` and surfaced in the app's Data tab.

## Known limitations (surfaced in the UI, not hidden)

1. Roster coverage is **partial** — the scrape gets most SIDEARM-based
   athletics sites (Nuxt + legacy) across all the major D1 conferences, but not
   every D1 tennis program (some use other platforms, or block automated
   access). `d1_players` therefore undercounts true D1 representation. Exact
   per-school/season coverage is in `data/real/roster_scrape_coverage.csv`;
   the built dataset's `_provenance.json` records the totals.
2. Predictors are near-static across the 2023–2026 span (ACS vintage lag).
3. International players (~40% of D1 tennis) have no U.S. county and are excluded
   from the panel; the count is reported in the provenance file.
4. `mten`/`m-tennis` slug sites and a few historical seasons don't always
   resolve — those schools contribute fewer seasons.

## Replacing the pilot roster with a full / licensed dataset

Produce a CSV matching `data/real/roster_import_template.csv`
(`realdata/roster_schema.py :: ROSTER_COLUMNS`), save it as
`data/real/rosters_pilot.csv`, and re-run `python -m realdata.build`. Nothing
else changes.

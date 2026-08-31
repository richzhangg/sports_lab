"""
Hometown string  ->  U.S. county FIPS.

Strategy (all offline, no API key):
  1. parse "City, ST" / "City, State" / "City, State, USA"
  2. exact match on the (normalized city, state) crosswalk from geo.py
  3. fuzzy match (rapidfuzz) within the same state, score >= 88
  4. unmatched -> recorded with reason (international players, ambiguous, typo)

International hometowns (non-US) are expected and simply excluded from the
county panel; the count of them is reported so coverage is transparent.
"""
from __future__ import annotations
import re
from functools import lru_cache

import pandas as pd
from rapidfuzz import process, fuzz

from .geo import normalize_city
from .paths import CITY_COUNTY_XWALK

COUNTRIES = {
    "spain", "france", "germany", "italy", "greece", "portugal", "netherlands", "belgium",
    "switzerland", "austria", "sweden", "norway", "denmark", "finland", "poland", "czech republic",
    "czechia", "slovakia", "hungary", "romania", "bulgaria", "serbia", "croatia", "slovenia",
    "bosnia and herzegovina", "russia", "ukraine", "belarus", "lithuania", "latvia", "estonia",
    "united kingdom", "england", "scotland", "wales", "ireland", "iceland",
    "canada", "mexico", "brazil", "argentina", "chile", "colombia", "peru", "ecuador", "venezuela",
    "uruguay", "paraguay", "bolivia", "china", "japan", "south korea", "korea", "india", "thailand",
    "vietnam", "indonesia", "philippines", "malaysia", "singapore", "taiwan", "hong kong",
    "australia", "new zealand", "south africa", "egypt", "morocco", "tunisia", "nigeria", "kenya",
    "israel", "turkey", "lebanon", "jordan", "united arab emirates", "uae", "qatar", "saudi arabia",
    "kazakhstan", "uzbekistan", "georgia (country)", "armenia", "puerto rico", "jamaica",
    "dominican republic", "bahamas", "barbados", "trinidad and tobago", "costa rica", "panama",
    "guatemala", "el salvador", "honduras", "cuba",
}

US_STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
    "colorado": "CO", "connecticut": "CT", "delaware": "DE", "district of columbia": "DC",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID", "illinois": "IL",
    "indiana": "IN", "iowa": "IA", "kansas": "KS", "kentucky": "KY", "louisiana": "LA",
    "maine": "ME", "maryland": "MD", "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
    "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT", "virginia": "VA",
    "washington": "WA", "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
}
USPS = set(US_STATES.values())

# AP / athletics-style state abbreviations as they appear in rosters ("Fla.", "N.C.")
AP_STATE_ABBR = {
    "ala": "AL", "ariz": "AZ", "ark": "AR", "calif": "CA", "colo": "CO", "conn": "CT",
    "del": "DE", "fla": "FL", "ga": "GA", "ill": "IL", "ind": "IN", "kan": "KS", "kans": "KS",
    "ky": "KY", "la": "LA", "mass": "MA", "md": "MD", "mich": "MI", "minn": "MN", "miss": "MS",
    "mo": "MO", "mont": "MT", "neb": "NE", "nebr": "NE", "nev": "NV", "okla": "OK", "ore": "OR",
    "pa": "PA", "penn": "PA", "tenn": "TN", "vt": "VT", "va": "VA", "wash": "WA", "wis": "WI",
    "wisc": "WI", "wva": "WV", "wva": "WV", "nc": "NC", "sc": "SC", "nd": "ND", "sd": "SD",
    "nh": "NH", "nj": "NJ", "nm": "NM", "ny": "NY", "ri": "RI", "dc": "DC", "colo.": "CO",
}


@lru_cache(maxsize=1)
def _xwalk() -> pd.DataFrame:
    return pd.read_csv(CITY_COUNTY_XWALK, dtype={"county_fips": str})


@lru_cache(maxsize=1)
def _by_state() -> dict[str, dict]:
    x = _xwalk()
    out: dict[str, dict] = {}
    for st, grp in x.groupby("state"):
        out[st] = {
            "keys": grp["city_key"].tolist(),
            "lookup": dict(zip(grp["city_key"], zip(grp["county_fips"], grp["county_name"]))),
        }
    return out


def parse_hometown(raw: str) -> tuple[str | None, str | None, bool]:
    """-> (city, state_usps, is_us). is_us False when clearly international."""
    if not raw or not str(raw).strip():
        return None, None, False
    s = re.sub(r"\s+", " ", str(raw).strip().strip("."))
    if s.lower() in COUNTRIES:
        return None, None, False
    parts = [p.strip() for p in s.split(",") if p.strip()]
    if len(parts) == 1:
        # try "City ST" / "City Statename" without a comma
        toks = parts[0].split()
        if len(toks) >= 2:
            last = toks[-1].upper().replace(".", "")
            if last in USPS:
                return " ".join(toks[:-1]), last, True
            if toks[-1].lower() in US_STATES:
                return " ".join(toks[:-1]), US_STATES[toks[-1].lower()], True
        return parts[0], None, True  # bare city, state unknown
    city = parts[0]
    tail = [p.lower() for p in parts[1:]]
    if any(t in ("usa", "u.s.a", "us", "u.s", "united states") for t in tail):
        tail = [t for t in tail if t not in ("usa", "u.s.a", "us", "u.s", "united states")]
    if not tail:
        return city, None, True
    raw_tok = tail[-1]
    tok = raw_tok.upper().replace(".", "").replace(" ", "")
    if tok in USPS:
        return city, tok, True
    if raw_tok in US_STATES:
        return city, US_STATES[raw_tok], True
    if tok.lower() in AP_STATE_ABBR:
        return city, AP_STATE_ABBR[tok.lower()], True
    # a non-US country name in the tail
    return city, None, False


def geocode_series(hometowns: pd.Series) -> pd.DataFrame:
    bs = _by_state()
    recs = []
    for raw in hometowns:
        city, st, is_us = parse_hometown(raw)
        rec = {"hometown_raw": raw, "city": city, "state": st,
               "county_fips": None, "county_name": None, "match": "none"}
        if not is_us:
            rec["match"] = "international"
            recs.append(rec); continue
        if not city:
            rec["match"] = "unparsed"
            recs.append(rec); continue
        key = normalize_city(city)
        states = [st] if st else list(bs.keys())
        best = None
        for s in states:
            d = bs.get(s)
            if not d:
                continue
            if key in d["lookup"]:
                fips, name = d["lookup"][key]
                rec.update(county_fips=fips, county_name=name, state=s, match="exact")
                best = "exact"
                break
        if best is None and st:  # fuzzy only when we know the state (keeps it safe)
            d = bs.get(st)
            if d and d["keys"]:
                m = process.extractOne(key, d["keys"], scorer=fuzz.WRatio, score_cutoff=88)
                if m:
                    fips, name = d["lookup"][m[0]]
                    rec.update(county_fips=fips, county_name=name, match=f"fuzzy:{int(m[1])}")
        recs.append(rec)
    return pd.DataFrame(recs)


if __name__ == "__main__":
    demo = pd.Series([
        "Winston-Salem, NC", "Bradenton, Florida", "Dallas, Texas, USA",
        "Moscow, Russia", "Saint Louis, MO", "Palo Alto, CA",
    ])
    print(geocode_series(demo).to_string(index=False))

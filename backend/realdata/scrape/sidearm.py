"""
Roster fetcher for college-athletics sites (predominantly the SIDEARM Sports
platform, now a Nuxt app that ships its data as a `devalue`-serialized payload).

Public methods return a list of raw player dicts:
    {season, player_name, gender, school, conference, division,
     hometown_raw, source_url}

Three extraction strategies are tried in order and the one that works is logged:
  1. Nuxt `devalue` blob in the season roster page  (works for current + history)
  2. SIDEARM `/api/v2/Rosters` JSON API              (current season only)
  3. legacy `sidearm-roster-player` HTML markup      (older sites)
"""
from __future__ import annotations
import json
import re
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
GLOBAL_SPORT_ID = {"mens-tennis": 19, "womens-tennis": 20}
SLUG_ALTS = {
    "mens-tennis": ["mens-tennis", "mten", "m-tennis", "mtennis"],
    "womens-tennis": ["womens-tennis", "wten", "w-tennis", "wtennis"],
}


def _get(url: str, tries: int = 2, **kw) -> requests.Response | None:
    for i in range(tries):
        try:
            # (connect, read) — read is between-bytes; keep it short so a
            # trickling server can't wedge a worker for minutes.
            r = requests.get(url, headers=UA, timeout=(6, 15), **kw)
            if r.status_code == 404:
                return r
            if r.status_code >= 500 or r.status_code == 429:
                time.sleep(3 * (i + 1)); continue
            return r
        except requests.RequestException:
            time.sleep(3 * (i + 1))
    return None


# --------------------------------------------------------------------------- #
# strategy 1: Nuxt devalue payload
# --------------------------------------------------------------------------- #
def _devalue_players(html: str) -> list[dict]:
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S)
    scripts = [s for s in scripts if "hometown" in s]
    arr = None
    for blob in sorted(scripts, key=len, reverse=True):
        m = re.search(r"(\[.*\])", blob, re.S)
        if not m:
            continue
        try:
            cand = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(cand, list) and len(cand) > 10:
            arr = cand
            break
    if arr is None:
        return []

    def unravel(x, depth=0):
        if isinstance(x, bool) or x is None:
            return x
        if isinstance(x, int):
            if 0 <= x < len(arr) and depth < 8:
                return unravel(arr[x], depth + 1)
            return x
        if isinstance(x, list):
            return [unravel(v, depth + 1) for v in x]
        if isinstance(x, dict):
            return {k: unravel(v, depth + 1) for k, v in x.items()}
        return x

    # SIDEARM templates use either camelCase or snake_case player keys
    FN = ("firstName", "first_name")
    LN = ("lastName", "last_name")

    def pick(d, keys):
        for k in keys:
            if k in d:
                return d[k]
        return None

    seen, out = set(), []
    for v in arr:
        if not isinstance(v, dict) or "hometown" not in v:
            continue
        if not (any(k in v for k in FN) and any(k in v for k in LN)):
            continue
        if str(v.get("type") or "").lower() == "coach":
            continue
        d = unravel(v)
        fn, ln, ht = pick(d, FN), pick(d, LN), d.get("hometown")
        if isinstance(fn, str) and fn.strip() and isinstance(ln, str):
            name = f"{fn} {ln}".strip()
            key = (name, ht if isinstance(ht, str) else None)
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "player_name": name,
                "gender": d.get("gender") if isinstance(d.get("gender"), str) else None,
                "hometown_raw": ht if isinstance(ht, str) else "",
            })
    return out


# --------------------------------------------------------------------------- #
# strategy 2: SIDEARM /api/v2
# --------------------------------------------------------------------------- #
def _api_v2_players(host: str, sport_slug: str) -> list[dict]:
    sp = _get(f"https://{host}/api/v2/sports")
    if not sp or sp.status_code != 200:
        return []
    try:
        sports = sp.json()
    except json.JSONDecodeError:
        return []
    gsid = GLOBAL_SPORT_ID[sport_slug]
    local = next((s for s in sports if s.get("globalSportId") == gsid), None)
    if not local:
        return []
    rr = _get(f"https://{host}/api/v2/Rosters?sportId={local['id']}&seasonId=")
    if not rr or rr.status_code != 200:
        return []
    try:
        items = rr.json().get("items", [])
    except json.JSONDecodeError:
        return []
    out = []
    for it in items:
        for p in it.get("players", []):
            fn, ln = (p.get("firstName") or "").strip(), (p.get("lastName") or "").strip()
            if fn:
                out.append({
                    "player_name": f"{fn} {ln}".strip(),
                    "gender": p.get("gender"),
                    "hometown_raw": p.get("hometown") or "",
                })
    return out


# --------------------------------------------------------------------------- #
# strategy 3: legacy (pre-Nuxt) SIDEARM HTML
# --------------------------------------------------------------------------- #
_TAGS = re.compile(r"<[^>]+>")


def _legacy_players(html: str) -> list[dict]:
    out, seen = [], set()
    # each roster entry is a <li class="sidearm-roster-player ...">
    blocks = re.split(r'<li[^>]*class="[^"]*sidearm-roster-player[ "]', html)[1:]
    for b in blocks:
        b = b[: b.find("</li>") if "</li>" in b else 4000]
        nm = re.search(r'sidearm-roster-player-name["\s>].*?<a\b[^>]*>(.*?)</a>', b, re.S)
        if not nm:
            nm = re.search(r'sidearm-roster-player-name["\s>](.*?)</(?:h3|p|div)>', b, re.S)
        ht = re.search(r'sidearm-roster-player-hometown["\s>][^>]*>(.*?)</span>', b, re.S)
        if not (nm and ht):
            continue
        name = _TAGS.sub("", nm.group(1)).strip()
        home = _TAGS.sub("", ht.group(1)).strip()
        if not name or len(name) > 60 or (name, home) in seen:
            continue
        seen.add((name, home))
        out.append({"player_name": name, "gender": None, "hometown_raw": home})
    return out


# --------------------------------------------------------------------------- #
def fetch_roster(host: str, sport_slug: str, season_label: str | None,
                 season_year: int, school: str, conference: str) -> tuple[list[dict], str]:
    """season_label like '2023-24', or None for the current roster."""
    # candidate roster URLs: path-suffix (Nuxt) and ?season= (legacy SIDEARM)
    if season_label:
        suffixes = [f"/{season_label}", f"?season={season_label}"]
    else:
        suffixes = [""]
    players, method, url = [], "none", f"https://{host}/sports/{sport_slug}/roster"
    for slug in SLUG_ALTS.get(sport_slug, [sport_slug]):
        for suffix in suffixes:
            cand = f"https://{host}/sports/{slug}/roster{suffix}"
            r = _get(cand)
            if r is None or r.status_code != 200:
                continue
            url = cand
            p = _devalue_players(r.text)
            if p:
                players, method = p, "devalue"
                break
            p = _legacy_players(r.text)
            if p:
                players, method = p, "legacy-html"
                break
        if players:
            break
    if not players and season_label is None:
        p = _api_v2_players(host, sport_slug)
        if p:
            players, method = p, "api-v2"

    default_gender = "M" if sport_slug == "mens-tennis" else "W"
    rows = [{
        "season": season_year,
        "player_name": p["player_name"],
        "gender": (p["gender"] or default_gender)[:1].upper(),
        "school": school,
        "conference": conference,
        "division": "D1",
        "hometown_raw": p["hometown_raw"],
        "source_url": url,
    } for p in players]
    return rows, method

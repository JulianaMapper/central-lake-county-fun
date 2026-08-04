#!/usr/bin/env python3
"""Audit every park pin on the map against independent sources.

Why this exists: on 2026-08-04 twelve pins turned out to be 1.3-4.9 miles from the
real park, including ones people actually drive to. They looked fine on the map.
The only way to catch that class of error is to compare each stored coordinate
against a source that had no hand in producing it.

Two independent references:
  1. Lake County GIS "Parks and Open Space" — 926 county-authored park polygons.
     Matched by name; the centroid is compared to our pin.
  2. US Census geocoder — the park's own street address, geocoded fresh.

A park is only flagged when a reference disagrees. Agreement between our pin and
either reference is treated as confirmation. Parks with no address and no GIS
match are reported as UNVERIFIABLE rather than quietly passing.

Usage:
    python3 tools/verify_pins.py                 # audit everything
    python3 tools/verify_pins.py --limit 40      # quick sample
    python3 tools/verify_pins.py --threshold 0.4 # miles before flagging

Nothing is written. This only reports.
"""
import argparse, difflib, json, math, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
GIS_URL = ("https://maps.lakecountyil.gov/arcgis/rest/services/GISMapping/"
           "WABConservation/MapServer/1/query")
CENSUS = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 Chrome/126"}


def load_parks():
    src = INDEX.read_text()
    i = src.index("const PARKS = [")
    j = src.index("\n", i)
    return json.loads(src[i:j][len("const PARKS = "):].rstrip().rstrip(";"))


def miles(a, b):
    R = 3958.8
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1])
    return 2 * R * math.asin(math.sqrt(
        math.sin((p2 - p1) / 2) ** 2 +
        math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))


def fetch_gis():
    """All named county park polygons, as {normalised name: (lat, lon)}."""
    out, offset = {}, 0
    while True:
        q = urllib.parse.urlencode({
            "where": "1=1", "outFields": "NAME", "returnGeometry": "true",
            "geometryPrecision": "6", "outSR": "4326", "f": "json",
            "resultOffset": offset, "resultRecordCount": 1000})
        d = json.load(urllib.request.urlopen(
            urllib.request.Request(f"{GIS_URL}?{q}", headers=UA), timeout=120))
        feats = d.get("features", [])
        for f in feats:
            name = (f["attributes"].get("NAME") or "").strip()
            pts = [p for ring in f["geometry"].get("rings", []) for p in ring]
            if name and pts:
                out.setdefault(norm(name), (sum(p[1] for p in pts) / len(pts),
                                            sum(p[0] for p in pts) / len(pts)))
        offset += len(feats)
        if len(feats) < 1000 or not d.get("exceededTransferLimit"):
            return out


def norm(s):
    s = re.sub(r"[’']", "", (s or "").lower())
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def census(addr):
    try:
        q = urllib.parse.urlencode({"address": addr,
                                    "benchmark": "Public_AR_Current",
                                    "format": "json"})
        d = json.load(urllib.request.urlopen(
            urllib.request.Request(f"{CENSUS}?{q}", headers=UA), timeout=30))
        m = d["result"]["addressMatches"]
        if m:
            return m[0]["coordinates"]["y"], m[0]["coordinates"]["x"]
    except Exception:
        pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=0.5,
                    help="miles of disagreement before a pin is flagged")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    parks = load_parks()
    if args.limit:
        parks = parks[:args.limit]
    print(f"auditing {len(parks)} parks (flag at {args.threshold} mi)\n")

    print("fetching Lake County GIS park polygons…", flush=True)
    gis = fetch_gis()
    keys = list(gis)
    print(f"  {len(gis)} named polygons\n")

    ok = flagged = unverifiable = 0
    problems = []
    for n, p in enumerate(parks, 1):
        pin = (p["lat"], p["lon"])
        refs = []

        k = norm(p["name"])
        # EXACT normalised name only. Fuzzy matching produced spectacular false
        # alarms (it once paired "Grassy Lake" with a park 18 miles away), and a
        # false alarm in an audit tool is worse than a miss — it destroys trust in
        # the whole report.
        hit = gis.get(k)
        if hit:
            refs.append(("county GIS", miles(pin, hit)))

        addr = (p.get("address") or "").strip()
        if addr and not re.search(r"&|and\b", addr):      # skip intersections
            c = census(f"{addr}, {p.get('city','')}, IL")
            time.sleep(0.25)
            if c:
                refs.append(("its own address", miles(pin, c)))

        if not refs:
            unverifiable += 1
            problems.append(("UNVERIFIABLE", p, None, None))
        elif min(d for _, d in refs) <= args.threshold:
            ok += 1                                      # at least one agrees
        else:
            flagged += 1
            src, dist = min(refs, key=lambda r: r[1])   # most conservative claim
            problems.append(("DISAGREES", p, src, dist))

        if n % 25 == 0:
            print(f"  …{n}/{len(parks)}", flush=True)

    print(f"\n{'='*74}\nconfirmed by at least one source : {ok}")
    print(f"disagree by >{args.threshold} mi             : {flagged}")
    print(f"no address and no GIS match      : {unverifiable}\n")

    bad = [x for x in problems if x[0] == "DISAGREES"]
    if bad:
        print("PINS TO CHECK BY HAND (worst first):")
        for _, p, src, dist in sorted(bad, key=lambda x: -x[3]):
            print(f"   {dist:5.2f} mi off per {src:16} {p['name'][:34]:34} {p.get('city','')}")
    unv = [x for x in problems if x[0] == "UNVERIFIABLE"]
    if unv:
        print(f"\nUNVERIFIABLE ({len(unv)}) — no street address on file and no county polygon:")
        for _, p, _, _ in unv[:30]:
            print(f"      {p['name'][:40]:40} {p.get('city','')}")
        if len(unv) > 30:
            print(f"      … and {len(unv)-30} more")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

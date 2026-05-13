#!/usr/bin/env python3
"""
check_geocodes.py — verify producer coordinates against Nominatim (OpenStreetMap).

Reads PRODUCERS directly from index.html so it stays in sync.
Tries each producer by name first; falls back to the region string if not found.
Rate-limited to 1 req/s to respect Nominatim's usage policy.

Usage:
    python3 check_geocodes.py
"""

import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request

THRESHOLD_KM = 5    # show as OK below this
FAR_KM = 30         # show as FAR between threshold and this; VERY FAR above

COUNTRY_CODES = {
    "France": "fr", "Italy": "it", "Spain": "es", "Portugal": "pt",
    "USA": "us", "Australia": "au", "New Zealand": "nz",
    "South Africa": "za", "Lebanon": "lb",
}


def haversine_km(lat1, lng1, lat2, lng2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def nominatim_search(q, countrycodes=None):
    params = {"q": q, "format": "json", "limit": 1}
    if countrycodes:
        params["countrycodes"] = countrycodes
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url, headers={"User-Agent": "WineCellarMapVerifier/1.0 (personal project)"}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def load_producers():
    with open("index.html", encoding="utf-8") as f:
        html = f.read()

    marker = "const PRODUCERS = "
    try:
        start = html.index(marker) + len(marker)
    except ValueError:
        sys.exit("ERROR: could not find 'const PRODUCERS' in index.html")

    # Walk forward counting braces to find the end of the object
    depth, end = 0, start
    for i, c in enumerate(html[start:], start):
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    js = html[start:end]
    # Make it valid JSON: quote bare keys, strip trailing commas
    js = re.sub(r"\b(lat|lng|region|country)\b\s*:", r'"\1":', js)
    js = re.sub(r",(\s*[}\]])", r"\1", js)

    try:
        return json.loads(js)
    except json.JSONDecodeError as e:
        sys.exit(f"ERROR parsing PRODUCERS: {e}")


def check_producer(name, geo):
    cc = COUNTRY_CODES.get(geo["country"])
    source = None
    results = None

    # Try 1: producer name + country
    try:
        results = nominatim_search(f"{name}, {geo['country']}", cc)
    except Exception as e:
        print(f"  [{name}] network error: {e}", file=sys.stderr)
    time.sleep(1.1)

    if not results:
        # Try 2: region + country (gives us at least the village)
        source = "region"
        try:
            results = nominatim_search(f"{geo['region']}, {geo['country']}", cc)
        except Exception as e:
            print(f"  [{name}] network error on fallback: {e}", file=sys.stderr)
        time.sleep(1.1)
    else:
        source = "name"

    if not results:
        return None, None, None, None, "NOT FOUND"

    r = results[0]
    slat, slng = float(r["lat"]), float(r["lon"])
    dist = haversine_km(geo["lat"], geo["lng"], slat, slng)
    display = r.get("display_name", "")

    if dist < THRESHOLD_KM:
        status = "OK"
    elif dist < FAR_KM:
        status = "FAR"
    else:
        status = "VERY FAR"

    return slat, slng, dist, display, status, source


def main():
    producers = load_producers()
    total = len(producers)
    print(f"\nChecking {total} producers against Nominatim (this takes ~{total * 2}s)…\n")

    results = {}
    for i, (name, geo) in enumerate(producers.items(), 1):
        print(f"  [{i}/{total}] {name}…", end=" ", flush=True)
        outcome = check_producer(name, geo)
        slat, slng, dist, display, status, *rest = outcome if len(outcome) == 6 else (*outcome, None)
        source = rest[0] if rest else None
        results[name] = {
            "geo": geo,
            "slat": slat, "slng": slng,
            "dist": dist, "display": display,
            "status": status, "source": source,
        }
        print(status if status == "OK" else f"{status} ({dist:.0f} km)" if dist else status)

    # ── Summary table ──────────────────────────────────────────────────────────
    W = 120
    print("\n" + "=" * W)
    print(f"{'Producer':<34} {'Status':<10} {'Current':^22} {'Suggested':^22} {'Dist':>7}  Via")
    print("-" * W)

    needs_review = []
    for name, r in results.items():
        geo = r["geo"]
        cur = f"{geo['lat']:.4f}, {geo['lng']:.4f}"

        if r["status"] == "NOT FOUND":
            print(f"{name:<34} {'NOT FOUND':<10} {cur:<22}")
            needs_review.append(name)
            continue

        sug = f"{r['slat']:.4f}, {r['slng']:.4f}"
        dist_str = f"{r['dist']:.1f} km"
        marker = " ◀" if r["status"] != "OK" else ""
        print(
            f"{name:<34} {r['status']:<10} {cur:<22} {sug:<22} {dist_str:>8}  [{r['source']}]{marker}"
        )
        if r["status"] != "OK":
            needs_review.append(name)

    print("=" * W)

    # ── Detail block for entries needing review ────────────────────────────────
    if not needs_review:
        print("\nAll producers look good.")
        return

    print(f"\n{'─'*W}")
    print(f"REVIEW NEEDED ({len(needs_review)} producers)\n")

    for name in needs_review:
        r = results[name]
        geo = r["geo"]
        print(f"  {name}")
        print(f"    region   : {geo['region']}, {geo['country']}")
        print(f"    current  : lat={geo['lat']}, lng={geo['lng']}")
        if r["status"] != "NOT FOUND":
            print(f"    suggested: lat={r['slat']:.4f}, lng={r['slng']:.4f}  ({r['dist']:.1f} km away)")
            print(f"    via [{r['source']}]: {(r['display'] or '')[:90]}")
            print(f"    JS snippet:")
            print(f'      "lat": {r["slat"]:.4f}, "lng": {r["slng"]:.4f},')
        print()


if __name__ == "__main__":
    main()

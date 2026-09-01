#!/usr/bin/env python3
"""Refresh recipe/sheets_city.geojson from the current transforms.

    python3 tools/sheetsgeo.py --year 1912

sheets_city.geojson is the §5 index of every unit's footprint and how it was
placed; coverage.py draws it. It was written once by the city export and not
touched by the control solves since, so its footprints had drifted from
transforms_city.json (and sheet 72, placed later, was missing). This rewrites
every footprint from the live transform and keeps each unit's tier/how,
taking them from the transform entry where the solve recorded one.
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe                      # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1912", "1899"])
    a = ap.parse_args()
    r = Recipe(int(a.year))
    p = os.path.join(r.dir, "sheets_city.geojson")
    old = json.load(open(p)) if os.path.exists(p) else {"type": "FeatureCollection", "features": []}
    props = {str(f["properties"].get("unit")): f["properties"] for f in old["features"]}
    feats = []
    for u in sorted(r.units, key=lambda k: int("".join(c for c in k if c.isdigit()))):
        e = r.units[u]["extent"]
        M, t = r.sheet_matrix(u)
        ring = [list(map(float, M @ np.array(c, float) + t)) for c in
                ((e[0], e[1]), (e[2], e[1]), (e[2], e[3]), (e[0], e[3]), (e[0], e[1]))]
        ts = r.transforms["sheets"][u]
        pr = dict(props.get(u, {"unit": u, "file": r.units[u].get("file"), "year": r.year}))
        pr["unit"] = u
        if ts.get("tier"):
            pr["tier"] = ts["tier"]
            pr["how"] = ts.get("how", pr.get("how"))
        pr.setdefault("tier", "control")
        pr["scale_px_per_native"] = round(float(np.hypot(M[0][0], M[1][0])), 5)
        pr["rotation_deg"] = round(float(np.degrees(np.arctan2(-M[0][1], M[0][0]))), 3)
        feats.append({"type": "Feature", "properties": pr,
                      "geometry": {"type": "Polygon",
                                   "coordinates": [[[round(x, 2), round(y, 2)] for x, y in ring]]}})
    json.dump({"type": "FeatureCollection",
               "note": "unit footprints in mosaic px from transforms_city.json (tools/sheetsgeo.py)",
               "features": feats}, open(p, "w"), indent=1)
    tiers = {}
    for f in feats:
        tiers[f["properties"]["tier"]] = tiers.get(f["properties"]["tier"], 0) + 1
    print(f"wrote {p}: {len(feats)} units, tiers {tiers}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

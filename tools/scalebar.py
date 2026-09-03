#!/usr/bin/env python3
"""Find each plate's printed 'Scale of Feet' bar and record it as furniture.

    python3 tools/scalebar.py --year 1912 [--apply]

The bar is engraved identically across the series, so one crop of it (from
sheet 4) template-matches every plate: scores run 0.52-0.74 for a true hit
and below 0.52 only where the bar sits outside the neatline-trimmed extent
or the sheet is at a different reduction (sheet 5's archival panels carry
'Scale 100 Ft. to One Inch.' at twice the size). Hits become
`furniture_native` boxes, which tools/reciplib.py cuts out of the unit's
footprint so a neighbour that maps the same ground owns it and the bar
never prints inside the city.

Written after the round-5 crops showed plate 14's bar standing in 27th St.
The boxes it produced are already in units.json; this keeps the method
with the recipe.
"""
import argparse
import json
import os
import sys

TPL_UNIT, TPL_BOX = "4", (2180, 3640, 2835, 3735)   # the crop the series matches
THRESH = 0.52


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=1912)
    ap.add_argument("--thresh", type=float, default=THRESH)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    import cv2
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from reciplib import Recipe
    r = Recipe(a.year)
    g = cv2.imread(r.fetch(r.sheet_file(TPL_UNIT)), cv2.IMREAD_GRAYSCALE)
    x0, y0, x1, y1 = TPL_BOX
    tpl = g[y0:y1, x0:x1]
    th, tw = tpl.shape
    doc = json.load(open(os.path.join(r.dir, "units.json")))
    hits = 0
    for u in sorted(r.units, key=lambda z: (len(z), z)):
        if r.units[u].get("panel_of"):
            continue
        img = cv2.imread(r.fetch(r.sheet_file(u)), cv2.IMREAD_GRAYSCALE)
        if img is None or img.shape[0] < th or img.shape[1] < tw:
            continue
        res = cv2.matchTemplate(img, tpl, cv2.TM_CCOEFF_NORMED)
        _, mx, _, loc = cv2.minMaxLoc(res)
        mark = "hit " if mx >= a.thresh else "    "
        print(f"{mark}{u:4s} {mx:.3f} at ({loc[0]}, {loc[1]})")
        if mx < a.thresh:
            continue
        hits += 1
        if a.apply:
            fu = doc["units"][u].setdefault("furniture_native", [])
            if not any(f["kind"] == "scale bar" for f in fu):
                fu.append({"kind": "scale bar",
                           "box": [loc[0] - 8, loc[1] - 8, loc[0] + tw + 8, loc[1] + th + 8],
                           "how": f"template match of the series' bar, score {mx:.2f} (tools/scalebar.py)"})
    print(f"{hits} plates over {a.thresh}")
    if a.apply:
        json.dump(doc, open(os.path.join(r.dir, "units.json"), "w"), indent=1)
        print("applied to units.json")


if __name__ == "__main__":
    main()

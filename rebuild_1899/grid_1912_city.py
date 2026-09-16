#!/usr/bin/env python3
"""Check placed 1912 units against a linearly extrapolated corridor grid.

(Historical: this check is what exposed the stacked outlot placements of the
chain solve. The grid itself is now solved by grid_place_1912.py; this
script only writes grid.json with --write-grid.)

Downtown corridors (streets 18-26, avenues A-K) are measured from verified
control files.  The rest of the island is a regular grid, so each axis is
fitted as x = x0 + px*slot, y = y0 + py*street on the verified corridors and
extrapolated; every extrapolated corridor is tagged as such.

The extrapolation is CHECKED, not assumed: for every placed outer unit the
key-map transcription gives its street/avenue span, so the span's predicted
centre is compared with the unit's placed footprint centre.  Residuals go to
recipe/qc/grid_city_check.json; the grid itself to recipe/grid.json (the
downtown entries keep their measured values).
"""
import json, os, re, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
from reciplib import Recipe
ROOT = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(ROOT); os.chdir(REPO)
RD = "outputs/1912/recipe"

g = json.load(open(f"{RD}/grid.json"))
st = {int(k): v["y"] for k, v in g["streets"].items()}
av = {int(k): v["x"] for k, v in g["avenues"].items()}
ks = np.array(sorted(st)); ys = np.array([st[k] for k in ks])
py, y0 = np.polyfit(ks, ys, 1)
ka = np.array(sorted(av)); xs = np.array([av[k] for k in ka])
px, x0 = np.polyfit(ka, xs, 1)
res_y = ys - (y0 + py * ks); res_x = xs - (x0 + px * ka)
print(f"street pitch {py:.1f} px (resid max {abs(res_y).max():.1f}); avenue pitch {px:.1f} px (resid max {abs(res_x).max():.1f})")

STREETS = range(6, 48); AVES = range(0, 28)
for s in STREETS:
    if s not in st:
        g["streets"][str(s)] = {"y": round(y0 + py * s, 1), "n": 0, "spread": None,
                                "method": "extrapolated from verified downtown corridors (linear fit)"}
for a in AVES:
    if a not in av:
        g["avenues"][str(a)] = {"x": round(x0 + px * a, 1), "n": 0, "spread": None,
                                "method": "extrapolated from verified downtown corridors (linear fit)"}
g["avenue_slots"] = "A=0 .. L=11 M=12 M1/2=13 N=14 N1/2=15 ... T=26 T1/2=27 (outlot half-avenues are full corridors)"
g["fit"] = {"street": {"y0": y0, "pitch": py, "resid_max": float(abs(res_y).max())},
            "avenue": {"x0": x0, "pitch": px, "resid_max": float(abs(res_x).max())},
            "note": "extrapolated corridors carry method='extrapolated'; see qc/grid_city_check.json for the per-unit check against placed footprints"}

# ---- check against placed units ----
R = Recipe(1912)
tf = R.transforms["sheets"]; units = R.units
spans = {}
for q in "NW NE SW SE".split():
    for r in json.load(open(f"rebuild_1899/out/keymap_1912_{q}.json"))["results"]:
        spans[str(r["sheet"])] = r
def st_int(v):
    return int(re.sub(r"\D", "", str(v)))
rows = []
for uid, u in units.items():
    sp = spans.get(uid)
    if not sp or not sp["avenues"]:
        continue
    try:
        slots = [Recipe.avenue_slot(a) for a in sp["avenues"]]
    except ValueError as e:
        print("skip", uid, e); continue
    s0, s1 = sorted(st_int(v) for v in sp["streets"])[0], sorted(st_int(v) for v in sp["streets"])[-1]
    cx = (g["avenues"][str(min(slots))]["x"] + g["avenues"][str(max(slots))]["x"]) / 2
    cy = (g["streets"][str(s0)]["y"] + g["streets"][str(s1)]["y"]) / 2
    M = np.array(tf[uid]["m"]); t = np.array(tf[uid]["t"])
    x0e, y0e, x1e, y1e = u["extent"]
    c = M @ np.array([(x0e + x1e) / 2, (y0e + y1e) / 2]) + t
    rows.append({"unit": uid, "tier": tf[uid]["tier"], "span_streets": [s0, s1], "span_slots": [min(slots), max(slots)],
                 "predicted_centre": [round(cx), round(cy)], "placed_centre": [round(float(c[0])), round(float(c[1]))],
                 "dx_px": round(float(c[0] - cx)), "dy_px": round(float(c[1] - cy)),
                 "dx_slots": round(float((c[0] - cx) / px), 2), "dy_streets": round(float((c[1] - cy) / py), 2)})
rows.sort(key=lambda r: -max(abs(r["dx_slots"]), abs(r["dy_streets"])))
json.dump({"note": "placed footprint centre vs centre predicted from key-map span on the extrapolated grid. "
                   "A sheet's printed area is not centred on its span (margins, insets, shoreline), so "
                   "|d| < ~0.6 pitch is agreement; larger values flag either a bad placement or a span/inset mismatch.",
           "rows": rows}, open(f"{RD}/qc/grid_city_check.json", "w"), indent=1)
if "--write-grid" in sys.argv:            # superseded by grid_place_1912.py's solved grid
    json.dump(g, open(f"{RD}/grid.json", "w"), indent=1)
d = np.array([[r["dx_slots"], r["dy_streets"]] for r in rows])
print(f"{len(rows)} units checked; |dx| median {np.median(abs(d[:,0])):.2f} slots, |dy| median {np.median(abs(d[:,1])):.2f} streets")
for r in rows[:15]:
    print(f"  {r['unit']:>4} {r['tier']:<16} dx {r['dx_slots']:+.2f} slots  dy {r['dy_streets']:+.2f} streets  span st{r['span_streets']} sl{r['span_slots']}")

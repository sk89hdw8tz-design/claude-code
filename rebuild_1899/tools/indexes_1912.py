#!/usr/bin/env python3
"""Build outputs/1912/recipe/{sheets,intersections,blocks}.geojson.

Coordinates are the 1912 MOSAIC frame (sheet 10 raw px minus [3326,3898]),
not geographic; properties carry the street/avenue names for address lookup.
"""
import json
import os

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(REPO)

tr = json.load(open("outputs/1912/recipe/transforms.json"))["sheets"]
plates = {str(p["sheet"]): p for p in
          json.load(open("outputs/1912/recipe/plates/plate_structure.json"))["plates"]}
grid = json.load(open("outputs/1912/recipe/grid.json"))

AVE_NAMES = {0: "Avenue A (Water)", 1: "Avenue B (Strand)", 2: "Avenue C (Mechanic)",
             3: "Avenue D (Market)", 4: "Avenue E (Postoffice)", 5: "Avenue F (Church)",
             6: "Avenue G (Winnie)", 7: "Avenue H (Ball)", 8: "Avenue I (Sealy)",
             9: "Broadway (Avenue J)", 10: "Avenue K"}
ST_NAME = lambda n: f"{n}{'st' if n % 10 == 1 and n != 11 else 'nd' if n % 10 == 2 and n != 12 else 'rd' if n % 10 == 3 and n != 13 else 'th'} Street"

def to_mosaic(sheet, xy):
    t = tr[sheet]["raw"]
    M = np.array([[t["a"], -t["b"]], [t["b"], t["a"]]])
    return (M @ np.array(xy, float) + np.array([t["tx"], t["ty"]])).tolist()

# ---- sheets.geojson: page quads through transforms
feats = []
for sheet, t in tr.items():
    p = plates.get(sheet)
    if p is None:
        continue
    quad = [to_mosaic(sheet, xy) for xy in p["page_quad_fullres"]]
    quad.append(quad[0])
    feats.append({"type": "Feature",
                  "properties": {"sheet": sheet, "year": 1912,
                                 "source_file": f"sanborn08539_004 image (see inventory)",
                                 "native_size": p["image_size"]},
                  "geometry": {"type": "Polygon", "coordinates": [quad]}})
json.dump({"type": "FeatureCollection",
           "crs_note": grid["frame"], "features": feats},
          open("outputs/1912/recipe/sheets.geojson", "w"), indent=1)

# ---- intersections.geojson
sts = {int(k): v for k, v in grid["streets"].items()}
avs = {int(k): v for k, v in grid["avenues"].items()}
feats = []
for si, srec in sorted(sts.items()):
    for ai, arec in sorted(avs.items()):
        feats.append({"type": "Feature",
                      "properties": {"street": ST_NAME(si), "street_no": si,
                                     "avenue": AVE_NAMES[ai], "avenue_slot": ai,
                                     "confidence": "measured" if srec["n"] > 1 and arec["n"] > 1 else "derived"},
                      "geometry": {"type": "Point",
                                   "coordinates": [arec["x"], srec["y"]]}})
json.dump({"type": "FeatureCollection", "crs_note": grid["frame"], "features": feats},
          open("outputs/1912/recipe/intersections.geojson", "w"), indent=1)

# ---- blocks.geojson: cells between adjacent corridors
feats = []
st_keys = sorted(sts)
av_keys = sorted(avs)
for i in range(len(st_keys) - 1):
    for j in range(len(av_keys) - 1):
        s0, s1 = st_keys[i], st_keys[i + 1]
        a0, a1 = av_keys[j], av_keys[j + 1]
        if s1 - s0 != 1 or a1 - a0 != 1:
            continue
        y0, y1 = sts[s0]["y"], sts[s1]["y"]
        x0, x1 = avs[a0]["x"], avs[a1]["x"]
        feats.append({"type": "Feature",
                      "properties": {
                          "bounded_by": [ST_NAME(s0), ST_NAME(s1),
                                         AVE_NAMES[a0], AVE_NAMES[a1]],
                          "streets": [s0, s1], "avenue_slots": [a0, a1]},
                      "geometry": {"type": "Polygon", "coordinates": [[
                          [x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]}})
json.dump({"type": "FeatureCollection", "crs_note": grid["frame"], "features": feats},
          open("outputs/1912/recipe/blocks.geojson", "w"), indent=1)
print(f"sheets: {len(tr)} transforms, {sum(1 for s in tr if s in plates)} quads; "
      f"intersections: {len(sts)}x{len(avs)}; blocks: {len(feats)}")

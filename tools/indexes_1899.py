#!/usr/bin/env python3
"""Build outputs/1899/recipe/{grid,intersections,blocks}.geojson (+sheets
once transforms exist).

The 1899 mosaic frame IS the ground grid (x = avenue_slot * 1006,
y = street_index * 1169; gauge sheet 13 pinned to its anchor offset), so the
corridor index is exact by construction; sheet footprints come from the
solved transforms when available.
"""
import json
import os

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
RD = "outputs/1899/recipe"

AV_PITCH, ST_PITCH = 1006.0, 1169.0
AVE_NAMES = {0: "Avenue A (Water)", 1: "Avenue B (Strand)", 2: "Avenue C (Mechanic)",
             3: "Avenue D (Market)", 4: "Avenue E (Postoffice)", 5: "Avenue F (Church)",
             6: "Avenue G (Winnie)", 7: "Avenue H (Ball)", 8: "Avenue I (Sealy)",
             9: "Avenue J (Broadway)"}
ST_NAME = lambda n: f"{n}{'st' if n % 10 == 1 and n != 11 else 'nd' if n % 10 == 2 and n != 12 else 'rd' if n % 10 == 3 and n != 13 else 'th'} Street"
STREETS = list(range(16, 28))
AVES = list(range(0, 10))

grid = {
 "frame": "1899 mosaic frame: x = avenue_slot*1006, y = street_index*1169 (SEED grid; gauge sheet 13 at anchor offset)",
 "avenue_slots": "A=0 .. J=9 within the wharf/downtown footprint",
 "streets": {str(s): {"y": s * ST_PITCH, "n": 0, "spread": 0.0,
                      "method": "frame definition"} for s in STREETS},
 "avenues": {str(a): {"x": a * AV_PITCH, "n": 0, "spread": 0.0,
                      "method": "frame definition"} for a in AVES},
}
json.dump(grid, open(f"{RD}/grid.json", "w"), indent=1)

feats = [{"type": "Feature",
          "properties": {"street": ST_NAME(s), "street_no": s,
                         "avenue": AVE_NAMES[a], "avenue_slot": a,
                         "confidence": "frame-exact"},
          "geometry": {"type": "Point", "coordinates": [a * AV_PITCH, s * ST_PITCH]}}
         for s in STREETS for a in AVES]
json.dump({"type": "FeatureCollection", "crs_note": grid["frame"], "features": feats},
          open(f"{RD}/intersections.geojson", "w"), indent=1)

feats = []
for s in STREETS[:-1]:
    for a in AVES[:-1]:
        x0, x1 = a * AV_PITCH, (a + 1) * AV_PITCH
        y0, y1 = s * ST_PITCH, (s + 1) * ST_PITCH
        feats.append({"type": "Feature",
                      "properties": {"bounded_by": [ST_NAME(s), ST_NAME(s + 1),
                                                    AVE_NAMES[a], AVE_NAMES[a + 1]],
                                     "streets": [s, s + 1], "avenue_slots": [a, a + 1]},
                      "geometry": {"type": "Polygon", "coordinates": [[
                          [x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]}})
json.dump({"type": "FeatureCollection", "crs_note": grid["frame"], "features": feats},
          open(f"{RD}/blocks.geojson", "w"), indent=1)

# sheets.geojson if transforms exist
tp = f"{RD}/transforms.json"
if os.path.exists(tp):
    tr = json.load(open(tp))["sheets"]
    feats = []
    for sheet, s in tr.items():
        M = np.array(s["m"]); t = np.array(s["t"])
        W, H = 3400, 4100
        quad = [(M @ np.array(p) + t).tolist() for p in
                ([0, 0], [W, 0], [W, H], [0, H], [0, 0])]
        feats.append({"type": "Feature",
                      "properties": {"sheet": sheet, "year": 1899,
                                     "source_file": f"Galveston_1899_sheet_{int(sheet):02d}.jpg"},
                      "geometry": {"type": "Polygon", "coordinates": [quad]}})
    json.dump({"type": "FeatureCollection", "crs_note": grid["frame"], "features": feats},
              open(f"{RD}/sheets.geojson", "w"), indent=1)
    print("sheets.geojson written from transforms")
else:
    print("transforms.json absent; sheets.geojson deferred")
print(f"grid + {len(STREETS)*len(AVES)} intersections + blocks written")

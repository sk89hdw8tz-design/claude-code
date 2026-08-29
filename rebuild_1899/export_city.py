#!/usr/bin/env python3
"""Export the city-wide placements into each year's recipe.

Writes, per year:
  recipe/transforms_city.json  every unit's similarity transform + how it was
                               placed + quality tier + its source file/panel
  recipe/units.json            unit -> file, panel region, extent, spans
  recipe/seams/ownership_city.json
                               per-unit ownership polygons in the mosaic frame:
                               Voronoi cell of the unit's centre, clipped to its
                               printed extent, and (downtown) minus the frozen
                               min-ink DP regions, which stay authoritative.
  recipe/sheets_city.geojson   unit footprints

Tiers: core (gated downtown solve) > fit (content match) > ties-sim/ties-trans
(adjudicated blind ties) > ties-single (one high-confidence tie) > prior
(grid estimate only — disclosed, not verified).
"""
import json, os, sys
import numpy as np
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
os.chdir(REPO)

TIER = {"frozen": "core", "core": "core", "fit": "fit", "ties-sim": "tie-fit",
        "ties-trans": "tie-translation", "ties-single": "tie-single",
        "profile": "profile", "prior": "prior-unverified", "isolated": "prior-unverified"}
def tier(how):
    for k, v in TIER.items():
        if how.startswith(k):
            return v
    return "unknown"

def halfplane_clip(poly, c_self, c_other):
    """Clip poly to the half-plane closer to c_self than to c_other."""
    d = c_other - c_self
    n = np.linalg.norm(d)
    if n < 1e-6:
        return poly
    d = d / n
    mid = (c_self + c_other) / 2.0
    # big rectangle on the c_self side of the bisector
    perp = np.array([-d[1], d[0]])
    L = 500000.0
    p1 = mid + perp * L
    p2 = mid - perp * L
    p3 = p2 - d * L
    p4 = p1 - d * L
    return poly.intersection(Polygon([p1, p2, p3, p4]))

def run(year, netf, afff, rrf):
    NET = json.load(open(f"rebuild_1899/out/{netf}"))
    AFF = json.load(open(f"rebuild_1899/out/{afff}"))["sheets"]
    RD = f"outputs/{year}/recipe"
    os.makedirs(f"{RD}/seams", exist_ok=True)
    units, tf = {}, {}
    centres, polys = {}, {}
    for uid, u in NET["units"].items():
        a = AFF[uid]
        M = np.array(a["m"], float); t = np.array(a["t"], float)
        x0, y0, x1, y1 = u["extent"]
        quad = [ (M @ np.array(p, float) + t).tolist()
                 for p in ((x0,y0),(x1,y0),(x1,y1),(x0,y1)) ]
        centres[uid] = np.array((M @ np.array([(x0+x1)/2,(y0+y1)/2], float) + t))
        polys[uid] = Polygon(quad)
        tf[uid] = {"m": a["m"], "t": a["t"], "how": a["how"], "tier": tier(a["how"]),
                   "theta_deg": float(np.degrees(np.arctan2(M[1,0], M[0,0]))),
                   "scale": float(np.hypot(M[0,0], M[1,0]))}
        units[uid] = {"file": u["file"], "region": u.get("region"),
                      "extent": u["extent"], "streets": u.get("st"),
                      "avenue_slots": u.get("slots") or u.get("av_slots"),
                      "source_image": u.get("working")}
    # frozen downtown DP regions stay authoritative where they exist
    frozen = {}
    mp = f"{RD}/seams/masks.json"
    if os.path.exists(mp):
        for r in json.load(open(mp))["regions"]:
            g = Polygon(r["polygon_mosaic"]["exterior"])
            if g.is_valid and g.area > 0:
                frozen.setdefault(str(r["sheet"]), []).append(g)
    frozen_union = unary_union([g for v in frozen.values() for g in v]) if frozen else None
    own = []
    for uid in units:
        if uid in frozen:
            for g in frozen[uid]:
                own.append({"unit": uid, "source": "dp-cut(frozen downtown)",
                            "polygon_mosaic": {"exterior": [[round(x,1), round(y,1)]
                                for x, y in np.array(g.exterior.coords)]}})
            continue
        cell = polys[uid]
        for other in units:
            if other == uid:
                continue
            if np.linalg.norm(centres[other] - centres[uid]) > 40000:
                continue
            cell = halfplane_clip(cell, centres[uid], centres[other])
            if cell.is_empty:
                break
        if not cell.is_empty and frozen_union is not None:
            cell = cell.difference(frozen_union)
        for g in ([cell] if cell.geom_type == "Polygon" else list(getattr(cell, "geoms", []))):
            if g.is_empty or g.geom_type != "Polygon" or g.area < 1000:
                continue
            own.append({"unit": uid, "source": "voronoi-clipped-to-extent",
                        "polygon_mosaic": {"exterior": [[round(x,1), round(y,1)]
                            for x, y in np.array(g.exterior.coords)]}})
    json.dump({"convention": {
        "model": "similarity per unit: p_mosaic = m @ p_native + t",
        "frame": ("1899 ground grid x=slot*1006, y=street*1169, gauge unit 13"
                  if year == 1899 else
                  "1912 mosaic frame (sheet 10 raw px minus [3326,3898]); outer units in working-copy px at ~2x"),
        "tiers": "core > fit > tie-fit > tie-translation > tie-single > prior-unverified"},
        "sheets": tf}, open(f"{RD}/transforms_city.json", "w"), indent=1)
    json.dump({"units": units}, open(f"{RD}/units.json", "w"), indent=1)
    json.dump({"convention": "mosaic frame; downtown keeps frozen min-ink DP cuts, "
                             "outer city uses Voronoi cells clipped to each unit's printed extent",
               "regions": own}, open(f"{RD}/seams/ownership_city.json", "w"), indent=1)
    feats = [{"type":"Feature",
              "properties":{"unit":uid,"file":units[uid]["file"],"year":year,
                            "tier":tf[uid]["tier"],"how":tf[uid]["how"]},
              "geometry":{"type":"Polygon","coordinates":[list(map(list, polys[uid].exterior.coords))]}}
             for uid in units]
    json.dump({"type":"FeatureCollection","features":feats},
              open(f"{RD}/sheets_city.geojson","w"), indent=1)
    import collections
    print(year, "units", len(units), "ownership polys", len(own),
          dict(collections.Counter(v["tier"] for v in tf.values())))

run(1899, "city_network.json", "affine_city_1899.json", "ring_report.json")
run(1912, "network_1912.json", "affine_city_1912.json", "ring_1912_report.json")

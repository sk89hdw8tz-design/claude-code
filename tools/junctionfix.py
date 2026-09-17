#!/usr/bin/env python3
"""Re-own the street intersections where three or four plates meet.

    python3 tools/junctionfix.py --year 1912 --units 7,8,... [--apply] [--side 520]

At a four-plate junction two seams cross inside the roadway, so the
intersection is assembled from four plates: each plate's neatline-trimmed
paper stops part-way across it (grey scanner margin or white canvas shows
where none reaches), and each plate's street-width label ("70'") near its
edge survives, so labels double. This tool gives each junction square to
as few plates as possible: the plate whose paper covers the most of the
square takes all of it that its paper maps; what remains goes to the next
plate, and so on. Geometry only; furniture boxes stay cut through
reciplib.footprint(). Writes seams/ownership_city.json in place (--apply)
after backing up the previous file, and a junction report to qc/junctions/.
"""
import argparse, json, os, sys, copy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe
from shapely.geometry import Polygon, Point, box, MultiPolygon
from shapely.ops import unary_union

def regions_by_unit(own):
    d = {}
    for r in own["regions"]:
        d.setdefault(str(r.get("unit", r.get("sheet"))), []).append(r)
    return d

def poly_of(r):
    pm = r["polygon_mosaic"]
    return Polygon(pm["exterior"], pm.get("interiors") or None).buffer(0)

def find_junctions(U, units, snap=200, reach=60):
    pts = []
    for i, a in enumerate(units):
        for b in units[i + 1:]:
            inter = U[a].buffer(20).intersection(U[b].buffer(20))
            if inter.is_empty:
                continue
            for g in (inter.geoms if inter.geom_type != "Polygon" else [inter]):
                bb = g.bounds
                for p in ((bb[0], bb[1]), (bb[2], bb[3]), (bb[0], bb[3]), (bb[2], bb[1])):
                    P = Point(p); near = tuple(sorted(u for u in units if U[u].distance(P) < reach))
                    if len(near) >= 3:
                        pts.append((round(p[0] / snap) * snap, round(p[1] / snap) * snap, near))
    J = {}
    for x, y, n in pts:
        J.setdefault(n, []).append((x, y))
    # merge junctions whose unit sets nest and whose points coincide
    out = []
    for n, ps in sorted(J.items(), key=lambda kv: -len(kv[0])):
        x = float(np.median([p[0] for p in ps])); y = float(np.median([p[1] for p in ps]))
        if any(set(n) <= set(m) and abs(x - ox) < 400 and abs(y - oy) < 400 for m, ox, oy in out):
            continue
        out.append((n, x, y))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1912"])
    ap.add_argument("--units", required=True, help="comma list; junctions among these units only")
    ap.add_argument("--side", type=float, default=520.0, help="junction square side, mosaic px")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    r = Recipe(int(a.year))
    op = os.path.join(r.dir, "seams", "ownership_city.json")
    own = json.load(open(op))
    R = regions_by_unit(own)
    U = {u: unary_union([poly_of(x) for x in v]) for u, v in R.items()}
    units = [u for u in a.units.split(",") if u in U]
    feet = {u: r.footprint(u, furniture=True) for u in U}
    js = find_junctions(U, units)
    report = []; touched_all = set()
    new_regions = {u: U[u] for u in U}
    for n, x, y in js:
        Q = box(x - a.side / 2, y - a.side / 2, x + a.side / 2, y + a.side / 2)
        # refine the centre: centroid of the multi-plate contact inside Q
        # every plate whose paper reaches the square is a candidate, and every
        # plate whose region touches it gives the square up
        cands = [u for u in U if feet[u].intersects(Q)]
        holders = [u for u in U if new_regions[u].intersects(Q)]
        cover = sorted(((feet[u].intersection(Q).area / Q.area, u) for u in cands), reverse=True)
        remaining = Q
        assign = []
        for frac, u in cover:
            take = remaining.intersection(feet[u])
            if take.area < 400:
                continue
            assign.append((u, take)); remaining = remaining.difference(take)
            if remaining.area < 400:
                break
        before = {u: round(new_regions[u].intersection(Q).area / Q.area, 2) for u in holders}
        for u in holders:
            new_regions[u] = new_regions[u].difference(Q)
        n = tuple(sorted(set(n) | set(holders) | {u for u, _ in assign}))
        for u, take in assign:
            new_regions[u] = unary_union([new_regions[u], take])
        touched_all.update(n)
        report.append({"units": list(n), "centre": [round(x), round(y)], "paper_cover": {u: round(f, 2) for f, u in cover},
                       "owned_before": before, "owned_after": {u: round(t.area / Q.area, 2) for u, t in assign},
                       "unpapered_px2": round(remaining.area)})
    # write
    n_before = len(own["regions"])
    if a.apply:
        bak = op.replace(".json", ".pre_junctionfix.json")
        if not os.path.exists(bak):
            json.dump(own, open(bak, "w"), indent=1)
        regs = []
        touched = touched_all
        for reg in own["regions"]:
            u = str(reg.get("unit", reg.get("sheet")))
            if u not in touched:
                regs.append(reg)
        for u in sorted(touched):
            g = new_regions[u]
            for piece in (g.geoms if g.geom_type != "Polygon" else [g]):
                if piece.is_empty or piece.area < 500:
                    continue
                proto = copy.deepcopy(R[u][0]); proto["unit"] = u
                proto["polygon_mosaic"] = {"exterior": [[round(px, 1), round(py, 1)] for px, py in piece.exterior.coords],
                                           "interiors": [[[round(px, 1), round(py, 1)] for px, py in i.coords] for i in piece.interiors]}
                proto["source"] = (proto.get("source", "") + " | junctionfix").strip(" |")
                regs.append(proto)
        own["regions"] = regs
        own["note"] = (own.get("note", "") + f" | tools/junctionfix.py: {len(js)} junctions re-owned (square {a.side:.0f} px, fewest plates whose paper covers)").strip(" |")
        json.dump(own, open(op, "w"), indent=1)
    od = os.path.join(r.dir, "qc", "junctions"); os.makedirs(od, exist_ok=True)
    json.dump({"side": a.side, "applied": a.apply, "junctions": report}, open(os.path.join(od, "junctionfix_report.json"), "w"), indent=1)
    print(f"{len(js)} junctions; regions {n_before} -> {len(own['regions'])}; applied={a.apply}")
    for j in report:
        print(j["units"], j["centre"], "after:", j["owned_after"], "unpapered", j["unpapered_px2"])

if __name__ == "__main__":
    main()

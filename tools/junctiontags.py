#!/usr/bin/env python3
"""Decide, per street-end cluster, which plate keeps its edge width tag.

    python3 tools/junctiontags.py --year 1912 [--apply]

Every plate prints a `70'`/`80'` width tag where a street leaves it, so at a
seam two (at a four-plate junction up to four) tags sit within a few feet
of each other. Cutting a tag as furniture only helps if the plate that
fills the hole has no tag of its own there; otherwise the neighbour's tag
appears in the hole (an island) or, if every plate's tag is cut, nothing
maps the hole and the renderer paints it grey. So: cluster the tag boxes
(`kind == "edge width tag"` in units.json) that lie within CLUSTER px of
each other across plates; in each cluster the plate that owns the most of
the cluster's ground KEEPS its tags (cut=False) and the other plates' tags
are cut where the keeper's paper (furniture-free) covers them. A lone tag
(no neighbour tag nearby) is cut where a neighbour maps it with its own
furniture already removed.
"""
import argparse, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe
from shapely.geometry import box
from shapely.affinity import affine_transform
from shapely.ops import unary_union

CLUSTER = 700.0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1912"])
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    r = Recipe(int(a.year))
    up = os.path.join(r.dir, "units.json"); U = json.load(open(up))
    own = {}
    for u, P in r.ownership_shapes():
        own.setdefault(u, []).append(P)
    own = {u: unary_union(v) for u, v in own.items()}
    tags = []
    for u, unit in U["units"].items():
        M, t = r.sheet_matrix(u)
        for i, f in enumerate(unit.get("furniture_native", [])):
            if f.get("kind") != "edge width tag":
                continue
            q = affine_transform(box(*f["box"]), [M[0,0], M[0,1], M[1,0], M[1,1], t[0], t[1]])
            tags.append({"u": u, "i": i, "q": q, "c": np.array(q.centroid.coords[0])})
    # cluster by centre distance (single linkage)
    n = len(tags); parent = list(range(n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for i in range(n):
        for j in range(i + 1, n):
            if tags[i]["u"] != tags[j]["u"] and np.linalg.norm(tags[i]["c"] - tags[j]["c"]) < CLUSTER:
                parent[find(i)] = find(j)
    clusters = {}
    for i in range(n):
        clusters.setdefault(find(i), []).append(i)
    feet_nf = {u: r.footprint(u, furniture=False) for u in U["units"]}
    stats = {"keep": 0, "cut": 0, "lone_cut": 0, "lone_keep": 0}
    decisions = []
    for members in clusters.values():
        units = sorted({tags[i]["u"] for i in members})
        hull = unary_union([tags[i]["q"] for i in members]).convex_hull.buffer(150)
        if len(units) == 1:
            for i in members:
                tg = tags[i]; others = [v for v in U["units"] if v != tg["u"] and feet_nf[v].intersects(tg["q"])]
                cov = 0.0
                if others:
                    cov = unary_union([r.footprint(v, furniture=True) for v in others]).intersection(tg["q"]).area / tg["q"].area
                cut = cov >= 0.98
                U["units"][tg["u"]]["furniture_native"][tg["i"]].update({"cut": bool(cut), "covered_fraction": round(cov, 3), "cluster": "lone"})
                stats["lone_cut" if cut else "lone_keep"] += 1
            continue
        share = {u: own.get(u, box(0,0,0,0)).intersection(hull).area for u in units}
        keeper = max(share, key=share.get)
        for i in members:
            tg = tags[i]
            if tg["u"] == keeper:
                U["units"][tg["u"]]["furniture_native"][tg["i"]].update({"cut": False, "cluster": f"keeper of {'+'.join(units)}"}); stats["keep"] += 1
            else:
                cov = feet_nf[keeper].intersection(tg["q"]).area / tg["q"].area
                cut = cov >= 0.98
                U["units"][tg["u"]]["furniture_native"][tg["i"]].update({"cut": bool(cut), "covered_fraction": round(cov, 3), "cluster": f"{keeper} keeps of {'+'.join(units)}"})
                stats["cut" if cut else "keep"] += 1
        decisions.append({"units": units, "keeper": keeper, "centre": [round(float(v)) for v in hull.centroid.coords[0]]})
    print(f"{n} tags in {len(clusters)} clusters; {stats}")
    if a.apply:
        json.dump(U, open(up, "w"), indent=1)
        od = os.path.join(r.dir, "qc", "junctions"); os.makedirs(od, exist_ok=True)
        json.dump({"clusters": decisions, "stats": stats}, open(os.path.join(od, "junctiontags.json"), "w"), indent=1)
        print("applied")

if __name__ == "__main__":
    main()

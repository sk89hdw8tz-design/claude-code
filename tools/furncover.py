#!/usr/bin/env python3
"""Decide which furniture boxes may be cut from a unit's footprint.

    python3 tools/furncover.py --year 1912 [--apply]

A furniture box (a plate's title, its numeral, its 'Scale of Feet' legend)
is cut out so that a neighbour mapping the same ground owns it and the
marking never prints inside the city. That only works if a neighbour maps
essentially ALL of the box: where it maps part, the rest falls back to the
plate's own scan and the result is a patch of neighbour paper beside half a
legend -- worse than either alternative. So each box is marked
`cut: true` only when other units' trimmed footprints cover at least
COVER of it; otherwise `cut: false` and the plate keeps its own paper, as
the accepted 27x40 master does with its scale bars and compass roses.

That independent test cannot see a CYCLE. Three plates' margins can meet at
one point, each declaring its own furniture there, and each blanking the
ground its neighbours would need: a box is kept because its neighbours do
not supply it, and those neighbours' boxes are cut because it does. Wave 4
found exactly one (`qc/wave4/proposal_cuts.md` §2): plate 63's 257,000 px2
"Scale of Feet" legend prints in the 33rd St roadway at 0.830 coverage,
while plates 70's and 71's own title rectangles -- declared BOTH as
`furniture_native` and as `exclude_native`, so `footprint_native` subtracts
them whatever their `cut` flag says -- are cut because 63 supplies them.
The cycle resolves in favour of the LARGEST box, which is backwards.

So a second pass, after the independent one, finds those cycles: for a kept
box, the ground its neighbours fail to supply is compared against those
neighbours' UNTRIMMED footprints, and where the shortfall is exactly a
neighbour's own furniture box (declared as an exclusion) and that box is
itself cut because this plate supplies it, the boxes are one cycle. Where no
plate outside the cycle maps the contested ground, exactly ONE box is kept --
the SMALLEST by mosaic area, i.e. the least furniture printed over mapped
ground -- and the rest are cut; the kept box's unit also drops the
`exclude_native` twin of that box, so its own paper supplies the others.
COVER is not touched: the threshold was never the thing at fault.
"""
import argparse
import json
import os
import sys

COVER = 0.98


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=1912)
    ap.add_argument("--cover", type=float, default=COVER)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from reciplib import Recipe
    from shapely.geometry import box as sbox
    from shapely.ops import unary_union
    from shapely.affinity import affine_transform
    import numpy as np
    r = Recipe(a.year)
    doc = json.load(open(os.path.join(r.dir, "units.json")))
    # every unit's footprint with furniture kept (what it could supply)
    foot = {}
    for u in r.units:
        try:
            foot[u] = r.footprint(u, furniture=False).buffer(0)
        except Exception:
            pass
    # the same ground with NO exclude_native subtracted: what a plate's paper
    # holds before its own inset frames and title rectangles are cut away.
    # A cycle is only a cycle when the shortfall is one of those exclusions.
    def raw_mosaic(u):
        from shapely.geometry import Polygon, box as bx
        ud = r.units[str(u)]
        g = (Polygon(ud["region_native"]).buffer(0) if ud.get("region_native")
             else bx(*ud["extent"]))
        M, t = r.sheet_matrix(u)
        return affine_transform(g, [M[0, 0], M[0, 1], M[1, 0], M[1, 1], t[0], t[1]])
    raw = {u: raw_mosaic(u) for u in r.units}

    def related(u, v):
        return (u == v or r.units[v].get("panel_of") == u
                or r.units[u].get("panel_of") == v)

    def mosaic_box(u, b, grow=0.0):
        M, t = r.sheet_matrix(u)
        return affine_transform(sbox(b[0] - grow, b[1] - grow, b[2] + grow, b[3] + grow),
                                [M[0, 0], M[0, 1], M[1, 0], M[1, 1], t[0], t[1]])

    def score(exclude_dropped=()):
        """Coverage of every furniture box. `exclude_dropped` names units whose
        exclude_native twins of their own kept boxes are treated as absent."""
        fp = {}
        for u in r.units:
            try:
                g = r.footprint(u, furniture=False).buffer(0)
            except Exception:
                continue
            if u in exclude_dropped:
                g = g.union(exclude_dropped[u]).buffer(0)
            fp[u] = g
        out = {}
        for u, ud in doc["units"].items():
            for i, f in enumerate(ud.get("furniture_native") or []):
                g = mosaic_box(u, f["box"])
                near = {v: o.intersection(g) for v, o in fp.items()
                        if not related(u, v) and o.intersects(g)}
                cov = unary_union(list(near.values())).area / g.area if near else 0.0
                D = g.difference(unary_union(list(near.values()))) if near else g
                out[(u, i)] = {"g": g, "cov": cov, "area": g.area,
                               "by": {v: p.area / g.area for v, p in near.items() if p.area > 0},
                               "deficit": D}
        return out

    sc = score()
    for (u, i), d in sc.items():
        f = doc["units"][u]["furniture_native"][i]
        f["cut"] = bool(d["cov"] >= a.cover)
        f["covered_fraction"] = round(d["cov"], 3)

    # --- cycle pass -------------------------------------------------------
    cycles = []
    for (u, i), d in sorted(sc.items()):
        if d["cov"] >= a.cover or d["deficit"].is_empty:
            continue
        D = d["deficit"]
        twins, outside = [], False
        for v in r.units:
            if related(u, v) or not raw[v].intersects(D):
                continue
            blocked = raw[v].intersection(D)
            if blocked.area < 0.01 * d["area"]:
                continue
            hit = None
            for j, g2 in enumerate(r.units[v].get("furniture_native") or []):
                if mosaic_box(v, g2["box"], 6.0).intersection(blocked).area > 0.8 * blocked.area:
                    hit = j
                    break
            if hit is None or sc[(v, hit)]["by"].get(u, 0.0) <= 0.0:
                outside = True          # a plate outside the cycle maps this ground
                break
            twins.append((v, hit))
        if outside or not twins:
            continue
        cycles.append([(u, i)] + twins)

    # cycles that share a box are one cycle
    comps = []
    for S in cycles:
        hit = [c for c in comps if set(c) & set(S)]
        merged = set(S)
        for c in hit:
            merged |= set(c)
            comps.remove(c)
        comps.append(sorted(merged))

    def exclusion_twins(v, box, grow=6.0):
        """(kept, dropped) exclude_native polygons of unit v against one of its
        own furniture boxes. A plate that declares the same rectangle twice --
        once as furniture, once as an exclusion -- blanks that ground for its
        neighbours whatever the `cut` flag says, which is the mechanism behind
        every cycle here. Inside a resolved cycle the twin is redundant: if the
        box is cut, `footprint_native` removes the same rectangle (grown 6 px)
        anyway; if it is the kept box, the plate is supposed to supply that
        paper to the others."""
        from shapely.geometry import Polygon
        kb = mosaic_box(v, box, grow)
        M, t = r.sheet_matrix(v)
        A = [M[0, 0], M[0, 1], M[1, 0], M[1, 1], t[0], t[1]]
        keep_ex, dropped = [], []
        for ex in r.units[v].get("exclude_native") or []:
            gm = affine_transform(Polygon(ex).buffer(0), A)
            (dropped if gm.intersection(kb).area > 0.9 * gm.area else keep_ex).append((ex, gm))
        return keep_ex, dropped

    def apply_cycle(S):
        keep = min(S, key=lambda k: sc[k]["area"])
        out = {}
        for v, j in S:
            doc["units"][v]["furniture_native"][j]["cut"] = ((v, j) != keep)
            out[(v, j)] = exclusion_twins(v, doc["units"][v]["furniture_native"][j]["box"])
        return keep, out

    # A cycle is only resolved if the resolution WORKS: every box it cuts must
    # then be supplied to at least COVER by the kept box's released paper.
    # Otherwise the independent verdict stands (half a legend beside a patch of
    # neighbour paper is worse than either alternative).
    live, drop, resolved = list(comps), {}, []
    for _ in range(4):
        drop, plan = {}, {}
        for S in live:
            keep, tw = apply_cycle(S)
            plan[tuple(S)] = (keep, tw)
            for (v, j), (_, dropped) in tw.items():
                if dropped:
                    drop[v] = unary_union([gm for _, gm in dropped] +
                                          ([drop[v]] if v in drop else []))
        sc2 = score(exclude_dropped=drop) if drop else score()
        bad = [S for S in live
               if any(sc2[k]["cov"] < a.cover for k in S if k != plan[tuple(S)][0])]
        if not bad:
            break
        for S in bad:                      # revert: the independent verdict stands
            live.remove(S)
            for v, j in S:
                f = doc["units"][v]["furniture_native"][j]
                f["cut"] = bool(sc[(v, j)]["cov"] >= a.cover)
    for S in live:
        keep, tw = plan[tuple(S)]
        for v, j in S:
            f = doc["units"][v]["furniture_native"][j]
            f["cycle"] = (("kept: the smallest box of the %d-box furniture cycle %s; its paper "
                           "supplies the others" % (len(S), " ".join("%s[%d]" % k for k in S)))
                          if (v, j) == keep else
                          ("cut: %s[%d] is the smallest box of the %d-box furniture cycle %s and "
                           "keeps its paper" % (keep[0], keep[1], len(S),
                                                " ".join("%s[%d]" % k for k in S))))
            keep_ex, dropped = tw[(v, j)]
            if dropped:
                doc["units"][v]["exclude_native"] = [e for e, _ in keep_ex]
                doc["units"][v]["exclude_dropped_note"] = (
                    "the exclude_native twin of furniture box %d was dropped by "
                    "tools/furncover.py's cycle pass (cycle %s): the same rectangle was declared "
                    "both as furniture and as an exclusion, which blanked the ground the cycle's "
                    "other plates need" % (j, " ".join("%s[%d]" % k for k in S)))
        resolved.append((S, keep))
    if drop:
        for (u, i), d in score(exclude_dropped=drop).items():
            doc["units"][u]["furniture_native"][i]["covered_fraction"] = round(d["cov"], 3)

    stats = {"cut": 0, "kept": 0}
    for u, ud in doc["units"].items():
        for f in ud.get("furniture_native") or []:
            stats["cut" if f["cut"] else "kept"] += 1
    print(f"{stats['cut']} boxes a neighbour can supply in full (cut), "
          f"{stats['kept']} kept on the plate's own paper")
    for S, keep in resolved:
        print("  cycle %s -> keep %s[%d] (%.0f px2), cut %s" % (
            " ".join("%s[%d]" % k for k in S), keep[0], keep[1], sc[keep]["area"],
            " ".join("%s[%d]" % k for k in S if k != keep)))
    if a.apply:
        json.dump(doc, open(os.path.join(r.dir, "units.json"), "w"), indent=1)
        print("applied to units.json")


if __name__ == "__main__":
    main()

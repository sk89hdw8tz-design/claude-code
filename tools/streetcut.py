#!/usr/bin/env python3
"""Cut sheet ownership along street centrelines, as the brief requires.

    python3 tools/streetcut.py --year 1912 [--apply]

Non-negotiable §2.5: "cut seams down street centrelines so no building
footprint is ever split across a seam". Three sources decide where a seam
between two overlapping sheets goes, in order:

  1. a CONTROL on the seam's axis -- the shared corridor an observer named
     and measured on both plates (recipe/controls/): the seam IS that line;
  2. the plates' own LATTICE (tools/faces.py) -- every plate's streets recur
     at the city pitch, so the corridor nearest the middle of the two sheets'
     overlap is read off each plate, mapped through its transform, and the
     seam is the mean of the two readings. The two readings also measure how
     far the pair still disagrees; that residual is reported;
  3. the midpoint of the overlap (corner contacts, or no lattice).

Two things this version does differently from the first, both from HQ-19:

  * A sheet is trimmed ONLY inside its overlap with each neighbour. The first
    version intersected whole half-planes, so a diagonal neighbour's cut
    reached across the entire sheet and stranded ground (the 57|63 white band
    was exactly that: an inlet of unclaimed ground between two half-planes
    that did not meet, open to the exterior so the hole audit never saw it).
    Now region(u) = base(u) - U_v (base(u) n base(v) n v's side), which can
    only remove ground the neighbour keeps.
  * The frozen downtown core keeps its accepted min-ink DP masks
    (seams/masks.json, the 27x40 master's own cuts) as its base; the first
    version had silently replaced them with bisector boxes. Ring neighbours
    are cut against the core exactly as against each other.

Geometry only; no pixel is altered.
"""
import argparse
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe, px_per_ft          # noqa: E402
from faces import lattice_all                    # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIG = 1e7
MIN_OVERLAP = 2500.0          # px^2; below this two sheets merely touch
BAND_FRACTION = 0.6           # overlap spanning this much of the shorter
                              # sheet across the seam axis is a true seam


def load_cuts(r):
    """{(a,b): {axis: (mosaic_coord, corridor)}} from every accepted control.

    A pair can carry TWO controls: the street it abuts along and, for a
    stacked pair, the avenue it crosses. Both are kept, keyed by axis, and
    the caller asks for the axis the seam's own geometry calls for.
    """
    out = {}
    cdir = os.path.join(r.dir, "controls")
    for f in sorted(os.listdir(cdir)):
        m = re.match(r"pair_([0-9]+[a-z]?)_([0-9]+[a-z]?)(?:_[xy])?\.json$", f)
        if not m:
            continue
        try:
            d = json.load(open(os.path.join(cdir, f)))
        except Exception:
            continue
        if "a_native" not in d or str(d.get("status", "")).upper() != "ACCEPTED":
            continue
        ua, ub = m.group(1).lstrip("0"), m.group(2).lstrip("0")
        if ua not in r.units or ub not in r.units:
            continue
        vert = str(d.get("axis", "")).lower().startswith("av")
        pos = []
        for uid, nat in ((ua, d["a_native"]), (ub, d["b_native"])):
            M, t = r.sheet_matrix(uid)
            e = r.units[uid]["extent"]
            p = M @ (np.array([float(nat), (e[1] + e[3]) / 2]) if vert
                     else np.array([(e[0] + e[2]) / 2, float(nat)])) + t
            pos.append(float(p[0] if vert else p[1]))
        out.setdefault((ua, ub), {})["x" if vert else "y"] = (
            float(np.mean(pos)), d.get("corridor", "?"))
    return out


def half_plane(axis, coord, keep_low):
    from shapely.geometry import box
    if axis == "x":
        return box(-BIG, -BIG, coord, BIG) if keep_low else box(coord, -BIG, BIG, BIG)
    return box(-BIG, -BIG, BIG, coord) if keep_low else box(-BIG, coord, BIG, BIG)


def lattice_coord(r, lat, u, axis, mid_xy):
    """Mosaic coordinate on `axis` of the lattice corridor of unit u nearest
    the mosaic point mid_xy, read through u's transform at that point."""
    L = (lat.get(u) or {}).get(axis)
    if not L or not L.get("faces") or L.get("weak"):
        return None
    M, t = r.sheet_matrix(u)
    Minv = np.linalg.inv(M)
    nat = Minv @ (np.array(mid_xy, float) - t)
    k = 0 if axis == "x" else 1
    best = None
    # only corridors whose faces were measured on the plate: the corridor
    # extrapolated one pitch past the chain was 100 px off on sheet 71
    for c in [(fa + fb) / 2.0 for fa, fb in L["faces"]]:
        q = nat.copy()
        q[k] = c
        p = M @ q + t
        if best is None or abs(p[k] - mid_xy[k]) < abs(best - mid_xy[k]):
            best = float(p[k])
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1912"])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--debug-unit", default=None)
    a = ap.parse_args()

    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    r = Recipe(int(a.year))
    ppf = px_per_ft(r)
    cuts = load_cuts(r)
    lat = lattice_all(r)
    print(f"{sum(len(v) for v in cuts.values())} accepted controls over "
          f"{len(cuts)} pairs; lattices for "
          f"{sum(1 for u in lat if lat[u].get('y') and lat[u].get('x'))} units",
          flush=True)

    def foot(u):
        e = r.units[u]["extent"]
        M, t = r.sheet_matrix(u)
        return Polygon([tuple(M @ np.array(c, float) + t) for c in
                        ((e[0], e[1]), (e[2], e[1]), (e[2], e[3]), (e[0], e[3]))])

    feet = {u: foot(u) for u in r.units}
    cen = {u: np.array([feet[u].centroid.x, feet[u].centroid.y]) for u in feet}

    # the accepted core: its own DP cuts are the base, not the paper quad
    core = {}
    mp = os.path.join(r.dir, "seams", "masks.json")
    if os.path.exists(mp):
        for reg in json.load(open(mp))["regions"]:
            u = str(reg.get("unit", reg.get("sheet")))
            if u in feet:
                core[u] = Polygon(reg["polygon_mosaic"]["exterior"]).buffer(0)
    base = {u: core.get(u, feet[u]) for u in feet}
    print(f"core base from masks.json: {sorted(core, key=int)}", flush=True)

    units = sorted(feet, key=lambda k: int("".join(c for c in k if c.isdigit())))
    seams, loss = [], {u: [] for u in units}
    stats = {"control": 0, "lattice": 0, "midpoint": 0, "core-core": 0}
    for i, u in enumerate(units):
        for v in units[i + 1:]:
            if not base[u].intersects(base[v]):
                continue
            O = base[u].intersection(base[v])
            if O.area < MIN_OVERLAP:
                continue
            if u in core and v in core:
                stats["core-core"] += 1       # already partitioned by the master
                continue
            d = cen[v] - cen[u]
            axis = "x" if abs(d[0]) >= abs(d[1]) else "y"
            k = 0 if axis == "x" else 1
            b = O.bounds
            span = (b[3] - b[1]) if axis == "x" else (b[2] - b[0])
            across = min(feet[u].bounds[3] - feet[u].bounds[1],
                         feet[v].bounds[3] - feet[v].bounds[1]) if axis == "x" else \
                     min(feet[u].bounds[2] - feet[u].bounds[0],
                         feet[v].bounds[2] - feet[v].bounds[0])
            band = span >= BAND_FRACTION * across
            mid = np.array([(b[0] + b[2]) / 2, (b[1] + b[3]) / 2])
            key = (u, v) if (u, v) in cuts else ((v, u) if (v, u) in cuts else None)
            got = cuts[key].get(axis) if key else None
            how, corridor, resid = None, None, None
            if got:
                coord, corridor = got
                how = "control"
            else:
                cu = lattice_coord(r, lat, u, axis, mid) if band else None
                cv = lattice_coord(r, lat, v, axis, mid) if band else None
                if cu is not None and cv is not None:
                    coord = (cu + cv) / 2.0
                    resid = abs(cu - cv)
                    how = "lattice"
                else:
                    coord = float(mid[k])
                    how = "midpoint"
            stats[how] += 1
            lower = u if cen[u][k] < cen[v][k] else v
            upper = v if lower == u else u
            loss[lower].append(O.intersection(half_plane(axis, coord, False)))
            loss[upper].append(O.intersection(half_plane(axis, coord, True)))
            seams.append({"pair": [u, v], "axis": axis, "coord": round(coord, 2),
                          "how": how, "corridor": corridor, "kind": "band" if band else "corner",
                          "overlap_px2": round(O.area), "span_px": round(span),
                          "lattice_disagreement_px": None if resid is None else round(resid, 1),
                          "lattice_disagreement_ft": None if resid is None else round(resid / ppf, 1)})

    regions, dropped = {}, []
    for u in units:
        g = base[u]
        if u == a.debug_unit:
            print(f"debug {u}: base {g.area:,.0f}; losses "
                  f"{[round(l.area) for l in loss[u]]}")
        if loss[u]:
            g = g.difference(unary_union(loss[u]))
            if u == a.debug_unit:
                print(f"debug {u}: after difference {g.geom_type} {g.area:,.0f}")
        if g.is_empty:
            continue
        # a difference can leave a notch attached to the ring at a single
        # point, which GEOS represents as a hole touching the exterior; the
        # export keeps only exteriors, so that notch would silently come
        # back as double ownership (77|84, 1.9M px2, on the first run). A
        # 1 px opening turns every such contact into a proper notch.
        g = g.buffer(-1.0).buffer(1.0)
        if g.geom_type != "Polygon":
            parts = sorted(g.geoms, key=lambda p: -p.area)
            g = parts[0]
            dropped += [(u, round(p.area)) for p in parts[1:] if p.area > MIN_OVERLAP]
        if g.interiors:
            g = Polygon(g.exterior)
        assert g.is_valid, u
        regions[u] = g

    print(f"seams: {stats['control']} on a control, {stats['lattice']} on the "
          f"plates' lattice, {stats['midpoint']} at the overlap midpoint "
          f"(corner contacts); {stats['core-core']} core-core pairs kept the "
          f"master's cuts", flush=True)
    res = [s["lattice_disagreement_ft"] for s in seams if s["lattice_disagreement_ft"] is not None]
    if res:
        print(f"lattice seams: the two plates' readings of the shared corridor "
              f"disagree by median {np.median(res):.1f} ft, 90th "
              f"{np.percentile(res, 90):.1f}, max {max(res):.1f}")
        for s in sorted(seams, key=lambda s: -(s["lattice_disagreement_ft"] or 0))[:8]:
            if s["lattice_disagreement_ft"]:
                print(f"    {s['pair'][0]}|{s['pair'][1]} {s['axis']} "
                      f"{s['lattice_disagreement_ft']:.0f} ft")
    if dropped:
        print(f"detached slivers dropped (become gaps for fillgaps): {dropped}")

    un = unary_union(list(regions.values()))
    s = sum(g.area for g in regions.values())
    holes = sum(1 for p in getattr(un, "geoms", [un]) for _ in p.interiors)
    print(f"{len(regions)} regions; union {un.area:,.0f} px2, "
          f"overlap {s-un.area:,.0f} px2 ({(s-un.area)/un.area*100:.4f}%), "
          f"pieces {len(getattr(un,'geoms',[un]))}, interior rings {holes}")

    doc = {"convention": "polygon_mosaic.exterior in mosaic pixels",
           "generated_by": "tools/streetcut.py",
           "note": ("core = the master's DP masks; ring seams on the control's "
                    "corridor, else on the plates' lattice corridor, else the "
                    "overlap midpoint; each sheet trimmed only inside its "
                    "overlap with the neighbour (§2.5)"),
           "seams": seams,
           "regions": [{"unit": u,
                        "source": "master DP mask" if u in core else "street-centreline cut",
                        "polygon_mosaic": {"exterior":
                            [[round(x, 3), round(y, 3)] for x, y in g.exterior.coords]}}
                       for u, g in sorted(regions.items(), key=lambda kv: int(kv[0]))]}
    p = os.path.join(r.dir, "seams", "ownership_streetcut.json")
    json.dump(doc, open(p, "w"), indent=1)
    print(f"wrote {p}")
    if a.apply:
        tgt = os.path.join(r.dir, "seams", "ownership_city.json")
        json.dump(doc, open(tgt, "w"), indent=1)
        print(f"applied to {tgt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

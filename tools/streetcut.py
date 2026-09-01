#!/usr/bin/env python3
"""Cut sheet ownership along street centrelines, as the brief requires.

    python3 tools/streetcut.py --year 1912 [--apply]

Non-negotiable §2.5: "cut seams down street centrelines so no building
footprint is ever split across a seam". The Voronoi re-cut that followed the
control solve does not do that — its boundaries are bisectors between sheet
centres and can run straight through a building.

The controls already say where to cut. Each one names the corridor two
adjacent sheets share and gives its position on both, so the seam between
that pair IS that corridor's centreline. So a sheet's region is simply the
intersection of the half-planes its controls put it on, clipped to the ground
it actually covers:

    region(u) = footprint(u)  ∩  { half-plane from each control on u }
                              ∩  { bisector for neighbours with no control }

That is convex, so every region is one clean ring, every boundary between two
controlled neighbours lies on a street or avenue centreline, and buildings —
which sit inside blocks, between corridors — are never split.

A single straight line per named street is deliberately NOT used: Galveston's
grid bends about 2 degrees to the south, so one street's mosaic coordinate
varies along its length. Each pair's own reading is used instead.

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

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Snapping an uncontrolled seam to the nearest grid centreline is off by
# default: it is a NEGATIVE RESULT, kept because the idea is a reasonable one
# to have and the measurement is worth not repeating. Every setting tried made
# the tiling worse -- 0.1 blocks gave 3 disjoint pieces, 0.2 and 0.3 gave 8,
# against 2 with plain bisectors -- because a seam that moves to reach a
# corridor trims the sheet away from a DIFFERENT neighbour's seam, and the
# east-end sheets (17-32) come apart. Constraining the snap to fall between
# the two sheet centres changed nothing; they already did.
SNAP_LIMIT_BLOCKS = 0.0
BIG = 1e7


def load_cuts(r):
    """{(a,b): {axis: (mosaic_coord, corridor)}} from every accepted control.

    A pair can now carry TWO controls: the street it abuts along and, for a
    stacked pair, the avenue it crosses. Keying only by pair let the second
    overwrite the first, and since a stacked pair's avenue control is on the
    wrong axis to cut with, the good street cut was lost and the seam fell
    back to a bisector. Keep both and let the caller ask for the axis the
    seam's own geometry calls for.
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


def grid_lines(r):
    """{axis: sorted mosaic coordinates of every corridor the grid knows}.

    Pairs with no control still need a seam, and a bisector between two sheet
    centres is an arbitrary line that can run through a building -- exactly
    what the brief forbids. Now that the city-wide grid is solved, the nearest
    real corridor is a better seam than the midpoint, and it is a centreline.
    """
    for name in ("grid_city.json", "grid.json"):
        p = os.path.join(r.dir, name)
        if os.path.exists(p):
            g = json.load(open(p))
            break
    else:
        return {"x": [], "y": []}
    return {"x": sorted(float(e["x"]) for e in g.get("avenues", {}).values()),
            "y": sorted(float(e["y"]) for e in g.get("streets", {}).values())}


def snap(lines, axis, coord, limit, lo, hi):
    """Nearest corridor on this axis, if one is within limit AND lies between
    the two sheets' centres.

    The between test is what keeps the tiling whole. Without it a snap can
    move a seam past a small sheet altogether -- the first run of this broke
    the mosaic into 8 pieces. A corridor between the two centres always
    separates them, so it can only trade one legal seam for a better-placed
    one.
    """
    ls = [v for v in (lines.get(axis) or []) if lo < v < hi]
    if not ls:
        return None
    best = min(ls, key=lambda v: abs(v - coord))
    return best if abs(best - coord) <= limit else None


def half_plane(axis, coord, keep_low):
    from shapely.geometry import box
    if axis == "x":
        return box(-BIG, -BIG, coord, BIG) if keep_low else box(coord, -BIG, BIG, BIG)
    return box(-BIG, -BIG, BIG, coord) if keep_low else box(-BIG, coord, BIG, BIG)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1912", "1899"])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--snap-blocks", type=float, default=SNAP_LIMIT_BLOCKS,
                    help="how far, in avenue blocks, a seam with no control "
                         "may move to land on a grid centreline (0 disables)")
    a = ap.parse_args()

    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    r = Recipe(int(a.year))
    ppf = px_per_ft(r)
    cuts = load_cuts(r)
    print(f"{sum(len(v) for v in cuts.values())} accepted controls over "
          f"{len(cuts)} pairs "
          f"({sum(1 for v in cuts.values() if 'x' in v)} with an avenue, "
          f"{sum(1 for v in cuts.values() if 'y' in v)} with a street)",
          flush=True)

    def foot(u):
        e = r.units[u]["extent"]
        M, t = r.sheet_matrix(u)
        return Polygon([tuple(M @ np.array(c, float) + t) for c in
                        ((e[0], e[1]), (e[2], e[1]), (e[2], e[3]), (e[0], e[3]))])

    feet = {u: foot(u) for u in r.units}
    cen = {u: np.array([feet[u].centroid.x, feet[u].centroid.y]) for u in feet}

    lines = grid_lines(r)
    # half a block: far enough to reach the corridor a bisector lands beside,
    # near enough that the seam stays between the same two block faces
    SNAP_LIMIT = a.snap_blocks * 350.0 * ppf
    print(f"grid corridors available: {len(lines['x'])} avenue, "
          f"{len(lines['y'])} street", flush=True)
    regions, stats = {}, {"control": 0, "bisector": 0, "snapped": 0}
    for u in feet:
        g = feet[u]
        for v in feet:
            if v == u or not feet[u].intersects(feet[v]):
                continue
            # the cut's ORIENTATION comes from how the two sheets are stacked,
            # not from whichever axis their control happens to be on. Diagonal
            # neighbours (e.g. 81 spans streets 36-39, 89 spans 39-42) often
            # share only an avenue; cutting them left/right on that avenue
            # splits a vertical relationship the wrong way and strands ground
            # that neither region then claims.
            d = cen[v] - cen[u]
            want = "x" if abs(d[0]) >= abs(d[1]) else "y"
            key = (u, v) if (u, v) in cuts else ((v, u) if (v, u) in cuts else None)
            got = cuts[key].get(want) if key else None
            if got:
                axis, (coord, _corr) = want, got
                k = 0 if axis == "x" else 1
                # sides must be assigned by which sheet lies lower on this axis,
                # NOT by comparing each centre to the line: a corridor at the far
                # edge of one sheet can leave both centres on the same side, and
                # both would then keep the same half-plane and overlap
                g = g.intersection(half_plane(axis, coord, cen[u][k] < cen[v][k]))
                stats["control"] += 1
            else:
                # no control for this neighbour. Snap the seam to the nearest
                # corridor the city grid knows rather than cutting on the
                # bare midpoint: it keeps the seam on a centreline, and the
                # midpoint against a diagonal neighbour trims deep enough to
                # strand ground inside a sheet -- 11 acres inside sheet 85 and
                # 8 inside sheet 69 on the first run of this.
                mid = (cen[u] + cen[v]) / 2
                axis = want
                k = 0 if axis == "x" else 1
                lo, hi = sorted((cen[u][k], cen[v][k]))
                coord = snap(lines, axis, mid[k], SNAP_LIMIT, lo, hi)
                if coord is None:
                    coord = mid[k]
                    stats["bisector"] += 1
                else:
                    stats["snapped"] += 1
                g = g.intersection(half_plane(axis, coord, cen[u][k] < coord))
            if g.is_empty:
                break
        if not g.is_empty:
            if g.geom_type != "Polygon":
                g = max(g.geoms, key=lambda p: p.area)
            regions[u] = g
    print(f"boundaries: {stats['control']//2} from controls, "
          f"{stats['snapped']//2} snapped to a grid corridor, "
          f"{stats['bisector']//2} from bisectors (no corridor near enough)",
          flush=True)

    un = unary_union(list(regions.values()))
    s = sum(g.area for g in regions.values())
    holes = sum(1 for p in getattr(un, "geoms", [un]) for _ in p.interiors)
    print(f"{len(regions)} regions; union {un.area:,.0f} px2, "
          f"overlap {s-un.area:,.0f} px2 ({(s-un.area)/un.area*100:.4f}%), "
          f"pieces {len(getattr(un,'geoms',[un]))}, interior rings {holes}")

    doc = {"convention": "polygon_mosaic.exterior in mosaic pixels",
           "generated_by": "tools/streetcut.py",
           "note": ("seams cut on the shared street/avenue centreline named by "
                    "each pair's control (§2.5); bisector only where a pair has "
                    "no control"),
           "regions": [{"unit": u,
                        "source": "street-centreline cut",
                        "polygon_mosaic": {"exterior":
                            [[round(x, 3), round(y, 3)] for x, y in g.exterior.coords]}}
                       for u, g in sorted(regions.items(), key=lambda kv: int(kv[0]))]}
    p = os.path.join(r.dir, "seams", "ownership_streetcut.json")
    json.dump(doc, open(p, "w"), indent=1)
    print(f"wrote {p}")
    if a.apply:
        import shutil
        tgt = os.path.join(r.dir, "seams", "ownership_city.json")
        if not os.path.exists(tgt + ".pre_streetcut"):
            shutil.copyfile(tgt, tgt + ".pre_streetcut")
        json.dump(doc, open(tgt, "w"), indent=1)
        print(f"applied to {tgt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Find the pairs that would tie the sheet rows together in x.

    python3 tools/crossrow.py --year 1912 [--prepare]

Sheets side by side share an avenue, so a row is chained in x. Sheets stacked
one above the other share a street, so a column is chained in y. Nothing in
that pattern ties one row to the next in x — and it shows: the 1912 ring came
out of the control solve with the rows sheared east-west against each other.

A stacked pair also crosses every avenue in its band, so it can be asked for an
avenue instead of a street. This lists the stacked pairs that would join two
x-components, picks a redundant spanning set of them, and with --prepare builds
the agent task for each.
"""
import argparse
import collections
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe, px_per_ft            # noqa: E402
from netsolve import load_controls                # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REDUNDANCY = 2          # controls per component join, so one bad call shows up
MIN_SHARE_FT = 500.0    # x-overlap worth asking about: more than one block


def footprints(r):
    out = {}
    for u in r.units:
        e = r.units[u]["extent"]
        M, t = r.sheet_matrix(u)
        pts = np.array([M @ np.array(c, float) + t for c in
                        ((e[0], e[1]), (e[2], e[1]), (e[2], e[3]), (e[0], e[3]))])
        out[u] = (pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max())
    return out


class DSU:
    def __init__(self, nodes):
        self.p = {n: n for n in nodes}

    def find(self, a):
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        self.p[ra] = rb
        return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1912", "1899"])
    ap.add_argument("--prepare", action="store_true")
    a = ap.parse_args()

    r = Recipe(int(a.year))
    ppf = px_per_ft(r)
    gj = json.load(open(os.path.join(r.dir, "sheets_city.geojson")))
    core = {str(f["properties"]["unit"]) for f in gj["features"]
            if f["properties"].get("tier") == "core"}
    have = {tuple(sorted((c[0], c[1]))) for c in load_controls(r) if c[2] == "x"}

    fp = footprints(r)
    units = sorted(fp)
    dsu = DSU(units)
    anchor = sorted(core)[0] if core else None
    for u in core:
        dsu.union(u, anchor)             # the frozen core is one rigid body in x
    for ua, ub in have:
        dsu.union(ua, ub)
    ncomp = len({dsu.find(u) for u in units})
    print(f"{len(have)} avenue(x) controls -> {ncomp} x-components "
          f"(core frozen as one)")

    # stacked pairs: overlapping in x, one above the other in y
    cand = []
    for i, ua in enumerate(units):
        for ub in units[i + 1:]:
            ax0, ay0, ax1, ay1 = fp[ua]
            bx0, by0, bx1, by1 = fp[ub]
            share = min(ax1, bx1) - max(ax0, bx0)
            if share < MIN_SHARE_FT * ppf:
                continue
            gap = max(ay0, by0) - min(ay1, by1)      # <0 means they overlap in y
            if gap > 200 * ppf:
                continue                              # rows too far apart
            if min(ay1, by1) - max(ay0, by0) > 0.6 * min(ay1 - ay0, by1 - by0):
                continue                              # side by side, not stacked
            if tuple(sorted((ua, ub))) in have:
                continue
            cand.append((-share, ua, ub))
    cand.sort()
    print(f"{len(cand)} stacked pairs share >= {MIN_SHARE_FT:.0f} ft of avenue band")

    # a redundant spanning set: every join made REDUNDANCY times over
    picked, joins = [], collections.Counter()
    for _ in range(REDUNDANCY):
        d2 = DSU(units)
        for u in core:
            d2.union(u, anchor)
        for ua, ub in have:
            d2.union(ua, ub)
        for ua, ub in [(p[1], p[2]) for p in picked]:
            if joins[tuple(sorted((ua, ub)))] > _:
                d2.union(ua, ub)
        for share, ua, ub in cand:
            k = tuple(sorted((ua, ub)))
            if joins[k]:
                continue
            if d2.union(ua, ub):
                picked.append((share, ua, ub))
                joins[k] += 1
    print(f"picked {len(picked)} pairs to commission")
    for share, ua, ub in picked:
        print(f"   {ua:>3}|{ub:<3}  shares {-share/ppf:6.0f} ft of avenue band")

    out = [[ua, ub, round(-s / ppf, 1)] for s, ua, ub in picked]
    p = os.path.join(REPO, "work", "crossrow_pairs.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(out, open(p, "w"), indent=1)
    print(f"wrote {p}")

    if a.prepare:
        import paircrops
        n = 0
        for ua, ub, _ in out:
            if paircrops.build(a.year, ua, ub, force_axis="avenue"):
                n += 1
        print(f"prepared {n} tasks under work/paircrops/*_x/")
    return 0


if __name__ == "__main__":
    sys.exit(main())

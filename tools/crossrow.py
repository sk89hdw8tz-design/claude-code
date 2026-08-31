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

import re

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe, px_per_ft            # noqa: E402
from netsolve import load_controls                # noqa: E402
from paircrops import keymap                      # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REDUNDANCY = 2      # controls per component join, so one bad call shows up
MIN_AVENUES = 2     # avenues both sheets contain: fewer is not worth asking
AVNAME = {Recipe.avenue_slot(n): n for n in
          [c for c in "ABCDEFGHIJKL"] +
          [f"{c}{h}" for c in "MNOPQRST" for h in ("", " 1/2")]}


def coverage(year):
    """Per sheet, from the key maps: the street numbers it spans and the
    avenue slots it contains. The key maps are read off the printed index, so
    unlike the sheets' current footprints they do not depend on the placement
    this is trying to correct — using the footprints here would be circular,
    and it proposed pairs four avenues apart."""
    out = {}
    for u, e in keymap(year).items():
        try:
            st = sorted(int(re.sub(r"[^0-9]", "", str(v))) for v in e["streets"])
            av = {Recipe.avenue_slot(str(v)) for v in e["avenues"]}
        except Exception:
            continue
        if len(st) == 2 and av:
            out[u] = (st, av)
    return out


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

    # stacked pairs, decided from the key maps: different street rows that
    # touch, and at least MIN_AVENUES avenues printed on both sheets
    cov = coverage(a.year)
    print(f"{len(cov)} sheets have a usable key map"
          + (f"; no key map for {sorted(set(units)-set(cov), key=str)}"
             if set(units) - set(cov) else ""))
    cand = []
    for i, ua in enumerate(units):
        for ub in units[i + 1:]:
            if ua not in cov or ub not in cov:
                continue
            (as0, as1), aav = cov[ua]
            (bs0, bs1), bav = cov[ub]
            if (as0, as1) == (bs0, bs1):
                continue                      # same row: already chained in x
            if min(as1, bs1) < max(as0, bs0):
                continue                      # rows do not touch
            shared = aav & bav
            if len(shared) < MIN_AVENUES:
                continue
            if tuple(sorted((ua, ub))) in have:
                continue
            cand.append((-len(shared), ua, ub, sorted(shared)))
    cand.sort()
    print(f"{len(cand)} stacked pairs share >= {MIN_AVENUES} printed avenues")

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
        for share, ua, ub, shared in cand:
            k = tuple(sorted((ua, ub)))
            if joins[k]:
                continue
            if d2.union(ua, ub):
                picked.append((share, ua, ub, shared))
                joins[k] += 1
    print(f"picked {len(picked)} pairs to commission")
    for share, ua, ub, shared in picked:
        print(f"   {ua:>3}|{ub:<3}  shares {-share} avenues: "
              + ", ".join(AVNAME[i] for i in shared))

    out = [[ua, ub, [AVNAME[i] for i in shared]] for _s, ua, ub, shared in picked]
    p = os.path.join(REPO, "work", "crossrow_pairs.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(out, open(p, "w"), indent=1)
    print(f"wrote {p}")

    if a.prepare:
        import paircrops
        n = 0
        for ua, ub, _av in out:
            if paircrops.build(a.year, ua, ub, force_axis="avenue",
                               avenues=_av, crossrow=True):
                n += 1
        print(f"prepared {n} tasks under work/paircrops/*_x/")
    return 0


if __name__ == "__main__":
    sys.exit(main())

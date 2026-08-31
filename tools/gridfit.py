#!/usr/bin/env python3
"""Rebuild the corridor grid city-wide from the named controls.

    python3 tools/gridfit.py --year 1912 [--apply]

recipe/grid.json is what turns "22nd and Avenue E" into a mosaic point. It was
built from the frozen downtown core alone, so it only knows streets 18-26 and
avenues A-K; anywhere else, crop.py fails with a KeyError.

Every accepted control already names its corridor ("Ave O 1/2", "27th St"), and
after the control solve both sheets in a control agree on where that corridor
is. So each control is a direct measurement of one named corridor's mosaic
coordinate. This aggregates those measurements, fits the block pitch through
them robustly, and fills in the corridors no control happened to name.

The core's own entries are kept verbatim: they came from hand-verified frontage
midlines and are the anchor everything else is measured against.
"""
import argparse
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe, px_per_ft           # noqa: E402
from netsolve import load_controls               # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STREET_RE = re.compile(r"(\d+)\s*(?:st|nd|rd|th)\b", re.I)
AVENUE_RE = re.compile(r"\bave?\.?\s*([a-t])\s*(1/2|½)?", re.I)


def ground_index(slot):
    """Slots count every named corridor, so south of Avenue M they step by a
    half block. This maps a slot to units of ONE full avenue pitch, which is
    what the pitch fit needs."""
    return slot if slot <= 12 else 12 + (slot - 12) / 2.0


def parse(axis, corridor):
    """-> ('street', 27) | ('avenue', slot) | None"""
    s = str(corridor)
    if axis == "y":
        m = STREET_RE.search(s)
        return ("street", int(m.group(1))) if m else None
    m = AVENUE_RE.search(s)
    if not m:
        return None
    return ("avenue", Recipe.avenue_slot(m.group(1) + ("1/2" if m.group(2) else "")))


def robust_line(idx, val):
    """Least squares with two rounds of 3-sigma trimming."""
    idx, val = np.asarray(idx, float), np.asarray(val, float)
    keep = np.ones(len(idx), bool)
    for _ in range(2):
        if keep.sum() < 3:
            break
        c = np.polyfit(idx[keep], val[keep], 1)
        r = val - np.polyval(c, idx)
        s = np.std(r[keep])
        if s <= 0:
            break
        keep = np.abs(r) < 3 * s
    c = np.polyfit(idx[keep], val[keep], 1)
    r = val[keep] - np.polyval(c, idx[keep])
    return c, float(np.std(r)), int(keep.sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1912", "1899"])
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    r = Recipe(int(a.year))
    ppf = px_per_ft(r)
    old = json.load(open(os.path.join(r.dir, "grid.json")))

    obs = {"street": {}, "avenue": {}}
    for ua, ub, ax, ma, mb, corridor, fn in load_controls(r):
        p = parse(ax, corridor)
        if p is None:
            continue
        kind, key = p
        obs[kind].setdefault(key, []).extend([(ma, ua), (mb, ub)])

    print(f"named corridors observed: {len(obs['street'])} streets, "
          f"{len(obs['avenue'])} avenues")

    out = dict(old)
    out["source"] = ("frozen core entries from verified frontage midlines; the "
                     "rest measured from named shared-corridor controls and "
                     "filled on the fitted block pitch (tools/gridfit.py)")
    report = {}

    for kind, field, section, index_of in (
            ("street", "y", "streets", lambda k: float(k)),
            ("avenue", "x", "avenues", ground_index)):
        core = {k: v for k, v in old.get(section, {}).items()}
        idx, val = [], []
        for key, samples in obs[kind].items():
            v = float(np.median([s[0] for s in samples]))
            idx.append(index_of(key))
            val.append(v)
        # the core entries are the anchor: weight them in by repeating them
        for k, v in core.items():
            key = int(k)
            idx.append(index_of(key))
            val.append(float(v[field]))
        c, sd, n = robust_line(idx, val)
        pitch = abs(c[0]) / ppf
        report[kind] = {"pitch_ft": round(pitch, 1),
                        "residual_ft": round(sd / ppf, 1), "kept": n,
                        "of": len(idx)}
        print(f"{kind:>7}: pitch {pitch:7.1f} ft, fit residual "
              f"{sd/ppf:6.1f} ft over {n}/{len(idx)} corridors")

        span = (range(min(min(obs[kind], default=99), min(map(int, core), default=99)),
                      max(max(obs[kind], default=0), max(map(int, core), default=0)) + 1)
                if kind == "street" else range(0, 28))
        sect = {}
        for key in span:
            k = str(key)
            if k in core:
                e = dict(core[k])
                e["source"] = "core (verified frontage midlines)"
                sect[k] = e
                continue
            if key in obs[kind]:
                samples = obs[kind][key]
                v = float(np.median([s[0] for s in samples]))
                sect[k] = {field: round(v, 1), "n": len(samples),
                           "spread": round(float(np.ptp([s[0] for s in samples])), 1),
                           "sheets": sorted({s[1] for s in samples}),
                           "source": "controls (named corridor)"}
            else:
                sect[k] = {field: round(float(np.polyval(c, index_of(key))), 1),
                           "n": 0, "source": "fitted block pitch"}
        out[section] = sect
        got = sum(1 for e in sect.values() if e["n"])
        print(f"         {len(sect)} entries, {got} measured, "
              f"{len(sect)-got} on the pitch fit")

    out["fit"] = report
    p = os.path.join(r.dir, "grid_city.json")
    json.dump(out, open(p, "w"), indent=1)
    print(f"\nwrote {p}")

    # what changed where both agree
    for section, field in (("streets", "y"), ("avenues", "x")):
        d = [abs(out[section][k][field] - old[section][k][field]) / ppf
             for k in old.get(section, {}) if k in out[section]]
        if d:
            print(f"vs old {section}: median {np.median(d):.1f} ft, "
                  f"max {max(d):.1f} ft over {len(d)} shared")

    if a.apply:
        import shutil
        tgt = os.path.join(r.dir, "grid.json")
        shutil.copyfile(tgt, tgt + ".pre_city")
        json.dump(out, open(tgt, "w"), indent=1)
        print(f"applied to {tgt} (previous kept as .pre_city)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

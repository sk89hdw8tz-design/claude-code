#!/usr/bin/env python3
"""Solve sheet placement from shared-corridor controls.

    python3 tools/netsolve.py --year 1912 [--apply]

Each control in recipe/controls/ asserts that one corridor — a named street or
avenue — is the SAME line on two sheets. An avenue control pins the pair's
relative x; a street control pins their relative y. The frozen core sheets are
held fixed, which anchors the whole network where the master already proves it.

Rotation and scale come from the existing solve and are left alone: they are
read off the drawings and are broadly right. What the ring lacks is position,
so this solves a translation per sheet by least squares over every control.
Transforms only; no pixel is touched.
"""
import argparse
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe, px_per_ft           # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_controls(r):
    """[(A, B, axis, mosaic_a, mosaic_b)] from every usable control file."""
    out = []
    cdir = os.path.join(r.dir, "controls")
    for fn in sorted(os.listdir(cdir)):
        m = re.match(r"pair_(\w+)_(\w+)\.json$", fn)
        if not m:
            continue
        try:
            d = json.load(open(os.path.join(cdir, fn)))
        except Exception:
            continue
        if str(d.get("status", "")).upper() not in ("ACCEPTED", ""):
            continue
        a, b = m.group(1), m.group(2)
        # the agent-written schema; the older core files use a richer layout
        if "a_native" not in d or "b_native" not in d:
            continue
        ua, ub = a.lstrip("0") or "0", b.lstrip("0") or "0"
        if ua not in r.units or ub not in r.units:
            continue
        axis = str(d.get("axis", "")).lower()
        vertical = axis.startswith("av")
        try:
            an, bn = float(d["a_native"]), float(d["b_native"])
        except Exception:
            continue
        Ma, ta = r.sheet_matrix(ua)
        Mb, tb = r.sheet_matrix(ub)
        da, db = r.units[ua]["extent"], r.units[ub]["extent"]
        mid_a = (da[1] + da[3]) / 2.0 if vertical else (da[0] + da[2]) / 2.0
        mid_b = (db[1] + db[3]) / 2.0 if vertical else (db[0] + db[2]) / 2.0
        pa = Ma @ (np.array([an, mid_a]) if vertical else np.array([mid_a, an])) + ta
        pb = Mb @ (np.array([bn, mid_b]) if vertical else np.array([mid_b, bn])) + tb
        out.append((ua, ub, "x" if vertical else "y",
                    float(pa[0] if vertical else pa[1]),
                    float(pb[0] if vertical else pb[1]),
                    d.get("corridor", "?"), fn))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1912", "1899"])
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    r = Recipe(int(a.year))
    ppf = px_per_ft(r)
    gj = json.load(open(os.path.join(r.dir, "sheets_city.geojson")))
    core = {str(f["properties"]["unit"]) for f in gj["features"]
            if f["properties"].get("tier") == "core"}

    ctl = load_controls(r)
    print(f"{len(ctl)} usable controls ({sum(1 for c in ctl if c[2]=='x')} avenue, "
          f"{sum(1 for c in ctl if c[2]=='y')} street)")
    if not ctl:
        print("nothing to solve")
        return 1

    units = sorted(r.units)
    free = [u for u in units if u not in core]
    ix = {u: i for i, u in enumerate(free)}
    n = len(free)

    rows, rhs, tags = [], [], []
    for ua, ub, ax, ma, mb, corr, fn in ctl:
        row = np.zeros(2 * n)
        k = 0 if ax == "x" else 1
        if ua in ix:
            row[2 * ix[ua] + k] += 1.0
        if ub in ix:
            row[2 * ix[ub] + k] -= 1.0
        if not row.any():
            continue                       # core-core: already consistent
        rows.append(row)
        rhs.append(mb - ma)                # want (ma+dA) - (mb+dB) = 0
        tags.append((f"{ua}|{ub}", ax, corr, fn))
    if not rows:
        print("all controls are core-core; nothing free to solve")
        return 1
    A = np.array(rows)
    b = np.array(rhs)
    # light damping keeps unconstrained sheets near where they are
    lam = 1e-3
    A = np.vstack([A, lam * np.eye(2 * n)])
    b = np.concatenate([b, np.zeros(2 * n)])
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    d = {u: (float(sol[2 * ix[u]]), float(sol[2 * ix[u] + 1])) for u in free}

    res = A[:len(rows)] @ sol - b[:len(rows)]
    print(f"\ncontrol residuals after solve (ft): median "
          f"{np.median(np.abs(res))/ppf:.1f}, 90th "
          f"{np.percentile(np.abs(res),90)/ppf:.1f}, max {np.abs(res).max()/ppf:.1f}")
    worst = np.argsort(-np.abs(res))[:8]
    for i in worst:
        print(f"   {tags[i][0]:<9} {tags[i][1]}  {abs(res[i])/ppf:7.1f} ft  "
              f"[{tags[i][2]}]")

    moves = sorted(((float(np.hypot(*d[u]))/ppf, u) for u in free), reverse=True)
    constrained = {t[0].split("|")[0] for t in tags} | {t[0].split("|")[1] for t in tags}
    nc = [u for u in free if u not in constrained]
    print(f"\n{len(free)-len(nc)} free sheets constrained, {len(nc)} unconstrained "
          f"(left where they are){': ' + ', '.join(nc[:12]) if nc else ''}")
    print(f"moves (ft): median {np.median([m for m,_ in moves]):.0f}, "
          f"max {moves[0][0]:.0f} ({moves[0][1]})")
    print("largest:", ", ".join(f"{u}:{m:.0f}ft" for m, u in moves[:10]))

    out = {"generated_by": "tools/netsolve.py",
           "note": "translation per sheet from shared-corridor controls; "
                   "core frozen; rotation and scale unchanged",
           "controls_used": len(rows),
           "residual_ft": {"median": float(np.median(np.abs(res))/ppf),
                           "max": float(np.abs(res).max()/ppf)},
           "sheets": {}}
    for u in units:
        M, t = r.sheet_matrix(u)
        dx, dy = d.get(u, (0.0, 0.0))
        out["sheets"][u] = {"m": [list(map(float, M[0])), list(map(float, M[1]))],
                            "t": [float(t[0] + dx), float(t[1] + dy)],
                            "moved_ft": float(np.hypot(dx, dy) / ppf),
                            "source": "frozen-core" if u in core else
                                      ("control-solved" if u in constrained else "unchanged")}
    p = os.path.join(r.dir, "transforms_controls.json")
    json.dump(out, open(p, "w"), indent=1)
    print(f"\nwrote {p}")

    if a.apply:
        import shutil
        tgt = os.path.join(r.dir, "transforms_city.json")
        shutil.copyfile(tgt, tgt + ".pre_controls")
        cur = json.load(open(tgt))
        for u, s in out["sheets"].items():
            if s["source"] == "control-solved":
                cur["sheets"][u] = {"m": s["m"], "t": s["t"],
                                    "tier": "control", "how": "shared-corridor control"}
        json.dump(cur, open(tgt, "w"), indent=1)
        print(f"applied to {tgt} (previous kept as .pre_controls)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

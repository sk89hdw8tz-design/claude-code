#!/usr/bin/env python3
"""Consolidate three independent landmark measurements into landmarks_v2.

Sources per feature:
  L  the original locator            (SEED landmarks.json, single-measured)
  M  the edge-template matcher       (r1_measurements.json verification;
                                      confirms L's a_xy against ink on B)
  R  the blind relocation agents     (result_A..D.json, description-only)

Rules:
  - dash-* features are EXCLUDED outright: group B's relocation established
    the dashed centreline rows are per-sheet drafting conventions, not
    shared physical points.
  - CONFIRMED: R agrees with L within 12 px on both sheets -> consensus =
    mean(L, R) per sheet.
  - ADOPTED-R: R disagrees with L, but M's ink match sides with R (within
    12 px on sheet B) -> take R.
  - ADOPTED-L: R disagrees with L, M sides with L -> take L.
  - DISPUTED: three-way disagreement or R not-found and M weak -> excluded.
  - Schematic features stay excluded from pass/fail but are carried for
    reporting.

The kept set is split per pair, alternating by id order: FIT half (solver
constraints) and GATE half (landmark_check hold-out). New agent-found
features (new: true) go straight to the FIT half (single-source).
Writes out/landmarks_v2.json.
"""
import glob
import json
import os
from collections import defaultdict

SEED = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "work", "seed_pipeline", "SEED_1899")
ROOT = os.path.dirname(os.path.abspath(__file__))

lm = json.load(open(os.path.join(SEED, "landmarks.json")))
meas = json.load(open(os.path.join(ROOT, "out", "r1_measurements.json")))
mver = {r["id"]: r for r in meas["landmark_verification"]}

reloc = {}
news = []
for p in sorted(glob.glob(os.path.join(ROOT, "out", "relocate", "result_*.json"))):
    for r in json.load(open(p))["results"]:
        if r.get("new"):
            news.append(r)
        else:
            # some ids collide across pairs; key by (id, pair) when given
            key = (r["id"], tuple(r.get("pair", ()))) if r.get("pair") else (r["id"], ())
            reloc[key] = r

def find_reloc(fid, pair):
    for key in ((fid, tuple(pair)), (fid, ())):
        if key in reloc:
            return reloc[key]
    return None

def close(p, q, tol=12):
    return p and q and max(abs(p[0] - q[0]), abs(p[1] - q[1])) <= tol

out = []
counts = defaultdict(int)
for f in lm["features"]:
    fid, pair = f["id"], [f["sheet_a"], f["sheet_b"]]
    rec = {"id": fid, "pair": pair, "schematic": bool(f.get("schematic"))}
    if fid.startswith("dash-"):
        rec.update(status="excluded-dash")
    else:
        R = find_reloc(fid, pair)
        M = mver.get(fid, {})
        m_b = M.get("b_xy_matched")
        L_a, L_b = f["a_xy"], f["b_xy"]
        if R and "a_xy" in R:
            r_a, r_b = R["a_xy"], R["b_xy"]
            if close(L_a, r_a) and close(L_b, r_b):
                rec.update(status="confirmed",
                           a_xy=[(L_a[0]+r_a[0])/2, (L_a[1]+r_a[1])/2],
                           b_xy=[(L_b[0]+r_b[0])/2, (L_b[1]+r_b[1])/2])
            elif close(m_b, r_b) and close(L_a, r_a, 20):
                rec.update(status="adopted-R", a_xy=r_a, b_xy=r_b)
            elif close(m_b, L_b):
                rec.update(status="adopted-L", a_xy=L_a, b_xy=L_b)
            else:
                rec.update(status="disputed",
                           detail={"L": [L_a, L_b], "R": [r_a, r_b], "M_b": m_b})
        else:
            # no relocation: keep only if the matcher verified L
            if M.get("verdict") == "verified":
                rec.update(status="matcher-only", a_xy=L_a, b_xy=L_b)
            else:
                rec.update(status="unverified")
    counts[rec["status"]] += 1
    out.append(rec)

for r in news:
    out.append({"id": r["id"], "pair": r.get("pair") or [r.get("sheet_a"), r.get("sheet_b")],
                "schematic": False, "status": "agent-new",
                "a_xy": r["a_xy"], "b_xy": r["b_xy"]})
    counts["agent-new"] += 1

# fit/gate split per pair over usable, non-schematic features
KEEP = {"confirmed", "adopted-R", "adopted-L", "matcher-only"}
by_pair = defaultdict(list)
for r in out:
    if r["status"] in KEEP and not r["schematic"]:
        by_pair[tuple(r["pair"])].append(r)
for pair, rows in by_pair.items():
    rows.sort(key=lambda r: r["id"])
    for i, r in enumerate(rows):
        r["split"] = "fit" if i % 2 == 0 else "gate"
for r in out:
    if r["status"] == "agent-new":
        r["split"] = "fit"

json.dump({"rules": __doc__, "counts": dict(counts), "features": out},
          open(os.path.join(ROOT, "out", "landmarks_v2.json"), "w"), indent=1)
print(dict(counts))
ngate = sum(1 for r in out if r.get("split") == "gate")
nfit = sum(1 for r in out if r.get("split") == "fit")
print(f"fit: {nfit}  gate: {ngate}")
for pair, rows in sorted(by_pair.items()):
    print(f"  {pair}: {len(rows)} usable ({sum(1 for r in rows if r['split']=='gate')} gate)")

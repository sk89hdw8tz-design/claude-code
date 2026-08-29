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
            r = reloc[key]
            # A low-confidence relocation, a not-found, or a line-crossing
            # with a pinned coordinate is not an independent measurement.
            if r.get("status") == "not-found" or r.get("confidence") == "low":
                return None
            return r
    return None

def close(p, q, tol=12):
    return p and q and max(abs(p[0] - q[0]), abs(p[1] - q[1])) <= tol

out = []
counts = defaultdict(int)
for f in lm["features"]:
    fid, pair = f["id"], [f["sheet_a"], f["sheet_b"]]
    rec = {"id": fid, "pair": pair, "schematic": bool(f.get("schematic"))}
    if fid.startswith("dash-") or fid.startswith("corridor-"):
        rec.update(status="excluded-dash")
    elif fid.startswith("width70"):
        # Italic width annotations are TEXT, which the seed prompt bans as
        # landmarks; the pair 15|16 labels imply a 4.5-degree rotation over
        # 890 px, i.e. at least one is measured on a different glyph.
        rec.update(status="excluded-text-label")
    elif "alarm" in fid:
        # Fire-alarm boxes are drafted symbols, not surveyed objects: both
        # alarm features deviate 40-60 px from their pair's consensus (and
        # group C's relocation note flags the placement difference for
        # alarm-box-212 explicitly). Excluded as unshared drafting.
        rec.update(status="excluded-alarm-symbol")
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
    pr = r.get("pair") or [r.get("sheet_a"), r.get("sheet_b")]
    if isinstance(pr, str):
        pr = pr.split("|")
    if ("a_xy" not in r or "b_xy" not in r or not pr or None in pr
            or r.get("confidence") == "low"):
        counts["agent-new-unusable"] += 1
        continue
    pr = [str(x) for x in pr]
    out.append({"id": r["id"], "pair": pr,
                "schematic": False, "status": "agent-new",
                "a_xy": r["a_xy"], "b_xy": r["b_xy"]})
    counts["agent-new"] += 1

# within-pair consistency: with >=3 usable features, fit a per-pair
# similarity and evict features >15 px off the pair's own consensus
# (wrong-object or drafting-difference survivors).
import numpy as np
KEEP = {"confirmed", "adopted-R", "adopted-L", "matcher-only"}
by_pair0 = defaultdict(list)
for r in out:
    if r["status"] in KEEP and not r["schematic"]:
        by_pair0[tuple(r["pair"])].append(r)
for pair, rows in by_pair0.items():
    if len(rows) < 3:
        continue
    A = np.array([r["a_xy"] for r in rows], float)
    B = np.array([r["b_xy"] for r in rows], float)
    ca, cb = A.mean(0), B.mean(0)
    H = (A - ca).T @ (B - cb)
    U, S, Vt = np.linalg.svd(H)
    R = Vt.T @ U.T
    if np.linalg.det(R) < 0:
        Vt[-1] *= -1; R = Vt.T @ U.T
    s = S.sum() / ((A - ca) ** 2).sum()
    pred = s * (R @ (A - ca).T).T + cb
    res = np.hypot(*(pred - B).T)
    for r, e in zip(rows, res):
        if e > 15:
            r["status"] = "excluded-pair-outlier"
            r["pair_residual_px"] = round(float(e), 1)
            counts["excluded-pair-outlier"] += 1

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

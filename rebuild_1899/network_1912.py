#!/usr/bin/env python3
"""1912 registration network at pct:50 working scale.

Materializes every unit's working image (pct:50 CI fetch for new sheets;
archival core downscaled x0.5 so ALL matching runs at one scale), computes
printed extents, seam-line native estimates, and pair contexts. The frozen
core transforms convert to the working scale as m' = 2*M (archival native =
2 x pct50 native), t unchanged — the mosaic frame stays the archival sheet
10 frame.

Writes out/network_1912.json; working images land in work/sheets/1912w/.
"""
import hashlib
import json
import os
import subprocess

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
os.chdir(REPO)

COV = json.load(open(os.path.join(ROOT, "out", "coverage_1912.json")))
INV = json.load(open("outputs/1912/recipe/inventory.json"))
CORE_T = json.load(open("outputs/1912/recipe/transforms.json"))["sheets"]
BRANCH = "origin/claude/galveston-1912-source-data"
WD = "work/sheets/1912w"
os.makedirs(WD, exist_ok=True)

ARCHIVAL = {"7": 11, "8": 13, "9": 15, "10": 17, "11": 19, "12": 21,
            "39": 49, "40": 50, "43": 53, "44": 54, "49": 59, "50": 60,
            "13": 23}

def materialize(uid):
    """Working image path for a unit; created if absent. Returns (path, scale)
    where scale = native px of the RECIPE frame per working px (2 for core
    archival sheets shrunk to half, 1 for pct50 units whose recipe native IS
    pct50)."""
    n = COV["units"][uid]["file"]
    dst = os.path.join(WD, f"u{uid}.jpg")
    if os.path.exists(dst):
        return dst
    if uid in ARCHIVAL:
        f = f"sanborn08539_004_img{ARCHIVAL[uid]:03d}_archival.jp2"
        it = next(i for i in INV["items"] if i["file"] == f)
        data = subprocess.run(["git", "show", f"{BRANCH}:{it['mirror']['path']}"],
                              capture_output=True, check=True).stdout
        assert hashlib.sha256(data).hexdigest() == it["sha256"]
        tmp = os.path.join(WD, "tmp.jp2")
        open(tmp, "wb").write(data)
        img = cv2.imread(tmp)
        os.remove(tmp)
        img = cv2.resize(img, (img.shape[1] // 2, img.shape[0] // 2),
                         interpolation=cv2.INTER_AREA)
    else:
        f = f"pct50/sheet_{n:04d}.jpg"
        it = next((i for i in INV["items"] if i["file"] == f), None)
        if it is None:
            return None
        data = subprocess.run(["git", "show", f"{BRANCH}:{it['mirror']['path']}"],
                              capture_output=True, check=True).stdout
        assert hashlib.sha256(data).hexdigest() == it["sha256"]
        open(dst, "wb").write(data)
        return dst
    cv2.imwrite(dst, img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return dst

ST_PITCH_W = 1105.0     # street pitch at working scale (archival ~2210 / 2)
M_TOP_W = 130.0

def printed_extent(g):
    H, W = g.shape
    core = g[:H]
    thr_dark = 200
    def first_last(v, thr=0.008, max_gap=260):
        idx = np.where(v > thr)[0]
        if len(idx) == 0:
            return (0, len(v) - 1)
        runs = []
        start = prev = idx[0]
        for i in idx[1:]:
            if i - prev > max_gap:
                runs.append((start, prev)); start = i
            prev = i
        runs.append((start, prev))
        lo, hi = max(runs, key=lambda r: r[1] - r[0])
        for r in runs:
            if 0 < lo - r[1] <= max_gap:
                lo = r[0]
            if 0 < r[0] - hi <= max_gap:
                hi = r[1]
        return int(lo), int(hi)
    # LOC scans: dark surround; printed page is the bright region
    bright = (core > np.percentile(core, 55)).astype(np.float32)
    x0, x1 = first_last(bright.mean(axis=0), thr=0.35, max_gap=300)
    y0, y1 = first_last(bright.mean(axis=1), thr=0.35, max_gap=300)
    return x0, y0, x1, y1

units_out = {}
missing = []
for uid, u in sorted(COV["units"].items(), key=lambda kv: int(kv[0])):
    p = materialize(uid)
    if p is None:
        missing.append(uid)
        continue
    g = cv2.imread(p, 0)
    ext = printed_extent(g)
    s0, s1 = u["st"]
    est_h = {str(stn): ext[1] + M_TOP_W + i * ST_PITCH_W
             for i, stn in enumerate(range(s0, s1 + 1))}
    units_out[uid] = {"file": u["file"], "working": p, "extent": list(ext),
                      "st": u["st"], "est_h": est_h,
                      "core": uid in ARCHIVAL, "note": u.get("note", "")[:120]}

pairs_out = []
for p in COV["pairs"]:
    a, b = p["owner"], p["nbr"]
    if a not in units_out or b not in units_out:
        continue
    ua, ub = units_out[a], units_out[b]
    if p["axis"] == "h" and p.get("idx"):
        idx = p["idx"]
        oa = ua["est_h"].get(str(idx))
        ob = ub["est_h"].get(str(idx))
        if oa is None or ob is None:
            continue
        pairs_out.append({"owner": a, "nbr": b, "axis": "h", "idx": idx,
                          "boundary": p["boundary"],
                          "owner_native": int(oa), "nbr_native": int(ob)})
    else:
        # vertical boundary: facing printed edges carry the shared corridor
        east_a = ua["extent"][2]
        west_b = ub["extent"][0]
        # decide which is west: keymap rects
        ra = COV["units"][a]["keymap_rect"]; rb = COV["units"][b]["keymap_rect"]
        if ra and rb and ra[0] > rb[0]:
            a2, b2, ua2, ub2 = b, a, ub, ua
        else:
            a2, b2, ua2, ub2 = a, b, ua, ub
        pairs_out.append({"owner": a2, "nbr": b2, "axis": "v", "idx": None,
                          "boundary": p["boundary"],
                          "owner_native": int(ua2["extent"][2] - 130),
                          "nbr_native": int(ub2["extent"][0] + 130)})

# frozen core at working scale
core_w = {}
for uid, s in CORE_T.items():
    if uid in units_out:
        r = s["raw"]
        core_w[uid] = {"m": [[2 * r["a"], -2 * r["b"]], [2 * r["b"], 2 * r["a"]]],
                       "t": [r["tx"], r["ty"]]}

json.dump({"units": units_out, "pairs": pairs_out, "core_working": core_w,
           "excluded": COV["excluded"],
           "frame": "1912 mosaic frame (archival sheet 10 raw px - center); working images at pct50 (core downscaled x0.5): p_mosaic = M_w @ p_working + t"},
          open(os.path.join(ROOT, "out", "network_1912.json"), "w"), indent=1)
print(f"units {len(units_out)} (missing working copies: {missing}); "
      f"pairs {len(pairs_out)}; core frozen {len(core_w)}")

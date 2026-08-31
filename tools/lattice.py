#!/usr/bin/env python3
"""Re-register the city sheets against Galveston's street lattice.

    python3 tools/lattice.py --year 1912 [--apply]

Why: outside the frozen downtown core the 1912 sheets were placed relative to
their neighbours (47% of them by translation alone, or from a single tie), so
error accumulates outward with nothing absolute to pin it. That is what makes
ring seams duplicate street labels and split buildings (HQ-9).

Galveston's grid is regular, so the streets themselves are the control. For
each sheet we find its street and avenue corridors, map them into the mosaic
frame with its current transform, snap each to the nearest lattice line (safe:
placement error is tens of feet against a ~350 ft block pitch), and re-fit a
similarity that lands the sheet's corridor crossings on the lattice.

The lattice is not assumed rigid — the island grid bends ~2 degrees to the
south — so sheets and lattice lines are solved together, alternating:
  1. fit every non-core sheet to the current lattice
  2. move every lattice line to the mean of what the sheets now say it is
The 12 frozen core sheets never move, which pins the lattice where the
master already proves it.

Only transforms change. No pixel is altered, resampled or retouched.
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe, px_per_ft            # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST_PITCH_FT, AV_PITCH_FT = 399.5, 350.4    # verified in HQ-10
MIN_CONTRAST = 0.06                        # reject sheets whose grid is unreadable
MIN_LINES = 2                              # need 2 in each axis for a similarity


def detect(prof, pitch, smooth=61):
    """(phase, corridor centres, contrast) for a low-ink comb of fixed pitch."""
    import cv2
    n = len(prof)
    sm = cv2.GaussianBlur(prof.reshape(-1, 1).astype(np.float32),
                          (1, smooth), 0).ravel()
    best = None
    for phase in np.arange(0, pitch, 2.0):
        c = np.arange(phase, n, pitch)
        b = c + pitch / 2.0
        ci = c[(c >= 0) & (c < n)].astype(int)
        bi = b[(b >= 0) & (b < n)].astype(int)
        if len(ci) < MIN_LINES or len(bi) < 1:
            continue
        s = float(sm[bi].mean() - sm[ci].mean())
        if best is None or s > best[0]:
            best = (s, phase, ci)
    return best


def load_keymap(year):
    """sheet -> (street indices, avenue slots) transcribed from the key maps.

    This is the absolute correspondence. Without it the only way to say which
    lattice line a detected corridor is, is to look through the very transform
    being corrected — which lets a badly placed sheet snap a whole block wrong.
    """
    import glob
    import re
    from reciplib import Recipe as _R
    out = {}
    for f in glob.glob(os.path.join(REPO, "rebuild_1899", "out",
                                    f"keymap_{year}_*.json")):
        for e in json.load(open(f)).get("results", []):
            sid = str(e["sheet"])
            st = []
            for s in e.get("streets", []):
                m = re.match(r"\s*(\d+)", str(s))
                if m:
                    st.append(int(m.group(1)))
            av = []
            for s in e.get("avenues", []):
                s = str(s).replace('"', " ")
                m = re.search(r"AVENUE\s+([A-Z])", s.upper())
                tok = m.group(1) if m else s.strip()
                try:
                    av.append(_R.avenue_slot(tok))
                except Exception:
                    pass
            if len(st) >= 2:
                st = list(range(min(st), max(st) + 1))
            out[sid] = (st, sorted(set(av)))
    return out


def similarity(src, dst):
    """Umeyama similarity (rotation+uniform scale+translation), src -> dst."""
    src = np.asarray(src, float)
    dst = np.asarray(dst, float)
    mu_s, mu_d = src.mean(0), dst.mean(0)
    S, D = src - mu_s, dst - mu_d
    C = D.T @ S / len(src)
    U, sv, Vt = np.linalg.svd(C)
    R = U @ Vt
    if np.linalg.det(R) < 0:
        U[:, -1] *= -1
        R = U @ Vt
    var = (S ** 2).sum() / len(src)
    s = float(sv.sum() / var) if var > 0 else 1.0
    M = s * R
    t = mu_d - M @ mu_s
    return M, t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1912", "1899"])
    ap.add_argument("--iters", type=int, default=4)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    import cv2
    r = Recipe(int(a.year))
    ppf = px_per_ft(r)                       # mosaic px per ground foot
    st_pitch_mos, av_pitch_mos = ST_PITCH_FT * ppf, AV_PITCH_FT * ppf
    units = r.units
    core = {u for u, s in r.transforms["sheets"].items()
            if str(s.get("tier", "")) == "core"}
    if not core:                             # tier lives in sheets_city.geojson
        gj = json.load(open(os.path.join(r.dir, "sheets_city.geojson")))
        core = {str(f["properties"]["unit"]) for f in gj["features"]
                if f["properties"].get("tier") == "core"}
    print(f"{len(units)} units, {len(core)} frozen core", flush=True)
    print(f"lattice pitch: streets {st_pitch_mos:.0f} px, avenues "
          f"{av_pitch_mos:.0f} px (mosaic)", flush=True)

    # ---- detect corridors once, cache ----
    cpath = os.path.join(r.dir, "corridors.json")
    if os.path.exists(cpath):
        det = json.load(open(cpath))
        print(f"loaded corridors for {len(det)} units from {cpath}", flush=True)
    else:
        det = {}
        for n, (uid, info) in enumerate(sorted(units.items()), 1):
            try:
                img = cv2.imread(r.fetch(r.sheet_file(uid)), cv2.IMREAD_GRAYSCALE)
            except Exception as e:
                print(f"  {uid}: no source ({e})", flush=True)
                continue
            if img is None:
                continue
            e = info["extent"]
            sub = img[e[1]:e[3], e[0]:e[2]]
            ink = (sub < 150).astype(np.float32)
            M, _ = r.sheet_matrix(uid)
            scale = float(np.sqrt(abs(np.linalg.det(M))))   # native px -> mosaic
            rs = detect(ink.mean(axis=1), st_pitch_mos / scale)
            cs = detect(ink.mean(axis=0), av_pitch_mos / scale)
            if rs is None or cs is None:
                continue
            det[uid] = {"rows": [float(v + e[1]) for v in rs[2]],
                        "row_contrast": rs[0],
                        "cols": [float(v + e[0]) for v in cs[2]],
                        "col_contrast": cs[0], "scale": scale}
            if n % 15 == 0:
                print(f"  detected {n}/{len(units)}", flush=True)
        json.dump(det, open(cpath, "w"), indent=1)
        print(f"wrote {cpath}", flush=True)

    usable = {u: d for u, d in det.items()
              if d["row_contrast"] > MIN_CONTRAST and d["col_contrast"] > MIN_CONTRAST
              and len(d["rows"]) >= MIN_LINES and len(d["cols"]) >= MIN_LINES}
    print(f"{len(usable)}/{len(det)} units have a readable grid "
          f"(contrast > {MIN_CONTRAST})", flush=True)

    # ---- current transforms ----
    T = {u: r.sheet_matrix(u) for u in units}

    # ---- initial lattice: index every corridor by snapping through the
    #      current transform, so indices are absolute street/avenue numbers ----
    def observations(T):
        """(street_index -> [mosaic y]), (avenue_index -> [mosaic x]) per unit."""
        so, ao = {}, {}
        for uid, d in usable.items():
            M, t = T[uid]
            for y in d["rows"]:
                p = M @ np.array([d["cols"][0], y], float) + t
                so.setdefault(uid, []).append(("row", y, float(p[1])))
            for x in d["cols"]:
                p = M @ np.array([x, d["rows"][0]], float) + t
                ao.setdefault(uid, []).append(("col", x, float(p[0])))
        return so, ao

    km = load_keymap(a.year)
    print(f"key map covers {len(km)} sheets", flush=True)

    # absolute index functions, fitted to grid.json (which the core proves)
    global GRID_ST, GRID_AV
    g = r.grid
    ks = sorted(int(k) for k in g["streets"])
    GRID_ST = tuple(map(float, np.polyfit(ks, [g["streets"][str(k)]["y"] for k in ks], 1)))
    ka = sorted(int(k) for k in g["avenues"])
    GRID_AV = tuple(map(float, np.polyfit(ka, [g["avenues"][str(k)]["x"] for k in ka], 1)))
    print(f"grid.json index model: streets y={GRID_ST[0]:.1f}*n{GRID_ST[1]:+.0f}, "
          f"avenues x={GRID_AV[0]:.1f}*s{GRID_AV[1]:+.0f}", flush=True)

    def assign(uid, kind):
        """[(native coord, absolute lattice index)] for one sheet and axis.

        Candidates come from the key map, so a mis-placed sheet cannot snap to
        a line outside the blocks it actually depicts; the current transform
        only picks among those few.
        """
        d = usable[uid]
        vals = sorted(d["rows"] if kind == "row" else d["cols"])
        want = (km.get(uid, ([], []))[0] if kind == "row"
                else km.get(uid, ([], []))[1])
        if not want or not vals:
            return []
        M, t = T[uid]
        other = (d["cols"][0] if kind == "row" else d["rows"][0])
        pitch, inter = (GRID_ST if kind == "row" else GRID_AV)
        lo, hi = min(want) - 1, max(want) + 1      # key map, with one line of slack
        out = []
        for v in vals:
            p = M @ (np.array([other, v], float) if kind == "row"
                     else np.array([v, other], float)) + t
            mos = float(p[1] if kind == "row" else p[0])
            k = int(round((mos - inter) / pitch))   # absolute index from grid.json
            if lo <= k <= hi:
                out.append((v, k))
        # a duplicate index means two detections claimed one line: keep neither
        seen = {}
        for v, k in out:
            seen.setdefault(k, []).append(v)
        return [(vs[0], k) for k, vs in sorted(seen.items()) if len(vs) == 1]

    ASSIGN = {u: {"row": assign(u, "row"), "col": assign(u, "col")}
              for u in usable}
    ok = [u for u in usable
          if len(ASSIGN[u]["row"]) >= MIN_LINES and len(ASSIGN[u]["col"]) >= MIN_LINES]
    print(f"{len(ok)}/{len(usable)} units have key-map correspondence on both axes",
          flush=True)

    # lattice seeded from the FROZEN CORE only, which the master already proves
    lat_y, lat_x = {}, {}
    for uid in ok:
        if uid not in core:
            continue
        M, t = T[uid]
        d = usable[uid]
        for v, k in ASSIGN[uid]["row"]:
            p = M @ np.array([d["cols"][0], v], float) + t
            lat_y.setdefault(k, []).append(float(p[1]))
        for v, k in ASSIGN[uid]["col"]:
            p = M @ np.array([v, d["rows"][0]], float) + t
            lat_x.setdefault(k, []).append(float(p[0]))
    LY = {k: float(np.median(v)) for k, v in lat_y.items()}
    LX = {k: float(np.median(v)) for k, v in lat_x.items()}
    print(f"core pins {len(LY)} street lines, {len(LX)} avenue lines", flush=True)
    # extend to every index the key map mentions, by the known pitch
    def extend(L, pitch, idxs):
        if len(L) >= 2:
            ks = sorted(L)
            A = np.polyfit(ks, [L[k] for k in ks], 1)
            slope, inter = float(A[0]), float(A[1])
        else:
            k0 = next(iter(L))
            slope, inter = pitch, L[k0] - pitch * k0
        for k in idxs:
            L.setdefault(k, slope * k + inter)
        return L
    want_y = {k for u in ok for _, k in ASSIGN[u]["row"]}
    want_x = {k for u in ok for _, k in ASSIGN[u]["col"]}
    LY = extend(LY, st_pitch_mos, want_y)
    LX = extend(LX, av_pitch_mos, want_x)
    print(f"lattice extended to {len(LY)} streets, {len(LX)} avenues", flush=True)

    # ---- alternate: fit sheets to lattice, then lattice to sheets ----
    newT = dict(T)
    for it in range(a.iters):
        moved = []
        for uid in ok:
            if uid in core:
                continue
            M, t = newT[uid]
            src, dst = [], []
            for y, ky in ASSIGN[uid]["row"]:
                for x, kx in ASSIGN[uid]["col"]:
                    if ky in LY and kx in LX:
                        src.append([x, y])
                        dst.append([LX[kx], LY[ky]])
            if len(src) < 3:
                continue
            M2, t2 = similarity(src, dst)
            shift = float(np.linalg.norm(M2 @ np.array(src).mean(0) + t2
                                         - (M @ np.array(src).mean(0) + t)))
            newT[uid] = (M2, t2)
            moved.append((shift / ppf, uid))
        # lattice update from all sheets (core included, so it stays pinned)
        ly, lx = {}, {}
        for uid in ok:
            M, t = newT[uid]
            d = usable[uid]
            w = 8.0 if uid in core else 1.0
            for y, ky in ASSIGN[uid]["row"]:
                p = M @ np.array([d["cols"][0], y], float) + t
                ly.setdefault(ky, []).append((w, float(p[1])))
            for x, kx in ASSIGN[uid]["col"]:
                p = M @ np.array([x, d["rows"][0]], float) + t
                lx.setdefault(kx, []).append((w, float(p[0])))
        for k, v in ly.items():
            ws = sum(w for w, _ in v)
            LY[k] = sum(w * val for w, val in v) / ws
        for k, v in lx.items():
            ws = sum(w for w, _ in v)
            LX[k] = sum(w * val for w, val in v) / ws
        moved.sort(reverse=True)
        med = np.median([m for m, _ in moved]) if moved else 0.0
        print(f"iter {it + 1}: adjusted {len(moved)} sheets, median move "
              f"{med:.1f} ft, worst {moved[0][0]:.0f} ft ({moved[0][1]})"
              if moved else f"iter {it + 1}: nothing to adjust", flush=True)

    # ---- report ----
    deltas = []
    for uid in usable:
        if uid in core:
            continue
        M0, t0 = T[uid]
        M1, t1 = newT[uid]
        c = np.array(units[uid]["extent"], float).reshape(2, 2).mean(0)
        d = float(np.linalg.norm((M1 @ c + t1) - (M0 @ c + t0))) / ppf
        deltas.append((d, uid))
    deltas.sort(reverse=True)
    print(f"\nsheets moved (ft of ground): median "
          f"{np.median([d for d, _ in deltas]):.0f}, "
          f"90th {np.percentile([d for d, _ in deltas], 90):.0f}")
    print("largest corrections:", ", ".join(f"{u}:{d:.0f}ft" for d, u in deltas[:12]))

    out = {"generated_by": "tools/lattice.py",
           "note": ("sheet transforms re-fitted to the street lattice; core "
                    "frozen; transforms only, no pixel change"),
           "pitch_mosaic_px": {"streets": st_pitch_mos, "avenues": av_pitch_mos},
           "lattice": {"streets": {str(k): v for k, v in sorted(LY.items())},
                       "avenues": {str(k): v for k, v in sorted(LX.items())}},
           "sheets": {}}
    for uid in units:
        M, t = newT.get(uid, T[uid])
        out["sheets"][uid] = {"m": [list(map(float, M[0])), list(map(float, M[1]))],
                              "t": [float(t[0]), float(t[1])],
                              "source": ("frozen-core" if uid in core else
                                         "lattice" if uid in usable else "unchanged")}
    p = os.path.join(r.dir, "transforms_lattice.json")
    json.dump(out, open(p, "w"), indent=1)
    print(f"\nwrote {p}")
    if a.apply:
        import shutil
        tgt = os.path.join(r.dir, "transforms_city.json")
        shutil.copyfile(tgt, tgt + ".pre_lattice")
        cur = json.load(open(tgt))
        for uid, s in out["sheets"].items():
            if s["source"] == "lattice":
                cur["sheets"][uid] = {"m": s["m"], "t": s["t"],
                                      "tier": "lattice", "how": "lattice-fit"}
        json.dump(cur, open(tgt, "w"), indent=1)
        print(f"applied to {tgt} (previous kept as .pre_lattice)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

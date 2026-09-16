#!/usr/bin/env python3
"""Absolute, grid-anchored placement of the outer 1912 units.

The chained (ring/tie) solve let one-avenue aliasing accumulate: the
grid check (qc/grid_city_check.json) showed units stacked on the same
ground in the outlot district. This replaces the chain with a placement
that cannot alias: every sheet's own printed corridors (detected from its
long block-outline lines, corridors.py) are fitted to a street/avenue
lattice, and the lattice lines are identified by the sheet's key-map span
(the sheet spanning 33rd-36th shows exactly those four street corridors).
Scale is the scan constant 2.0 (pct:50 working copies into the sheet-10
frame; the core solve measured 2.0005) and rotation 0 (upright scans);
translation comes from the identified corridors. Multi-panel sheets
(48, 85, 93, 99) are split into panels with their own spans.

Downtown core units keep their frozen solve. Units whose sheet shows no
corridor grid (wharf/beach: 1-6, 32 beach, ...) cannot be grid-anchored;
they keep the chain placement, tagged so.

Writes out/grid_place_1912.json and out/network_1912_v2.json.
"""
import json, os, re, sys
import cv2, numpy as np
ROOT = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(ROOT); os.chdir(REPO)
sys.path.insert(0, ROOT); sys.path.insert(0, "tools")
from corridors import corridors
from reciplib import Recipe

NET = json.load(open(f"{ROOT}/out/network_1912.json"))
AFF = json.load(open(f"{ROOT}/out/affine_city_1912.json"))["sheets"]
G = json.load(open("outputs/1912/recipe/grid.json"))
SY = {int(k): v["y"] for k, v in G["streets"].items()}
_p = (SY[26] - SY[18]) / 8.0
for _s in range(6, 54):
    SY.setdefault(_s, SY[26] + (_s - 26) * _p)
for _s in range(6, 54):
    G["streets"].setdefault(str(_s), {"y": SY[_s], "n": 0, "spread": None, "method": "extrapolated"})
SX = {int(k): v["x"] for k, v in G["avenues"].items()}
PY = G["fit"]["street"]["pitch"] / 2.0       # native px per street (scale 2)
PX = G["fit"]["avenue"]["pitch"] / 2.0
SCALE = 2.0

# key-map spans; a sheet listed twice keeps the entry that names avenues
spans = {}
for q in "NW NE SW SE".split():
    for r in json.load(open(f"{ROOT}/out/keymap_1912_{q}.json"))["results"]:
        k = str(r["sheet"])
        if k not in spans or (r["avenues"] and not spans[k]["avenues"]):
            spans[k] = r
def st_int(v): return int(re.sub(r"\D", "", str(v)))
def span_of(rec):
    ss = sorted(st_int(v) for v in rec["streets"])
    sl = sorted(Recipe.avenue_slot(a) for a in rec["avenues"]) if rec["avenues"] else []
    return (ss[0], ss[-1]), ((sl[0], sl[-1]) if sl else None)

# panels: unit id -> (source unit, detection rect, streets, slots, ownership rect)
W, H = 3327, 3898
PANELS = {
  "48":  ("48", (40, 40, 2000, 3858),  (30, 33), (23, 24), "L-shape: full sheet minus inset"),
  "48b": ("48", (2020, 40, 3260, 2120), (29, 30), (23, 23), "inset top-right"),
  "85":  ("85", (1210, 40, 3287, 3858), (39, 42), (10, 13), "sheet minus inset (block 99 K-L top-left included)"),
  "85b": ("85", (72, 1700, 1200, 3840), (39, 40), (9, 10), "inset bottom-left"),
  "93":  ("93", (40, 1330, 3287, 3858), (43, 45), (9, 12), "sheet minus inset (block 42 top-right included)"),
  "93b": ("93", (72, 120, 1160, 1320), (45, 46), (9, 10), "inset top-left"),
  "99":  ("99", (40, 40, 1712, 3858),  (33, 36), (25, 26), "left panel"),
  "99b": ("99", (1712, 40, 3287, 3858), (36, 39), (26, 27), "right panel"),
}
# ownership extents (native) for the panels; the L-shapes are handled as
# rect minus inset rect in export
PANEL_EXTENT = {
  "48": [40, 40, 3287, 3858], "48b": [2020, 40, 3260, 2120],
  "85": [40, 40, 3287, 3858], "85b": [72, 1700, 1200, 3840],
  "93": [40, 40, 3287, 3858], "93b": [72, 120, 1160, 1320],
  "99": [40, 40, 1712, 3858], "99b": [1712, 40, 3287, 3858],
}
# corrections from the blind corridor readers (qc/corridor_check/_verdict.json):
# per unit, an optional detection rect and explicit native->line identifications
# that replace the lattice fit on that axis ({} = the detections on that axis
# are not corridors -> no support -> prior).
OVERRIDES = {
  "26": {"rect": (40, 40, 2000, 3858), "y": {3619: 21}, "x": {1168: 18}},
  "17": {"rect": (1340, 1200, 3287, 3858)},
  "54": {"y": {2587: 26}},
  "85": {"x": {2198: 12, 3187: 13}},
  "75": {"x": {}},
}
PANELS.update({
  "26":  ("26", (40, 40, 2000, 3858), (18, 21), (17, 18), "sheet minus inset"),
  "17":  ("17", (1340, 1200, 3287, 3858), (7, 9), (0, 2), "sheet minus two insets (east-end blocks)"),
  "20":  ("20", (40, 40, 3287, 3858), (7, 9), (8, 11), "sheet minus inset"),
  "25":  ("25", (40, 40, 3287, 3858), (9, 12), (11, 14), "sheet minus inset"),
  "54":  ("54", (40, 40, 3287, 3858), (24, 27), (20, 22), "sheet minus inset"),
  "26b": ("26", (2020, 40, 3280, 2140), (17, 18), (17, 17), "inset top-right: beach strip seaward of Seawall Blvd"),
  "17b": ("17", (40, 40, 1340, 2660), (50, 52), (9, 10), "inset top-left: outlying blocks 6/7 at 50th-52nd (3 mi W of P.O.)"),
  "20b": ("20", (2140, 40, 3287, 1560), (9, 9), (11, 11), "inset top-right: beach strip seaward of Seawall Blvd at 9th/Ave L"),
  "25b": ("25", (2520, 40, 3287, 1160), (12, 12), (14, 14), "inset top-right: beach strip seaward of Seawall Blvd at 12th/Ave N"),
  "54b": ("54", (2080, 40, 3287, 2280), (23, 24), (20, 20), "inset top-right: beach amusement strip (Gulfview Hotel) 23rd-24th at Ave Q"),
})
PANEL_EXTENT.update({"26": [40, 40, 3287, 3858], "26b": [2020, 40, 3280, 2140],
                     "17": [40, 40, 3287, 3858], "17b": [40, 40, 1340, 2660],
                     "20": [40, 40, 3287, 3858], "20b": [2140, 40, 3287, 1560],
                     "25": [40, 40, 3287, 3858], "25b": [2520, 40, 3287, 1160],
                     "54": [40, 40, 3287, 3858], "54b": [2080, 40, 3287, 2280]})
# sheet 17 also carries an un-placeable framed panel (Union Slaughtering Co.,
# "8 miles W of P.O.", no street grid): excluded from ownership, not a unit
EXTRA_HOLES = {"17": [[1240, 40, 2540, 1280]]}
PANEL_HOLE = {"26": [2020, 40, 3280, 2140], "17": [40, 40, 1340, 2660],
              "20": [2140, 40, 3287, 1560], "25": [2520, 40, 3287, 1160], "54": [2080, 40, 3287, 2280], "48": [2020, 40, 3260, 2120], "85": [72, 1700, 1200, 3840], "93": [72, 120, 1160, 1320]}

def lattice_fit(dets, pitch, lines, prior_first, tol=60, gpos=None):
    """dets: detected corridor centres (native). lines: ordered grid indices
    the panel should show (e.g. streets 33..36). Find the phase and index
    assignment: maximise supported lines in the span, penalise support
    outside it and distance from the prior position of the first line.
    Returns (offset_native_for_line0, n_supported, residuals) or None."""
    if not dets:
        return None
    dets = np.array([d["c"] for d in dets]); m = len(lines)
    # native offsets of the lines relative to line 0 (from the current grid)
    rel = (np.array([gpos[l] for l in lines]) - gpos[lines[0]]) / SCALE if gpos else np.arange(m) * pitch
    ext = {l: (gpos[l] - gpos[lines[0]]) / SCALE for l in gpos} if gpos else None
    best = None
    # candidate phases: each detection could be any of the m lines
    for d in dets:
        for j in range(m):
            first = d - rel[j]
            pos = first + rel
            # support: detections within tol of predicted line
            dif = np.abs(dets[:, None] - pos[None, :])
            sup = (dif.min(axis=0) < tol)
            n_in = int(sup.sum())
            # detections that fit the lattice but fall outside the span
            if ext:
                others = np.array([first + v for l, v in ext.items() if l not in lines])
                n_out = int((np.abs(dets[:, None] - others[None, :]).min(axis=1) < tol).sum()) if len(others) else 0
            else:
                k = np.round((dets - first) / pitch)
                on_lat = np.abs(dets - (first + k * pitch)) < tol
                n_out = int((on_lat & ((k < 0) | (k >= m))).sum())
            score = n_in - 0.7 * n_out - 0.4 * abs(first - prior_first) / pitch
            if best is None or score > best[0]:
                res = dif.min(axis=0)[sup]
                # refine phase by the mean residual of supported lines
                cols = dif.argmin(axis=0)[sup]
                shift = float(np.mean(dets[cols] - pos[sup])) if n_in else 0.0
                ident = {lines[c]: float(dets[r]) for r, c in zip(cols, np.arange(m)[sup])}
                best = (score, first + shift, n_in, n_out, [float(r) for r in res], ident)
    return best

out, net2 = {}, {"units": {}, "pairs": NET["pairs"], "frame": NET["frame"],
                 "note": "v2: grid-anchored placements; panels split for 48/85/93/99"}
imgs = {}
def gray(u):
    if u not in imgs:
        imgs[u] = cv2.imread(NET["units"][u]["working"], 0)
    return imgs[u]

def place(uid, src, rect, streets, slots, prior_c):
    g = gray(src)
    ov = OVERRIDES.get(uid, {})
    rect = tuple(ov.get("rect", rect))
    hs = corridors(g, rect, "h"); vs = corridors(g, rect, "v")
    s_lines = list(range(streets[0], streets[1] + 1))
    a_lines = list(range(slots[0], slots[1] + 1)) if slots else []
    # prior: panel centre maps to span centre
    cx_n, cy_n = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
    py_first = cy_n - ((SY[streets[1]] - SY[streets[0]]) / 2) / SCALE
    fy = lattice_fit(hs, PY, s_lines, py_first, gpos=SY)
    fx = None
    if a_lines:
        px_first = cx_n - ((SX[slots[1]] - SX[slots[0]]) / 2) / SCALE
        fx = lattice_fit(vs, PX, a_lines, px_first, gpos=SX)
    rec = {"src": src, "rect": rect, "streets": streets, "slots": slots,
           "det_h": [round(d["c"]) for d in hs], "det_v": [round(d["c"]) for d in vs]}
    ty = tx = None
    if "y" in ov:
        fy = (0, 0, len(ov["y"]), 0, [], {l: float(c) for c, l in ov["y"].items()}) if ov["y"] else None
    if "x" in ov:
        fx = (0, 0, len(ov["x"]), 0, [], {l: float(c) for c, l in ov["x"].items()}) if ov["x"] else None
    if fy and fy[2] >= 1:
        ty = float(np.mean([SY[l] - SCALE * v for l, v in fy[5].items()]))
        rec["y"] = {"n_sup": fy[2], "n_out": fy[3], "resid": fy[4], "ident": fy[5]}
    if fx and fx[2] >= 1:
        tx = float(np.mean([SX[l] - SCALE * v for l, v in fx[5].items()]))
        rec["x"] = {"n_sup": fx[2], "n_out": fx[3], "resid": fx[4], "ident": fx[5]}
    how = []
    if ty is None:
        ty = prior_c[1] - SCALE * cy_n; how.append("y:prior")
    else:
        how.append(f"y:grid(n={rec['y']['n_sup']})")
    if tx is None:
        tx = prior_c[0] - SCALE * cx_n; how.append("x:prior")
    else:
        how.append(f"x:grid(n={rec['x']['n_sup']})")
    label = ("span-prior(no corridors detected; centre of key-map span)" if how == ["y:prior", "x:prior"]
             else "grid-anchored " + " ".join(how))
    if ov: rec["override"] = {k: (v if k == "rect" else {str(c): l for c, l in v.items()}) for k, v in ov.items()}
    rec.update({"m": [[SCALE, 0.0], [0.0, SCALE]], "t": [float(tx), float(ty)], "how": label})
    return rec

MEAS_S = {int(k): v["y"] for k, v in G["streets"].items() if v.get("n", 0) > 0}
MEAS_A = {int(k): v["x"] for k, v in G["avenues"].items() if v.get("n", 0) > 0}

def solve_axis(meas, ident_sets, keys):
    """LSQ for corridor coordinates: measured downtown values (weight 10)
    + within-sheet differences between identified corridors (weight 1,
    scale 2). Corridors touched by neither keep the current extrapolation
    (weak prior, weight 0.01)."""
    idx = {k: i for i, k in enumerate(keys)}
    rows, rhs, w = [], [], []
    cur = SY if keys[0] in SY and len(keys) > 30 else SX
    for k in keys:
        r = np.zeros(len(keys)); r[idx[k]] = 1
        if k in meas:
            rows.append(r); rhs.append(meas[k]); w.append(10.0)
        else:
            rows.append(r); rhs.append(cur[k]); w.append(0.01)
    n_obs = 0
    for ident in ident_sets:
        ls = sorted(ident)
        for a, b in zip(ls, ls[1:]):
            r = np.zeros(len(keys)); r[idx[b]] = 1; r[idx[a]] = -1
            rows.append(r); rhs.append(SCALE * (ident[b] - ident[a])); w.append(1.0); n_obs += 1
    A = np.array(rows) * np.array(w)[:, None]; b = np.array(rhs) * np.array(w)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    res = (np.array(rows) @ sol - np.array(rhs))
    touched = set()
    for ident in ident_sets: touched |= set(ident)
    return {k: float(sol[idx[k]]) for k in keys}, n_obs, touched, res[-n_obs:] if n_obs else res[:0]

def run_pass():
    out.clear(); net2["units"].clear()
    for uid, u in NET["units"].items():
        a = AFF[uid]
        if a["how"].startswith("frozen") or a["how"] == "core":
            out[uid] = {"m": a["m"], "t": a["t"], "how": a["how"], "src": uid}
            net2["units"][uid] = dict(u); continue
        if uid in PANELS:
            continue
        sp = spans.get(uid)
        if not sp or not sp["avenues"]:
            out[uid] = {"m": a["m"], "t": a["t"], "how": "chain-only(no corridor grid: " + (sp["note"][:60] if sp else "no keymap span") + ")", "src": uid}
            net2["units"][uid] = dict(u); continue
        (s0, s1), sl = span_of(sp)
        rect = tuple(u["extent"])
        prior_c = ((SX[sl[0]] + SX[sl[1]]) / 2, (SY[s0] + SY[s1]) / 2)
        out[uid] = place(uid, uid, rect, (s0, s1), sl, prior_c)
        net2["units"][uid] = dict(u)
    for pid, (src, rect, streets, slots, desc) in PANELS.items():
        prior_c = ((SX[slots[0]] + SX[slots[1]]) / 2, (SY[streets[0]] + SY[streets[1]]) / 2)
        out[pid] = place(pid, src, rect, streets, slots, prior_c); out[pid]["panel"] = desc
        u = dict(NET["units"][src]); u["extent"] = PANEL_EXTENT[pid]; u["st"] = list(streets)
        u["panel"] = desc; u["region"] = pid
        if pid in PANEL_HOLE: u["hole"] = PANEL_HOLE[pid]
        if pid in EXTRA_HOLES: u["holes"] = [PANEL_HOLE[pid]] + EXTRA_HOLES[pid]
        net2["units"][pid] = u

for it in range(3):
    run_pass()
    ys = [v["y"]["ident"] for v in out.values() if "y" in v and len(v["y"]["ident"]) >= 2]
    xs = [v["x"]["ident"] for v in out.values() if "x" in v and len(v["x"]["ident"]) >= 2]
    newY, ny, tY, rY = solve_axis(MEAS_S, ys, sorted(SY))
    newX, nx, tX, rX = solve_axis(MEAS_A, xs, sorted(SX))
    dy = max(abs(newY[k] - SY[k]) for k in SY); dx = max(abs(newX[k] - SX[k]) for k in SX)
    print(f"pass {it}: grid update max |dy| {dy:.0f} px ({ny} street obs, rms {np.sqrt(np.mean(rY**2)):.0f}), max |dx| {dx:.0f} px ({nx} avenue obs, rms {np.sqrt(np.mean(rX**2)):.0f})")
    SY.update(newY); SX.update(newX)
run_pass()
# corridors no sheet shows: extrapolate from the nearest solved ones at the median solved pitch
def extrapolate(D, touched):
    ks = sorted(D); sol = sorted(k for k in ks if k in touched or k in (MEAS_S if D is SY else MEAS_A))
    pitch = float(np.median(np.diff([D[k] for k in sol]) / np.diff(sol)))
    for k in ks:
        if k not in sol:
            near = min(sol, key=lambda s: abs(s - k)); D[k] = D[near] + (k - near) * pitch
extrapolate(SY, tY); extrapolate(SX, tX)
for k, v in G["streets"].items():
    if int(k) not in MEAS_S:
        v["y"] = round(SY[int(k)], 1)
        v["method"] = ("solved from sheet-internal corridor spacing (LSQ, anchored on measured downtown corridors)"
                       if int(k) in tY else "extrapolated (no sheet shows this corridor)")
for k, v in G["avenues"].items():
    if int(k) not in MEAS_A:
        v["x"] = round(SX[int(k)], 1)
        v["method"] = ("solved from sheet-internal corridor spacing (LSQ, anchored on measured downtown corridors)"
                       if int(k) in tX else "extrapolated (no sheet shows this corridor)")
G["fit"]["note"] = "corridors outside downtown solved from the sheets' own corridor spacing; see rebuild_1899/grid_place_1912.py"
json.dump(G, open("outputs/1912/recipe/grid.json", "w"), indent=1)
print("streets", {k: round(SY[k]) for k in sorted(SY)})
print("avenues", {k: round(SX[k]) for k in sorted(SX)})

json.dump({"convention": "p_frame = m @ p_native + t; native = pct:50 working copy px", "sheets": out},
          open(f"{ROOT}/out/grid_place_1912.json", "w"), indent=1)
json.dump(net2, open(f"{ROOT}/out/network_1912_v2.json", "w"), indent=1)
import collections
print(collections.Counter(v["how"].split("(")[0].split(" ")[0] for v in out.values()))
for k, v in out.items():
    if "det_h" in v:
        print(f"{k:>4} {v['how']:<34} y_res {[round(r) for r in v.get('y',{}).get('resid',[])]} x_res {[round(r) for r in v.get('x',{}).get('resid',[])]} out y{v.get('y',{}).get('n_out')} x{v.get('x',{}).get('n_out')}")

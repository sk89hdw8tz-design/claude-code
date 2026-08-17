#!/usr/bin/env python3
"""Self-test for fit_sheet5.py (synthetic two-panel fixture).

Builds a scratch fixture with KNOWN panel transforms and a fake frozen
block (sheets 7/9/11; sheet 13 deliberately absent), writes control files
in the verified-pair schema -- including a string/int mixed "pair", one
record with reversed A/B sides, a face-specific sigma override in
sigma_basis prose, an overlap-marked 5A-7 seam, and a CONTEXT_ONLY 5B-13
file -- then asserts:

  * parameter recovery within 3 sigma (propagated from the fit covariance)
    for both panels, including the non-zero rotations and the ~2x scales;
  * the cross-panel report detects an injected 50 px mosaic inconsistency
    on the pier pairs while leaving the consistent street pairs unflagged;
  * CONTEXT_ONLY data is fitted to nothing but reported (relative mode);
  * reversed sides and the sigma override are parsed correctly.

Run:  /home/user/g1912/venv/bin/python 40_solve/test_fit_sheet5.py
Prints PASS/FAIL lines; exit 0 iff all pass.
"""

import json
import math
import os
import shutil
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fit_sheet5 as fs  # noqa: E402

RNG = np.random.default_rng(20260817)

X_M = -6760.0          # mosaic x of the Ave A east face (ground truth)
WIDTH = 460.0          # mosaic px street width (~78 ft)
WIDTH_25TH = 700.0     # Rosenberg class
L_PANEL = 300.0        # mosaic length of panel-side face segments
L_BLOCK = 400.0
SIG_P, SIG_B, SIG_X = 4.0, 4.5, 3.0

POLY_A = [[0, 0], [3789, 0], [3866, 7795], [0, 7795], [0, 0]]
POLY_B = [[3789, 0], [6653, 0], [6653, 7795], [3866, 7795], [3789, 0]]

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    print(f"{'PASS' if ok else 'FAIL'}: {name}" + (f"  [{detail}]" if detail
                                                   else ""))


# ---------------------------------------------------------------------------
# Truth transforms (raw-pixel form)
# ---------------------------------------------------------------------------

def make_raw(s, theta_deg, ref_native, ref_mosaic):
    """Similarity with scale s, rotation theta, fixed by T(ref_native) =
    ref_mosaic.  Returned in raw form {a,b,tx,ty}."""
    th = math.radians(theta_deg)
    a, b = s * math.cos(th), s * math.sin(th)
    R = fs.rot(a, b)
    t = np.asarray(ref_mosaic, float) - R @ np.asarray(ref_native, float)
    return {"a": a, "b": b, "tx": float(t[0]), "ty": float(t[1])}


def inv_raw(T, g):
    R = fs.rot(T["a"], T["b"])
    return np.linalg.solve(R, np.asarray(g, float)
                           - np.array([T["tx"], T["ty"]]))


BLOCK_TRUTH = {
    7:  make_raw(1.0020, 0.30, [2440.0, 2500.0], [X_M, -8300.0]),
    9:  make_raw(0.9950, 0.05, [2550.0, 505.0], [X_M, -3400.0]),
    11: make_raw(0.9980, -0.10, [2505.0, 2322.0], [X_M, 5400.0]),
}
T13_TRUTH = make_raw(0.9970, 0.08, [2520.0, 501.0], [X_M, 10300.0])

T5A_TRUTH = make_raw(1.980, 0.45, [3610.0, 5350.0], [X_M, -4850.0])
T5B_TRUTH = make_raw(2.015, -0.35, [6390.0, 2500.0], [X_M, 1800.0])

# Mosaic face1 y per street
STREET_Y = {"19th": -8300.0, "20th": -6100.0, "21st": -3400.0,
            "22nd": -1400.0, "23rd": 900.0, "24th": 3100.0,
            "25th": 5400.0, "26th": 8000.0, "27th": 10300.0,
            "28th": 12000.0}


# ---------------------------------------------------------------------------
# Fixture generation
# ---------------------------------------------------------------------------

def face_seg(T, y_g, length, sigma_along):
    """Native-pixel face segment for the face line at mosaic y=y_g starting
    at the Ave A corner (mosaic x=X_M) and extending landward (+x)."""
    c = inv_raw(T, [X_M, y_g])
    f = inv_raw(T, [X_M + length, y_g])
    dy = RNG.normal(0.0, sigma_along)  # one line-position read per face/side
    return [[float(c[0] + RNG.normal(0, SIG_X)), float(c[1] + dy)],
            [float(f[0] + RNG.normal(0, SIG_X)), float(f[1] + dy)]]


def anchor_rec(name, status, panel_label, block_label, T_p, T_b, width,
               block_face1_sigma=None, notes="", swap_sides=False):
    y1 = STREET_Y[name]
    s_p = math.hypot(T_p["a"], T_p["b"])
    s_b = math.hypot(T_b["a"], T_b["b"])
    side_p = {
        "sheet": panel_label,
        "face1_seg": face_seg(T_p, y1, L_PANEL, SIG_P),
        "face2_seg": face_seg(T_p, y1 + width, L_PANEL, SIG_P),
        "sigma_along_px": SIG_P,
        "sigma_basis": "fixture clean rules",
    }
    b_sig1 = block_face1_sigma if block_face1_sigma else SIG_B
    side_b = {
        "sheet": block_label,
        "face1_seg": face_seg(T_b, y1, L_BLOCK, b_sig1),
        "face2_seg": face_seg(T_b, y1 + width, L_BLOCK, SIG_B),
        "sigma_along_px": SIG_B,
        "sigma_basis": (f"face1 reference outline ghost, sigma "
                        f"{block_face1_sigma:g} for that face; face2 clean "
                        f"single rule" if block_face1_sigma
                        else "fixture clean rules"),
    }
    wA, wB = round(width / s_p), round(width / s_b)
    if swap_sides:
        rec = {"anchor": name, "status": status, "A": side_b, "B": side_p,
               "drafted_width_px": {"A": wB, "B": wA,
                                    "annotation": "fixture"}}
    else:
        rec = {"anchor": name, "status": status, "A": side_p, "B": side_b,
               "drafted_width_px": {"A": wA, "B": wB,
                                    "annotation": "fixture"}}
    rec["notes"] = notes
    return rec


def build_fixture(root):
    controls = os.path.join(root, "controls")
    out_dir = os.path.join(root, "out")
    os.makedirs(controls)

    # --- fake frozen block transforms.json (sheet 11 centered-only to
    # exercise the raw-composition fallback; sheet 13 absent on purpose)
    center = np.array([3326.0, 3898.0])
    sheets = {}
    for sid, T in BLOCK_TRUTH.items():
        R = fs.rot(T["a"], T["b"])
        t_cent = np.array([T["tx"], T["ty"]]) + R @ center
        entry = {"a": T["a"], "b": T["b"],
                 "tx": float(t_cent[0]), "ty": float(t_cent[1])}
        if sid != 11:
            entry["raw"] = {"a": T["a"], "b": T["b"],
                            "tx": T["tx"], "ty": T["ty"]}
        sheets[str(sid)] = entry
    transforms_path = os.path.join(root, "transforms.json")
    with open(transforms_path, "w") as fh:
        json.dump({"convention": {"center": center.tolist()},
                   "kappa_px_per_ft": 6.0, "kappa_prior_dominated": True,
                   "sheets": sheets}, fh)

    # --- regions geojson (real panel polygons)
    regions_path = os.path.join(root, "regions.geojson")
    feats = []
    for rid, poly in (("A", POLY_A), ("B", POLY_B)):
        feats.append({"type": "Feature",
                      "properties": {"region_id": rid},
                      "geometry": {"type": "Polygon",
                                   "coordinates": [poly]}})
    feats.append({"type": "Feature",
                  "properties": {"region_id": "BREAK_RULE"},
                  "geometry": {"type": "LineString",
                               "coordinates": [[3789, 0], [3866, 7795]]}})
    with open(regions_path, "w") as fh:
        json.dump({"type": "FeatureCollection", "features": feats}, fh)

    # --- pair files
    def dump(name, obj):
        with open(os.path.join(controls, name), "w") as fh:
            json.dump(obj, fh, indent=1)

    dump("pair_05A_07.json", {
        "pair": ["5A", 7],  # int/str mix on purpose
        "boundary": "Ave A (fixture)",
        "controls": [
            anchor_rec("19th", "ACCEPTED", "5A", 7, T5A_TRUTH,
                       BLOCK_TRUTH[7], WIDTH,
                       notes="fixture: sheet 7 duplicates the bay strip -- "
                             "genuine two-sided overlap"),
            anchor_rec("20th", "ACCEPTED", "5A", 7, T5A_TRUTH,
                       BLOCK_TRUTH[7], WIDTH),
        ]})
    dump("pair_05A_09.json", {
        "pair": ["5A", "9"],
        "boundary": "Ave A (fixture)",
        "controls": [
            anchor_rec("21st", "ACCEPTED", "5A", "9", T5A_TRUTH,
                       BLOCK_TRUTH[9], WIDTH, block_face1_sigma=12.0),
            anchor_rec("22nd", "ACCEPTED", "5A", "9", T5A_TRUTH,
                       BLOCK_TRUTH[9], WIDTH),
        ]})
    dump("pair_05B_09.json", {
        "pair": ["5B", "9"],
        "boundary": "Ave A (fixture)",
        "controls": [
            anchor_rec("22nd", "ACCEPTED", "5B", "9", T5B_TRUTH,
                       BLOCK_TRUTH[9], WIDTH),
            anchor_rec("23rd", "ACCEPTED", "5B", "9", T5B_TRUTH,
                       BLOCK_TRUTH[9], WIDTH),
            anchor_rec("24th", "ACCEPTED", "5B", "9", T5B_TRUTH,
                       BLOCK_TRUTH[9], WIDTH),
        ]})
    dump("pair_05B_11.json", {
        "pair": [11, "5B"],  # reversed order AND reversed record sides
        "boundary": "Ave A (fixture)",
        "controls": [
            anchor_rec("25th", "ACCEPTED", "5B", 11, T5B_TRUTH,
                       BLOCK_TRUTH[11], WIDTH_25TH, swap_sides=True),
            anchor_rec("26th", "ACCEPTED", "5B", 11, T5B_TRUTH,
                       BLOCK_TRUTH[11], WIDTH, swap_sides=True),
        ]})
    dump("pair_05B_13.json", {
        "pair": ["5B", "13"],
        "attachment_class": "CONTEXT_ONLY (fixture tasking)",
        "boundary": "Ave A (fixture, outside target)",
        "controls": [
            anchor_rec("27th", "CONTEXT_ONLY", "5B", "13", T5B_TRUTH,
                       T13_TRUTH, WIDTH),
            anchor_rec("28th", "CONTEXT_ONLY", "5B", "13", T5B_TRUTH,
                       T13_TRUTH, WIDTH),
        ]})

    # --- cross-panel file: consistent street pairs, pier pairs with an
    # injected 50 px mosaic inconsistency on the 5B side
    def pt(T, g, extra=(0.0, 0.0)):
        p = inv_raw(T, np.asarray(g, float) + np.asarray(extra, float))
        return [float(p[0] + RNG.normal(0, 2.0)),
                float(p[1] + RNG.normal(0, 2.0))]

    g22n = [X_M, STREET_Y["22nd"]]
    g22s = [X_M, STREET_Y["22nd"] + WIDTH]
    gp_w = [-7400.0, -1150.0]
    gp_e = [-7250.0, -1180.0]
    dump("cross_panel_05.json", {
        "pair": ["5A", "5B"],
        "point_pairs": [
            {"id": "P1_22ndSt_blockN", "panel_A": pt(T5A_TRUTH, g22n),
             "panel_B": pt(T5B_TRUTH, g22n), "sigma_px": {"A": 4, "B": 4}},
            {"id": "P2_22ndSt_blockS", "panel_A": pt(T5A_TRUTH, g22s),
             "panel_B": pt(T5B_TRUTH, g22s), "sigma_px": {"A": 4, "B": 4}},
            {"id": "P3_pier22_W", "panel_A": pt(T5A_TRUTH, gp_w),
             "panel_B": pt(T5B_TRUTH, gp_w, extra=(50.0, 0.0)),
             "sigma_px": {"A": 5, "B": 5}},
            {"id": "P4_pier22_E", "panel_A": pt(T5A_TRUTH, gp_e),
             "panel_B": pt(T5B_TRUTH, gp_e, extra=(50.0, 0.0)),
             "sigma_px": {"A": 5, "B": 5}},
        ]})
    return controls, transforms_path, regions_path, out_dir


# ---------------------------------------------------------------------------
# Assertions
# ---------------------------------------------------------------------------

def centered_truth(T_raw, center):
    R = fs.rot(T_raw["a"], T_raw["b"])
    t = np.array([T_raw["tx"], T_raw["ty"]]) + R @ np.asarray(center, float)
    return np.array([T_raw["a"], T_raw["b"], float(t[0]), float(t[1])])


def check_panel_recovery(payload, pid, T_truth):
    sol = payload["panels"].get(pid)
    check(f"{pid} solved", sol is not None)
    if sol is None:
        return
    truth = centered_truth(T_truth, sol["center"])
    cov = np.array(sol["covariance"])
    names = sol["param_order"]
    est = np.array([sol["a"], sol["b"], sol["tx"], sol["ty"]])
    for i, nm in enumerate(names):
        std = math.sqrt(max(cov[i, i], 0.0))
        ok = abs(est[i] - truth[i]) <= 3.0 * std + 1e-9
        check(f"{pid} {nm} within 3 sigma", ok,
              f"est {est[i]:.4f} truth {truth[i]:.4f} std {std:.4f}")
    # sanity: covariance is meaningful, not inflated into vacuity
    check(f"{pid} covariance sane",
          sol["param_std"]["tx"] < 25.0 and sol["param_std"]["a"] < 0.02,
          f"std tx {sol['param_std']['tx']:.2f} a {sol['param_std']['a']:.4f}")
    # rotation genuinely recovered (free, non-zero in the fixture)
    th_true = math.degrees(math.atan2(T_truth["b"], T_truth["a"]))
    dth = abs(sol["theta_deg"] - th_true)
    check(f"{pid} rotation within 3 sigma", dth <= 3.0 *
          sol["theta_std_mrad"] / 1000.0 * 180.0 / math.pi + 1e-9,
          f"theta {sol['theta_deg']:.4f} truth {th_true:.4f} "
          f"std {sol['theta_std_mrad']:.2f} mrad")
    s_true = math.hypot(T_truth["a"], T_truth["b"])
    check(f"{pid} scale within 3 sigma",
          abs(sol["s"] - s_true) <= 3.0 * sol["s_std"] + 1e-9,
          f"s {sol['s']:.4f} truth {s_true:.4f} std {sol['s_std']:.4f}")


def main():
    root = tempfile.mkdtemp(prefix="fit_sheet5_test_")
    controls, transforms_path, regions_path, out_dir = build_fixture(root)
    payload = fs.run_fit(controls_dir=controls,
                         transforms_path=transforms_path,
                         regions_path=regions_path, out_dir=out_dir)

    check_panel_recovery(payload, "5A", T5A_TRUTH)
    check_panel_recovery(payload, "5B", T5B_TRUTH)

    # ---- scale ratio ~2x expectation reported
    ratios = {r["seam"]: r["solved_scale_ratio"]
              for r in payload["scale_comparison"]}
    check("scale comparison covers all fitted seams",
          set(ratios) == {"5A-7", "5A-9", "5B-9", "5B-11"}, str(set(ratios)))
    check("scale ratios near 2x", all(1.9 < v < 2.1 for v in ratios.values()),
          str({k: round(v, 3) for k, v in ratios.items()}))

    # ---- overlap seam produced pp rows; abutting seams along+across
    rows5a = payload["panels"]["5A"]["rows"]
    pp = [r for r in rows5a if r["seam"] == "5A-7"]
    check("5A-7 uses point-to-point rows (duplicated ground)",
          len(pp) == 8 and all(r["type"] in ("pp_along", "pp_across")
                               for r in pp), f"{len(pp)} rows")
    a9types = {r["type"] for r in rows5a if r["seam"] == "5A-9"}
    check("5A-9 uses along+across rows", a9types == {"along", "across"},
          str(a9types))

    # ---- sigma override parsed from prose
    o = [r for r in rows5a if r["seam"] == "5A-9" and r["anchor"] == "21st"
         and r["face"] == 1 and r["type"] == "along"]
    check("face-specific sigma override applied",
          len(o) == 1 and o[0]["sigma_block_native"] == 12.0,
          str([r["sigma_block_native"] for r in o]))

    # ---- reversed-sides record handled
    check("reversed sides handled (5B-11)",
          payload["attachments"]["5B-11"]["reversed_sides"] is True)

    # ---- CONTEXT_ONLY: fitted to nothing, reported in relative mode
    all_rows = rows5a + payload["panels"]["5B"]["rows"]
    check("5B-13 excluded from the fit",
          not any(r["seam"] == "5B-13" for r in all_rows))
    ctx = [c for c in payload["context_reports"] if c["seam"] == "5B-13"]
    check("5B-13 context report present (relative mode)",
          len(ctx) == 1 and ctx[0]["mode"] == "relative")
    if ctx and ctx[0]["separations"]:
        sep = ctx[0]["separations"][0]
        check("5B-13 relative separation consistent",
              abs(sep["difference_ft"]) < 5.0 and
              abs(sep["direction_diff_deg"]) < 1.0,
              f"diff {sep['difference_ft']:.2f} ft, "
              f"dir {sep['direction_diff_deg']:.2f} deg")
    else:
        check("5B-13 relative separation consistent", False, "no separations")

    # ---- cross-panel: injected 50 px inconsistency detected, streets clean
    cp = payload["cross_panel"]
    check("cross-panel report present", cp is not None)
    if cp:
        by_id = {p["id"]: p for p in cp["pairs"]}
        streets = [by_id["P1_22ndSt_blockN"], by_id["P2_22ndSt_blockS"]]
        piers = [by_id["P3_pier22_W"], by_id["P4_pier22_E"]]
        check("street pairs consistent (unflagged, < 30 px)",
              all(not p["flagged"] and p["norm_px"] < 30 for p in streets),
              str([round(p["norm_px"], 1) for p in streets]))
        check("injected 50 px inconsistency detected on pier pairs",
              all(p["flagged"] and 25.0 <= p["norm_px"] <= 80.0
                  for p in piers),
              str([round(p["norm_px"], 1) for p in piers]))
        check("flagged ids are exactly the pier pairs",
              set(cp["flagged_ids"]) == {"P3_pier22_W", "P4_pier22_E"})

    # ---- outputs written and loadable
    tpath = os.path.join(out_dir, "transforms_sheet5.json")
    dpath = os.path.join(out_dir, "diagnostics.md")
    ok_files = os.path.exists(tpath) and os.path.exists(dpath)
    if ok_files:
        with open(tpath) as fh:
            written = json.load(fh)
        ok_files = ("5A" in written["panels"] and "5B" in written["panels"]
                    and "raw" in written["panels"]["5A"]
                    and os.path.getsize(dpath) > 500)
    check("output files written and loadable", ok_files)

    n_fail = sum(1 for _, ok in RESULTS if not ok)
    print(f"\n{len(RESULTS) - n_fail}/{len(RESULTS)} checks passed")
    if n_fail:
        print(f"fixture kept for debugging: {root}")
        return 1
    shutil.rmtree(root, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

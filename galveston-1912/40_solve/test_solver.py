#!/usr/bin/env python3
"""Synthetic ground-truth self-test for the Galveston 1912 network solver.

Generates 12 synthetic sheets with known random similarity transforms
(rotations up to 0.5 deg, scales 1 +- 0.5%, translation jitter), writes
synthetic control JSONs in the exact MEASUREMENT_BRIEF schema to a temp dir,
adds Gaussian noise per the stated sigmas (plus an 8 px across-seam drafting
scatter, below the 12 px sigma_across floor the solver assumes), runs the
solver, and asserts:

  1. recovered parameters match ground truth within 3x the propagated
     uncertainty (plus tiny absolute floors for variance-factor noise);
  2. the rotation-covariance flag fires when a corner sheet (40) is
     deliberately weakened by dropping half its observations, while a
     well-connected interior sheet (43) stays unflagged at baseline;
  3. leave-one-seam-out degrades gracefully (all 17 seams refittable,
     finite and bounded prediction errors);
  4. the solver tolerates missing seam files (partial data): sheet 40
     disconnected -> reported unsolved, the rest still recovered.

Prints PASS/FAIL lines; exit code 0 iff all pass.

Run:  /home/user/g1912/venv/bin/python test_solver.py
"""

import json
import math
import os
import shutil
import sys
import tempfile
import traceback

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import solver  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADJACENCY = os.path.join(BASE, "10_key", "adjacency.json")

KAPPA_TRUE = 6.05
DX, DY = 6000.0, 7000.0
CENTER = solver.CENTER
SEED = 20260817

SHEET_RC = {7: (1, 1), 8: (1, 2), 39: (1, 3), 40: (1, 4),
            9: (2, 1), 10: (2, 2), 43: (2, 3), 44: (2, 4),
            11: (3, 1), 12: (3, 2), 49: (3, 3), 50: (3, 4)}

# (left_sheet, right_sheet, col_of_left, row)
VSEAMS = [(7, 8, 1, 1), (9, 10, 1, 2), (11, 12, 1, 3),
          (8, 39, 2, 1), (10, 43, 2, 2), (12, 49, 2, 3),
          (39, 40, 3, 1), (43, 44, 3, 2), (49, 50, 3, 3)]
# (top_sheet, bottom_sheet, col, row_of_top)
HSEAMS = [(7, 9, 1, 1), (8, 10, 2, 1), (39, 43, 3, 1), (40, 44, 4, 1),
          (9, 11, 1, 2), (10, 12, 2, 2), (43, 49, 3, 2), (44, 50, 4, 2)]

VBOUND = {1: ("Ave C (Mechanic)", 70.0), 2: ("Ave F (Church)", 70.0),
          3: ("Ave I (Sealy)", 80.0)}
HBOUND = {1: ("21st or Center St", 80.0), 2: ("24th St", 80.0)}
ROW_STREETS = {1: ["19th St", "20th St"], 2: ["22nd St", "23rd St"],
               3: ["25th St", "26th St"]}
COL_AVES = {1: ["Ave B", "Ave B-east"], 2: ["Ave D", "Ave E"],
            3: ["Ave G", "Ave H"], 4: ["Ave J", "Ave K"]}

FACE_OFF = 30.0 * KAPPA_TRUE     # crossing-street half width (60 ft street)
SEG_LEN = 300.0                  # face segment length, px
DRAFT_ACROSS_SIGMA = 8.0         # per-anchor drafting scatter across the seam


def make_truth(rng):
    truth = {}
    for sheet, (r, c) in SHEET_RC.items():
        if sheet == solver.DATUM_SHEET:
            truth[sheet] = np.array([1.0, 0.0, 0.0, 0.0])
            continue
        th = math.radians(rng.uniform(-0.5, 0.5))
        s = rng.uniform(0.995, 1.005)
        truth[sheet] = np.array([
            s * math.cos(th), s * math.sin(th),
            (c - 2) * DX + rng.uniform(-30, 30),
            (r - 2) * DY + rng.uniform(-30, 30)])
    return truth


def to_sheet(params, pm):
    """mosaic point -> raw sheet pixels (inverse of the centered similarity)."""
    a, b, tx, ty = params
    det = a * a + b * b
    dx, dy = pm[0] - tx, pm[1] - ty
    return np.array([(a * dx + b * dy) / det + CENTER[0],
                     (-b * dx + a * dy) / det + CENTER[1]])


def _side_record(sheet, segs_m, truth, rng, sigma):
    """Convert mosaic-truth segments to a noisy sheet-side record."""
    rec = {"sheet": sheet, "measured_at": "synthetic corner adjacent to seam",
           "sigma_along_px": round(sigma, 2),
           "sigma_basis": "synthetic clean rule",
           "source_sha256": "synthetic-selftest"}
    for name, seg in segs_m.items():
        pts = []
        for pm in seg:
            p = to_sheet(truth[sheet], pm) + rng.normal(0.0, sigma, size=2)
            pts.append([round(float(p[0]), 2), round(float(p[1]), 2)])
        rec[name] = pts
    return rec


def _anchor_entry(name, A_sheet, B_sheet, segsA, segsB, truth, rng, w_ft):
    sA = rng.uniform(1.2, 2.0)
    sB = rng.uniform(1.2, 2.0)
    scaleA = math.hypot(*truth[A_sheet][:2])
    scaleB = math.hypot(*truth[B_sheet][:2])
    dwA = (w_ft * KAPPA_TRUE + rng.normal(0, 4.0)) / scaleA
    dwB = (w_ft * KAPPA_TRUE + rng.normal(0, 4.0)) / scaleB
    return {
        "anchor": name, "status": "ACCEPTED", "class": "observed",
        "why_not_one_block_off": "synthetic ground truth; identity by construction",
        "anchor_evidence": "synthetic",
        "A": _side_record(A_sheet, segsA, truth, rng, sA),
        "B": _side_record(B_sheet, segsB, truth, rng, sB),
        "drafted_width_px": {"A": round(dwA, 1), "B": round(dwB, 1),
                             "annotation": f"{w_ft:.0f}' printed mid-street"},
        "evidence_crops": [], "notes": "synthetic",
    }


def gen_dataset(dirpath, rng, weak_seams=None, drop_seams=None):
    """Write synthetic pair_*.json files.  weak_seams: seam keys keeping only
    their first anchor; drop_seams: seam keys not written at all."""
    weak_seams = weak_seams or set()
    drop_seams = drop_seams or set()
    truth = make_truth(rng)
    os.makedirs(dirpath, exist_ok=True)

    for A, B, c, r in VSEAMS:
        key = f"{A}-{B}"
        if key in drop_seams:
            continue
        boundary, w_ft = VBOUND[c]
        sx = (c - 2) * DX + 3000.0
        halfw = w_ft * KAPPA_TRUE / 2.0
        controls = []
        names = ROW_STREETS[r]
        ys_list = [(r - 2) * DY - 1600.0, (r - 2) * DY + 1600.0]
        for name, ys in zip(names, ys_list):
            d = rng.normal(0.0, DRAFT_ACROSS_SIGMA)
            cornerA = sx - halfw - d / 2.0
            cornerB = sx + halfw + d / 2.0
            segsA = {"face1_seg": [[cornerA - SEG_LEN, ys - FACE_OFF],
                                   [cornerA, ys - FACE_OFF]],
                     "face2_seg": [[cornerA - SEG_LEN, ys + FACE_OFF],
                                   [cornerA, ys + FACE_OFF]]}
            segsB = {"face1_seg": [[cornerB, ys - FACE_OFF],
                                   [cornerB + SEG_LEN, ys - FACE_OFF]],
                     "face2_seg": [[cornerB, ys + FACE_OFF],
                                   [cornerB + SEG_LEN, ys + FACE_OFF]]}
            controls.append(_anchor_entry(name, A, B, segsA, segsB,
                                          truth, rng, w_ft))
        if key in weak_seams:
            controls = controls[:1]
        payload = {"pair": [A, B], "axis": "vertical", "boundary": boundary,
                   "observer": "test_solver-synthetic", "controls": controls}
        with open(os.path.join(dirpath, f"pair_{A}_{B}.json"), "w") as fh:
            json.dump(payload, fh, indent=1)

    for A, B, c, r in HSEAMS:
        key = f"{A}-{B}"
        if key in drop_seams:
            continue
        boundary, w_ft = HBOUND[r]
        sy = (r - 2) * DY + 3500.0
        halfw = w_ft * KAPPA_TRUE / 2.0
        controls = []
        names = COL_AVES[c]
        xs_list = [(c - 2) * DX - 1500.0, (c - 2) * DX + 1500.0]
        for name, xa in zip(names, xs_list):
            d = rng.normal(0.0, DRAFT_ACROSS_SIGMA)
            cornerA = sy - halfw - d / 2.0
            cornerB = sy + halfw + d / 2.0
            segsA = {"face1_seg": [[xa - FACE_OFF, cornerA - SEG_LEN],
                                   [xa - FACE_OFF, cornerA]],
                     "face2_seg": [[xa + FACE_OFF, cornerA - SEG_LEN],
                                   [xa + FACE_OFF, cornerA]]}
            segsB = {"face1_seg": [[xa - FACE_OFF, cornerB],
                                   [xa - FACE_OFF, cornerB + SEG_LEN]],
                     "face2_seg": [[xa + FACE_OFF, cornerB],
                                   [xa + FACE_OFF, cornerB + SEG_LEN]]}
            controls.append(_anchor_entry(name, A, B, segsA, segsB,
                                          truth, rng, w_ft))
        if key in weak_seams:
            controls = controls[:1]
        payload = {"pair": [A, B], "axis": "horizontal", "boundary": boundary,
                   "observer": "test_solver-synthetic", "controls": controls}
        with open(os.path.join(dirpath, f"pair_{A}_{B}.json"), "w") as fh:
            json.dump(payload, fh, indent=1)

    return truth


# Absolute floors added to the 3-sigma tolerances (guard against the s0
# variance-factor's own estimation noise; small vs any real failure mode).
FLOOR_THETA_RAD = 0.10e-3
FLOOR_S_REL = 50e-6
FLOOR_T_PX = 1.0


def check_recovery(result, truth, sheets, label):
    """Assert recovered params within 3x propagated sigma (+floors)."""
    problems = []
    for sheet in sheets:
        if sheet == solver.DATUM_SHEET or sheet not in result["params"]:
            continue
        rec, tru = result["params"][sheet], truth[sheet]
        m = result["marginals"][sheet]
        th_r = math.atan2(rec[1], rec[0])
        th_t = math.atan2(tru[1], tru[0])
        s_r = math.hypot(rec[0], rec[1])
        s_t = math.hypot(tru[0], tru[1])
        checks = [
            ("theta", abs(th_r - th_t),
             3 * m["theta_std_mrad"] * 1e-3 + FLOOR_THETA_RAD),
            ("s_rel", abs(s_r - s_t) / s_t,
             3 * m["s_std_ppm"] * 1e-6 + FLOOR_S_REL),
            ("tx", abs(rec[2] - tru[2]), 3 * m["tx_std_px"] + FLOOR_T_PX),
            ("ty", abs(rec[3] - tru[3]), 3 * m["ty_std_px"] + FLOOR_T_PX),
        ]
        for pname, err, tol in checks:
            if not (err <= tol):
                problems.append(f"sheet {sheet} {pname}: err {err:.4g} > tol {tol:.4g}")
    k_err = abs(result["kappa"] - KAPPA_TRUE)
    k_tol = 3 * result["kappa_std"] + 0.005
    if not (k_err <= k_tol):
        problems.append(f"kappa: err {k_err:.4g} > tol {k_tol:.4g}")
    if problems:
        raise AssertionError(f"[{label}] recovery outside 3-sigma:\n  "
                             + "\n  ".join(problems))


def run_case(tmp, name, rng, **gen_kwargs):
    cdir = os.path.join(tmp, name)
    truth = gen_dataset(cdir, rng, **gen_kwargs)
    return cdir, truth


def main():
    tmp = tempfile.mkdtemp(prefix="g1912_solver_test_")
    passed = failed = 0

    def report(label, fn):
        nonlocal passed, failed
        try:
            fn()
            print(f"PASS  {label}")
            passed += 1
        except Exception as exc:
            print(f"FAIL  {label}: {exc}")
            traceback.print_exc()
            failed += 1

    rng = np.random.default_rng(SEED)
    full_dir, full_truth = run_case(tmp, "full", rng)
    out_dir = os.path.join(tmp, "out_full")
    full_result = solver.run_solve(full_dir, out_dir, ADJACENCY,
                                   run_loso=True, write_outputs=True)

    # ---- Test 1: full-network ground-truth recovery -------------------------
    def t1():
        assert full_result is not None, "solver returned no result"
        assert full_result["unsolved_sheets"] == [], \
            f"unsolved: {full_result['unsolved_sheets']}"
        check_recovery(full_result, full_truth, solver.SHEETS, "full")
        assert 0.2 < full_result["s0_sq"] < 3.0, \
            f"variance factor implausible: {full_result['s0_sq']:.3f}"
        # interior sheet 43 (four seams) must not carry a rotation flag
        assert not full_result["marginals"][43]["flag_rotation"], \
            "well-connected sheet 43 unexpectedly rotation-flagged"
        # output files written and parseable
        for f in ("transforms.json", "residuals.json", "covariance.json"):
            with open(os.path.join(out_dir, f)) as fh:
                json.load(fh)
        assert os.path.exists(os.path.join(out_dir, "diagnostics.md"))
        # collinearity: all six numbered streets present, deviations bounded
        streets = {c["street"] for c in full_result["collinearity"]}
        for st in ("19th St", "20th St", "22nd St", "23rd St",
                   "25th St", "26th St"):
            assert st in streets, f"collinearity missing {st}"
        for c in full_result["collinearity"]:
            assert c["max_perp_deviation_px"] < 20.0, \
                f"{c['street']} deviation {c['max_perp_deviation_px']:.1f} px"
        kinked = [c for c in full_result["collinearity"] if "ave_i_kink" in c]
        assert len(kinked) == 6, f"Ave I kink computed for {len(kinked)} streets, want 6"
    report("full-network parameter recovery within 3x propagated sigma "
           "(+ outputs written, collinearity/kink computed)", t1)

    # ---- Test 2: covariance flag fires on a weakened corner sheet ----------
    def t2():
        rng2 = np.random.default_rng(SEED)  # same truth, same noise stream
        weak_dir, weak_truth = run_case(tmp, "weak40", rng2,
                                        weak_seams={"39-40", "40-44"})
        res = solver.run_solve(weak_dir, os.path.join(tmp, "out_weak"),
                               ADJACENCY, write_outputs=False)
        assert res is not None
        base_std = full_result["marginals"][40]["theta_std_mrad"]
        weak_std = res["marginals"][40]["theta_std_mrad"]
        assert weak_std > base_std, \
            f"weakening did not inflate sheet-40 rotation std " \
            f"({weak_std:.2f} vs {base_std:.2f} mrad)"
        assert res["marginals"][40]["flag_rotation"], \
            f"rotation flag did not fire on weakened sheet 40 " \
            f"(std {weak_std:.2f} mrad)"
        # weakened solution still statistically consistent with truth
        check_recovery(res, weak_truth, solver.SHEETS, "weak40")
    report("rotation-covariance flag fires on weakened corner sheet 40", t2)

    # ---- Test 3: leave-one-seam-out degrades gracefully --------------------
    def t3():
        loso = full_result["loso"]
        assert loso is not None and len(loso) == 17, \
            f"expected 17 LOSO entries, got {loso and len(loso)}"
        for r in loso:
            assert r["status"] == "ok", f"seam {r['seam']}: {r['status']}"
            assert np.isfinite(r["pred_rms_px"]), f"seam {r['seam']}: non-finite"
            assert r["pred_rms_px"] < 40.0, \
                f"seam {r['seam']} LOSO prediction RMS {r['pred_rms_px']:.1f} px"
    report("leave-one-seam-out refits all 17 seams with bounded prediction "
           "error", t3)

    # ---- Test 4: partial data (missing seam files) tolerated ---------------
    def t4():
        rng4 = np.random.default_rng(SEED)
        part_dir, part_truth = run_case(tmp, "partial", rng4,
                                        drop_seams={"39-40", "40-44"})
        res = solver.run_solve(part_dir, os.path.join(tmp, "out_partial"),
                               ADJACENCY, write_outputs=True)
        assert res is not None
        assert res["unsolved_sheets"] == [40], \
            f"expected sheet 40 unsolved, got {res['unsolved_sheets']}"
        solved = [s for s in solver.SHEETS if s != 40]
        assert res["solved_sheets"] == sorted(solved)
        check_recovery(res, part_truth, solved, "partial")
    report("partial data: missing seam files tolerated, disconnected sheet "
           "reported, remainder recovered", t4)

    print(f"\n{passed} passed, {failed} failed  "
          f"({'ALL PASS' if failed == 0 else 'FAILURES PRESENT'})")
    shutil.rmtree(tmp, ignore_errors=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

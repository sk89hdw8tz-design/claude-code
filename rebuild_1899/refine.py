#!/usr/bin/env python3
"""Refine loop: re-measure seam matches predicting through the solved
transforms (tight search), then re-solve. Run after solve2.py has produced
out/affine_1899.json.
"""
import importlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import measure  # noqa: E402

aff = json.load(open(os.path.join(ROOT, "out", "affine_1899.json")))["sheets"]
measure.TRANSFORMS = aff

lm_out = measure.verify_landmarks()
from collections import Counter
print("landmarks:", Counter(r["verdict"] for r in lm_out))

seams, matches = [], {}
for ctx in measure.PAIR_CTX:
    # transforms already carry the geometry: no extra bias, tight search
    s, recs = measure.measure_pair(ctx, lm_bias=None)
    seams.append(s)
    matches[f"{ctx['owner']}|{ctx['nbr']}"] = recs
    print(f"  {ctx['owner']}|{ctx['nbr']:>2} {ctx['boundary']:<14} "
          f"n={s['n_candidates_matched']:3d} med={s['pred_err_median']}")

out = json.load(open(os.path.join(ROOT, "out", "r1_measurements.json")))
out["landmark_verification"] = lm_out
out["seam_summaries"] = seams
out["seam_matches"] = matches
out["note"] = "refined pass: predictions through solved affine_1899.json"
json.dump(out, open(os.path.join(ROOT, "out", "r1_measurements.json"), "w"), indent=1)
print("re-measured; re-solving...")
subprocess.run([sys.executable, os.path.join(ROOT, "solve2.py")], check=True)

#!/usr/bin/env python3
"""Re-measure the dense seam matches with per-pair biases from the
consolidated landmark set (landmarks_v2), so the dense population and the
landmark constraints describe the same lock. Pairs whose dense matches
still sit far from the landmark-implied offset get their dense matches
DROPPED (landmarks only) and are flagged in the output.
"""
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import measure  # noqa: E402

v2 = json.load(open(os.path.join(ROOT, "out", "landmarks_v2.json")))["features"]
KEEP = {"confirmed", "adopted-R", "adopted-L", "matcher-only", "agent-new"}

def lm_bias_v2():
    acc = {}
    for f in v2:
        if f["status"] not in KEEP or f.get("schematic"):
            continue
        a, b = f["pair"]
        px, py = measure.predict_on_b(a, b, f["a_xy"])
        e = (f["b_xy"][0] - px, f["b_xy"][1] - py)
        acc.setdefault((a, b), []).append(e)
        acc.setdefault((b, a), []).append((-e[0], -e[1]))
    return {k: (float(np.median([e[0] for e in v])),
                float(np.median([e[1] for e in v])))
            for k, v in acc.items()}

bias = lm_bias_v2()
out = json.load(open(os.path.join(ROOT, "out", "r1_measurements.json")))
seams, matches = [], {}
flags = {}
for ctx in measure.PAIR_CTX:
    a, b = ctx["owner"], ctx["nbr"]
    key = f"{a}|{b}"
    s, recs = measure.measure_pair(ctx, lm_bias=bias)
    # compare dense median offset to the landmark bias; > 18 px apart on
    # either axis means the dense lock disagrees with verified landmarks
    if recs and (a, b) in bias:
        med = (float(np.median([m["pred_err"][0] for m in recs])),
               float(np.median([m["pred_err"][1] for m in recs])))
        lb = bias[(a, b)]
        gap = (abs(med[0] + 0 - 0), abs(med[1]))  # pred_err already includes bias
        if max(abs(med[0]), abs(med[1])) > 18:
            flags[key] = {"dense_vs_landmark_px": [round(med[0], 1), round(med[1], 1)],
                          "action": "dense dropped, landmarks only"}
            recs = []
    seams.append(s)
    matches[key] = recs
    print(f"  {key:6} {ctx['boundary']:<14} n={len(recs):3d} "
          f"{'FLAGGED' if key in flags else ''}")
out["seam_matches"] = matches
out["seam_summaries"] = seams
out["dense_flags"] = flags
out["note"] = "re-measured with landmarks_v2 biases; disagreeing pairs dropped to landmark-only"
json.dump(out, open(os.path.join(ROOT, "out", "r1_measurements.json"), "w"), indent=1)
print("flags:", json.dumps(flags, indent=1))

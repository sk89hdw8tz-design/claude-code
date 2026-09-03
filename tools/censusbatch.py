#!/usr/bin/env python3
"""Build census batches from the seam crop index.

    python3 tools/censusbatch.py --year 1912 --per 2 --out outputs/1912/qc/seams/census_round5_batches.json

Each batch is a list of seams, each with its crop file names, ready to hand
to a grader (one agent per batch).
"""
import argparse
import json
import os

ap = argparse.ArgumentParser()
ap.add_argument("--year", type=int, default=1912)
ap.add_argument("--per", type=int, default=2)
ap.add_argument("--out", required=True)
a = ap.parse_args()

idx = json.load(open(f"outputs/{a.year}/qc/seams/index.json"))["seams"]
seams = []
for s in idx:
    tag = "_".join(s["pair"])
    crops = sorted({c["crop_100"].split("/")[-1] for c in s.get("crops", [])}
                   | ({s["crop_100"].split("/")[-1]} if s.get("crop_100") else set()))
    crops = [c for c in crops if os.path.exists(f"outputs/{a.year}/qc/seams/{c}")]
    if not crops:
        continue
    seams.append({"seam": tag, "kind": s["kind"], "axis": s["axis"],
                  "corridor": s.get("corridor"), "how": s["how"],
                  "overlap_px2": s.get("overlap_px2"), "crops": crops})
seams.sort(key=lambda z: z["seam"])
batches = [seams[i:i + a.per] for i in range(0, len(seams), a.per)]
json.dump(batches, open(a.out, "w"), indent=1)
print(f"{len(seams)} seams, {len(batches)} batches of {a.per} -> {a.out}")

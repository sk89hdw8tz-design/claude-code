#!/usr/bin/env python3
"""Write outputs/{year}/coverage.png — the brief's §5 coverage picture.

One polygon per placed unit in the year's mosaic frame, coloured by how its
transform was obtained: the frozen downtown core the 27x40 master covers in
one colour, every sheet added by the city-wide expansion in others. Units
listed in the recipe but never placed are drawn hatched so gaps are obvious.

    python3 tools/coverage.py --year 1899
"""
import argparse
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                      # noqa: E402
from matplotlib.patches import Polygon as MplPolygon  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# tier -> (face, edge, label); "core" is the master's own footprint
STYLE = {
    "core":            ("#c8961e", "#7a5a0a", "master core (frozen)"),
    "fit":             ("#3d7ab8", "#1f4670", "fitted to neighbours"),
    "tie-fit":         ("#5fa8d3", "#2c6b94", "tie-fit (similarity)"),
    "tie-translation": ("#8fc4e0", "#4a7f9c", "tie-placed (translation)"),
    "tie-single":      ("#d6a86a", "#8a6a34", "single-tie fallback"),
    "prior-unverified": ("#c0524a", "#7a2f29", "prior, unverified"),
}
UNKNOWN = ("#999999", "#555555", "other")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", choices=["1899", "1912"], required=True)
    ap.add_argument("--out")
    a = ap.parse_args()

    rec = os.path.join(REPO, "outputs", a.year, "recipe")
    gj = json.load(open(os.path.join(rec, "sheets_city.geojson")))
    units = json.load(open(os.path.join(rec, "units.json")))["units"]

    placed = {str(f["properties"]["unit"]) for f in gj["features"]}
    missing = sorted(set(map(str, units)) - placed)

    fig, ax = plt.subplots(figsize=(11, 14))
    seen, counts = {}, {}
    for f in gj["features"]:
        tier = f["properties"].get("tier", "?")
        face, edge, label = STYLE.get(tier, UNKNOWN)
        counts[tier] = counts.get(tier, 0) + 1
        ring = f["geometry"]["coordinates"][0]
        ax.add_patch(MplPolygon(ring, closed=True, facecolor=face,
                                edgecolor=edge, linewidth=0.6, alpha=0.85,
                                label=None if tier in seen else label))
        seen[tier] = True
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        ax.text(sum(xs) / len(xs), sum(ys) / len(ys),
                str(f["properties"]["unit"]), ha="center", va="center",
                fontsize=5.5, color="#1a1a1a")

    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.invert_yaxis()          # mosaic frame is image coords: +y is down
    ax.set_xlabel("mosaic x (px)")
    ax.set_ylabel("mosaic y (px)")
    tally = ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
    # a unit carried over unverified is drawn, but it is not a placement
    unver = sorted(str(f["properties"]["unit"]) for f in gj["features"]
                   if f["properties"].get("tier") == "prior-unverified")
    head = f"{len(placed) - len(unver)}/{len(units)} units placed"
    if unver:
        head += f", {len(unver)} carried over unverified ({', '.join(unver)})"
    ax.set_title(f"Galveston {a.year} — full-city coverage\n"
                 f"{head}  ({tally})"
                 + (f"\nnot placed: {', '.join(missing)}" if missing else ""),
                 fontsize=11)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.9)
    ax.grid(True, linewidth=0.3, alpha=0.3)

    out = a.out or os.path.join(REPO, "outputs", a.year, "coverage.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out, dpi=140, bbox_inches="tight")
    print(f"{out}  ({head}"
          + (f", missing {missing}" if missing else "") + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())

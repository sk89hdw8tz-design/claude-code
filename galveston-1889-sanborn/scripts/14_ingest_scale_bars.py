#!/usr/bin/env python3
"""Ingest the printed "Scale of Feet" bar measured on each of the eight sheets.

Two INDEPENDENT passes exist for every sheet and both are recorded:

  pass A  one examiner per sheet, working by eye at 16-30x zoom on a
          1-source-pixel grid overlay, reading tick centres directly;
  pass B  one reviewer over all eight sheets with a single automated method
          (morphological location of the bar, robust fit of its top edge to
          absorb tilt, ink integration in an 8-row band above that edge so the
          numerals and bar body are excluded, then a background-subtracted
          intensity centroid per tick).

They agree to 0.10% or better on every sheet, so the bar itself is measured
about as well as this material allows.  The ADOPTED value is pass B's
five-tick least-squares fit, because it is the only estimator produced by one
uniform procedure on all eight sheets -- which is what a *relative* scale
comparison requires.

Writes metadata/source_scale_measurements.csv and output/qc/scale_comparison.csv.
"""
from __future__ import annotations

import csv
import json
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
NOMINAL_PPF = 3.000        # 1 in = 100 ft plate scanned at 300 dpi

# pass A -- per-sheet examiner. (file, primary px/ft, span ft, sigma px/endpoint)
PASS_A = {
    "1":  ("sheet01_scalebar.json",             3.0284, 200, 0.8),
    "2":  ("sheet2_scalebar.json",              3.0586, 150, 1.0),
    "7":  ("sheet07-scalebar-source-examiner.json", 3.0567, 150, 1.0),
    "8":  ("sheet08_scalebar.json",             3.0260, 150, 1.0),
    "9":  ("sheet9-scalebar.json",              3.0310, 200, 0.8),
    "10": ("sheet10-scalebar-examiner.json",    3.0456, 200, 1.0),
    "27": ("sheet27-scalebar.json",             3.0713, 150, 0.7),
    "29": ("scalebar_sheet29.json",             3.0382, 200, 0.8),
}

REVIEW = ROOT / "gcps" / "manual" / "REVIEW_independent_scale_and_seam_audit.json"


def main() -> int:
    review = json.loads(REVIEW.read_text())["scale"]

    rows = []
    for sheet, (fname, ppf_a, span_ft, sigma) in PASS_A.items():
        detail = json.loads((ROOT / "gcps" / "manual" / fname).read_text())
        r = review[sheet]
        ticks = r["my_ticks_m50_0_50_100_150"]
        adopted = r["my_ppf_lsq_5tick"]
        # An endpoint uncertainty of `sigma` px over a `span_ft` baseline
        # propagates to sqrt(2)*sigma/span_ft in px/ft.
        sigma_ppf = (2 ** 0.5) * sigma / span_ft
        rows.append({
            "sheet": sheet,
            "source_file": detail.get("source_file") or detail.get("file", ""),
            "scale_bar_present": "yes",
            "printed_scale_statement": "Scale of Feet.",
            "tick_x_minus50": round(ticks[0], 2),
            "tick_x_0": round(ticks[1], 2),
            "tick_x_50": round(ticks[2], 2),
            "tick_x_100": round(ticks[3], 2),
            "tick_x_150": round(ticks[4], 2),
            "passA_px_per_ft": round(ppf_a, 4),
            "passA_span_ft": span_ft,
            "passA_sigma_px_per_endpoint": sigma,
            "passB_px_per_ft_0_150": round(r["my_ppf_0to150"], 4),
            "passB_px_per_ft_m50_150": round(r["my_ppf_m50to150"], 4),
            "passB_px_per_ft_lsq5": round(adopted, 4),
            "passA_vs_passB_pct": round(100.0 * (ppf_a - adopted) / adopted, 3),
            "adopted_px_per_ft": round(adopted, 4),
            "adopted_sigma_px_per_ft": round(sigma_ppf, 4),
            "vs_nominal_3.000_pct": round(100.0 * (adopted - NOMINAL_PPF) / NOMINAL_PPF, 2),
            "method": "passA: examiner at 16-30x on 1-src-px grid; passB: uniform automated tick centroid",
            "status": "measured",
        })

    rows.sort(key=lambda r: float(r["sheet"]))
    out1 = ROOT / "metadata" / "source_scale_measurements.csv"
    with out1.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    adopted = {r["sheet"]: r["adopted_px_per_ft"] for r in rows}
    mean = statistics.fmean(adopted.values())
    lo, hi = min(adopted.values()), max(adopted.values())

    out2 = ROOT / "output" / "qc" / "scale_comparison.csv"
    out2.parent.mkdir(parents=True, exist_ok=True)
    with out2.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["sheet", "adopted_px_per_ft", "sigma_px_per_ft",
                    "relative_to_mean", "pct_from_mean", "vs_nominal_pct"])
        for r in rows:
            a = r["adopted_px_per_ft"]
            w.writerow([r["sheet"], a, r["adopted_sigma_px_per_ft"],
                        round(a / mean, 5), round(100.0 * (a - mean) / mean, 3),
                        r["vs_nominal_3.000_pct"]])
        w.writerow([])
        w.writerow(["mean", round(mean, 4), "", 1.0, 0.0,
                    round(100.0 * (mean - NOMINAL_PPF) / NOMINAL_PPF, 2)])
        w.writerow(["spread_pct", round(100.0 * (hi - lo) / mean, 3)])

    print(f"wrote {out1.relative_to(ROOT)} and {out2.relative_to(ROOT)}")
    print(f"  8 sheets, adopted mean {mean:.4f} px/ft, "
          f"range {lo:.4f}-{hi:.4f} = {100.0 * (hi - lo) / mean:.2f}% spread")
    worst = max(abs(float(r["passA_vs_passB_pct"])) for r in rows)
    print(f"  worst pass-A vs pass-B disagreement: {worst:.3f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Ingest the semantically-identified, hand-measured seam control into one CSV.

Every row here is a physical feature that a human-level reader IDENTIFIED on
both sheets by its printed evidence -- lettered avenue names, block numbers,
water-main diameters and the exact point where a main changes size, named
buildings, terminal ends of the drawn area -- and only then measured.  Nothing
in this file came from blind template matching, NCC or RANSAC; those were tried
three ways on this material and are documented in research/experiment_log.md as
producing confident *wrong* matches on the repeating street grid.

Each row carries `uncertainty_px`, the observer's honest standard error for
that point.  The adjustment weights by 1/sigma^2, so a hydrant symbol placed by
eye at +/-20 px cannot outvote a lettered block corner at +/-3 px.

Where a second, independent reviewer re-measured a point, the two measurements
are AVERAGED and the uncertainty is inflated to at least 1.5x their
disagreement, so a quiet difference of convention shows up as honest error
rather than as false precision.

Writes gcps/tiepoints_verified.csv and gcps/manual/workflow_results.json.
"""
from __future__ import annotations

import csv
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANUAL = ROOT / "gcps" / "manual"

# sheet id as printed  ->  region id used throughout the pipeline
REGION = {"1": "S1_main", "2": "S2", "7": "S7", "8": "S8",
          "9": "S9", "10": "S10", "27": "S27", "29": "S29"}

FIELDS = ["point_id", "sheet", "region", "role", "src_x", "src_y",
          "ref_x", "ref_y", "ref_lon", "ref_lat", "street_a", "street_b",
          "feature", "category", "control_class", "method", "confidence",
          "selected_by", "uncertainty_px", "sigma_x_px", "sigma_y_px",
          "residual_px", "accepted", "note"]

# --------------------------------------------------------------------------
# Which seams share INKED ground, and which construct their tie.
#
# Sheets that abut along a numbered street overlap: both plates draw the whole
# roadway (each its own kerb as block frontage, the far kerb as the outer rule
# of its continuation boxes), so a corner is genuinely inked on both and the
# tie is measured in both axes.
#
# Sheets that abut along a lettered AVENUE frequently share nothing at all.
# Sheet 8 stops on the west line of Av. G and sheet 29 begins on the east
# line; the 70-ft roadway between is drawn by neither. The tie is then built
# by stepping half the PRINTED width inward from each plate's own frontage.
# That construction is sound along the seam, where real crossing lines fix the
# station, but across the seam it rests entirely on the printed figure -- and
# the plates are observed to disagree about a drawn avenue width by up to 9 px
# (sheet 1 draws Av. A 224 px wide where sheet 2 draws it 215 px).
#
# So those ties get an inflated sigma on the ACROSS-seam axis only. Every one
# of these seams runs vertically down the page, so across = x.
CONSTRUCTED_ACROSS_SIGMA_PX = 10.0
CONSTRUCTED_SEAMS = {
    ("S10", "S9"):  ("x", "Av. D: no duplicated feature; each plate draws only "
                          "its own frontage, centreline stepped from printed 70 ft"),
    ("S29", "S8"):  ("x", "Av. G: overlap_exists=no; the roadway is drawn by "
                          "neither plate"),
    ("S10", "S27"): ("x", "Av. G: no duplicated map detail; ~55-60 ft of empty "
                          "roadway between the two drawn limits"),
}


def axis_sigmas(region_a: str, region_b: str, sigma: float) -> tuple[float, float, str]:
    """(sigma_x, sigma_y, note) for one tie."""
    entry = CONSTRUCTED_SEAMS.get(tuple(sorted((region_a, region_b))))
    if not entry:
        return sigma, sigma, ""
    axis, why = entry
    loose = max(sigma, CONSTRUCTED_ACROSS_SIGMA_PX)
    if axis == "x":
        return loose, sigma, f"across-seam sigma inflated to {loose:.0f}px -- {why}"
    return sigma, loose, f"across-seam sigma inflated to {loose:.0f}px -- {why}"

# Two classes of control, and they are NOT interchangeable.
#
#   geometric  a corner, a property line, a pipe junction -- a place where two
#              drawn LINES meet.  Both draftsmen were copying the same survey,
#              so these must agree, and a disagreement here is a real defect
#              in the reconstruction.
#
#   symbol     a fire plug, hydrant or valve disc.  Sanborn draftsmen placed
#              these by eye somewhere in the street, not by survey; the same
#              plug is drawn up to ~45 px (15 ft) apart on two plates of one
#              edition.  That is a fact about the 1889 source and no transform
#              can remove it.  Symbol points stay in the solve at their honest
#              (large) sigma, where they carry almost no weight, but they are
#              EXCLUDED from seam grading -- grading a seam on them would
#              condemn a correct reconstruction.  They are reported separately
#              as drafting scatter.
SYMBOL_WORDS = ("fire plug", "hydrant", "valve", "plug")


def control_class(category: str, feature: str) -> str:
    """Classify by the STRUCTURED category, never by an incidental mention.

    Observers routinely use a nearby plug to argue that a corner is the right
    corner ("...with a fire plug 29 px south-east of it").  Scanning the free
    text for symbol words demotes exactly those well-argued corners, so the
    category field decides whenever it is populated, and the text is consulted
    only when it is not.
    """
    cat = (category or "").strip().lower()
    if cat:
        return "symbol" if any(w in cat for w in SYMBOL_WORDS) else "geometric"
    # No category recorded: scan the whole description. Safe here precisely
    # because a file that names its features carefully enough to mention a
    # nearby plug as a landmark also fills in `category`, so it never lands in
    # this branch.
    hay = (feature or "").lower()
    return "symbol" if any(w in hay for w in SYMBOL_WORDS) else "geometric"

# --------------------------------------------------------------------------
# Independent re-measurements from the reviewer audit, keyed by the substring
# that identifies the correspondence in its own seam file.  Value is
# (sheet_a_xy, sheet_b_xy) or None for a coordinate the reviewer did not read.
# --------------------------------------------------------------------------
RECONCILE = [
    # seam, feature-substring, reviewer a (x,y), reviewer b (x,y), note
    ("S1_main|S2", "North-west corner of block 742",
     (2606.3, 140.3), (2551.0, 3686.3), ""),
    ("S1_main|S2", "North-east corner of block 742",
     (2979.5, 138.27), (2925.5, 3685.84),
     "reviewer x ~3px right on BOTH sheets (threshold-crossing vs "
     "last-solid-pixel convention); the differential agrees to 1px"),
    ("S27|S29", "West corner of the 20-ft alley mouth where it meets the NORTH",
     (1606.31, None), (1669.89, None), ""),
    ("S27|S29", "East corner of the same 20-ft alley mouth on the NORTH",
     (1662.20, None), (1729.64, None), ""),
    ("S27|S29", "West corner of the 20-ft alley mouth east of Av. I East",
     (2612.20, None), (2680.50, None), ""),
    ("S27|S29", "East corner of the same alley mouth on the NORTH",
     (2670.90, None), (2740.30, None), ""),
    ("S27|S29", "North-west corner of the Av. H East",
     (1020.50, None), (1084.50, None), ""),
    ("S27|S29", "North-east corner of the Av. H East",
     (1226.50, None), (1297.50, None), ""),
    ("S27|S29", "North-west terminus of the drawn 22nd St",
     (222.50, None), (288.50, None), ""),
    ("S27|S29", "North-east terminus",
     (3040.50, None), (3108.50, None), ""),
    ("S7|S9", "North-west corner of the Strand(Av.B)/22nd St",
     (1118.83, None), (1093.16, None),
     "sheet 7 draws two parallel lines ~6px apart at every avenue face "
     "(wall + awning edge); the choice cancels in the differential"),
    ("S7|S9", "North-east corner of the Strand(Av.B)/22nd St",
     (1355.41, None), (1332.48, None), ""),
    ("S7|S9", "North-west corner of the Market(Av.D)/22nd St",
     (3095.36, None), (3101.59, None), ""),
]

# The 6-inch tee on S7|S9 is NOT averaged: the reviewer showed the two passes
# picked different lines of the same double-dashed pipe, a 3.5 px systematic
# offset in dy.  The reviewer's pass is internally consistent (same convention
# on both sheets), so it REPLACES the original and the uncertainty is raised.
REPLACE = [
    ("S7|S9", "Water-main tee where the 22nd St main crosses the 6-inch",
     (2714.0, 3738.2), (2713.0, 282.2), 5.0,
     "reviewer replacement: original took the crossing centre on S7 but the "
     "upper dashed line on S9, a 3.5px systematic dy"),
]


def load_seams() -> list[dict]:
    """Normalise every seam JSON in gcps/manual/ to one shape."""
    seams = []
    for path in sorted(MANUAL.glob("*.json")):
        name = path.name
        if name.startswith("REVIEW") or "scalebar" in name.lower() \
                or name == "workflow_results.json":
            continue
        doc = json.loads(path.read_text())
        if "seam" not in doc:
            continue
        seams.append({"path": path, "doc": doc})
    return seams


# Seams where a later pass DIAGNOSED a specific, mechanical error in an
# earlier one, rather than merely differing from it. Averaging is right when
# two passes disagree for no identified reason -- neither is known to be
# better, so the mean is the best estimate and the spread is the honest
# uncertainty. It is wrong once the disagreement has a named cause, because
# then one reading is known to be biased and the mean inherits half the bias.
SUPERSEDES = {
    "S7|S9": ("seam_S7_S9_secondpass.json",
              "the first pass fitted ONE straight line to sheet 9's "
              "continuation-box rule across the whole plate; that rule is not "
              "straight (true slope about -0.0088 against the fitted "
              "-0.004977), so its error grows from 0.3 px at the west end to "
              "10.5 px at Av. D -- exactly the observed disagreement pattern. "
              "The second pass intersects lines fitted LOCALLY, within about "
              "150 px of each corner, which is immune to that. Where both "
              "passes are clean and independent they agree to 0.43 px."),
}


def merge_passes(seams, log_skips):
    """Fold independent re-measurements of the same seam into one control set.

    Where two observers worked the same seam without seeing each other's
    numbers, the pair of readings is worth more than either alone: the
    coordinate becomes their inverse-variance weighted mean, and the
    uncertainty becomes the combination of the two -- but never tighter than
    1.5x the disagreement they actually showed. Two passes that agree to
    0.3 px have earned a small sigma; two that differ by 4 px have not,
    whatever either one claims.

    Correspondences are paired only when BOTH endpoints land within 25 px on
    both plates, which on this material is unambiguous (the passes agree to
    about a pixel) while being far too tight to pair up neighbouring corners.
    Anything unpaired is carried through untouched.
    """
    by_seam = {}
    for entry in seams:
        by_seam.setdefault(entry["doc"]["seam"], []).append(entry)

    merged = []
    for seam, entries in by_seam.items():
        if len(entries) == 1:
            merged.append(entries[0])
            continue
        sup = SUPERSEDES.get(seam)
        if sup and any(e["path"].name == sup[0] for e in entries):
            base = next(e for e in entries if e["path"].name == sup[0])
            others = [e for e in entries if e is not base]
            log_skips.append(f"{seam}: {sup[0]} SUPERSEDES the earlier pass "
                             f"where they share a point -- {sup[1]}")
        else:
            entries.sort(key=lambda e: len(e["doc"].get("correspondences") or []),
                         reverse=True)
            base, others = entries[0], entries[1:]
            sup = None
        corr = [dict(c) for c in (base["doc"].get("correspondences") or [])]
        used = 0
        for other in others:
            for c2 in other["doc"].get("correspondences") or []:
                hit = None
                for c1 in corr:
                    if (abs(c1["a_x"] - c2["a_x"]) <= 25 and abs(c1["a_y"] - c2["a_y"]) <= 25
                            and abs(c1["b_x"] - c2["b_x"]) <= 25
                            and abs(c1["b_y"] - c2["b_y"]) <= 25):
                        hit = c1
                        break
                if hit is None:
                    corr.append(dict(c2))
                    continue
                if sup:
                    # Superseded: keep the trusted pass's coordinate and its
                    # own sigma untouched. Disagreement with a reading known to
                    # be biased says nothing about this one's precision, so it
                    # must not inflate it either.
                    dd = max(abs(hit[k] - c2[k])
                             for k in ("a_x", "a_y", "b_x", "b_y"))
                    hit["_merged"] = (f"supersedes {other['path'].name} here "
                                      f"(they differ by {dd:.2f} px); "
                                      f"coordinate and sigma are this pass's")
                    used += 1
                    continue
                s1 = float(hit.get("uncertainty_px", 8.0)) or 8.0
                s2 = float(c2.get("uncertainty_px", 8.0)) or 8.0
                w1, w2 = 1.0 / (s1 * s1), 1.0 / (s2 * s2)
                disagree = 0.0
                for k in ("a_x", "a_y", "b_x", "b_y"):
                    disagree = max(disagree, abs(hit[k] - c2[k]))
                    hit[k] = (w1 * hit[k] + w2 * c2[k]) / (w1 + w2)
                combined = (1.0 / (w1 + w2)) ** 0.5
                hit["uncertainty_px"] = round(max(combined, 1.5 * disagree), 2)
                hit["_merged"] = (f"merged with an independent pass "
                                  f"({other['path'].name}): the two readings "
                                  f"differ by at most {disagree:.2f} px, "
                                  f"sigma {s1:.1f}/{s2:.1f} -> "
                                  f"{hit['uncertainty_px']:.2f}")
                used += 1
        doc = dict(base["doc"])
        doc["correspondences"] = corr
        merged.append({"path": base["path"], "doc": doc})
        log_skips.append(f"{seam}: merged {len(entries)} independent passes, "
                         f"{used} correspondence(s) paired and averaged, "
                         f"{len(corr)} total")
    return merged


def sheet_ids(doc: dict) -> tuple[str, str]:
    """The two sheet numbers of a seam, whatever spelling the file used."""
    a = doc.get("sheet_a")
    b = doc.get("sheet_b")
    if isinstance(a, dict):
        a = a.get("id")
    if isinstance(b, dict):
        b = b.get("id")
    if a is None or b is None:
        left, right = doc["seam"].split("|")
        inv = {v: k for k, v in REGION.items()}
        a, b = inv[left.strip()], inv[right.strip()]
    return str(a), str(b)


def reconcile(seam: str, feature: str, a: list, b: list, sigma: float,
              log: list) -> tuple[list, list, float, str]:
    """Average in a second independent reading of the same point."""
    for s, sub, ra, rb, note in RECONCILE:
        if s != seam or sub.lower() not in feature.lower():
            continue
        disagree = 0.0
        for pt, rv in ((a, ra), (b, rb)):
            for i in (0, 1):
                if rv[i] is None:
                    continue
                disagree = max(disagree, abs(pt[i] - rv[i]))
                pt[i] = 0.5 * (pt[i] + rv[i])
        new_sigma = max(sigma, 1.5 * disagree)
        log.append({"seam": s, "feature": feature[:70],
                    "max_disagreement_px": round(disagree, 2),
                    "sigma_before": sigma, "sigma_after": round(new_sigma, 2)})
        extra = "; reconciled with independent reviewer " \
                f"(max disagreement {disagree:.2f}px)"
        return a, b, new_sigma, (note + extra if note else extra.lstrip("; "))
    return a, b, sigma, ""


def main() -> int:
    seams = load_seams()
    if not seams:
        print("no seam JSON found in gcps/manual/", file=sys.stderr)
        return 2

    rows: list[dict] = []
    summary: list[dict] = []
    recon_log: list[dict] = []
    log_skips: list[str] = []
    seams = merge_passes(seams, log_skips)

    for entry in seams:
        doc, path = entry["doc"], entry["path"]
        seam = doc["seam"]
        sa, sb = sheet_ids(doc)
        ra, rb = REGION[sa], REGION[sb]
        n_by_conf = {"high": 0, "medium": 0, "low": 0}

        corr = doc.get("correspondences") or []
        for i, c in enumerate(corr):
            feature = c.get("feature", "")
            pa = [float(c["a_x"]), float(c["a_y"])]
            pb = [float(c["b_x"]), float(c["b_y"])]
            sigma = float(c.get("uncertainty_px", 8.0))
            conf = c.get("confidence", "medium")
            note = ""

            replaced = False
            for s, sub, na, nb, nsig, nnote in REPLACE:
                if s == seam and sub.lower() in feature.lower():
                    pa, pb, sigma, note = list(na), list(nb), nsig, nnote
                    replaced = True
                    break
            if not replaced:
                pa, pb, sigma, note = reconcile(seam, feature, pa, pb,
                                                sigma, recon_log)
            if c.get("_merged"):
                note = f"{note}; {c['_merged']}".strip("; ")

            n_by_conf[conf] = n_by_conf.get(conf, 0) + 1
            sx, sy, axis_note = axis_sigmas(ra, rb, sigma)
            if axis_note:
                note = f"{note}; {axis_note}".strip("; ")
            pid = f"MV_{ra}_{rb}_{i:02d}"
            for sheet, region, p in ((sa, ra, pa), (sb, rb, pb)):
                rows.append({
                    "point_id": pid, "sheet": sheet, "region": region,
                    "role": "tie", "src_x": round(p[0], 2), "src_y": round(p[1], 2),
                    "ref_x": "", "ref_y": "", "ref_lon": "", "ref_lat": "",
                    "street_a": "", "street_b": "",
                    "feature": feature.replace("\n", " ")[:220],
                    "category": c.get("category", ""),
                    "control_class": control_class(c.get("category", ""), feature),
                    "method": "semantic identification from printed evidence, "
                              "then sub-pixel measurement on a 1-src-px grid overlay",
                    "confidence": conf, "selected_by": path.name,
                    "uncertainty_px": round(sigma, 2),
                    "sigma_x_px": round(sx, 2), "sigma_y_px": round(sy, 2),
                    "residual_px": "", "accepted": "true",
                    "note": note,
                })

        # ---- named boundary-line stations ---------------------------------
        # A sampled boundary line is only a set of CORRESPONDENCES when each
        # station was independently identified; a line sampled at "equal
        # fractions along" is interpolation dressed as measurement, and is
        # refused here. Stations are also skipped where the seam already has
        # plenty of point control, so the same feature is not counted twice.
        bl = doc.get("boundary_line") or {}
        names = bl.get("station_names") or []
        apts, bpts = bl.get("a_points") or [], bl.get("b_points") or []
        geo_so_far = sum(1 for c in corr
                         if control_class(c.get("category", ""), c.get("feature", ""))
                         == "geometric")
        if names and len(names) == len(apts) == len(bpts) and geo_so_far < 6:
            for j, (nm, pa_, pb_) in enumerate(zip(names, apts, bpts)):
                pid = f"MV_{ra}_{rb}_L{j:02d}"
                n_by_conf["medium"] = n_by_conf.get("medium", 0) + 1
                for sheet, region, pt in ((sa, ra, pa_), (sb, rb, pb_)):
                    rows.append({
                        "point_id": pid, "sheet": sheet, "region": region,
                        "role": "tie", "src_x": round(float(pt[0]), 2),
                        "src_y": round(float(pt[1]), 2),
                        "ref_x": "", "ref_y": "", "ref_lon": "", "ref_lat": "",
                        "street_a": "", "street_b": "",
                        "feature": f"{bl.get('name', 'shared boundary')} at {nm}"[:220],
                        "category": "boundary station",
                        "control_class": "geometric",
                        "method": "named station on the shared street line, "
                                  "sampled on both sheets",
                        "confidence": "medium", "selected_by": path.name,
                        "uncertainty_px": 6.0,
                        "sigma_x_px": round(axis_sigmas(ra, rb, 6.0)[0], 2),
                        "sigma_y_px": round(axis_sigmas(ra, rb, 6.0)[1], 2),
                        "residual_px": "", "accepted": "true",
                        "note": "boundary-line station (independently named, "
                                "not interpolated)",
                    })
        elif names and geo_so_far >= 6:
            log_skips.append(f"{seam}: boundary_line stations skipped -- "
                             f"{geo_so_far} point correspondences already cover it")
        elif apts and not names:
            log_skips.append(f"{seam}: boundary_line has no station_names, so its "
                             "points are interpolated, not identified -- refused")

        # ---- S10|S9: no duplicated point features exist across Av. D. -----
        # The only shared geometry is the avenue itself.  Each sheet draws the
        # frontage line of its OWN side; the common line is Av. D's centreline,
        # reached by stepping half the printed 70 ft width inward using that
        # sheet's own measured scale bar.  Recorded with a deliberately loose
        # sigma because any error in the printed width biases the seam.
        for j, bp in enumerate(doc.get("boundary_points") or []):
            ax, ay = bp.get(f"s{sa}_centreline_x"), bp.get(f"s{sa}_y")
            bx, by = bp.get(f"s{sb}_centreline_x"), bp.get(f"s{sb}_y")
            if None in (ax, ay, bx, by):
                continue
            pid = f"MV_{ra}_{rb}_B{j:02d}"
            n_by_conf["medium"] = n_by_conf.get("medium", 0) + 1
            for sheet, region, p in ((sa, ra, (ax, ay)), (sb, rb, (bx, by))):
                rows.append({
                    "point_id": pid, "sheet": sheet, "region": region,
                    "role": "tie", "src_x": round(float(p[0]), 2),
                    "src_y": round(float(p[1]), 2),
                    "ref_x": "", "ref_y": "", "ref_lon": "", "ref_lat": "",
                    "street_a": "", "street_b": "",
                    "feature": bp.get("latitude", "")[:220],
                    "category": "property line intersection",
                    "control_class": "geometric",
                    "method": "block frontage line crossing a street property "
                              "line, stepped to the shared avenue centreline "
                              "using the sheet's own measured scale bar",
                    "confidence": "medium", "selected_by": path.name,
                    "uncertainty_px": 6.0,
                    "sigma_x_px": round(axis_sigmas(ra, rb, 6.0)[0], 2),
                    "sigma_y_px": round(axis_sigmas(ra, rb, 6.0)[1], 2),
                    "residual_px": "", "accepted": "true",
                    "note": "constructed centreline: no duplicated point "
                            "feature exists across this seam",
                })

        summary.append({"seam": seam, "file": path.name,
                        "regions": [ra, rb],
                        "overlap": doc.get("overlap_exists") or doc.get("overlap", ""),
                        "n_correspondences": len(corr),
                        "n_boundary_points": len(doc.get("boundary_points") or []),
                        "by_confidence": n_by_conf,
                        "self_check": doc.get("self_check_similarity")
                                      or doc.get("similarity_check")
                                      or doc.get("transform_analysis")})

    out = ROOT / "gcps" / "tiepoints_verified.csv"
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    pairs, cls = {}, {}
    for r in rows:
        pairs.setdefault(r["point_id"], []).append(r["region"])
        cls[r["point_id"]] = r["control_class"]
    seam_counts: dict[tuple, dict] = {}
    for pid, regs in pairs.items():
        if len(regs) == 2:
            k = tuple(sorted(regs))
            c = seam_counts.setdefault(k, {"geometric": 0, "symbol": 0})
            c[cls[pid]] += 1

    results = {"seams": summary, "reconciliations": recon_log,
               "refused_or_skipped": log_skips,
               "verified_points_per_seam": {"|".join(k): v
                                            for k, v in sorted(seam_counts.items())},
               "control_classes": {"geometric": sum(1 for v in cls.values() if v == "geometric"),
                                   "symbol": sum(1 for v in cls.values() if v == "symbol")},
               "total_correspondences": len(pairs),
               "total_rows": len(rows)}
    (MANUAL / "workflow_results.json").write_text(json.dumps(results, indent=1))

    print(f"wrote {out.relative_to(ROOT)}: "
          f"{len(pairs)} correspondences over {len(seam_counts)} seams "
          f"({len(rows)} rows)")
    for k, v in sorted(seam_counts.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"   {k[0]:>8} | {k[1]:<8} {v['geometric']:3d} geometric"
              + (f" + {v['symbol']} symbol" if v["symbol"] else ""))
    for msg in log_skips:
        print(f"  note: {msg}")
    if recon_log:
        worst = max(recon_log, key=lambda r: r["max_disagreement_px"])
        print(f"  reconciled {len(recon_log)} points against the independent "
              f"reviewer; worst disagreement {worst['max_disagreement_px']} px "
              f"({worst['feature'][:50]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""08c -- Cut each mask at the shared centreline implied by the VERIFIED control.

WHY THIS REPLACES 08b
    08b took its cut positions from `gridlines.refine_grid`, the automatic
    street-band detector.  It cut each sheet at the first and last avenue the
    detector happened to FIND, and the detector is least reliable exactly at
    the edge of the paper -- which is where every seam is.  On sheet 7 it
    reached only Av. C, so the east cut landed a full block short of Av. D and
    threw away the eastern third of the sheet; mosaic coverage fell from 86.7%
    to 76.1% with no map data missing, only masked away.

    The same detector's measurement error is the documented root cause of the
    earlier geometry failure (research/experiment_log.md, entries 5 and 13).
    Nothing in the final product should depend on it.

WHAT THIS DOES INSTEAD
    Two sheets that abut share a street, and this project now has verified,
    semantically identified control ON that street for all ten adjacencies.
    Pushed through the solved transforms, each correspondence gives a point in
    the reconstruction plane where the two sheets agree; the midpoints of a
    seam's correspondences lie along the shared street.  Fitting a line
    through them IS the shared centreline, measured rather than detected.

    Each region's mask is then transported into the plane, clipped against one
    half-plane per neighbour (Sutherland-Hodgman, keeping the side its own
    centroid is on), and transported back to source pixels.  Cutting both
    sheets of a seam on the same plane line makes them butt exactly: no
    overlap to blend, no gap to fill.

    Edges with no neighbour keep the mapped-area bound that 08 established.

Outputs
    masks/sheet<N>_regions.geojson   (cut polygons; excluded regions preserved)
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sanborn import geometry as G
from sanborn import masks as M
from sanborn.config import load_config, paths, read_json, setup_logging

OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}


def clip_halfplane(ring, normal, offset, keep_point):
    """Sutherland-Hodgman clip of a polygon by {p : normal.p <= offset}.

    Orientation is chosen so that `keep_point` survives, which removes any
    need to reason about which way a seam faces.
    """
    normal = np.asarray(normal, float)
    sign = 1.0 if (normal @ np.asarray(keep_point, float)) <= offset else -1.0
    n, o = sign * normal, sign * offset

    def inside(p):
        return (n @ np.asarray(p, float)) <= o + 1e-9

    out = []
    pts = list(ring)
    if len(pts) > 1 and np.allclose(pts[0], pts[-1]):
        pts = pts[:-1]
    for i, cur in enumerate(pts):
        prv = pts[i - 1]
        ci, pi = inside(cur), inside(prv)
        if ci != pi:
            d = np.asarray(cur, float) - np.asarray(prv, float)
            den = n @ d
            if abs(den) > 1e-12:
                t = (o - n @ np.asarray(prv, float)) / den
                out.append(tuple(np.asarray(prv, float) + t * d))
        if ci:
            out.append(tuple(np.asarray(cur, float)))
    return out


def tidy(ring, ndigits=2):
    """Drop duplicate and collinear vertices and round, so re-running the cut
    produces a byte-identical artifact rather than a churn of equivalent
    vertex lists. The polygon is unchanged; only its representation is."""
    pts = [tuple(round(float(c), ndigits) for c in q) for q in ring]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    out = []
    for q in pts:
        if not out or (abs(q[0] - out[-1][0]) > 1e-9 or abs(q[1] - out[-1][1]) > 1e-9):
            out.append(q)
    if len(out) > 2 and out[0] == out[-1]:
        out = out[:-1]
    keep = []
    n = len(out)
    for i in range(n):
        a, b, c = out[i - 1], out[i], out[(i + 1) % n]
        cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(cross) > 1e-6:
            keep.append(b)
    return (keep or out) + [(keep or out)[0]]


def expand_toward_neighbours(ring, directions, page_wh, inset):
    """Push the sides that face a neighbour back out to the page bound.

    `ring` is a mask rectangle in source pixels; `directions` are the compass
    directions in which this region has a neighbour. Sides facing a neighbour
    will be cut at the shared centreline anyway, so their current value is
    irrelevant and starting from the page bound makes the cut idempotent.
    Sides facing nothing keep the mapped-area bound established by 08.
    """
    r = np.asarray(ring, float)
    x0, x1 = float(r[:, 0].min()), float(r[:, 0].max())
    y0, y1 = float(r[:, 1].min()), float(r[:, 1].max())
    W, H = page_wh
    if "north" in directions:
        y0 = inset
    if "south" in directions:
        y1 = H - inset
    if "west" in directions:
        x0 = inset
    if "east" in directions:
        x1 = W - inset
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]


def seam_lines(cfg, T, ties_plane, log):
    """{(regionA, regionB): (normal, offset)} in reconstruction-plane coords."""
    lines = {}
    for t in cfg.get("topology", []):
        a, b = t["region"], t["neighbour"]
        if a not in T or b not in T:
            continue
        key = tuple(sorted((a, b)))
        mids = ties_plane.get(key)
        if not mids or len(mids) < 2:
            log.warning("%s | %s: %d verified midpoint(s) -- cannot fit a "
                        "centreline, edge left uncut", a, b, len(mids or []))
            continue
        P = np.asarray(mids, float)
        direction = t["direction"]
        if direction in ("north", "south"):
            # street runs east-west: fit y = c + m x, normal is (-m, 1)
            m, c = np.polyfit(P[:, 0], P[:, 1], 1)
            normal = np.array([-m, 1.0])
        else:
            # avenue runs north-south: fit x = c + m y, normal is (1, -m)
            m, c = np.polyfit(P[:, 1], P[:, 0], 1)
            normal = np.array([1.0, -m])

        # Control on a shared street usually sits on BOTH of its property
        # lines -- 245 px apart for an 80 ft street -- not on the centreline.
        # A least-squares line through both families lands on the centreline
        # only when the families are balanced, and leans toward whichever side
        # was easier to measure when they are not. Taking the midpoint of the
        # 10th and 90th percentile offsets is unbiased under imbalance and
        # still resistant to a single stray point.
        d = (normal @ P.T) / np.linalg.norm(normal)
        lo, hi = float(np.percentile(d, 10)), float(np.percentile(d, 90))
        offset = 0.5 * (lo + hi) * np.linalg.norm(normal)
        span = hi - lo
        lines[key] = (normal, offset)
        log.info("%-8s | %-8s  %-5s  centreline from %2d midpoints, "
                 "control spans %6.1f px across the street (%s)",
                 a, b, direction, len(P), span,
                 "both property lines" if span > 60 else "one line only")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="galveston1889")
    ap.add_argument("--inset", type=float, default=6.0,
                    help="keep this many pixels clear of the page edge")
    args = ap.parse_args()

    cfg = load_config(args.profile)
    p = paths().ensure()
    log = setup_logging("08c_cut_masks_from_solution")
    root = Path(cfg["_root"])

    T = {k: np.asarray(v, float)
         for k, v in read_json(p.working / "transforms.json")["transforms"].items()}

    # verified correspondences -> midpoints in the plane
    by_id = defaultdict(list)
    with (p.gcps / "tiepoints_verified.csv").open(newline="") as fh:
        for row in csv.DictReader(fh):
            by_id[row["point_id"]].append(row)
    ties_plane = defaultdict(list)
    for pid, rows in by_id.items():
        if len(rows) != 2 or rows[0].get("control_class") == "symbol":
            continue
        ra, rb = rows[0]["region"], rows[1]["region"]
        if ra not in T or rb not in T:
            continue
        pa = G.apply(T[ra], [(float(rows[0]["src_x"]), float(rows[0]["src_y"]))])[0]
        pb = G.apply(T[rb], [(float(rows[1]["src_x"]), float(rows[1]["src_y"]))])[0]
        ties_plane[tuple(sorted((ra, rb)))].append(0.5 * (pa + pb))

    lines = seam_lines(cfg, T, ties_plane, log)

    nb, nb_dir = defaultdict(set), defaultdict(set)
    for t in cfg.get("topology", []):
        nb[t["region"]].add(t["neighbour"])
        nb[t["neighbour"]].add(t["region"])
        nb_dir[t["region"]].add(t["direction"])
        nb_dir[t["neighbour"]].add(OPP[t["direction"]])

    page = {}
    src_dir = root / ((cfg.get("paths") or {}).get("original_dir") or "data/original")
    for sh in cfg.get("sheets", []):
        with Image.open(src_dir / sh["file"]) as im:
            page[sh["id"]] = im.size

    for sh in cfg.get("sheets", []):
        sid = sh["id"]
        mask_path = p.masks / f"sheet{sid}_regions.geojson"
        if not mask_path.exists():
            continue
        doc = M.read_mask(mask_path)
        regs = {r[0]: r for r in M.regions(doc, keep_only=False)}
        feats, touched = [], []
        for rid, (_, ring0, props) in regs.items():
            keep = bool(props.get("keep", True))
            if not keep or rid not in T:
                feats.append(M.polygon_feature(
                    sheet=sid, region=rid, ring=ring0, keep=keep,
                    role=props.get("role", "map_region"),
                    source_image=sh["file"],
                    confidence=props.get("confidence", "high"),
                    defined_by=props.get("defined_by", ""),
                    note=props.get("note", "")))
                continue
            # Reset every edge that HAS a neighbour back to the page bound
            # before clipping, and keep the mapped-area bound only on edges
            # that face no neighbour. Without this the script is not
            # idempotent: run twice, and each pass trims the previous pass's
            # cut again. It also means a mask that a previous, less reliable
            # cutting pass trimmed too far is recovered rather than inherited.
            ring0 = expand_toward_neighbours(ring0, nb_dir.get(rid, set()),
                                             page[sid], args.inset)
            plane = G.apply(T[rid], ring0)
            centroid = plane.mean(axis=0)
            cut = plane
            for other in sorted(nb.get(rid, ())):
                key = tuple(sorted((rid, other)))
                if key not in lines:
                    continue
                normal, offset = lines[key]
                cut = clip_halfplane(cut, normal, offset, centroid)
                if len(cut) < 3:
                    break
                touched.append(other)
            if len(cut) < 3:
                log.error("sheet %s %s: clipping emptied the mask; left uncut",
                          sid, rid)
                cut_src = ring0
            else:
                cut_src = tidy(G.apply(np.linalg.inv(T[rid]), np.asarray(cut, float)))
            feats.append(M.polygon_feature(
                sheet=sid, region=rid, ring=[tuple(map(float, q)) for q in cut_src],
                keep=True, role="map_region", source_image=sh["file"],
                confidence="high",
                defined_by="cut at shared street centrelines fitted to the "
                           "verified control, in the reconstruction plane",
                note="Butt joint: both sheets of a seam are cut on the SAME "
                     "plane line, so they meet with no overlap and no gap. "
                     "Edges with no neighbour keep the mapped-area bound."))
        M.write_mask(mask_path, feats)
        log.info("sheet %-3s cut against %s", sid,
                 ", ".join(sorted(set(touched))) or "(no neighbours)")

    log.info("masks re-cut from the solution; re-run 09 and 10")
    return 0


if __name__ == "__main__":
    sys.exit(main())

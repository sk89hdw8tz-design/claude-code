#!/usr/bin/env python
"""Shared geometry/IO helpers for the Galveston 1912 seam-cut and mask pipeline.

Conventions (from 40_solve/output/transforms.json, read at RUN TIME, never baked in):
    raw transform: p_mosaic = [[a,-b],[b,a]] @ p_sheet + (raw.tx, raw.ty)
    axes: raster pixels, origin top-left, x right, y down.

All outputs are written with `write_canonical_json` (sorted keys, floats rounded to
3 dp, fixed separators) so that re-running without input changes yields
byte-identical files.
"""

import hashlib
import json
import math
import os

import numpy as np

# ---------------------------------------------------------------------------
# paths

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)

TRANSFORMS_JSON = os.path.join(PROJECT, "40_solve", "output", "transforms.json")
ADJACENCY_JSON = os.path.join(PROJECT, "10_key", "adjacency.json")
INVENTORY_JSON = os.path.join(PROJECT, "00_inventory", "INVENTORY.json")
PLATE_STRUCTURE_JSON = os.path.join(PROJECT, "20_plates", "plate_structure.json")
VERIFIED_DIR = os.path.join(PROJECT, "30_controls", "verified")
SHEET5_REGIONS_GEOJSON = os.path.join(PROJECT, "fable_review", "sheet05_candidate_regions.geojson")
CUTS_JSON = os.path.join(PROJECT, "50_seams", "cuts.json")
MASKS_JSON = os.path.join(PROJECT, "50_seams", "masks.json")
MANUAL_EXCLUSIONS_JSON = os.path.join(PROJECT, "50_seams", "manual_exclusions.json")


# ---------------------------------------------------------------------------
# canonical JSON

def _canon(obj, ndigits=3):
    if isinstance(obj, dict):
        return {str(k): _canon(v, ndigits) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_canon(v, ndigits) for v in obj]
    if isinstance(obj, (np.floating,)):
        obj = float(obj)
    if isinstance(obj, (np.integer,)):
        obj = int(obj)
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError("non-finite float in canonical output")
        r = round(obj, ndigits)
        if r == 0.0:
            r = 0.0  # normalise -0.0
        return r
    return obj


def canonical_dumps(obj, ndigits=3):
    return json.dumps(_canon(obj, ndigits), sort_keys=True, indent=1,
                      separators=(",", ": "), ensure_ascii=False) + "\n"


def write_canonical_json(path, obj, ndigits=3):
    text = canonical_dumps(obj, ndigits)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return text


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# transforms

def load_transforms(path=TRANSFORMS_JSON):
    """Return (per-sheet raw transforms {int sheet: {a,b,tx,ty}}, full doc)."""
    with open(path) as f:
        doc = json.load(f)
    raw = {}
    for k, v in doc["sheets"].items():
        r = v["raw"]
        raw[int(k)] = {"a": float(r["a"]), "b": float(r["b"]),
                       "tx": float(r["tx"]), "ty": float(r["ty"])}
    return raw, doc


def apply_raw(T, pts):
    """Apply raw sheet->mosaic transform to an (N,2) array (or single point)."""
    p = np.atleast_2d(np.asarray(pts, dtype=float))
    a, b = T["a"], T["b"]
    out = np.empty_like(p)
    out[:, 0] = a * p[:, 0] - b * p[:, 1] + T["tx"]
    out[:, 1] = b * p[:, 0] + a * p[:, 1] + T["ty"]
    return out[0] if np.asarray(pts).ndim == 1 else out


def invert_raw(T):
    """Return the mosaic->sheet transform in the same {a,b,tx,ty} form."""
    a, b = T["a"], T["b"]
    det = a * a + b * b
    ai, bi = a / det, -b / det
    # p_sheet = Rinv @ (p_mosaic - t)
    tx = -(ai * T["tx"] - bi * T["ty"])
    ty = -(bi * T["tx"] + ai * T["ty"])
    return {"a": ai, "b": bi, "tx": tx, "ty": ty}


def warp_matrix(T, origin=(0.0, 0.0), scale=1.0):
    """2x3 cv2.warpAffine matrix: sheet px -> canvas px
    (canvas = scale * (mosaic - origin))."""
    a, b = T["a"], T["b"]
    ox, oy = origin
    return np.array([
        [scale * a, -scale * b, scale * (T["tx"] - ox)],
        [scale * b, scale * a, scale * (T["ty"] - oy)],
    ], dtype=np.float64)


# ---------------------------------------------------------------------------
# adjacency / street naming

def slug(name):
    s = "".join(c.lower() if c.isalnum() else "_" for c in name)
    while "__" in s:
        s = s.replace("__", "_")
    return s.strip("_")


def load_adjacency(path=ADJACENCY_JSON):
    with open(path) as f:
        return json.load(f)


def street_of_pair(adjacency, a, b):
    """Canonical (street_id, street_name) for an internal pair, else (None, None)."""
    want = {int(a), int(b)}
    for entry in adjacency["internal_pairs"]:
        if set(int(s) for s in entry["sheets"]) == want:
            name = entry["shared_feature"]
            return slug(name), name
    return None, None


def sheet_edge_for_street(adjacency, sheet, street_id):
    """Which edge ('left'/'right'/'top'/'bottom') of `sheet` carries `street_id`."""
    edges = adjacency["edges"][str(sheet)]
    for side, val in edges.items():
        if not val or val[0] is None:
            continue
        nbr, feature = val[0], val[1]
        if feature is None:
            continue
        if slug(feature) == street_id:
            return side, nbr
    return None, None


def seamward_endpoint(seg, side):
    """Endpoint of a 2-point face segment nearest the seam, given the sheet's
    edge side that carries the seam ('right' -> max x, 'left' -> min x, etc.)."""
    p0, p1 = np.asarray(seg[0], float), np.asarray(seg[1], float)
    if side == "right":
        return p0 if p0[0] >= p1[0] else p1
    if side == "left":
        return p0 if p0[0] <= p1[0] else p1
    if side == "bottom":
        return p0 if p0[1] >= p1[1] else p1
    if side == "top":
        return p0 if p0[1] <= p1[1] else p1
    raise ValueError("bad side %r" % side)


# ---------------------------------------------------------------------------
# verified pair-file parsing

def load_pair_anchors(verified_dir, adjacency, solved_sheets, statuses=("ACCEPTED",)):
    """Parse 30_controls/verified/pair_*.json into anchor records for pairs whose
    two sheets are both solved. Returns (records, file_hashes, skipped)."""
    records = []
    file_hashes = {}
    skipped = []
    for fn in sorted(os.listdir(verified_dir)):
        if not (fn.startswith("pair_") and fn.endswith(".json")):
            continue
        path = os.path.join(verified_dir, fn)
        with open(path) as f:
            doc = json.load(f)
        pair = doc.get("pair", [])
        try:
            a, b = int(pair[0]), int(pair[1])
        except (ValueError, TypeError):
            skipped.append((fn, "non-integer sheet ids (wharf attachment; out of scope)"))
            continue
        if a not in solved_sheets or b not in solved_sheets:
            skipped.append((fn, "pair not fully solved"))
            continue
        street_id, street_name = street_of_pair(adjacency, a, b)
        if street_id is None:
            skipped.append((fn, "pair not in adjacency internal_pairs"))
            continue
        file_hashes[fn] = sha256_file(path)
        for ctrl in doc.get("controls", []):
            if ctrl.get("status") not in statuses:
                continue
            plates = {}
            ok = True
            for key in ("A", "B"):
                obs = ctrl.get(key)
                if not obs or "face1_seg" not in obs or "face2_seg" not in obs:
                    ok = False
                    break
                sheet = int(obs["sheet"])
                side, nbr = sheet_edge_for_street(adjacency, sheet, street_id)
                if side is None:
                    ok = False
                    break
                # single-shared-face controls may record one face as null
                # (e.g. pair_9_11 Ave A anchor); use the faces that exist
                segs = [s for s in (obs["face1_seg"], obs["face2_seg"])
                        if s is not None]
                if not segs:
                    ok = False
                    break
                corners = [seamward_endpoint(s, side) for s in segs]
                plates[sheet] = {
                    "segs_sheet": [[list(map(float, p)) for p in s] for s in segs],
                    "corners_sheet": [list(map(float, c)) for c in corners],
                    "side": side,
                    "source_sha256": obs.get("source_sha256"),
                }
            if not ok:
                skipped.append((fn + ":" + str(ctrl.get("anchor")), "incomplete observation"))
                continue
            records.append({
                "street_id": street_id,
                "street_name": street_name,
                "pair": [a, b],
                "anchor": ctrl.get("anchor"),
                "file": fn,
                "plates": plates,
            })
    records.sort(key=lambda r: (r["street_id"], r["pair"], str(r["anchor"])))
    return records, file_hashes, skipped


# ---------------------------------------------------------------------------
# line fitting (total least squares) and (t, offset) frames

def fit_tls_line(points):
    """Total-least-squares line through (N,2) points.
    Returns dict with p0 (centroid), dir (unit), normal (unit, left of dir),
    rms_perp."""
    P = np.asarray(points, dtype=float)
    if len(P) < 2:
        raise ValueError("need >= 2 points for a TLS line")
    c = P.mean(axis=0)
    Q = P - c
    _, _, vt = np.linalg.svd(Q, full_matrices=False)
    d = vt[0]
    # deterministic sign: dominant component positive
    if abs(d[0]) >= abs(d[1]):
        if d[0] < 0:
            d = -d
    else:
        if d[1] < 0:
            d = -d
    n = np.array([-d[1], d[0]])
    offs = Q @ n
    return {
        "p0": [float(c[0]), float(c[1])],
        "dir": [float(d[0]), float(d[1])],
        "normal": [float(n[0]), float(n[1])],
        "rms_perp_px": float(np.sqrt(np.mean(offs ** 2))),
        "n_points": int(len(P)),
    }


def line_along(line, pts):
    p = np.atleast_2d(np.asarray(pts, float)) - np.asarray(line["p0"])
    t = p @ np.asarray(line["dir"])
    return t[0] if np.asarray(pts).ndim == 1 else t


def line_offset(line, pts):
    p = np.atleast_2d(np.asarray(pts, float)) - np.asarray(line["p0"])
    o = p @ np.asarray(line["normal"])
    return o[0] if np.asarray(pts).ndim == 1 else o


def line_point(line, t, off=0.0):
    p0 = np.asarray(line["p0"])
    d = np.asarray(line["dir"])
    n = np.asarray(line["normal"])
    return p0 + t * d + off * n


def polyline_from_tn(line, tn_pairs):
    """Map [(t, off), ...] to mosaic xy vertices."""
    return [list(map(float, line_point(line, t, o))) for t, o in tn_pairs]


def halfplane_polygon(line, tn_pairs, side_sign, big=1.0e6):
    """Shapely polygon of the `side_sign` side of the cut polyline.

    tn_pairs are the cut vertices in (t, offset) coordinates, ordered by t.
    The polyline is extended straight beyond both ends; the region is closed at
    offset side_sign*big. Two calls with opposite side_sign share the exact
    polyline boundary, so the two regions tile without overlap or gap.
    """
    from shapely.geometry import Polygon

    tn = sorted((float(t), float(o)) for t, o in tn_pairs)
    first = (tn[0][0] - big, tn[0][1])
    last = (tn[-1][0] + big, tn[-1][1])
    ring_tn = [first] + tn + [last,
                              (last[0], side_sign * big),
                              (first[0], side_sign * big)]
    ring = [tuple(line_point(line, t, o)) for t, o in ring_tn]
    return Polygon(ring)


# ---------------------------------------------------------------------------
# page quads

def load_page_quads(path=PLATE_STRUCTURE_JSON):
    """{int sheet: (4,2) array of full-res page-quad corners (paper on backdrop)}."""
    with open(path) as f:
        doc = json.load(f)
    quads = {}
    for pl in doc["plates"]:
        quads[int(pl["sheet"])] = np.asarray(pl["page_quad_fullres"], dtype=float)
    return quads


def load_inventory(path=INVENTORY_JSON):
    with open(path) as f:
        doc = json.load(f)
    items = {}
    for it in doc["items"]:
        items[int(it["sheet"])] = it
    return items, doc


# ---------------------------------------------------------------------------
# region-id guard

class RegionIdError(ValueError):
    pass


class RegionRegistry:
    """Collects mask features as a LIST; raises on any duplicate region_id so a
    reused id can never silently overwrite another region."""

    def __init__(self):
        self.features = []
        self._ids = set()

    def add(self, feature):
        rid = feature.get("region_id")
        if not rid:
            raise RegionIdError("feature without region_id")
        if rid in self._ids:
            raise RegionIdError("duplicate region_id: %r" % rid)
        self._ids.add(rid)
        self.features.append(feature)

#!/usr/bin/env python
"""qalib.py — shared helpers for the Galveston 1912 QA harness (70_qa).

QA is read-only over the pipeline: sources, transforms, cuts, masks, and the
master are NEVER modified. Every artifact embeds the master's sha256 so the
aggregate report can refuse stale artifacts.

Key facts baked in from validation (do not "simplify" these away):
  * cv2.warpAffine output is byte-exact under integer *y* window offsets but
    NOT under *x* window offsets (per-column fixed-point tables). To reproduce
    the exact bytes the renderer wrote, any QA warp must reuse the sheet's
    render-time x window origin (canvas_bbox[0] from the render manifest) and
    may choose its own integer y origin.  Validated empirically 2026-08-17.
  * Canvas mapping: canvas_px = (mosaic - (x0m, y0m)) * scale, scale = 1.0 in
    the final render, so canvas pixels ARE mosaic pixels re-origined.
"""

import datetime
import hashlib
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(os.path.dirname(HERE))          # galveston-1912/
QA = os.path.join(PROJECT, "70_qa")
RUN = os.path.join(QA, "run1")
FINAL = os.path.join(PROJECT, "60_master", "final")
MASTER_TIF = os.path.join(FINAL, "candidate_master.tif")
RENDER_MANIFEST = os.path.join(FINAL, "render_manifest.json")
FREEZE_MANIFEST = os.path.join(PROJECT, "40_solve", "FREEZE_MANIFEST.json")
RESIDUALS_JSON = os.path.join(PROJECT, "40_solve", "output", "residuals.json")

sys.path.insert(0, os.path.join(PROJECT, "50_seams"))
import seamlib as sl  # noqa: E402

SCRATCH = os.environ.get(
    "G1912_SCRATCH",
    "/tmp/claude-0/-home-user-claude-code/3107d3d8-6779-530e-9ae5-ba7b48239c4e/scratchpad")


# ---------------------------------------------------------------------------
# hashing / stale guard

def sha256_file(path):
    return sl.sha256_file(path, chunk=1 << 22)


_MASTER_SHA_CACHE = os.path.join(RUN, "master_sha256.txt")


def master_sha256():
    """sha256 of the final master TIFF, cached (keyed by size+mtime)."""
    st = os.stat(MASTER_TIF)
    key = "%d:%d" % (st.st_size, int(st.st_mtime))
    cache2 = os.path.join(SCRATCH, "master_sha_" + key + ".txt")
    if os.path.exists(cache2):
        return open(cache2).read().split()[0]
    h = sha256_file(MASTER_TIF)
    os.makedirs(SCRATCH, exist_ok=True)
    with open(cache2, "w") as f:
        f.write(h + "\n")
    with open(_MASTER_SHA_CACHE, "w") as f:
        f.write(h + "  " + os.path.relpath(MASTER_TIF, PROJECT) + "\n")
    return h


def load_freeze():
    with open(FREEZE_MANIFEST) as f:
        return json.load(f)


def load_manifest():
    with open(RENDER_MANIFEST) as f:
        return json.load(f)


class FreezeMismatch(SystemExit):
    pass


def verify_frozen_inputs(loud=True):
    """REFUSE (raise) if the final render's inputs or the on-disk geometry
    files do not match FREEZE_MANIFEST. Returns (manifest, freeze, report)."""
    man = load_manifest()
    fz = load_freeze()
    comp = fz["components"]
    checks = []

    def chk(name, got, want):
        ok = (got == want)
        checks.append({"check": name, "got": got, "frozen": want, "ok": ok})
        return ok

    ok = True
    ok &= chk("render.inputs.cuts_json", man["inputs"]["cuts_json"]["sha256"], comp["cuts"])
    ok &= chk("render.inputs.masks_json", man["inputs"]["masks_json"]["sha256"], comp["masks"])
    ok &= chk("render.inputs.transforms_json",
              man["inputs"]["transforms_json"]["sha256"], comp["transforms_block"])
    # on-disk files still the frozen ones
    ok &= chk("disk.cuts.json", sha256_file(sl.CUTS_JSON), comp["cuts"])
    ok &= chk("disk.masks.json", sha256_file(sl.MASKS_JSON), comp["masks"])
    ok &= chk("disk.transforms.json", sha256_file(sl.TRANSFORMS_JSON), comp["transforms_block"])
    ok &= chk("disk.INVENTORY.json", sha256_file(sl.INVENTORY_JSON), comp["source_inventory"])
    # archival sources vs inventory (against the manifest's recorded values)
    inv_items, _ = sl.load_inventory()
    for s in man["sheets"]:
        ok &= chk("source.sheet%02d" % s["sheet"], s["source_sha256"],
                  inv_items[s["sheet"]]["sha256"])
    if not ok and loud:
        bad = [c for c in checks if not c["ok"]]
        raise FreezeMismatch(
            "FREEZE MISMATCH — QA REFUSES TO RUN.\n" +
            "\n".join("  %(check)s: got %(got)s != frozen %(frozen)s" % c for c in bad))
    return man, fz, checks


def stamp(tool_name, extra=None):
    """Provenance stamp embedded in every QA artifact."""
    d = {
        "tool": tool_name,
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "master_tif": os.path.relpath(MASTER_TIF, PROJECT),
        "master_sha256": master_sha256(),
        "qa_policy": "report only; sources/cuts/masks/transforms/master never modified",
    }
    if extra:
        d.update(extra)
    return d


# ---------------------------------------------------------------------------
# master access (decode once to a scratch memmap)

def master_array():
    """(H,W,3) uint8 RGB memmap of the final master (decoded once per hash)."""
    import tifffile
    h = master_sha256()
    man = load_manifest()
    W, H = man["canvas"]["size_px"]
    path = os.path.join(SCRATCH, "master_decoded_%s.dat" % h[:16])
    if os.path.exists(path) and os.path.getsize(path) == H * W * 3:
        return np.memmap(path, dtype=np.uint8, mode="r", shape=(H, W, 3))
    arr = np.memmap(path, dtype=np.uint8, mode="w+", shape=(H, W, 3))
    with tifffile.TiffFile(MASTER_TIF) as tf:
        page = tf.pages[0]
        assert page.shape[:2] == (H, W), "master size != manifest size"
        page.asarray(out=arr)
    arr.flush()
    return np.memmap(path, dtype=np.uint8, mode="r", shape=(H, W, 3))


# ---------------------------------------------------------------------------
# geometry

def load_geometry():
    """Everything needed to reason about the mosaic in one bundle."""
    from shapely.geometry import Polygon
    man = load_manifest()
    raw, tdoc = sl.load_transforms()
    with open(sl.CUTS_JSON) as f:
        cuts = json.load(f)
    with open(sl.MASKS_JSON) as f:
        masks = json.load(f)
    adj = sl.load_adjacency()
    inv_items, _ = sl.load_inventory()
    quads = sl.load_page_quads()
    x0m, y0m, x1m, y1m = man["canvas"]["mosaic_rect"]
    scale = float(man["canvas"]["scale"])
    W, H = man["canvas"]["size_px"]

    regions = []
    for feat in masks["regions"]:
        poly = Polygon(feat["polygon_mosaic"]["exterior"],
                       feat["polygon_mosaic"]["interiors"])
        regions.append({"sheet": int(feat["sheet"]), "region_id": feat["region_id"],
                        "poly_mosaic": poly, "feat": feat})

    def m2c(pts):
        p = np.atleast_2d(np.asarray(pts, float))
        out = (p - [x0m, y0m]) * scale
        return out[0] if np.asarray(pts).ndim == 1 else out

    def c2m(pts):
        p = np.atleast_2d(np.asarray(pts, float))
        out = p / scale + [x0m, y0m]
        return out[0] if np.asarray(pts).ndim == 1 else out

    solved = sorted(raw)
    pairs = []
    for entry in adj["internal_pairs"]:
        try:
            a, b = sorted(int(s) for s in entry["sheets"])
        except (TypeError, ValueError):
            continue
        if a in solved and b in solved:
            sid = sl.slug(entry["shared_feature"])
            pairs.append({"pair": (a, b), "street_id": sid,
                          "street_name": entry["shared_feature"]})
    pairs.sort(key=lambda p: (p["street_id"], p["pair"]))

    return {
        "manifest": man, "raw": raw, "tdoc": tdoc, "cuts": cuts, "masks": masks,
        "adjacency": adj, "inventory": inv_items, "quads": quads,
        "mosaic_rect": (x0m, y0m, x1m, y1m), "scale": scale, "size": (W, H),
        "regions": regions, "pairs": pairs, "m2c": m2c, "c2m": c2m,
        "streets": {s["street_id"]: s for s in cuts["streets"]},
        "sheet_bbox": {s["sheet"]: s["canvas_bbox"] for s in man["sheets"]},
    }


def seam_segment(geo, a, b):
    """Shared boundary (mosaic frame) between the owned regions of sheets a, b.
    Returns (merged LineString or None, total length)."""
    from shapely.geometry import LineString, MultiLineString
    from shapely.ops import linemerge
    pa = [r["poly_mosaic"] for r in geo["regions"] if r["sheet"] == a]
    pb = [r["poly_mosaic"] for r in geo["regions"] if r["sheet"] == b]
    from shapely.ops import unary_union
    A = unary_union(pa)
    B = unary_union(pb)
    inter = A.boundary.intersection(B.boundary)
    if inter.is_empty:
        return None, 0.0
    lines = []
    def collect(g):
        if isinstance(g, LineString):
            lines.append(g)
        elif isinstance(g, MultiLineString):
            lines.extend(g.geoms)
        elif hasattr(g, "geoms"):
            for gg in g.geoms:
                collect(gg)
    collect(inter)
    if not lines:
        return None, 0.0
    merged = linemerge(MultiLineString(lines))
    return merged, sum(l.length for l in lines)


# ---------------------------------------------------------------------------
# render-path-exact warps

def _load_sheet_bgr(geo, sheet, verify=True):
    item = geo["inventory"][sheet]
    if verify:
        got = sha256_file(item["path"])
        if got != item["sha256"]:
            raise SystemExit("sha256 mismatch for sheet %d source — refusing" % sheet)
    img = cv2.imread(item["path"], cv2.IMREAD_COLOR)
    if img is None or img.shape[:2] != (item["height"], item["width"]):
        raise SystemExit("decode failure for sheet %d" % sheet)
    return img


def sheet_own_raster(geo, sheet):
    """Sheet-frame ownership raster, exactly as render_master rasterizes it."""
    item = geo["inventory"][sheet]
    feats = sorted((r["feat"] for r in geo["regions"] if r["sheet"] == sheet),
                   key=lambda f: f["region_id"])
    m = np.zeros((item["height"], item["width"]), dtype=np.uint8)
    for feat in feats:
        ext = np.rint(np.asarray(feat["polygon_sheet_px"]["exterior"])).astype(np.int32)
        cv2.fillPoly(m, [ext], 255)
        for hole in feat["polygon_sheet_px"]["interiors"]:
            cv2.fillPoly(m, [np.rint(np.asarray(hole)).astype(np.int32)], 0)
    return m


def warp_window(geo, sheet, rect, img=None, own=None):
    """Warp sheet (and its ownership raster) into integer canvas rect
    [rx, ry, rw, rh], reproducing the renderer's bytes exactly on owned pixels.

    Uses the sheet's render-time x window origin (manifest canvas_bbox[0]) so
    the per-column fixed-point tables match the render; y origin is free
    (byte-exact under integer y shifts). Columns left of the sheet's window
    are padded white/unowned. Returns (rgb (rh,rw,3), own_bool (rh,rw)).
    """
    rx, ry, rw, rh = rect
    for v in rect:
        if not isinstance(v, (int, np.integer)):
            raise ValueError("non-integer panel rect %r — float-truncation guard" % (rect,))
    x0m, y0m = geo["mosaic_rect"][:2]
    scale = geo["scale"]
    T = geo["raw"][sheet]
    if img is None:
        img = _load_sheet_bgr(geo, sheet)
    if own is None:
        own = sheet_own_raster(geo, sheet)
    bx0 = int(geo["sheet_bbox"][sheet][0])
    M = sl.warp_matrix(T, origin=(x0m, y0m), scale=scale)
    # The window MUST start at the renderer's x origin bx0; columns < bx0 were
    # never written by this sheet (outside its canvas bbox), so pad white.
    wx0 = bx0
    wx1 = rx + rw
    out_rgb = np.full((rh, rw, 3), 255, np.uint8)
    out_own = np.zeros((rh, rw), bool)
    if wx1 <= wx0:
        return out_rgb, out_own    # rect entirely left of the sheet's window
    Ms = M.copy()
    Ms[0, 2] -= wx0
    Ms[1, 2] -= ry
    w = wx1 - wx0
    warped = cv2.warpAffine(img, Ms, (w, rh), flags=cv2.INTER_LANCZOS4,
                            borderMode=cv2.BORDER_CONSTANT,
                            borderValue=(255, 255, 255))
    ownw = cv2.warpAffine(own, Ms, (w, rh), flags=cv2.INTER_NEAREST,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    sx = rx - wx0   # >= 0 iff rx >= bx0
    if sx >= 0:
        out_rgb[:, :] = warped[:, sx:sx + rw][..., ::-1]
        out_own[:, :] = ownw[:, sx:sx + rw] > 0
    else:
        out_rgb[:, -sx:] = warped[:, :rw + sx][..., ::-1]
        out_own[:, -sx:] = ownw[:, :rw + sx] > 0
    return out_rgb, out_own


# ---------------------------------------------------------------------------
# panel annotation

def label_bar(width, lines, bar_h=None):
    """White header bar with black text (no external fonts)."""
    lh = 22
    bar_h = bar_h or (10 + lh * len(lines))
    bar = np.full((bar_h, width, 3), 255, np.uint8)
    for i, txt in enumerate(lines):
        cv2.putText(bar, txt, (8, 20 + lh * i), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (0, 0, 0), 1, cv2.LINE_AA)
    bar[-2:, :] = 40
    return bar


def save_png(path, rgb):
    cv2.imwrite(path, rgb[..., ::-1])


def write_json(path, obj):
    sl.write_canonical_json(path, obj)

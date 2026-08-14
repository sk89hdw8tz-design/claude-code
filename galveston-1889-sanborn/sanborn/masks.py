"""Editable region masks held in SOURCE-PIXEL coordinates.

Masks are stored as GeoJSON so they can be opened, inspected and hand-edited in
QGIS or any text editor, but their coordinates are deliberately *not*
geographic: they are (x, y) pixel positions in the original, unmodified scan,
with y increasing downward.  Each file records that convention explicitly in a
`pixel_crs` property so nothing downstream can mistake it for lon/lat.

Why pixel space?  Because a mask must stay valid no matter how the sheet is
later transformed, and because the archival scan is the one thing in this
project that never changes.  Re-running the adjustment with different GCPs
changes every world coordinate; it does not change a single mask vertex.

Polygons are closed rings, exterior only, in image order.  All transforms used
by this project (similarity/affine/projective) map straight lines to straight
lines, so a mask polygon can be carried into the output grid exactly by
transforming its vertices -- no rasterise-then-resample step, and therefore no
soft or shifted mask edges where sheets meet.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

PIXEL_CRS_NOTE = (
    "Coordinates are source-image pixels (x right, y DOWN) of the original "
    "unmodified scan named in properties.source_image. NOT a geographic CRS."
)


def polygon_feature(sheet, region, ring, *, keep=True, role="map_region",
                    source_image="", note="", confidence="", defined_by=""):
    """Build one mask feature. `ring` is an iterable of (x, y) pixel pairs."""
    ring = [[float(x), float(y)] for x, y in ring]
    if ring[0] != ring[-1]:
        ring.append(list(ring[0]))
    if len(ring) < 4:
        raise ValueError("a polygon ring needs at least 3 distinct vertices")
    return {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [ring]},
        "properties": {
            "sheet": sheet,
            "region": region,
            "keep": bool(keep),
            "role": role,
            "source_image": source_image,
            "pixel_crs": PIXEL_CRS_NOTE,
            "note": note,
            "confidence": confidence,
            "defined_by": defined_by,
        },
    }


def write_mask(path, features, extra=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "type": "FeatureCollection",
        "name": path.stem,
        "pixel_crs": PIXEL_CRS_NOTE,
        "features": list(features),
    }
    if extra:
        doc.update(extra)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return path


def read_mask(path):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if doc.get("type") != "FeatureCollection":
        raise ValueError(f"{path}: not a GeoJSON FeatureCollection")
    return doc


def regions(doc, keep_only=True):
    """Yield (region_id, ring_array, properties) for each polygon."""
    out = []
    for f in doc.get("features", []):
        props = f.get("properties", {})
        if keep_only and not props.get("keep", True):
            continue
        geom = f.get("geometry") or {}
        if geom.get("type") != "Polygon":
            continue
        ring = np.asarray(geom["coordinates"][0], dtype=float)
        out.append((props.get("region", ""), ring, props))
    return out


def rect_ring(x0, y0, x1, y1):
    """Axis-aligned rectangle as a closed ring (convenience for collars)."""
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]


def inset_ring(width, height, left=0, top=0, right=0, bottom=0):
    """Full page inset by a per-edge margin -- the usual page-collar mask."""
    return rect_ring(left, top, width - right, height - bottom)


def rasterize(rings, shape, value=255):
    """Rasterise rings into a uint8 mask of `shape` = (height, width).

    Used only to produce human-viewable previews and to clip in source space;
    the mosaic itself carries mask polygons through the transform analytically.
    """
    import cv2

    h, w = shape
    mask = np.zeros((h, w), dtype=np.uint8)
    polys = [np.round(np.asarray(r, dtype=float)).astype(np.int32) for r in rings]
    if polys:
        cv2.fillPoly(mask, polys, int(value))
    return mask


def ring_area(ring):
    """Shoelace area in square pixels (sign-independent)."""
    r = np.asarray(ring, dtype=float)
    x, y = r[:, 0], r[:, 1]
    return float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2.0)


def ring_bounds(ring):
    r = np.asarray(ring, dtype=float)
    return (float(r[:, 0].min()), float(r[:, 1].min()),
            float(r[:, 0].max()), float(r[:, 1].max()))


def validate(doc, image_size=None, tolerance=2.0):
    """Sanity-check a mask document; returns a list of human-readable problems.

    `image_size` is (width, height) of the source scan when known, so we can
    catch a mask that was authored against a different derivative -- the single
    most likely way for a hand-edited mask to go quietly wrong.
    """
    problems = []
    feats = doc.get("features", [])
    if not feats:
        problems.append("mask contains no features")
    seen = set()
    for f in feats:
        p = f.get("properties", {})
        rid = p.get("region")
        if not rid:
            problems.append("a feature has no 'region' property")
        elif rid in seen:
            problems.append(f"duplicate region id {rid!r}")
        else:
            seen.add(rid)
        geom = f.get("geometry") or {}
        if geom.get("type") != "Polygon":
            problems.append(f"region {rid!r}: geometry is not a Polygon")
            continue
        ring = np.asarray(geom["coordinates"][0], dtype=float)
        if len(ring) < 4:
            problems.append(f"region {rid!r}: fewer than 3 vertices")
        if not np.allclose(ring[0], ring[-1]):
            problems.append(f"region {rid!r}: ring is not closed")
        if ring_area(ring) <= 0:
            problems.append(f"region {rid!r}: zero area")
        if image_size:
            w, h = image_size
            x0, y0, x1, y1 = ring_bounds(ring)
            if x0 < -tolerance or y0 < -tolerance or x1 > w + tolerance or y1 > h + tolerance:
                problems.append(
                    f"region {rid!r}: extends outside the {w}x{h} source image "
                    f"(bounds {x0:.0f},{y0:.0f},{x1:.0f},{y1:.0f}) - was this mask "
                    f"authored against a different image size?")
    return problems

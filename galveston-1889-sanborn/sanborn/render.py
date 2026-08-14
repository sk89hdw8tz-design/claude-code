"""Warping and mosaicking.

Two rules drive this module.

1.  **One resampling.**  Every output pixel is interpolated exactly once,
    straight from the original scan to the final grid.  Nothing is rotated,
    cropped, saved and re-warped along the way, so the master never
    accumulates generational softening.  The mosaic step that follows is a
    pure pixel copy: the per-sheet warped rasters are already on the master's
    grid, so combining them resamples nothing.

2.  **Hard mask edges, no feathering.**  Sanborn sheets carry 1-2 px printed
    text.  Blending overlapping sheets across a wide ramp would smear it, so
    sheets meet along an exact polygon boundary carried analytically through
    the transform.  Where sheets genuinely overlap, a deterministic priority
    decides the winner; nothing is averaged.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
import rasterio
from affine import Affine
from rasterio.windows import Window

from . import geometry as G

INTERP = {
    "nearest": cv2.INTER_NEAREST,
    "linear": cv2.INTER_LINEAR,
    "cubic": cv2.INTER_CUBIC,
    "lanczos": cv2.INTER_LANCZOS4,
    "area": cv2.INTER_AREA,
}

# Lossless, tiled, BigTIFF-safe.  DEFLATE with a horizontal predictor is the
# most universally readable lossless option; ZSTD is faster but not every
# consumer's GDAL is built with it.
MASTER_PROFILE = dict(
    driver="GTiff", compress="deflate", predictor=2, zlevel=9,
    tiled=True, blockxsize=512, blockysize=512, BIGTIFF="YES",
    num_threads="ALL_CPUS", interleave="pixel",
)


@dataclass
class OutputGrid:
    """The common raster grid every region is warped onto."""
    u0: float
    v0: float
    width: int
    height: int
    pixels_per_unit: float = 1.0

    @property
    def transform(self) -> Affine:
        # Reconstruction plane is y-DOWN, so the 'e' term is positive: this
        # grid is an image, not a north-up map.  The georeferenced derivative
        # is produced separately in 12_export_final.py.
        s = 1.0 / self.pixels_per_unit
        return Affine(s, 0.0, self.u0, 0.0, s, self.v0)

    def to_dict(self):
        return {"u0": self.u0, "v0": self.v0, "width": self.width,
                "height": self.height, "pixels_per_unit": self.pixels_per_unit}

    @staticmethod
    def from_dict(d):
        return OutputGrid(d["u0"], d["v0"], int(d["width"]), int(d["height"]),
                          float(d.get("pixels_per_unit", 1.0)))

    def plane_to_pixel(self, pts):
        p = np.atleast_2d(np.asarray(pts, dtype=float))
        return np.column_stack([(p[:, 0] - self.u0) * self.pixels_per_unit,
                                (p[:, 1] - self.v0) * self.pixels_per_unit])


@dataclass
class RegionSpec:
    """One mapped region to be warped: a source image plus its mask ring."""
    region_id: str
    sheet: str
    source_path: str
    transform: np.ndarray                    # 3x3, source px -> plane
    ring: np.ndarray                         # (N,2) mask polygon, source px
    priority: int = 100                      # lower wins where sheets overlap
    meta: dict = field(default_factory=dict)


def transformed_ring(spec: RegionSpec) -> np.ndarray:
    """Mask polygon carried into the reconstruction plane.

    Exact, because similarity/affine/projective all map lines to lines -- so
    transforming the vertices is equivalent to transforming the whole polygon.
    """
    return G.apply(spec.transform, spec.ring)


def build_output_grid(specs, padding=0, pixels_per_unit=1.0) -> OutputGrid:
    if not specs:
        raise ValueError("no regions to place")
    pts = np.vstack([transformed_ring(s) for s in specs])
    u0 = float(np.floor(pts[:, 0].min())) - padding
    v0 = float(np.floor(pts[:, 1].min())) - padding
    u1 = float(np.ceil(pts[:, 0].max())) + padding
    v1 = float(np.ceil(pts[:, 1].max())) + padding
    width = int(np.ceil((u1 - u0) * pixels_per_unit))
    height = int(np.ceil((v1 - v0) * pixels_per_unit))
    return OutputGrid(u0, v0, width, height, pixels_per_unit)


def read_image(path) -> np.ndarray:
    """Load a source scan as HxWx3 uint8 RGB."""
    path = str(path)
    if path.lower().endswith((".tif", ".tiff")):
        with rasterio.open(path) as ds:
            arr = ds.read()
            if arr.shape[0] >= 3:
                arr = arr[:3]
            else:
                arr = np.repeat(arr[:1], 3, axis=0)
            return np.ascontiguousarray(np.transpose(arr, (1, 2, 0)))
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None          # archival scans exceed the bomb guard
    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"))


def image_size(path):
    path = str(path)
    if path.lower().endswith((".tif", ".tiff")):
        with rasterio.open(path) as ds:
            return ds.width, ds.height
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    with Image.open(path) as im:
        return im.size


def warp_region(spec: RegionSpec, grid: OutputGrid, out_path,
                interp="lanczos", tile=1024, src_image=None):
    """Warp one region onto `grid`, writing a windowed RGBA GeoTIFF.

    Only the region's own bounding box is written, so eight sheets do not each
    cost a full-mosaic-sized file.  The file's affine carries its offset, so
    the mosaic step can copy it into place with no arithmetic beyond a window.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    ring_px = grid.plane_to_pixel(transformed_ring(spec))
    x0 = max(0, int(np.floor(ring_px[:, 0].min())))
    y0 = max(0, int(np.floor(ring_px[:, 1].min())))
    x1 = min(grid.width, int(np.ceil(ring_px[:, 0].max())) + 1)
    y1 = min(grid.height, int(np.ceil(ring_px[:, 1].max())) + 1)
    if x1 <= x0 or y1 <= y0:
        raise ValueError(f"region {spec.region_id} falls outside the output grid")
    w, h = x1 - x0, y1 - y0

    img = read_image(spec.source_path) if src_image is None else src_image
    sh, sw = img.shape[:2]

    # plane -> source pixels
    Hinv = np.linalg.inv(spec.transform)
    ppu = grid.pixels_per_unit
    flag = INTERP[interp]

    # Mask, drawn once in this window's own pixel space with a hard edge.
    local_ring = np.round((ring_px - np.array([x0, y0])) * 1.0).astype(np.int32)
    poly = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(poly, [local_ring], 255)

    profile = dict(MASTER_PROFILE)
    profile.update(width=w, height=h, count=4, dtype="uint8",
                   transform=grid.transform * Affine.translation(x0, y0),
                   crs=None, photometric="RGB", alpha="UNSPECIFIED")

    with rasterio.open(out_path, "w", **profile) as dst:
        for ty in range(0, h, tile):
            th = min(tile, h - ty)
            for tx in range(0, w, tile):
                tw = min(tile, w - tx)
                sub = poly[ty:ty + th, tx:tx + tw]
                if not sub.any():
                    continue                       # nothing of this region here

                cols = np.arange(x0 + tx, x0 + tx + tw, dtype=np.float64)
                rows = np.arange(y0 + ty, y0 + ty + th, dtype=np.float64)
                U = grid.u0 + cols / ppu
                V = grid.v0 + rows / ppu
                UU, VV = np.meshgrid(U, V)
                den = Hinv[2, 0] * UU + Hinv[2, 1] * VV + Hinv[2, 2]
                den = np.where(np.abs(den) < 1e-12, 1e-12, den)
                sx = (Hinv[0, 0] * UU + Hinv[0, 1] * VV + Hinv[0, 2]) / den
                sy = (Hinv[1, 0] * UU + Hinv[1, 1] * VV + Hinv[1, 2]) / den

                valid = (sx >= 0) & (sx <= sw - 1) & (sy >= 0) & (sy <= sh - 1)
                alpha = np.where(valid & (sub > 0), 255, 0).astype(np.uint8)
                if not alpha.any():
                    continue

                patch = cv2.remap(img, sx.astype(np.float32), sy.astype(np.float32),
                                  flag, borderMode=cv2.BORDER_REPLICATE)
                patch = np.where(alpha[..., None] > 0, patch, 0)

                win = Window(tx, ty, tw, th)
                for b in range(3):
                    dst.write(patch[..., b], b + 1, window=win)
                dst.write(alpha, 4, window=win)

        dst.update_tags(region_id=spec.region_id, sheet=spec.sheet,
                        source_image=str(spec.source_path),
                        transform_matrix=json.dumps(np.asarray(spec.transform).tolist()),
                        interpolation=interp)
    return {"path": str(out_path), "window": [x0, y0, w, h],
            "region_id": spec.region_id, "sheet": spec.sheet}


def mosaic(warped, out_path, grid: OutputGrid, priority=None, tile=1024):
    """Combine warped regions into one RGBA master. First-wins by priority.

    Pure copy -- no interpolation, no averaging, no exposure matching, so the
    1889 colours in the master are exactly the colours in the scans.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    order = sorted(warped, key=lambda w: (priority or {}).get(w["region_id"], 100))

    profile = dict(MASTER_PROFILE)
    profile.update(width=grid.width, height=grid.height, count=4, dtype="uint8",
                   transform=grid.transform, crs=None, photometric="RGB")

    placed = []
    with rasterio.open(out_path, "w", **profile) as dst:
        # Track which output pixels are already claimed, one row-band at a time
        # so we never hold a full-mosaic mask in memory.
        for ty in range(0, grid.height, tile):
            th = min(tile, grid.height - ty)
            claimed = np.zeros((th, grid.width), dtype=bool)
            band = np.zeros((th, grid.width, 4), dtype=np.uint8)
            for w in order:
                x0, y0, ww, hh = w["window"]
                iy0, iy1 = max(ty, y0), min(ty + th, y0 + hh)
                if iy1 <= iy0:
                    continue
                with rasterio.open(w["path"]) as src:
                    win = Window(0, iy0 - y0, ww, iy1 - iy0)
                    arr = src.read(window=win)               # (4, rows, ww)
                a = arr[3]
                sl_y = slice(iy0 - ty, iy1 - ty)
                sl_x = slice(x0, x0 + ww)
                take = (a > 0) & ~claimed[sl_y, sl_x]
                if not take.any():
                    continue
                region = band[sl_y, sl_x]
                for b in range(4):
                    region[..., b] = np.where(take, arr[b], region[..., b])
                band[sl_y, sl_x] = region
                claimed[sl_y, sl_x] |= take
            for b in range(4):
                dst.write(band[..., b], b + 1, window=Window(0, ty, grid.width, th))
        dst.update_tags(
            product="historical reconstruction (not georeferenced)",
            grid=json.dumps(grid.to_dict()),
            regions=json.dumps([w["region_id"] for w in order]),
            note="Reconstruction-plane image. Units are anchor-sheet scan pixels.")
        placed = [w["region_id"] for w in order]
    return {"path": str(out_path), "order": placed,
            "size": [grid.width, grid.height]}


def downsample_preview(src_path, out_path, max_dim=6000, background=(255, 255, 255)):
    """Flatten RGBA onto a background and shrink for a viewable preview."""
    src_path, out_path = str(src_path), Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(src_path) as ds:
        scale = min(1.0, max_dim / max(ds.width, ds.height))
        ow, oh = max(1, int(ds.width * scale)), max(1, int(ds.height * scale))
        arr = ds.read(out_shape=(ds.count, oh, ow),
                      resampling=rasterio.enums.Resampling.average)
    rgb = np.transpose(arr[:3], (1, 2, 0)).astype(np.float32)
    if arr.shape[0] >= 4:
        a = (arr[3].astype(np.float32) / 255.0)[..., None]
        bg = np.array(background, dtype=np.float32)
        rgb = rgb * a + bg * (1.0 - a)
    from PIL import Image
    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).save(out_path)
    return {"path": str(out_path), "size": [ow, oh], "scale": scale}

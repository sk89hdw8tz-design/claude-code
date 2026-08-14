"""Synthetic multi-sheet fixture with exactly known ground truth.

This exists so the pipeline can be proven correct without touching the archival
scans -- and, in an environment where the scans cannot be downloaded at all, so
that "the code works" is a measured claim rather than an assertion.

It builds one large procedural city map (the ground truth), then cuts it into
overlapping "sheets", each printed on a paper page with a collar and distorted
by its own rotation / scale error / keystone, saved as JPEG the way an archival
scan would be.  Because the true sheet->ground-truth transform of every sheet
is recorded, reconstruction error can be measured absolutely, not just by
self-consistency.

One sheet deliberately carries TWO mapped regions on the same page -- a main
region belonging with the group and a geographically detached strip from far
away -- so the Sheet 1 exclusion logic is exercised end to end.

Nothing here is historical data.  It is a test rig, and every file it writes is
labelled as such.
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

PAPER = (246, 240, 226)      # aged paper
INK = (40, 38, 45)
BRICK = (196, 150, 154)      # Sanborn pink-ish
FRAME = (238, 222, 150)      # Sanborn yellow-ish
STONE = (176, 186, 196)
WATER = (188, 214, 224)

# Street names, chosen to look like a coastal grid city without claiming to be
# any real place: numbered cross-streets, lettered avenues.
AVENUES = ["AVENUE A", "AVENUE B", "AVENUE C", "AVENUE D", "AVENUE E",
           "AVENUE F", "AVENUE G", "AVENUE H"]


def _rng(seed):
    return np.random.default_rng(seed)


def build_ground_truth(width=7200, height=4200, block=420, street=54, seed=11):
    """Draw the reference city map and return (image, intersections, meta)."""
    rng = _rng(seed)
    img = np.full((height, width, 3), PAPER, dtype=np.uint8)

    xs = list(range(block // 2, width, block))          # numbered streets
    ys = list(range(block // 2, height, block))         # lettered avenues

    # Waterfront along the top edge, like a harbour front.
    cv2.rectangle(img, (0, 0), (width, ys[0] - street), WATER, -1)
    for i in range(0, width, 260):                      # wharf fingers
        cv2.rectangle(img, (i + 40, 10), (i + 150, ys[0] - street - 8), STONE, -1)
        cv2.rectangle(img, (i + 40, 10), (i + 150, ys[0] - street - 8), INK, 2)

    # City blocks, buildings and lot lines.
    for bi, x in enumerate(xs[:-1]):
        for bj, y in enumerate(ys[:-1]):
            bx0, by0 = x + street // 2, y + street // 2
            bx1, by1 = xs[bi + 1] - street // 2, ys[bj + 1] - street // 2
            cv2.rectangle(img, (bx0, by0), (bx1, by1), (236, 228, 210), -1)
            # lot lines
            nlots = rng.integers(3, 6)
            for k in range(1, nlots):
                lx = bx0 + int((bx1 - bx0) * k / nlots)
                cv2.line(img, (lx, by0), (lx, by1), (150, 145, 140), 1)
            # buildings
            for k in range(int(rng.integers(4, 9))):
                w = int(rng.integers(40, 110))
                h = int(rng.integers(34, 90))
                px = int(rng.integers(bx0 + 4, max(bx0 + 5, bx1 - w - 4)))
                py = int(rng.integers(by0 + 4, max(by0 + 5, by1 - h - 4)))
                col = BRICK if rng.random() < 0.55 else FRAME
                cv2.rectangle(img, (px, py), (px + w, py + h), col, -1)
                cv2.rectangle(img, (px, py), (px + w, py + h), INK, 1)
                if rng.random() < 0.35:                  # hatching
                    for hx in range(px + 3, px + w - 2, 7):
                        cv2.line(img, (hx, py + 2), (hx, py + h - 2), (120, 100, 100), 1)
                if rng.random() < 0.5:                   # tiny storey annotation
                    cv2.putText(img, str(int(rng.integers(1, 4))),
                                (px + 3, py + 13), cv2.FONT_HERSHEY_SIMPLEX,
                                0.32, INK, 1, cv2.LINE_AA)

    # Street casings and names last, so they sit on top.
    for i, x in enumerate(xs):
        cv2.line(img, (x - street // 2, 0), (x - street // 2, height), (120, 118, 120), 2)
        cv2.line(img, (x + street // 2, 0), (x + street // 2, height), (120, 118, 120), 2)
        for y in range(300, height, 900):
            cv2.putText(img, f"{i + 1}TH ST", (x - 20, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, INK, 1, cv2.LINE_AA)
    for j, y in enumerate(ys):
        cv2.line(img, (0, y - street // 2), (width, y - street // 2), (120, 118, 120), 2)
        cv2.line(img, (0, y + street // 2), (width, y + street // 2), (120, 118, 120), 2)
        for x in range(300, width, 1100):
            cv2.putText(img, AVENUES[j % len(AVENUES)], (x, y + 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, INK, 1, cv2.LINE_AA)

    intersections = []
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            intersections.append({
                "id": f"X{i + 1:02d}_{j + 1:02d}",
                "x": float(x), "y": float(y),
                "street_a": f"{i + 1}TH ST",
                "street_b": AVENUES[j % len(AVENUES)],
            })
    meta = {"width": width, "height": height, "block": block, "street": street,
            "xs": xs, "ys": ys}
    return img, intersections, meta


def _page_transform(rng, kind="similarity", rot_deg=1.2, scale_err=0.012,
                    keystone=0.0):
    """A plausible scan/print distortion: page pixels -> ground truth offsets."""
    th = np.deg2rad(rng.uniform(-rot_deg, rot_deg))
    s = 1.0 + rng.uniform(-scale_err, scale_err)
    A = s * np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    H = np.eye(3)
    H[:2, :2] = A
    if kind == "affine":
        H[0, 1] += rng.uniform(-0.004, 0.004)
        H[1, 0] += rng.uniform(-0.004, 0.004)
    if keystone:
        H[2, 0] = rng.uniform(-keystone, keystone)
        H[2, 1] = rng.uniform(-keystone, keystone)
    return H


def _place_region(page, gt, gt_rect, place, Hdist):
    """Draw one mapped region onto the page and return its exact transform."""
    gx0, gy0, gx1, gy1 = gt_rect
    px0, py0, px1, py1 = place
    sx = (gx1 - gx0) / (px1 - px0)
    sy = (gy1 - gy0) / (py1 - py0)
    # page px -> ground truth, before the scan/print distortion
    base = np.array([[sx, 0, gx0 - sx * px0],
                     [0, sy, gy0 - sy * py0],
                     [0, 0, 1.0]], dtype=float)
    # apply the distortion about the region centre so it stays on the page
    cx, cy = (px0 + px1) / 2.0, (py0 + py1) / 2.0
    C = np.array([[1, 0, -cx], [0, 1, -cy], [0, 0, 1.0]], dtype=float)
    H = base @ np.linalg.inv(C) @ Hdist @ C

    ys_, xs_ = np.mgrid[py0:py1, px0:px1].astype(np.float64)
    den = H[2, 0] * xs_ + H[2, 1] * ys_ + H[2, 2]
    den = np.where(np.abs(den) < 1e-12, 1e-12, den)
    mapx = ((H[0, 0] * xs_ + H[0, 1] * ys_ + H[0, 2]) / den).astype(np.float32)
    mapy = ((H[1, 0] * xs_ + H[1, 1] * ys_ + H[1, 2]) / den).astype(np.float32)
    page[py0:py1, px0:px1] = cv2.remap(
        gt, mapx, mapy, cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_CONSTANT, borderValue=PAPER)
    cv2.rectangle(page, (px0 - 2, py0 - 2), (px1 + 1, py1 + 1), INK, 2)
    return {"page_rect": [px0, py0, px1, py1], "gt_rect": list(gt_rect),
            "H_page_to_gt": H.tolist()}


def render_sheet(gt, gt_rect, page_size, Hdist, main_place, extra=None,
                 label="", seed=0):
    """Render one sheet page carrying one or more mapped regions.

    `extra` is a list of (gt_rect, placement) for additional regions printed on
    the same physical page -- the Sheet 1 case, where a geographically detached
    section shares the sheet with the region that belongs to the group.
    Each returned region records the exact 3x3 page-pixel -> ground-truth map.
    """
    rng = _rng(seed)
    pw, ph = page_size
    page = np.full((ph, pw, 3), PAPER, dtype=np.uint8)

    regions = [dict(role="main", **_place_region(page, gt, gt_rect, main_place, Hdist))]
    for r, place in (extra or []):
        regions.append(dict(role="detached", **_place_region(page, gt, r, place, Hdist)))

    # Sheet furniture: title block, printed border and a scanner-edge shadow.
    # The collar mask has to exclude all of this without eating map content.
    cv2.putText(page, label, (main_place[0], main_place[1] - 18),
                cv2.FONT_HERSHEY_DUPLEX, 0.9, INK, 2, cv2.LINE_AA)
    for r in regions[1:]:
        cv2.putText(page, "DETACHED SECTION - NOT PART OF THIS GROUP",
                    (r["page_rect"][0], r["page_rect"][1] - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, INK, 1, cv2.LINE_AA)
    cv2.rectangle(page, (0, 0), (pw - 1, ph - 1), (120, 116, 110), 6)
    page[:8, :] = (70, 68, 66)
    page[-8:, :] = (70, 68, 66)

    page = np.clip(page.astype(np.float32) + rng.normal(0, 2.0, page.shape), 0, 255)
    return page.astype(np.uint8), regions


def build_fixture(outdir, seed=11, overlap=240, jpeg_quality=92):
    """Write the full fixture: ground truth, 8 sheet JPEGs, and truth JSON."""
    outdir = Path(outdir)
    (outdir / "original").mkdir(parents=True, exist_ok=True)
    rng = _rng(seed)

    gt, intersections, gtmeta = build_ground_truth(seed=seed)
    cv2.imwrite(str(outdir / "ground_truth.png"), cv2.cvtColor(gt, cv2.COLOR_RGB2BGR))

    W, H = gtmeta["width"], gtmeta["height"]
    # 4 x 2 arrangement of mapped regions across the ground truth.  The overlap
    # is wider than half a block on purpose: real Sanborn sheets repeat the
    # boundary street, so the same intersections are printed on both sheets.
    # Without that, every available tie point along a seam is collinear and a
    # per-sheet affine adjustment is rank deficient (see geometry.py).
    cols, rows = 4, 2
    cw, ch = W / cols, H / rows
    names = ["S1", "S2", "S7", "S8", "S9", "S10", "S27", "S29"]

    # Every sheet is printed at ONE common scale, in both axes -- which is what
    # makes them a survey rather than a set of unrelated drawings, and what lets
    # a similarity model join them.  So the ground footprint is derived from the
    # printed area, never the reverse.  Sheets at the edge of the grid simply
    # run off the mapped area and pick up blank paper, as real ones do.
    margin = 110
    detached_band = 240              # printed height of Sheet 1's second region
    detached_gap = 40
    foot_w, foot_h = cw + 2 * overlap, ch + 2 * overlap
    place_w = 2180.0
    S = foot_w / place_w             # ground units per printed pixel
    place_h = foot_h / S
    page_size = (int(round(place_w + 2 * margin)),
                 int(round(place_h + 2 * margin)))

    sheets = []
    for k, name in enumerate(names):
        c, r = k % cols, k // cols
        cx, cy = (c + 0.5) * cw, (r + 0.5) * ch
        sheets.append({"name": name, "grid": [c, r],
                       "gt_rect": [cx - foot_w / 2, cy - foot_h / 2,
                                   cx + foot_w / 2, cy + foot_h / 2]})

    truth = {"note": "SYNTHETIC TEST FIXTURE - not historical data",
             "ground_truth": gtmeta, "scale_gt_per_page_px": S,
             "intersections": intersections, "sheets": []}

    for i, sh in enumerate(sheets):
        kind = "affine" if sh["name"] in ("S9",) else "similarity"
        keystone = 3.5e-5 if sh["name"] == "S27" else 0.0
        Hd = _page_transform(_rng(seed + 100 + i), kind=kind, keystone=keystone)

        extra = None
        gx0, gy0, gx1, gy1 = sh["gt_rect"]
        main_place = (margin, margin, page_size[0] - margin, page_size[1] - margin)
        if sh["name"] == "S1":
            # The main region gives up the bottom band of the page, so it covers
            # correspondingly less ground -- at the SAME scale as every other
            # sheet.  Squeezing the same ground into a shorter box instead would
            # make this one sheet anisotropic and unjoinable, which is a fixture
            # bug, not a realistic scan defect.
            main_h = page_size[1] - 2 * margin - detached_band - detached_gap
            main_place = (margin, margin, page_size[0] - margin, margin + main_h)
            sh["gt_rect"] = [gx0, gy0, gx1, gy0 + main_h * S]
            # A strip from the far side of the map: the detached-section analogue.
            det_w, det_h = place_w * S, detached_band * S
            extra = [([W * 0.86, H * 0.74, W * 0.86 + det_w, H * 0.74 + det_h],
                      (margin, page_size[1] - margin - detached_band,
                       page_size[0] - margin, page_size[1] - margin))]

        img, regions = render_sheet(gt, sh["gt_rect"], page_size, Hd, main_place,
                                    extra, f"SHEET {sh['name'][1:]}", seed + 200 + i)

        path = outdir / "original" / f"synthetic_{sh['name']}.jpg"
        cv2.imwrite(str(path), cv2.cvtColor(img, cv2.COLOR_RGB2BGR),
                    [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])
        truth["sheets"].append({
            "name": sh["name"], "grid": sh["grid"], "file": path.name,
            "page_size": list(page_size), "regions": regions,
        })

    (outdir / "truth.json").write_text(json.dumps(truth, indent=2), encoding="utf-8")
    return truth

#!/usr/bin/env python
"""Self-test for build_cuts / build_masks geometry on synthetic data.

Two fake sheets with known transforms and known frontage faces, asserting:
  1. the pooled cut lands midway between the plates' drawn extents;
  2. the two ownership masks tile: no overlap, no gap along the cut;
  3. idempotency: regenerating the files yields byte-identical output;
  4. the region-id uniqueness guard actually raises on a duplicate id;
  5. a measured frontage corner crossing the nominal midline is FLAGGED and
     the cut deviates rather than silently clipping.

Run:  /home/user/g1912/venv/bin/python 50_seams/test_seam_geometry.py
"""

import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seamlib as sl
import build_cuts
import build_masks

from shapely.geometry import Polygon, box


# ---------------------------------------------------------------------------
# synthetic fixture: vertical seam "Test St" between sheet 1 (west, frontage at
# sheet x=900) and sheet 2 (east, frontage at sheet x=100, raw tx=950).
# Mosaic frontages: 900 (sheet 1) and 1050 (sheet 2) -> cut must land at 975.

RAW = {
    1: {"a": 1.0, "b": 0.0, "tx": 0.0, "ty": 0.0},
    2: {"a": 1.0, "b": 0.0, "tx": 950.0, "ty": 0.0},
}
QUADS = {
    1: np.array([[0.0, 0.0], [1000.0, 0.0], [1000.0, 800.0], [0.0, 800.0]]),
    2: np.array([[0.0, 0.0], [1000.0, 0.0], [1000.0, 800.0], [0.0, 800.0]]),
}
ADJ = {
    "edges": {
        "1": {"top": [None, None], "bottom": [None, None],
              "left": [None, None], "right": [2, "Test St"]},
        "2": {"top": [None, None], "bottom": [None, None],
              "left": [1, "Test St"], "right": [None, None]},
    },
    "internal_pairs": [{"sheets": [1, 2], "shared_feature": "Test St"}],
}


def anchor(name, y, x1=900.0, x2=100.0):
    """One synthetic anchor: both plates' cross-street faces ending at their
    frontage corners (seam-ward endpoints) at height y."""
    return {
        "street_id": "test_st", "street_name": "Test St", "pair": [1, 2],
        "anchor": name, "file": "synthetic",
        "plates": {
            1: {"segs_sheet": [[[700.0, y - 10], [x1, y - 10]],
                               [[700.0, y + 10], [x1, y + 10]]],
                "corners_sheet": [[x1, y - 10], [x1, y + 10]],
                "side": "right", "source_sha256": None},
            2: {"segs_sheet": [[[x2, y - 10], [300.0, y - 10]],
                               [[x2, y + 10], [300.0, y + 10]]],
                "corners_sheet": [[x2, y - 10], [x2, y + 10]],
                "side": "left", "source_sha256": None},
        },
    }


def make_cut(records=None):
    records = records or [anchor("A", 100.0), anchor("B", 700.0)]
    return build_cuts.derive_street_cut("test_st", "Test St", records, RAW, QUADS)


def test_cut_lands_midway():
    cut = make_cut()
    pts = np.asarray(cut["polyline_mosaic"])
    assert cut["orientation"] == "vertical"
    assert np.allclose(pts[:, 0], 975.0, atol=1e-6), pts
    assert all(abs(o) < 1e-9 for _, o in cut["polyline_tn"])
    assert cut["flagged_spans"] == []
    # solved width = separation of the two frontages
    for a in cut["anchors"]:
        assert abs(a["solved_street_width_px"] - 150.0) < 1e-6
    print("PASS cut lands midway (x=975, width 150)")
    return cut


def test_masks_tile(cut):
    cuts_doc = {"streets": [cut]}
    features, stats = build_masks.build_regions(
        RAW, ADJ, QUADS, cuts_doc, {"exclusions": []})
    assert len(features) == 2
    polys = {f["sheet"]: Polygon(f["polygon_mosaic"]["exterior"]) for f in features}
    inter = polys[1].intersection(polys[2])
    assert inter.area < 1e-6, "overlap along cut: %.6f px^2" % inter.area
    union = polys[1].union(polys[2])
    pages = Polygon(sl.apply_raw(RAW[1], QUADS[1])).union(
        Polygon(sl.apply_raw(RAW[2], QUADS[2])))
    assert abs(union.area - pages.area) < 1e-6, "gap: union != page union"
    # a band straddling the cut is fully covered
    band = box(960.0, 5.0, 990.0, 795.0)
    assert band.difference(union).area < 1e-9, "gap in band around the cut"
    # sheet-frame polygons round-trip: sheet 1 region reaches exactly x=975
    f1 = [f for f in features if f["sheet"] == 1][0]
    xs = [p[0] for p in f1["polygon_sheet_px"]["exterior"]]
    assert abs(max(xs) - 975.0) < 1e-6
    f2 = [f for f in features if f["sheet"] == 2][0]
    xs2 = [p[0] for p in f2["polygon_sheet_px"]["exterior"]]
    assert abs(min(xs2) - 25.0) < 1e-6  # mosaic 975 - tx 950
    # coverage margins positive on both sides
    for st in stats:
        for c in st["cut_coverage_margins_px"]:
            assert c["margin_px"] > 0
    print("PASS masks tile: overlap 0, no gap, sheet-frame round-trip exact")
    return cuts_doc, features


def test_idempotency(cut):
    with tempfile.TemporaryDirectory() as td:
        pa, pb = os.path.join(td, "a.json"), os.path.join(td, "b.json")
        cut2 = make_cut()
        sl.write_canonical_json(pa, {"streets": [cut]})
        sl.write_canonical_json(pb, {"streets": [cut2]})
        ba, bb = open(pa, "rb").read(), open(pb, "rb").read()
        assert ba == bb, "regenerated cuts differ byte-wise"
        # masks path
        f1, _ = build_masks.build_regions(RAW, ADJ, QUADS, {"streets": [cut]},
                                          {"exclusions": []})
        f2, _ = build_masks.build_regions(RAW, ADJ, QUADS, {"streets": [cut2]},
                                          {"exclusions": []})
        assert sl.canonical_dumps(f1) == sl.canonical_dumps(f2)
    print("PASS idempotency: regenerated outputs byte-identical")


def test_duplicate_region_id_raises():
    reg = sl.RegionRegistry()
    reg.add({"region_id": "s01_r0"})
    try:
        reg.add({"region_id": "s01_r0"})
    except sl.RegionIdError:
        print("PASS duplicate region_id raises RegionIdError")
        return
    raise AssertionError("duplicate region_id did NOT raise")


def test_crossing_is_flagged_and_deviated():
    # sheet 2's frontage corner at anchor C crosses the nominal midline
    # (three anchors so the TLS fit cannot simply chase the outlier)
    recs = [anchor("A", 100.0), anchor("B", 400.0), anchor("C", 700.0)]
    recs[2]["plates"][2]["corners_sheet"] = [[0.0, 690.0], [100.0, 710.0]]
    cut = build_cuts.derive_street_cut("test_st", "Test St", recs, RAW, QUADS)
    assert len(cut["flagged_spans"]) >= 1, "crossing corner was not flagged"
    f = cut["flagged_spans"][0]
    assert f["sheet"] == 2 and f["margin_px"] < 4.0
    # polyline actually deviates (has non-zero offsets), not silently straight
    offs = [o for _, o in cut["polyline_tn"]]
    assert min(offs) < 0 or max(offs) > 0, "cut did not deviate at flagged span"
    # deviated cut keeps the crossing corner on sheet 2's side with clearance
    line = cut["line_fit"]
    corner = np.asarray(f["corner_mosaic"])
    tn = cut["polyline_tn"]
    t_c = sl.line_along(line, corner)
    # offset of the polyline at t_c
    tn_sorted = sorted(tn)
    o_cut = np.interp(t_c, [t for t, _ in tn_sorted], [o for _, o in tn_sorted])
    sgn = cut["sheet_side_sign"]["2"]
    assert sgn * (sl.line_offset(line, corner) - o_cut) >= 8.0
    print("PASS crossing content flagged and cut deviates with clearance")


def main():
    cut = test_cut_lands_midway()
    test_masks_tile(cut)
    test_idempotency(cut)
    test_duplicate_region_id_raises()
    test_crossing_is_flagged_and_deviated()
    print("ALL SELF-TESTS PASSED")


if __name__ == "__main__":
    main()

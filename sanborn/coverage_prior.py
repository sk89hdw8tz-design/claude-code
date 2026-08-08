"""Verified sheet coverage (spec §3.3/§3.4 priors, revised against the actual
scans during the build — sheet 11 is L-shaped and is split into two
rectangular on-grid panels; sheet 13's upper panel covers D-G x 26-28 West).

Units are registration/compositing units: one rectangular on-grid panel each.
Keys are strings; "file" is the physical sheet number. "region" is the panel
rectangle in native px (None = whole sheet).

Avenue indices: A=0 ... J=9. Streets are plain numbers.
"""

AV = {c: i for i, c in enumerate("ABCDEFGHIJ")}

COVERAGE = {
    "1885": {
        "2":   {"file": 2,  "av": ("A", "D"), "st": (16, 19), "region": None},
        "3":   {"file": 3,  "av": ("D", "G"), "st": (18, 20),
                "region": (0, 2500, 6450, 7650),
                "note": "lower panel; upper panel off-scale (street pitch ~606) — excluded"},
        "4":   {"file": 4,  "av": ("G", "H"), "st": (25, 28),
                "region": (0, 0, 2260, 7650),
                "note": "left panel; middle/right panels east of Broadway — excluded"},
        "5":   {"file": 5,  "av": ("G", "J"), "st": (20, 23), "region": None},
        "6":   {"file": 6,  "av": ("D", "G"), "st": (20, 23), "region": None,
                "note": "contains 22nd & Postoffice"},
        "7":   {"file": 7,  "av": ("A", "D"), "st": (19, 22), "region": None},
        "9":   {"file": 9,  "av": ("A", "D"), "st": (22, 25), "region": None,
                "note": "wash-dominated (Strand brick); tone needs the cream "
                        "filter — paper itself is warm, NOT green"},
        "10":  {"file": 10, "av": ("D", "G"), "st": (23, 26), "region": None},
        "11a": {"file": 11, "av": ("G", "H"), "st": (23, 25),
                "region": (0, 0, 2200, 4950),
                "clip_region": (0, 0, 2040, 4950),
                "note": "left leg of L-shaped upper-left panel"},
        "11b": {"file": 11, "av": ("H", "I"), "st": (23, 24),
                "region": (1850, 0, 4190, 2650),
                "clip_region": (2040, 0, 4190, 2650),
                "note": "upper step; clip disjoint from 11a so the overlap "
                        "renders once. Split at 2040 keeps the vertical "
                        "AV. H OR WILLIAMS E. label (x~2070-2230) whole on "
                        "11b's side — at 2100 the units' mapping mismatch "
                        "beheaded every glyph (QC v3-2)"},
        "13":  {"file": 13, "av": ("D", "G"), "st": (26, 28),
                "region": (0, 0, 6450, 5100),
                "clip_region": (0, 0, 6450, 5195),
                "note": "upper panel (West addresses); wharf lower panel excluded. "
                        "clip_region reaches past the detection region to keep the "
                        "SEE SHEET No.17/16 row whole (text ends ~5161, lower "
                        "panel frame starts ~5215)"},
        "14":  {"file": 14, "av": ("A", "D"), "st": (25, 28), "region": None},
    },
    "1877": {
        "3":  {"file": 3,  "av": ("A", "D"), "st": (20, 23), "region": None},
        "4":  {"file": 4,  "av": ("A", "D"), "st": (23, 26), "region": None},
        "9":  {"file": 9,  "av": ("D", "G"), "st": (23, 26), "region": None},
        "10": {"file": 10, "av": ("D", "G"), "st": (20, 23), "region": None,
               "note": "physical tear blocks 441-442 — retained, authentic"},
    },
}

EXCLUDED = {
    "1885": {
        "1": "index/key sheet — reference only, never in art",
        "3-upper": "off-scale panel (street pitch ~606 vs 1135 at detect scale)",
        "4-middle/right": "east of Broadway, outside downtown grid",
        "8": "Avenue A wharf strip, outside crop",
        "11-other-panels": "Ave J-M West / 26th-31st, off the downtown grid",
        "12": "Ave M-N / Beach Hotel, outside crop",
        "13-lower": "wharf panel (33rd-35th), outside crop",
        "15,16,17,18,19": "west/south of the downtown crop (28th-34th)",
    },
    "1877": {
        "2": "A-D x 17-20, west of crop",
        "5": "outlying (B-E West, 26-29)",
        "6": "outlying (C-F West, 29-32)",
        "7": "cotton presses, disconnected",
        "8": "nine geographically disconnected panels",
    },
}

# Genuine gaps in the composite extent with NO on-grid source in the edition:
# - 1885 avenues G-J x streets 16-20 (sheet 3's off-scale upper panel covered
#   part; nothing on-grid does)
# - 1885 avenues D-G x streets 16-18 (no sheet in the 19-sheet edition covers
#   this band; verified by reading sheets 12-19)
# - 1885 avenue I-J columns south of 23/25 except where sheets 4/5 reach
# Filled with flat paper tone and disclosed. Never generated content.


def expected_lines(year, key):
    c = COVERAGE[year][key]
    a0, a1 = AV[c["av"][0]], AV[c["av"][1]]
    s0, s1 = c["st"]
    return list(range(a0, a1 + 1)), list(range(s0, s1 + 1))


def composite_extent(year):
    avs, sts = [], []
    for key in COVERAGE[year]:
        a, s = expected_lines(year, key)
        avs += a
        sts += s
    return min(avs), max(avs), min(sts), max(sts)


# Seams where the default owner (top/left unit) CANNOT own the boundary
# corridor because its printed panel physically ends at the boundary: the
# ownership cap then pins the cut at the owner's print extent, exposing the
# neighbor's duplicate street label below it (QC v3-3: "25TH ST." printed
# twice at Ave G, overprinting SEE SHEET No.4). Flipped seams are owned by
# the OTHER unit, whose sheet prints the whole corridor: the cut is searched
# ABOVE/LEFT of the boundary line and the default owner keeps only content
# beyond its own label copy.
SEAM_FLIPS = {
    ("h", 25, frozenset({"11a", "4"})),   # 11a's panel stops at 25th
}

# Manual cut positions (global px relative to the boundary line) for
# corridors where automated placement cannot resolve the label layout —
# measured from the corridor ink profiles and verified by crop:
#   h19 2|7: sheet 2's 19TH ST. label ends +50, its 8" W.PIPE main ends
#     ~+150, its frame rule starts ~+250 -> cut in the clean band between.
#   h23 5|x: sheet 5's small 23RD OR copy sits ~-160..-30 while 11a/11b
#     carry the display TREMONT below the line -> cut above 5's copy so
#     exactly one (the neighbors') renders.
# All values profile-measured (owner ink mean/p97 over the corridor) and
# placed in verified-clean rows; QC rounds v4.2-1 and v4.3.
SEAM_CUTS = {
    ("h", 19, frozenset({"2", "7"})): +190,
    ("h", 22, frozenset({"7", "9"})): +252,   # +190 sliced the scale-bar
    #   numerals at +200..+230; clean window +240..+265, frame rule +340
    ("h", 23, frozenset({"5", "11a"})): -210,
    ("h", 23, frozenset({"5", "11b"})): -210,
    ("h", 23, frozenset({"6", "10"})): +150,  # auto cut -176 replaced the
    #   TREMONT OPERA HO. block + Babcock note with sheet 10's margin;
    #   +150 sits after the label zone, before the rule at +200
    ("h", 25, frozenset({"9", "14"})): +318,  # auto cut -200 replaced the
    #   25th x Ave B north-side row (T.W. English Coal Yard, Artificial
    #   Stone Wks, lots 501-508, Scale of Feet) with sheet 14's margin;
    #   +318 is the clean row past that content
    ("v", 6, frozenset({"10", "11a"})): -200,  # AV. G OR WINNIE printed
    #   twice at 23-25 with the +36 auto cut between the copies; -200 is
    #   west of both so only 11a's prints (QC v4.2-1)
}

# Static per-scan-edge insets (native px) for retained exterior margins,
# fixed by measurement + visual verification of every retained side
# (compare/margins/*.jpg). Dynamic junk detection failed in BOTH
# directions here: thin scanner rules slipped through erosion, while
# rail sidings and bay water along Water St (sheets 2, 9, 14) were
# flagged as junk and the trim beheaded certified annotations (QC
# v3.2-1). The scanner rules hug the scan edge; nothing legitimate
# sits within ~20 px of it. Keyed by (sheet_file, side); default 24.
SCAN_INSET_DEFAULT = 24
SCAN_INSETS = {
    (5, "top"): 65,      # tapering black wedge, up to ~28 px thick
    (5, "right"): 70,    # full-height black band + backing strip
    (3, "right"): 70,    # black band + grey-blue backing
    (3, "top"): 120,     # region-relative: panel divider carries the
                         # upper panel's ~44px frame rule (QC v4-C)
    (4, "bottom"): 90,
    (7, "left"): 80,
    (13, "bottom"): 0,   # clip_region 5195 is precision-set to the SEE
                         # SHEET row; no further inset
    (14, "left"): 60,
    (14, "bottom"): 170,   # 80 re-exposed the ~50-70px backing board at
                           # source y~7499 (QC v4-B); 170 trims to y7480
}


def neighbors(year):
    """Seam registry: {(axis, boundary_index, frozenset({keyA,keyB}))} where
    axis 'v' = shared avenue (vertical line), 'h' = shared street. A pair
    shares a seam when one's max equals the other's min on that axis and
    their ranges overlap on the cross axis."""
    seams = []
    ks = list(COVERAGE[year])
    for i, ka in enumerate(ks):
        aa, sa = expected_lines(year, ka)
        for kb in ks[i + 1:]:
            ab, sb = expected_lines(year, kb)
            # vertical seam: A's right avenue == B's left avenue, street overlap
            if max(aa) == min(ab) and min(max(sa), max(sb)) > max(min(sa), min(sb)):
                seams.append(("v", max(aa), ka, kb))   # ka = left
            if max(ab) == min(aa) and min(max(sa), max(sb)) > max(min(sa), min(sb)):
                seams.append(("v", max(ab), kb, ka))
            # horizontal seam: A's bottom street == B's top street, avenue overlap
            if max(sa) == min(sb) and min(max(aa), max(ab)) > max(min(aa), min(ab)):
                seams.append(("h", max(sa), ka, kb))   # ka = top
            if max(sb) == min(sa) and min(max(aa), max(ab)) > max(min(aa), min(ab)):
                seams.append(("h", max(sb), kb, ka))
    return seams

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
    s0, s1 = c["st"]
    if "av_slots" in c:
        # 1899-style: uniform-pitch corridor slots (A=0..M=12, then the
        # outlot district names every corridor: M1/2=13 .. S=24)
        return list(c["av_slots"]), list(range(s0, s1 + 1))
    a0, a1 = AV[c["av"][0]], AV[c["av"][1]]
    return list(range(a0, a1 + 1)), list(range(s0, s1 + 1))


def expected_detect_lines(year, key):
    """Line identities the detector should find — same as expected_lines
    now that the 1899 axis is uniform slots (every slot is a real,
    comb-detectable corridor)."""
    return expected_lines(year, key)


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
    # (1885 entries only — 1899 lives in SEAM_CUTS_1899 below)
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


def scan_inset(year, filenum, side):
    """Per-year lookup: SCAN_INSETS keys are bare (file, side) measured on
    the 1885 LoC masters; they must never leak onto 1899's UT scans, whose
    sheet numbers overlap. 1899 has its own measured table."""
    if year == "1885":
        return SCAN_INSETS.get((filenum, side), SCAN_INSET_DEFAULT)
    if year == "1899":
        return SCAN_INSETS_1899.get((filenum, side), SCAN_INSET_DEFAULT)
    return SCAN_INSET_DEFAULT


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



# 1885 edge-line overrides (playbook s3). The whiteness comb latches the
# block FRONTAGE wherever a corridor is cut by the sheet's own paper edge.
# Measured on every unit by fixing the pitch at the edition nominal
# (1856 x 2170, confirmed by unit 14 whose lines are clean to +-0.4%) and
# anchoring the phase on the unit's INTERIOR lines: both edge spacings ran
# 3-5% short on nearly every sheet while the middle spacing sat at nominal,
# i.e. both edges pulled inward onto frontages. Verified visually on unit
# 10's Avenue D line: the detected position lay on the building frontage,
# the predicted position in the open corridor. Untreated this distorted the
# fitted SCALE enough to fail the +-2% gate on units 6 and 9.
# Values are native px on the LoC masters (6450 x 7650).
LINE_OVERRIDES_1885 = {
    "7": {
        "y": {"19": 564.8, "22": 7074.8},
    },
    "9": {
        "x": {"0": 492.1, "3": 6060.1},
        "y": {"22": 582.6, "25": 7092.6},
    },
    "3": {
        "x": {"6": 5875.8},
    },
    "6": {
        "x": {"6": 5910.0},
        "y": {"20": 561.0, "23": 7071.0},
    },
    "10": {
        "x": {"3": 391.1, "6": 5959.2},
        "y": {"23": 544.8, "26": 7054.8},
    },
    "5": {
        "x": {"6": 527.6},
        "y": {"20": 580.2, "23": 7090.2},
    },
    "2": {
        "x": {"3": 6147.2},
        "y": {"16": 569.6, "19": 7079.6},
    },
    "4": {
        "y": {"25": 556.2, "28": 7066.2},
    },
}

for _u, _ov in LINE_OVERRIDES_1885.items():
    if _u in COVERAGE["1885"]:
        _lo = COVERAGE["1885"][_u].setdefault("line_overrides", {})
        for _ax, _f in _ov.items():
            _lo.setdefault(_ax, {}).update(_f)

def _load_1889():
    import json as _json
    import os as _os
    p = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                      "coverage_1889.json")
    if _os.path.exists(p):
        d = _json.load(open(p))
        COVERAGE["1889"] = d["units"]
        EXCLUDED["1889"] = d.get("excluded", {})


def _load_1899():
    import json as _json
    import os as _os
    p = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                      "coverage_1899.json")
    if _os.path.exists(p):
        d = _json.load(open(p))
        COVERAGE["1899"] = d["units"]
        EXCLUDED["1899"] = d["excluded"]


_load_1889()
_load_1899()


def neighbors(year):
    """Seam registry: {(axis, boundary_index, frozenset({keyA,keyB}))} where
    axis 'v' = shared avenue (vertical line), 'h' = shared street. A pair
    shares a seam when one's max equals the other's min on that axis and
    their ranges overlap on the cross axis."""
    def overlaps(ra, rb):
        """Do two identity ranges share more than a corner? Strict for two
        real ranges (corner-touching units are not neighbours), but a
        DEGENERATE range — a wharf unit carrying the single Avenue A line —
        genuinely shares that corridor with the unit above it. Requiring a
        strict overlap left 06|07 with no seam at all, so both rendered the
        22nd St corridor and feathered together: doubled PIER No 22, doubled
        22ND ST., and a ghosted warehouse through the blend band."""
        ov = min(max(ra), max(rb)) - max(min(ra), min(rb))
        degenerate = len(ra) == 1 or len(rb) == 1
        return ov > 0 or (degenerate and ov == 0)

    seams = []
    ks = list(COVERAGE[year])
    for i, ka in enumerate(ks):
        aa, sa = expected_lines(year, ka)
        for kb in ks[i + 1:]:
            ab, sb = expected_lines(year, kb)
            # vertical seam: A's right avenue == B's left avenue, street overlap
            if max(aa) == min(ab) and overlaps(sa, sb):
                seams.append(("v", max(aa), ka, kb))   # ka = left
            if max(ab) == min(aa) and overlaps(sa, sb):
                seams.append(("v", max(ab), kb, ka))
            # horizontal seam: A's bottom street == B's top street, avenue overlap
            if max(sa) == min(sb) and overlaps(aa, ab):
                seams.append(("h", max(sa), ka, kb))   # ka = top
            if max(sb) == min(sa) and overlaps(aa, ab):
                seams.append(("h", max(sb), kb, ka))
    return seams


# 1899 manual cuts. The wharf sheets ABUT at their shared street rather than
# overlapping (verified: their drawings of the shared band correlate at only
# 0.145, while the railroad tracks cross the join with a 4.5 px jog — the
# geometry is right, the sheets simply do not draw the same ground twice).
# Each sheet nevertheless letters the same pier on its own side of the line,
# so an automatic cut placed between the two copies renders both. Measured
# positions, global px relative to the shared line:
# That is now handled uniformly by the owner-on-top seam policy rather than
# by per-seam offsets.
SEAM_CUTS_1899 = {
    # Default: every 1899 seam is resolved by the owner-on-top policy
    # (config.EDITIONS['1899']['seam_policy']) plus the frame/paper clamp
    # in legal_cut, which together keep one complete copy of the shared
    # corridor. Manual offsets would re-introduce a cut inside the
    # overlap — exactly what the seam QC pass found destroys frontage
    # strips and street names. Exceptions below are measured to the pixel.
    #
    # h22 06|07 (wharf): sheet 07 draws the ENTIRE shared band to its
    # paper edge — full Pier 22 warehouse, its "6" pointer numeral
    # (native rows 3846-3917), NO EXPOSURE (to 3934), paper ends ~3937,
    # UT citation on backing at 3986+. The frame-estimate clamp cut at
    # +142, slicing the pointer numeral in half. +175 = the paper edge:
    # numeral and NO EXPOSURE whole, backing and citation excluded.
    # (Flipping 06 on top was tried and rejected: 06's scan is cut at
    # ~90 px above 22nd, so every candidate cut sliced or ghosted a
    # label copy — 22ND ST, PIER No 22 — that 07 prints intact.)
    ("h", 22, frozenset({"06", "07"})): +177,
}

# 1899 per-scan-edge insets (native px), measured like the 1885 table.
# Sheet 7's bottom: content runs to native 3934, paper to ~3937, white
# backing from 3940 — the default 24 would pull a paper-edge cut into
# the pointer numeral.
SCAN_INSETS_1899 = {
    (7, "bottom"): 0,
    # h-seam owner bottoms: content ends 2-9 px above the paper edge (the
    # atlas cut these sheets at the shared street); the default 24 would
    # pull the paper-edge cut into the frontage numerals. The UT citation
    # sits on backing BELOW the cream paper, outside paper_bounds.
    (11, "bottom"): 0,
    (12, "bottom"): 0,
    (41, "bottom"): 0,
    (13, "bottom"): 0,
    (14, "bottom"): 0,
    (39, "bottom"): 0,
}

# Sides where the atlas cut the sheet AT the shared street and printed NO
# frame line (verified for EVERY interior side of the twelve 1899 sheets:
# no dark run > 1500 px anywhere in the 450 px edge band; content runs to
# within 2-9 px of the paper edge on the h-seam bottoms). frame_bounds
# latches onto interior block walls on these sides; capping clips there
# amputated the frontage band only that sheet draws (south-side 21st/24th
# address rows, Ave D/G east-kerb columns, the "Avenue D void" — content
# QC findings 1-5). The paper bound replaces the frame estimate on these
# sides for clips AND the legal_cut window, so owner-on-top cuts land at
# the true paper edge like the wharf +175 cut.
FRAME_OPEN_SIDES = {
    # 1889: measured the same way as 1899 and with the same result — no
    # printed frame line on any seam-facing edge. Longest dark run in the
    # 260 px edge band (scaled from 1899's 450 px band for these 3400 px
    # scans) came out 77-402 px on every interior side; the few larger hits
    # (09 left 1437, 07 left 1046, 27 left 927, 10 top 989) are still under
    # 35% of the sheet dimension, i.e. rail lines and frontage rules, not
    # neat lines. Untreated, the bogus frame estimate clamped the v-seam
    # cuts to only +6..+61 px past the corridor line, so BOTH sheets'
    # copies of the avenue label rendered (AV. D OR MARKET E. twice at the
    # 07|08 seam). 1899's equivalent cuts sit at +167..+174.
    "1889": {
        ("07", "right"), ("07", "bottom"),
        ("08", "left"), ("08", "right"), ("08", "bottom"),
        ("29", "left"), ("29", "bottom"),
        ("09", "right"), ("09", "top"),
        ("10", "left"), ("10", "right"), ("10", "top"),
        ("27", "left"), ("27", "top"),
        ("02", "right"), ("02", "bottom"),
        ("01", "right"), ("01", "top"),
    },
    "1899": {
        ("11", "bottom"), ("11", "right"),
        ("12", "left"), ("12", "bottom"), ("12", "right"),
        ("41", "left"), ("41", "bottom"),
        ("13", "top"), ("13", "bottom"), ("13", "right"),
        ("14", "top"), ("14", "left"), ("14", "bottom"), ("14", "right"),
        ("39", "top"), ("39", "left"), ("39", "bottom"),
        ("15", "top"), ("15", "right"),
        ("16", "top"), ("16", "left"), ("16", "right"),
        ("37", "top"), ("37", "left"),
    },
}

SEAM_CUTS_BY_YEAR = {"1885": SEAM_CUTS, "1899": SEAM_CUTS_1899}


def seam_cut(year, axis, idx, pair):
    """Manual cut offset for one seam, or None. Year-scoped: 1885's keys are
    unpadded sheet numbers that would otherwise collide with 1899's."""
    return SEAM_CUTS_BY_YEAR.get(year, {}).get((axis, idx, pair))

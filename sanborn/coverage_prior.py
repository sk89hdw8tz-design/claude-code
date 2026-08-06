"""Verified sheet coverage from the prior run (spec §3.3/§3.4).

These are PRIORS: Phase B re-verifies each sheet's identity two independent
ways (1885 index-sheet street index + each sheet's own printed labels; 1877
labels only) before the affine fit trusts these ranges.

Avenue indices: A=0, B=1, ... J=9. Streets are plain numbers.
"""

AV = {c: i for i, c in enumerate("ABCDEFGHIJ")}

# edges: which sides of this sheet lie on the rim of the whole composite
# (extend clip outward there instead of shifting past a boundary street).
COVERAGE = {
    "1885": {
        2:  {"av": ("A", "D"), "st": (16, 19)},
        3:  {"av": ("D", "G"), "st": (18, 20), "panel": "lower",
             "note": "upper panel off-scale (street pitch ~606) — excluded"},
        4:  {"av": ("G", "H"), "st": (25, 28), "panel": "left",
             "note": "right panel east of Broadway — excluded"},
        5:  {"av": ("G", "J"), "st": (20, 23)},
        6:  {"av": ("D", "G"), "st": (20, 23), "note": "contains 22nd & Postoffice"},
        7:  {"av": ("A", "D"), "st": (19, 22)},
        9:  {"av": ("A", "D"), "st": (22, 25)},
        10: {"av": ("D", "G"), "st": (23, 26)},
        11: {"av": ("G", "I"), "st": (23, 25), "panel": "upper-left",
             "note": "stepped boundary; only upper-left panel on grid"},
        14: {"av": ("A", "D"), "st": (25, 28)},
    },
    "1877": {
        3:  {"av": ("A", "D"), "st": (20, 23)},
        4:  {"av": ("A", "D"), "st": (23, 26)},
        9:  {"av": ("D", "G"), "st": (23, 26)},
        10: {"av": ("D", "G"), "st": (20, 23),
             "note": "physical tear blocks 441-442 — retained, authentic"},
    },
}

EXCLUDED = {
    "1885": {
        1: "index/key sheet — reference only, never in art",
        "3-upper": "off-scale panel (street pitch ~606 vs 1135)",
        "4-right": "east of Broadway, outside downtown crop",
        8: "Avenue A wharf strip, outside crop",
        "12,13,15-19": "outside downtown crop",
    },
    "1877": {
        2: "A-D x 17-20, west of crop used only if crop extended",
        5: "outlying (B-E West, 26-29)",
        6: "outlying (C-F West, 29-32)",
        7: "cotton presses, disconnected",
        8: "nine geographically disconnected panels",
    },
}

# Known genuine gap, 1885: Avenue G-H x 18th-20th — the edition does not map
# it (index lists Eighteenth St. only on sheets 2-3; the 19th-20th part exists
# only on sheet 3's excluded upper panel). Flat paper tone, disclosed.


def expected_lines(year, sheet):
    """(avenue indices, street numbers) this sheet should contribute."""
    c = COVERAGE[year][sheet]
    a0, a1 = AV[c["av"][0]], AV[c["av"][1]]
    s0, s1 = c["st"]
    return list(range(a0, a1 + 1)), list(range(s0, s1 + 1))


def composite_extent(year):
    """(av_min, av_max, st_min, st_max) over the working set."""
    avs, sts = [], []
    for sheet in COVERAGE[year]:
        a, s = expected_lines(year, sheet)
        avs += a
        sts += s
    return min(avs), max(avs), min(sts), max(sts)


def composite_edges(year, sheet):
    a0, a1, s0, s1 = composite_extent(year)
    a, s = expected_lines(year, sheet)
    edges = set()
    if min(a) == a0:
        edges.add("left")
    if max(a) == a1:
        edges.add("right")
    if min(s) == s0:
        edges.add("top")
    if max(s) == s1:
        edges.add("bottom")
    return edges

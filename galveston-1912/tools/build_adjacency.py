"""Record the adjacency graph read from the plates' printed edge references,
and check it for reciprocity and against the key-map grid.

Each plate prints its neighbour's sheet number centred on each edge, together
with the street or avenue they share. That is a third source, independent of
the key map and the street index, and it names the shared feature -- which is
what the seam network needs.
"""

import json
import os
from itertools import combinations

OUT = "/home/user/claude-code/galveston-1912/10_key"
os.makedirs(OUT, exist_ok=True)

# Transcribed from galveston-1912 adjacency montage (plate edge references).
# None = edge faces the bay or carries no reference.
EDGES = {
    # Sheet 5 is a long wharf strip spanning several street rows, so its landward
    # edge carries several references along its length (7, 9, 11, then 13 beyond
    # the selected set), all on Ave. A or Water. Verified by reading the whole
    # edge; sampling only its centre finds just one and fakes a reciprocity error.
    5:  {"top": (None, "16th St"),      "bottom": (None, None),
         "left": (None, "Galveston Bay"),
         "right": [(7, "Ave. A or Water"), (9, "Ave. A or Water"),
                   (11, "Ave. A or Water"), (13, "Ave. A or Water")]},
    7:  {"top": (33, "18th St"),  "bottom": (9,  "21st or Center St"),
         "left": (5, "Ave. A or Water"), "right": (8,  "Ave. C or Mechanic")},
    8:  {"top": (34, "18th St"),  "bottom": (10, "21st or Center St"),
         "left": (7, "Ave. C or Mechanic"), "right": (39, "Ave. F or Church")},
    9:  {"top": (7,  "21st or Center St"), "bottom": (11, "24th St"),
         "left": (5, "Ave. A or Water"), "right": (10, "Ave. C or Mechanic")},
    10: {"top": (8,  "21st or Center St"), "bottom": (12, "24th St"),
         "left": (9, "Ave. C or Mechanic"), "right": (43, "Ave. F or Church")},
    11: {"top": (9,  "24th St"),  "bottom": (13, "27th St"),
         "left": (5, "Ave. A or Water"), "right": (12, "Ave. C or Mechanic")},
    12: {"top": (10, "24th St"),  "bottom": (14, "27th St"),
         "left": (11, "Ave. C or Mechanic"), "right": (49, "Ave. F or Church")},
    39: {"top": (35, "18th St"),  "bottom": (43, "21st or Center St"),
         "left": (8, "Ave. F or Church"), "right": (40, "Ave. I or Sealy")},
    40: {"top": (36, "18th St"),  "bottom": (44, "21st or Center St"),
         "left": (39, "Ave. I or Sealy"), "right": (41, "Avenue L")},
    43: {"top": (39, "21st or Center St"), "bottom": (49, "24th St"),
         "left": (10, "Ave. F or Church"), "right": (44, "Ave. I or Sealy")},
    44: {"top": (40, "21st or Center St"), "bottom": (50, "24th St"),
         "left": (43, "Ave. I or Sealy"), "right": (45, "Avenue L")},
    49: {"top": (43, "24th St"),  "bottom": (55, "27th St"),
         "left": (12, "Ave. F or Church"), "right": (50, "Ave. I or Sealy")},
    50: {"top": (44, "24th St"),  "bottom": (56, "27th St"),
         "left": (49, "Ave. I or Sealy"), "right": (51, "Avenue L")},
}

OPPOSITE = {"top": "bottom", "bottom": "top", "left": "right", "right": "left"}
IN_SET = set(EDGES)


def refs(side_value):
    """An edge carries one reference, or several along its length."""
    return side_value if isinstance(side_value, list) else [side_value]


# --- reciprocity check -------------------------------------------------------
problems = []
pairs = {}
for a, sides in EDGES.items():
    for side, value in sides.items():
        for b, feature in refs(value):
            if b is None or b not in IN_SET:
                continue  # bay, or a boundary neighbour outside the selected set
            back_refs = refs(EDGES[b][OPPOSITE[side]])
            match = [(nb, nf) for nb, nf in back_refs if nb == a]
            if not match:
                problems.append(
                    f"sheet {a} {side} -> {b}, but sheet {b} {OPPOSITE[side]} -> "
                    f"{[nb for nb, _ in back_refs]}"
                )
                continue
            back_feature = match[0][1]
            if feature != back_feature:
                problems.append(
                    f"pair {a}-{b}: shared feature disagrees ({feature!r} vs {back_feature!r})"
                )
            key = tuple(sorted((a, b)))
            pairs[key] = {
                "sheets": list(key),
                "shared_feature": feature,
                "orientation": "vertical-seam" if side in ("left", "right") else "horizontal-seam",
            }

# --- pooled seam groups: several pairs along one historical street -----------
pooled = {}
for p in pairs.values():
    pooled.setdefault(p["shared_feature"], []).append(p["sheets"])

# --- cross-check against the key-map grid ------------------------------------
# column -> avenues, row -> street span, from the key map and street index
GRID = {
    7: (1, 1), 8: (2, 1), 39: (3, 1), 40: (4, 1),
    9: (1, 2), 10: (2, 2), 43: (3, 2), 44: (4, 2),
    11: (1, 3), 12: (2, 3), 49: (3, 3), 50: (4, 3),
}
grid_problems = []
for (a, b), p in pairs.items():
    if a in GRID and b in GRID:
        (ca, ra), (cb, rb) = GRID[a], GRID[b]
        dc, dr = abs(ca - cb), abs(ra - rb)
        expect = "vertical-seam" if (dc, dr) == (1, 0) else (
            "horizontal-seam" if (dc, dr) == (0, 1) else None
        )
        if expect is None:
            grid_problems.append(f"pair {a}-{b} not grid-adjacent (col/row {GRID[a]} vs {GRID[b]})")
        elif expect != p["orientation"]:
            grid_problems.append(f"pair {a}-{b}: orientation {p['orientation']} != grid {expect}")

result = {
    "source": "adjoining-sheet numbers printed on each plate edge (independent of key map and street index)",
    "sheets": sorted(IN_SET),
    "edges": {str(k): v for k, v in EDGES.items()},
    "internal_pairs": sorted(pairs.values(), key=lambda p: p["sheets"]),
    "pooled_seam_groups": {k: sorted(v) for k, v in sorted(pooled.items())},
    "boundary_neighbours": sorted(
        {
            b
            for s in EDGES.values()
            for v in s.values()
            for b, _ in refs(v)
            if b is not None and b not in IN_SET
        }
    ),
    "reciprocity_problems": problems,
    "key_grid_problems": grid_problems,
}
with open(f"{OUT}/adjacency.json", "w") as fh:
    json.dump(result, fh, indent=1)

print(f"internal pairs: {len(pairs)}")
for feat, ps in sorted(pooled.items()):
    print(f"  {feat:22s} {len(ps)} pair(s): {ps}")
print(f"\nboundary neighbours (outside set): {result['boundary_neighbours']}")
print(f"reciprocity problems: {problems or 'none'}")
print(f"key-grid problems:    {grid_problems or 'none'}")
print(f"\nwrote {OUT}/adjacency.json")

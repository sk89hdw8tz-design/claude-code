"""Map selected 1912 sheet numbers to LOC image indices and emit FETCH_LIST.json.

Sheet numbers come from the key map and are independently confirmed by the
street index; the mapping to LOC image indices is derived from the page
identifiers embedded in the image URLs (e.g. ...g085391912:08539_1912-0039),
never by assuming a fixed offset -- the volume interleaves six skeleton
sheets (0007s..0012s) which would otherwise shift the numbering.
"""

import json
import re

META = "/home/user/g1912/data-branch/galveston_1912_sources/sanborn08539_004_metadata.json"
OUT = "/home/user/g1912/data-branch/galveston_1912_sources/FETCH_LIST.json"

SELECTED = [5, 7, 8, 9, 10, 11, 12, 39, 40, 43, 44, 49, 50]

j = json.load(open(META))
groups = []
for res in j.get("resources", []):
    for g in res.get("files", []):
        if isinstance(g, list):
            groups.append([f for f in g if isinstance(f, dict)])

ident_of = {}
for idx, g in enumerate(groups):
    for f in g:
        m = re.search(r"g085391912[:/]08539_1912-([A-Za-z0-9]+)", str(f.get("url") or ""))
        if m:
            ident_of[idx] = m.group(1)
            break

# sheet number -> index, using only purely-numeric identifiers (skeletons end in 's')
sheet_to_idx = {}
for idx, ident in ident_of.items():
    if ident.isdigit():
        n = int(ident)
        if n in sheet_to_idx:
            raise SystemExit(f"duplicate sheet {n}: idx {sheet_to_idx[n]} and {idx}")
        sheet_to_idx[n] = idx

missing = [s for s in SELECTED if s not in sheet_to_idx]
if missing:
    raise SystemExit(f"sheets not present in volume: {missing}")

indices = [sheet_to_idx[s] for s in SELECTED]
for s in SELECTED:
    print(f"  sheet {s:3d} -> image index {sheet_to_idx[s]:3d} (id {ident_of[sheet_to_idx[s]]})")

payload = {
    "item_id": "sanborn08539_004",
    "kind": "sheet-archival",
    "indices": indices,
    "sheets": SELECTED,
    "sheet_to_image_index": {str(s): sheet_to_idx[s] for s in SELECTED},
    "note": (
        "Downtown/wharf sheets for the 1912 mosaic: 19th-25th St, Avenue A (Water) "
        "to Avenue I (Sealy), Piers 19-25. Selected from the 1912 key map and "
        "independently confirmed against the 1912 street index."
    ),
}
with open(OUT, "w") as fh:
    json.dump(payload, fh, indent=1)
print(f"\nwrote {OUT}: {len(indices)} sheets -> indices {indices}")

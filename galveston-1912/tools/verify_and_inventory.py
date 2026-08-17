"""Verify the archival 1912 sheets and build the immutable source inventory.

Checks, for every selected sheet: the file's SHA-256 matches what the fetch
recorded, the JP2 decodes, and the decoded raster matches the dimensions LOC
declared. Then writes the project inventory. The originals are never modified;
they are read only.
"""

import hashlib
import json
import os
from datetime import datetime, timezone

from PIL import Image

Image.MAX_IMAGE_PIXELS = None

SRC_DIR = "/home/user/g1912/data-branch/galveston_1912_sources"
OUT_DIR = "/home/user/claude-code/galveston-1912/00_inventory"
os.makedirs(OUT_DIR, exist_ok=True)

fetch_list = json.load(open(f"{SRC_DIR}/FETCH_LIST.json"))
recorded = {i["file"]: i for i in json.load(open(f"{SRC_DIR}/inventory.json"))["items"]}
sheet_of_idx = {v: int(k) for k, v in fetch_list["sheet_to_image_index"].items()}

items, problems = [], []
for sheet in fetch_list["sheets"]:
    idx = fetch_list["sheet_to_image_index"][str(sheet)]
    name = f"sanborn08539_004_img{idx:03d}_archival.jp2"
    path = os.path.join(SRC_DIR, name)

    if not os.path.exists(path):
        problems.append(f"sheet {sheet}: MISSING {name}")
        continue

    with open(path, "rb") as fh:
        blob = fh.read()
    sha = hashlib.sha256(blob).hexdigest()

    rec = recorded.get(name)
    if rec is None:
        problems.append(f"sheet {sheet}: not in fetch inventory")
    elif rec["sha256"] != sha:
        problems.append(f"sheet {sheet}: SHA MISMATCH disk={sha[:12]} fetch={rec['sha256'][:12]}")
    if rec and rec["bytes"] != len(blob):
        problems.append(f"sheet {sheet}: size mismatch {len(blob)} vs {rec['bytes']}")

    try:
        im = Image.open(path)
        w, h = im.size
        mode = im.mode
        im.load()  # force full decode, not just the header
        decoded = True
    except Exception as exc:  # noqa: BLE001
        problems.append(f"sheet {sheet}: DECODE FAILED {exc}")
        decoded, w, h, mode = False, None, None, None

    if decoded and (w, h) != (6653, 7795):
        problems.append(f"sheet {sheet}: unexpected size {w}x{h}")

    items.append(
        {
            "sheet": sheet,
            "loc_image_index": idx,
            "file": name,
            "path": path,
            "bytes": len(blob),
            "sha256": sha,
            "width": w,
            "height": h,
            "mode": mode,
            "megapixels": round(w * h / 1e6, 1) if decoded else None,
            "decoded_ok": decoded,
            "source_url": rec["source_url"] if rec else None,
            "downloaded_utc": rec["downloaded_utc"] if rec else None,
        }
    )
    print(f"sheet {sheet:3d} idx {idx:3d}  {w}x{h} {mode}  {len(blob)/1e6:5.1f} MB  sha {sha[:12]}  {'OK' if decoded else 'FAIL'}")

inv = {
    "generated_utc": datetime.now(timezone.utc).isoformat(),
    "edition": "Sanborn Fire Insurance Map, Galveston, Galveston County, Texas, 1912",
    "loc_item": "sanborn08539_004",
    "provenance": "Library of Congress Sanborn Maps Collection; public domain (published pre-1931)",
    "target_extent": "Avenue A (Water) to Avenue I (Sealy); 19th St to 25th St (Rosenberg Av); Piers 19-25",
    "sheet_count": len(items),
    "all_verified": not problems,
    "problems": problems,
    "items": items,
}
with open(os.path.join(OUT_DIR, "INVENTORY.json"), "w") as fh:
    json.dump(inv, fh, indent=1)

print()
if problems:
    print("PROBLEMS:")
    for p in problems:
        print("  -", p)
else:
    print(f"All {len(items)} sheets verified: checksums match, all decode at 6653x7795.")
    tot = sum(i["bytes"] for i in items)
    print(f"Total {tot/1e6:.0f} MB compressed; {sum(i['megapixels'] for i in items):.0f} MP of source raster.")

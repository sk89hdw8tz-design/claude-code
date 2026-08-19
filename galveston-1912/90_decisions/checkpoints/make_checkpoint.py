"""Write a frozen-state checkpoint recording component -> path -> sha256.

The original Pier 22 checkpoint stored hashes WITHOUT paths, which made its
verifier resolve paths by hashing the whole tree - and made a parser bug read as
"0 artefacts checked ... OK". Paths are recorded explicitly here so a component
that cannot be located fails loudly.

Usage: make_checkpoint.py <NAME> "<scope sentence>"
"""
import glob
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

G = "/home/user/claude-code/galveston-1912"
SCAN5 = ("/home/user/g1912/data-branch/galveston_1912_sources/"
         "sanborn08539_004_img009_archival.jp2")

COMPONENTS = {
    "block_transforms": "40_solve/output/transforms.json",
    "block_covariance": "40_solve/output/covariance.json",
    "adjacency_topology": "10_key/adjacency.json",
    "cuts_block_streets": "50_seams/cuts.json",
    "masks_block": "50_seams/masks.json",
    "manual_deviations": "50_seams/manual_deviations.json",
    "manual_exclusions": "50_seams/manual_exclusions.json",
    "freeze_manifest": "40_solve/FREEZE_MANIFEST.json",
    "inventory": "00_inventory/INVENTORY.json",
    "sheet5_panel_transforms":
        "40_solve/output_sheet5_joint/transforms_sheet5_joint_shared.json",
    "block_master_tif": "60_master/final/candidate_master.tif",
    "current_master_full": "60_master/final/master_full.tif",
    "compositor": "60_master/tools/composite_wharf.py",
    "water_spec": "50_seams/water_regions.geojson",
    "tone_spec": "50_seams/tone_anchors.json",
    "flatfield_spec": "50_seams/paper_flatfield.json",
    "archival_sheet5": SCAN5,
}


def sha256_file(p, chunk=1 << 22):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


name = sys.argv[1]
scope = sys.argv[2] if len(sys.argv) > 2 else ""
items = {}
for k, rel in COMPONENTS.items():
    p = rel if os.path.isabs(rel) else os.path.join(G, rel)
    if not os.path.exists(p):
        sys.exit(f"FATAL: {k} missing at {p}")
    items[k] = {"path": rel, "sha256": sha256_file(p)}
ctrl = {}
for p in sorted(glob.glob(f"{G}/30_controls/verified/*.json")):
    ctrl[os.path.basename(p)] = {"path": os.path.relpath(p, G), "sha256": sha256_file(p)}
items["controls"] = ctrl

out = {"checkpoint": name, "created_utc": datetime.now(timezone.utc).isoformat(),
       "scope": scope, "immutable": items}
dest = f"{G}/90_decisions/checkpoints/{name}.json"
json.dump(out, open(dest, "w"), indent=1)
n = len(items) - 1 + len(ctrl)
print(f"wrote {dest}  ({n} artefacts hashed, paths recorded)")

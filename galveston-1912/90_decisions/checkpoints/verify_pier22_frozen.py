"""Mechanically verify that the Pier 22 repair touched nothing it was not
authorised to touch.

The checkpoint records component -> sha256 with no paths, so the mapping is
resolved by SEARCH rather than by assumption: every candidate file in the
project (plus the archival scan) is hashed, and each frozen hash is looked up in
that index. A frozen hash that is still present somewhere proves that artefact
is byte-identical; a frozen hash with no match means the artefact changed, and
the resolved path table below names which one.

Exactly two components are permitted to differ: `compositor` (the tool carrying
the bounded D-014 override) and `current_master_full` (its output). Any other
component failing to match is a scope breach and exits non-zero.
"""

import hashlib
import json
import os
import sys

G = "/home/user/claude-code/galveston-1912"
SCAN = ("/home/user/g1912/data-branch/galveston_1912_sources/"
        "sanborn08539_004_img009_archival.jp2")
CK = f"{G}/90_decisions/checkpoints/1912_PRE_S5_PIER22_LOCAL_REPAIR_FROZEN.json"
ALLOWED_TO_CHANGE = {"compositor", "current_master_full"}


def sha256_file(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


# ---- build a hash index over everything the checkpoint could refer to -------
index = {}
for root, dirs, files in os.walk(G):
    dirs[:] = [d for d in dirs if d not in
               {".git", "__pycache__", "deliverables"}]
    for fn in files:
        if not fn.endswith((".json", ".py", ".tif")):
            continue
        p = os.path.join(root, fn)
        try:
            index.setdefault(sha256_file(p), []).append(os.path.relpath(p, G))
        except OSError:
            pass
if os.path.exists(SCAN):
    index.setdefault(sha256_file(SCAN), []).append(SCAN)

ck = json.load(open(CK))["immutable"]

rows = []
for name, val in ck.items():
    if isinstance(val, dict):
        for fn, h in val.items():
            rows.append((f"{name}/{fn}", h))
    else:
        rows.append((name, val))

bad, ok, changed = [], 0, []
print(f"{'component':<34} {'status':<11} resolved path")
for name, h in rows:
    top = name.split("/")[0]
    hit = index.get(h)
    if hit:
        ok += 1
        print(f"{name:<34} {'UNCHANGED':<11} {hit[0]}")
    else:
        changed.append(name)
        if top in ALLOWED_TO_CHANGE:
            print(f"{name:<34} {'CHANGED':<11} (authorised by D-014)")
        else:
            print(f"{name:<34} {'CHANGED':<11} <-- SCOPE BREACH")
            bad.append(name)

print(f"\n{len(rows)} frozen artefacts checked")
print(f"  byte-identical : {ok}")
print(f"  changed        : {len(changed)}  {changed}")
if bad:
    print(f"\nSCOPE BREACH: {bad}")
    sys.exit(1)
if set(changed) - ALLOWED_TO_CHANGE:
    print(f"\nunexpected change set: {changed}")
    sys.exit(1)
print("\nOK: every frozen transform, control, mask, cut, the block master and "
      "the archival scan are byte-identical. Only the compositor and its "
      "output changed, as authorised by D-014.")

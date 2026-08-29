#!/usr/bin/env python3
"""Fold the CI-fetched pct:50 working copies into the 1912 recipe inventory.

Reads galveston_1912_sources/pct50/FETCHED.tsv from the data branch
(name, url, sha256, bytes per file), verifies each git blob against its
recorded hash, and appends inventory entries with resolution metadata:
working copies are pct:50 IIIF renders; the full-resolution URL for
off-cloud fetches is derivable by replacing pct:50 with pct:100 (recorded
per entry as full_url).
"""
import json
import subprocess
import hashlib

BRANCH = "origin/claude/galveston-1912-source-data"
subprocess.run(["git", "fetch", "-q", "origin", "claude/galveston-1912-source-data"], check=True)
tsv = subprocess.run(["git", "show", f"{BRANCH}:galveston_1912_sources/pct50/FETCHED.tsv"],
                     capture_output=True, text=True)
if tsv.returncode != 0:
    raise SystemExit("FETCHED.tsv not on the data branch yet")
inv = json.load(open("outputs/1912/recipe/inventory.json"))
have = {i["file"] for i in inv["items"]}
added = verified = 0
for line in tsv.stdout.strip().splitlines():
    name, url, sha, size = line.split("\t")
    fname = f"pct50/{name}.jpg"
    if fname in have:
        continue
    blob = subprocess.run(["git", "show", f"{BRANCH}:galveston_1912_sources/{fname}"],
                          capture_output=True)
    if blob.returncode != 0:
        print("missing blob:", fname)
        continue
    got = hashlib.sha256(blob.stdout).hexdigest()
    if got != sha:
        print("HASH MISMATCH:", fname)
        continue
    verified += 1
    inv["items"].append({
        "file": fname,
        "kind": "working-copy-pct50",
        "resolution": "IIIF pct:50",
        "source_url": url,
        "full_url": url.replace("/pct:50/", "/pct:100/"),
        "sha256": sha,
        "bytes": int(size),
        "mirror": {"kind": "git", "repo": "sk89hdw8tz-design/claude-code",
                   "branch": "claude/galveston-1912-source-data",
                   "path": f"galveston_1912_sources/{fname}"},
    })
    added += 1
inv["count"] = len(inv["items"])
json.dump(inv, open("outputs/1912/recipe/inventory.json", "w"), indent=1)
print(f"added {added} entries ({verified} hash-verified); inventory now {inv['count']} items")

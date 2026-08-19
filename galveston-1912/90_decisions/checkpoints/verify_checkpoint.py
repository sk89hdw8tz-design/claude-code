"""Verify a frozen-state checkpoint that records component -> path -> sha256.

Unlike the original Pier 22 verifier, this resolves nothing by search: every
component names its own path, so a missing or moved artefact fails loudly
instead of silently matching nothing.

Usage: verify_checkpoint.py [checkpoint.json] [--allow name[,name...]]
"""
import hashlib
import json
import os
import sys

G = "/home/user/claude-code/galveston-1912"
DEFAULT = f"{G}/90_decisions/checkpoints/1912_POST_D018_FROZEN.json"


def sha256_file(p, chunk=1 << 22):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


args = [a for a in sys.argv[1:] if not a.startswith("--")]
allow = set()
for a in sys.argv[1:]:
    if a.startswith("--allow"):
        allow = set(a.split("=", 1)[1].split(",")) if "=" in a else allow
ck = json.load(open(args[0] if args else DEFAULT))
rows = []
for name, rec in ck["immutable"].items():
    entries = rec.items() if isinstance(rec, dict) and "sha256" not in rec else [(name, rec)]
    for sub, e in entries:
        p = e["path"] if os.path.isabs(e["path"]) else os.path.join(G, e["path"])
        label = name if sub == name else f"{name}/{sub}"
        if not os.path.exists(p):
            rows.append((label, "MISSING", e["path"]))
            continue
        rows.append((label, "UNCHANGED" if sha256_file(p) == e["sha256"] else "CHANGED",
                     e["path"]))

bad = []
print(f"checkpoint: {ck['checkpoint']}")
for label, status, path in rows:
    if status != "UNCHANGED":
        mark = "  (allowed)" if label.split("/")[0] in allow else "  <-- FAIL"
        if label.split("/")[0] not in allow:
            bad.append(label)
        print(f"  {label:<28} {status:<10} {path}{mark}")
ok = sum(1 for r in rows if r[1] == "UNCHANGED")
print(f"\n{len(rows)} artefacts checked: {ok} byte-identical, {len(rows)-ok} changed")
if bad:
    print(f"FAIL: {bad}")
    sys.exit(1)
print("OK: every frozen artefact is byte-identical (or explicitly allowed).")

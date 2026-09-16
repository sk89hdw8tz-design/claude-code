#!/usr/bin/env python3
"""Compare blind corridor readings with the lattice identification key."""
import json, glob, re, sys, os
sys.path.insert(0, "tools"); from reciplib import Recipe
key = json.load(open("outputs/1912/recipe/qc/corridor_check/_key.json"))
reads = {}
for f in sorted(glob.glob("rebuild_1899/out/corridor_reads/batch*.json")):
    reads.update(json.load(open(f)))
def norm_street(s):
    m = re.search(r"(\d+)", s); return int(m.group(1)) if m else None
def norm_ave(s):
    s = s.upper().replace("AVENUE", "").replace("AVE.", "").replace("AVE", "").strip()
    s = s.replace("OR", " ").replace("\"", "").split()
    # prefer the letter token if present ("D OR MARKET" -> D)
    for tok in s:
        if len(tok) == 1 and tok.isalpha():
            half = "1/2" in " ".join(s)
            return Recipe.avenue_slot(tok + (" 1/2" if half else ""))
    try: return Recipe.avenue_slot(" ".join(s))
    except Exception: return None
ok = bad = unread = 0; issues = []; per_unit = {}
for u, strips in key.items():
    r = reads.get("u" + u)
    if r is None: continue
    for st in strips:
        got = r.get(str(st["strip"]), "")
        if not got or "unread" in got.lower() or "not a corridor" in got.lower():
            unread += 1; issues.append((u, st["strip"], st["expected"], got)); continue
        idx = norm_street(got) if st["kind"] == "street" else norm_ave(got)
        if idx == st["index"]:
            ok += 1; per_unit.setdefault(u, [0, 0])[0] += 1
        else:
            bad += 1; per_unit.setdefault(u, [0, 0])[1] += 1; issues.append((u, st["strip"], st["expected"], got))
print(f"read units {len([u for u in key if 'u'+u in reads])}/{len(key)}; strips ok {ok} wrong {bad} unreadable/not-corridor {unread}")
for i in issues: print("  ", i)
json.dump({"ok": ok, "wrong": bad, "unreadable": unread, "issues": issues, "per_unit": per_unit},
          open("outputs/1912/recipe/qc/corridor_check/_verdict.json", "w"), indent=1)

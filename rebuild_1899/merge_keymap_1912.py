#!/usr/bin/env python3
"""Merge the four key-map quadrant transcriptions into coverage_1912.json.

Units = regular grid sheets; wharf/pier sheets with no street grid are
excluded with cause (same policy as 1899). Adjacency comes from the
transcribed keymap rectangles (edge-sharing within tolerance), boundary
street numbers from the span bounds. Registration runs at pct:50 working
scale; the frozen archival core is downscaled to match (recorded).
"""
import glob
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

recs = {}
for p in sorted(glob.glob(os.path.join(ROOT, "out", "keymap_1912_*.json"))):
    for r in json.load(open(p))["results"]:
        n = int(r["sheet"])
        if n not in recs:
            recs[n] = r
        else:
            # duplicate across quadrant boundary: keep the larger rect
            def area(q):
                x0, y0, x1, y1 = q.get("keymap_rect", [0, 0, 0, 0])
                return max(0, x1 - x0) * max(0, y1 - y0)
            if area(r) > area(recs[n]):
                recs[n] = r

EXCLUDE = {}
# wharf/pier sheets: rotated or gridless per the transcriptions; sheet 5's
# panels are already in the frozen core recipe (transforms_sheet5.json)
FORCE_EXCLUDE = {1: "SP Terminal, piers drawn rotated ~45deg, no street grid",
                 2: "wharf piers, no street grid",
                 3: "wharf shoreline strip, no regular grid",
                 4: "wharf flats, no street grid",
                 5: "two-panel wharf sheet; already solved in the core recipe",
                 6: "piers 10-15, no street grid"}
units = {}
for n, r in sorted(recs.items()):
    if n in FORCE_EXCLUDE:
        EXCLUDE[n] = FORCE_EXCLUDE[n]
        continue
    note = (r.get("note") or "").lower()
    sts = r.get("streets") or []
    if (not sts or len(sts) != 2) and any(k in note for k in
            ("no street grid", "pier", "wharf-only", "wharf flats", "rotated ~45")):
        EXCLUDE[n] = r.get("note", "no street grid")
        continue
    if not sts or len(sts) != 2:
        EXCLUDE[n] = f"no usable street span: {r.get('note','')[:80]}"
        continue
    import re
    def stnum(v):
        m = re.search(r"\d+", str(v))
        return int(m.group(0)) if m else None
    s0, s1 = stnum(sts[0]), stnum(sts[1])
    if s0 is None or s1 is None:
        EXCLUDE[n] = f"unparseable street span {sts}"
        continue
    units[str(n)] = {
        "file": n,
        "st": [s0, s1],
        "avenues": r.get("avenues") or [],
        "keymap_rect": r.get("keymap_rect"),
        "note": r.get("note", ""),
    }

# adjacency from keymap rects
def rect(u):
    return u.get("keymap_rect") or [0, 0, 0, 0]

pairs = []
uids = sorted(units, key=int)
TOL = 60
for i, a in enumerate(uids):
    ra = rect(units[a])
    for b in uids[i + 1:]:
        rb = rect(units[b])
        # horizontal adjacency (share a vertical edge on the keymap = avenue boundary)
        x_touch = (abs(ra[2] - rb[0]) < TOL or abs(rb[2] - ra[0]) < TOL)
        y_ov = min(ra[3], rb[3]) - max(ra[1], rb[1])
        y_touch = (abs(ra[3] - rb[1]) < TOL or abs(rb[3] - ra[1]) < TOL)
        x_ov = min(ra[2], rb[2]) - max(ra[0], rb[0])
        if x_touch and y_ov > 80:
            pairs.append({"owner": a, "nbr": b, "axis": "v",
                          "boundary": "shared avenue (keymap adjacency)"})
        elif y_touch and x_ov > 80:
            # boundary street = touching span bounds when they agree
            sa, sb = units[a]["st"], units[b]["st"]
            idx = sa[1] if sa[1] == sb[0] else (sb[1] if sb[1] == sa[0] else None)
            pairs.append({"owner": a, "nbr": b, "axis": "h", "idx": idx,
                          "boundary": f"street {idx}" if idx else "shared street (span bounds disagree)"})

deg = {}
for p in pairs:
    deg[p["owner"]] = deg.get(p["owner"], 0) + 1
    deg[p["nbr"]] = deg.get(p["nbr"], 0) + 1
iso = [u for u in units if deg.get(u, 0) == 0]

out = {"units": units, "pairs": pairs, "excluded": EXCLUDE,
       "note": "registration at IIIF pct:50 working scale; archival core downscaled x0.5 to match"}
json.dump(out, open(os.path.join(ROOT, "out", "coverage_1912.json"), "w"), indent=1)
print(f"units {len(units)}  excluded {len(EXCLUDE)} {sorted(EXCLUDE)}  "
      f"pairs {len(pairs)}  isolated {iso}")
lo = sorted((d, u) for u, d in deg.items())[:6]
print("lowest degree:", lo)
# validate against the frozen core's known adjacency
KNOWN = [("7","9"),("9","11"),("8","10"),("10","12"),("39","43"),("43","49"),
         ("40","44"),("44","50"),("7","8"),("9","10"),("11","12"),("8","39"),
         ("10","43"),("12","49"),("39","40"),("43","44"),("49","50")]
have = {(p["owner"], p["nbr"]) for p in pairs} | {(p["nbr"], p["owner"]) for p in pairs}
missing = [k for k in KNOWN if k not in have]
print("known core pairs missing:", missing)

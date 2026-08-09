"""Generate the 1899 coverage registry from the survey batches.

Reads build/1899/survey_batch_*.json (agent-surveyed street/avenue labels
per sheet) and emits sanborn/coverage_1899.json for coverage_prior to load.

Axis model: streets by ordinal (6..46); avenues by half-step index
(A=0, A half=1, B=2, ..., S=36) so half-avenues land between full ones and
the physical spacing per index step is uniform (~half a block).
"""
import glob
import json
import os
import re
import sys

EXCLUDED = {
    "01": "wharf sheet, no street grid (proposed warehouse outlines only)",
    "02": "wharf piers/warehouses, rotated axis, detached creosote inset",
    "03": "waterfront warehouses; streets marked not opened, no avenue line",
    "09": "rotated wharf grid with detached pier inset",
    "10": "wharf piers only, no street grid",
}


def street_ord(label):
    m = re.match(r"(\d+)(ST|ND|RD|TH)", label.replace(" ", "").upper())
    return int(m.group(1)) if m else None


def avenue_key(label):
    s = label.upper().replace("AVENUE", " ").replace("AV.", " ")
    s = s.replace("½", " 1/2").replace(".", " ")
    m = re.search(r"\b([A-S])\b(\s*1/2)?", s)
    if not m:
        return None
    return m.group(1) + ("+" if m.group(2) else "")


def av_index(key):
    return (ord(key[0]) - 65) * 2 + (1 if key.endswith("+") else 0)


def main(survey_dir, out_path):
    records = {}
    for f in sorted(glob.glob(os.path.join(survey_dir, "survey_batch_*.json"))):
        for r in json.load(open(f)):
            records[r["sheet"]] = r

    units = {}
    for sid, r in sorted(records.items()):
        if sid in EXCLUDED:
            continue
        sts = sorted({street_ord(s) for s in r["streets"]} - {None})
        av_keys = [avenue_key(a) for a in r["avenues"]]
        av_idx = [av_index(a) for a in av_keys if a]
        if sid == "71":
            # two side-by-side panels: left 43rd-46th x J-K, right 24th-27th x M-N
            units["71a"] = {"file": 71,
                            "av_idx": list(range(18, 21)), "st": [43, 46],
                            "region": [60, 30, 1150, 4040],
                            "note": "left panel"}
            units["71b"] = {"file": 71,
                            "av_idx": list(range(24, 27)), "st": [24, 27],
                            "region": [1190, 30, 3400, 4040],
                            "note": "right panel"}
            continue
        if not sts or not av_idx or len(sts) < 2 or len(av_idx) < 1:
            EXCLUDED[sid] = f"insufficient grid ({len(sts)} streets, {len(av_idx)} avenues)"
            continue
        if sts != list(range(sts[0], sts[-1] + 1)):
            print(f"WARN sheet {sid}: streets not contiguous {sts}; using span")
            sts = list(range(sts[0], sts[-1] + 1))
        # CONTIGUOUS half-index range: every 605px comb slot is an identity;
        # unnamed slots are the mid-block alleys the south names as
        # half-avenues, and they are genuine detectable corridors
        lo, hi = min(av_idx), max(av_idx)
        units[sid] = {"file": int(sid), "av_idx": list(range(lo, hi + 1)),
                      "st": [sts[0], sts[-1]], "region": None,
                      "note": (r.get("note") or "")[:60]}
        if r.get("irregular"):
            units[sid]["note"] = "IRREGULAR: " + units[sid]["note"]

    out = {"units": units, "excluded": EXCLUDED}
    json.dump(out, open(out_path, "w"), indent=1)
    print(f"{len(units)} units, {len(EXCLUDED)} excluded -> {out_path}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

"""Generate the 1899 coverage registry from the survey batches.

Reads build/1899/survey_batch_*.json (agent-surveyed street/avenue labels
per sheet) and emits sanborn/coverage_1899.json for coverage_prior to load.

Axis model (verified by autocorrelation over 62 sheets + the 1kb index map):
the physical avenue grid is UNIFORM at ~1006 px full pitch citywide. Naming
changes district: north of Avenue M corridors are lettered A..M (half-letter
alleys are narrow mid-block splits, never comb-detected); south of M — the
outlot district, whose quarter-opening streets the index map documents —
EVERY consecutive corridor gets a name (M 1/2, N, N 1/2 ...). So the global
axis is SLOTS: slot = av_index/2 for av_index <= 24 (A=0 .. M=12),
slot = av_index - 12 for av_index >= 24 (M 1/2=13, N=14 ... S=24).
Streets by ordinal (6..49) at 1169 px pitch.
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
    "94": "detached Texas City inset (7 miles NW of Galveston) — "
          "not part of the Galveston grid",
}

# Survey-label corrections, each verified by targeted crop inspection.
# {sheet: {wrong_av_index: right_av_index}}
LABEL_FIXES = {
    # Sheet 32's east-edge corridor is printed AVENUE N 1/2, but it sits one
    # uniform pitch past M 1/2 and its edge numeral adjoins sheet 83, whose
    # west corridor is AVENUE N — same physical corridor, inconsistent
    # Sanborn naming. Registered as N (slot 14); disclosed in the report.
    "32": {27: 26},
}


def street_ord(label):
    m = re.match(r"(\d+)(ST|ND|RD|TH)", label.replace(" ", "").upper())
    return int(m.group(1)) if m else None


def avenue_key(label):
    s = label.upper().replace("AVENUE", " ").replace("AV.", " ")
    s = s.replace("½", " 1/2").replace(".", " ")
    m = re.search(r"\b([A-T])\b(\s*1/2)?", s)
    if not m:
        return None
    return m.group(1) + ("+" if m.group(2) else "")


def av_index(key):
    return (ord(key[0]) - 65) * 2 + (1 if key.endswith("+") else 0)


def av_slot(idx):
    """Uniform-pitch corridor slot for a half-step avenue index."""
    if idx <= 24:
        if idx % 2:
            return None  # townsite half-letter: narrow alley, not a corridor
        return idx // 2
    return idx - 12


def main(survey_dir, out_path):
    records = {}
    for f in sorted(glob.glob(os.path.join(survey_dir, "survey_batch_*.json"))):
        if "supplement" in f:
            continue
        for r in json.load(open(f)):
            records[r["sheet"]] = r

    units = {}
    for sid, r in sorted(records.items()):
        if sid in EXCLUDED:
            continue
        sts = sorted({street_ord(s) for s in r["streets"]} - {None})
        av_keys = [avenue_key(a) for a in r["avenues"]]
        idxs = [av_index(a) for a in av_keys if a]
        idxs = [LABEL_FIXES.get(sid, {}).get(i, i) for i in idxs]
        slots = sorted({s for s in (av_slot(i) for i in idxs) if s is not None})
        if sid == "26":
            # Broadway's diagonal offsets the east grid: main panel H..K,
            # heavy-bordered sub-panel redraws 39th-40th x K..L (cemetery)
            units["26"] = {"file": 26, "av_slots": [7, 8, 9, 10],
                           "st": [39, 42],
                           "region": [40, 60, 2260, 4094],
                           "clip_region": [40, 60, 2210, 4094],
                           "note": "main panel west of the K break"}
            units["26b"] = {"file": 26, "av_slots": [10, 11], "st": [39, 40],
                            "region": [2160, 1500, 3400, 4094],
                            "clip_region": [2210, 1500, 3400, 4094],
                            "note": "cemetery sub-panel K-L x 39-40"}
            continue
        if sid == "71":
            # two side-by-side panels: left 43rd-46th x J-K, right 24th-27th
            # x M-N (M, M 1/2, N = slots 12-14)
            units["71a"] = {"file": 71,
                            "av_slots": [9, 10], "st": [43, 46],
                            "region": [60, 30, 1150, 4040],
                            "note": "left panel"}
            units["71b"] = {"file": 71,
                            "av_slots": [12, 13, 14], "st": [24, 27],
                            "region": [1190, 30, 3400, 4040],
                            # comb locks onto bright vacant-lot gaps here and
                            # the region insets clip M and N; corridor centers
                            # measured by CoM on the whiteness profile
                            "v_anchors": {"12": 1214, "13": 2238, "14": 3264},
                            "note": "right panel"}
            continue
        if sid in ("04", "05", "06", "07", "08"):
            # wharf hybrids: bay piers fill the sheet's left; the only named
            # avenue corridor is Av. A at the right edge. Detect within the
            # right strip so the comb can't lock onto pier/track corridors;
            # composite clipping stays full-sheet (piers are exterior-margin
            # content north of Avenue A, like 1885's bay water).
            # Av. A corridor positions verified by the label-reading fleet
            # (comb + nearest-center picked the terminal-track corridor
            # ~700 px west) and CoM-refined on the whiteness profile
            # Avenue A anchors, label-verified, then refined by matching the
            # wharf terminal TRACKS across each shared street: sheet 06 by
            # (-6,-5) and sheet 08 by (-28,-4) onto sheet 07, which stays
            # fixed as the pair's reference. The tracks are the dominant
            # feature crossing these seams, so they are what alignment is
            # judged on.
            av_a = {"04": 3136, "05": 3094, "06": 3093,
                    "07": 3127, "08": 3147}[sid]
            # Street anchors: on these sheets the streets survive only in the
            # narrow strip beside Avenue A, half-buried in the wharf terminal
            # yards, and the comb latches onto a block FRONTAGE line instead
            # of the corridor centre — on sheet 06 by a uniform +114 px on
            # every line, which a per-sheet translation absorbs, so the
            # consensus residuals stayed under 15 px while the sheet's
            # CONTENT sat 114 px out. It printed 22nd St, its 10" water main
            # and its T.H. hydrant a second time, 132 px below sheet 07's.
            # Centres here are measured as the midpoint of the two block
            # frontage lines bounding each corridor, the same 245 px
            # corridor verified on downtown sheet 13 (1312/1557, centre
            # 1434.5 vs its detected 1438).
            st_anchor = {
                "06": {"22": 176, "23": 1343, "24": 2511, "25": 3678},
                "07": {"19": 201, "20": 1368, "21": 2534, "22": 3700},
                "08": {"16": 289, "17": 1457, "18": 2626, "19": 3795},
            }.get(sid)
            units[sid] = {"file": int(sid), "av_slots": [0],
                          "st": [sts[0], sts[-1]], "region": None,
                          "detect_region": [2350, 0, 3400, 4095],
                          "v_anchors": {"0": av_a},
                          "note": "wharf hybrid; Av.A + street anchors "
                                  "measured; piers render as exterior margin"}
            if st_anchor:
                units[sid]["h_anchors"] = st_anchor
            continue
        if sid == "70":
            # beach sheet: grid only in the SW quadrant (Q 1/2-R x 23-24);
            # bath-house piers over the Gulf + detached orphanage inset.
            units["70"] = {"file": 70, "av_slots": [21, 22], "st": [23, 24],
                           "region": None,
                           "detect_region": [0, 2100, 1600, 4110],
                           # bright Gulf water inside the detect region pulls
                           # the comb ~300 px east / ~190 px south of the
                           # printed corridors; CoM-measured, label-verified
                           # (spacings 1005 / 1162 match the edition pitches)
                           "v_anchors": {"21": 155, "22": 1160},
                           "h_anchors": {"23": 2599, "24": 3761},
                           # clip excludes the DETACHED St. Mary's orphans-
                           # home inset (top band, frame ends ~y1010); the
                           # sacrificed sliver left of it is open Gulf water
                           "clip_region": [0, 1015, 3400, 4110],
                           "note": "beach sheet; grid in SW quadrant; "
                                   "detached orphans-home inset excluded"}
            continue
        if not sts or len(sts) < 2 or len(slots) < 2:
            EXCLUDED[sid] = (f"insufficient grid ({len(sts)} streets, "
                             f"{len(slots)} avenue corridors)")
            continue
        if sts != list(range(sts[0], sts[-1] + 1)):
            print(f"WARN sheet {sid}: streets not contiguous {sts}; using span")
            sts = list(range(sts[0], sts[-1] + 1))
        if slots != list(range(slots[0], slots[-1] + 1)):
            print(f"WARN sheet {sid}: avenue slots not contiguous {slots} "
                  f"(labels {sorted(idxs)}) — survey label suspect")
        units[sid] = {"file": int(sid), "av_slots": slots,
                      "st": [sts[0], sts[-1]], "region": None,
                      "note": (r.get("note") or "")[:60]}
        if r.get("irregular"):
            units[sid]["note"] = "IRREGULAR: " + units[sid]["note"]

    out = {"units": units, "excluded": EXCLUDED}
    json.dump(out, open(out_path, "w"), indent=1)
    print(f"{len(units)} units, {len(EXCLUDED)} excluded -> {out_path}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

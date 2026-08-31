#!/usr/bin/env python3
"""Check accepted controls against evidence they were not fitted to.

    python3 tools/ctlcheck.py --year 1912

Two independent tests, both from the printed record rather than from the
solve:

FRAMING. A key map's rectangle says where on the island that plate sits. Two
sheets framed one avenue column apart have rectangles offset by one column,
and their shared corridor must then sit about one avenue block apart in native
pixels. So the key-map offset predicts the control's native difference, and a
control that took the same corridor on one sheet and its neighbour on the
other disagrees with that prediction by a whole block. This is the trap that
caught 75|83, 82|90, 85|94, 86|94, 61|68, 87|95 and 88|96 -- there it was
caught by hand, and here it is checked mechanically.

WIDTH. Observers converged on a clean separator: an avenue measures 206-214
native px between its block faces (the printed 70 ft at the plates' 2.97
px/ft), a mid-block alley about 60 px (20 ft). Every candidate the corridor
detector proposed was an alley or a lot line. Controls that report a
detector candidate verbatim are therefore suspect, and this counts them.
"""
import argparse
import glob
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe                        # noqa: E402
from paircrops import keymap                       # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AVENUE_PITCH_PX = 1000.0     # native px between full avenues, measured
TOL_BLOCKS = 0.45            # how far off a whole-block count may drift


def ground_index(slot):
    """Slots in units of one avenue pitch.

    This used to halve every slot south of Avenue M, on the assumption that a
    "1/2" avenue sits half a block from its neighbour. The plates say
    otherwise, in three independent places: on sheet 57 Ave M reads 1191.7 and
    Ave M 1/2 reads 2199.8, 1008 px apart; on sheet 90 Ave S 1/2 and Ave T are
    998 px apart; on sheet 96 Ave P 1/2 and Ave Q are 987 px apart. Every one
    is a full lattice step, the same ~1000 px that separates Ave C from Ave D
    downtown. South of Broadway the outlot district simply names every
    corridor it has, and the halves are naming, not spacing.
    """
    return slot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1912", "1899"])
    a = ap.parse_args()

    r = Recipe(int(a.year))
    km = keymap(a.year, warn=False)
    det = json.load(open(os.path.join(r.dir, "corridors.json")))

    # Key-map rectangles are in key-map pixels, and a rectangle spans several
    # avenue columns, so the conversion to columns has to be calibrated rather
    # than assumed. Calibrate it against the controls' own whole-block counts:
    # a control's native difference divided by the avenue pitch rounds to the
    # number of columns the two plates are framed apart, and that integer is
    # what the key-map offset has to reproduce.
    rects = {u: e["keymap_rect"] for u, e in km.items() if e.get("keymap_rect")}

    def kmdx(ua, ub):
        if ua not in rects or ub not in rects:
            return None
        # anchor on the WEST edge, not the centre. The rectangles are drawn
        # by hand and their widths vary -- sheet 47's is 590 px against ~365
        # for sheets 26 and 53 covering the same avenues -- so a centre offset
        # invents a shift of half that difference. All three share x=3400 on
        # the left, which is the edge that actually means something.
        return rects[ub][0] - rects[ua][0]

    def west_slot(u):
        av = (km.get(u) or {}).get("avenues") or []
        try:
            return min(Recipe.avenue_slot(str(v)) for v in av)
        except Exception:
            return None

    def r_av(u):
        av = (km.get(u) or {}).get("avenues") or []
        return "/".join(str(v) for v in av) or "?"

    def accepted():
        for fn in sorted(glob.glob(os.path.join(r.dir, "controls",
                                                "pair_*_x.json"))):
            d = json.load(open(fn))
            if str(d.get("status", "")).upper() != "ACCEPTED":
                continue
            m = re.match(r"pair_([0-9]+[a-z]?)_([0-9]+[a-z]?)_x\.json$",
                         os.path.basename(fn))
            if not m:
                continue
            try:
                yield (m.group(1), m.group(2), float(d["a_native"]),
                       float(d["b_native"]), d.get("corridor", "?"))
            except Exception:
                continue

    cal = []
    for ua, ub, an, bn, _c in accepted():
        dx = kmdx(ua, ub)
        blocks = round((bn - an) / AVENUE_PITCH_PX)
        if dx is not None and blocks:
            cal.append(dx / -blocks)
    if not cal:
        print("no calibration pairs")
        return 1
    col_px = float(np.median(cal))
    print(f"key-map scale calibrated from {len(cal)} framed pairs: "
          f"{col_px:.1f} key-map px per avenue column "
          f"(spread {np.percentile(cal,10):.1f}-{np.percentile(cal,90):.1f})\n")

    rows, flagged = [], []
    for fn in sorted(glob.glob(os.path.join(r.dir, "controls", "pair_*_x.json"))):
        d = json.load(open(fn))
        if str(d.get("status", "")).upper() != "ACCEPTED":
            continue
        m = re.match(r"pair_([0-9]+[a-z]?)_([0-9]+[a-z]?)_x\.json$",
                     os.path.basename(fn))
        if not m:
            continue
        ua, ub = m.group(1), m.group(2)
        try:
            an, bn = float(d["a_native"]), float(d["b_native"])
        except Exception:
            continue
        note = []
        # WIDTH: did the control just echo a detector candidate?
        for u, v in ((ua, an), (ub, bn)):
            if u in det and any(abs(float(c) - v) < 3.0 for c in det[u]["cols"]):
                note.append(f"{u} matches a detector candidate")
        # FRAMING: key-map columns predict the native block offset
        # FRAMING from the key maps' avenue LISTS. Where each plate's
        # westernmost named avenue sits on the island is known outright, so
        # the shift between two plates is a difference of two integers rather
        # than a measurement off a hand-drawn rectangle -- and it is correct
        # south of Avenue M, where a named column is half a block.
        wa, wb = west_slot(ua), west_slot(ub)
        if wa is not None and wb is not None:
            pred = ground_index(wb) - ground_index(wa)
            got = (bn - an) / AVENUE_PITCH_PX
            err = got + pred
            if abs(err) > TOL_BLOCKS:
                note.append(f"key-map avenues predict {-pred:+.2f} blocks "
                            f"({r_av(ua)} vs {r_av(ub)}), control gives "
                            f"{got:+.2f} ({err:+.2f} off)")
        rows.append((f"{ua}|{ub}", d.get("corridor", "?"), an, bn, note))
        if note:
            flagged.append(rows[-1])

    print(f"{len(rows)} accepted avenue controls checked; "
          f"{len(flagged)} flagged\n")
    for pair, corr, an, bn, note in flagged:
        print(f"  {pair:<9} {str(corr)[:20]:<22} a={an:7.1f} b={bn:7.1f}")
        for n in note:
            print(f"      - {n}")
    if not flagged:
        print("  none")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Modern Galveston address -> block, sheet, and pixel bounds on a year's mosaic.

    python3 tools/lookup.py --year 1899 --address "2314 Strand St, Galveston, TX"
    python3 tools/lookup.py --year 1912 --address "2314 Strand" --preview out.png

Galveston's grid is regular: numbered streets run one way, lettered avenues
(with names downtown: A=Water, B=Strand, C=Mechanic, D=Market, E=Postoffice,
F=Church, G=Winnie, H=Ball, I=Sealy, J=Broadway) the other. On an avenue the
hundred-block IS the lower cross street, so 2314 Strand sits between 23rd and
24th. That gives the block without geocoding.

Per the brief, an address that cannot be placed with confidence returns the
block and says so rather than guessing a lot.
"""
import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe, px_per_ft   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

ORDINAL = re.compile(r"^(\d+)\s*(?:st|nd|rd|th)$", re.I)


def parse_address(addr):
    """(house_number, street_token, on_numbered_street) from a free-form address."""
    s = addr.split(",")[0].strip()
    m = re.match(r"^\s*(\d{2,5})\s+(.*)$", s)
    if not m:
        raise ValueError(
            f"cannot read a house number from {addr!r} "
            "(expected something like '2314 Strand St')")
    house, rest = int(m.group(1)), m.group(2).strip()
    # drop a trailing street-type word; keep 'Ave M 1/2' style intact
    rest = re.sub(r"\b(street|st|avenue|ave|av|road|rd|blvd|boulevard)\.?\s*$",
                  "", rest, flags=re.I).strip()
    on_numbered = bool(ORDINAL.match(rest)) or rest.isdigit()
    return house, rest, on_numbered


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, required=True, choices=(1899, 1912))
    ap.add_argument("--address", required=True)
    ap.add_argument("--preview", nargs="?", const="auto", default=None,
                    help="also render a preview PNG of the block")
    a = ap.parse_args()

    try:
        house, name, on_numbered = parse_address(a.address)
    except ValueError as e:
        sys.exit(f"error: {e}")

    r = Recipe(a.year)
    if r.grid is None:
        sys.exit(f"error: the {a.year} recipe has no corridor grid")

    hundred = house // 100
    confident = True
    notes = []

    if on_numbered:
        # on a numbered street the hundred-block indexes the avenue, a mapping
        # that has shifted over the years -- report the block, not a lot
        street_lo = int(ORDINAL.match(name).group(1) if ORDINAL.match(name)
                        else name)
        street_hi = street_lo
        slot_lo, slot_hi = hundred - 1, hundred
        confident = False
        notes.append(
            "address is on a numbered street: the avenue is inferred from the "
            "hundred-block, a mapping that has shifted since 1912 -- treat the "
            "avenue as approximate")
    else:
        try:
            slot_lo = Recipe.avenue_slot(name)
        except ValueError as e:
            sys.exit(f"error: {e}")
        slot_hi = slot_lo
        street_lo, street_hi = hundred, hundred + 1

    streets, avenues = r.grid["streets"], r.grid["avenues"]

    def corridor(table, key, what):
        e = table.get(str(key))
        if e is None:
            have = sorted(int(k) for k in table)
            sys.exit(f"error: {what} {key} is outside the {a.year} grid index "
                     f"(indexed: {have[0]}-{have[-1]})")
        return e

    from shapely.geometry import Point, Polygon
    own = [(u, Polygon(p)) for u, p in r.ownership()]

    def owner_of(x, y):
        pt = Point(x, y)
        return [u for u, poly in own if poly.contains(pt)]

    ppf = px_per_ft(r)

    if on_numbered:
        # frontage runs along the street; the two bounding avenues are inferred
        y_front = corridor(streets, street_lo, "street")["y"]
        x_lo = corridor(avenues, slot_lo, "avenue")["x"]
        x_hi = corridor(avenues, slot_hi, "avenue")["x"]
        cx, cy = (x_lo + x_hi) / 2.0, y_front
        block_desc = (f"{street_lo} St between avenue slots "
                      f"{slot_lo} and {slot_hi}")
        spans = [("block", min(x_lo, x_hi), max(x_lo, x_hi), y_front, y_front)]
    else:
        # frontage is the mid-block point on the named avenue; the lot lies in
        # one of the two blocks flanking it -- the house number alone does not
        # say which side, so report both
        y_lo = corridor(streets, street_lo, "street")["y"]
        y_hi = corridor(streets, street_lo + 1, "street")["y"]
        x_front = corridor(avenues, slot_lo, "avenue")["x"]
        cx, cy = x_front, (y_lo + y_hi) / 2.0
        block_desc = (f"{name.title()} frontage between {street_lo} and "
                      f"{street_lo + 1} (avenue slot {slot_lo})")
        spans = []
        for adj, label in ((slot_lo - 1, "side A"), (slot_lo + 1, "side B")):
            e = avenues.get(str(adj))
            if e is not None:
                spans.append((label, min(x_front, e["x"]),
                              max(x_front, e["x"]), y_lo, y_hi))
        notes.append("the house number does not say which side of the avenue "
                     "the lot is on; both flanking blocks are listed")

    owners = owner_of(cx, cy)

    print(f"address     : {a.address}")
    print(f"year        : {a.year}")
    print(f"block       : {block_desc}")
    print(f"mosaic point: ({cx:.0f}, {cy:.0f}) px  [frontage]")
    for label, bx0, bx1, by0, by1 in spans:
        sheets = sorted(set(owner_of((bx0 + bx1) / 2.0, (by0 + by1) / 2.0)))
        print(f"{label:<12}: x {bx0:.0f}..{bx1:.0f}  y {by0:.0f}..{by1:.0f} px "
              f"({(bx1 - bx0) / ppf:.0f} x {(by1 - by0) / ppf:.0f} ft)"
              + (f"  sheet {', '.join(sheets)}" if sheets else ""))
    print(f"sheet       : {', '.join(owners) if owners else 'none -- point is outside the mosaic'}")
    print(f"confidence  : {'block-level, grid-indexed' if confident else 'LOW -- see note'}")
    print("lat/lng     : not available -- the mosaic frame is not georeferenced "
          "yet (no EPSG:3857 solve in the recipe); use the mosaic point above")
    for n in notes:
        print(f"note        : {n}")

    if not owners:
        return 1

    if a.preview:
        out = (a.preview if a.preview != "auto"
               else f"lookup_{a.year}_{house}_{re.sub(r'[^A-Za-z0-9]', '', name)}.png")
        cmd = [sys.executable, os.path.join(HERE, "crop.py"),
               "--year", str(a.year), "--cx", f"{cx:.2f}", "--cy", f"{cy:.2f}",
               "--width-in", "4", "--height-in", "4", "--dpi", "150",
               "--out", out]
        print("preview     :", " ".join(cmd))
        rc = subprocess.run(cmd).returncode
        if rc != 0:
            print("preview failed (see crop.py output above)")
            return rc
        print("preview     :", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

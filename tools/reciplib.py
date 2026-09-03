#!/usr/bin/env python3
"""Shared recipe access for render.py / crop.py.

A "recipe" is outputs/{year}/recipe/: inventory (URL + sha256 + git mirror
per source file), per-sheet transforms into the year's mosaic frame, per-
sheet ownership polygons, and the corridor grid for address lookup.

Sheets are fetched lazily into work/sheets/{year}/ keyed by sha256: the git
mirror branch first (works offline once the repo is cloned), the recorded
source URL second. Every byte is verified against the inventory hash.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Recipe:
    def __init__(self, year):
        self.year = int(year)
        self.dir = os.path.join(REPO, "outputs", str(year), "recipe")
        self.inv = json.load(open(os.path.join(self.dir, "inventory.json")))
        self.items_by_file = {i["file"]: i for i in self.inv["items"]}
        tpath = os.path.join(self.dir, "transforms.json")
        self.transforms = json.load(open(tpath)) if os.path.exists(tpath) else None
        # city-wide superset (all units incl. outer sheets); the gated core
        # keeps identical values, so preferring this only adds coverage
        cpath = os.path.join(self.dir, "transforms_city.json")
        self.city = json.load(open(cpath)) if os.path.exists(cpath) else None
        upath = os.path.join(self.dir, "units.json")
        self.units = json.load(open(upath))["units"] if os.path.exists(upath) else {}
        if self.city:
            self.transforms = self.city
        gpath = os.path.join(self.dir, "grid.json")
        self.grid = json.load(open(gpath)) if os.path.exists(gpath) else None
        mpath = os.path.join(self.dir, "seams", "masks.json")
        self.masks = json.load(open(mpath)) if os.path.exists(mpath) else None
        opath = os.path.join(self.dir, "seams", "ownership_city.json")
        self.own_city = json.load(open(opath)) if os.path.exists(opath) else None
        if self.own_city:
            self.masks = self.own_city
        # unit -> hash-pinned source for the working images the city
        # transforms were solved against (1912; see working_sources.json)
        wpath = os.path.join(self.dir, "working_sources.json")
        self.working = json.load(open(wpath)) if os.path.exists(wpath) else None
        self.cache = os.path.join(REPO, "work", "sheets", str(year))
        os.makedirs(self.cache, exist_ok=True)

    # ---------------- working images ----------------
    def materialize(self, unit, path):
        """Rebuild a working image from its hash-pinned source.

        The 1912 city transforms were solved at pct:50 scale: the 13 archival
        core sheets halved, every other sheet's pct50 scan as-is. Rebuilding
        keeps a clean clone renderable without the scratch dir.
        """
        spec = (self.working or {}).get("units", {}).get(str(unit))
        if spec is None:
            raise RuntimeError(
                f"no working-source mapping for unit {unit}; cannot rebuild "
                f"{path} (expected outputs/{self.year}/recipe/working_sources.json)")
        src = self.fetch(spec["file"])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if spec["op"] == "copy":
            shutil.copyfile(src, path)
            return path
        if spec["op"] == "full":
            # the wharf plate (sheet 5) is drawn at 100 ft/in, half the
            # other plates' scale, so its archival scan is used unreduced
            from PIL import Image
            Image.MAX_IMAGE_PIXELS = None
            with Image.open(src) as im:
                im.convert("RGB").save(path, quality=92)
            return path
        if spec["op"] != "half":
            raise RuntimeError(f"unknown working-source op {spec['op']!r}")
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        with Image.open(src) as im:
            im = im.convert("RGB")
            # BOX over an exact factor of 2 == the area-average the solve used
            im.resize((im.width // 2, im.height // 2), Image.BOX).save(
                path, quality=92)
        return path

    # ---------------- fetching ----------------
    def fetch(self, file):
        """Return a local path to the named source file, hash-verified."""
        if file.startswith("LOCAL:"):
            path = os.path.join(REPO, file[6:])
            if not os.path.exists(path):
                # scratch working copy absent (fresh clone): rebuild it from
                # the hash-pinned source recorded in working_sources.json
                unit = os.path.splitext(os.path.basename(path))[0].lstrip("u")
                self.materialize(unit, path)
            return path
        it = self.items_by_file[file]
        dst = os.path.join(self.cache, it["sha256"] + os.path.splitext(file)[1])
        if os.path.exists(dst):
            return dst
        data = None
        mir = it.get("mirror")
        if mir and mir.get("kind") == "git":
            r = subprocess.run(["git", "-C", REPO, "show",
                                f"origin/{mir['branch']}:{mir['path']}"],
                               capture_output=True)
            if r.returncode != 0:
                subprocess.run(["git", "-C", REPO, "fetch", "-q", "origin",
                                mir["branch"]], check=False)
                r = subprocess.run(["git", "-C", REPO, "show",
                                    f"origin/{mir['branch']}:{mir['path']}"],
                                   capture_output=True)
            if r.returncode == 0:
                data = r.stdout
        if data is None and it.get("source_url"):
            import urllib.request
            req = urllib.request.Request(it["source_url"],
                                         headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=120).read()
        if data is None:
            raise RuntimeError(f"cannot fetch {file}: git mirror and URL both failed")
        got = hashlib.sha256(data).hexdigest()
        if got != it["sha256"]:
            raise RuntimeError(f"hash mismatch for {file}: {got} != {it['sha256']}")
        with open(dst, "wb") as f:
            f.write(data)
        return dst

    def source_bytes(self, sheet):
        """Download size of a unit's source, for disk estimates."""
        f = self.sheet_file(sheet)
        if f.startswith("LOCAL:"):
            spec = (self.working or {}).get("units", {}).get(str(sheet))
            return spec["bytes"] if spec else 0
        return self.items_by_file[f]["bytes"]

    # ---------------- geometry ----------------
    def sheet_matrix(self, sheet):
        """(M, t): p_mosaic = M @ p_native + t, from the recipe transforms.

        A detached inset panel (units.json `panel_of` + `shift_native`) is
        drawn on its parent plate at the parent's scale and orientation, so
        its transform is the parent's with the native shift folded in:
        p_mosaic = M_parent @ (p_native + shift) + t_parent. Deriving it here
        keeps a panel attached to its plate through any later re-solve.
        """
        u = self.units.get(str(sheet)) or {}
        if str(sheet) not in self.transforms["sheets"] and u.get("panel_of"):
            M, t = self.sheet_matrix(u["panel_of"])
            return M, t + M @ np.array(u["shift_native"], float)
        s = self.transforms["sheets"][str(sheet)]
        if "raw" in s:                       # 1912 convention
            r = s["raw"]
            return (np.array([[r["a"], -r["b"]], [r["b"], r["a"]]]),
                    np.array([r["tx"], r["ty"]]))
        if "m" in s:                         # 1899 affine convention
            return np.array(s["m"], float), np.array(s["t"], float)
        raise ValueError(f"unknown transform format for sheet {sheet}")

    def footprint_native(self, unit, furniture=True):
        """Shapely polygon of the ground a unit's scan actually maps, in its
        own pixels: the neatline-trimmed extent, minus any `exclude_native`
        polygons (a parent plate's inset frame), or the `region_native`
        polygon for a panel unit. With `furniture` the `furniture_native`
        boxes (plate number and title, stray edge numerals) are cut out too
        -- of a panel as well, since a panel shares its parent's scan -- so
        the seams can hand that ground to a neighbour that maps it. The
        renderer's last-resort fallback asks with furniture=False: where no
        plate maps the ground under a title, the title stays on its own
        paper rather than leaving a white hole."""
        from shapely.geometry import Polygon, box
        u = self.units[str(unit)]
        if u.get("region_native"):
            g = Polygon(u["region_native"]).buffer(0)
        else:
            e = u["extent"]
            g = box(e[0], e[1], e[2], e[3])
        for ex in u.get("exclude_native") or []:
            g = g.difference(Polygon(ex).buffer(0))
        if furniture:
            src = u
            if u.get("panel_of"):
                src = self.units[str(u["panel_of"])]
            for f in src.get("furniture_native") or []:
                if f.get("cut") is False:     # no neighbour maps the whole box
                    continue
                b = f["box"]
                g = g.difference(box(b[0] - 6, b[1] - 6, b[2] + 6, b[3] + 6))
        if g.geom_type != "Polygon":
            g = max(g.geoms, key=lambda p: p.area)
        return g

    def footprint(self, unit, furniture=True):
        """footprint_native mapped into the mosaic frame."""
        from shapely.affinity import affine_transform
        M, t = self.sheet_matrix(unit)
        return affine_transform(self.footprint_native(unit, furniture),
                                [M[0, 0], M[0, 1], M[1, 0], M[1, 1], t[0], t[1]])

    def ownership(self):
        """[(unit, exterior_polygon_mosaic np.ndarray)]"""
        out = []
        for r in self.masks["regions"]:
            uid = str(r.get("unit", r.get("sheet")))
            out.append((uid, np.array(r["polygon_mosaic"]["exterior"], float)))
        return out

    def interior_unowned(self):
        """Polygons of ground no region claims that lies INSIDE the mosaic:
        the holes of the union of all ownership regions.

        The renderer's fallback paints only here. Ground no region claims on
        the OUTER boundary is where the map ends -- a plate's blank margin,
        or the paper under a title box that no neighbour maps -- and painting
        it would put plate furniture at the edge of the finished map. Inside
        the city a hole is worse than the plate's own paper, so there the
        fallback still fills it from a covering plate's scan."""
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        if getattr(self, "_interior_unowned", None) is None:
            u = unary_union([Polygon(p).buffer(0) for _, p in self.ownership()])
            geoms = [u] if u.geom_type == "Polygon" else list(u.geoms)
            self._interior_unowned = [Polygon(r) for g in geoms for r in g.interiors]
        return self._interior_unowned

    def sheet_file(self, sheet):
        """Inventory file name for a unit's source scan."""
        u = self.units.get(str(sheet))
        if u:
            if self.year == 1912 and u.get("source_image"):
                return ("LOCAL:" + u["source_image"])   # working copy on disk
            return f"Galveston_1899_sheet_{int(u['file']):02d}.jpg"
        if self.year == 1912:
            m = {"7": 11, "8": 13, "9": 15, "10": 17, "11": 19, "12": 21,
                 "39": 49, "40": 50, "43": 53, "44": 54, "49": 59, "50": 60,
                 "5": 9, "13": 23}
            return f"sanborn08539_004_img{m[str(sheet)]:03d}_archival.jp2"
        return f"Galveston_1899_sheet_{int(sheet):02d}.jpg"

    # ---------------- address lookup ----------------
    @staticmethod
    def avenue_slot(avenue):
        """Slot for an avenue given as a slot int, a letter (optionally with
        1/2), or a name. A..M are slots 0..12; south of Avenue M the outlot
        district names every corridor, so M1/2=13, N=14, N1/2=15 ... T1/2=27.
        """
        if isinstance(avenue, int):
            return avenue
        s = str(avenue).strip().lower()
        # strip a leading Ave/Av./Avenue token wherever it appears; the old
        # code only stripped "avenue" and "av.", so "Ave M 1/2" -- the form the
        # controls actually use -- fell through to the letter tests as "a" and
        # raised.
        s = re.sub(r"\bave?(?:nue)?\.?", " ", s)
        # key maps letter some corridors both ways: 'STRAND OR. AVENUE "B"'.
        # Take the quoted letter when there is one, and match an alias
        # anywhere in the string -- the old code read the leading word's first
        # letter, so that example silently parsed as Avenue S.
        q = re.search(r'"\s*([a-t])\s*"', s)
        if q:
            return Recipe.avenue_slot(q.group(1))
        for name, slot in (("broadway", 9), ("water", 0), ("strand", 1),
                           ("mechanic", 2), ("market", 3), ("post office", 4),
                           ("postoffice", 5 - 1), ("church", 5), ("winnie", 6),
                           ("ball", 7), ("sealy", 8)):
            if name in s:
                return slot
        s = s.replace("or.", "").replace(" or ", " ").strip(' ."\'')
        if s.isdigit():
            return int(s)
        if s.startswith("broadway"):
            return 9
        aliases = {"water": 0, "strand": 1, "mechanic": 2, "market": 3,
                   "postoffice": 4, "post office": 4, "church": 5,
                   "winnie": 6, "ball": 7, "sealy": 8}
        if s in aliases:
            return aliases[s]
        half = ("1/2" in s) or ("½" in s) or s.endswith("half")
        letter = s[0]
        if letter in "abcdefghijkl" and not half:
            return "abcdefghijkl".index(letter)
        if letter == "m":
            return 13 if half else 12
        if letter in "nopqrst":
            j = "nopqrst".index(letter)
            return 14 + 2 * j + (1 if half else 0)
        raise ValueError(f"unknown avenue {avenue!r}")

    def locate(self, street_no=None, avenue=None):
        """Mosaic-frame point for a street/avenue crossing (either may be
        None: returns the corridor coordinate that is known)."""
        g = self.grid
        x = y = None
        if avenue is not None:
            slot = self.avenue_slot(avenue)
            x = g["avenues"][str(slot)]["x"]
        if street_no is not None:
            y = g["streets"][str(int(street_no))]["y"]
        return x, y

def px_per_ft(recipe):
    """Mosaic pixels per ground foot.

    1912 is verified against the master's own print manifest: its
    map_rect_canvas_xyxy and map_rect_mosaic_xyxy are both 22882x14489, so the
    mosaic frame IS the print frame at 1:1, and 22882 px over a 40 in page at
    5.7966 px/ft works out to ~99 ft/in. (Note that is ~100 ft/in, not the
    50 ft/in the brief states -- the master is a half-scale reduction of the
    sheets' native drawing scale.) At 5.7966 the corridor grid gives block
    pitches of 350.4 ft (avenues) and 399.5 ft (streets), and a street the
    sheet labels 80' measures 76 ft.

    1899 was wrong: it assumed an avenue pitch of 262 ft, which is the block
    face, not the centre-to-centre pitch. Galveston's geometry is the same in
    both years, so the 1899 mosaic's 1006 px avenue pitch and 1169 px street
    pitch correspond to the 350.4/399.5 ft above, giving 2.871 and 2.926.
    Cross-check: an 80'-labelled street measures 84 ft at 2.90 and an
    implausible 63 ft at the old 3.84. The old value made every 1899 crop
    cover 1.34x the ground asked for, so crops printed at 1.34x the requested
    ft/in.
    """
    if recipe.year == 1912:
        return 5.7966
    return 2.8985                            # mean of the avenue/street solves

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
        """(M, t): p_mosaic = M @ p_native + t, from the recipe transforms."""
        s = self.transforms["sheets"][str(sheet)]
        if "raw" in s:                       # 1912 convention
            r = s["raw"]
            return (np.array([[r["a"], -r["b"]], [r["b"], r["a"]]]),
                    np.array([r["tx"], r["ty"]]))
        if "m" in s:                         # 1899 affine convention
            return np.array(s["m"], float), np.array(s["t"], float)
        raise ValueError(f"unknown transform format for sheet {sheet}")

    def ownership(self):
        """[(unit, exterior_polygon_mosaic np.ndarray)]"""
        out = []
        for r in self.masks["regions"]:
            uid = str(r.get("unit", r.get("sheet")))
            out.append((uid, np.array(r["polygon_mosaic"]["exterior"], float)))
        return out

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
        s = str(avenue).strip().lower().replace("avenue", "").replace("av.", "").strip()
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
    if recipe.year == 1912:
        return 5.7966                        # kappa from the 1912 solve
    return 1006.0 / 262.0                    # 1899: avenue pitch over ~262 ft

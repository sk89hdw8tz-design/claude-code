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
        gpath = os.path.join(self.dir, "grid.json")
        self.grid = json.load(open(gpath)) if os.path.exists(gpath) else None
        mpath = os.path.join(self.dir, "seams", "masks.json")
        self.masks = json.load(open(mpath)) if os.path.exists(mpath) else None
        self.cache = os.path.join(REPO, "work", "sheets", str(year))
        os.makedirs(self.cache, exist_ok=True)

    # ---------------- fetching ----------------
    def fetch(self, file):
        """Return a local path to the named source file, hash-verified."""
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
        """[(sheet, exterior_polygon_mosaic np.ndarray)]"""
        out = []
        for r in self.masks["regions"]:
            out.append((str(r["sheet"]),
                        np.array(r["polygon_mosaic"]["exterior"], float)))
        return out

    def sheet_file(self, sheet):
        """Inventory file name for a sheet's full-resolution scan."""
        if self.year == 1912:
            m = {"7": 11, "8": 13, "9": 15, "10": 17, "11": 19, "12": 21,
                 "39": 49, "40": 50, "43": 53, "44": 54, "49": 59, "50": 60,
                 "5": 9, "13": 23}
            return f"sanborn08539_004_img{m[str(sheet)]:03d}_archival.jp2"
        return f"Galveston_1899_sheet_{int(sheet):02d}.jpg"

    # ---------------- address lookup ----------------
    def locate(self, street_no=None, avenue=None):
        """Mosaic-frame point for a street/avenue crossing (either may be
        None: returns the corridor coordinate that is known)."""
        g = self.grid
        x = y = None
        if avenue is not None:
            slot = avenue if isinstance(avenue, int) else \
                "abcdefghijk".index(avenue.strip().lower()[0]) if avenue.strip().lower() != "broadway" else 9
            x = g["avenues"][str(slot)]["x"]
        if street_no is not None:
            y = g["streets"][str(int(street_no))]["y"]
        return x, y

def px_per_ft(recipe):
    if recipe.year == 1912:
        return 5.7966                        # kappa from the 1912 solve
    return 1006.0 / 262.0                    # 1899: avenue pitch over ~262 ft

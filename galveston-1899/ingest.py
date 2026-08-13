#!/usr/bin/env python3
"""Take a zip (or folder) of hand-saved sheets and normalise it for the pipeline.

Files saved by hand carry whatever names the browser gave them, and may include
both the plain and (Skeleton) version of a sheet. The rest of the pipeline keys
off exact labels, so this sorts the incoming pile out first: it works out what
each file is, renames a copy into the canonical scheme, verifies every image
decodes, and reports what is present, missing or unexpected.

    python3 ingest.py --src incoming.zip --out maps

Canonical names produced:
    00-key.jpg  00-index.jpg  00-title.jpg
    sheet-08.jpg            (plain)
    sheet-08-skeleton.jpg   (skeleton variant, kept but never printed)

Nothing is deleted or moved -- the source is only read.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile

EXPECTED_SHEETS = [8, 7, 6, 5, 11, 13, 15, 12, 14, 16, 41, 39, 37]
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".gif"}

SKELETON_RE = re.compile(r"skelet", re.I)
KEY_RE = re.compile(r"\bkey\b|[-_]key[-_.]", re.I)
INDEX_RE = re.compile(r"\bindex\b|[-_]index[-_.]", re.I)
TITLE_RE = re.compile(r"title", re.I)
COMPRESS_RE = re.compile(r"compress", re.I)
# "sheet 12", "sheet-12", "sheet_12", "sht12", "s12"
SHEET_RE = re.compile(r"(?:sheet|sht)[\s\-_]*0*(\d{1,3})\b", re.I)
YEAR_RE = re.compile(r"\b(1[6-9]\d{2}|20\d{2})\b")


def classify(name: str) -> tuple[str | None, bool]:
    """Return (kind, is_skeleton). kind is 'sheet-N', 'key', 'index', 'title',
    'compress', or None when the file cannot be identified."""
    stem = os.path.splitext(os.path.basename(name))[0]
    skel = bool(SKELETON_RE.search(stem))

    m = SHEET_RE.search(stem)
    if m:
        return f"sheet-{int(m.group(1)):02d}", skel

    # Front matter only after ruling out a sheet number, since a filename like
    # "index-sheet-12" is a sheet.
    if KEY_RE.search(stem):
        return "key", skel
    if INDEX_RE.search(stem):
        return "index", skel
    if TITLE_RE.search(stem):
        return "title", skel
    if COMPRESS_RE.search(stem):
        return "compress", skel

    # Last resort: a bare number that is not a year (e.g. "galveston_1899_12").
    candidates = [int(x) for x in re.findall(r"\d{1,3}", YEAR_RE.sub(" ", stem))]
    if len(candidates) == 1 and 1 <= candidates[0] <= 200:
        return f"sheet-{candidates[0]:02d}", skel
    return None, skel


def collect(src: str, workdir: str) -> tuple[str, list[str]]:
    """Return (root, image paths). Extracts a zip into workdir if needed."""
    if os.path.isdir(src):
        root = src
    elif zipfile.is_zipfile(src):
        root = os.path.join(workdir, "unzipped")
        os.makedirs(root, exist_ok=True)
        with zipfile.ZipFile(src) as zf:
            for info in zf.infolist():
                # Refuse absolute paths and ../ escapes from the archive.
                target = os.path.normpath(os.path.join(root, info.filename))
                if not target.startswith(os.path.abspath(root) + os.sep) and \
                        os.path.abspath(target) != os.path.abspath(root):
                    print(f"  ! skipping unsafe archive path: {info.filename}")
                    continue
                zf.extract(info, root)
        print(f"Extracted {src} -> {root}")
    else:
        print(f"error: {src} is neither a directory nor a zip", file=sys.stderr)
        raise SystemExit(1)

    paths = []
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if f.startswith("."):
                continue
            if os.path.splitext(f)[1].lower() in IMAGE_EXT:
                paths.append(os.path.join(dirpath, f))
    return root, sorted(paths)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True, help="zip file or directory of saved sheets")
    ap.add_argument("--out", default="maps", help="normalised output directory")
    ap.add_argument("--no-verify", action="store_true")
    args = ap.parse_args()

    workdir = tempfile.mkdtemp(prefix="ingest-")
    try:
        root, paths = collect(args.src, workdir)
        if not paths:
            print(f"error: no image files found in {args.src}", file=sys.stderr)
            return 1
        print(f"Found {len(paths)} image file(s)\n")

        os.makedirs(args.out, exist_ok=True)
        assigned: dict[str, str] = {}
        collisions: list[str] = []
        unknown: list[str] = []
        manifest = []

        for p in paths:
            kind, skel = classify(os.path.relpath(p, root))
            if kind is None:
                unknown.append(os.path.relpath(p, root))
                continue
            label = kind if kind.startswith("sheet-") else f"00-{kind}"
            if skel:
                label += "-skeleton"
            ext = os.path.splitext(p)[1].lower()
            if ext == ".jpeg":
                ext = ".jpg"
            dest_name = label + ext
            dest = os.path.join(args.out, dest_name)

            if label in assigned:
                collisions.append(f"{os.path.relpath(p, root)} -> {label} "
                                  f"(already taken by {assigned[label]})")
                continue
            assigned[label] = os.path.relpath(p, root)
            shutil.copy2(p, dest)

            entry = {"label": label, "file": dest_name,
                     "source_name": os.path.relpath(p, root),
                     "bytes": os.path.getsize(dest)}
            if not args.no_verify:
                try:
                    from PIL import Image
                    with Image.open(dest) as im:
                        im.verify()
                    with Image.open(dest) as im:
                        entry["width"], entry["height"] = im.size
                        entry["format"] = im.format
                except ImportError:
                    pass
                except Exception as e:  # noqa: BLE001
                    print(f"  ! {dest_name}: unreadable image ({e})")
                    entry["error"] = str(e)
            entry["sha256"] = hashlib.sha256(open(dest, "rb").read()).hexdigest()
            manifest.append(entry)

        plain = {l for l in assigned if l.startswith("sheet-") and not l.endswith("-skeleton")}
        skels = {l for l in assigned if l.endswith("-skeleton")}
        want = {f"sheet-{n:02d}" for n in EXPECTED_SHEETS}

        print(f"Normalised {len(manifest)} file(s) into {args.out}/")
        print(f"  plain sheets    : {len(plain)}")
        print(f"  skeleton sheets : {len(skels)}")
        for k in ("00-key", "00-index", "00-title", "00-compress"):
            if k in assigned:
                print(f"  {k:<16}: yes")

        missing = sorted(want - plain)
        extra = sorted(plain - want)
        print()
        if missing:
            print(f"  ! MISSING {len(missing)} of the 13 requested: {', '.join(missing)}")
        else:
            print("  All 13 requested sheets present.")
        if extra:
            print(f"  ! extra sheets not in the requested 13: {', '.join(extra)}")
        if "00-key" not in assigned:
            print("  ! no Key found")
        if "00-index" not in assigned:
            print("  ! no Index found -- the mosaic cannot be aligned without an index map")
        if collisions:
            print(f"  ! {len(collisions)} file(s) mapped to a label already taken:")
            for c in collisions:
                print(f"      {c}")
        if unknown:
            print(f"  ! {len(unknown)} file(s) could not be identified:")
            for u in unknown[:12]:
                print(f"      {u}")
            print("    Rename these to include the sheet number (e.g. 'sheet-12') and re-run.")

        with open(os.path.join(args.out, "ingest-manifest.json"), "w") as fh:
            json.dump({"source": os.path.abspath(args.src), "items": manifest,
                       "unidentified": unknown, "collisions": collisions}, fh, indent=2)
        print(f"\nManifest: {os.path.join(args.out, 'ingest-manifest.json')}")
        print("\nNext:")
        print(f"  python3 read_index.py tiles --src {args.out}/00-index.jpg --out index-tiles")
        print(f"  python3 make_print.py --src {args.out} --exclude key,index,skeleton "
              f"--coverage --probe --trim --neatline")
        return 1 if (missing or unknown or collisions) else 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

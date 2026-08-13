#!/usr/bin/env python3
"""Fetch selected Galveston 1899 Sanborn sheets from the UT Austin PCL map library.

The index page lists more than one Galveston 1899 run (the "first" and "second"
sets). Rather than hard-coding URLs, this script parses the index page at run
time, splits the Galveston 1899 links into groups by their URL directory, and
lets you pick which group to pull from. Run with --list first to see what is
actually on the page before committing to a download.

Typical use:

    python3 fetch_maps.py --list                     # show the groups, download nothing
    python3 fetch_maps.py --group 2 --out ./maps     # download + zip the second set

Requires: Pillow (for download verification only; pass --no-verify to skip).
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import html.parser
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import OrderedDict

INDEX_URL = "https://maps.lib.utexas.edu/maps/sanborn/g.html"

# The 13 map sheets requested, in the order they were given.
DEFAULT_SHEETS = [8, 7, 6, 5, 11, 13, 15, 12, 14, 16, 41, 39, 37]

# Front matter to ship alongside the sheets. The 1899 listing has a "Key" but
# nothing literally called "Legend"; "the key and legend" means the Key sheet.
# The Index is pulled too because one of these two is the index map that gives
# each sheet's geographic position -- it is the alignment reference for the
# mosaic. Both go in the zip; neither is printed as a tile.
DEFAULT_FRONT = ["key", "index"]

FRONT_PATTERNS = {
    "key": re.compile(r"\bkey\b", re.I),
    "legend": re.compile(r"\blegend\b", re.I),
    "title": re.compile(r"\btitle\s*page\b", re.I),
    "index": re.compile(r"\bindex\b", re.I),
    "compress": re.compile(r"cotton\s+compress", re.I),
}

# "Galveston 1899 Sheet 12" / "Galveston 1899 Sheet 12 (Skeleton)"
SHEET_RE = re.compile(r"\bsheet\s+(\d{1,3})\b", re.I)
SKELETON_RE = re.compile(r"skeleton", re.I)
YEAR_RE = re.compile(r"\b1899\b")
CITY_RE = re.compile(r"galveston", re.I)

USER_AGENT = (
    "Mozilla/5.0 (compatible; sanborn-fetch/1.0; personal archival use; "
    "+https://maps.lib.utexas.edu/maps/sanborn/)"
)


@dataclasses.dataclass
class Link:
    text: str
    url: str
    order: int

    @property
    def directory(self) -> str:
        p = urllib.parse.urlparse(self.url)
        return f"{p.scheme}://{p.netloc}{p.path.rsplit('/', 1)[0]}/"

    @property
    def filename(self) -> str:
        name = urllib.parse.unquote(urllib.parse.urlparse(self.url).path.rsplit("/", 1)[-1])
        return name or f"item-{self.order}"

    @property
    def sheet_no(self) -> int | None:
        m = SHEET_RE.search(self.text)
        return int(m.group(1)) if m else None

    @property
    def is_skeleton(self) -> bool:
        return bool(SKELETON_RE.search(self.text))

    def front_kind(self) -> str | None:
        if self.sheet_no is not None:
            return None
        for kind, pat in FRONT_PATTERNS.items():
            if pat.search(self.text):
                return kind
        return None


class LinkParser(html.parser.HTMLParser):
    """Collect <a href> links with their visible text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[Link] = []
        self._href: str | None = None
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self._flush()
            self._href = href
            self._buf = []

    def handle_data(self, data):
        if self._href is not None:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a":
            self._flush()

    def _flush(self):
        if self._href is None:
            return
        text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
        if text:
            self.links.append(Link(text=text, url=self._href, order=len(self.links)))
        self._href = None
        self._buf = []

    def close(self):
        super().close()
        self._flush()


def http_get(url: str, retries: int = 4, timeout: int = 60) -> bytes:
    """GET with exponential backoff on transient failures."""
    delay = 2.0
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            # 4xx other than 429 will not fix themselves; fail fast.
            if e.code != 429 and 400 <= e.code < 500:
                raise
            last = e
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            last = e
        if attempt < retries:
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"GET failed after {retries + 1} attempts: {url} ({last})")


def discover(index_url: str) -> list[Link]:
    """Return every Galveston 1899 link on the index page, absolute and de-duped."""
    raw = http_get(index_url)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    parser = LinkParser()
    parser.feed(text)
    parser.close()

    out: list[Link] = []
    seen: set[str] = set()
    for link in parser.links:
        if not (CITY_RE.search(link.text) and YEAR_RE.search(link.text)):
            continue
        absolute = urllib.parse.urljoin(index_url, link.url)
        if not re.search(r"\.(jpe?g|gif|png|tiff?|pdf)$", urllib.parse.urlparse(absolute).path, re.I):
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        out.append(Link(text=link.text, url=absolute, order=len(out)))
    return out


def group_links(links: list[Link]) -> "OrderedDict[str, list[Link]]":
    """Split into groups by URL directory, in first-appearance order.

    The distinct runs of a given city/year on this site live in separate
    directories, so directory is the reliable discriminator. Groups are
    numbered by the order they first appear on the page, so --group 2 is the
    second set as read top-to-bottom.
    """
    groups: "OrderedDict[str, list[Link]]" = OrderedDict()
    for link in links:
        groups.setdefault(link.directory, []).append(link)
    return groups


def select(
    links: list[Link],
    sheets: list[int],
    front: list[str],
    skeleton: bool = False,
) -> tuple[list[tuple[str, Link]], list[str]]:
    """Pick the requested sheets and front matter out of one group.

    Returns (selected, problems). Selection is exact: a requested sheet that is
    missing is reported rather than silently substituted.
    """
    by_sheet: dict[int, list[Link]] = {}
    by_front: dict[str, list[Link]] = {}
    for link in links:
        n = link.sheet_no
        if n is not None:
            by_sheet.setdefault(n, []).append(link)
        else:
            kind = link.front_kind()
            if kind:
                by_front.setdefault(kind, []).append(link)

    selected: list[tuple[str, Link]] = []
    problems: list[str] = []

    for kind in front:
        cands = by_front.get(kind, [])
        if not cands:
            problems.append(f"front matter '{kind}': not found in this group")
            continue
        for i, link in enumerate(cands):
            suffix = f"-{i + 1}" if len(cands) > 1 else ""
            selected.append((f"00-{kind}{suffix}", link))

    for n in sheets:
        cands = by_sheet.get(n, [])
        if not cands:
            problems.append(f"sheet {n}: not found in this group")
            continue
        wanted = [c for c in cands if c.is_skeleton == skeleton]
        if not wanted:
            wanted = cands
            problems.append(
                f"sheet {n}: no {'skeleton' if skeleton else 'standard'} variant; "
                f"using '{wanted[0].text}'"
            )
        if len(wanted) > 1:
            problems.append(
                f"sheet {n}: {len(wanted)} candidates, using first "
                f"({', '.join(repr(w.text) for w in wanted)})"
            )
        selected.append((f"sheet-{n:02d}", wanted[0]))

    return selected, problems


def verify_image(path: str) -> tuple[int, int, str] | None:
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            return im.width, im.height, im.format or "?"
    except Exception as e:  # noqa: BLE001 - report, don't crash the batch
        raise RuntimeError(f"not a readable image: {e}") from e


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--index-url", default=INDEX_URL)
    ap.add_argument("--group", type=int, default=2,
                    help="which Galveston 1899 group to pull (1 = first set, 2 = second set). Default 2.")
    ap.add_argument("--list", action="store_true", help="list discovered groups and exit")
    ap.add_argument("--sheets", default=",".join(str(s) for s in DEFAULT_SHEETS),
                    help="comma-separated sheet numbers")
    ap.add_argument("--front", default=",".join(DEFAULT_FRONT),
                    help=f"front matter to include; choices: {','.join(FRONT_PATTERNS)}")
    ap.add_argument("--skeleton", action="store_true",
                    help="prefer the (Skeleton) variant where one exists")
    ap.add_argument("--out", default="maps", help="output directory")
    ap.add_argument("--zip", dest="zip_path", default=None,
                    help="zip path (default <out>/galveston-1899-selection.zip)")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between downloads (be polite)")
    ap.add_argument("--no-verify", action="store_true", help="skip image verification")
    ap.add_argument("--force", action="store_true", help="re-download files that already exist")
    args = ap.parse_args()

    sheets = [int(s) for s in args.sheets.split(",") if s.strip()]
    front = [f.strip().lower() for f in args.front.split(",") if f.strip()]
    for f in front:
        if f not in FRONT_PATTERNS:
            print(f"error: unknown front matter '{f}' (choices: {', '.join(FRONT_PATTERNS)})", file=sys.stderr)
            return 2

    print(f"Reading index: {args.index_url}")
    try:
        links = discover(args.index_url)
    except Exception as e:  # noqa: BLE001
        print(f"error: could not read the index page: {e}", file=sys.stderr)
        return 1

    if not links:
        print("error: no Galveston 1899 image links found -- the page layout may have changed.",
              file=sys.stderr)
        return 1

    groups = group_links(links)
    print(f"Found {len(links)} Galveston 1899 links in {len(groups)} group(s):\n")
    for i, (directory, items) in enumerate(groups.items(), start=1):
        n_sheets = sum(1 for x in items if x.sheet_no is not None)
        n_front = sum(1 for x in items if x.front_kind())
        rng = [x.sheet_no for x in items if x.sheet_no is not None]
        span = f"sheets {min(rng)}-{max(rng)}" if rng else "no numbered sheets"
        print(f"  [{i}] {directory}")
        print(f"      {len(items)} links | {n_sheets} sheet links ({span}) | {n_front} front-matter links")
        print(f"      first: {items[0].text}  ->  {items[0].filename}")
        print(f"      last : {items[-1].text}  ->  {items[-1].filename}")
        print()

    if args.list:
        return 0

    if not 1 <= args.group <= len(groups):
        print(f"error: --group {args.group} out of range; page has {len(groups)} group(s).", file=sys.stderr)
        return 2

    directory, chosen = list(groups.items())[args.group - 1]
    print(f"Using group [{args.group}]: {directory}\n")

    selected, problems = select(chosen, sheets, front, skeleton=args.skeleton)
    for p in problems:
        print(f"  ! {p}")
    if problems:
        print()

    missing = [p for p in problems if "not found" in p]
    if missing:
        print(f"error: {len(missing)} requested item(s) are not in group {args.group}. "
              f"Re-run with --list to check the other group, or adjust --sheets/--front.",
              file=sys.stderr)
        return 1

    os.makedirs(args.out, exist_ok=True)
    manifest = []
    failures = []

    for i, (label, link) in enumerate(selected, start=1):
        ext = os.path.splitext(link.filename)[1] or ".jpg"
        dest_name = f"{label}{ext}"
        dest = os.path.join(args.out, dest_name)

        if os.path.exists(dest) and not args.force and os.path.getsize(dest) > 0:
            print(f"  [{i:2d}/{len(selected)}] {dest_name:<28} cached")
        else:
            print(f"  [{i:2d}/{len(selected)}] {dest_name:<28} <- {link.filename}", end="", flush=True)
            try:
                data = http_get(link.url)
            except Exception as e:  # noqa: BLE001
                print(f"  FAILED: {e}")
                failures.append((dest_name, str(e)))
                continue
            tmp = dest + ".part"
            with open(tmp, "wb") as fh:
                fh.write(data)
            os.replace(tmp, dest)
            print(f"  {len(data) / 1e6:.1f} MB")
            if args.delay:
                time.sleep(args.delay)

        entry = {
            "label": label,
            "file": dest_name,
            "title": link.text,
            "url": link.url,
            "bytes": os.path.getsize(dest),
            "sha256": hashlib.sha256(open(dest, "rb").read()).hexdigest(),
        }
        if not args.no_verify:
            try:
                info = verify_image(dest)
            except RuntimeError as e:
                print(f"       ! {dest_name}: {e}")
                failures.append((dest_name, str(e)))
                continue
            if info:
                entry["width"], entry["height"], entry["format"] = info
        manifest.append(entry)

    manifest_path = os.path.join(args.out, "manifest.json")
    with open(manifest_path, "w") as fh:
        json.dump(
            {
                "source_index": args.index_url,
                "group_index": args.group,
                "group_directory": directory,
                "requested_sheets": sheets,
                "front_matter": front,
                "skeleton_variant": args.skeleton,
                "items": manifest,
            },
            fh,
            indent=2,
        )
    print(f"\nManifest: {manifest_path}")

    if failures:
        print(f"\n{len(failures)} item(s) failed; zip not written:", file=sys.stderr)
        for name, err in failures:
            print(f"  - {name}: {err}", file=sys.stderr)
        return 1

    zip_path = args.zip_path or os.path.join(args.out, "galveston-1899-selection.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for entry in manifest:
            zf.write(os.path.join(args.out, entry["file"]), entry["file"])
        zf.write(manifest_path, "manifest.json")
    size = os.path.getsize(zip_path)
    print(f"Zip: {zip_path} ({size / 1e6:.1f} MB, {len(manifest) + 1} entries)")

    if not args.no_verify:
        dims = [(e["label"], e.get("width"), e.get("height")) for e in manifest if e.get("width")]
        if dims:
            print("\nSheet dimensions (feed these to make_print.py):")
            for label, w, h in dims:
                print(f"  {label:<16} {w} x {h}  (aspect {w / h:.3f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Fetch Galveston 1912 Sanborn material from the Library of Congress.

Runs in GitHub Actions (ordinary internet egress) because the Claude Code
session environments deny egress to archival hosts. The UT Austin PCL server
403s GitHub-runner IPs, so the source is LOC's Sanborn collection (public
domain, designed for programmatic access): volume group `sanborn08539`,
Galveston, Galveston County, Texas.

Two phases, controlled by FETCH_LIST.json in this directory:

Phase A (no FETCH_LIST.json):
  - query /item/sanborn08539_00N/?fo=json for N=1..10, keep items whose date
    is 1912 (the pre-1931 public-domain edition, 77 sheets + key + skeletons);
  - save full item JSON metadata;
  - download image index 0 (customarily the key/index sheet) at FULL
    resolution;
  - download EVERY image at contact-sheet size (~1500 px wide) so sheet
    numbers can be read offline and mapped to image indices.

Phase B (FETCH_LIST.json present, {"item_id": ..., "indices": [...]}):
  - download the listed image indices at FULL resolution.

Downloads are immutable archival originals: never edited or recompressed.
Every file gets SHA-256 + exact source URL in inventory.json. Errors are
written to FETCH_STATUS.md so diagnostics survive even on failure.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
ITEM_GROUP = "sanborn08539"
CANDIDATE_ITEMS = [f"{ITEM_GROUP}_{n:03d}" for n in range(1, 11)]
TARGET_DATE = "1912"
USER_AGENT = "sanborn-mosaic-fetch/2.0 (personal archival research of public-domain maps)"
DELAY_THUMB_S = 2.0
DELAY_FULL_S = 3.0
RETRIES = 4
STATUS_LINES: list[str] = []


def log(msg: str) -> None:
    print(msg, flush=True)
    STATUS_LINES.append(msg)


def fetch(url: str, expect_json: bool = False):
    last: Exception | None = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = resp.read()
            return json.loads(data) if expect_json else data
        except Exception as exc:  # noqa: BLE001
            last = exc
            log(f"  retry {attempt + 1}/{RETRIES} for {url}: {exc}")
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"failed after {RETRIES} attempts: {url}: {last}")


def image_groups(item_json: dict) -> list[list[dict]]:
    """Return one list of format-dicts per physical image in the item."""
    groups: list[list[dict]] = []
    for res in item_json.get("resources", []):
        for grp in res.get("files", []):
            if isinstance(grp, list):
                groups.append([f for f in grp if isinstance(f, dict)])
    return groups


def pick_jpeg(group: list[dict], target_width: int | None) -> dict | None:
    jpegs = [
        f
        for f in group
        if f.get("mimetype") == "image/jpeg" and f.get("url")
    ]
    if not jpegs:
        return None
    for f in jpegs:
        f["_w"] = int(f.get("width") or 0)
    if target_width is None:
        return max(jpegs, key=lambda f: f["_w"])
    return min(jpegs, key=lambda f: abs(f["_w"] - target_width))


def save(url: str, dest: Path, inventory: list[dict], kind: str, index: int) -> None:
    data = fetch(url)
    if not data.startswith(b"\xff\xd8"):
        raise RuntimeError(f"not a JPEG ({len(data)} bytes): {url}")
    dest.write_bytes(data)
    inventory.append(
        {
            "file": dest.name,
            "kind": kind,
            "image_index": index,
            "source_url": url,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "downloaded_utc": datetime.now(timezone.utc).isoformat(),
        }
    )
    log(f"ok [{kind}] {dest.name} {len(data)} bytes")


def load_inventory() -> list[dict]:
    p = OUT_DIR / "inventory.json"
    if p.exists():
        return json.loads(p.read_text()).get("items", [])
    return []


def write_inventory(items: list[dict]) -> None:
    (OUT_DIR / "inventory.json").write_text(
        json.dumps(
            {
                "generated_utc": datetime.now(timezone.utc).isoformat(),
                "source": "Library of Congress Sanborn collection, public domain",
                "item_group": ITEM_GROUP,
                "count": len(items),
                "items": items,
            },
            indent=1,
        )
    )


def main() -> int:
    inventory = load_inventory()
    fetch_list = None
    fl_path = OUT_DIR / "FETCH_LIST.json"
    if fl_path.exists():
        fetch_list = json.loads(fl_path.read_text())

    if fetch_list is None:
        # ---- Phase A ----
        log(f"Phase A start {datetime.now(timezone.utc).isoformat()}")
        matches = []
        for item_id in CANDIDATE_ITEMS:
            url = f"https://www.loc.gov/item/{item_id}/?fo=json"
            try:
                j = fetch(url, expect_json=True)
            except RuntimeError as exc:
                log(f"item {item_id}: unavailable ({exc})")
                continue
            item = j.get("item", {})
            date = str(item.get("date", ""))
            title = str(item.get("title", ""))
            n_img = len(image_groups(j))
            log(f"item {item_id}: date={date!r} images={n_img} title={title[:70]!r}")
            if TARGET_DATE in date:
                matches.append((item_id, j))
            time.sleep(1.0)

        if not matches:
            log("ERROR: no sanborn08539 item with date 1912 found")
            return 1

        for item_id, j in matches:
            (OUT_DIR / f"{item_id}_metadata.json").write_text(json.dumps(j, indent=1))
            groups = image_groups(j)
            log(f"{item_id}: saving metadata; {len(groups)} images")

            full0 = pick_jpeg(groups[0], None) if groups else None
            if full0:
                save(
                    full0["url"],
                    OUT_DIR / f"{item_id}_img000_full.jpg",
                    inventory,
                    "phaseA-full-first-image",
                    0,
                )
                time.sleep(DELAY_FULL_S)

            for idx, grp in enumerate(groups):
                thumb = pick_jpeg(grp, 1500)
                if not thumb:
                    log(f"  WARNING image {idx}: no jpeg format found")
                    continue
                save(
                    thumb["url"],
                    OUT_DIR / f"{item_id}_img{idx:03d}_thumb.jpg",
                    inventory,
                    "phaseA-contact-thumb",
                    idx,
                )
                time.sleep(DELAY_THUMB_S)

        write_inventory(inventory)
        log("Phase A complete")
        return 0

    # ---- Phase B ----
    item_id = fetch_list["item_id"]
    indices = list(fetch_list["indices"])
    log(f"Phase B start {datetime.now(timezone.utc).isoformat()}: {item_id} x{len(indices)}")
    meta_path = OUT_DIR / f"{item_id}_metadata.json"
    j = (
        json.loads(meta_path.read_text())
        if meta_path.exists()
        else fetch(f"https://www.loc.gov/item/{item_id}/?fo=json", expect_json=True)
    )
    groups = image_groups(j)
    have = {i["file"] for i in inventory}
    for idx in indices:
        name = f"{item_id}_img{idx:03d}_full.jpg"
        if name in have:
            log(f"skip {name}: already present")
            continue
        if idx >= len(groups):
            log(f"ERROR index {idx} out of range ({len(groups)} images)")
            return 1
        full = pick_jpeg(groups[idx], None)
        if not full:
            log(f"ERROR image {idx}: no jpeg format found")
            return 1
        save(full["url"], OUT_DIR / name, inventory, "phaseB-full-sheet", idx)
        time.sleep(DELAY_FULL_S)
    write_inventory(inventory)
    log("Phase B complete")
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception as exc:  # noqa: BLE001 - record diagnostics before dying
        STATUS_LINES.append(f"FATAL: {exc}")
        code = 1
    finally:
        (OUT_DIR / "FETCH_STATUS.md").write_text(
            "# CI fetch status\n\nMost recent run (UTC "
            + datetime.now(timezone.utc).isoformat()
            + ")\n\n```\n"
            + "\n".join(STATUS_LINES)
            + "\n```\n"
        )
    sys.exit(code)

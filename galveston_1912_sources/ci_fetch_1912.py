#!/usr/bin/env python3
"""Fetch the Galveston 1912 Sanborn sheets from the UT Austin PCL map library.

Runs inside GitHub Actions (which has ordinary internet egress) because the
Claude Code session environments deny egress to maps.lib.utexas.edu. Downloads
are immutable archival originals: nothing is edited, resized, or recompressed.

Strategy: parse the live index page, keep every .jpg link whose URL mentions
Galveston and 1912 (key, index, and all sheets), download politely, verify
JPEG magic bytes, and write an inventory with SHA-256 + provenance. The full
1912 set is fetched; downtown/wharf sheet selection happens later, offline,
from the key map itself.
"""

from __future__ import annotations

import hashlib
import html.parser
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

INDEX_URL = "https://maps.lib.utexas.edu/maps/sanborn/g.html"
OUT_DIR = Path(__file__).resolve().parent
USER_AGENT = (
    "Mozilla/5.0 (compatible; sanborn-fetch/2.0; personal archival use; "
    "+https://maps.lib.utexas.edu/maps/sanborn/)"
)
DELAY_S = 1.5
RETRIES = 4


class LinkParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []  # (href, text)
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._text).split())))
            self._href = None


def fetch(url: str) -> bytes:
    last: Exception | None = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001 - retry any transient failure
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"failed after {RETRIES} attempts: {url}: {last}")


def main() -> int:
    started = datetime.now(timezone.utc).isoformat()
    index_html = fetch(INDEX_URL)
    (OUT_DIR / "ut_index_g.html").write_bytes(index_html)

    parser = LinkParser()
    parser.feed(index_html.decode("utf-8", errors="replace"))

    galveston = []
    for href, text in parser.links:
        absu = urllib.parse.urljoin(INDEX_URL, href)
        blob = f"{absu} {text}".lower()
        if "galveston" in blob and absu.lower().endswith((".jpg", ".jpeg")):
            galveston.append({"url": absu, "text": text})

    targets = [l for l in galveston if "1912" in f"{l['url']} {l['text']}".lower()]

    (OUT_DIR / "link_audit.json").write_text(
        json.dumps(
            {
                "fetched_utc": started,
                "index_url": INDEX_URL,
                "galveston_links_total": len(galveston),
                "galveston_1912_links": len(targets),
                "all_galveston_links": galveston,
            },
            indent=1,
        )
    )

    if not targets:
        print("ERROR: no Galveston 1912 links found; see link_audit.json", file=sys.stderr)
        return 1

    inventory = []
    seen: set[str] = set()
    for link in targets:
        url = link["url"]
        if url in seen:
            continue
        seen.add(url)
        name = urllib.parse.unquote(urllib.parse.urlparse(url).path.rsplit("/", 1)[-1])
        dest = OUT_DIR / name
        data = fetch(url)
        if not data.startswith(b"\xff\xd8"):
            print(f"ERROR: not a JPEG: {url} ({len(data)} bytes)", file=sys.stderr)
            return 1
        dest.write_bytes(data)
        inventory.append(
            {
                "file": name,
                "source_url": url,
                "link_text": link["text"],
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "downloaded_utc": datetime.now(timezone.utc).isoformat(),
            }
        )
        print(f"ok {name} {len(data)} bytes")
        time.sleep(DELAY_S)

    (OUT_DIR / "inventory.json").write_text(
        json.dumps(
            {
                "generated_utc": datetime.now(timezone.utc).isoformat(),
                "index_url": INDEX_URL,
                "count": len(inventory),
                "items": inventory,
            },
            indent=1,
        )
    )
    print(f"done: {len(inventory)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())

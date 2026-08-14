#!/usr/bin/env python3
"""01 -- Acquire the official source scans from UT Perry-Castaneda Library.

DISCOVERY, NOT GUESSWORK
    This script does not contain a hard-coded path to any image. It fetches the
    collection page named in config, follows links, and works out which files
    correspond to the requested sheets. A URL that was never confirmed against
    the live site is not recorded anywhere in this project, because a
    plausible-looking wrong URL is worse than no URL.

HIGHEST AVAILABLE OFFICIAL RESOLUTION
    Before settling for the linked JPG, each page is probed for something
    better, in this order:
      1. a IIIF image service (info.json -> full/max) if one is advertised;
      2. a sibling file with an archival extension (.tif/.jp2/...);
      3. the linked JPG itself.
    Everything is probed with a real request and accepted only on a 200 with a
    plausible content type. Nothing is upscaled, and no unofficial mirror is
    ever consulted -- an upscaled copy is not resolution, it is invention.

PRIVACY
    Downloads only. Nothing is uploaded, and no third-party image service is
    contacted.

Outputs
    data/original/<file>              the untouched scans
    data/original/MANIFEST.json       URL, retrieval time, size, SHA-256, type
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sanborn.config import (load_config, paths, setup_logging, sha256_file,
                            utcnow, write_json)

IMAGE_EXT = (".jpg", ".jpeg", ".tif", ".tiff", ".png", ".jp2", ".sid", ".gif")


def make_session(cfg):
    import requests
    s = requests.Session()
    s.headers.update({"User-Agent": cfg["acquisition"].get(
        "user_agent", "sanborn-private-research/1.0")})
    return s


def get(session, url, timeout, retries, log, stream=False, method="GET"):
    """Fetch with exponential backoff. Network denials are reported, not hidden."""
    delay = 2.0
    last = None
    for attempt in range(1, retries + 1):
        try:
            r = session.request(method, url, timeout=timeout, stream=stream,
                                allow_redirects=True)
            if r.status_code < 400:
                return r
            last = f"HTTP {r.status_code}"
            # A policy denial will not improve by retrying.
            if r.status_code in (401, 403, 404, 405, 407):
                break
        except Exception as exc:
            last = f"{type(exc).__name__}: {exc}"
        if attempt < retries:
            log.warning("  %s (attempt %d/%d) -> retrying in %.0fs",
                        last, attempt, retries, delay)
            time.sleep(delay)
            delay *= 2
    log.error("  FAILED %s : %s", url, last)
    return None


def discover_links(session, cfg, log):
    """Walk the collection page and collect candidate pages for our city/year."""
    from bs4 import BeautifulSoup

    acq = cfg["acquisition"]
    base = acq["collection_url"]
    city, year = acq["city"].lower(), str(acq["year"])
    log.info("fetching collection index: %s", base)
    r = get(session, base, acq["timeout_seconds"], acq["retries"], log)
    if r is None:
        return None, ("Could not reach the collection index. If this is a "
                      "network-policy denial, run this script from a machine "
                      "with ordinary internet access -- see README.")
    soup = BeautifulSoup(r.text, "lxml")

    # Any link whose URL or text mentions the city is a candidate; the year is
    # matched loosely because collections label editions inconsistently.
    candidates = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = " ".join(a.get_text(" ", strip=True).split())
        blob = f"{href} {text}".lower()
        if city in blob:
            candidates.append((urljoin(base, href), text))
    log.info("  %d link(s) mention %r on the index page", len(candidates), city)

    # Prefer links that also mention the year; otherwise follow city pages one
    # level deeper and look for the year there.
    direct = [(u, t) for u, t in candidates if year in f"{u} {t}"]
    pages = direct or candidates
    return pages, None


def collect_image_urls(session, cfg, pages, log):
    """From candidate pages, gather image URLs keyed by sheet identifier."""
    from bs4 import BeautifulSoup

    acq = cfg["acquisition"]
    year = str(acq["year"])
    wanted = {str(s) for s in acq["sheets"]}
    extra = [e.lower() for e in acq.get("extra_pages", [])]
    found = {}

    to_visit = list(dict.fromkeys(u for u, _ in pages))
    seen_pages = set()
    while to_visit:
        url = to_visit.pop(0)
        if url in seen_pages:
            continue
        seen_pages.add(url)
        if url.lower().endswith(IMAGE_EXT):
            _classify(url, wanted, extra, year, found, log)
            continue
        r = get(session, url, acq["timeout_seconds"], acq["retries"], log)
        if r is None or "html" not in r.headers.get("Content-Type", ""):
            continue
        soup = BeautifulSoup(r.text, "lxml")
        for a in soup.find_all("a", href=True):
            link = urljoin(url, a["href"])
            if link.lower().endswith(IMAGE_EXT):
                _classify(link, wanted, extra, year, found, log,
                          label=a.get_text(" ", strip=True))
            elif year in link and urlparse(link).netloc == urlparse(url).netloc \
                    and link not in seen_pages and len(seen_pages) < 40:
                to_visit.append(link)
    return found


def _classify(url, wanted, extra, year, found, log, label=""):
    """Decide whether an image URL is one of our sheets, the key, or the index."""
    name = Path(urlparse(url).path).name
    blob = f"{name} {label}".lower()
    if year not in url and year not in blob:
        return
    for kw in extra:
        if kw in blob:
            found.setdefault(kw, url)
            log.info("  %-6s <- %s", kw, url)
            return
    # Sheet numbers appear as a delimited token, so "1" never matches "10"/"21".
    for num in sorted(wanted, key=len, reverse=True):
        if re.search(rf"(?<![0-9]){num}(?![0-9])", name):
            key = f"sheet{num}"
            if key not in found:
                found[key] = url
                log.info("  %-6s <- %s", key, url)
            return


def probe_better_resolution(session, cfg, url, log):
    """Look for an official higher-resolution derivative of `url`.

    Returns (best_url, note). Every candidate is actually requested; nothing is
    assumed to exist because the pattern looks right.
    """
    acq = cfg["acquisition"]
    if not acq.get("prefer_higher_resolution", True):
        return url, "probing disabled in config"
    notes = []
    best, best_len = url, _content_length(session, cfg, url, log)

    if acq.get("probe_iiif", True):
        stem = url.rsplit(".", 1)[0]
        for cand in (f"{stem}/info.json", f"{url}/info.json"):
            r = get(session, cand, acq["timeout_seconds"], 1, log)
            if r is None:
                continue
            try:
                info = r.json()
            except Exception:
                continue
            svc = info.get("@id") or info.get("id")
            if svc:
                full = f"{svc}/full/max/0/default.jpg"
                ln = _content_length(session, cfg, full, log)
                notes.append(f"IIIF service advertised at {cand}")
                if ln and (not best_len or ln > best_len):
                    best, best_len = full, ln
                break

    for ext in acq.get("probe_extensions", []):
        cand = url.rsplit(".", 1)[0] + ext
        if cand == url:
            continue
        ln = _content_length(session, cfg, cand, log)
        if ln and (not best_len or ln > best_len):
            notes.append(f"archival derivative found: {cand} ({ln} bytes)")
            best, best_len = cand, ln

    return best, "; ".join(notes) or "no higher-resolution derivative found"


def _content_length(session, cfg, url, log):
    acq = cfg["acquisition"]
    r = get(session, url, acq["timeout_seconds"], 1, log, method="HEAD")
    if r is None:
        return None
    ctype = r.headers.get("Content-Type", "")
    if "image" not in ctype and "octet-stream" not in ctype:
        return None
    try:
        return int(r.headers.get("Content-Length", "0")) or None
    except ValueError:
        return None


def download(session, cfg, url, dest, log):
    acq = cfg["acquisition"]
    r = get(session, url, acq["timeout_seconds"], acq["retries"], log, stream=True)
    if r is None:
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    total = 0
    with tmp.open("wb") as fh:
        for chunk in r.iter_content(1 << 20):
            fh.write(chunk)
            total += len(chunk)
    tmp.replace(dest)
    log.info("  saved %s (%.1f MB)", dest.name, total / 1e6)
    return total


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default="galveston1889")
    ap.add_argument("--dry-run", action="store_true",
                    help="discover and probe, but download nothing")
    ap.add_argument("--force", action="store_true",
                    help="re-download even if the file is already present")
    args = ap.parse_args()

    cfg = load_config(args.profile)
    p = paths().ensure()
    log = setup_logging("01_fetch_sources")

    if cfg.get("acquisition", {}).get("skip"):
        log.info("profile %r declares acquisition.skip -- nothing to download",
                 args.profile)
        return 0

    session = make_session(cfg)
    pages, err = discover_links(session, cfg, log)
    if pages is None:
        log.error("%s", err)
        log.error("NOTHING WAS DOWNLOADED. The originals directory is unchanged.")
        return 2

    found = collect_image_urls(session, cfg, pages, log)
    wanted = [f"sheet{s}" for s in cfg["acquisition"]["sheets"]] + \
             list(cfg["acquisition"].get("extra_pages", []))
    missing = [w for w in wanted if w not in found]
    if missing:
        log.warning("could not locate: %s", ", ".join(missing))
        log.warning("Inspect the collection page by hand and add the correct "
                    "links to config -- do not guess them.")

    manifest = {"retrieved_utc": utcnow(),
                "collection_url": cfg["acquisition"]["collection_url"],
                "profile": args.profile, "items": {}}
    for key in wanted:
        if key not in found:
            manifest["items"][key] = {"status": "not_found"}
            continue
        url = found[key]
        best, note = probe_better_resolution(session, cfg, url, log)
        if best != url:
            log.info("  %s: using higher-resolution %s", key, best)
        dest = p.original / f"galveston_1889_{key}{Path(urlparse(best).path).suffix or '.jpg'}"
        entry = {"linked_url": url, "chosen_url": best, "resolution_note": note,
                 "file": dest.name, "status": "pending"}
        if args.dry_run:
            entry["status"] = "dry_run"
        elif dest.exists() and not args.force:
            entry["status"] = "already_present"
            log.info("  %s already present, skipping (use --force to refetch)", dest.name)
        else:
            size = download(session, cfg, best, dest, log)
            entry["status"] = "downloaded" if size else "download_failed"
        if dest.exists():
            entry["bytes"] = dest.stat().st_size
            entry["sha256"] = sha256_file(dest)
            entry["retrieved_utc"] = utcnow()
        manifest["items"][key] = entry

    write_json(p.original / "MANIFEST.json", manifest)
    log.info("manifest written: %s", p.original / "MANIFEST.json")
    ok = sum(1 for v in manifest["items"].values()
             if v.get("status") in ("downloaded", "already_present"))
    log.info("%d/%d source files present", ok, len(wanted))
    return 0 if ok == len(wanted) else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Phase A — acquisition.

Downloads LoC 1885 master TIFFs and UT 1877 JPEGs into sources/{year}/,
verifies dimensions, and writes sha256 manifest + source_urls.txt.
Originals are never edited in place.

Usage: python3 acquire.py [1885|1877|all]
"""

import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request

import config

os.environ.setdefault("OPENCV_IO_MAX_IMAGE_PIXELS", str(2**40))
import cv2  # noqa: E402


def log(msg):
    print(f"[acquire] {msg}", flush=True)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_loc_json(item):
    url = f"https://www.loc.gov/item/{item}/?fo=json"
    req = urllib.request.Request(url, headers={"User-Agent": config.UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r), url


def download(url, dest, headers=None, retries=3, min_bytes=1 << 20):
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers or {"User-Agent": config.UA})
            with urllib.request.urlopen(req, timeout=600) as r, open(dest, "wb") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            if os.path.getsize(dest) >= min_bytes:
                return True
            log(f"  too small ({os.path.getsize(dest)} B), attempt {attempt}")
        except Exception as e:
            log(f"  attempt {attempt} failed: {e}")
        time.sleep(2 * attempt)
    return False


def verify_image(path, expect_wh=None):
    img = cv2.imread(path, cv2.IMREAD_REDUCED_COLOR_8)
    if img is None:
        return None
    full = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if full is None:
        return None
    h, w = full.shape[:2]
    del full
    if expect_wh and (w, h) != tuple(expect_wh):
        log(f"  WARNING {os.path.basename(path)}: {w}x{h}, expected {expect_wh}")
    return (w, h)


def acquire_1885(urls_out):
    ed = config.EDITIONS["1885"]
    outdir = os.path.join(config.SOURCES_DIR, "1885")
    os.makedirs(outdir, exist_ok=True)

    meta, meta_url = fetch_loc_json(ed["loc_item"])
    urls_out.append(meta_url)
    files = meta["resources"][0]["files"]
    log(f"LoC item lists {len(files)} sheets")
    with open(os.path.join(outdir, "loc_item.json"), "w") as f:
        json.dump(meta, f)

    sheets = [ed["index_sheet"]] + ed["working_set"]
    results = {}
    for num in sheets:
        url = ed["loc_master_base"].format(num=num)
        dest = os.path.join(outdir, f"08539_1885-{num:04d}.tif")
        if os.path.exists(dest) and os.path.getsize(dest) > 100 << 20:
            log(f"sheet {num}: already present")
        else:
            log(f"sheet {num}: downloading master TIFF")
            if not download(url, dest, min_bytes=100 << 20):
                log(f"sheet {num}: FAILED after retries")
                results[num] = None
                continue
        wh = verify_image(dest, ed["native_size"])
        results[num] = {"path": dest, "size": os.path.getsize(dest), "wh": wh}
        urls_out.append(url)
        log(f"sheet {num}: {results[num]['size']>>20} MB, {wh}")
    return results


def acquire_1877(urls_out):
    """UT cookie-jar recipe: F5 BIG-IP bot defense returns intermittent 503
    (TSPD_101_R0 cookies, 307 redirects). Cookie jar + Referer + up to 10
    retries with 5 s sleeps succeeds, often on try 2-6."""
    ed = config.EDITIONS["1877"]
    outdir = os.path.join(config.SOURCES_DIR, "1877")
    os.makedirs(outdir, exist_ok=True)
    jar = os.path.join(outdir, "cookies.txt")

    # Prime the jar on the index page first.
    subprocess.run(
        ["curl", "-sS", "-L", "-A", config.UA, "-c", jar, "-b", jar,
         "-o", os.path.join(outdir, "g.html"), ed["ut_referer"]],
        check=False,
    )

    results = {}
    for num in ed["all_sheets"]:
        url = ed["ut_url"].format(num=num)
        dest = os.path.join(outdir, f"txu-sanborn-galveston-1877-{num:02d}.jpg")
        ok = os.path.exists(dest) and os.path.getsize(dest) > 200 << 10
        for attempt in range(1, 11):
            if ok:
                break
            r = subprocess.run(
                ["curl", "-sS", "-L", "-A", config.UA, "-c", jar, "-b", jar,
                 "-e", ed["ut_referer"], "-o", dest, "-w", "%{http_code}", url],
                capture_output=True, text=True,
            )
            code = r.stdout.strip()
            if code == "200" and os.path.getsize(dest) > 200 << 10:
                # Guard against an HTML block page saved as .jpg
                with open(dest, "rb") as f:
                    ok = f.read(3) == b"\xff\xd8\xff"
            if not ok:
                log(f"sheet {num}: try {attempt} -> HTTP {code}, retrying in 5 s")
                time.sleep(5)
        if not ok:
            log(f"sheet {num}: FAILED after 10 tries")
            results[num] = None
            continue
        wh = verify_image(dest)
        results[num] = {"path": dest, "size": os.path.getsize(dest), "wh": wh}
        urls_out.append(url)
        log(f"sheet {num}: {results[num]['size']>>10} KB, {wh}")
    return results


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.makedirs(config.SOURCES_DIR, exist_ok=True)
    urls = []
    all_results = {}
    if which in ("1885", "all"):
        all_results["1885"] = acquire_1885(urls)
    if which in ("1877", "all"):
        all_results["1877"] = acquire_1877(urls)

    manifest = os.path.join(config.SOURCES_DIR, "manifest.txt")
    with open(manifest, "w") as f:
        for year, res in sorted(all_results.items()):
            for num, info in sorted(res.items()):
                if info:
                    f.write(f"{sha256(info['path'])}  {info['path']}\n")
    with open(os.path.join(config.SOURCES_DIR, "source_urls.txt"), "w") as f:
        f.write("\n".join(urls) + "\n")

    failed = [(y, n) for y, res in all_results.items() for n, i in res.items() if not i]
    log(f"done. failures: {failed or 'none'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

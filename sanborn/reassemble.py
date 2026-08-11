"""Pull the sanborn-data branch, reassemble chunked TIFFs, verify checksums.

Usage: python3 reassemble.py
Places verified originals under config.SOURCES_DIR/{1877,1885}/ and writes
sources/manifest.txt combining both years. Exits nonzero on any mismatch.
"""

import hashlib
import os
import shutil
import subprocess
import sys

import config

REPO = "/home/user/claude-code"
WORKTREE = os.path.join(config.WORK_ROOT, "sanborn-data-checkout")


def sh(*cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, capture_output=True, **kw)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    os.makedirs(config.WORK_ROOT, exist_ok=True)
    sh("git", "-C", REPO, "fetch", "origin", "sanborn-data")
    if os.path.exists(WORKTREE):
        sh("git", "-C", REPO, "worktree", "remove", "--force", WORKTREE)
    sh("git", "-C", REPO, "worktree", "add", "--force", WORKTREE, "origin/sanborn-data")

    src_root = os.path.join(WORKTREE, "sources")
    if os.path.exists(os.path.join(src_root, "FETCH_BLOCKED.txt")):
        print("FETCH_BLOCKED reported by fetcher session:")
        print(open(os.path.join(src_root, "FETCH_BLOCKED.txt")).read())
        return 2

    failures = []
    combined = []
    for year in ("1877", "1885"):
        srcdir = os.path.join(src_root, year)
        outdir = os.path.join(config.SOURCES_DIR, year)
        os.makedirs(outdir, exist_ok=True)
        if not os.path.isdir(srcdir):
            print(f"{year}: no directory on data branch")
            continue

        # Reassemble chunked files: foo.tif.part-aa + ... -> foo.tif
        bases = sorted({f.split(".part-")[0] for f in os.listdir(srcdir) if ".part-" in f})
        for base in bases:
            parts = sorted(p for p in os.listdir(srcdir) if p.startswith(base + ".part-"))
            dest = os.path.join(outdir, base)
            with open(dest, "wb") as out:
                for p in parts:
                    with open(os.path.join(srcdir, p), "rb") as f:
                        shutil.copyfileobj(f, out)
        # Plain files
        for f in os.listdir(srcdir):
            if ".part-" not in f and not f.endswith(".json"):
                shutil.copy2(os.path.join(srcdir, f), os.path.join(outdir, f))
        for f in os.listdir(srcdir):
            if f.endswith(".json"):
                shutil.copy2(os.path.join(srcdir, f), os.path.join(outdir, f))

        manifest = os.path.join(src_root, f"manifest_{year}.txt")
        if not os.path.exists(manifest):
            print(f"{year}: manifest missing — cannot verify")
            failures.append((year, "manifest missing"))
            continue
        for line in open(manifest):
            want, name = line.split()
            name = os.path.basename(name)
            local = os.path.join(outdir, name)
            if not os.path.exists(local):
                failures.append((year, f"{name} missing"))
                print(f"{year} {name}: MISSING")
                continue
            got = sha256(local)
            ok = got == want
            print(f"{year} {name}: {'OK' if ok else 'SHA MISMATCH'}")
            if not ok:
                failures.append((year, f"{name} sha mismatch"))
            else:
                combined.append(f"{got}  {local}")

    os.makedirs(config.SOURCES_DIR, exist_ok=True)
    with open(os.path.join(config.SOURCES_DIR, "manifest.txt"), "w") as f:
        f.write("\n".join(combined) + "\n")
    urls = os.path.join(src_root, "source_urls.txt")
    if os.path.exists(urls):
        shutil.copy2(urls, os.path.join(config.SOURCES_DIR, "source_urls.txt"))

    print(f"\nverified files: {len(combined)}; failures: {failures or 'none'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

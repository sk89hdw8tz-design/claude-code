"""Guard-metric suite. Run on EVERY build; compare before/after every change.

In the prior 1899 build an untested cleanup dropped source coverage from
98.98% to 90.85% and nothing caught it until a later inspection. These are
cheap; run them every time.

Usage:
    python3 build_metrics.py composite.png coverage_mask.png [baseline.json]

Emits JSON to stdout and, when a baseline is given, a pass/fail per metric.
"""
import json
import sys

import cv2
import numpy as np

cv2.setNumThreads(0)

# Direction each metric must move. "max" = lower is better.
GUARDS = {
    "coverage_pct": "min",
    "pure_white_px": "max",
    "pure_black_pct": "max",
}


def measure(comp_path, mask_path):
    img = cv2.imread(comp_path, cv2.IMREAD_COLOR)
    if img is None:
        raise IOError(comp_path)
    flat = img.reshape(-1, 3)
    n = flat.shape[0]
    m = {
        "size": [int(img.shape[1]), int(img.shape[0])],
        "megapixels": round(n / 1e6, 1),
        "pure_white_px": int((flat == 255).all(axis=1).sum()),
        "pure_black_px": int((flat.max(axis=1) == 0).sum()),
    }
    m["pure_black_pct"] = round(100.0 * m["pure_black_px"] / n, 4)
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    if mask is not None:
        # The composite is usually a CROP of a larger canvas while the mask
        # covers the whole canvas; comparing them directly reports nonsense
        # (34.7% instead of 99.0%). Pass --crop x0,y0,x1,y1 to align them.
        sub = mask
        if "--crop" in sys.argv:
            x0, y0, x1, y1 = [int(v) for v in
                              sys.argv[sys.argv.index("--crop") + 1].split(",")]
            sub = mask[y0:y1, x0:x1]
        elif mask.shape[:2] != img.shape[:2]:
            raise SystemExit(
                f"mask {mask.shape[1]}x{mask.shape[0]} does not match composite "
                f"{img.shape[1]}x{img.shape[0]} — pass --crop x0,y0,x1,y1")
        m["coverage_pct"] = round(100.0 * float((sub > 0).mean()), 2)
    # paper-tone step across the image, a proxy for visible banding
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    rows = g[::64, ::8].mean(axis=1)
    m["row_tone_max_jump"] = round(float(np.abs(np.diff(rows)).max()), 2)
    return m


def main(comp, mask, baseline=None):
    m = measure(comp, mask)
    print(json.dumps(m, indent=1))
    if not baseline:
        return 0
    base = json.load(open(baseline))
    bad = []
    print("\nvs baseline:")
    for k, direction in GUARDS.items():
        if k not in m or k not in base:
            continue
        now, was = m[k], base[k]
        ok = now >= was if direction == "min" else now <= was
        print(f"  {k:20} {was!r:>12} -> {now!r:>12}  {'OK' if ok else 'REGRESSED'}")
        if not ok:
            bad.append(k)
    if bad:
        print(f"\nREGRESSED: {bad} — reject this change")
        return 1
    print("\nno guard metric regressed")
    return 0


if __name__ == "__main__":
    pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    skip = set()
    for i, a in enumerate(sys.argv):
        if a == "--crop" and i + 1 < len(sys.argv):
            skip.add(sys.argv[i + 1])
    pos = [a for a in pos if a not in skip]
    sys.exit(main(*pos[:3]))

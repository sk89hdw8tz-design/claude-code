"""Detect street (horizontal) and avenue (vertical) corridors in a 1912
working copy from its long block-outline lines.

Block outlines are long straight strokes; text, lot ticks and buildings are
not. A morphological opening with a long line kernel keeps only the
outlines, whose row (column) projection peaks at block edges. A corridor is
the gap between two facing edges ~150-330 px apart (pct:50 scans) with
little line-ink between; block interiors are ~800 px deep, so the two are
separable by gap width alone.
"""
import cv2, numpy as np

def line_profile(gray, rect, axis, klen=220):
    x0, y0, x1, y1 = rect
    sub = gray[y0:y1, x0:x1]
    bg = np.median(sub)
    ink = (sub < bg - 40).astype(np.uint8)
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (klen, 1) if axis == "h" else (1, klen))
    lines = cv2.morphologyEx(ink, cv2.MORPH_OPEN, k)
    p = lines.sum(axis=1) if axis == "h" else lines.sum(axis=0)
    p = np.convolve(p.astype(np.float32), np.ones(5) / 5, mode="same")
    return p, (y0 if axis == "h" else x0)

def edge_peaks(p, min_len=250, merge=12):
    peaks = []
    for i in range(2, len(p) - 2):
        if p[i] >= min_len and p[i] == p[i-2:i+3].max():
            if peaks and i - peaks[-1][0] < merge:
                if p[i] > peaks[-1][1]:
                    peaks[-1] = (i, p[i])
            else:
                peaks.append((i, float(p[i])))
    return peaks

def corridors(gray, rect, axis, gap=(150, 340), min_len=250):
    """Native coordinates of corridor centre lines along the axis, with the
    two bounding edge coordinates and the edge strengths."""
    p, base = line_profile(gray, rect, axis)
    pk = edge_peaks(p, min_len)
    out = []
    for (a, va), (b, vb) in zip(pk, pk[1:]):
        w = b - a
        if gap[0] <= w <= gap[1]:
            inner = p[a + 20:b - 20]
            if len(inner) == 0 or inner.max() < 0.5 * min(va, vb):
                out.append({"c": base + (a + b) / 2.0, "lo": base + a, "hi": base + b,
                            "w": int(w), "s": float(min(va, vb))})
    # a corridor may be bounded by doubled lines (sidewalk + curb): merge within 120 px
    merged = []
    for c in out:
        if merged and c["c"] - merged[-1]["c"] < 120:
            if c["s"] > merged[-1]["s"]:
                merged[-1] = c
        else:
            merged.append(c)
    return merged

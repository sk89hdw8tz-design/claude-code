#!/usr/bin/env python
"""Column / row darkness profiles for precise line location on Sanborn sheets.

Usage:
  python _profile.py col SHEET X0 X1 Y0 Y1     -> per-column mean darkness
  python _profile.py row SHEET X0 X1 Y0 Y1     -> per-row mean darkness
Prints index, darkness (0-255, higher = darker) for every index, and a list of
local maxima (candidate ink lines) with sub-pixel centroids.
"""
import sys, os
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

ROOT = '/home/user/claude-code/galveston-1889-sanborn'
SRC = os.path.join(ROOT, 'data', 'original', 'txu-sanborn-galveston-1889-Sheet {}.jpg')


def load(sheet):
    return np.asarray(Image.open(SRC.format(sheet)).convert('L'), dtype=np.float32)


def main():
    mode, sheet = sys.argv[1], sys.argv[2]
    x0, x1, y0, y1 = [int(v) for v in sys.argv[3:7]]
    thr = float(sys.argv[7]) if len(sys.argv) > 7 else 0.35
    a = load(sheet)[y0:y1, x0:x1]
    dark = 255.0 - a
    if mode == 'col':
        prof = dark.mean(axis=0)
        base = x0
    else:
        prof = dark.mean(axis=1)
        base = y0
    lo = np.percentile(prof, 20)
    prof2 = prof - lo
    peak = prof2.max()
    print('# base=%d n=%d floor=%.1f peak=%.1f' % (base, len(prof), lo, peak))
    for i, v in enumerate(prof):
        print('%d %.1f' % (base + i, v))
    # local maxima above thr*peak, with 3-point centroid
    print('# PEAKS (centroid over contiguous run above %.2f*peak)' % thr)
    m = prof2 > thr * peak
    i = 0
    while i < len(m):
        if m[i]:
            j = i
            while j < len(m) and m[j]:
                j += 1
            w = prof2[i:j]
            c = base + i + (w * np.arange(len(w))).sum() / w.sum()
            print('PEAK %.2f width=%d maxval=%.1f' % (c, j - i, prof2[i:j].max()))
            i = j
        else:
            i += 1


main()

#!/usr/bin/env python
"""Measure block corners on the Av. D property lines at each cross-street, S7 & S8."""
import numpy as np, os
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
ROOT = '/home/user/claude-code/galveston-1889-sanborn'
SRC = os.path.join(ROOT, 'data', 'original', 'txu-sanborn-galveston-1889-Sheet {}.jpg')
IMG = {s: np.asarray(Image.open(SRC.format(s)).convert('L'), dtype=np.float32) for s in ('7', '8')}


def peaks(sheet, mode, x0, x1, y0, y1, thr=0.35):
    a = 255.0 - IMG[sheet][y0:y1, x0:x1]
    prof = a.mean(axis=0) if mode == 'col' else a.mean(axis=1)
    base = x0 if mode == 'col' else y0
    p = prof - np.percentile(prof, 20)
    pk = p.max()
    out, m, i = [], p > thr * pk, 0
    while i < len(m):
        if m[i]:
            j = i
            while j < len(m) and m[j]:
                j += 1
            w = p[i:j]
            out.append((base + i + float((w * np.arange(len(w))).sum() / w.sum()), j - i, float(w.max())))
            i = j
        else:
            i += 1
    return out


LAT = [
    # name,           S7 street-y win,      S7 AvD-x win,      S8 street-y win,      S8 AvD-x win
    ('19th St N line', (3010, 3105, 110, 165), (3085, 3160, 55, 128), (300, 400, 78, 132), (262, 330, 25, 96)),
    ('19th St S line', (3010, 3105, 355, 408), (3085, 3160, 396, 500), (300, 400, 325, 378), (262, 330, 362, 462)),
    ('20th St N line', (3010, 3105, 1272, 1322), (3085, 3160, 1195, 1288), (300, 400, 1250, 1302), (262, 330, 1175, 1268)),
    ('21st St N line', (3010, 3105, 2432, 2482), (3085, 3160, 2350, 2448), (300, 400, 2412, 2462), (262, 330, 2328, 2430)),
    ('21st St S line', (3010, 3105, 2678, 2726), (3085, 3160, 2732, 2812), (300, 400, 2658, 2712), (262, 330, 2700, 2790)),
    ('22nd St N line', (3010, 3105, 3592, 3642), (3085, 3160, 3505, 3602), (300, 400, 3584, 3634), (262, 330, 3495, 3598)),
    ('22nd St S line', (3010, 3105, 3838, 3888), (3085, 3160, 3878, 3962), (300, 400, 3828, 3878), (262, 330, 3866, 3950)),
]

for name, s7y, s7x, s8y, s8x in LAT:
    print('==', name)
    print('   S7 street-y :', ['%.2f w%d v%.0f' % p for p in peaks('7', 'row', *s7y)])
    print('   S7 AvD_W  x :', ['%.2f w%d v%.0f' % p for p in peaks('7', 'col', *s7x)])
    print('   S8 street-y :', ['%.2f w%d v%.0f' % p for p in peaks('8', 'row', *s8y)])
    print('   S8 AvD_E  x :', ['%.2f w%d v%.0f' % p for p in peaks('8', 'col', *s8x)])

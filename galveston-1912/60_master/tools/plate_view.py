#!/usr/bin/env python
"""Warp ONE block sheet into a canvas window, so a plate can be read on its own.

Diagnostic only: nothing is written into the repo and no archival scan is
modified. Used to see what each plate actually letters at a pooled cut, which
the composite cannot show once the cut has sliced it.

  plate_view.py --sheet 9 --rect x0 y0 x1 y1 --out /path/out.jpg
"""
import argparse, os, sys
import numpy as np, cv2, json

ROOT = '/home/user/claude-code/galveston-1912'
sys.path.insert(0, f'{ROOT}/50_seams')
import seamlib as sl

CX0, CY0 = -16734, -8279


def plate_crop(sheet, x0, y0, x1, y1, transforms=f'{ROOT}/40_solve/output/transforms.json'):
    raw, _ = sl.load_transforms(transforms)
    inv_items, _ = sl.load_inventory()
    T = raw[int(sheet)]
    item = inv_items[int(sheet)]
    img = cv2.imread(item['path'], cv2.IMREAD_COLOR)
    if img is None:
        raise SystemExit(f'decode failure for sheet {sheet}: {item["path"]}')
    M = sl.warp_matrix(T, origin=(CX0, CY0), scale=1.0)   # sheet px -> canvas px
    M = M.copy(); M[0, 2] -= x0; M[1, 2] -= y0
    out = cv2.warpAffine(img, M, (x1 - x0, y1 - y0), flags=cv2.INTER_LANCZOS4,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 0, 255))
    return out[:, :, ::-1]                                 # RGB


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--sheet', type=int, required=True)
    ap.add_argument('--rect', type=int, nargs=4, required=True,
                    metavar=('X0', 'Y0', 'X1', 'Y1'), help='canvas rect')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    c = plate_crop(a.sheet, *a.rect)
    cv2.imwrite(a.out, c[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 94])
    cov = float((c != np.array([255, 0, 255])).any(axis=2).mean())
    print(f'sheet {a.sheet} canvas {a.rect} -> {a.out}  coverage {cov*100:.1f}% '
          f'(magenta = off-plate)')

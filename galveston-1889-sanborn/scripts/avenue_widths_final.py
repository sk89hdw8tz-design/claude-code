#!/usr/bin/env python3
"""FINAL measurement of drawn avenue widths + grid-pitch scale, all 8 sheets.

Line convention
---------------
A frontage line's position is the HALF-MAX CROSSING MIDPOINT of the
baseline-subtracted mean-darkness profile across it, computed over a row band
several hundred rows tall.  Half-max midpoint rather than centroid: the heavy
line very often has a thin lot line or a column of address numerals a few px to
one side, which drags a centroid but not a half-max midpoint.

A candidate is accepted as the heavy continuous FRONTAGE line only if it is
(a) the strongest peak on its side of the roadway in a profile that is the
MEDIAN over many separated bands, and (b) CONTINUOUS -- some pixel within +/-4
px is darker than 120 on >=85% of rows.  The dashed awning/gallery edge, which
runs ~40 px (13-15 ft) inside the roadway, scores 0.35-0.70 on that test and is
rejected.  Every accepted line was also confirmed visually on an upscaled crop
carrying a 1-source-pixel grid.

Scale convention
----------------
px/ft comes ONLY from the plat's fixed grid pitch, never from a printed width:
  x: spacing of the SAME-SIDE frontage lines of consecutive avenues.
     west_k -> west_k+1 = block depth + width(avenue k)
     east_k -> east_k+1 = block depth + width(avenue k+1)
     so an interval is exactly 260+70 = 330 ft when the avenue whose width
     enters it is a 70 ft one.  Intervals governed by Av. B (Strand, 80 ft) are
     340 ft and are EXCLUDED rather than mislabelled 330.
  y: spacing of the same-side frontage lines of consecutive numbered streets,
     = 300 + 80 = 380 ft for every pair (all numbered streets are 80 ft).
"""
import os
import sys
import json
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from av_measure import gray, shape, CROPS, ROOT, find_line_halfmax, continuity
from measure_avenue_widths import (SPEC, FULLNAME, PRINTED, PRINTED_STREET,
                                   block_bands, group_bands, _cands_in, track, val)

# printed-width class of each avenue: the plat step that a same-side interval
# spans is 260 + (width of the governing avenue)
CLASS_FT = {'A': 70, 'B': 80, 'C': 70, 'D': 70, 'E': 70, 'F': 70,
            'G': 70, 'H': 70, 'I': 70, 'J': 150}

SCALEBAR = {'1': 3.0297, '2': 3.0576, '7': 3.0570, '8': 3.0269,
            '9': 3.0295, '10': 3.0487, '27': 3.0735, '29': 3.0397}

# Which single frontage line an edge avenue draws, established by reading the
# sheet's own "SEE SHEET No. N" caption and confirmed on crops (see report).
EDGE_SIDE = {
    ('1', 'A'): 'west', ('2', 'A'): 'west',
    ('7', 'A'): 'east', ('7', 'D'): 'west',
    ('8', 'D'): 'east', ('8', 'G'): 'west',
    ('9', 'A'): 'east', ('9', 'D'): 'west',
    ('10', 'D'): 'east', ('10', 'G'): 'west',
    ('27', 'G'): 'east', ('27', 'J'): 'west',
    ('29', 'G'): 'east', ('29', 'J'): 'west',
}
# Avenue A on sheets 1, 2, 7, 9 lies in the harbour front and its roadway is
# full of railroad track pairs that pass the continuity test; its frontage is
# therefore taken from the explicit seed below rather than from peak strength.
SEED = {
    ('7', 'A', 'east'): 349.0, ('9', 'A', 'east'): 324.0,
    ('1', 'A', 'west'): 2959.0, ('2', 'A', 'west'): 3147.0,
}

YREF, XREF = 2000.0, 1700.0


def all_bands(n, axis):
    sp = SPEC[n]
    h, w = shape(n)
    if axis == 'v':
        return block_bands(sorted(sp['streets'].values()), h, nper=6, half_road=150)
    b = block_bands(sorted(sp['avenues'].values()), w, nper=6, half_road=150)
    return [x for x in b if x[0] >= sp.get('xmin', 0) + 20]


def locate(n, key, nominal, axis, halfwin, sides_wanted):
    """Return {'west'/'east' (or 'north'/'south'): fit} for one avenue/street."""
    bands = all_bands(n, axis)
    lo_name, hi_name = ('west', 'east') if axis == 'v' else ('north', 'south')
    out, chosen = {}, {}
    # coarse pick, per short group of bands so tilt cannot smear the peak
    votes = {lo_name: [], hi_name: []}
    for grp in group_bands(bands):
        ps = _cands_in(n, nominal, halfwin, grp, axis)
        for side, sel in ((lo_name, lambda p: p['x'] < nominal - 25),
                          (hi_name, lambda p: p['x'] > nominal + 25)):
            c = [p for p in ps if sel(p) and p['cont'] >= 0.85 and p['v'] >= 75]
            if c:
                votes[side].append(max(c, key=lambda p: p['v']))
    for side in sides_wanted:
        s = SEED.get((n, key, side))
        if s is None:
            if not votes[side]:
                continue
            # the frontage is the candidate the bands agree on; take the median
            s = float(np.median([p['x'] for p in votes[side]]))
        f = track(n, s, bands, axis=axis, ref=(YREF if axis == 'v' else XREF),
                  half=10, minpeak=40.0)
        if f:
            out[side] = f
            chosen[side] = s
    return out, chosen


def measure(n):
    sp = SPEC[n]
    h, w = shape(n)
    R = {'sheet': n, 'size': [w, h], 'avenues': {}, 'streets': {}}

    for name, x0 in sorted(sp['avenues'].items(), key=lambda kv: kv[1]):
        halfwin = 300 if name == 'J' else 200
        edge = EDGE_SIDE.get((n, name))
        want = [edge] if edge else ['west', 'east']
        fits, seeds = locate(n, name, x0, 'v', halfwin, want)
        e = {'printed_ft': PRINTED[name], 'both_frontages': edge is None,
             'lines': {}, 'seeds': seeds}
        for s, f in fits.items():
            e['lines'][s] = f
        if 'west' in fits and 'east' in fits:
            wpx = {}
            for y in (1000, 2000, 3000):
                wpx[str(y)] = round(val(fits['east'], y) - val(fits['west'], y), 3)
            e['width_px_at_y'] = wpx
            e['mean_width_px'] = round(float(np.mean(list(wpx.values()))), 3)
            # per-band widths -> honest spread
            pw = []
            for p in fits['west']['pts']:
                y = p[0]
                q = [r for r in fits['east']['pts'] if abs(r[0] - y) < 1e-6]
                if q:
                    pw.append(q[0][1] - p[1])
            if pw:
                e['per_band_widths'] = [round(v, 2) for v in pw]
                e['width_spread_px'] = round(float(max(pw) - min(pw)), 2)
                e['width_sd_px'] = round(float(np.std(pw)), 3)
        R['avenues'][name] = e

    for name, y0 in sorted(sp['streets'].items(), key=lambda kv: kv[1]):
        fits, seeds = locate(n, name, y0, 'h', 200, ['north', 'south'])
        e = {'printed_ft': PRINTED_STREET, 'lines': {}, 'seeds': seeds}
        for s, f in fits.items():
            e['lines'][s] = f
        if 'north' in fits and 'south' in fits:
            wpx = {}
            for x in (600, 1700, 2800):
                wpx[str(x)] = round(val(fits['south'], x) - val(fits['north'], x), 3)
            e['width_px_at_x'] = wpx
            e['mean_width_px'] = round(float(np.mean(list(wpx.values()))), 3)
        R['streets'][name] = e
    return R


# ------------------------------------------------------------------ scales

def scales(R):
    n = R['sheet']
    av = sorted(SPEC[n]['avenues'].items(), key=lambda kv: kv[1])
    st = sorted(SPEC[n]['streets'].items(), key=lambda kv: kv[1])

    xint = []
    for (k1, _), (k2, _) in zip(av[:-1], av[1:]):
        a, b = R['avenues'][k1], R['avenues'][k2]
        # west->west spans block + width(k1);  east->east spans block + width(k2)
        for side, gov in (('west', k1), ('east', k2)):
            if side in a['lines'] and side in b['lines'] and CLASS_FT[gov] == 70:
                d = val(b['lines'][side], YREF) - val(a['lines'][side], YREF)
                xint.append({'from': k1, 'to': k2, 'side': side, 'px': round(d, 3),
                             'plat_ft': 330, 'px_per_ft': round(d / 330.0, 5)})
    yint = []
    for (k1, _), (k2, _) in zip(st[:-1], st[1:]):
        a, b = R['streets'][k1], R['streets'][k2]
        for side in ('north', 'south'):
            if side in a['lines'] and side in b['lines']:
                d = val(b['lines'][side], XREF) - val(a['lines'][side], XREF)
                yint.append({'from': k1, 'to': k2, 'side': side, 'px': round(d, 3),
                             'plat_ft': 380, 'px_per_ft': round(d / 380.0, 5)})
    sx = float(np.mean([i['px_per_ft'] for i in xint])) if xint else None
    sy = float(np.mean([i['px_per_ft'] for i in yint])) if yint else None
    R['grid'] = {
        'x_intervals': xint, 'y_intervals': yint,
        'px_per_ft_from_grid_x': round(sx, 4) if sx else None,
        'px_per_ft_from_grid_y': round(sy, 4) if sy else None,
        'x_sd': round(float(np.std([i['px_per_ft'] for i in xint])), 5) if len(xint) > 1 else None,
        'y_sd': round(float(np.std([i['px_per_ft'] for i in yint])), 5) if len(yint) > 1 else None,
        'anisotropy_pct': round(200.0 * (sy - sx) / (sy + sx), 3) if (sx and sy) else None,
        'scalebar_px_per_ft': SCALEBAR[n],
    }
    return R


# --------------------------------------------------------------------- QC

def qc_panel(R, name, y0=1750, y1=2150, pad=60):
    """Crop the avenue with the accepted frontage lines marked, at 3x."""
    n = R['sheet']
    e = R['avenues'][name]
    if not e['lines']:
        return None
    xs = [val(f, 0.5 * (y0 + y1)) for f in e['lines'].values()]
    x0 = int(min(xs) - pad); x1 = int(max(xs) + pad)
    g = gray(n)
    h, w = g.shape
    x0 = max(0, x0); x1 = min(w, x1)
    a = g[y0:y1, x0:x1].astype(np.uint8)
    z = 3
    im = Image.fromarray(a).convert('RGB').resize(((x1 - x0) * z, (y1 - y0) * z), Image.NEAREST)
    d = ImageDraw.Draw(im)
    for sd, f in e['lines'].items():
        col = (255, 0, 0) if sd == 'west' else (0, 140, 255)
        for yy in range(y0, y1, 2):
            xx = (val(f, yy) - x0) * z
            d.line([(xx, (yy - y0) * z), (xx, (yy - y0 + 1) * z)], fill=col, width=1)
    out = os.path.join(CROPS, f'QC_S{n}_Av{name}.png')
    im.save(out)
    return out


if __name__ == '__main__':
    allR = {}
    for n in (sys.argv[1:] or list(SPEC)):
        R = scales(measure(n))
        allR[n] = R
        g = R['grid']
        print(f"===== sheet {n}   px/ft grid x={g['px_per_ft_from_grid_x']} "
              f"y={g['px_per_ft_from_grid_y']}  aniso={g['anisotropy_pct']}%  "
              f"scalebar={g['scalebar_px_per_ft']}")
        for i in g['x_intervals']:
            print(f"    X {i['from']}->{i['to']:2s} {i['side']:5s} {i['px']:9.2f} px /330ft = {i['px_per_ft']:.4f}")
        for i in g['y_intervals']:
            print(f"    Y {i['from']}->{i['to']:5s} {i['side']:5s} {i['px']:9.2f} px /380ft = {i['px_per_ft']:.4f}")
        for k, e in R['avenues'].items():
            if 'mean_width_px' in e:
                sx = g['px_per_ft_from_grid_x'] or g['scalebar_px_per_ft']
                print(f"  AV {k} printed {e['printed_ft']}ft  width {e['mean_width_px']:8.2f} px"
                      f"  at y {e['width_px_at_y']}  spread {e.get('width_spread_px')}"
                      f"  -> {e['mean_width_px']/sx:6.2f} ft (grid-x)"
                      f"  {e['mean_width_px']/g['scalebar_px_per_ft']:6.2f} ft (scalebar)")
            else:
                sides = ','.join(e['lines'].keys())
                print(f"  AV {k} printed {e['printed_ft']}ft  ONE FRONTAGE ONLY [{sides}]")
        for k, e in R['streets'].items():
            if 'mean_width_px' in e:
                print(f"  ST {k:5s} width {e['mean_width_px']:8.2f} px  at x {e['width_px_at_x']}")
            else:
                print(f"  ST {k:5s} incomplete [{','.join(e['lines'].keys())}]")
    with open(os.path.join(ROOT, 'working', 'avenue_widths_final_raw.json'), 'w') as f:
        json.dump(allR, f, indent=1)
    print('\nwrote working/avenue_widths_final_raw.json')

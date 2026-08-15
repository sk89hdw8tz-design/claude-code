#!/usr/bin/env python3
"""Measure the DRAWN width of every lettered avenue (heavy frontage line to
heavy frontage line) on every sheet where both frontages are inked.

No printed width is used anywhere in the scale derivation: px/ft comes only
from the Galveston plat's fixed grid pitch (avenue centreline pitch 260+70=330 ft,
street centreline pitch 300+80=380 ft).

Everything runs locally on data/original. Nothing is uploaded.
"""
import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from av_measure import (gray, shape, crop, stack_profile, find_peaks_simple,
                        continuity, find_line_halfmax, CROPS, ROOT)

# ----------------------------------------------------------------- sheet spec
# Nominal positions are only SEEDS for the search; identity of every avenue was
# read from the printed lettering on the sheet (see AVENUE_LABELS).
SPEC = {
    '1':  dict(streets={'22nd': 15, '23rd': 1180, '24th': 2350, '25th': 3500},
               avenues={'A': 3075}, xmin=1568),
    '2':  dict(streets={'19th': 50, '20th': 1220, '21st': 2390, '22nd': 3563},
               avenues={'A': 3057}),
    '7':  dict(streets={'19th': 265, '20th': 1470, '21st': 2590, '22nd': 3740},
               avenues={'A': 240, 'B': 1243, 'C': 2236, 'D': 3230}),
    '8':  dict(streets={'19th': 220, '20th': 1393, '21st': 2570, '22nd': 3765},
               avenues={'D': 187, 'E': 1196, 'F': 2201, 'G': 3205}),
    '9':  dict(streets={'22nd': 290, '23rd': 1476, '24th': 2637, '25th': 3880},
               avenues={'A': 218, 'B': 1217, 'C': 2220, 'D': 3220}),
    '10': dict(streets={'22nd': 220, '23rd': 1389, '24th': 2557, '25th': 3728},
               avenues={'D': 191, 'E': 1202, 'F': 2212, 'G': 3218}),
    '27': dict(streets={'22nd': 240, '23rd': 1419, '24th': 2596, '25th': 3833},
               avenues={'G': 115, 'H': 1126, 'I': 2134, 'J': 3264}),
    '29': dict(streets={'19th': 240, '20th': 1412, '21st': 2582, '22nd': 3750},
               avenues={'G': 180, 'H': 1180, 'I': 2190, 'J': 3320}),
}

FULLNAME = {
    'A': 'Av. A or Water E.', 'B': 'Av. B or Strand E.',
    'C': 'Av. C or Mechanic E.', 'D': 'Av. D or Market E.',
    'E': 'Av. E or Post Office E.', 'F': 'Av. F or Church E.',
    'G': 'Av. G or Winnie E.', 'H': 'Av. H East', 'I': 'Av. I East',
    'J': 'Av. J or E. Broadway',
}

# printed widths, read off the sheets' own dimension figures (see read_printed_widths)
PRINTED = {'A': 70, 'B': 80, 'C': 70, 'D': 70, 'E': 70, 'F': 70,
           'G': 70, 'H': 70, 'I': 70, 'J': 150}
PRINTED_STREET = 80


# ---------------------------------------------------------------- utilities

def mid_bands(lo, hi, n, margin=0.10):
    """n bands spanning lo..hi, trimmed by `margin` of the span at each end so
    the bands sit inside the block and clear of the cross-street corners."""
    span = hi - lo
    a = lo + margin * span
    b = hi - margin * span
    step = (b - a) / n
    return [(int(a + i * step), int(a + (i + 1) * step)) for i in range(n)]


def block_bands(pos_sorted, extent, nper=4, half_road=130):
    """Row (or column) bands lying between consecutive cross-line positions."""
    out = []
    for p, q in zip(pos_sorted[:-1], pos_sorted[1:]):
        lo, hi = p + half_road, q - half_road
        if hi - lo > 200:
            out += mid_bands(lo, hi, nper)
    # also the partial blocks at either end
    if pos_sorted:
        lo, hi = 40, pos_sorted[0] - half_road
        if hi - lo > 300:
            out += mid_bands(lo, hi, 2)
        lo, hi = pos_sorted[-1] + half_road, extent - 40
        if hi - lo > 300:
            out += mid_bands(lo, hi, 2)
    return out


def _cands_in(n, centre, halfwin, bands, axis, thresh=120):
    xs, v = stack_profile(n, centre, halfwin, bands, axis=axis)
    ps = find_peaks_simple(xs, v, minprom=8.0)
    t0 = min(b[0] for b in bands); t1 = max(b[1] for b in bands)
    g = gray(n)
    for p in ps:
        i = int(round(p['x']))
        if axis == 'v':
            a = g[t0:t1, max(0, i - 4):i + 5]
            p['cont'] = float((a.min(axis=1) < thresh).mean())
        else:
            a = g[max(0, i - 4):i + 5, t0:t1]
            p['cont'] = float((a.min(axis=0) < thresh).mean())
    return ps


def group_bands(bands, max_span=1000):
    """Split a band list into groups whose total span is short enough that the
    line's own tilt does not smear the stacked profile (a few px at most)."""
    groups, cur = [], []
    for b in bands:
        if cur and b[1] - cur[0][0] > max_span:
            groups.append(cur); cur = []
        cur.append(b)
    if cur:
        groups.append(cur)
    return [g for g in groups if len(g) >= 2]


def pick_frontages(n, centre, halfwin, bands, axis='v', vmin=90.0, contmin=0.85,
                   inner_gap=25):
    """Return (lo_line, hi_line, candidates) -- coarse positions of the two
    HEAVY CONTINUOUS lines bracketing `centre`.

    Selection is done inside one short group of bands at a time, so the line's
    tilt cannot smear the peak. Within a group the profile is the MEDIAN over
    the bands, which kills block detail, lettering and address numerals but
    keeps anything running the full height. The winner on each side is the
    strongest peak that is also CONTINUOUS: a dashed awning edge scores ~0.5-0.7
    on the continuity test and is rejected, which is the specific failure mode
    this project has already been bitten by.
    """
    best = None
    for grp in group_bands(bands):
        ps = _cands_in(n, centre, halfwin, grp, axis)
        lo = [p for p in ps if p['x'] < centre - inner_gap]
        hi = [p for p in ps if p['x'] > centre + inner_gap]

        def pick(c):
            c2 = [p for p in c if p['cont'] >= contmin and p['v'] >= vmin]
            return max(c2, key=lambda p: p['v']) if c2 else None
        a, b = pick(lo), pick(hi)
        if a and b:
            score = min(a['v'], b['v'])
            if best is None or score > best[0]:
                best = (score, a, b, ps, grp)
    if best is None:
        ps = _cands_in(n, centre, halfwin, bands, axis)
        return None, None, ps
    return best[1], best[2], best[3]


def scan(n, x0, bands, axis='v', half=10, minpeak=70.0, maxfwhm=6.0):
    """Detect the line in every band. Weak (peak<minpeak) or smeared
    (fwhm>maxfwhm) detections are dropped: those are places where the line runs
    behind lettering or fades at a block end, and they were the single largest
    source of slope error in an earlier pass."""
    pts, pred = [], x0
    for (t0, t1) in bands:
        r = find_line_halfmax(n, pred, t0, t1, half=half, axis=axis)
        if r is None:
            continue
        if len(pts) >= 3:
            ts = np.array([p[0] for p in pts[-6:]])
            cs = np.array([p[1] for p in pts[-6:]])
            b, a = np.polyfit(ts, cs, 1)
            nxt = a + b * (t1 + 0.5 * (t1 - t0))
            pred = nxt if abs(nxt - r['c']) < 40 else r['c']
        else:
            pred = r['c']
        if r['peak'] < minpeak or r['fwhm'] > maxfwhm:
            continue
        pts.append([0.5 * (t0 + t1), r['c'], r['peak'], r['fwhm']])
    return pts


def _theil_sen(ts, cs):
    sl = [(cs[j] - cs[i]) / (ts[j] - ts[i])
          for i in range(len(ts)) for j in range(i + 1, len(ts))
          if ts[j] != ts[i]]
    return float(np.median(sl)) if sl else 0.0


def fit_pts(pts, ref):
    """Theil-Sen start, MAD clip, then least squares. Robust to the handful of
    bands where the detector locks onto a neighbouring line."""
    if len(pts) < 3:
        return None
    ts = np.array([p[0] for p in pts]); cs = np.array([p[1] for p in pts])
    b0 = _theil_sen(ts, cs)
    r0 = cs - (b0 * (ts - ref) + np.median(cs - b0 * (ts - ref)))
    mad = max(1.4826 * np.median(np.abs(r0 - np.median(r0))), 0.4)
    keep = np.abs(r0 - np.median(r0)) <= 3.0 * mad
    if keep.sum() < 3:
        keep = np.ones(len(pts), bool)
    P = [p for p, k in zip(pts, keep) if k]
    ts = np.array([p[0] for p in P]); cs = np.array([p[1] for p in P])
    A = np.vstack([np.ones(len(ts)), ts - ref]).T
    sol, *_ = np.linalg.lstsq(A, cs, rcond=None)
    r = cs - A @ sol
    return {'a': float(sol[0]), 'b': float(sol[1]), 'ref': float(ref),
            'rms': float(np.sqrt((r ** 2).mean())), 'n': len(P),
            'tmin': float(ts.min()), 'tmax': float(ts.max()),
            'mean_peak': float(np.mean([p[2] for p in P])),
            'mean_fwhm': float(np.mean([p[3] for p in P])),
            'pts': [[round(p[0], 1), round(p[1], 3), round(p[2], 1), round(p[3], 2)] for p in P]}


def track(n, x0, bands, axis='v', ref=2000.0, half=10, minpeak=70.0):
    return fit_pts(scan(n, x0, bands, axis=axis, half=half, minpeak=minpeak), ref)


def val(f, t):
    return f['a'] + f['b'] * (t - f['ref'])


# ------------------------------------------------------------------- measure

def measure_sheet(n):
    sp = SPEC[n]
    h, w = shape(n)
    xmin = sp.get('xmin', 0)
    res = {'height': h, 'width': w, 'streets': {}, 'avenues': {}}

    st_y = sorted(sp['streets'].values())
    av_x = sorted(sp['avenues'].values())

    # ---- column bands used when measuring STREETS: inside blocks, away from
    #      avenue roadways, and (sheet 1) right panel only
    colb = block_bands(av_x, w, nper=4, half_road=140)
    colb = [b for b in colb if b[0] >= xmin + 20]
    if not colb:
        colb = [(xmin + 60, w - 60)]

    # ---- row bands used when measuring AVENUES
    rowb = block_bands(st_y, h, nper=4, half_road=150)

    # STREETS (near-horizontal): frontage pair -> width and centreline
    for name, y0 in sorted(sp['streets'].items(), key=lambda kv: kv[1]):
        lo, hi, cands = pick_frontages(n, y0, 190, colb, axis='h')
        entry = {'nominal': y0, 'candidates': [
            {'x': round(p['x'], 1), 'v': round(p['v'], 1), 'cont': round(p['cont'], 2)}
            for p in cands if p['v'] > 60]}
        if lo and hi:
            fa = track(n, lo['x'], colb, axis='h', ref=1700.0)
            fb = track(n, hi['x'], colb, axis='h', ref=1700.0)
            if fa and fb:
                entry['north'] = fa; entry['south'] = fb
                entry['width_px'] = round(val(fb, 1700.0) - val(fa, 1700.0), 3)
                entry['centre_at_ref'] = round(0.5 * (val(fa, 1700.0) + val(fb, 1700.0)), 3)
                entry['ok'] = True
        res['streets'][name] = entry

    # AVENUES (near-vertical)
    for name, x0 in sorted(sp['avenues'].items(), key=lambda kv: kv[1]):
        halfwin = 300 if name == 'J' else 190
        lo, hi, cands = pick_frontages(n, x0, halfwin, rowb, axis='v')
        entry = {'nominal': x0, 'candidates': [
            {'x': round(p['x'], 1), 'v': round(p['v'], 1), 'cont': round(p['cont'], 2)}
            for p in cands if p['v'] > 60]}
        if lo and hi:
            fa = track(n, lo['x'], rowb, axis='v', ref=2000.0)
            fb = track(n, hi['x'], rowb, axis='v', ref=2000.0)
            if fa and fb:
                entry['west'] = fa; entry['east'] = fb
                entry['width_px'] = round(val(fb, 2000.0) - val(fa, 2000.0), 3)
                entry['centre_at_ref'] = round(0.5 * (val(fa, 2000.0) + val(fb, 2000.0)), 3)
                entry['ok'] = True
        res['avenues'][name] = entry
    return res


if __name__ == '__main__':
    out = {}
    for n in (sys.argv[1:] or list(SPEC)):
        out[n] = measure_sheet(n)
        r = out[n]
        print(f'===== sheet {n}  {r["width"]}x{r["height"]}')
        for k, e in r['streets'].items():
            if e.get('ok'):
                print(f"  ST {k:5s} N={val(e['north'],1700):8.2f} S={val(e['south'],1700):8.2f}"
                      f"  w={e['width_px']:7.2f}  rms {e['north']['rms']:.2f}/{e['south']['rms']:.2f}"
                      f"  n {e['north']['n']}/{e['south']['n']}"
                      f"  slope {e['north']['b']:+.5f}/{e['south']['b']:+.5f}")
            else:
                print(f"  ST {k:5s} FAILED  cands={e['candidates'][:6]}")
        for k, e in r['avenues'].items():
            if e.get('ok'):
                print(f"  AV {k:5s} W={val(e['west'],2000):8.2f} E={val(e['east'],2000):8.2f}"
                      f"  w={e['width_px']:7.2f}  rms {e['west']['rms']:.2f}/{e['east']['rms']:.2f}"
                      f"  n {e['west']['n']}/{e['east']['n']}"
                      f"  slope {e['west']['b']:+.5f}/{e['east']['b']:+.5f}")
            else:
                print(f"  AV {k:5s} FAILED  cands={e['candidates'][:8]}")
    with open(os.path.join(ROOT, 'working', 'avenue_raw_measurements.json'), 'w') as f:
        json.dump(out, f, indent=1)

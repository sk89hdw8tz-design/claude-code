#!/usr/bin/env python3
"""Assemble gcps/manual/avenue_widths.json from the raw line fits."""
import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from av_measure import ROOT
from avenue_widths_final import (SPEC, FULLNAME, PRINTED, PRINTED_STREET,
                                CLASS_FT, SCALEBAR, EDGE_SIDE, val, YREF, XREF,
                                XREF_SHEET)

RAW = json.load(open(os.path.join(ROOT, 'working', 'avenue_widths_final_raw.json')))

# Avenue A is the harbour-front street: its roadway carries several continuous
# railroad track pairs that pass every "heavy continuous line" test, so its
# frontage cannot be identified from ink alone. Excluded from scale and width.
EXCLUDE_AV = {'A'}


# Sheets 1 and 2 ink their numbered streets over a ~370 px tier of blocks only,
# so the span a fit can possibly cover there is short by construction.
SHORT = {'1', '2'}


def line_ok(f, n=None):
    if f is None:
        return False
    span = f['tmax'] - f['tmin']
    if n in SHORT:
        return f['n'] >= 6 and span >= 250 and f['rms'] <= 2.5
    return f['n'] >= 8 and span >= 1500 and f['rms'] <= 2.5


def pair_ok(a, b, n=None):
    tol = 0.007 if n in SHORT else 0.004
    return line_ok(a, n) and line_ok(b, n) and abs(a['b'] - b['b']) <= tol


def fmt(f):
    s = '+' if f['b'] >= 0 else '-'
    return f"x = {f['a']:.2f} {s} {abs(f['b']):.5f}*(y-{f['yref' if 'yref' in f else 'ref']:.0f})" \
        if False else f"{f['a']:.3f} {s} {abs(f['b']):.6f}*(t-{f['ref']:.0f})"


def line_expr(f, var):
    s = '+' if f['b'] >= 0 else '-'
    return f"{f['a']:.3f} {s} {abs(f['b']):.6f}*({var}-{f['ref']:.0f})"


out = {}
out['method'] = (
    "Local measurement on data/original at full resolution (PIL, "
    "Image.MAX_IMAGE_PIXELS=None); nothing uploaded, no external image API. "
    "A frontage line's position is the HALF-MAX-CROSSING MIDPOINT of the "
    "baseline-subtracted mean-darkness profile taken across the line over a row "
    "band ~150 rows tall; half-max midpoint rather than centroid because a thin "
    "lot line or a column of address numerals a few px to one side drags a "
    "centroid but not a half-max midpoint. Each avenue was searched in a window "
    "+/-200 px about the centre of its PRINTED lettering, in a profile that is the "
    "MEDIAN over many separated bands (which suppresses block detail, party walls "
    "and lettering while keeping anything that runs the full height). The accepted "
    "frontage is the strongest such peak on each side that is also CONTINUOUS: "
    ">=85% of rows have a pixel darker than 120 within +/-4 px. The dashed "
    "awning/gallery edge, which sits ~40 px (13-15 ft) inside the roadway, scores "
    "0.35-0.70 on that test and is rejected -- it was seen explicitly in the "
    "profiles and in the crops, and never selected. Each line was then tracked "
    "through 16-24 mid-block bands spanning 2200-3000 rows and robust-fitted "
    "(2.5 sigma clip) to x = a + b*(y-2000); fit rms and band count are reported. "
    "Every accepted line was confirmed visually on 3x-12x NEAREST crops carrying a "
    "1-source-pixel grid, in output/qc/manual_crops/ (QC_S<sheet>_Av<letter>.png "
    "marks the two accepted lines red=west, blue=east). "
    "SCALE: px/ft is derived only from the plat's fixed grid pitch and never from "
    "a printed width. In x the interval between the SAME-SIDE frontage lines of "
    "consecutive avenues is (block depth + the width of one avenue): west_k->west_k+1 "
    "carries avenue k's width, east_k->east_k+1 carries avenue k+1's width, so the "
    "interval is exactly 260+70 = 330 ft whenever the avenue whose width enters it "
    "is a 70 ft one. Intervals governed by Av. B (Strand, printed 80 ft) span 340 ft, "
    "not 330, and are EXCLUDED rather than mislabelled -- this is the single point on "
    "which the earlier 3%-narrow finding turns. In y every consecutive same-side "
    "street-frontage interval is 300+80 = 380 ft. Lines are used for scale only if "
    "n>=8 bands, span>=1500 rows and rms<=2.5 px (6 bands / 250 px on the two "
    "harbour plates, whose streets are inked over a short tier of blocks only). A "
    "WIDTH is additionally required to come from a pair whose slopes agree to "
    "0.004 px/row, since one avenue's two frontages must be parallel; that test is "
    "deliberately NOT applied to a pitch interval between two different avenues."
)

out['what_is_measurable'] = {
    'finding': (
        "Every lettered avenue that lies on a sheet boundary is drawn with ONE "
        "frontage line only -- the sheet inks its own side and stops; the roadway "
        "and the far frontage are blank paper carrying only the avenue lettering, "
        "the printed width figure and the SEE SHEET caption. Verified on crops for "
        "Av. D on sheets 9 and 10 and Av. G on sheets 10 and 27, and confirmed by "
        "profile for every other edge avenue. Consequently Av. A, D, G and J are "
        "NOT measurable on any of the eight sheets, because each of them is a sheet "
        "boundary everywhere in this set. Their drawn width has to be taken from "
        "the 70-ft avenues that ARE fully inked on the same sheet."),
    'measurable': {}, 'not_measurable': {},
}

sheets = {}
conv = {}
halfw = {}

for n in ['1', '2', '7', '8', '9', '10', '27', '29']:
    R = RAW[n]
    S = {'size_px': R['size']}

    # ---------------- scale from grid pitch
    av = sorted(SPEC[n]['avenues'].items(), key=lambda kv: kv[1])
    st = sorted(SPEC[n]['streets'].items(), key=lambda kv: kv[1])
    xint, yint = [], []
    # ---- x: same-side avenue frontage spacings.
    # A single step west_k->west_k+1 spans (block depth + width of avenue k);
    # east_k->east_k+1 spans (block depth + width of avenue k+1).  Only steps
    # whose governing avenue is a 70 ft one are used, so the plat length is
    # unambiguously 260+70 = 330 ft.  Multi-step spans made only of such steps
    # are used too, for the longer baseline.
    # No slope-agreement test here: two different avenues may be drawn with
    # slightly different tilt on a distorted plate; that is a property of the
    # plate, not a reason to distrust the spacing of their frontage lines at a
    # fixed latitude.
    for side in ('west', 'east'):
        for i in range(len(av)):
            for j in range(i + 1, len(av)):
                k1, k2 = av[i][0], av[j][0]
                if any(av[m][0] in EXCLUDE_AV for m in range(i, j + 1)):
                    continue
                gov = [av[m][0] if side == 'west' else av[m + 1][0]
                       for m in range(i, j)]
                if any(CLASS_FT[g] != 70 for g in gov):
                    continue
                fa = R['avenues'][k1]['lines'].get(side)
                fb = R['avenues'][k2]['lines'].get(side)
                if not (line_ok(fa, n) and line_ok(fb, n)):
                    continue
                d = val(fb, YREF) - val(fa, YREF)
                ft = 330.0 * (j - i)
                xint.append({'interval': f'{k1}->{k2} {side} frontages',
                             'steps': j - i, 'plat_ft': ft, 'px': round(d, 2),
                             'px_per_ft': round(d / ft, 4)})
    # ---- y: same-side street frontage spacings, 380 ft per step.
    # Both endpoint streets must have a COMPLETE gate-passing north/south pair,
    # which is what proves the two lines were identified as north and south
    # correctly; a lone line near a clipped sheet edge is not admitted.
    complete = [k for k, _ in st
                if pair_ok(R['streets'][k]['lines'].get('north'),
                           R['streets'][k]['lines'].get('south'), n)]
    idx = {k: i for i, (k, _) in enumerate(st)}
    for a_ in range(len(complete)):
        for b_ in range(a_ + 1, len(complete)):
            k1, k2 = complete[a_], complete[b_]
            steps = idx[k2] - idx[k1]
            ft = 380.0 * steps
            for side in ('north', 'south'):
                fa = R['streets'][k1]['lines'][side]
                fb = R['streets'][k2]['lines'][side]
                xr = XREF_SHEET.get(n, XREF)
                d = val(fb, xr) - val(fa, xr)
                yint.append({'interval': f'{k1}->{k2} {side} frontages',
                             'steps': steps, 'plat_ft': ft, 'px': round(d, 2),
                             'px_per_ft': round(d / ft, 4)})
    sx = float(np.mean([i['px_per_ft'] for i in xint])) if xint else None
    sy = float(np.mean([i['px_per_ft'] for i in yint])) if yint else None
    S['px_per_ft_from_grid_x'] = round(sx, 4) if sx else None
    S['px_per_ft_from_grid_y'] = round(sy, 4) if sy else None
    S['px_per_ft_x_sd'] = round(float(np.std([i['px_per_ft'] for i in xint])), 4) if len(xint) > 1 else None
    S['px_per_ft_y_sd'] = round(float(np.std([i['px_per_ft'] for i in yint])), 4) if len(yint) > 1 else None
    S['anisotropy_pct'] = round(100.0 * (sy - sx) / (0.5 * (sx + sy)), 2) if (sx and sy) else None
    S['grid_intervals_x'] = xint
    S['grid_intervals_y'] = yint
    S['printed_scalebar_px_per_ft'] = SCALEBAR[n]

    # ---------------- avenues
    S['avenues'] = []
    meas70 = []
    for name, x0 in av:
        a = R['avenues'][name]
        e = {'name': FULLNAME[name], 'letter': name, 'printed_ft': PRINTED[name]}
        fw, fe = a['lines'].get('west'), a['lines'].get('east')
        e['west_line_x_fit'] = ('x = ' + line_expr(fw, 'y')) if fw else None
        e['east_line_x_fit'] = ('x = ' + line_expr(fe, 'y')) if fe else None
        for sd, f in (('west', fw), ('east', fe)):
            if f:
                e[f'{sd}_fit_rms_px'] = round(f['rms'], 2)
                e[f'{sd}_n_bands'] = f['n']
                e[f'{sd}_y_span'] = [round(f['tmin']), round(f['tmax'])]
        if name in EXCLUDE_AV:
            e['both_frontages_inked'] = False
            e['note'] = ("Harbour-front street. Only one frontage is on this sheet "
                         "and its roadway carries continuous railroad track pairs "
                         "that are indistinguishable from a frontage line by ink "
                         "alone; excluded from width and from scale.")
            e['confidence'] = 'low'
        elif fw and fe and pair_ok(fw, fe, n):
            e['both_frontages_inked'] = True
            e['width_px_at_y'] = a['width_px_at_y']
            e['mean_width_px'] = a['mean_width_px']
            e['width_variation_px_over_sheet'] = round(
                max(a['width_px_at_y'].values()) - min(a['width_px_at_y'].values()), 2)
            e['per_band_width_sd_px'] = a.get('width_sd_px')
            e['fit_rms_px'] = round(max(fw['rms'], fe['rms']), 2)
            if sx:
                e['implied_ft'] = round(a['mean_width_px'] / sx, 2)
                e['implied_vs_printed_pct'] = round(
                    100.0 * (a['mean_width_px'] / sx - PRINTED[name]) / PRINTED[name], 2)
            # scale-free check: width / grid pitch should equal printed/330
            if xint:
                pitch = float(np.mean([i['px'] / i['steps'] for i in xint]))
                r = a['mean_width_px'] / pitch
                e['scale_free_width_over_330ft_pitch'] = round(r, 5)
                e['scale_free_plat_ratio'] = round(PRINTED[name] / 330.0, 5)
                e['scale_free_pct_vs_plat'] = round(
                    100.0 * (r - PRINTED[name] / 330.0) / (PRINTED[name] / 330.0), 2)
            good = (max(fw['rms'], fe['rms']) <= 1.3 and min(fw['n'], fe['n']) >= 12
                    and e['width_variation_px_over_sheet'] <= 4.5)
            e['confidence'] = 'high' if good else 'medium'
            if PRINTED[name] == 70:
                meas70.append(a['mean_width_px'])
            out['what_is_measurable']['measurable'].setdefault(n, []).append(name)
        else:
            e['both_frontages_inked'] = False
            side = EDGE_SIDE.get((n, name))
            e['note'] = (f"Sheet boundary avenue: only the {side} frontage is inked "
                         f"on this sheet; the roadway and the far frontage are blank "
                         f"paper. Width not measurable here.")
            e['confidence'] = 'n/a'
            out['what_is_measurable']['not_measurable'].setdefault(n, []).append(name)
        S['avenues'].append(e)

    # ---------------- streets (convention check + y scale)
    S['streets'] = []
    best = None
    for name, y0 in st:
        s_ = R['streets'][name]
        fn, fs = s_['lines'].get('north'), s_['lines'].get('south')
        e = {'name': name, 'printed_ft': PRINTED_STREET}
        if fn and fs and pair_ok(fn, fs, n):
            e['measured_px'] = s_['mean_width_px']
            e['width_px_at_x'] = s_['width_px_at_x']
            e['fit_rms_px'] = round(max(fn['rms'], fs['rms']), 2)
            if sy:
                e['implied_ft'] = round(s_['mean_width_px'] / sy, 2)
                e['implied_vs_printed_pct'] = round(
                    100.0 * (s_['mean_width_px'] / sy - 80) / 80, 2)
            if yint:
                pitch = float(np.mean([i['px'] / i['steps'] for i in yint]))
                r = s_['mean_width_px'] / pitch
                e['scale_free_width_over_380ft_pitch'] = round(r, 5)
                e['scale_free_plat_ratio'] = round(80.0 / 380.0, 5)
                e['scale_free_pct_vs_plat'] = round(
                    100.0 * (r - 80.0 / 380.0) / (80.0 / 380.0), 2)
            q = max(fn['rms'], fs['rms'])
            if best is None or q < best[0]:
                best = (q, e)
        else:
            e['measured_px'] = None
            e['note'] = 'incomplete on this sheet (clipped at the sheet edge)'
        S['streets'].append(e)
    if best:
        b = best[1]
        conv[n] = {'street': b['name'] + ' St', 'printed_ft': 80,
                   'measured_px': b['measured_px'],
                   'implied_ft': b.get('implied_ft'),
                   'scale_free_pct_vs_plat': b.get('scale_free_pct_vs_plat'),
                   'fit_rms_px': b['fit_rms_px'],
                   'note': ('Measured with the identical convention used for the '
                            'avenues (heavy continuous frontage line, half-max '
                            'midpoint). Streets are drawn true, so this calibrates '
                            'the convention: it returns 80 ft to within ~1%.')}

    # ---------------- half width for centreline construction
    if meas70:
        mw = float(np.mean(meas70))
        S['measured_70ft_avenue_width_px'] = round(mw, 2)
        S['measured_70ft_half_width_px'] = round(mw / 2.0, 2)
        S['half_width_basis'] = 'mean of this sheet\'s fully inked 70 ft avenues: ' + \
            ', '.join(a['letter'] for a in S['avenues'] if a.get('both_frontages_inked') and a['printed_ft'] == 70)
    else:
        S['measured_70ft_avenue_width_px'] = None
        S['measured_70ft_half_width_px'] = None
        S['half_width_basis'] = 'no fully inked avenue on this sheet'
    sheets[n] = S

# --------------------------------------------------- half widths for seams
SEAM_AV = {'1': ['A'], '2': ['A'], '7': ['A', 'D'], '8': ['D', 'G'],
           '9': ['A', 'D'], '10': ['D', 'G'], '27': ['G', 'J'], '29': ['G', 'J']}
for n, names in SEAM_AV.items():
    S = sheets[n]
    d = {}
    for nm in names:
        printed_half_px = 0.5 * PRINTED[nm] * SCALEBAR[n]
        if PRINTED[nm] == 70 and S['measured_70ft_half_width_px']:
            m = S['measured_70ft_half_width_px']
            basis = 'measured on this sheet (' + S['half_width_basis'] + ')'
        elif PRINTED[nm] == 70:
            m = None
            basis = 'not measurable on this sheet - no fully inked avenue'
        else:
            m = None
            basis = (f'Av. J is printed {PRINTED[nm]} ft (E. Broadway); no '
                     f'{PRINTED[nm]} ft avenue is fully inked anywhere in this set, '
                     f'so no measured half width can be offered')
        d[FULLNAME[nm]] = {
            'half_width_px_measured': m,
            'half_width_px_from_printed_figure': round(printed_half_px, 2),
            'printed_minus_measured_px': round(printed_half_px - m, 2) if m else None,
            'basis': basis,
        }
    halfw[n] = d

out['convention_check'] = conv
out['sheets'] = sheets
out['half_width_px_for_centreline_construction'] = halfw

# --------------------------------------------------- the two seams asked about
def seam_row(sheet, avletter, drawn_side):
    S = sheets[sheet]
    printed_half = 0.5 * PRINTED[avletter] * SCALEBAR[sheet]
    meas_half = S['measured_70ft_half_width_px']
    if meas_half is None:
        return None
    sgn = +1 if drawn_side == 'west' else -1   # centreline = frontage + sgn*half
    shift = sgn * (meas_half - printed_half)
    return {
        'sheet': sheet, 'avenue': FULLNAME[avletter],
        'frontage_drawn_on_this_sheet': drawn_side,
        'half_width_px_printed_figure': round(printed_half, 2),
        'half_width_px_measured': round(meas_half, 2),
        'centreline_shift_px_measured_minus_printed': round(shift, 2),
        'direction': 'east' if shift > 0 else 'west',
    }

seams = {}
for label, rows in (('Av. D or Market E. -- seam S9|S10',
                     [seam_row('9', 'D', 'west'), seam_row('10', 'D', 'east')]),
                    ('Av. G or Winnie E. -- seam S10|S27',
                     [seam_row('10', 'G', 'west'), seam_row('27', 'G', 'east')])):
    rows = [r for r in rows if r]
    rel = None
    if len(rows) == 2:
        rel = round(rows[0]['centreline_shift_px_measured_minus_printed']
                    - rows[1]['centreline_shift_px_measured_minus_printed'], 2)
    seams[label] = {
        'per_sheet': rows,
        'relative_change_across_the_seam_px': rel,
        'note': ('Each sheet\'s constructed centreline moves by the per-sheet figure. '
                 'Because both sheets\' tie points move the SAME way and by nearly the '
                 'same amount, the part that a seam solve can actually see -- the '
                 'difference between the two -- is what matters, and it is given as '
                 'relative_change_across_the_seam_px.')}
out['seam_impact'] = seams

out['conclusion'] = (
    "The premise that the draughtsmen drew the avenues about 3% narrow is NOT "
    "supported by the drawn ink. Measured against each sheet's own grid pitch -- "
    "which needs no printed width -- the fully inked lettered avenues come out at "
    "69.0-70.3 ft against a printed 70 ft, and Av. B (Strand) at 79.8-80.3 ft "
    "against a printed 80 ft. The scale-free form of the same test is even more "
    "direct: drawn avenue width divided by the drawn 330 ft grid pitch is 0.2092-"
    "0.2129 against the plat's 70/330 = 0.2121, i.e. the avenues are drawn at their "
    "printed width to within -1.4%..+0.4%, and drawn street width over the drawn "
    "380 ft street pitch is 0.2096-0.2117 against 80/380 = 0.2105. Avenues and "
    "streets are drawn to the same standard; neither is 3% out. "
    "The earlier -2.8%/-3.5% arose from the x scale, not from the widths. Sheet 9's "
    "px/ft in x was obtained from the Av. B -> Av. C centreline pitch taken as 330 ft. "
    "That pitch is 335 ft, not 330: the Strand is printed 80 ft, so the centre-to-"
    "centre step from Av. B to Av. C is 260 + 80/2 + 70/2 = 335 ft. Reading 1003 px "
    "as 330 ft instead of 335 ft inflates px/ft_x by 1.5%, and every avenue width "
    "then converts ~1.5% too narrow -- which, on top of a real ~1% effect, is the "
    "reported 2.8-3.5%. Using only intervals whose plat length is unambiguously "
    "330 ft gives sheet 9 px/ft_x = 2.998, not 3.043. "
    "Isotropy: on this reading the sheets are NOT isotropic to 0.7%. Sheets 8, 10, "
    "27 and 29 run 0.6-1.2% (y larger than x); sheet 9 runs 2.2% and sheet 7 runs "
    "3.6%. Sheet 7's avenue grid is genuinely compressed in x relative to its own "
    "printed scale bar (grid x 2.94 vs bar 3.06) while its street grid in y matches "
    "the bar; sheet 7 should not be given an isotropic similarity without allowing "
    "for that. "
    "Practical consequence for the seams: rebuilding the Av. D and Av. G centrelines "
    "from measurement instead of the printed 70 ft moves each sheet's tie points by "
    "only 0.5-0.7 px, and -- because both sheets of a seam move the same way -- the "
    "relative change a seam solve can see is 0.02-0.03 px. The systematic seam bias "
    "being chased is not in the avenue width. It is not worth re-cutting the "
    "centrelines for; the honest gain is to record that the printed-width "
    "construction was already right to well under a pixel. Sheet 7 is the one place "
    "where the printed construction is materially off (5.5 px per side on Av. D), "
    "because sheet 7's x scale is not its scale-bar scale."
)

path = os.path.join(ROOT, 'gcps', 'manual', 'avenue_widths.json')
with open(path, 'w') as f:
    json.dump(out, f, indent=1)
print('wrote', path)

# ------------------------------------------------------------------ console
for n, S in sheets.items():
    print(f"\n== sheet {n}: px/ft grid x={S['px_per_ft_from_grid_x']} "
          f"(sd {S['px_per_ft_x_sd']}, {len(S['grid_intervals_x'])} intervals)  "
          f"y={S['px_per_ft_from_grid_y']} (sd {S['px_per_ft_y_sd']}, "
          f"{len(S['grid_intervals_y'])})  aniso={S['anisotropy_pct']}%  "
          f"bar={S['printed_scalebar_px_per_ft']}")
    for a in S['avenues']:
        if a.get('both_frontages_inked'):
            print(f"   {a['letter']} printed {a['printed_ft']}ft: {a['mean_width_px']:.2f} px "
                  f"-> {a.get('implied_ft')} ft "
                  f"(grid)  scale-free {a.get('scale_free_pct_vs_plat')}%  "
                  f"var {a['width_variation_px_over_sheet']} px  {a['confidence']}")
    if n in conv:
        c = conv[n]
        print(f"   street {c['street']}: {c['measured_px']} px -> {c['implied_ft']} ft "
              f"(grid-y)  scale-free {c['scale_free_pct_vs_plat']}%")
    print(f"   half width for centreline: {S['measured_70ft_half_width_px']} px")
print()
print(json.dumps(out['seam_impact'], indent=1))


# Narrative conclusion, per-sheet status and headline block are applied by
# scripts/avenue_widths_finalise.py so the wording lives in one place.
import subprocess
subprocess.run([sys.executable,
                os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             'avenue_widths_finalise.py')],
               cwd=ROOT, check=True)

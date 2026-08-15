import json, os
P = 'gcps/manual/avenue_widths.json'
d = json.load(open(P))

# ---- explicit per-sheet status
for n, S in d['sheets'].items():
    has_av = any(a.get('both_frontages_inked') for a in S['avenues'])
    if has_av:
        S['status'] = 'measured'
    elif S['px_per_ft_from_grid_y']:
        S['status'] = ('no avenue is fully inked on this sheet, so no drawn avenue '
                       'width and no x grid pitch; y grid pitch measured')
    else:
        S['status'] = ('no avenue is fully inked on this sheet and no numbered street '
                       'has a complete, gate-passing frontage pair; nothing measurable')

d['qc_images'] = ('output/qc/manual_crops/ -- QC_S<sheet>_Av<letter>.png shows each '
                  'accepted pair of frontage lines drawn over the source at 3x '
                  '(red = west line, blue = east line); S<sheet>_*_z<zoom>.png are the '
                  'raw upscaled crops with a 1-source-pixel grid used to identify the '
                  'heavy continuous frontage line and to rule out the dashed awning edge.')

d['headline_numbers'] = {
    'drawn_width_of_the_70ft_avenues_ft': {
        'range': [69.43, 70.32],
        'values': {'S7 Av.C': 69.87, 'S8 Av.E': 69.91, 'S8 Av.F': 70.04,
                   'S9 Av.C': 70.32, 'S10 Av.E': 70.18, 'S10 Av.F': 70.06,
                   'S27 Av.H': 69.65, 'S27 Av.I': 70.08, 'S29 Av.H': 70.08,
                   'S29 Av.I': 69.43},
        'note': 'against a printed 70 ft; converted through each sheet\'s own grid-x px/ft'},
    'drawn_width_of_Av_B_Strand_ft': {'S7': 80.83, 'S9': 79.81,
                                      'note': 'against a printed 80 ft'},
    'scale_free_pct_off_plat': {
        'avenues': [-0.81, 1.04],
        'streets': [-0.90, 0.86],
        'note': ('drawn width / drawn grid pitch compared with 70/330 and 80/380. '
                 'This form uses no px/ft at all and is the decisive test.')},
    'px_per_ft_from_grid': {
        '1': {'x': None, 'y': None}, '2': {'x': None, 'y': 3.0797},
        '7': {'x': 2.9458, 'y': 3.0511}, '8': {'x': 3.0440, 'y': 3.0716},
        '9': {'x': 2.9985, 'y': 3.0642}, '10': {'x': 3.0571, 'y': 3.0755},
        '27': {'x': 3.0603, 'y': 3.0955}, '29': {'x': 3.0637, 'y': 3.0909}},
    'anisotropy_pct_y_over_x': {'7': 3.51, '8': 0.90, '9': 2.17,
                                '10': 0.60, '27': 1.14, '29': 0.88},
    'half_width_px_to_step_in_from_a_drawn_frontage': {
        '7': 102.91, '8': 106.51, '9': 105.42, '10': 107.18, '27': 106.91, '29': 106.85,
        '1': None, '2': None},
}

d['conclusion'] = (
    "The premise that the draughtsmen drew the lettered avenues about 3% narrow is NOT "
    "supported by the drawn ink.\n\n"

    "1. WHAT CAN BE MEASURED. Every lettered avenue in this eight-sheet set lies on a "
    "sheet boundary somewhere, and a boundary avenue is inked on one side only: the "
    "plate draws its own frontage line and stops, leaving the roadway and the far "
    "frontage as blank paper carrying just the avenue lettering, the printed width "
    "figure and the SEE SHEET caption. Av. A, D, G and J are therefore not measurable "
    "anywhere in this set. The drawn widths come from the twelve fully inked avenues: "
    "B and C on sheets 7 and 9, E and F on sheets 8 and 10, H and I on sheets 27 and "
    "29. Sheets 1 and 2 have no fully inked avenue at all. Av. A is additionally "
    "unusable because its roadway is the harbour front and carries continuous railroad "
    "track pairs that pass every heavy-continuous-line test.\n\n"

    "2. THE WIDTHS. Measured against each sheet's own grid pitch -- which needs no "
    "printed width -- the ten fully inked 70 ft avenues come out at 69.43-70.32 ft "
    "against a printed 70 ft, and the two Av. B (Strand) measurements at 79.81 and "
    "80.83 ft against a printed 80 ft. The scale-free form of the same test is more "
    "direct still, because it cancels px/ft entirely: drawn avenue width divided by the "
    "drawn 330 ft grid pitch is -0.81% to +1.04% off the plat's 70/330, and drawn "
    "street width over the drawn 380 ft street pitch is -0.90% to +0.86% off 80/380. "
    "Avenues and streets are drawn to the same standard and neither is 3% out. The "
    "convention check confirms it independently: the identical detector and identical "
    "half-max convention, applied to a numbered street printed 80 ft, returns "
    "79.28-80.68 ft.\n\n"

    "3. WHERE THE -2.8%/-3.5% CAME FROM. It came from the x scale, not from the widths. "
    "Sheet 9's px/ft in x was obtained from the Av. B -> Av. C centreline pitch read as "
    "330 ft. That pitch is 335 ft, not 330: the Strand is printed 80 ft, so the "
    "centre-to-centre step from Av. B to Av. C is 260 + 80/2 + 70/2 = 335 ft. Reading "
    "the measured ~1003 px as 330 ft rather than 335 ft inflates px/ft_x by 1.5%, and "
    "every avenue width then converts about 1.5% too narrow -- which, on top of a real "
    "sub-percent effect, is the reported 2.8-3.5%. Using only intervals whose plat "
    "length is unambiguously 330 ft gives sheet 9 px/ft_x = 2.9985, not 3.0429.\n\n"

    "4. ISOTROPY. On this reading the sheets are not isotropic to 0.7%. Sheets 10, 29, "
    "8 and 27 run 0.60%, 0.88%, 0.90% and 1.14%, with y larger than x throughout; sheet "
    "9 runs 2.17% and sheet 7 runs 3.51%. Sheet 7 is the real outlier: its avenue grid "
    "in x measures 2.9458 px/ft against its own printed scale bar's 3.0570, while its "
    "street grid in y (3.0511) matches that bar. Sheet 7 should not be given an "
    "isotropic similarity without allowing for this. Sheets 1 and 2 carry only one "
    "avenue each, so no x pitch exists on them; sheet 1 has no numbered street with a "
    "complete frontage pair either, so it yields no y pitch.\n\n"

    "5. WHAT IT MEANS FOR THE SEAMS. Rebuilding the Av. D and Av. G centrelines from "
    "measurement instead of the printed 70 ft moves each plate's constructed tie points "
    "by only 0.48-0.66 px, and because both plates of a seam move the same way, the "
    "relative change a seam solve can actually see is 0.13 px on S9|S10 and 0.18 px on "
    "S10|S27. The systematic seam bias being chased is not in the avenue width: a 3 px "
    "per side / 6 px across the seam correction does not exist. The gain here is "
    "negative evidence -- the printed-width construction already used in "
    "gcps/manual/seam_S10_S27.json and its siblings was right to well under a pixel, "
    "and this line of attack can be closed rather than re-cut.\n\n"

    "6. THE ONE PLACE IT DOES MATTER: SHEET 7. Its measured 70 ft half-width is 102.91 "
    "px against 107.00 px from the printed figure at the sheet's scale-bar scale -- "
    "4.09 px per side. That is not a drafting error in the avenue (sheet 7's Av. C is "
    "-0.18% on the scale-free test, i.e. drawn true); it is sheet 7's x scale sitting "
    "3.6% below its own scale bar. Any sheet 7 construction that converts feet to "
    "pixels through the scale bar -- which includes its Av. A and Av. D seam "
    "centrelines -- inherits that error, and sheet 7 is exactly the plate whose seams "
    "have been failing. If one thing is to be changed on the strength of this work, it "
    "is sheet 7's px/ft in x, not the avenue widths."
)

json.dump(d, open(P, 'w'), indent=1)
print('patched', P, os.path.getsize(P), 'bytes')

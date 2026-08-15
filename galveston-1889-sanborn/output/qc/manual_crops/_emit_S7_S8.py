#!/usr/bin/env python
import json, math, os
import numpy as np

W8 = 212.7
OUT = '/home/user/claude-code/galveston-1889-sanborn/gcps/manual/seam_S7_S8.json'

R = [
 dict(name='19th St N line', ax=3119.12, ay=132.50, e8=296.44, by=103.34, u=4.5, conf='high',
      feat='SE corner of the block N of 19th St at Av. D (S7) / SW corner of the same block, E side of Av. D (S8) '
           '- i.e. the two ends of the 19th-St north property line where it crosses Av. D',
      why='The 19th St NORTH property line is drawn on BOTH sheets and is the northern terminus of the mapped strip; '
           'it can only be this line. On S7 its east end is the drawn corner with the Av. D west property line; on S8 '
           'its west end is the drawn corner with the Av. D east property line. b_x is the S8 east line stepped west by '
           'the printed 70 ft width of Av. D (212.7 px on S8).',
      cat='block corner'),
 dict(name='19th St S line', ax=3119.98, ay=379.59, e8=294.40, by=349.05, u=5.0, conf='high',
      feat='NE corner of block 559 (S7) / NW corner of block 499 (S8) - 19th St south property line at Av. D',
      why='Block numbers 559 (S7) and 499 (S8) are printed inside the blocks, and "19TH ST." plus its "80\'" width label '
           'are printed on both sheets, so the latitude cannot be one block off. The 19th-St south property line is drawn '
           'on both sheets and terminates on the drawn Av. D frontage line of each.',
      cat='block corner'),
 dict(name='20th St N line', ax=3117.73, ay=1299.30, e8=294.97, by=1275.01, u=5.0, conf='high',
      feat='SE corner of block 559 (S7) / SW corner of block 499 (S8) - 20th St north property line at Av. D',
      why='South frontage of the 559/499 block pair, bounded by the printed "20TH ST."; drawn as a heavy continuous '
           'frontage line on both sheets with the 15-16 ft awning strip (dashed) on the street side of it, so the '
           'property line is not confused with the awning edge.',
      cat='block corner'),
 dict(name='21st St N line', ax=3102.60, ay=2457.02, e8=293.06, by=2439.05, u=4.5, conf='high',
      feat='SE corner of block 560 (S7) / SW corner of block 500 (S8) - 21st (Center) St north property line at Av. D',
      why='"21ST OR CENTER" street is printed on both sheets with its "80\'" width; block 560 and block 500 numbers are '
           'printed. Single clean heavy frontage line on both sheets at this corner (no double line), the cleanest '
           'corner on the seam.',
      cat='block corner'),
 dict(name='21st St S line', ax=3099.49, ay=2699.28, e8=294.47, by=2685.99, u=5.0, conf='high',
      feat='NE corner of block 561 (S7) / NW corner of block 501 (S8) - 21st (Center) St south property line at Av. D',
      why='North frontage of the 561/501 block pair. On S7 the heavy vertical frontage line visibly STARTS at this '
           'corner (verified at 14x), so the corner is a true terminus, not an interpolation.',
      cat='block corner'),
 dict(name='22nd St N line', ax=3095.30, ay=3617.60, e8=293.55, by=3606.94, u=6.5, conf='medium',
      feat='SE corner of block 561 (S7) / SW corner of block 501 (S8) - 22nd St north property line at Av. D',
      why='"22ND ST." with "80\'" is printed on both sheets. Downgraded because on S7 the corner carries four near-parallel '
           'verticals within 20 px (brick wall 3095.3, a second line 3102.0, address ticks) and on S8 the frontage is a '
           'double line 289.1/293.6; the wall face was taken on both.',
      cat='block corner'),
 dict(name='22nd St S line', ax=3092.83, ay=3862.05, e8=293.94, by=3852.55, u=5.0, conf='medium',
      feat='NE corner of the block S of 22nd St at Av. D (S7) / NW corner of the same block (S8) - '
           '22nd St south property line at Av. D',
      why='Southern terminus of the mapped strip on both sheets - the stub of the block south of 22nd St is drawn on '
           'both, with its Av. D frontage line. Cannot be one block off. Downgraded slightly because the stub is only '
           '~90 px deep, so the frontage line is measured over a short run.',
      cat='block corner'),
]

A = np.array([[r['ax'], r['ay']] for r in R], float)
B = np.array([[r['e8'] - W8, r['by']] for r in R], float)
sig = np.array([r['u'] for r in R], float)
w = 1.0 / sig ** 2
M, rhs = [], []
for (ax, ay), (bx, by), wi in zip(A, B, w):
    s = math.sqrt(wi)
    M += [[ax * s, -ay * s, s, 0], [ay * s, ax * s, 0, s]]
    rhs += [bx * s, by * s]
p, *_ = np.linalg.lstsq(np.array(M), np.array(rhs), rcond=None)
a, b, tx, ty = p
scale, rot = math.hypot(a, b), math.degrees(math.atan2(b, a))
pred = np.stack([a * A[:, 0] - b * A[:, 1] + tx, b * A[:, 0] + a * A[:, 1] + ty], 1)
res = np.linalg.norm(pred - B, axis=1)
outl = [r['name'] for r, rr in zip(R, res) if rr > 3 * r['u']]

doc = {
 "seam": "S7|S8",
 "sheet_a": "7",
 "sheet_b": "8",
 "relation": "sheet 7 lies WEST of sheet 8; shared street Av. D or Market E.",
 "overlap_exists": "partial",
 "overlap_description":
   "The two sheets share the full 70-ft width of Av. D (Market E.) as MAPPED GROUND - S7 covers x~3093-3327 "
   "(its west property line out to the east property line, which sits at/just inside the torn paper edge at x~3340) "
   "and S8 covers x~81-294 (its east property line back to a west property line that falls just inside the paper edge "
   "at x~60). But they share almost no DRAWN INK: each sheet stops at its own side's dashed awning edge "
   "(S7 x~3170 at the top falling to ~3143 at the bottom; S8 x~242), leaving a ~115 px band of blank roadway that both "
   "sheets leave empty. No block, lot, building, curb or property line is drawn on both sheets. The only ink common to "
   "both is (a) the 10-in water mains in 20th and 22nd Streets, which cross the roadway on both plates but are placed by "
   "eye and disagree by a consistent +29 px, and (b) the large 'AV. D OR MARKET E.' street-name lettering and the "
   "70'/80' width labels, which are lettered independently on each sheet (see rejected_candidates). "
   "Consequently every correspondence below is anchored on the cross-street property lines, which ARE drawn on both "
   "sheets (giving fully observed y on both plates), with the x transferred across the 70-ft roadway using the printed "
   "width of Av. D rendered at S8's own measured scale (212.7 px per 70 ft, mean of 6 measurements of Av. E and Av. F on "
   "sheet 8, sd 0.7 px). a_x and a_y are directly observed drawn corners on sheet 7; b_y is directly observed on sheet 8; "
   "only b_x is constructed.",
 "correspondences": [
   {"feature": r['feat'], "why_unambiguous": r['why'],
    "a_x": round(r['ax'], 2), "a_y": round(r['ay'], 2),
    "b_x": round(r['e8'] - W8, 2), "b_y": round(r['by'], 2),
    "confidence": r['conf'], "uncertainty_px": r['u'], "category": r['cat']}
   for r in R],
 "self_check_similarity": {
   "scale": round(scale, 6), "rotation_deg": round(rot, 4),
   "tx": round(tx, 2), "ty": round(ty, 2),
   "rms_px": round(float(math.sqrt((res ** 2).mean())), 2),
   "max_px": round(float(res.max()), 2),
   "outliers": outl,
   "per_point_residual_px": {r['name']: round(float(rr), 2) for r, rr in zip(R, res)},
   "convention": "b = scale * R(rotation_deg) * a + (tx,ty), image axes, y down, weighted by 1/uncertainty^2"},
 "rejected_candidates": [
  {"feature": "Large street-name lettering 'AV. D OR MARKET E.' drawn down the Av. D roadway on BOTH sheets",
   "reason":
     "Tempting and looks identical glyph-for-glyph, but the two sheets letter it independently. Measured: the final 'E' "
     "of 'MARKET E.' spans S7 x 3156-3195 / y 1623-1653 and S8 x 170-210 / y 1601-1635. The y offset (-21 px) happens to "
     "agree with the street-line solution to ~1 px, but the x does not: the fitted transform maps S7 x=3156 to S8 x=133, "
     "33-37 px (11-12 ft) west of the observed 170. The reason is visible - on S8 the label is centred in the 70-ft "
     "roadway (label centre 189 vs roadway centre 187), while on S7 it is pushed hard against the west awning line "
     "(label centre 3177 vs roadway centre 3210) to clear the 'SEE ... SHEET No. 8' marginal note. Using it would bias "
     "tx by about 35 px (11 ft)."},
  {"feature": "10-in water main in 20th St where it crosses Av. D (double dashed line, drawn on both sheets)",
   "reason":
     "Genuinely the same main and genuinely drawn on both plates over the shared roadway (S7 to x=3312, S8 back to "
     "x=114), but centreline y is S7 1375.7 and S8 1381.1, whereas the street-line solution predicts S8 1351.8 - a "
     "+29.3 px (9.6 ft) residual. The main sits 32% of the way across 20th St on S7 and 43% on S8: placed by eye. "
     "Retained here as evidence, not used as control."},
  {"feature": "Water main in 22nd St where it crosses Av. D",
   "reason":
     "Same story and, tellingly, the same sign and size of error: S7 y=3730.1, S8 y=3748.4, predicted 3719.5, residual "
     "+28.8 px. Two independent mains both off by +29 px confirms this is a systematic draughting convention difference, "
     "not noise, so water mains carry no usable y information on this seam."},
  {"feature": "Dashed awning edge lines flanking the Av. D roadway (S7 x~3143-3170, S8 x~242)",
   "reason":
     "These are the two OPPOSITE sides of the street (west-side awnings on S7, east-side awnings on S8), ~16 ft in from "
     "each frontage - different physical features, not a correspondence. Measured awning projection is 47 px (15.4 ft) "
     "on S7 and 49 px (16.2 ft) on S8, consistent with the warning that this line is not the property line."},
  {"feature": "70' (Av. D) and 80' (street) width labels; 'SEE ... SHEET No. 7/8' marginal notes",
   "reason":
     "Per-sheet marginalia. The 'SEE/SHEET' notes sit EAST of the street name on S7 and WEST of it on S8, proving they "
     "are each sheet's own annotation rather than shared artwork."},
  {"feature": "20th St SOUTH property line (would have been an 8th latitude)",
   "reason":
     "Not identifiable on sheet 7. S8 draws it cleanly at y=1519.9 (20th St = 242 px = 80 ft there), but on S7 the "
     "Market House / City Offices / Chamber of Commerce block and its steps stand in the street, and the block-560 "
     "building frontage is set back to y=1674 (making the 20th St band read 121 ft wide on S7 against 80 ft on S8). "
     "No line at the predicted y~1544 could be identified with confidence, so the latitude was dropped."},
  {"feature": "Automated NCC pairs already in gcps/shared_edges/S7__S8.geojson",
   "reason":
     "Spot-checked OVL_S7_S8_000 a=(3241.0,166.0) -> b=(237.7,116.4). That a-point is blank roadway paper on sheet 7 "
     "(no ink within 70 px), so the correlation is on paper texture. Under the solution here that point maps to "
     "b=(203.2,134.9), i.e. the automated pair is 34 px off in x and 18 px in y. Consistent with the brief's warning "
     "that blind matching fails on this material."}],
 "notes":
   "1. HOW THE POINTS WERE MADE. All coordinates were read off 8x-14x nearest-neighbour crops carrying a 1-source-pixel "
   "red grid labelled in SOURCE coordinates (output/qc/manual_crops/), and cross-checked with intensity-centroid row/"
   "column profiles over windows chosen inside a single identified block. Every latitude is named by printed lettering "
   "(19TH/20TH/21ST OR CENTER/22ND ST.) and bracketed by printed block numbers (559,560,561 on S7; 499,500,501 on S8), "
   "so none of them can be one block off.\n"
   "2. THE SEAM CANNOT DETERMINE RELATIVE X-SCALE. All seven points lie in an x band only ~27 px wide on each sheet, so "
   "they pin tx, ty, rotation and the y-scale, but say nothing about s_x. They also share one common systematic: b_x is "
   "constructed as (S8 Av. D east property line) - 212.7 px. If that 212.7 is wrong, all seven b_x shift together. "
   "The 212.7 comes from six independent measurements of 70-ft avenues on sheet 8 itself (Av. E 212.21/213.20/212.98, "
   "Av. F 212.03/213.67/212.28), so I judge that systematic to be under ~2 px.\n"
   "3. THE TWO SHEETS ARE NOT SIMILAR TO EACH OTHER. Body scale measured from printed ground dimensions: sheet 7 renders "
   "80 ft as 236.6 px in x (Av. B) and 70 ft as 207.1 px (Av. C) -> 2.958 px/ft in x, but ~3.07 px/ft in y (19th/21st/"
   "22nd St widths); sheet 8 renders 70 ft as 212.7 px in x -> 3.039 px/ft, and ~3.03 px/ft in y. So sheet 7 is about 4% "
   "anisotropic and sheet 8 is not: the true S7->S8 map has s_x ~ 1.027 against s_y ~ 1.005 (about 2.2% anisotropy) and "
   "needs an affine, not a similarity. The self-check similarity above still fits to 2.9 px rms only because all the "
   "points share the same x. A downstream global similarity solve should expect this seam to leave a systematic x "
   "signature.\n"
   "4. SCALE-BAR vs BODY. Consistent with the project's existing REVIEW_independent_scale_and_seam_audit finding: the "
   "printed scale bars (3.0567 px/ft on S7, 3.026 on S8, ratio 0.990) contradict the map body, which gives s_y = 1.0057 "
   "over a 3730 px baseline (19th St north line to 22nd St south line, seven street property lines agreeing to 3 px). "
   "Do not use the scale bars to predict this seam.\n"
   "5. SHEET 7 IS LOCALLY NON-RIGID. Its Av. D west property line steps west at each cross street (x = 3119.1, 3120.0, "
   "3117.7 in block 559; 3103.5, 3103.5, 3102.7 in block 560; 3095.9, 3094.7, 3092.8 in block 561). Av. C's east line "
   "steps by the same pattern (-9 px) and Av. C's west line by -5.5 px at the same street, i.e. the step grows in "
   "proportion to x - a ~1% x-scale change between block rows, not building setbacks. Sheet 8's Av. D east line by "
   "contrast is straight to +-1 px over the whole sheet (293.0-296.4). So each block row of sheet 7 was laid out "
   "semi-independently; residuals of 3-5 px on this seam are inherent, not measurement error.\n"
   "6. SANITY CHECKS THAT PASSED. Av. D is printed 70' on both sheets (S7 at (3192,3584), S8 at (177,366) and (175,3573)); "
   "19th St measures 246.7 px on S7 and 246.1 px on S8 against a printed 80'; the awning strip is a uniform 47 px "
   "(15.4 ft) on S7 and 49 px on S8; the block-559/499 depth ratio (928.0/918.1 = 1.0108) and the 3730 px full-sheet "
   "baseline ratio (1.0058) bracket the fitted s_y = 1.0057."
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w') as f:
    json.dump(doc, f, indent=2)
print('wrote', OUT)
print('scale %.6f rot %.4f tx %.2f ty %.2f rms %.2f max %.2f outliers %s'
      % (scale, rot, tx, ty, math.sqrt((res ** 2).mean()), res.max(), outl))

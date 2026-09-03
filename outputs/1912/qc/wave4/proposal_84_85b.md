# Proposal: 84 | 85b (Ave J / Broadway, 3900 block) — no change; the doubled 10" main is real

Source: interior 1:1 sweep win_72 (rect [10218,39220,11718,40720]); Opus diagnosis, nothing applied.
All native px are raster coordinates of `work/sheets/1912w/u84.jpg` / `u85.jpg` (both 3327x3898).
Native scale: 2.8959 px/ft on plate 84, 2.8914 px/ft on plate 85. Mosaic 5.7966 px/ft.

## What 85b is, and the seam geometry

85b is **a panel of plate 85, not a main sheet**: `units.json` gives it `region: "85b"`,
`panel_of: "85"`, `region_native` = the rectangle [90,1730]-[1176,3812] of the *u85* scan and
`shift_native` [-943,-1658]. It is the detached inset drawn over the cemetery in the lower-left
of plate 85 (block 159, Broadway-Ave K, 39th-40th St). It has no row in
`transforms_city.json`; `reciplib.Recipe.sheet_matrix` (lines 153-155) composes it as plate 85's
`m`,`t` translated by `m @ shift_native` -> t = [10961.21, 34572.04]. The panel sits within
**0.87 ft in y of its parent sheet** at the 40th St north face (85b native y 2923.5 -> mosaic
40439.7; 85 main native y 1253 -> mosaic 40434.6), so the inset shift is sound.

Seam: plate 84's paper ends inside the Broadway roadway (extent x 3225 -> mosaic 11159.8) and the
inset's west edge is `region_native` x 90 -> mosaic 11113.2. Ownership (`seams/ownership_city.json`):
84's cut polygon reaches x 11160.3, 85b's begins at x 11113.5. **The shared band is 46.8 px = 8.1 ft
wide** and straddles Broadway's median. Plate 84 owns the west copy of the main, 85b the east copy
(checked by point-in-polygon: (11009.7,40309.5) -> ['84']; (11237.5,40397.2) -> ['85b']).

## Defect as reported

Two parallel dashed lines run down Broadway 227.8 mosaic px (39.3 ft) apart, each with its own
"10" W. PIPE" caption, each with its own "150'" numeral, each elbowing east into 40th St. The
adversarial confirmer agreed the doubling is on the canvas. It is - and it is correct.

## Cause: they are two different mains, one each side of Broadway's esplanade

Broadway is the only 150-ft avenue on the island and the plates draw it **compressed**: 301.2 +/- 1.1
native px face-to-face, measured by `pair_84_93_x` on the three sheets that show both faces
(69: 300.1 / 299.9 / 301.8; 77: 301.9; 56: 302.4), against ~209 px for a 70-ft avenue - i.e. ~101 ft
drawn. `pair_50_56_x` reads the same corridor 303.0 px (sheet 50) and 303.7 px (sheet 56) beside the
lettered "150 ft. wide", and `pair_92_93` was re-read in review D on exactly this "302-px (105 ft)
Broadway convention". Half-width constant: 150.6 px.

Each plate draws ONE main, on its own side of the median:

| | plate 84 | plate 85 (inset 85b) |
|---|---|---|
| Broadway street line (own side) | x = **3052.0** (y 300-1200; project's own reading 3052.8 for this block row) | x = **235.7** (y 1800-2900) |
| pipe double-dash centre | **3145.0** @y985, **3150.0** @y1215, **3151.0** @y1285 | **152.0** @y2905, **153.0** @y2960 |
| offset from own street line | 98.0 px = **33.8 ft** | 83.2 px = **28.8 ft** |
| derived Broadway centreline (face -/+ 150.6) | 3203.4 | 85.1 |
| **offset from the centreline** | **18.4 ft west of centre** | **23.3 ft east of centre** |
| 40th St faces (own plate) | y 1235.0 / 1478.0 = 243 px = 83.9 ft (printed 80') | y 2923.5 / 3166.0 = 242.5 px = 83.9 ft |
| elbow into 40th St | (3151.5, 1352.0) = 48.1% across 40th St | (152.5, 3044.0) = 49.7% across 40th St |

33.8 + 28.8 = 62.6 ft. If the two dashes were one pipe, Broadway would have to be 62.6 ft wide
face-to-face, i.e. 181 native px, against the 301.2 px the series draws and the 150' both plates
letter. **One pipe is arithmetically impossible.** The plates' own geometry predicts the two mains
18.4 + 23.3 = 41.7 ft apart; the mosaic renders them 39.5 ft apart. They agree to 2.2 ft.

Both plates put the elbow on 40th St's centreline (48.1% / 49.7% of their own 83.9-ft street), so
both draw the same corner of the same street - a 10" main comes down each side of the esplanade and
turns east into 40th St. The captions and the "150'" numerals are duplicated because each plate
letters the avenue it fronts (84's "150'" at native (3135,349) on its own main; 85b's at native
(141,2042) on its own).

## Width proof that the x registration is right (no label needed)

Broadway face-to-face in the mosaic: 84's north line (native 3052.0,y1215) -> mosaic x 10813.6;
85b's south line (native 235.7,y2905) -> mosaic x 11405.3. **591.7 px = 102.1 ft**, against 99.4 ft
(sheet 50) / 99.9 ft (sheet 56) / ~101 ft (the 301.2-px constant) drawn on the plates that show the
whole street. The two independently derived centrelines land at mosaic x **11116.6** (from 84) and
**11103.4** (from 85b): **the 84|85b x registration is good to 13.2 px = 2.3 ft.** There is no 39-ft
x error available to blame for the doubling.

## Independent tie (width-free) — and the real defect in this window

84 and 85/85b share **no drawn line in x** (the two Broadway faces are different lines, and the two
pipes are different pipes), which is why **no `pair_84_85*.json` exists**; the controls that carry
the seam are `pair_84_93_x` (Ave J/Broadway, 84:3211.0 <-> 93:129.3, ACCEPTED) on one side and
`pair_78_85_x` / `pair_85_93_x` (Ave L) / `pair_85_94_x` (Ave M) on the other. `pair_84_93_x`'s
a_native checks out against the scan: it is 3060.4 + 150.6, and Broadway's west face on 84 measures
3052.0 in this (39th-40th) block row against the control's own stated drift 3052.8 -> 3061.2 top to
bottom - agreement 0.8 px.

The one corridor the two units do share is **40th St**, and it is width-free (a face pair on each
plate). Fitting each plate's own 40th St north face from two native bands and evaluating both at the
seam (mosaic x 11150):

- plate 84: native (2600,1235.87) and (2945,1234.59) -> mosaic y **40346.7** (slope -0.0031)
- panel 85b: native (360,2922.31) and (800,2923.50) -> mosaic y **40430.2** (slope +0.0076)

**A step of 83.5 px = 14.4 ft, 85b south of 84**, uniform on both faces of the street (north face
90.6 px, south face 90.4 px at the measured points) - a pure translation, not rotation. This is the
step census_round3 recorded for 84_85b ("40th St face steps ~45 px" at working resolution) and it is
still there; census_round5's score 4 for this seam looked only at the tone break and missed it.
It is also visible in win_72 as the ~95-px offset between 84's "916 918 920 922 924" row and 85b's
"1002 1004 1006" row. Plate 84 agrees with its west neighbour 83 at the same corridor to 8.4 px
(1.4 ft: 83 native (2850,1243.5) -> 40340.7 at mosaic x 4397; 84 -> 40349.1 at x 10349), so the step
sits on plate 85, not on 84.

## Change

**No change to any control from the pipe.** The doubling is source-real: two 10" mains flanking the
Broadway esplanade, drawn once per plate, rendered 2.2 ft from where the plates' own geometry puts
them. Disclosure line for the seam register:

> 84|85b, Ave J/Broadway 3900 block: the two parallel 10" W. PIPE runs are two separate mains, one
> each side of Broadway's esplanade (84 draws its main 18.4 ft west of the drawn centreline, 85b
> draws its main 23.3 ft east). Not a duplicate; no cut can or should remove either.

**No change proposed for the 14.4-ft y step either — it is a net tension, not one wrong value**, and
it is not this seam's to fix. Dry runs (no `--apply`):

- `localsolve --year 1912 --units 84`: 9 controls, residual median **1.6 ft**, max **7.7 ft**
  (`pair_84_93` y -7.7, `pair_83_84_y` y -4.4, `pair_76_84_x` x +3.1); plate moves **(-0,+0) ft**.
  With `--similarity`: 14 samples, median **1.1**, max **1.6 ft**; scale +0.07%, rotation
  +0.037 -> +0.072 deg, centre unmoved.
- `localsolve --year 1912 --units 85`: 9 controls, median **2.1 ft**, max **8.3 ft**
  (`pair_78_85_x` x +8.3, `pair_85_94_x` x +7.4, `pair_85_96` y -6.5, `pair_85_93` y +6.1);
  plate moves **(-1,+3) ft**. With `--similarity`: 16 samples, median **0.7**, max **2.0 ft**;
  scale -0.09%, rotation +0.280 -> +0.248 deg, centre unmoved.
- `localsolve --year 1912 --units 84 85` (both free): 18 controls, median 1.9, max 8.3; 84 moves
  (-0,+0), 85 moves (-1,+3). **Neither plate can move to close a 14.4-ft step.**

The step is carried by the two 42nd-St ties into the *same* plate 93, pulling opposite ways:
`pair_84_93` y **-7.7 ft** and `pair_85_93` y **+6.1 ft** = 13.8 ft of opposed pull, which is the
step to within 0.6 ft. Both quote the same `b_native` 225.5 on plate 93, but they meet plate 93
~2000 native px apart in x (84 at Broadway, native 93 x~130; 85 at Ave L, native 93 x~2164), and
93's 42nd St south face is not flat in its own raster: it reads y 295 at native x~325, 290.5 at
x~875 and 348 at x~2875, while 93's solved rotation is only +0.335 deg. `pair_84_93`'s own note
concedes "roughly +/-20 px of tilt-related slack" (= 7 ft in the mosaic). One `b_native` cannot
serve both ties. That is a `pair_84_93` / `pair_85_93` / plate-93-rotation question and wants its
own proposal with plate 93 measured across its width; I am not proposing a value here on a single
face reading. Corroborating oddity for whoever takes it: plate 84's rotation +0.037 deg is the
outlier of its whole row (83 +0.237, 85 +0.280, 86 +0.243, 91 +0.256, 92 +0.200, 93 +0.335).

## Could a different cut suppress one copy?

**No.** `footprint('84') ∩ footprint('85b')` is the band x 11104.3-11161.0; inside win_72 it is
x 11111.6-11160.5, **48.9 px = 8.4 ft wide**. The west copy sits at mosaic x 11009.7 - **16.3 ft
west** of the band - and the east copy at 11237.5 - **13.2 ft east** of it. Point-in-polygon
confirms neither is in the intersection (west: in 84 True / in 85b False; east: in 84 False /
in 85b True). No cut path through the shared band can touch either line, and neither should be
suppressed: they are different pipes.

## Related seams to re-check

- **84_93 / 85_93 (y)**: the 13.8 ft of opposed pull described above; needs plate 93's 42nd St line
  measured across its full width and, probably, 93's rotation re-solved before either `b_native`
  is trusted. `bandresid` already reports `pair_84_93` and `pair_84_93_x` as "no overlap"
  (diagonal-corner pairs, unchecked by the band test).
- **census_round5 entry for 84_85b (score 4)**: it reports only the foxing-stain tone step and
  states that faces "continue across the cut with no offset"; that is wrong in y by 14.4 ft.
  Round 3's score 1 / offset 35 ft entry is the better record, though its "two separate 10in W. pipe
  runs ... (one per plate)" should now be marked source-real rather than a defect.
- **78_85 (y, `disagreement_before_ft` 37.0)** and **85_93 (y, 24.0)**: the two largest lattice
  disagreements holding plate 85's y; both should be re-read before anyone moves 85.
- **Broadway elsewhere**: any interior window on Ave J where two plates meet in the roadway will
  show the same two mains (e.g. 92|93 at the 4300 block). Grade them against the 18-23 ft
  offsets-from-centreline above, not against each other.

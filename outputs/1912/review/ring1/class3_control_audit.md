# Class-3 control audit, 1912 ring 1 (east of Ave L, 18th St row)

Blind re-read of 15 accepted controls whose band residuals contradict each other. Data: `class3_control_audit.json`; crops: `class3_crops/` (per plate a 1:1 measurement crop with a crop-local ruler and a half-scale identity strip; `check_*` strips are the Ave L width evidence and a sheet-56 zoom).

## How it was read

- Two readers per plate. **A**: an automated ink-profile rule detector (native px, sub-pixel centroid, extent-centre window +-750 px along the corridor) that knows nothing about the filed values. **B**: a visual read of the crops. No sub-agent spawning tool existed in this session, so reader B was the lead; to keep it blind the rulers were labelled in crop-local px with a hidden random origin that was not looked up until all 30 crops had been read. B is blind to the numbers, not to the fact that the controls were under suspicion; A is fully blind.
- Every plate in this set draws only ONE face of its edge corridor, so the midpoint is face +- half the drafted roadway of the corridor's class: 121.5 px for 80 ft streets (241-244 px wherever fully drawn; sheet 26 draws 18th St in full at 242.6 px) and 106 px for 70 ft avenues (206-214 px fully drawn on 34, 35, 40, 41, 45, 85, 93).
- A and B agree on every face to within 9 px (median 3 px). **No face was misread and no corridor identity is wrong.** All 15 names read match the files; `pair_50_51_y` is "25TH ST. OR ROSENBERG AV." and `pair_41_45_x` is "AVENUE M 1/2" (both filed as "?").
- Correction rule: both readers agree, and either a filed value is more than 12 px from face +- half-width, or the pair as filed implies a roadway more than 12 px off the class width (that pair-level error is what the seam sees).

## Verdicts

| control | corridor | current a / b | verdict | why |
|---|---|---|---|---|
| pair_40_41 | Ave L | 3232 / 143 | **correct a to 3216.5, b to 159** | faces right (3110.5, 264.9); 80 ft half-width used on a 70 ft avenue; pair drafts L 243 px instead of ~212 (10 ft) |
| pair_36_37 | Ave L | 3214 / 136 | **correct a to 3199, b to 151** | same defect ("review B" re-centred with +-121); faces 3093.3 / 257.2 |
| pair_37_41 | 18th St | 3669 / 218 | **correct a to 3680** (b 213.5 optional) | 37's value was extrapolated from the block pitch, not the face (3558.5 -> 3680); pair drafts 18th 227.5 px instead of 243 |
| pair_37_40 | 18th St | 3669 / 217 | **correct a to 3680** | same sheet-37 value; 40's face 336.6 confirms 217 |
| pair_33_8 | 18th St | 3661.2 / 218.4 | **correct a to 3671.5, b to 212** | read at the Ave C edge (33's "south face" was the neatline) instead of the extent centre; plates skew 6-11 px; pair drafts 18th 226 px |
| pair_44_45 | Ave L | 3210 / 130 | confirmed | 70 ft half-width already used; faces 3103.0 / 235.9 |
| pair_56_57 | Ave L | 3194.5 / 188.5 | confirmed (a is 7 px low) | extent-centre face is 3095.6, the file's 3088 was read at the skewed south end; "face 82" on 57 is the margin bracket but the centre is right |
| pair_55_56 | Ave I (Sealy) | 3159 / 114 | confirmed (pair-consistent) | asymmetric half-widths (+115 / -96) sum to the right 211 px; only the cut sits 10 px off centre (3150 / 104 would be symmetric) |
| pair_40_45 | 21st St | 3669 / 217 | confirmed | faces 3548.5 / 339.4; diagonal pair, valid as an extent-centre tie |
| pair_45_50 | 24th St | 3670 / 158 | confirmed | faces 3549.9 / 278.1 |
| pair_44_51 | 24th St | 3675 / 168 | confirmed | faces 3556.5 / 288.6; diagonal pair |
| pair_50_51_y | 25th (Rosenberg) | 1365 / 1379.5 | confirmed | fully drawn 364/359 px boulevard; 1365.9 / 1376.5 |
| pair_41_45_x | Ave M 1/2 | 2169 / 2135.5 | confirmed | 41: 2163.6; 45: avenue not opened at the extent centre (S.W. 18 block), north-block faces give 2134.7 and its east face continues as the 1332/1402 lot line at 2241.5 |
| pair_34_35 | Ave F (Church) | 3180 / 138 | confirmed | 3178.6 / 137.5 |
| pair_33_34 | Ave C (Mechanic) | 3203 / 174.5 | confirmed | 3203 / 173 |

The loop 44-45-50-51 (44_45_y, 45_50, 50_51_y, 44_51) closes to 0.5 px in translation, so the 21st/24th/25th readings are mutually consistent as filed.

## Ave L is 70 ft, not 80

Sheet 20 prints `AVENUE L.` with `70'` at both ends of the name, sheet 85 prints `AVENUE L` with `70'`, sheet 93 draws it ~206-211 px wide, and every other accepted Ave L control (24|25 roadway 206/206, 30|31, 44|45, 56|57, 20|25, 85|93) uses the 70 ft width. The rotated `80'` figures at the Ave L block corners belong to the 80 ft cross streets (the same rotated `80'` sits beside the fully drawn 212 px Ave F on sheet 34). Only 40|41 and 36|37 used the 80 ft half-width; these are the two Ave L controls with the anomalous residuals.

## Effect of the corrections (scratch copy of the recipe; nothing under recipe/ was changed)

`localsolve --units 41 45 51`, translation only: pair_40_41 +7.0 -> -0.9 ft, pair_37_41 -3.4 -> +1.1, pair_41_45_x +5.2 -> +3.1, pair_44_45 -3.7 -> -2.9. Nine-unit block (33 36 37 40 41 44 45 50 51): pair_33_8 -4.9 -> -0.6, pair_36_40_x +4.0 -> +1.3, pair_30_36_x +3.7 -> +0.1, median 2.4 -> 2.0 ft.

What the corrections do not fix, and why: the +5 ft y set around 45 (40_45, 45_50, 44_51, 50_51_y) is a plate-scale effect, not a misreading. Plates 40/44/50 sit at transform scale 2.0065-2.0074 and 41/45/51 at 1.99-2.00, and each plate's own 18th-to-21st face distance differs by ~8 px from its neighbour's, which a translation-only solve spreads as 3-7 ft; `localsolve --similarity --units 40 41 44 45 50 51` with the corrected controls reaches median 1.0 ft, max 3.2 ft. The remaining large residuals (pair_47_51 -11.8 ft with no band overlap, pair_51_52 -8.6, pair_32_37 +8.5, pair_50_55 +5.3) involve controls outside this audit and are the next candidates.

## Recommended edits to outputs/1912/recipe/controls (not applied)

- pair_40_41.json: a_native 3216.5, b_native 159 (note: Ave L 70 ft, half-width 106)
- pair_36_37.json: a_native 3199, b_native 151
- pair_37_41.json: a_native 3680, b_native 213.5
- pair_37_40.json: a_native 3680 (b 215)
- pair_33_8.json: a_native 3671.5, b_native 212 (extent-centre reading)
- cosmetic: pair_50_51_y corridor "25th St (Rosenberg Ave)", pair_41_45_x corridor "Ave M 1/2", pair_56_57 a_native 3201.5, pair_55_56 3150/104

Then re-solve 36-37 and 40-51 with the similarity mode, since the plate scales carry the rest of the seam steps.

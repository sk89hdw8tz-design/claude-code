# Ring 1 — blind seam census (2026-09-17)

48 seams graded by five blind agents on the branch's own round-5 rubric (`outputs/1912/qc/seams/GRADER_BRIEF_R5.md`), crops rendered from the delivered recipe (band seams via `tools/seamcrops.py`; the nine corner contacts via a direct render of the footprint junction). Graders saw no prior scores.

| score | n | seams |
|---|---|---|
| 5 | 5 | 12_55, 13_14, 14_55, 56_57, 8_35 |
| 4 | 20 | 11_14, 12_14, 33_34, 34_35, 35_36, 35_39, 35_40, 37_40, 40_41, 41_45, 44_45, 45_51, 49_55, 50_51, 50_57, 51_57, 5a_33, 5b_11, 7_34, 8_34 |
| 3 | 10 | 34_39, 36_37, 36_39, 36_40, 37_41, 45_50, 49_56, 55_56, 5b_9, 8_33 |
| 2 | 11 | 11_13, 12_13, 14_49, 36_41, 41_44, 50_55, 50_56, 51_56, 5a_5b, 5a_9, 7_33 |
| 1 | 2 | 5a_7, 5b_13 |

Defect classes (a seam may carry several): tone 34, duplicate-label 19, furniture 15, step 15, rail-utility 10, none 5, gap 5, split-building 2, ownership 2

## Findings by seam

| seam | score | defects | finding | fix hint |
|---|---|---|---|---|
| 5a\|7 | 1 | split-building, rail-utility, step | Cut runs diagonally through the Galveston Wharf Co. terminal yard west of blocks 738-740: the round COTTON (SEED) OIL tank north of the IR.CL. PUMP HO. is drawn on both plates (plate 7 full circle, plate 5a a second arc ~9 ft west) so it reads doubled; plate 7's five diagonal yard tracks start abruptly at the ragged cut ~10 ft from 5a's curved tracks; plate 7's 6" W. PIPE run ends at the cut ~24 ft north of 5a's. | Move the cut so the tank, pump house and diagonal yard tracks come wholly from plate 7 (or wholly from 5a); re-register 7 to 5a on the 6" pipe / 80 ft street crossing. |
| 5b\|13 | 1 | furniture, duplicate-label, ownership, gap | Plate 13's west margin is inside the mosaic: bracket with plate number '13' over the west half of block 687 (lots 101-105) and a second over block 688 below 28th St; sheet numeral shows four times; '28TH ST.' lettered twice ~70 ft apart; rail-yard plate covers block 687's west face with blank paper and its lower edge clips 'AVE. A OR WATER' to 'AVE. A OR WA' and the top of block 748/Elevator B. | Move the vertical cut east to plate 13's inner margin so 5b supplies the west half of 28th St and lots 101-105; route east of plate 13's 28TH ST label; lower the horizontal cut so 5b no longer covers the AVE. A label and block 748. |
| 11\|13 | 2 | furniture, duplicate-label, split-building, ownership, tone | 27th St between 686/626 and 687/627: geometry fine (within 3 ft) but plate 13's margin is inside the map: dark-grey margin strip with border rule and a ~65 ft '13' numeral over the rail yard west of block 687; jagged mask edge covers the NW corner of block 687 (the K of KEMP BREWING CO. missing, west end of the 107-111 building cut); a second '13' in the roadway half hidden; a lone 'ST.' duplicates the full 27TH ST label. | Pull the lower plate's mask inside its neat line; give the yard strip and NW corner of 687 to plate 11 or the yard plate; keep the cut on the 27th St centreline. |
| 12\|13 | 2 | gap, furniture, tone | Corner of 27TH ST and the 70' street between 626/566 and 627/567: dead centre of the intersection a rectangular mid-grey patch ~30x20 ft of off-paper scan background with a white sliver and a lettering fragment; block faces consistent (within ~5 px). | Re-route the cut so the intersection pixels come from a plate whose paper extends across 27th St. |
| 14\|49 | 2 | duplicate-label, furniture, tone | Corner between 446/386 and 447/387: two pink F.A. fire-alarm symbols in the same intersection ~35 ft apart, one on the cut with a clipped 'F.' fragment; faces step <=2.5 ft. | Give the whole intersection to the plate carrying block 446 and move the cut ~60 px south/east. |
| 36\|41 | 2 | furniture, gap, duplicate-label, step, tone | Corner between 77/17 and 78/18: mid-grey off-paper rectangle ~19x26 ft in the intersection; 70' label doubled north and south (clipped '7(' beside a complete 70'); south face of the avenue steps ~5 ft across the vertical cut; west face of the 70' street steps ~5 ft between 77 and 78. | Re-route the cut so the intersection is owned by a plate whose paper covers it; check the block-18/78 plate placement for a ~14 px N-S offset. |
| 41\|44 | 2 | duplicate-label, furniture, step, tone | E-W street between 80/20 and 81/21: at the west end a street label sits on the cut with the top halves hidden; the head of a north arrow with S flourish visible beside it; lower plate reads 3-4.5 ft west at the 80/81 and 20/21 faces; two 80' width tags at the four-corner ~100 ft apart. | Move the cut a few feet at the west end so the label and arrow are wholly on one plate; recheck plate 44 registration. |
| 50\|55 | 2 | gap, furniture, duplicate-label, tone | Corner between 266/206 and 267/207: grey off-paper rectangle ~42x21 ft in the intersection centre with a white sliver and clipped label fragments; width labels double as 70'70'; west face steps ~3.5 ft between 266 and 267. | Route the cut so the intersection is taken from a single plate whose paper covers it. |
| 50\|56 | 2 | duplicate-label, tone | 27th St between 206/146/86 and 207/147/87: pipes and faces align (<1 ft); east of the 1012/1014 alley the cut rises to the block-86 face line and clips the house numbers 1102-1112 (Baptist Church block south frontage) to half height. | East of the 1012/1014 alley drop the cut 40-50 px (14-17 ft) into mid-27th so the 1102-1112 numerals stay whole on the north plate. |
| 51\|56 | 2 | gap, duplicate-label, furniture, tone | Corner between 86/26 and 87/27: horizontal cut runs through the lot-number row 1104-1112 (upper halves only) along block 86's south face; white triangular gap ~9 ft of canvas at the intersection centre beside a grey off-paper patch with a '.G' fragment; faces step 2-3 ft. | Drop the horizontal cut ~20 px south along block 86; extend one plate's ownership across the junction. |
| 5a\|5b | 2 | duplicate-label, furniture, rail-utility, tone | Cut runs E-W through the Galveston Wharf Co's / Gulf Fishery Co. building on Pier 22: footprint matches but lettering ('GULF FISHERY CO. LESSEE', 'NIGHT WATCHMAN REPORTS...') stops at the cut with no continuation on 5b; strong tone step; plate 5a's scale bar sits on the cut left of the PIER 22 label; 6" W. PIPE dashed run beside 22ND ST jogs ~8-12 ft (uncertain). | Drop the cut 60-80 ft south so the whole Gulf Fishery building comes from 5a (or raise it above); steer the west end north of 5a's scale bar. |
| 5a\|9 | 2 | duplicate-label, rail-utility, furniture, step | At the head of Pier 22 the wharf plate's '6" W. PIPE' label is cut to '6"W.PIP' at the seam; the city plate's 6" pipe dash run reaches the cut ~110 px (~40 ft) north of the wharf plate's run; ~six rail tracks on the block-740/741 plate run SW into the cut and terminate against the slip water/quay edge drawn on the wharf plate (20-28 ft overlap); a compass rose sits inside the rail yard just east of the cut; where the lower plate takes over above '22ND' the N-S 6" W. PIPE dash line steps ~44 px (~15 ft) east. | Route the cut along the quay line (keep slip and full pipe label on the wharf plate), give the track bundle and its pipe to one plate through the 22nd St approach, take the compass-rose area from the wharf plate. |
| 7\|33 | 2 | step, rail-utility | 18th St: N-S block faces jog eastward on the lower plate, 677/678 west faces ~9 ft, 617/618 ~5 ft (partly the plates drawing the 70 ft street at different widths); twin-line spur along 737/738 west faces jogs ~10 ft at the cut; westernmost yard track terminates at the cut. | Re-check plate 33 registration against 7 at 18th St (~5 ft east). |
| 34\|39 | 3 | duplicate-label, step, tone | Corner between 437/377 and 438/378: two complete 70' width labels side by side ~16 ft apart at the south of the intersection; east face of the 70' street steps ~3.5 ft between 377 and 378. | Shift the vertical cut ~50 px east south of the avenue; ~8 px lateral nudge. |
| 36\|37 | 3 | duplicate-label, tone | Avenue L between 75-77 and 15-17: geometry <1 ft; west plate's own 'AVENUE L' lettering partly visible as a 'VEN' fragment at the cut beside the east plate's complete label; two '70'' width labels side by side at the top cross street. | Shift the cut ~25-30 px east over the 1440-1520 band to cover the VEN fragment; jog at the top cross street to hide one 70'. |
| 36\|39 | 3 | duplicate-label, tone | Corner between 257/197 and 258/198: left plate's 70 and right plate's 70' overlap on the cut into a garbled '70 0''; ragged tone step; faces within 1.5 ft. | Move the vertical cut ~40 px in the block south of the avenue so the label is whole from one plate. |
| 36\|40 | 3 | step, duplicate-label, tone | 18th St between 197/137/77 and 198/138/78: lower plate reads ~3.5-4.5 ft east at 137/138 and 77/78 faces; pipes carry across with <=1 ft kink; '70 70'' doubled at the east edge belongs to the adjoining vertical seam. | Check plate 40 registration at 77/78 (~4 ft west); fix the doubled 70' on the vertical seam. |
| 37\|41 | 3 | furniture, step | 18th St between 17/NE20/SE20 and 18/NW20/SW20: pipes cross cleanly; west end offset ~2.5-3 ft (slight rotation); in the roadway above 1405-1409 a fragment of a north-arrow flourish (~20 ft) sits on mapped street. | Move the cut a few px at 1401-1411 so the compass fragment falls off the retained plate. |
| 45\|50 | 3 | duplicate-label, step, tone | Corner between 83/23 and 84/24: clipped '70' beside a full 70' north of the avenue centreline; south face of the avenue steps ~3.5 ft across the cut; small white slivers and a stray mark fragment at the cut. | Shift the vertical cut ~40 px east north of the avenue; nudge block-24 plate ~10 px north. |
| 49\|56 | 3 | duplicate-label, tone | 80 ft street between 266/206 and 267/207: edges and pipes continuous; at the four-plate junction a small roadway label is clipped ('E. ..', 'GI..') by a darker sliver. | Move the junction so the small label is wholly on the plate that carries it; clear the sliver. |
| 55\|56 | 3 | step, rail-utility, tone | Ave I (Sealy) between 267-269 and 207-209: plates relatively rotated, frontages differ 3 ft at 267/207 and 4.5 ft at 268/208, 269/209; the 16" pipe arrives at the cut ~5 ft higher on 55 than on 56. | Re-register plate 56 with a small rotation. |
| 5b\|9 | 3 | duplicate-label, rail-utility, tone | Cut along the west face of blocks 682/683 (23rd St): block edges and pipes continuous; two '22ND ST.' labels in the same roadway ~175 ft apart (5a strip and plate 9); two yard tracks from 5b end abruptly against block-682 sidewalk where plate 9's roadway is blank; where the cut jogs west plate 9's blank roadway sits inside the track field. | Keep the cut on plate 9's curb line of 682-683 (no jogs into the roadway); near 22nd St give plate 9's roadway ownership under 5a's second label or move the cut west of it. |
| 8\|33 | 3 | rail-utility, duplicate-label, step, tone | Four-plate corner between 617/557 and 618/558: 10" W. PIPE along the avenue centreline jogs ~4.5 ft at the cut; bottom-left plate's 70' label clipped to a lone '0'' beside the bottom-right plate's 70'; west face of the 70' street steps ~4 ft between 617 and 618; avenue faces ~2.5 ft. | Take the avenue centreline strip from the plate with block 617; push the vertical cut ~30 px east; ~10 px northward nudge of the 618-side plate. |
| 11\|14 | 4 | tone | 27TH ST between 626/566 and 627/567: faces align, alley pipes continuous, label intact; small darker sliver (~15x10 ft) at the four-plate junction. | Optionally give the junction sliver to one plate. |
| 12\|14 | 4 | step | 27th St between 566/506/446 and 567/507/447: block side lines offset a consistent ~2-3 ft E-W and the west pipe shows the same kink; 12" pipe passes cleanly; '14' numeral clipped over blank street (allowed). | Shift plate 14 ~2-3 ft east. |
| 33\|34 | 4 | tone | Ave C (Mechanic) between 615-617 and 555-557: frontages align within ~2 ft; pipes continue with <=2 ft kinks; tone step (33 grey, 34 white). | None beyond tone policy. |
| 34\|35 | 4 | tone | Ave F (Church) between 435-437 and 375-377; cross avenues meet within 1-2 px; west plate greyer. | None; tone only |
| 35\|36 | 4 | tone | Ave I (Sealy) between 255-257 and 195-197: ragged torn-paper tone edge along the seam; faces within 2-4 ft; pipe continuous (12"/10" label difference is source). | Tone only; optionally move the cut a few feet west onto the centreline. |
| 35\|39 | 4 | tone | 18TH ST between 377/317/257 and 378/318/258: all edges and alley pipes continuous; faint lighter tone band in the roadway. | None |
| 35\|40 | 4 | step | 18th St between 257/197 and 258/198: pipes continue with ~1.5 ft kinks; block 257/258 side lines offset ~3 ft E-W. A doubled 70' at the vertical join belongs to the 40/41 or 35/37 corner. | Nudge plate 40 ~3 ft east. |
| 37\|40 | 4 | tone | 80 ft street between 77/17 and 78/18: edges and pipes continuous; grey sliver ~20x26 ft at the four-plate junction. | Give the junction sliver to one plate. |
| 40\|41 | 4 | duplicate-label, tone | Avenue L between 78-80 and 18-20: geometry <1 ft; at top of crop a a '70' label from the west plate sits beside the east plate's '70'' (~17 ft apart). | Jog the cut ~30 px east across the top cross street. |
| 41\|45 | 4 | tone, furniture | 21ST OR CENTER ST between 20/NW19/SW19 and 21/NE18/SE18: faces align, pipe continuous; a compass rose sits in the roadway at Avenue M 1/2 (crop b). | Optional: shift the cut ~40 ft east of block 19 so the rose is outside the mosaic. |
| 44\|45 | 4 | step, tone | Avenue L between 81-83 and 21-23: frontages consistently ~2.5 ft higher on the right plate and the 10" pipe in 22nd St jogs ~4 ft; lettering single; mild tone step. | Nudge plate 45 ~2.5 ft south. |
| 45\|51 | 4 | tone | 24th St between 23/NE17/SE17 and 24/NW17/SW17: alley pipes cross unbroken, faces parallel; a lighter paper patch (~185x30 ft) in the roadway reads as tone. | None; optionally move the cut 40 px so the patch is on one plate. |
| 49\|55 | 4 | furniture | 27th St between 386/326/266 and 387/327/267: faces within 3 ft, pipes carry across, single label; a small clipped arrow tip with S flourish under '27TH', upper part hidden by the cut. | Optional nudge so the glyph is whole or gone. |
| 50\|51 | 4 | tone | Avenue L between 84-86 and 24-26: frontages align within 1-3 px; block 84/24 south line differs ~3.5 ft but the 12" pipe jogs only 2.5 ft (probably source); tone step. | None. |
| 50\|57 | 4 | tone, furniture | E-W street between 86/26 and 87/27: faces within 3 ft; pipes continuous; at the four-corner a clipped text fragment and two 80' tags ~85 ft apart. | Tidy the four-corner vertical seam. |
| 51\|57 | 4 | tone | 27TH ST between 26/NW16/SW16 and 27/NE15/SE15: faces align, pipe continuous; faint tone band; small torn sliver at far right. | None |
| 5a\|33 | 4 | tone, rail-utility, furniture | N-S cut between the rail yard (5a) and blocks 736 (County Jail)/737 (Texas Oil): a ~115 ft blank strip of distinct tone; a heavy ruled line at its top stops dead at the cut (spur or 5a neat-line fragment); buildings continuous; Ave A blocks align within 2 ft. | Verify whether the strip lies outside 5a's neat line; if so pull 5a's mask back. |
| 5b\|11 | 4 | tone, rail-utility | Vertical cut between the wharf tracks (5b) and the Ave A block faces 2401-2627 (11): tracks and lettering single and continuous; 5b's 12" W. PIPE in the 25th St extension dead-ends at the seam (plate 11 draws no pipe there: likely source omission); clear tone step. | Check plate 11 for a 12" main; else accept as source. |
| 7\|34 | 4 | rail-utility, tone | 80 ft street between 617/557 and 618/558: faces align within 2-4 ft; the 10" W. PIPE elbow at the 617/557 corner is missing for ~50 ft across the cut; a grey sliver ~20x25 ft at the four-plate junction. | Move the cut ~30 ft off the pipe elbow so one plate draws the turn; clear the junction sliver. |
| 8\|34 | 4 | step | 18th St between 557/497/437 and 558/498/438: pipes cross without jog, labels single; block side lines match at the west end but drift to ~2.5-3 ft at the east end (slight relative rotation). | Optional: rotate plate 34 ~0.2 deg. |
| 12\|55 | 5 | none | 80' avenue between 446/386 (Seaboard Lumber) and 447/387; alley pipes unbroken, faces align (<1 ft). | None |
| 13\|14 | 5 | none | Ave C (Mechanic) between 627-629 and 567-569: faces align within ~1 ft; pipes continuous; one label; slight tone only. | None |
| 14\|55 | 5 | none | Ave F (Church) between 447-449 and 387-389: block ends align within ~2 ft; pipe labelled 10"/16" is a source disagreement. | None |
| 56\|57 | 5 | none | Avenue L between 87-89 and 27-29; faces meet within 1 px; 16"/12" pipe label difference is a source difference. | None |
| 8\|35 | 5 | none | 80' avenue between blocks 437/377 and 438/378; alley pipes run straight through, faces parallel (<1 ft). | None |

## What this means

Under blind grading ring 1 is **not** AAA: 5 of 48 seams score 5, 20 score 4, 23 score 3 or below. The round-5 census on the branch had 33 fives for these same seams; the difference is mostly that these graders were stricter on 2-5 ft steps and doubled width tags, and that the nine corner contacts (never graded before) all score 2-3.

The defects fall into four systematic classes, none of which is a one-line fix:

1. **Four-plate street junctions** (every corner seam, plus 36|41, 50|55, 12|13 ...): two seams cross inside the intersection, each plate's paper stops part-way across (grey/white patches) and every plate's `70'`/`80'` width tag and adjoining numeral survives, so tags double. A junction-square re-ownership was tried (`tools/junctionfix.py`, 29 junctions) and **rejected**: it removes the patches but leaves the squares visible as tone patches and still cuts through tags (`junctions_after/_montage_square_fix_rejected.jpg`). The real fix is to box each plate's edge width tags as furniture (as the pipeline already does for adjoining numerals) so an intersection can be owned by one plate with the others' tags cut: about 15 plates x 8 tags, each box reviewed.
2. **Wharf plates 5a/5b against 7/9/11/13/33** (5a|7 = 1, 5b|13 = 1, 5a|5b, 5a|9, 5b|9 = 2-3): the frontage cuts run through the terminal yard, double the cotton-oil tank, clip the Gulf Fishery building lettering, and plate 13's margin bracket and numeral sit inside the map. Needs a re-designed cut along the quay/neatline for each pair and a furniture box for 13's west margin.
3. **Registration steps of 2-5 ft** on about 12 seams (plates 33, 34, 40, 44/45, 14, 56 and the 36/41 corner): below the old 6 ft bar but visible; local re-solves with the branch's `tools/localsolve.py` on the observer controls, one plate at a time.
4. **Label clipping on long seams** (50|56 house numbers 1102-1112, 51|56 lot row 1104-1116, 36|37 'VEN' fragment, 41|44 street label): the min-ink path runs along a block face; a 15-20 ft nudge of the cut in that stretch.

Tone (34 seams) is reported but by policy not corrected.

Nothing in the delivered recipe was changed by this census. Proposed order: class 2 (worst scores, self-contained), then 4, then 3, then 1 -- each with before/after crops and a blind re-grade, ring 1 only.


# Ring 1 — blind seam census v2 (2026-09-17, after the AAA pass)

Same rubric, same crop method, five fresh blind graders. 47 seams (8|35 no longer shares ground after the re-cut).

| score | v1 (before) | v2 (after) |
|---|---|---|
| 5 | 5 | 3 |
| 4 | 20 | 17 |
| 3 | 10 | 19 |
| 2 | 11 | 8 |
| 1 | 2 | 0 |

Improved: 13 seams (11_13, 12_13, 12_14, 36_37, 36_41, 50_56, 51_56, 5a_5b, 5a_7, 5a_9, 5b_11, 5b_13, 5b_9). Worse: 13 (12_55, 13_14, 14_55, 33_34, 34_35, 35_39, 35_40, 41_45, 49_55, 50_57, 55_56, 56_57, 7_34). Defect classes now: tone 31, rail-utility 15, furniture 14, step 14, duplicate-label 12, gap 6, none 3

## What was done between v1 and v2

- **Class 2, wharf plate 5** — frontage seams made straight and pinned 60 px inside the block plates' neatlines (5a|7, 5a|9, 5b|9, 5b|11, 5b|13, new 5a|33); the panel break 5a|5b moved south of the Gulf Fishery building; six declared local nudges (`seams/nudges.json`) so 5a keeps the whole Pier 21 shed and its pipe note and 5b the whole Mallory shed; plates 7 and 9 compass roses boxed. A latent bug fixed in `tools/streetcut.py`: a `_x` registration tie next to a seam-position control was silently moving the 5b seams to Ave A (plate 13's margin bracket inside the map was that). Scores: 5a|7 1→5, 5b|13 1→3, 5b|11 2→5, 5a|5b 2→4, 5a|9 2→4, 5b|9 3→4, 5a|33 4→4.
- **Class 4, label clipping** — root cause on 50|56 was plate 50's scale-bar furniture box swallowing the house-number row; box lowered. `tools/seamnudge.py` + `seams/nudges.json` added for declared local seam moves. 36|37 3→4, 50|56 2→3 (a doubled T.H. hydrant label remains).
- **Class 3, registration** — 15 contradictory controls re-read blind: no plate misread; five controls had applied an 80 ft half-width to the 70 ft Avenue L or read an edge instead of the extent centre. Corrected and the 13 ring plates re-solved (similarity) against the frozen core: band residual median 1.2 ft. Graders still see 2–4 ft steps on 33|34, 34|35, 35|39, 7|33, 7|34, 55|56: these sit against core plates 7/8 and among 33–35, where the remaining disagreement is between the plates' own drawings (block depths differ 8 px) and the frozen core cannot move.
- **Class 1, junction width tags** — `tools/widthtag.py` detected 384 edge width tags; 322 unflagged ones recorded as furniture. Round 1 cut them wherever a neighbour's paper covered, which left grey placeholder squares and tag islands (the neighbour has its own tag there) — that is what the v2 graders saw as 'grey rectangle patches'. Round 2 (`tools/junctiontags.py`, applied AFTER the v2 crops were rendered) keeps one plate's tags per street-end cluster and cuts the others only where the keeper's paper covers: the three test junctions now show one tag per street and no grey (`junctions_after/_montage_widthtag_keeper.jpg`). **v2 scores on junction seams therefore understate the current state; a v3 census of the 20 junction-affected seams is the first task next session.**

## Still open after this pass

1. Registration steps of 2–4 ft against the frozen core (7|33, 7|34, 35|39, 33|34, 34|35, 55|56, 37|41 east end): only a decision to let ring plates carry a small rotation against the core's row, or to re-read the core-side controls, can close these.
2. Doubled fire-alarm boxes at 12|55 and 14|49 (both plates draw the F.A. at the same corner ~40 ft apart): give the intersection square to one plate.
3. Doubled T.H. hydrant labels at 50|56 and 51|56, and the north arrow halves at 41|45 / 41|44 / 49|55: per-spot nudges or furniture boxes.
4. 1–2 px white hairlines at region joins (tiling audit: 11 cut-line hairlines): a 2 px dilation of the winning region at those joins.
5. Tone steps on 34 seams: by policy not corrected.

Full per-seam findings: `grades/v2/blind_census_v2.json` (scores) and the five grader hand-backs in this session's log; v1 findings remain in `grades/blind_census_v1.json`.

## Scores by seam (v1 → v2)

| seam | v1 | v2 | v2 defects |
|---|---|---|---|
| 12|55 | 5 | 2 | duplicate-label, gap, tone |
| 14|49 | 2 | 2 | duplicate-label |
| 41|44 | 2 | 2 | duplicate-label, furniture |
| 50|55 | 2 | 2 | duplicate-label, furniture, tone |
| 50|57 | 4 | 2 | duplicate-label, furniture, tone |
| 55|56 | 3 | 2 | gap, step, rail-utility, tone |
| 7|33 | 2 | 2 | step, rail-utility |
| 7|34 | 4 | 2 | step, rail-utility, gap, tone |
| 11|13 | 2 | 3 | rail-utility, tone |
| 33|34 | 4 | 3 | step, rail-utility, tone, furniture |
| 34|35 | 4 | 3 | step, tone |
| 34|39 | 3 | 3 | duplicate-label, gap |
| 35|39 | 4 | 3 | step, tone |
| 35|40 | 4 | 3 | furniture, step |
| 36|39 | 3 | 3 | duplicate-label |
| 36|40 | 3 | 3 | furniture |
| 36|41 | 2 | 3 | rail-utility, tone |
| 37|41 | 3 | 3 | step, tone |
| 41|45 | 4 | 3 | furniture, tone |
| 45|50 | 3 | 3 | duplicate-label, step, furniture, tone |
| 49|55 | 4 | 3 | furniture |
| 49|56 | 3 | 3 | duplicate-label, step, tone |
| 50|56 | 2 | 3 | duplicate-label, rail-utility, gap |
| 51|56 | 2 | 3 | duplicate-label, rail-utility, tone |
| 56|57 | 5 | 3 | rail-utility, gap, tone |
| 5b|13 | 1 | 3 | furniture, tone |
| 8|33 | 3 | 3 | rail-utility, duplicate-label |
| 11|14 | 4 | 4 | tone |
| 12|13 | 2 | 4 | tone |
| 13|14 | 5 | 4 | rail-utility, tone |
| 14|55 | 5 | 4 | tone |
| 35|36 | 4 | 4 | tone |
| 36|37 | 3 | 4 | rail-utility, step, tone |
| 37|40 | 4 | 4 | step, furniture |
| 40|41 | 4 | 4 | rail-utility, tone |
| 44|45 | 4 | 4 | step, rail-utility, tone |
| 45|51 | 4 | 4 | tone |
| 50|51 | 4 | 4 | step, tone, furniture |
| 51|57 | 4 | 4 | rail-utility |
| 5a|33 | 4 | 4 | tone |
| 5a|5b | 2 | 4 | furniture, tone |
| 5a|9 | 2 | 4 | tone |
| 5b|9 | 3 | 4 | tone |
| 8|34 | 4 | 4 | furniture |
| 12|14 | 4 | 5 | none |
| 5a|7 | 1 | 5 | none |
| 5b|11 | 4 | 5 | none |

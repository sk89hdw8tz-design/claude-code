# Quality control

Profile `galveston1889` -- 2026-08-14T19:17:00+00:00

- transform model: **similarity**
- anchor region: `S9`
- coverage: 87.4% (remainder transparent; no synthesised content)

## Residuals

| set | n | median | rms | p90 | max |
|---|---|---|---|---|---|
| at control points | 37 | 8.84 | 27.35 | 48.31 | 66.20 |
| held out (cross-validated) | 37 | 31.12 | 490.67 | 88.02 | 2635.74 |

Target: median <= 5 px, nothing unexplained above 15 px.

## Seams

| sheet A | sheet B | contact | n | median px | max px | bias | scatter | reading |
|---|---|---|---|---|---|---|---|---|
| S10 | S27 | edge | 3 | 26.98 | 66.20 | 14.67 | 38.33 | SCATTERED -- consistent with drafting/survey disagreement between the two 1889 sheets rather than processing error |
| S10 | S29 | none | 1 | 27.07 | 27.07 | 0.00 | 0.00 | too few points to classify |
| S10 | S7 | none | 1 | 3.72 | 3.72 | 0.00 | 0.00 | too few points to classify |
| S10 | S8 | edge | 4 | 11.71 | 56.20 | 15.16 | 18.64 | mixed |
| S10 | S9 | edge | 3 | 33.60 | 59.38 | 18.08 | 34.14 | mixed |
| S1_main | S7 | none | 1 | 0.94 | 0.94 | 0.00 | 0.00 | too few points to classify |
| S1_main | S9 | edge | 4 | 37.36 | 57.62 | 15.88 | 34.45 | SCATTERED -- consistent with drafting/survey disagreement between the two 1889 sheets rather than processing error |
| S2 | S7 | edge | 3 | 3.22 | 38.55 | 10.85 | 14.07 | mixed |
| S27 | S29 | edge | 4 | 11.19 | 27.02 | 7.94 | 12.64 | mixed |
| S27 | S8 | corner | 1 | 37.77 | 37.77 | 0.00 | 0.00 | too few points to classify |
| S29 | S8 | edge | 4 | 27.58 | 33.65 | 7.76 | 24.11 | SCATTERED -- consistent with drafting/survey disagreement between the two 1889 sheets rather than processing error |
| S7 | S8 | edge | 4 | 5.22 | 23.94 | 5.86 | 9.13 | mixed |
| S7 | S9 | edge | 3 | 4.67 | 5.79 | 0.80 | 4.94 | SCATTERED -- consistent with drafting/survey disagreement between the two 1889 sheets rather than processing error |
| S8 | S9 | none | 1 | 7.63 | 7.63 | 0.00 | 0.00 | too few points to classify |

`bias` is the mean displacement of the whole seam (a systematic shift points at processing); `scatter` is the spread about that mean (which points at genuine 1889 disagreement).

## Seam panels

27 full-resolution panels in `output/qc/seam_report/`. Each shows sheet A alone, sheet B alone, then the merged mosaic, so a street that only *looks* continuous because one sheet covers the other's error is visible.

Pixel step across seams: median ratio 9.63, max 28.98 (1.0 = indistinguishable from ordinary adjacent pixels).

## Verdict

- median 8.84 px EXCEEDS the 5 px target
- 17 point(s) exceed 15 px

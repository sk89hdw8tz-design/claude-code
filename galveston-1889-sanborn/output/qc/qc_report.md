# Quality control

Profile `galveston1889` -- 2026-08-14T19:41:38+00:00

- transform model: **similarity**
- anchor region: `S9`
- coverage: 86.7% (remainder transparent; no synthesised content)

## Residuals

| set | n | median | rms | p90 | max |
|---|---|---|---|---|---|
| at control points | 32 | 4.87 | 22.63 | 42.87 | 63.79 |
| held out (cross-validated) | 32 | 36.23 | 9457.47 | 770.21 | 53113.59 |

Target: median <= 5 px, nothing unexplained above 15 px.

## Seams

| sheet A | sheet B | contact | n | median px | max px | bias | scatter | reading |
|---|---|---|---|---|---|---|---|---|
| S10 | S27 | edge | 4 | 8.42 | 31.01 | 5.53 | 12.02 | SCATTERED -- consistent with drafting/survey disagreement between the two 1889 sheets rather than processing error |
| S10 | S7 | none | 1 | 3.13 | 3.13 | 0.00 | 0.00 | too few points to classify |
| S10 | S8 | edge | 4 | 5.95 | 43.56 | 8.86 | 14.20 | mixed |
| S10 | S9 | corner | 4 | 36.05 | 63.79 | 27.76 | 34.28 | mixed |
| S1_main | S9 | edge | 2 | 0.00 | 0.00 | 0.00 | 0.00 | too few points to classify |
| S2 | S7 | edge | 4 | 7.13 | 48.84 | 9.55 | 15.07 | mixed |
| S2 | S9 | none | 1 | 18.75 | 18.75 | 0.00 | 0.00 | too few points to classify |
| S27 | S8 | none | 1 | 2.20 | 2.20 | 0.00 | 0.00 | too few points to classify |
| S29 | S8 | edge | 2 | 0.00 | 0.00 | 0.00 | 0.00 | too few points to classify |
| S7 | S8 | edge | 4 | 4.97 | 9.98 | 3.00 | 4.97 | mixed |
| S7 | S9 | corner | 4 | 22.99 | 36.64 | 9.01 | 20.68 | SCATTERED -- consistent with drafting/survey disagreement between the two 1889 sheets rather than processing error |
| S8 | S9 | corner | 1 | 4.84 | 4.84 | 0.00 | 0.00 | too few points to classify |

`bias` is the mean displacement of the whole seam (a systematic shift points at processing); `scatter` is the spread about that mean (which points at genuine 1889 disagreement).

## Seam panels

25 full-resolution panels in `output/qc/seam_report/`. Each shows sheet A alone, sheet B alone, then the merged mosaic, so a street that only *looks* continuous because one sheet covers the other's error is visible.

Pixel step across seams: median ratio 3.79, max 12.73 (1.0 = indistinguishable from ordinary adjacent pixels).

## Verdict

- median 4.87 px meets the <= 5 px target
- 9 point(s) exceed 15 px

# Quality control

Profile `synthetic` -- 2026-08-14T18:05:28+00:00

- transform model: **similarity**
- anchor region: `S2`
- coverage: 93.1% (remainder transparent; no synthesised content)

## Residuals

| set | n | median | rms | p90 | max |
|---|---|---|---|---|---|
| at control points | 62 | 2.43 | 3.49 | 4.45 | 14.62 |
| held out (cross-validated) | 62 | 3.08 | 4.60 | 5.67 | 18.42 |

Target: median <= 5 px, nothing unexplained above 15 px.

## Seams

| sheet A | sheet B | contact | n | median px | max px | bias | scatter | reading |
|---|---|---|---|---|---|---|---|---|
| S10 | S1_main | edge | 1 | 0.28 | 0.28 | 0.00 | 0.00 | too few points to classify |
| S10 | S2 | edge | 10 | 3.09 | 5.46 | 0.14 | 3.09 | SCATTERED -- consistent with drafting/survey disagreement between the two 1889 sheets rather than processing error |
| S10 | S27 | edge | 6 | 3.03 | 14.62 | 1.58 | 4.00 | SCATTERED -- consistent with drafting/survey disagreement between the two 1889 sheets rather than processing error |
| S10 | S7 | edge | 2 | 2.44 | 3.41 | 0.00 | 0.00 | too few points to classify |
| S10 | S9 | edge | 5 | 2.39 | 3.22 | 0.25 | 2.42 | SCATTERED -- consistent with drafting/survey disagreement between the two 1889 sheets rather than processing error |
| S1_main | S2 | edge | 5 | 1.50 | 4.26 | 0.34 | 1.62 | SCATTERED -- consistent with drafting/survey disagreement between the two 1889 sheets rather than processing error |
| S1_main | S9 | edge | 4 | 2.45 | 4.38 | 0.40 | 2.58 | SCATTERED -- consistent with drafting/survey disagreement between the two 1889 sheets rather than processing error |
| S2 | S27 | edge | 2 | 1.79 | 2.10 | 0.00 | 0.00 | too few points to classify |
| S2 | S7 | edge | 6 | 2.93 | 3.58 | 0.44 | 2.90 | SCATTERED -- consistent with drafting/survey disagreement between the two 1889 sheets rather than processing error |
| S2 | S9 | edge | 1 | 0.95 | 0.95 | 0.00 | 0.00 | too few points to classify |
| S27 | S29 | edge | 5 | 3.20 | 8.49 | 1.31 | 4.43 | SCATTERED -- consistent with drafting/survey disagreement between the two 1889 sheets rather than processing error |
| S27 | S7 | edge | 3 | 0.75 | 2.45 | 0.99 | 0.87 | mixed |
| S29 | S7 | edge | 1 | 1.29 | 1.29 | 0.00 | 0.00 | too few points to classify |
| S29 | S8 | edge | 6 | 1.55 | 2.69 | 0.59 | 1.28 | SCATTERED -- consistent with drafting/survey disagreement between the two 1889 sheets rather than processing error |
| S7 | S8 | edge | 5 | 3.22 | 4.51 | 0.71 | 2.68 | SCATTERED -- consistent with drafting/survey disagreement between the two 1889 sheets rather than processing error |

`bias` is the mean displacement of the whole seam (a systematic shift points at processing); `scatter` is the spread about that mean (which points at genuine 1889 disagreement).

## Seam panels

76 full-resolution panels in `output/qc/seam_report/`. Each shows sheet A alone, sheet B alone, then the merged mosaic, so a street that only *looks* continuous because one sheet covers the other's error is visible.

Pixel step across seams: median ratio 6.51, max 71.53 (1.0 = indistinguishable from ordinary adjacent pixels).

## Verdict

- median 2.43 px meets the <= 5 px target

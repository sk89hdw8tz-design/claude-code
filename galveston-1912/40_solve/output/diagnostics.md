# Solve diagnostics -- Galveston 1912 12-sheet block

- Gauge: sheet 10 fixed to identity (mosaic frame = sheet 10 centered pixel frame). Its zero covariance is a gauge artefact, not precision.
- Along-seam direction linearized to axis unit vectors (near-axis-aligned assumption; rotations are sub-degree).
- Solved sheets: [7, 8, 9, 10, 11, 12, 39, 40, 43, 44, 49, 50]
- Observations used: 99 (+ kappa prior); parameters: 45; rank 45; dof 66
- Robust variance factor s0^2 = 4.291
- Kappa posterior: 5.8263 +- 0.3055 px/ft (prior 6.07 +- 0.15; unscaled marginal std 0.1475). Compare with per-plate drafted widths before reuse.
- **Kappa is prior-determined, not measured**: the across-seam loop structure cancels kappa against sheet translations exactly, so the data cannot constrain it. The across constraints therefore enforce W_ft x prior kappa; validate kappa against per-plate drafted widths directly.

## Seams loaded

| seam | axis | boundary | W (ft) | accepted | rejected | context |
|---|---|---|---|---|---|---|
| 10-12 | horizontal | 24th St | 70 | 2 | 0 | 0 |
| 10-43 | vertical | Ave F (Church) | 80 | 2 | 0 | 0 |
| 11-12 | vertical | Ave C (Mechanic) | 70 | 2 | 0 | 0 |
| 12-49 | vertical | Ave F (Church) | 70 | 2 | 0 | 0 |
| 39-40 | vertical | Ave I (Sealy) | 80 | 2 | 0 | 0 |
| 39-43 | horizontal | 21st (Center) St | 70 | 2 | 0 | 0 |
| 40-44 | horizontal | 21st (Center) St | 80 | 2 | 0 | 0 |
| 43-44 | vertical | Ave I (Sealy) | 80 | 2 | 0 | 0 |
| 43-49 | horizontal | 24th St | 70 | 2 | 0 | 0 |
| 44-50 | horizontal | 24th St | 80 | 2 | 0 | 0 |
| 49-50 | vertical | Ave I (Sealy) | 80 | 2 | 0 | 0 |
| 7-8 | vertical | Ave C (Mechanic) | 70 | 2 | 0 | 0 |
| 7-9 | horizontal | 21st (Center) St | 80 | 2 | 0 | 0 |
| 8-10 | horizontal | 21st (Center) St | 70 | 2 | 0 | 0 |
| 8-39 | vertical | Ave F (Church) | 80 | 2 | 0 | 0 |
| 9-10 | vertical | Ave C (Mechanic) | 70 | 2 | 0 | 0 |
| 9-11 | horizontal | 24th St | 80 | 1 | 0 | 0 |

## Residual RMS

By type:
- across: RMS 30.97 px (n=33)
- along: RMS 7.53 px (n=66)

By seam:
| seam | n | RMS (px) | max |abs| (px) |
|---|---|---|---|
| 10-12 | 6 | 7.11 | 11.35 |
| 10-43 | 6 | 16.93 | 32.22 |
| 11-12 | 6 | 38.50 | 91.27 |
| 12-49 | 6 | 49.10 | 94.79 |
| 39-40 | 6 | 6.25 | 10.94 |
| 39-43 | 6 | 10.08 | 17.93 |
| 40-44 | 6 | 5.96 | 12.11 |
| 43-44 | 6 | 3.65 | 7.26 |
| 43-49 | 6 | 8.61 | 15.64 |
| 44-50 | 6 | 8.93 | 15.60 |
| 49-50 | 6 | 6.59 | 13.82 |
| 7-8 | 6 | 12.44 | 25.38 |
| 7-9 | 6 | 19.91 | 43.41 |
| 8-10 | 6 | 9.45 | 17.84 |
| 8-39 | 6 | 6.38 | 12.95 |
| 9-10 | 6 | 24.48 | 37.88 |
| 9-11 | 3 | 0.51 | 0.89 |

## Per-sheet marginal uncertainty (theta, s)

| sheet | theta std (mrad) | s std (ppm) | tx std (px) | ty std (px) | flag |
|---|---|---|---|---|---|
| 7 | 3.294 | 3105.2 | 27.91 | 29.13 | **ROTATION > 1.5 mrad** |
| 8 | 3.001 | 2137.0 | 9.45 | 26.54 | **ROTATION > 1.5 mrad** |
| 9 | 3.218 | 3070.4 | 26.58 | 10.43 | **ROTATION > 1.5 mrad** |
| 10 | 0.000 | 0.0 | 0.00 | 0.00 | GAUGE |
| 11 | 3.629 | 3543.6 | 28.94 | 30.26 | **ROTATION > 1.5 mrad** |
| 12 | 3.138 | 2419.0 | 10.27 | 27.19 | **ROTATION > 1.5 mrad** |
| 39 | 2.818 | 2520.9 | 29.11 | 27.71 | **ROTATION > 1.5 mrad** |
| 40 | 3.459 | 3048.9 | 54.67 | 31.34 | **ROTATION > 1.5 mrad** |
| 43 | 2.390 | 2284.5 | 28.54 | 7.52 | **ROTATION > 1.5 mrad** |
| 44 | 3.047 | 2749.3 | 54.18 | 16.20 | **ROTATION > 1.5 mrad** |
| 49 | 2.980 | 2551.3 | 30.09 | 28.14 | **ROTATION > 1.5 mrad** |
| 50 | 3.475 | 2992.9 | 54.94 | 32.18 | **ROTATION > 1.5 mrad** |

Flagged sheets (rotation std > 1.5 mrad): **[7, 8, 9, 11, 12, 39, 40, 43, 44, 49, 50]**

## Down-weighted observations (Huber, delta = 2.5 sigma)

11 of 99 observations down-weighted (never dropped):
| seam | anchor | type | face | residual (px) | norm. resid | huber w |
|---|---|---|---|---|---|---|
| 10-12 | Ave D (Market) | along | 1 | 11.35 | 4.01 | 0.623 |
| 10-12 | Ave E (Post Office) | along | 2 | -10.84 | -3.83 | 0.652 |
| 10-43 | 23rd St | along | 1 | 20.17 | 5.17 | 0.484 |
| 10-43 | 23rd St | across | 1 | -32.22 | -2.68 | 0.931 |
| 11-12 | 25th St (Rosenberg) | along | 2 | 17.02 | 4.72 | 0.530 |
| 11-12 | 25th St (Rosenberg) | across | 1 | -91.27 | -7.61 | 0.329 |
| 12-49 | 25th St (Rosenberg Ave) | across | 1 | 94.79 | 7.90 | 0.316 |
| 12-49 | 26th St | across | 1 | 73.46 | 6.12 | 0.408 |
| 7-9 | Ave B (Strand) | across | 1 | -43.41 | -3.62 | 0.691 |
| 9-10 | 22nd St | along | 2 | 36.53 | 7.31 | 0.342 |
| 9-10 | 23rd St | along | 2 | -21.96 | -4.13 | 0.605 |

## Through-street collinearity

Street center points (mean of the two face midpoints per pair/sheet) mapped to the mosaic; TLS line per street.
| street | axis | points | seams | max perp dev (px) | RMS dev (px) |
|---|---|---|---|---|---|
| 19th St | vertical | 6 | 39-40, 7-8, 8-39 | 5.79 | 3.79 |
| 20th St | vertical | 6 | 39-40, 7-8, 8-39 | 46.58 | 29.69 |
| 22nd St | vertical | 6 | 10-43, 43-44, 9-10 | 12.72 | 7.11 |
| 23rd St | vertical | 6 | 10-43, 43-44, 9-10 | 17.03 | 9.12 |
| 25th St (Rosenberg Ave) | vertical | 4 | 12-49, 49-50 | 2.46 | 1.64 |
| 26th St | vertical | 6 | 11-12, 12-49, 49-50 | 21.57 | 14.22 |
| Ave B (Strand) | horizontal | 4 | 7-9, 9-11 | 0.69 | 0.62 |
| Ave D (Market) | horizontal | 4 | 10-12, 8-10 | 3.02 | 2.06 |
| Ave E (Post Office) | horizontal | 4 | 10-12, 8-10 | 5.12 | 3.54 |
| Ave G (Winnie) | horizontal | 4 | 39-43, 43-49 | 1.34 | 0.92 |
| Ave H (Ball) | horizontal | 4 | 39-43, 43-49 | 1.95 | 1.40 |
| Ave J (Broadway) | horizontal | 4 | 40-44, 44-50 | 0.76 | 0.51 |
| Ave K | horizontal | 4 | 40-44, 44-50 | 3.59 | 3.12 |

### Ave I (Sealy) kink check -- column-4 points vs line through columns 1-3

| street | col4 sheets | col4 deviations (px) | max |abs| |
|---|---|---|---|
| 19th St | [40] | -5.54 | 5.54 |
| 20th St | [40] | -44.58 | 44.58 |
| 22nd St | [44] | -1.10 | 1.10 |
| 23rd St | [44] | +12.34 | 12.34 |
| 25th St (Rosenberg Ave) | [50] | +0.05 | 0.05 |
| 26th St | [50] | -16.42 | 16.42 |

## Leave-one-seam-out

| seam | status | n pred | pred RMS (px) | pred max (px) |
|---|---|---|---|---|
| 10-12 | ok | 4 | 135.25 | 147.26 |
| 10-43 | ok | 4 | 49.72 | 64.06 |
| 11-12 | ok | 4 | 2606.21 | 2649.93 |
| 12-49 | ok | 4 | 19.27 | 31.17 |
| 39-40 | ok | 4 | 39.16 | 43.03 |
| 39-43 | ok | 4 | 30.81 | 32.61 |
| 40-44 | ok | 4 | 16.01 | 21.86 |
| 43-44 | ok | 4 | 19.76 | 24.67 |
| 43-49 | ok | 4 | 63.92 | 71.61 |
| 44-50 | ok | 4 | 18.00 | 20.30 |
| 49-50 | ok | 4 | 53.99 | 56.36 |
| 7-8 | ok | 4 | 167.12 | 187.59 |
| 7-9 | ok | 4 | 73.26 | 94.13 |
| 8-10 | ok | 4 | 70.83 | 78.13 |
| 8-39 | ok | 4 | 46.26 | 55.37 |
| 9-10 | ok | 4 | 117.17 | 143.04 |
| 9-11 | ok | 2 | 121.87 | 123.10 |

## Load / solve log

- [load] pair_05A_07.json: non-block pair ['5A', '7'] (sheet-5 attachment); set aside for the panel-fit stage
- [load] pair_05A_09.json: non-block pair ['5A', '9'] (sheet-5 attachment); set aside for the panel-fit stage
- [load] pair_05B_09.json: non-block pair ['5B', '9'] (sheet-5 attachment); set aside for the panel-fit stage
- [load] pair_05B_11.json: non-block pair ['5B', '11'] (sheet-5 attachment); set aside for the panel-fit stage
- [load] pair_05B_13.json: non-block pair ['5B', '13'] (sheet-5 attachment); set aside for the panel-fit stage
- [load] pair_10_12.json/Ave D (Market): side 'A' has no valid sigma_along_px; using fallback 2.0 px
- [load] pair_10_12.json/Ave D (Market): side 'B' has no valid sigma_along_px; using fallback 2.0 px
- [load] pair_10_12.json/Ave E (Post Office): side 'A' has no valid sigma_along_px; using fallback 2.0 px
- [load] pair_10_12.json/Ave E (Post Office): side 'B' has no valid sigma_along_px; using fallback 2.0 px
- [width] seam 10-12: overriding default 80 ft with annotated 70 ft (drafted evidence implies 68.8 ft, scatter 2.2 ft)
- [width] seam 10-12: using W = 70 ft (24th St)
- [load] pair_10_12.json: seam 10-12 (horizontal, 24th St): 2 accepted, 0 rejected, 0 context-only
- [width] seam 10-43: overriding default 70 ft with annotated 80 ft (drafted evidence implies 82.3 ft, scatter 3.3 ft)
- [width] seam 10-43: using W = 80 ft (Ave F (Church))
- [load] pair_10_43.json: seam 10-43 (vertical, Ave F (Church)): 2 accepted, 0 rejected, 0 context-only
- [width] seam 11-12: drafted evidence implies 100.7 ft vs table 70 ft (scatter 38.1 ft) -- kept table value, flagged for review
- [width] seam 11-12: using W = 70 ft (Ave C (Mechanic))
- [load] pair_11_12.json: seam 11-12 (vertical, Ave C (Mechanic)): 2 accepted, 0 rejected, 0 context-only
- [width] seam 12-49: drafted evidence implies 99.3 ft vs table 70 ft (scatter 41.2 ft) -- kept table value, flagged for review
- [width] seam 12-49: using W = 70 ft (Ave F (Church))
- [load] pair_12_49.json: seam 12-49 (vertical, Ave F (Church)): 2 accepted, 0 rejected, 0 context-only
- [width] seam 39-40: using W = 80 ft (Ave I (Sealy))
- [load] pair_39_40.json: seam 39-40 (vertical, Ave I (Sealy)): 2 accepted, 0 rejected, 0 context-only
- [width] seam 39-43: overriding default 80 ft with annotated 70 ft (drafted evidence implies 69.4 ft, scatter 0.7 ft)
- [width] seam 39-43: using W = 70 ft (21st (Center) St)
- [load] pair_39_43.json: seam 39-43 (horizontal, 21st (Center) St): 2 accepted, 0 rejected, 0 context-only
- [width] seam 40-44: using W = 80 ft (21st (Center) St)
- [load] pair_40_44.json: seam 40-44 (horizontal, 21st (Center) St): 2 accepted, 0 rejected, 0 context-only
- [width] seam 43-44: using W = 80 ft (Ave I (Sealy))
- [load] pair_43_44.json: seam 43-44 (vertical, Ave I (Sealy)): 2 accepted, 0 rejected, 0 context-only
- [width] seam 43-49: overriding default 80 ft with annotated 70 ft (drafted evidence implies 69.6 ft, scatter 1.6 ft)
- [width] seam 43-49: using W = 70 ft (24th St)
- [load] pair_43_49.json: seam 43-49 (horizontal, 24th St): 2 accepted, 0 rejected, 0 context-only
- [width] seam 44-50: drafted evidence implies 85.0 ft vs table 80 ft (scatter 30.1 ft) -- kept table value, flagged for review
- [width] seam 44-50: using W = 80 ft (24th St)
- [load] pair_44_50.json: seam 44-50 (horizontal, 24th St): 2 accepted, 0 rejected, 0 context-only
- [width] seam 49-50: drafted evidence implies 99.4 ft vs table 80 ft (scatter 41.2 ft) -- kept table value, flagged for review
- [width] seam 49-50: using W = 80 ft (Ave I (Sealy))
- [load] pair_49_50.json: seam 49-50 (vertical, Ave I (Sealy)): 2 accepted, 0 rejected, 0 context-only
- [width] seam 7-8: drafted evidence implies 101.4 ft vs table 70 ft (scatter 44.0 ft) -- kept table value, flagged for review
- [width] seam 7-8: using W = 70 ft (Ave C (Mechanic))
- [load] pair_7_8.json: seam 7-8 (vertical, Ave C (Mechanic)): 2 accepted, 0 rejected, 0 context-only
- [load] pair_7_9.json/Ave A (Water): side 'A' has no valid sigma_along_px; using fallback 2.0 px
- [load] pair_7_9.json/Ave A (Water): side 'B' has no valid sigma_along_px; using fallback 2.0 px
- [load] pair_7_9.json/Ave B (Strand): side 'A' has no valid sigma_along_px; using fallback 2.0 px
- [load] pair_7_9.json/Ave B (Strand): side 'B' has no valid sigma_along_px; using fallback 2.0 px
- [width] seam 7-9: drafted evidence implies 73.7 ft vs table 80 ft (scatter 9.5 ft) -- kept table value, flagged for review
- [width] seam 7-9: using W = 80 ft (21st (Center) St)
- [load] pair_7_9.json: seam 7-9 (horizontal, 21st (Center) St): 2 accepted, 0 rejected, 0 context-only
- [load] pair_8_10.json/Ave D (Market): side 'A' has no valid sigma_along_px; using fallback 2.0 px
- [load] pair_8_10.json/Ave D (Market): side 'B' has no valid sigma_along_px; using fallback 2.0 px
- [load] pair_8_10.json/Ave E (Post Office): side 'A' has no valid sigma_along_px; using fallback 2.0 px
- [load] pair_8_10.json/Ave E (Post Office): side 'B' has no valid sigma_along_px; using fallback 2.0 px
- [width] seam 8-10: overriding default 80 ft with annotated 70 ft (drafted evidence implies 68.4 ft, scatter 0.9 ft)
- [width] seam 8-10: using W = 70 ft (21st (Center) St)
- [load] pair_8_10.json: seam 8-10 (horizontal, 21st (Center) St): 2 accepted, 0 rejected, 0 context-only
- [width] seam 8-39: overriding default 70 ft with annotated 80 ft (drafted evidence implies 79.2 ft, scatter 2.0 ft)
- [width] seam 8-39: using W = 80 ft (Ave F (Church))
- [load] pair_8_39.json: seam 8-39 (vertical, Ave F (Church)): 2 accepted, 0 rejected, 0 context-only
- [width] seam 9-10: drafted evidence implies 81.9 ft vs table 70 ft (scatter 5.6 ft) -- kept table value, flagged for review
- [width] seam 9-10: using W = 70 ft (Ave C (Mechanic))
- [load] pair_9_10.json: seam 9-10 (vertical, Ave C (Mechanic)): 2 accepted, 0 rejected, 0 context-only
- [load] pair_9_11.json/Ave A (Water): side 'A' has no valid sigma_along_px; using fallback 2.0 px
- [load] pair_9_11.json/Ave A (Water): side 'B' malformed (sheet=11, segs valid=False,True); anchor skipped
- [load] pair_9_11.json/Ave B (Strand): side 'A' has no valid sigma_along_px; using fallback 2.0 px
- [load] pair_9_11.json/Ave B (Strand): side 'B' has no valid sigma_along_px; using fallback 2.0 px
- [width] seam 9-11: using W = 80 ft (24th St)
- [load] pair_9_11.json: seam 9-11 (horizontal, 24th St): 1 accepted, 0 rejected, 0 context-only
- [solve] kappa is prior-determined (unscaled marginal std 0.147 vs prior 0.15): the across-seam network cancels kappa against sheet translations; do not read the kappa posterior as a measurement -- compare per-plate drafted widths directly

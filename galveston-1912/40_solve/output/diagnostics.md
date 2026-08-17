# Solve diagnostics -- Galveston 1912 12-sheet block

- Gauge: sheet 10 fixed to identity (mosaic frame = sheet 10 centered pixel frame). Its zero covariance is a gauge artefact, not precision.
- Along-seam direction linearized to axis unit vectors (near-axis-aligned assumption; rotations are sub-degree).
- Solved sheets: [7, 8, 9, 10, 11, 12, 39, 40, 43, 44, 49, 50]
- Observations used: 99 seam obs + 124 collinearity rows (+ kappa prior); parameters: 97; rank 97; dof 138
- Straight-street collinearity ON: 26 face lines (+52 line unknowns c, m; m free per line -- straightness only, no direction assumed), sigma_perp = 6 px, residual RMS 14.98 px; rows linearized at pass-1 mosaic coordinates (two-stage solve)
- Robust variance factor s0^2 = 3.428
- Kappa posterior: 5.7976 +- 0.2723 px/ft (prior 6.07 +- 0.15; unscaled marginal std 0.1471). Compare with per-plate drafted widths before reuse.
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
- across: RMS 35.20 px (n=33)
- along: RMS 7.22 px (n=66)

By seam:
| seam | n | RMS (px) | max |abs| (px) |
|---|---|---|---|
| 10-12 | 6 | 7.81 | 11.73 |
| 10-43 | 6 | 16.19 | 32.14 |
| 11-12 | 6 | 36.81 | 87.78 |
| 12-49 | 6 | 61.33 | 106.14 |
| 39-40 | 6 | 7.95 | 15.97 |
| 39-43 | 6 | 9.72 | 20.01 |
| 40-44 | 6 | 3.90 | 6.22 |
| 43-44 | 6 | 3.93 | 7.11 |
| 43-49 | 6 | 11.33 | 22.66 |
| 44-50 | 6 | 13.20 | 25.15 |
| 49-50 | 6 | 7.07 | 11.94 |
| 7-8 | 6 | 13.80 | 30.24 |
| 7-9 | 6 | 22.71 | 48.87 |
| 8-10 | 6 | 8.87 | 15.85 |
| 8-39 | 6 | 8.59 | 19.31 |
| 9-10 | 6 | 23.17 | 37.62 |
| 9-11 | 3 | 4.38 | 7.49 |

## Per-sheet marginal uncertainty (theta, s)

| sheet | theta std (mrad) | s std (ppm) | tx std (px) | ty std (px) | flag |
|---|---|---|---|---|---|
| 7 | 2.903 | 2498.6 | 24.45 | 25.38 | **ROTATION > 1.5 mrad** |
| 8 | 1.988 | 1788.0 | 6.49 | 23.42 | **ROTATION > 1.5 mrad** |
| 9 | 2.704 | 2436.5 | 23.53 | 8.50 | **ROTATION > 1.5 mrad** |
| 10 | 0.000 | 0.0 | 0.00 | 0.00 | GAUGE |
| 11 | 3.223 | 3063.9 | 25.55 | 26.26 | **ROTATION > 1.5 mrad** |
| 12 | 2.126 | 2052.6 | 7.16 | 23.95 | **ROTATION > 1.5 mrad** |
| 39 | 1.979 | 2117.2 | 25.42 | 24.14 | **ROTATION > 1.5 mrad** |
| 40 | 2.997 | 2563.9 | 48.31 | 26.93 | **ROTATION > 1.5 mrad** |
| 43 | 1.385 | 1890.1 | 24.94 | 5.09 |  |
| 44 | 2.543 | 2291.1 | 47.98 | 11.11 | **ROTATION > 1.5 mrad** |
| 49 | 2.054 | 2156.1 | 26.11 | 24.48 | **ROTATION > 1.5 mrad** |
| 50 | 3.021 | 2520.0 | 48.53 | 27.28 | **ROTATION > 1.5 mrad** |

Flagged sheets (rotation std > 1.5 mrad): **[7, 8, 9, 11, 12, 39, 40, 44, 49, 50]**

## Straight-street collinearity constraints (pass 2)

Each through-street face line measured on >= 2 sheets is one drafted straight line; faces are canonicalized low/high by pass-1 perpendicular coordinate and NEVER mixed. m is free per line (no direction assumed).
| street | axis | face | points | sheets | RMS (px) | max abs (px) | downweighted |
|---|---|---|---|---|---|---|---|
| 19th St | vertical | high | 6 | 4 | 3.37 | 5.07 | 0 |
| 19th St | vertical | low | 6 | 4 | 2.55 | 4.08 | 0 |
| 20th St | vertical | high | 6 | 4 | 64.99 | 118.66 | 4 |
| 20th St | vertical | low | 6 | 4 | 6.74 | 10.76 | 0 |
| 22nd St | vertical | high | 6 | 4 | 10.36 | 20.25 | 1 |
| 22nd St | vertical | low | 6 | 4 | 2.15 | 3.88 | 0 |
| 23rd St | vertical | high | 6 | 4 | 9.01 | 14.15 | 0 |
| 23rd St | vertical | low | 6 | 4 | 6.75 | 13.67 | 0 |
| 25th St (Rosenberg Ave) | vertical | high | 4 | 3 | 0.29 | 0.43 | 0 |
| 25th St (Rosenberg Ave) | vertical | low | 4 | 3 | 2.10 | 2.28 | 0 |
| 26th St | vertical | high | 6 | 4 | 6.67 | 13.11 | 0 |
| 26th St | vertical | low | 6 | 4 | 2.89 | 4.14 | 0 |
| Ave B (Strand) | horizontal | high | 4 | 3 | 2.93 | 4.34 | 0 |
| Ave B (Strand) | horizontal | low | 4 | 3 | 1.63 | 2.11 | 0 |
| Ave D (Market) | horizontal | high | 4 | 3 | 3.02 | 3.77 | 0 |
| Ave D (Market) | horizontal | low | 4 | 3 | 3.13 | 3.73 | 0 |
| Ave E (Post Office) | horizontal | high | 4 | 3 | 4.72 | 6.98 | 0 |
| Ave E (Post Office) | horizontal | low | 4 | 3 | 2.00 | 2.62 | 0 |
| Ave G (Winnie) | horizontal | high | 4 | 3 | 0.24 | 0.30 | 0 |
| Ave G (Winnie) | horizontal | low | 4 | 3 | 3.12 | 4.49 | 0 |
| Ave H (Ball) | horizontal | high | 4 | 3 | 2.16 | 3.09 | 0 |
| Ave H (Ball) | horizontal | low | 4 | 3 | 1.01 | 1.48 | 0 |
| Ave J (Broadway) | horizontal | high | 4 | 3 | 1.04 | 1.34 | 0 |
| Ave J (Broadway) | horizontal | low | 4 | 3 | 1.02 | 1.34 | 0 |
| Ave K | horizontal | high | 4 | 3 | 2.36 | 3.21 | 0 |
| Ave K | horizontal | low | 4 | 3 | 3.00 | 4.29 | 0 |

Overall collinearity residual RMS: 14.98 px (sigma_perp 6 px).

### Rotation std, pass 1 (no collinearity) vs pass 2 (with collinearity)

| sheet | pass-1 theta std (mrad) | pass-2 theta std (mrad) | ratio |
|---|---|---|---|
| 7 | 3.294 | 2.903 | 1.1x |
| 8 | 3.001 | 1.988 | 1.5x |
| 9 | 3.218 | 2.704 | 1.2x |
| 10 | (gauge) | (gauge) | - |
| 11 | 3.629 | 3.223 | 1.1x |
| 12 | 3.138 | 2.126 | 1.5x |
| 39 | 2.818 | 1.979 | 1.4x |
| 40 | 3.459 | 2.997 | 1.2x |
| 43 | 2.390 | 1.385 | 1.7x |
| 44 | 3.047 | 2.543 | 1.2x |
| 49 | 2.980 | 2.054 | 1.5x |
| 50 | 3.475 | 3.021 | 1.2x |

## Down-weighted observations (Huber, delta = 2.5 sigma)

17 of 223 data rows (seam + collinearity) down-weighted (never dropped):
| seam | anchor | type | face | residual (px) | norm. resid | huber w |
|---|---|---|---|---|---|---|
| 10-12 | Ave D (Market) | along | 1 | 11.73 | 4.15 | 0.603 |
| 10-12 | Ave E (Post Office) | along | 2 | -10.16 | -3.59 | 0.696 |
| 10-43 | 23rd St | along | 1 | 19.74 | 5.06 | 0.495 |
| 10-43 | 23rd St | across | 1 | -32.14 | -2.68 | 0.933 |
| 11-12 | 25th St (Rosenberg) | along | 2 | 17.98 | 4.99 | 0.501 |
| 11-12 | 25th St (Rosenberg) | across | 1 | -87.78 | -7.31 | 0.342 |
| 12-49 | 25th St (Rosenberg Ave) | across | 1 | 105.91 | 8.83 | 0.283 |
| 12-49 | 26th St | across | 1 | 106.14 | 8.84 | 0.283 |
| 7-8 | 19th St | across | 1 | 30.24 | 2.52 | 0.992 |
| 7-9 | Ave B (Strand) | across | 1 | -48.87 | -4.07 | 0.614 |
| 9-10 | 22nd St | along | 2 | 34.09 | 6.82 | 0.367 |
| 9-10 | 23rd St | along | 2 | -19.37 | -3.65 | 0.686 |
| 39-40 | 20th St | collin | high | 22.00 | 3.67 | 0.682 |
| 7-8 | 20th St | collin | high | 17.93 | 2.99 | 0.837 |
| 8-39 | 20th St | collin | high | -118.66 | -19.78 | 0.126 |
| 8-39 | 20th St | collin | high | -102.25 | -17.04 | 0.147 |
| 9-10 | 22nd St | collin | high | -20.25 | -3.37 | 0.741 |

## Through-street collinearity

Street center points (mean of the two face midpoints per pair/sheet) mapped to the mosaic; TLS line per street.
| street | axis | points | seams | max perp dev (px) | RMS dev (px) |
|---|---|---|---|---|---|
| 19th St | vertical | 6 | 39-40, 7-8, 8-39 | 1.48 | 0.84 |
| 20th St | vertical | 6 | 39-40, 7-8, 8-39 | 40.77 | 25.65 |
| 22nd St | vertical | 6 | 10-43, 43-44, 9-10 | 9.73 | 5.81 |
| 23rd St | vertical | 6 | 10-43, 43-44, 9-10 | 12.52 | 6.22 |
| 25th St (Rosenberg Ave) | vertical | 4 | 12-49, 49-50 | 1.17 | 1.15 |
| 26th St | vertical | 6 | 11-12, 12-49, 49-50 | 6.50 | 3.80 |
| Ave B (Strand) | horizontal | 4 | 7-9, 9-11 | 1.10 | 0.88 |
| Ave D (Market) | horizontal | 4 | 10-12, 8-10 | 3.08 | 2.13 |
| Ave E (Post Office) | horizontal | 4 | 10-12, 8-10 | 4.83 | 3.31 |
| Ave G (Winnie) | horizontal | 4 | 39-43, 43-49 | 2.15 | 1.48 |
| Ave H (Ball) | horizontal | 4 | 39-43, 43-49 | 2.29 | 1.55 |
| Ave J (Broadway) | horizontal | 4 | 40-44, 44-50 | 0.05 | 0.04 |
| Ave K | horizontal | 4 | 40-44, 44-50 | 2.96 | 2.45 |

### Ave I (Sealy) kink check -- column-4 points vs line through columns 1-3

| street | col4 sheets | col4 deviations (px) | max |abs| |
|---|---|---|---|
| 19th St | [40] | -0.56 | 0.56 |
| 20th St | [40] | -38.35 | 38.35 |
| 22nd St | [44] | -3.50 | 3.50 |
| 23rd St | [44] | -8.77 | 8.77 |
| 25th St (Rosenberg Ave) | [50] | +2.68 | 2.68 |
| 26th St | [50] | -1.93 | 1.93 |

## Leave-one-seam-out

| seam | status | n pred | pred RMS (px) | pred max (px) |
|---|---|---|---|---|
| 10-12 | ok | 4 | 132.65 | 145.73 |
| 10-43 | ok | 4 | 16.05 | 24.34 |
| 11-12 | ok | 4 | 2600.67 | 2646.06 |
| 12-49 | ok | 4 | 15.22 | 24.53 |
| 39-40 | ok | 4 | 81.59 | 87.22 |
| 39-43 | ok | 4 | 10.54 | 13.74 |
| 40-44 | ok | 4 | 25.90 | 35.02 |
| 43-44 | ok | 4 | 30.51 | 36.47 |
| 43-49 | ok | 4 | 129.68 | 137.66 |
| 44-50 | ok | 4 | 13.20 | 18.72 |
| 49-50 | ok | 4 | 4.25 | 6.33 |
| 7-8 | ok | 4 | 197.64 | 219.08 |
| 7-9 | ok | 4 | 83.96 | 106.25 |
| 8-10 | ok | 4 | 17.40 | 22.25 |
| 8-39 | ok | 4 | 34.91 | 43.92 |
| 9-10 | ok | 4 | 62.24 | 88.86 |
| 9-11 | ok | 2 | 144.69 | 145.83 |

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
- [collin] two-stage solve: pass 1 done; building collinearity rows from pass-1 mosaic coordinates (sigma_perp = 6 px)
- [collin] line 25th St (Rosenberg)/high: only 2 points for 2 line unknowns (no redundancy); skipped
- [collin] line 25th St (Rosenberg)/low: only 2 points for 2 line unknowns (no redundancy); skipped
- [collin] line Ave A (Water)/high: only 2 points for 2 line unknowns (no redundancy); skipped
- [collin] line Ave A (Water)/low: only 2 points for 2 line unknowns (no redundancy); skipped
- [collin] 26 straight-street face lines promoted to observations: 124 rows, +52 line unknowns (c, m per line; m free -- straightness only, no direction assumed)
- [solve] kappa is prior-determined (unscaled marginal std 0.147 vs prior 0.15): the across-seam network cancels kappa against sheet translations; do not read the kappa posterior as a measurement -- compare per-plate drafted widths directly

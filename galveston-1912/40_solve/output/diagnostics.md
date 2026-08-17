# Solve diagnostics -- Galveston 1912 12-sheet block

- Gauge: sheet 10 fixed to identity (mosaic frame = sheet 10 centered pixel frame). Its zero covariance is a gauge artefact, not precision.
- Along-seam direction linearized to axis unit vectors (near-axis-aligned assumption; rotations are sub-degree).
- Solved sheets: [7, 8, 9, 10, 11, 12, 39, 40, 43, 44, 49, 50]
- Observations used: 108 seam obs + 140 collinearity rows (+ kappa prior); parameters: 101; rank 101; dof 159
- Straight-street collinearity ON: 28 face lines (+56 line unknowns c, m; m free per line -- straightness only, no direction assumed), sigma_perp = 6 px, residual RMS 14.19 px; rows linearized at pass-1 mosaic coordinates (two-stage solve)
- Robust variance factor s0^2 = 3.145
- Kappa posterior: 5.7967 +- 0.2604 px/ft (prior 6.07 +- 0.15; unscaled marginal std 0.1468). Compare with per-plate drafted widths before reuse.
- **Kappa is prior-determined, not measured**: the across-seam loop structure cancels kappa against sheet translations exactly, so the data cannot constrain it. The across constraints therefore enforce W_ft x prior kappa; validate kappa against per-plate drafted widths directly.

## Seams loaded

| seam | axis | boundary | W (ft) | accepted | rejected | context |
|---|---|---|---|---|---|---|
| 10-12 | horizontal | 24th St | 70 | 2 | 0 | 0 |
| 10-43 | vertical | Ave F (Church) | 80 | 2 | 0 | 0 |
| 11-12 | vertical | Ave C (Mechanic) | 70 | 2 | 0 | 0 |
| 12-49 | vertical | Ave F (Church) | 70 | 2 | 0 | 0 |
| 39-40 | vertical | Ave I (Sealy) | 80 | 3 | 0 | 0 |
| 39-43 | horizontal | 21st (Center) St | 70 | 2 | 0 | 0 |
| 40-44 | horizontal | 21st (Center) St | 80 | 2 | 0 | 0 |
| 43-44 | vertical | Ave I (Sealy) | 80 | 2 | 0 | 0 |
| 43-49 | horizontal | 24th St | 70 | 2 | 0 | 0 |
| 44-50 | horizontal | 24th St | 80 | 2 | 0 | 0 |
| 49-50 | vertical | Ave I (Sealy) | 80 | 2 | 0 | 0 |
| 7-8 | vertical | Ave C (Mechanic) | 70 | 3 | 0 | 0 |
| 7-9 | horizontal | 21st (Center) St | 80 | 2 | 0 | 0 |
| 8-10 | horizontal | 21st (Center) St | 70 | 2 | 0 | 0 |
| 8-39 | vertical | Ave F (Church) | 80 | 3 | 0 | 0 |
| 9-10 | vertical | Ave C (Mechanic) | 70 | 2 | 0 | 0 |
| 9-11 | horizontal | 24th St | 80 | 1 | 0 | 0 |

## Residual RMS

By type:
- across: RMS 34.17 px (n=36)
- along: RMS 7.23 px (n=72)

By seam:
| seam | n | RMS (px) | max |abs| (px) |
|---|---|---|---|
| 10-12 | 6 | 7.59 | 11.18 |
| 10-43 | 6 | 17.97 | 35.98 |
| 11-12 | 6 | 36.64 | 87.64 |
| 12-49 | 6 | 62.88 | 110.83 |
| 39-40 | 9 | 6.33 | 14.00 |
| 39-43 | 6 | 11.90 | 23.88 |
| 40-44 | 6 | 4.09 | 6.65 |
| 43-44 | 6 | 3.87 | 6.94 |
| 43-49 | 6 | 12.22 | 24.77 |
| 44-50 | 6 | 13.96 | 26.67 |
| 49-50 | 6 | 6.65 | 12.05 |
| 7-8 | 9 | 11.05 | 22.74 |
| 7-9 | 6 | 20.32 | 44.42 |
| 8-10 | 6 | 6.42 | 10.51 |
| 8-39 | 9 | 9.39 | 22.54 |
| 9-10 | 6 | 23.53 | 37.68 |
| 9-11 | 3 | 4.46 | 7.63 |

## Per-sheet marginal uncertainty (theta, s)

| sheet | theta std (mrad) | s std (ppm) | tx std (px) | ty std (px) | flag |
|---|---|---|---|---|---|
| 7 | 2.446 | 1919.9 | 22.78 | 23.92 | **ROTATION > 1.5 mrad** |
| 8 | 1.676 | 1602.8 | 5.58 | 22.36 | **ROTATION > 1.5 mrad** |
| 9 | 2.556 | 2191.0 | 22.45 | 8.05 | **ROTATION > 1.5 mrad** |
| 10 | 0.000 | 0.0 | 0.00 | 0.00 | GAUGE |
| 11 | 3.077 | 2832.7 | 24.40 | 25.01 | **ROTATION > 1.5 mrad** |
| 12 | 1.879 | 1944.1 | 6.41 | 22.89 | **ROTATION > 1.5 mrad** |
| 39 | 1.664 | 1760.3 | 23.93 | 22.82 | **ROTATION > 1.5 mrad** |
| 40 | 2.541 | 2059.4 | 45.61 | 25.24 | **ROTATION > 1.5 mrad** |
| 43 | 1.322 | 1774.2 | 23.64 | 4.87 |  |
| 44 | 2.412 | 2122.1 | 45.67 | 10.59 | **ROTATION > 1.5 mrad** |
| 49 | 1.866 | 2041.8 | 24.91 | 23.35 | **ROTATION > 1.5 mrad** |
| 50 | 2.889 | 2381.5 | 46.27 | 25.93 | **ROTATION > 1.5 mrad** |

Flagged sheets (rotation std > 1.5 mrad): **[7, 8, 9, 11, 12, 39, 40, 44, 49, 50]**

## Straight-street collinearity constraints (pass 2)

Each through-street face line measured on >= 2 sheets is one drafted straight line; faces are canonicalized low/high by pass-1 perpendicular coordinate and NEVER mixed. m is free per line (no direction assumed).
| street | axis | face | points | sheets | RMS (px) | max abs (px) | downweighted |
|---|---|---|---|---|---|---|---|
| 18th St (top boundary) | vertical | high | 6 | 4 | 2.61 | 4.18 | 0 |
| 18th St (top boundary) | vertical | low | 6 | 4 | 2.97 | 4.76 | 0 |
| 19th St | vertical | high | 6 | 4 | 2.17 | 3.19 | 0 |
| 19th St | vertical | low | 6 | 4 | 4.33 | 6.70 | 0 |
| 20th St | vertical | high | 6 | 4 | 65.03 | 117.54 | 4 |
| 20th St | vertical | low | 6 | 4 | 6.11 | 9.75 | 0 |
| 22nd St | vertical | high | 6 | 4 | 10.55 | 20.79 | 1 |
| 22nd St | vertical | low | 6 | 4 | 2.39 | 4.06 | 0 |
| 23rd St | vertical | high | 6 | 4 | 9.65 | 15.77 | 1 |
| 23rd St | vertical | low | 6 | 4 | 6.86 | 14.21 | 0 |
| 25th St (Rosenberg Ave) | vertical | high | 6 | 4 | 4.95 | 9.05 | 0 |
| 25th St (Rosenberg Ave) | vertical | low | 6 | 4 | 4.31 | 6.59 | 0 |
| 26th St | vertical | high | 6 | 4 | 4.96 | 10.39 | 0 |
| 26th St | vertical | low | 6 | 4 | 2.94 | 4.00 | 0 |
| Ave B (Strand) | horizontal | high | 4 | 3 | 3.32 | 4.89 | 0 |
| Ave B (Strand) | horizontal | low | 4 | 3 | 1.38 | 1.69 | 0 |
| Ave D (Market) | horizontal | high | 4 | 3 | 3.28 | 4.15 | 0 |
| Ave D (Market) | horizontal | low | 4 | 3 | 3.24 | 3.47 | 0 |
| Ave E (Post Office) | horizontal | high | 4 | 3 | 4.58 | 6.76 | 0 |
| Ave E (Post Office) | horizontal | low | 4 | 3 | 1.79 | 2.48 | 0 |
| Ave G (Winnie) | horizontal | high | 4 | 3 | 0.40 | 0.57 | 0 |
| Ave G (Winnie) | horizontal | low | 4 | 3 | 3.13 | 4.58 | 0 |
| Ave H (Ball) | horizontal | high | 4 | 3 | 2.62 | 3.75 | 0 |
| Ave H (Ball) | horizontal | low | 4 | 3 | 1.31 | 1.94 | 0 |
| Ave J (Broadway) | horizontal | high | 4 | 3 | 1.11 | 1.45 | 0 |
| Ave J (Broadway) | horizontal | low | 4 | 3 | 0.86 | 1.08 | 0 |
| Ave K | horizontal | high | 4 | 3 | 2.25 | 3.16 | 0 |
| Ave K | horizontal | low | 4 | 3 | 2.83 | 4.03 | 0 |

Overall collinearity residual RMS: 14.19 px (sigma_perp 6 px).

### Rotation std, pass 1 (no collinearity) vs pass 2 (with collinearity)

| sheet | pass-1 theta std (mrad) | pass-2 theta std (mrad) | ratio |
|---|---|---|---|
| 7 | 2.827 | 2.446 | 1.2x |
| 8 | 2.448 | 1.676 | 1.5x |
| 9 | 3.067 | 2.556 | 1.2x |
| 10 | (gauge) | (gauge) | - |
| 11 | 3.484 | 3.077 | 1.1x |
| 12 | 3.015 | 1.879 | 1.6x |
| 39 | 2.298 | 1.664 | 1.4x |
| 40 | 2.995 | 2.541 | 1.2x |
| 43 | 2.292 | 1.322 | 1.7x |
| 44 | 2.912 | 2.412 | 1.2x |
| 49 | 2.861 | 1.866 | 1.5x |
| 50 | 3.340 | 2.889 | 1.2x |

## Down-weighted observations (Huber, delta = 2.5 sigma)

18 of 248 data rows (seam + collinearity) down-weighted (never dropped):
| seam | anchor | type | face | residual (px) | norm. resid | huber w |
|---|---|---|---|---|---|---|
| 10-12 | Ave D (Market) | along | 1 | 11.18 | 3.95 | 0.633 |
| 10-12 | Ave E (Post Office) | along | 2 | -9.72 | -3.44 | 0.728 |
| 10-43 | 23rd St | along | 1 | 20.13 | 5.15 | 0.485 |
| 10-43 | 23rd St | across | 1 | -35.98 | -3.00 | 0.834 |
| 11-12 | 25th St (Rosenberg Ave) | along | 2 | 16.49 | 4.57 | 0.547 |
| 11-12 | 25th St (Rosenberg Ave) | across | 1 | -87.64 | -7.30 | 0.342 |
| 12-49 | 25th St (Rosenberg Ave) | across | 1 | 106.56 | 8.88 | 0.282 |
| 12-49 | 26th St | across | 1 | 110.83 | 9.24 | 0.271 |
| 7-9 | Ave B (Strand) | along | 2 | -7.11 | -2.51 | 0.995 |
| 7-9 | Ave B (Strand) | across | 1 | -44.42 | -3.70 | 0.675 |
| 9-10 | 22nd St | along | 2 | 34.76 | 6.95 | 0.360 |
| 9-10 | 23rd St | along | 2 | -21.57 | -4.06 | 0.616 |
| 39-40 | 20th St | collin | high | 23.95 | 3.99 | 0.626 |
| 7-8 | 20th St | collin | high | 20.32 | 3.39 | 0.738 |
| 8-39 | 20th St | collin | high | -117.54 | -19.59 | 0.128 |
| 8-39 | 20th St | collin | high | -102.80 | -17.13 | 0.146 |
| 9-10 | 22nd St | collin | high | -20.79 | -3.46 | 0.722 |
| 9-10 | 23rd St | collin | high | -15.77 | -2.63 | 0.951 |

## Through-street collinearity

Street center points (mean of the two face midpoints per pair/sheet) mapped to the mosaic; TLS line per street.
| street | axis | points | seams | max perp dev (px) | RMS dev (px) |
|---|---|---|---|---|---|
| 18th St (top boundary) | vertical | 6 | 39-40, 7-8, 8-39 | 4.48 | 2.74 |
| 19th St | vertical | 6 | 39-40, 7-8, 8-39 | 2.17 | 1.50 |
| 20th St | vertical | 6 | 39-40, 7-8, 8-39 | 40.86 | 26.14 |
| 22nd St | vertical | 6 | 10-43, 43-44, 9-10 | 10.19 | 6.06 |
| 23rd St | vertical | 6 | 10-43, 43-44, 9-10 | 13.14 | 6.69 |
| 25th St (Rosenberg Ave) | vertical | 6 | 11-12, 12-49, 49-50 | 4.31 | 3.14 |
| 26th St | vertical | 6 | 11-12, 12-49, 49-50 | 3.73 | 2.09 |
| Ave B (Strand) | horizontal | 4 | 7-9, 9-11 | 1.59 | 1.21 |
| Ave D (Market) | horizontal | 4 | 10-12, 8-10 | 3.56 | 2.43 |
| Ave E (Post Office) | horizontal | 4 | 10-12, 8-10 | 4.65 | 3.15 |
| Ave G (Winnie) | horizontal | 4 | 39-43, 43-49 | 2.23 | 1.51 |
| Ave H (Ball) | horizontal | 4 | 39-43, 43-49 | 2.84 | 1.94 |
| Ave J (Broadway) | horizontal | 4 | 40-44, 44-50 | 0.19 | 0.14 |
| Ave K | horizontal | 4 | 40-44, 44-50 | 2.65 | 2.28 |

### Ave I (Sealy) kink check -- column-4 points vs line through columns 1-3

| street | col4 sheets | col4 deviations (px) | max |abs| |
|---|---|---|---|
| 18th St (top boundary) | [40] | +1.59 | 1.59 |
| 19th St | [40] | +1.12 | 1.12 |
| 20th St | [40] | -40.32 | 40.32 |
| 22nd St | [44] | -3.42 | 3.42 |
| 23rd St | [44] | -9.09 | 9.09 |
| 25th St (Rosenberg Ave) | [50] | +6.33 | 6.33 |
| 26th St | [50] | +0.36 | 0.36 |

## Leave-one-seam-out

| seam | status | n pred | pred RMS (px) | pred max (px) |
|---|---|---|---|---|
| 10-12 | ok | 4 | 133.14 | 145.37 |
| 10-43 | ok | 4 | 18.16 | 31.64 |
| 11-12 | ok | 4 | 2612.42 | 2654.72 |
| 12-49 | ok | 4 | 14.02 | 19.22 |
| 39-40 | ok | 6 | 79.28 | 88.52 |
| 39-43 | ok | 4 | 5.14 | 7.92 |
| 40-44 | ok | 4 | 20.87 | 28.24 |
| 43-44 | ok | 4 | 27.02 | 32.65 |
| 43-49 | ok | 4 | 129.08 | 137.11 |
| 44-50 | ok | 4 | 17.22 | 23.09 |
| 49-50 | ok | 4 | 4.20 | 6.21 |
| 7-8 | ok | 6 | 209.53 | 255.17 |
| 7-9 | ok | 4 | 56.10 | 79.60 |
| 8-10 | ok | 4 | 15.30 | 20.78 |
| 8-39 | ok | 6 | 28.37 | 39.76 |
| 9-10 | ok | 4 | 61.50 | 89.52 |
| 9-11 | ok | 2 | 148.22 | 148.76 |

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
- [load] pair_11_12.json/27th St (bottom boundary): side 'A' malformed (sheet=11, segs valid=True,False); anchor skipped
- [width] seam 11-12: drafted evidence implies 100.7 ft vs table 70 ft (scatter 38.1 ft) -- kept table value, flagged for review
- [width] seam 11-12: using W = 70 ft (Ave C (Mechanic))
- [load] pair_11_12.json: seam 11-12 (vertical, Ave C (Mechanic)): 2 accepted, 0 rejected, 0 context-only
- [load] pair_12_49.json/27th St (bottom boundary): side 'A' malformed (sheet=12, segs valid=True,False); anchor skipped
- [width] seam 12-49: drafted evidence implies 99.3 ft vs table 70 ft (scatter 41.2 ft) -- kept table value, flagged for review
- [width] seam 12-49: using W = 70 ft (Ave F (Church))
- [load] pair_12_49.json: seam 12-49 (vertical, Ave F (Church)): 2 accepted, 0 rejected, 0 context-only
- [width] seam 39-40: using W = 80 ft (Ave I (Sealy))
- [load] pair_39_40.json: seam 39-40 (vertical, Ave I (Sealy)): 3 accepted, 0 rejected, 0 context-only
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
- [load] pair_49_50.json/27th St (bottom boundary): side 'A' malformed (sheet=49, segs valid=True,False); anchor skipped
- [width] seam 49-50: drafted evidence implies 99.4 ft vs table 80 ft (scatter 41.2 ft) -- kept table value, flagged for review
- [width] seam 49-50: using W = 80 ft (Ave I (Sealy))
- [load] pair_49_50.json: seam 49-50 (vertical, Ave I (Sealy)): 2 accepted, 0 rejected, 0 context-only
- [width] seam 7-8: drafted evidence implies 94.2 ft vs table 70 ft (scatter 44.0 ft) -- kept table value, flagged for review
- [width] seam 7-8: using W = 70 ft (Ave C (Mechanic))
- [load] pair_7_8.json: seam 7-8 (vertical, Ave C (Mechanic)): 3 accepted, 0 rejected, 0 context-only
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
- [width] seam 8-39: overriding default 70 ft with annotated 80 ft (drafted evidence implies 79.5 ft, scatter 2.0 ft)
- [width] seam 8-39: using W = 80 ft (Ave F (Church))
- [load] pair_8_39.json: seam 8-39 (vertical, Ave F (Church)): 3 accepted, 0 rejected, 0 context-only
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
- [collin] line Ave A (Water)/high: only 2 points for 2 line unknowns (no redundancy); skipped
- [collin] line Ave A (Water)/low: only 2 points for 2 line unknowns (no redundancy); skipped
- [collin] 28 straight-street face lines promoted to observations: 140 rows, +56 line unknowns (c, m per line; m free -- straightness only, no direction assumed)
- [solve] kappa is prior-determined (unscaled marginal std 0.147 vs prior 0.15): the across-seam network cancels kappa against sheet translations; do not read the kappa posterior as a measurement -- compare per-plate drafted widths directly

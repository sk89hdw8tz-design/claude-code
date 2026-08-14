# Transform fitting

Profile `synthetic` -- 2026-08-14T18:02:18+00:00

- model selected: **similarity**
- anchor region: `S2`
- conformal weight: 200.0
- tie observations: 62

## Model comparison

| model | usable | cross-validated median (px) | fit median (px) | note |
|---|---|---|---|---|
| similarity | True | 3.080 | 2.432 |  |
| affine | False | 3.065 | 2.092 | physically implausible sheet geometry: S27(rotation/shear/anisotropy), S29(anisotropy), S7(rotation/shear/anisotropy), S8(anisotropy) |
| projective | False | - | - | rank deficient - not enough well-spread observations to determine 8 parameters per sheet |

## Residuals by sheet pair

| pair | n | median | p90 | max | over target | gross |
|---|---|---|---|---|---|---|
| S10|S1_main | 1 | 0.28 | 0.28 | 0.28 | 0 | 0 |
| S10|S2 | 10 | 3.09 | 4.56 | 5.46 | 1 | 0 |
| S10|S27 | 6 | 3.03 | 9.59 | 14.62 | 1 | 0 |
| S10|S7 | 2 | 2.44 | 3.21 | 3.41 | 0 | 0 |
| S10|S9 | 5 | 2.39 | 3.18 | 3.22 | 0 | 0 |
| S1_main|S2 | 5 | 1.50 | 3.22 | 4.26 | 0 | 0 |
| S1_main|S9 | 4 | 2.45 | 3.81 | 4.38 | 0 | 0 |
| S27|S29 | 5 | 3.20 | 7.47 | 8.49 | 2 | 0 |
| S27|S7 | 3 | 0.75 | 2.11 | 2.45 | 0 | 0 |
| S29|S7 | 1 | 1.29 | 1.29 | 1.29 | 0 | 0 |
| S29|S8 | 6 | 1.55 | 2.65 | 2.69 | 0 | 0 |
| S2|S27 | 2 | 1.79 | 2.03 | 2.10 | 0 | 0 |
| S2|S7 | 6 | 2.93 | 3.54 | 3.58 | 0 | 0 |
| S2|S9 | 1 | 0.95 | 0.95 | 0.95 | 0 | 0 |
| S7|S8 | 5 | 3.22 | 4.39 | 4.51 | 0 | 0 |

## Solved sheet geometry

| region | scale x | scale y | rotation | shear | anisotropy |
|---|---|---|---|---|---|
| S1_main | 0.9837 | 0.9837 | -0.05 | -0.00 | 0.0000 |
| S2 | 1.0000 | 1.0000 | +0.00 | +0.00 | 0.0000 |
| S7 | 0.9849 | 0.9849 | +0.09 | +0.00 | 0.0000 |
| S8 | 0.9855 | 0.9855 | +1.76 | -0.00 | 0.0000 |
| S9 | 0.9937 | 0.9937 | +1.34 | -0.00 | 0.0000 |
| S10 | 0.9984 | 0.9984 | +0.05 | +0.00 | 0.0000 |
| S27 | 0.9788 | 0.9788 | +2.15 | +0.00 | 0.0000 |
| S29 | 1.0044 | 1.0044 | +2.37 | +0.00 | 0.0000 |

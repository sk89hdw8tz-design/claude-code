# Grid-derived control points

Control points are intersections of street and avenue centrelines. A crossing carries the same `point_id` on every sheet that shows it, which is what ties those sheets together.

| sheet | region | streets kept | avenues kept | points | rot streets | rot avenues |
|---|---|---|---|---|---|---|
| 1 | S1_main | 23rd, 24th, 25th | A | 3 | +0.052° | +1.039° |
| 2 | S2 | 19th, 20th, 21st, 22nd | A | 4 | -0.021° | +0.887° |
| 7 | S7 | 19th, 20th, 21st, 22nd | A, B, C, D | 16 | +0.377° | +0.017° |
| 8 | S8 | 19th, 20th, 21st, 22nd | D, E, F, G | 16 | +0.396° | +0.139° |
| 9 | S9 | 22nd, 23rd, 24th, 25th | A, B, C, D | 16 | -0.202° | -0.475° |
| 10 | S10 | 22nd, 23rd, 24th, 25th | D, E, F, G | 16 | +0.318° | -0.180° |
| 27 | S27 | 22nd, 23rd, 24th, 25th | G, H, I, J | 16 | +0.678° | +0.920° |
| 29 | S29 | 19th, 21st | G, H, I, J | 8 | +0.680° | -0.253° |

## Shared crossings per sheet pair

| pair | shared points |
|---|---|
| S10 – S27 | 4 |
| S10 – S7 | 1 |
| S10 – S8 | 4 |
| S10 – S9 | 4 |
| S1_main – S9 | 3 |
| S2 – S7 | 4 |
| S2 – S9 | 1 |
| S27 – S8 | 1 |
| S29 – S8 | 2 |
| S7 – S8 | 4 |
| S7 – S9 | 4 |
| S8 – S9 | 1 |

## Bands rejected by the quality gates

| sheet | kind | name | reason |
|---|---|---|---|
| 1 | street | 22nd | moved 151px |
| 29 | street | 20th | slope off by 0.0417 |
| 29 | street | 22nd | moved 151px |

Overlays for visual verification are in `output/qc/grid_overlays/`. Check that each line sits down the middle of its street before trusting any of this.

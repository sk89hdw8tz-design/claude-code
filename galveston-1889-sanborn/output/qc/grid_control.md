# Grid-derived control points

Control points are intersections of street and avenue centrelines. A crossing carries the same `point_id` on every sheet that shows it, which is what ties those sheets together.

| sheet | region | streets kept | avenues kept | points | rot streets | rot avenues |
|---|---|---|---|---|---|---|
| 1 | S1_main | 22nd, 23rd, 24th, 25th | A | 4 | +0.264° | -2.117° |
| 2 | S2 | 19th, 20th, 21st | A | 3 | +0.131° | -0.579° |
| 7 | S7 | 19th, 20th, 21st, 22nd | A, C, D | 12 | +0.200° | +0.572° |
| 8 | S8 | 19th, 20th, 21st, 22nd | D, E, F, G | 16 | +0.424° | +0.418° |
| 9 | S9 | 22nd, 23rd, 24th, 25th | A, B, C, D | 16 | +0.309° | +0.794° |
| 10 | S10 | 22nd, 23rd, 24th | D, E, F, G | 12 | -0.304° | -0.254° |
| 27 | S27 | 22nd, 23rd, 24th, 25th | G, H, I, J | 16 | +0.678° | +1.077° |
| 29 | S29 | 19th, 20th, 21st, 22nd | G, H, I, J | 16 | -0.015° | +0.243° |

## Shared crossings per sheet pair

| pair | shared points |
|---|---|
| S10 – S27 | 3 |
| S10 – S29 | 1 |
| S10 – S7 | 1 |
| S10 – S8 | 4 |
| S10 – S9 | 3 |
| S1_main – S7 | 1 |
| S1_main – S9 | 4 |
| S2 – S7 | 3 |
| S27 – S29 | 4 |
| S27 – S8 | 1 |
| S29 – S8 | 4 |
| S7 – S8 | 4 |
| S7 – S9 | 3 |
| S8 – S9 | 1 |

## Bands rejected by the quality gates

| sheet | kind | name | reason |
|---|---|---|---|
| 2 | street | 22nd | slope off by 0.0511 |
| 7 | avenue | B | slope off by 0.0449 |
| 10 | street | 25th | slope off by 0.0405 |

Overlays for visual verification are in `output/qc/grid_overlays/`. Check that each line sits down the middle of its street before trusting any of this.

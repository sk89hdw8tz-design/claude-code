# Sheet-5 two-panel fit -- diagnostics

**This fit is downstream of the frozen block.**  It must be re-run after any block re-freeze (new `40_solve/output/transforms.json`); the sha256 below identifies the freeze actually used.

- block transforms: `/home/user/claude-code/galveston-1912/40_solve/output/transforms.json`
- sha256: `a57f3dcb8614c9939f1ab82322f8091167e98ba3122ebed634ff1c8b4f0bf11b`
- block sheets available: [7, 8, 9, 10, 11, 12, 39, 40, 43, 44, 49, 50]
- block kappa (reference only, prior-dominated=True): 5.797 px/ft

## Panel solutions (mosaic frame; centered on panel-polygon centroids)

| panel | s | s std | theta (deg) | theta std (mrad) | tx | ty | center | n_obs | dof | s0^2 |
|---|---|---|---|---|---|---|---|---|---|---|
| 5A | 1.978879 | 0.006341 | -1.2430 | 6.19 | -10180.2 | -7597.3 | (1913.8, 3910.6) | 14 | 10 | 6.48 |
| 5B | 1.988778 | 0.004629 | 0.0874 | 4.76 | -9030.5 | 6069.8 | (5240.2, 3879.8) | 15 | 11 | 6.76 |

Rotation was left fully free per panel (wharf plates are rotated relative to north-up; the similarity finds whatever rotation the controls demand -- the near-zero solved values are an outcome, not an assumption).

## Scale vs the block (~2x expectation: 100 ft/in vs 50 ft/in)

| seam | solved s_panel/s_block | mean drafted width ratio (B/A) | expectation |
|---|---|---|---|
| 5A-7 | 1.9783 | 1.953 | 2.00 |
| 5A-9 | 1.9922 | 1.907 | 2.00 |
| 5B-9 | 2.0021 | 1.938 | 2.00 |
| 5B-11 | 1.9924 | 1.977 | 2.00 |

Panel 5A implied mosaic scale: s x 3.09 = 6.115 px/ft (block kappa is prior-dominated; drafted-width ratios above are the meaningful comparison).

Panel 5B implied mosaic scale: s x 3.09 = 6.145 px/ft (block kappa is prior-dominated; drafted-width ratios above are the meaningful comparison).

## Residual RMS per attachment

| seam | type | n | RMS (mosaic px) | max |n| |
|---|---|---|---|---|
| 5A-7 | pp_across | 4 | 49.59 | 5.38 |
| 5A-7 | pp_along | 4 | 16.25 | 2.17 |
| 5A-9 | across | 2 | 39.50 | 4.10 |
| 5A-9 | along | 4 | 16.46 | 1.57 |
| 5B-11 | across | 2 | 42.63 | 4.77 |
| 5B-11 | along | 4 | 8.53 | 1.05 |
| 5B-9 | across | 3 | 30.08 | 3.83 |
| 5B-9 | along | 6 | 41.11 | 8.81 |

## Huber downweights (logged, never dropped)

| seam | anchor | face | type | residual (px) | normalized | weight |
|---|---|---|---|---|---|---|
| 5A-7 | 19th St | 2 | pp_across | -41.4 | -3.45 | 0.725 |
| 5A-7 | 20th St | 1 | pp_across | 64.6 | 5.38 | 0.464 |
| 5A-7 | 20th St | 2 | pp_across | 61.4 | 5.12 | 0.488 |
| 5A-9 | 22nd St | 1 | across | -49.2 | -4.10 | 0.609 |
| 5B-9 | 24th St | 1 | along | -82.6 | -8.81 | 0.284 |
| 5B-9 | 24th St | 2 | along | -43.4 | -2.57 | 0.974 |
| 5B-9 | 24th St | 1 | across | 46.0 | 3.83 | 0.652 |
| 5B-11 | 26th St | 1 | across | -57.2 | -4.77 | 0.524 |

## Cross-panel consistency (5A vs 5B; NOT in the fit)

Flag threshold 30 mosaic px; ft at 6.13 px/ft.

| pair | group | dx (px) | dy (px) | |d| (px) | ~ft | flagged |
|---|---|---|---|---|---|---|
| P1_22ndSt_blockN_SW_corner | street | 25.3 | 9.5 | 27.0 | 4.4 | no |
| P2_22ndSt_blockS_NW_corner | street | 4.3 | 8.4 | 9.5 | 1.5 | no |
| P3_pier22_shed_root_W_corner | pier | -352.3 | -30.9 | 353.7 | 57.7 | YES |
| P4_pier22_shed_root_E_corner | pier | -333.8 | -1.8 | 333.8 | 54.4 | YES |
| P5_pier22_deck_root_W_corner | pier | -293.4 | -30.2 | 294.9 | 48.1 | YES |
| P6_pier22_deck_root_E_corner | pier | -413.0 | 13.4 | 413.2 | 67.4 | YES |

- street pairs: n=2, mean 18.2 px, max 27.0 px

- pier pairs: n=4, mean 348.9 px, max 413.2 px

Street-corner pairs are the meaningful check; the pier-ground pairs are a recorded drafted disagreement (~55 ft) -- reported, never constrained.  Nothing here entered the fit.

## 5B-13 CONTEXT_ONLY consistency report (fitted to nothing)

### 5B-13 (pair_05B_13.json) -- mode: relative

sheet 13 has no frozen transform (outside the block solve), so two-sided point residuals are not computable; report compares relative anchor separations (translation-free) and drafted width ratios instead.  Block-side native px are converted at the drafted 50 ft/in (6.18 px/ft); the direction comparison assumes sheet 13 is drafted axis-aligned like its frozen neighbours (all block rotations < 0.5 deg).

| anchor | width ratio (block/panel) |
|---|---|
| 27th St | 1.988 |
| 28th St | 1.958 |

| span | panel sep (ft) | sheet-13 sep (ft) | diff (ft) | direction diff (deg) |
|---|---|---|---|---|
| 27th St -> 28th St | 368.9 | 372.5 | -3.6 | +0.39 |

## Model decisions (documented)

- Observation basis: face midpoints as corresponding-line (along) observations; the shared Ave A east-face corner endpoints (smaller-x endpoint, both plates bay-page-left) as zero-offset across observations; direct 2-component point-to-point rows at those corners where the record marks genuine duplicated ground (5A-7 bay strip, per its notes).
- No kappa: both plates draft the same Ave A corner, so no street-width x kappa construction is needed anywhere in this fit; recorded drafted widths are used only for the scale diagnostics and sigma floors.
- Across sigma floor 12 mosaic px (block amendment-5 floor); native sigmas scaled into the mosaic with the frozen block scales and the current panel scale inside IRLS.
- Face-specific sigma overrides parsed from sigma_basis prose ('sigma N for that face'): see log lines below.
- Panel centers = area centroids of the region polygons (candidate-regions GeoJSON).
- Along-frontage = page-y on both sides was VERIFIED from the anchor geometry (see [axes] log lines), and panel rotation was solved, not assumed near zero.

## Log

```
[load] frozen block: 12 sheets from /home/user/claude-code/galveston-1912/40_solve/output/transforms.json (sha256 a57f3dcb8614...)
[load] panel 5A centroid (1913.8, 3910.6)
[load] panel 5B centroid (5240.2, 3879.8)
[parse] pair_05A_07.json: seam 5A-7, 2 anchors, context_only=False, overlap=True
[parse] pair_05A_09.json:21st (Center) St block(B): face1 sigma override 12 px (from sigma_basis prose)
[parse] pair_05A_09.json: seam 5A-9, 2 anchors, context_only=False, overlap=False
[parse] pair_05B_09.json:24th St block(B): face2 sigma override 15 px (from sigma_basis prose)
[parse] pair_05B_09.json: seam 5B-9, 3 anchors, context_only=False, overlap=False
[parse] pair_05B_11.json: seam 5B-11, 2 anchors, context_only=False, overlap=False
[parse] pair_05B_13.json:27th St block(B): face1 sigma override 12 px (from sigma_basis prose)
[parse] pair_05B_13.json: seam 5B-13, 2 anchors, context_only=True, overlap=False
[regions] 5A-7: all panel-side points inside the 5A polygon
[axes] 5A-7 panel: along=page-y verified (anchor spread y 1409 px vs x 14 px)
[axes] 5A-7 block: along=page-y verified (anchor spread y 2814 px vs x 101 px)
[axes] 5A-7: page-y runs the same direction on both sides
[regions] 5A-9: all panel-side points inside the 5A polygon
[axes] 5A-9 panel: along=page-y verified (anchor spread y 1417 px vs x 13 px)
[axes] 5A-9 block: along=page-y verified (anchor spread y 2800 px vs x 154 px)
[axes] 5A-9: page-y runs the same direction on both sides
[regions] 5B-9: all panel-side points inside the 5B polygon
[axes] 5B-9 panel: along=page-y verified (anchor spread y 2534 px vs x 12 px)
[axes] 5B-9 block: along=page-y verified (anchor spread y 5139 px vs x 202 px)
[axes] 5B-9: page-y runs the same direction on both sides
[regions] 5B-11: all panel-side points inside the 5B polygon
[axes] 5B-11 panel: along=page-y verified (anchor spread y 1527 px vs x 41 px)
[axes] 5B-11 block: along=page-y verified (anchor spread y 3040 px vs x 176 px)
[axes] 5B-11: page-y runs the same direction on both sides
[regions] 5B-13: all panel-side points inside the 5B polygon
[axes] 5B-13 panel: along=page-y verified (anchor spread y 1380 px vs x 28 px)
[axes] 5B-13 block: along=page-y verified (anchor spread y 2773 px vs x 78 px)
[axes] 5B-13: page-y runs the same direction on both sides
[class] 5B-13: CONTEXT_ONLY -- loaded, fitted to nothing, reported below
[obs] 5A-7: 8 rows (pp (duplicated ground))
[obs] 5A-9: 6 rows (along+across)
[solve] 5A: 14 rows, dof 10, s0^2 6.478, 4 Huber-downweighted; s=1.978879, theta=-1.2430 deg
[obs] 5B-9: 9 rows (along+across)
[obs] 5B-11: 6 rows (along+across)
[solve] 5B: 15 rows, dof 11, s0^2 6.761, 4 Huber-downweighted; s=1.988778, theta=0.0874 deg
[context] 5B-13: relative consistency report (1 separation pair(s)); nothing fitted
[cross] 6 pairs; flagged (> 30 px): ['P3_pier22_shed_root_W_corner', 'P4_pier22_shed_root_E_corner', 'P5_pier22_deck_root_W_corner', 'P6_pier22_deck_root_E_corner']
```

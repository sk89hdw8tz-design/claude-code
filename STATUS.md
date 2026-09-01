# Galveston Sanborn mosaics — status

**Updated:** 2026-09-01 (1912 row shear fixed; seams re-cut; grid city-wide) · **Branch:** `claude/galveston-setup-part-a-mk5z1l` · **Ledger:** `state/ledger.json`

## Headline

| | 1899 | 1912 |
|---|---|---|
| Sources inventoried | **102/102** (UT PCL, sha256 ✅) | **129/129** (LOC IIIF, sha256 ✅) |
| Target sheets | 13 (of which 13 in repo) | 13 + 1 context (18 archival JP2s in repo) |
| Registration | ✅ full-affine rebuild, gated | ✅ solved affines (prior accepted run) |
| Seams | ✅ 19 min-ink cuts + ownership | ✅ cuts + masks frozen |
| QC | ✅ gate + guard metrics + proof panels | ✅ prior run1 + 2 reviewer reports |
| Recipe consolidated | ⬜ | ✅ (hash-verified vs freeze) |

## Stage bars

```
Stage 0  inventory + environment   ██████████ done
Stage 1  consolidate 1912 recipe   ██████████ done
Stage 2  register 1899             ██████████ done (HQ-4 awaiting answer)
Stage 3  QC + human queue          ██████████ done (HQ-4 awaiting answer)
Stage 4  indexes + render/crop     ██████████ done (both years; DZI deferred off-cloud)
Stage 5  1899 city-wide (90 units)  ██████████ 89/90 placed (71a: no shared ground)
Stage 6  1912 full volume           ██████████ 92/92 placed; city recipe exported
```

## Sheet grid (target footprint)

Row/col per the key maps; 1899 wharf column sits 0.67 rows high of the inland grid.

| 1899 | | | | | 1912 | | | | |
|---|---|---|---|---|---|---|---|---|---|
| wharf | 8 ✅ | 7 ✅ | 6 ✅ | 5 ✅ | wharf | 5 ✅ | | | |
| col 1 | 11 ✅ | 13 ✅ | 15 ✅ | | A–B | 7 ✅ | 9 ✅ | 11 ✅ | |
| col 2 | 12 ✅ | 14 ✅ | 16 ✅ | | C–E | 8 ✅ | 10 ✅ | 12 ✅ | |
| col 3 | 41 ✅ | 39 ✅ | 37 ✅ | | F–H | 39 ✅ | 43 ✅ | 49 ✅ | |
| | | | | | I–K | 40 ✅ | 44 ✅ | 50 ✅ | |

✅ = source sheet in repo with verified hash. Registration status is per the table above, not per cell.

## Worst ten seams

### 1912 (consolidated QA)

| seam | across RMS px* | mask tiling |
|---|---|---|
| 12\|49 | 108.71 | PASS |
| 11\|12 | 62.09 | PASS |
| 7\|9 | 34.52 | PASS |
| 9\|10 | 28.53 | PASS |
| 10\|43 | 26.97 | PASS |
| 44\|50 | 23.86 | PASS |
| 43\|49 | 20.38 | PASS |
| 39\|43 | 20.12 | PASS |
| 7\|8 | 17.05 | PASS |
| 8\|39 | 14.96 | PASS |

\*across = drafted frontage separation vs. default street width — absorbs the plates' drafted-width disagreement, **not** seam misregistration (source: prior QA run1, consolidated). All 17 seams PASS mask tiling; worst gap 0.001 px.

### 1899 (held-out landmark gate, worst first)

| landmark | pair | step px |
|---|---|---|
| th-hydrant-514 (symbol) | 14\|16 | 19.7 — HQ-4 |
| pier22_apron_sw (wharf drawing disagreement) | 07\|06 | 19.4 |
| th-hydrant-314 (symbol) | 13\|15 | 13.7 |
| e-corner-2101 | 14\|39 | 8.6 |
| red-disc-7 (symbol) | 11\|12 | 6.7 |
| all remaining structural | — | ≤5.9 |

(rev2 rigid-similarity solve; the earlier 2.7 px median was the overfit
affine's illusion — see REPORT.md.)

## Active agents

| agent | task |
|---|---|
| orchestrator | city recipes exported; 1912 city grid outstanding |
| adjudicators (6 batches) | ✅ finished — 227 landmark-anchored ties |

## ETA

All cloud stages complete. HQ-1..4 closed 2026-08-30 under delegated
authority; HQ-6 (1912 recipe not renderable from a clean clone) found and
fixed in the same pass. Remaining: HQ-7 (`71a`), and the off-cloud
full-resolution renders/DZI (single commands, documented in REPORT.md).

Both years verified end-to-end in-cloud at 1/8 on 2026-08-30. Full-city
extents at 1/2: 1899 → 15180×23783 (~1.1 GB canvas, 178 MB sources);
1912 → 20370×45493 (~2.8 GB canvas, 205 MB sources).

## Coverage

`outputs/1899/coverage.png` — 89/90 placed, `71a` carried over unverified.
`outputs/1912/coverage.png` — 92/92 placed.

## 1912 row shear found and fixed (2026-09-01)

The published mosaic was sheared east-west from one sheet row to the next:
sheets 57 and 63 cover the same avenue band one street row apart, their y
differed by the correct 1,225 ft and their x by **1,643 ft**. Structural, not
drafting. The control network only asked two questions -- side-by-side sheets
share an avenue (pins a row in x), stacked sheets share a street (pins a
column in y) -- so nothing tied one row to the next in x. With the core frozen
as one rigid body the 56 avenue controls left **26 independent x-components**.

A stacked pair abuts along a street but *crosses* every avenue in its band, so
it can be asked the other question. 45 such pairs went to 15 Opus observers,
who read each shared avenue's centreline off a native-pixel ruler and argued
identity from the printed lettering and hundred-block address runs.

| | before | after |
|---|---|---|
| avenue(x) controls | 56 | **106** |
| independent x-components | 26 | **1** |
| control residual, median | — | 2.1 ft (90th 10.0, max 33.6) |
| avenue index | non-monotonic | **monotonic, all 26 slots** |
| worst per-avenue scatter | 479 ft | **66 ft** |
| city-wide avenue pitch fit | 334.6 ft, residual 329.2 | **348.8 ft, residual 22.8** |

`ctlcheck.py` re-checks every accepted control against evidence it was not
fitted to -- the key maps predict the framing shift between two plates, so a
control that took the right corridor on one sheet and its neighbour on the
other is off by a whole block. **45 of 46 pass.** The three that ever flagged
are all on the two plates observers independently identified as composites
(sheet 85's inset panel, sheet 99's two out-of-register beach strips).

Seams re-cut against the corrected placement: **one connected piece, 0 px²
overlap, 8 interior holes.** Address lookup extended to streets 7-46 and all
28 avenue slots.

## Human queue

See `HUMAN_QUEUE.md` — open items:
- **HQ-19** plate margins bleed in where a cut lands on a centreline; 8 holes
  remain, of which the two largest are genuine source gaps (25% and 37% of
  that ground is on any plate).
- **HQ-18** the existing 154 controls were proposed by a detector that finds
  alleys, not avenues; a width-test pass over them is not yet done.
- **HQ-7** 1899 `71a` drawn but unverified and visibly misplaced.

HQ-1..HQ-4 resolved; HQ-6, HQ-8, HQ-9 and HQ-17 fixed.

# Galveston Sanborn mosaics — status

**Updated:** 2026-08-29 (Stage 4 partial: 1912 tools live) · **Branch:** `claude/galveston-setup-part-a-mk5z1l` · **Ledger:** `state/ledger.json`

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

## Human queue

See `HUMAN_QUEUE.md` — 1 open item (HQ-7: 1899 `71a` drawn but unverified
and visibly misplaced). HQ-1..HQ-4 resolved, HQ-6 fixed.

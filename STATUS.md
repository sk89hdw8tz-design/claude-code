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
| th-hydrant-514 (symbol) | 14\|16 | 16.3 — HQ-4 |
| red-disc-7 (symbol) | 11\|12 | 14.3 — HQ-4 |
| blk-sw-corner-east-of-tracks | 08\|07 | 7.7 |
| pier22 corners | 07\|06 | ≤5.6 |
| all remaining structural | — | ≤3.6 |

## Active agents

| agent | task |
|---|---|
| orchestrator | all stages complete; awaiting HUMAN_QUEUE answers |
| measurers A–D | ✅ finished (63 relocations + 5 new features) |

## ETA

All cloud stages complete. Remaining: HUMAN_QUEUE answers (HQ-1..4) and the
off-cloud full-resolution renders/DZI (single commands, documented in
REPORT.md).

## Human queue

See `HUMAN_QUEUE.md` — 4 open items (Part B; 1899 scope; 1912 D-019/D-023; 1899 symbol-variance adjudication HQ-4 with PNGs).

# Galveston Sanborn mosaics — status

**Updated:** 2026-08-29 (Stage 4 partial: 1912 tools live) · **Branch:** `claude/galveston-setup-part-a-mk5z1l` · **Ledger:** `state/ledger.json`

## Headline

| | 1899 | 1912 |
|---|---|---|
| Sources inventoried | **102/102** (UT PCL, sha256 ✅) | **129/129** (LOC IIIF, sha256 ✅) |
| Target sheets | 13 (of which 13 in repo) | 13 + 1 context (18 archival JP2s in repo) |
| Registration | ✅ full-affine rebuild, gated | ✅ solved affines (prior accepted run) |
| Seams | ✅ 19 min-ink cuts + ownership | ✅ cuts + masks frozen |
| QC | ⬜ | ✅ prior run1 + 2 reviewer reports |
| Recipe consolidated | ⬜ | ✅ (hash-verified vs freeze) |

## Stage bars

```
Stage 0  inventory + environment   ██████████ done
Stage 1  consolidate 1912 recipe   ██████████ done
Stage 2  register 1899             █████████░ solved + gated (HQ-4 adjudication open)
Stage 3  QC + human queue          ░░░░░░░░░░
Stage 4  indexes + render/crop     █████████░ both years live (crop.py verified on 1899 + 1912)
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

1899: measured after the consolidated solve.

## Active agents

| agent | task |
|---|---|
| orchestrator | 1912 indexes + tools; 1899 solve pending relocations |
| measurer A | wharf + Avenue A landmarks (running) |
| measurer B | ✅ 16/16 located (dash-* features condemned as unshared) |
| measurer C | center seams (running) |
| measurer D | ✅ 12/13 located |

## ETA

Stage 1 is file consolidation (no compute): hours, not days. Stage 2 (1899
registration) is the long pole; band depends on how many control pairs verify
cleanly at half resolution. Estimate firms up after the first seam group.

## Human queue

See `HUMAN_QUEUE.md` — 4 open items (Part B; 1899 scope; 1912 D-019/D-023; 1899 symbol-variance adjudication HQ-4 with PNGs).

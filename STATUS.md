# Galveston Sanborn mosaics — status

**Updated:** 2026-08-29 (Stage 4 partial: 1912 tools live) · **Branch:** `claude/galveston-setup-part-a-mk5z1l` · **Ledger:** `state/ledger.json`

## Headline

| | 1899 | 1912 |
|---|---|---|
| Sources inventoried | **102/102** (UT PCL, sha256 ✅) | **129/129** (LOC IIIF, sha256 ✅) |
| Target sheets | 13 (of which 13 in repo) | 13 + 1 context (18 archival JP2s in repo) |
| Registration | ⬜ provisional grid only | ✅ solved affines (prior accepted run) |
| Seams | ⬜ | ✅ cuts + masks frozen |
| QC | ⬜ | ✅ prior run1 + 2 reviewer reports |
| Recipe consolidated | ⬜ | ✅ (hash-verified vs freeze) |

## Stage bars

```
Stage 0  inventory + environment   ██████████ done
Stage 1  consolidate 1912 recipe   ██████████ done
Stage 2  register 1899             ████░░░░░░ in progress (landmark relocation: 2/4 agent groups done)
Stage 3  QC + human queue          ░░░░░░░░░░
Stage 4  indexes + render/crop     ██████░░░░ 1912 done (grid, 3 geojsons, crop.py + render.py verified)
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

Not yet measured this run. The prior 1912 QA seam matrix lives at
`claude/galveston-1912-sanborn-mosaic-747rju:galveston-1912/70_qa/run1/seam_matrix.md`
and is consolidated in Stage 1.

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

See `HUMAN_QUEUE.md` — 3 open items (Part B unavailable; 1899 scope; 1912 D-019/D-023 approval).

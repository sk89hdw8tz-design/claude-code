# Controller measurement brief (binding for all measurement agents)

You are measuring seam controls for the 1912 Galveston Sanborn 12-sheet block.
INDEPENDENCE RULE: do NOT open `fable_review/` or `30_controls/harvest/` — your numbers
must be independent of prior measurements. You MAY read this brief, the protocol, and
the topology files listed below.

## Read first
- `30_controls/VERIFICATION_PROTOCOL.md` (including the 2026-08-17 amendment block — binding)
- `30_controls/CONTROL_STRATEGY.md`, `30_controls/SEAM_STRUCTURE.md`
- `10_key/adjacency.json`, `10_key/SELECTION.md`
- `90_decisions/FAILED_EXPERIMENTS.md` (F-001..F-004 — do not repeat these detectors)

## Sources (read-only; never modify)
`/home/user/g1912/data-branch/galveston_1912_sources/sanborn08539_004_imgNNN_archival.jp2`
sheet→img: 7→011, 8→013, 9→015, 10→017, 11→019, 12→021, 39→049, 40→050, 43→053, 44→054, 49→059, 50→060.
All 6653×7795. Python: `/home/user/g1912/venv/bin/python` (PIL/cv2/numpy; set `Image.MAX_IMAGE_PIXELS=None`).
SHA-256 per file: `00_inventory/INVENTORY.json` (bind `source_sha256` fields from it).
Navigation panels (never for coordinates): `/home/user/g1912/work/panels/pair_XX_YY.jpg`.

## Method (semi-manual; automation may only locate/illustrate)
Per seam, 2 interior crossing anchors (vertical seams: the two interior numbered streets;
horizontal seams: the interior avenues). Per anchor, on BOTH plates: cut your own 1:1
crops at the corner adjacent to the seam street, with drawn pixel rulers; read the TWO
flanking block-face/property lines of the crossing feature; record segment endpoints
(both ends of the span you read), at the corner nearest the seam. Read the printed
address runs / labels in the same crop — they are your disambiguation evidence.
Excluded as precision control: water mains/dashed pipes, hydrants, symbols, bare labels.
Known trap (seam 7-9): 20-ft mid-block alley near x≈5400 carries the 10" pipe and mimics
an avenue; verify anchor identity by address runs.

## Record schema — write one JSON per seam to `30_controls/verified/pair_A_B.json`
```json
{"pair": [7,8], "axis": "vertical", "boundary": "Ave C (Mechanic)",
 "observer": "<agent-name>", "controls": [
 {"anchor": "19th St", "status": "ACCEPTED|REJECTED|CONTEXT_ONLY",
  "class": "observed",
  "why_not_one_block_off": "<explicit sentence naming printed evidence>",
  "anchor_evidence": "<address runs, labels, block numbers read on the crops>",
  "A": {"sheet": 7, "face1_seg": [[x,y],[x,y]], "face2_seg": [[x,y],[x,y]],
        "measured_at": "<where along frontage>", "sigma_along_px": 0.0,
        "sigma_basis": "<clean rule / obstructed etc>", "source_sha256": "<from inventory>"},
  "B": {... same for other sheet ...},
  "drafted_width_px": {"A": 0.0, "B": 0.0, "annotation": "<e.g. 80' printed mid-street>"},
  "evidence_crops": ["<paths>"], "notes": "<incl. any plate disagreement, recorded not reconciled>"}]}
```
Axis convention: raster pixels, origin top-left, x right, y down. Per-reading sigma from
stated criteria (clean single rule ≈ half line width; obstructed/doubled ≥2×) — identical
sigmas across a file fails review. Keep REJECTED/CONTEXT_ONLY entries with reasons.
Evidence crops → `70_qa/control_evidence/` named `pairA-B_<anchor>_sheetN.jpg`; annotate
only your own crops.

## Self-adversarial pass (mandatory, after measuring)
Re-challenge each control: neighbouring block? pipe/continuation rule instead of face?
same drafted feature on both plates (same corner, same face)? coordinate from a
compressed image? Downgrade/reject failures; do not inflate counts.

Final message: per seam — anchors accepted/rejected, drafted-width agreement values,
any plate disagreements, and anything contradicting the documented topology.

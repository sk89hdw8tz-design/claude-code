# Control verification protocol — Galveston 1912

Adopted after F-004: automation proposes and illustrates; a human reads and records.
Nothing enters the solve that was not read off the plates by eye.

## Instruments

1. **Seam panels** (`tools/seam_panels.py`, one per pair, all 17 generated):
   both plates' near-seam strips side by side with a full-resolution pixel ruler
   every 500 px. Purpose: locate each crossing feature, confirm its name from the
   street labels, and choose the corner windows for fine reading.
2. **Fine corner crops** (`tools/pair_window.py` with tick rulers, generated on
   demand per intersection): native-resolution windows around one crossing-feature ×
   seam-street corner on both plates. Purpose: read the flanking block-face line
   positions to ±10 px or better.

## What is recorded per control

One control = one crossing feature at one seam, observed on both plates.

```json
{
  "pair": [7, 8],
  "seam": "Ave. C (Mechanic)",
  "anchor": "19th St",
  "anchor_evidence": "street label '19TH ST.' and address run 216-224/215-223 (sheet 7), 1823-1829/301-307 (sheet 8) read on the panel",
  "class": "observed",
  "A": {"sheet": 7, "north_face_y": null, "south_face_y": null, "measured_at_x": null},
  "B": {"sheet": 8, "north_face_y": null, "south_face_y": null, "measured_at_x": null},
  "sigma_along_px": 8.0,
  "sigma_across": "constructed from drafted street width at solve time",
  "verified_by": "visual read of fine corner crops",
  "notes": ""
}
```

- Both flanking faces are recorded (e.g. north and south frontage of 19th St): the
  *pair* of lines is the disambiguating shape, and their separation must agree with
  the drafted street width — a built-in sanity check per control.
- `measured_at_x` (or `_y` for horizontal seams) records where along the face the
  reading was taken, because frontages jog between corners; readings on the two
  plates must be taken at corresponding corners, i.e. adjacent to the seam street.
- Block numbers and address runs go in `anchor_evidence`, never inferred from layout.

## Acceptance rules

- A control is `verified: true` only after both plates' readings come from fine
  crops (never from the compressed overview panels alone — panel scale ~0.24 makes
  a 1-px reading error ~4 px on the plate).
- Pipe lines, hydrants, and symbols are never measured, per the brief; if a street's
  only visible structure near the seam is its pipe line, the control moves to the
  next corner along the seam.
- Disagreements between the two plates' face positions are recorded as found — they
  are data (drafting or survey difference), not errors to reconcile at harvest time.

## Coverage target

Per vertical pair: the two interior crossing streets, both faces each — 2 controls.
Per horizontal pair: the interior crossing avenues — 1–2 controls.
Boundary features (clipped at plate corners) are junction QA, not primary control.
Network total: ~29 controls / ~58 line readings across 17 pairs, each anchored by
name and address evidence — enough for a strongly redundant 4-DOF-per-sheet solve
of the 12-sheet block.

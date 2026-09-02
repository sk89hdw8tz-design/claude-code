# Periphery review brief (1912 Galveston Sanborn mosaic)

`edge_NN.jpg` are 1/4-scale windows (1 px ≈ 1.4 ft) laid along the OUTER
boundary of the city mosaic. Blue numbers are the plate/panel ids that own
each region. White is unpainted canvas (no plate covers it).

For each window report what is visible at the mosaic's edge that is NOT
map content and should not print, and any defect inside the window:

- **furniture**: a large plate number (e.g. "26", "48", "99"), a lone
  adjoining-sheet numeral ("0", "74"), a north arrow / compass rose, a
  scale bar, a plate title ("Galveston, Texas", "Aug 1912"), a border rule
  or bracket marks. Give its approximate position in the window as
  fractions (x, y from top-left, 0–1) and what ground it sits on (blank
  paper, water, roadway, drawn blocks).
- **margin**: bare paper beyond the plate's rule, scanner border, paper
  edge or shadow showing inside the mosaic.
- **gap**: white canvas that looks like it should be mapped (a street that
  stops at white, half a block missing), as opposed to the bay, the Gulf,
  or the end of the city.
- **misplacement**: a plate whose streets or blocks obviously do not line
  up with its neighbour (step > ~20 ft, duplicated street, doubled label).
- **wrong-owner**: a strip of one plate's coarse or blank drawing where the
  neighbour draws the same ground in detail.

Return ONLY a JSON array, one object per window:

```json
[{"window": "edge_07.jpg", "ok": false,
  "findings": [{"kind": "furniture", "what": "plate number 26", "at": [0.82, 0.12],
                "ground": "Gulf water", "units": ["26b"]},
               {"kind": "gap", "what": "36th St runs into white", "at": [0.4, 0.9], "units": ["82"]}],
  "note": "one sentence"}]
```

Use `"ok": true` with an empty findings list when the window shows only
map content, water, or the natural end of the mapped city. Do not report
paper stains, foxing, or tone as defects.

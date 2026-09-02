# Registration review brief (1912 mosaic, correction round)

You are checking seams where the census graders saw a STEP between two
plates (block faces, alleys, pipe runs jogging at the cut by 8–35 ft). Your
job: decide, from the plates themselves, whether one plate is misplaced and
propose the tie that would fix it. You do NOT apply anything.

## What you have

- `outputs/1912/qc/seams/census_round3.json` — every seam's grade, the
  grader's reason and fix_hint (`seams[]`, keyed by `seam` like `53_54`).
- `outputs/1912/qc/seams/seam_<a>_<b>[_a|_b]_100.jpg` — the crop(s) of the
  seam at working resolution (1 px = 0.35 ft; a 70 ft avenue ≈ 200 px, an
  80 ft street ≈ 230 px). `_50.jpg` is the overview.
- `outputs/1912/recipe/controls/pair_<a>_<b>[_x|_y].json` — accepted
  controls. `axis: "avenue"` pins x (a_native/b_native are native x on each
  plate), `axis: "street"` pins y. `observer` starting with `lattice` means
  the tie was read by a detector with identity taken from the placement —
  treat those as suspect when they disagree with what you see.
- `outputs/1912/recipe/plates/lattice.json` → `units[<plate>][y|x].faces`:
  the block-face pairs of every street (y) / avenue (x) chain on the plate,
  in native px, top-to-bottom / left-to-right. `units.json` `streets` and
  the key maps (`rebuild_1899/out/keymap_1912_*.json`) say which streets and
  avenues a plate covers, so face index → street name.
- Working images: `work/sheets/1912w/u<plate>.jpg` (native px), if you need
  to read a lot number or a label to settle identity. Use Read on a crop you
  make with python/cv2 rather than the whole plate.
- `python3 tools/localsolve.py --year 1912 --units <plate>` prints, for the
  named plate held free with everything else fixed, the residual of every
  control touching it and the move it would make (dry run; `--similarity`
  also solves rotation and scale from the controls as lines). Never pass
  `--apply`.

## Method (per seam)

1. Look at the crop. Name the feature that steps (which street/avenue, which
   block faces or alley or pipe) and estimate the step in ft and its
   direction; note whether it is constant along the seam (translation) or
   grows along it (rotation/scale), and whether the two plates simply DRAW
   the feature differently (e.g. Broadway drawn 108 ft on one plate and 146
   on the other, both labelled 150'; a street drawn 40 ft on one plate and
   80 on the other) — that is a source disagreement, not registration.
2. List the controls on the pair and on each plate's other seams. Which
   axis is unconstrained? Is a `lattice` tie holding the plate where it is?
3. Decide which plate is wrong: the one that disagrees with MORE of its
   neighbours (check the neighbouring seams' grades and crops).
4. If it is registration, propose the tie: the shared corridor's name, its
   face pair on each plate from lattice.json (or measured), the centre
   (midpoint of the faces) as a_native/b_native, and the identity argument
   (printed names, address runs / lot numbers, key-map coverage) — the same
   standard as the existing observer controls' `why_not_one_block_off`.
   Then run the dry-run localsolve on the plate you would move and report
   its residuals and move.

## Output

Write a JSON array to the path you were given, one object per seam:

```json
[{"seam": "53_54", "verdict": "registration" | "source-disagreement" | "cut-only" | "ok",
  "feature": "25th St block faces (116/115) and the 8in pipe",
  "step_ft": 27, "direction": "plate 54 north of 53", "varies_along_seam": false,
  "plate_to_move": "53", "why_this_plate": "...",
  "proposed_ties": [{"file": "pair_53_54_y.json", "action": "reject" | "add" | "replace",
                     "axis": "street", "corridor": "25th St", "a": 53, "b": 54,
                     "a_native": 2529.0, "b_native": 2522.0,
                     "faces": {"53": [2408, 2650], "54": [2401, 2643]},
                     "why_not_one_block_off": "..."}],
  "dry_run": "localsolve output summary: residuals median x ft, max y ft; plate moves (dx, dy) ft",
  "confidence": "high" | "medium" | "low",
  "note": "one or two sentences"}]
```

Be concrete and honest. If you cannot tell which plate is wrong, say so
(`confidence: low`) rather than guessing. Do not edit any recipe file.

# Proposal: win_123 — "2117" on the 42nd St north block face is cut by unit 88's blank paper

Opus evidence reviewer, wave 4 interior 1:1 sweep. **Dry-run only — nothing applied, no recipe file edited.**
Window win_123 = mosaic rect [33879,45032,35379,46532], units 88 / 96 / 97; defect point ≈ mosaic (34659,45587)
(= window px [780,555] of `outputs/1912/qc/interior/win_123.jpg`). Mosaic frame 5.7966 px/ft.

## Defect

The odd-number run on the south face of 42nd St (2113 2115 2117 2119 2121 2123) is drawn by **unit 96**.
Only "2117" is mutilated: its terminal "7" survives as its bottom tail alone. The pixels over the upper
half of the digit are owned by **unit 88**, which is blank paper there.

* owner at (34659,45587): **88** (`ownership_shapes()`; 96's polygon starts one row lower)
* footprints covering it: 88 and 96 only — no third plate is involved
* native coordinates: 88 → (1853.3, 3773.4); 96 → (2854.9, 341.7)
* 96 draws the numerals at native rows 331–348, its 42nd St south frontage rule at rows 350–352
* 88 is blank at native (1306–1891, 3690–3785): `frac(grey<140) = 0.0000`, min grey 158–166 on every
  sampled row 3690…3782. Its last drawn ink in that column band is row 3688 (the "42ND ST." street
  label, rows ~3650–3690); its own block numbers 2102–2122 are at row 3555.

So 88 is blank there **because the point lies in the blank strip between that plate's last mapped content
and its neatline extent bottom** (`extent[3] = 3778`), not because it draws different content. The extent
itself is right and must not be tightened: across the full width `x 90..3224`, unit 88 carries ink on
every row down to 3780 (`frac(grey<140)` 0.07–0.15 for rows 3724–3780, min grey 1–27), and its border
rule is at row 3784 (`frac = 0.715`). The blank is local to x 1306–1891, i.e. the 42nd St roadway.

## Cause — a furniture box, not an extent, exclude, fillgaps patch or plain streetcut jag

`outputs/1912/recipe/units.json`, unit **96**:

```json
"extent": [92, 118, 3224, 3776],
"extent_source": "tools/neatline.py: inner edge of the border rule",
"furniture_native": [
  ...
  { "kind": "compass rose",
    "box": [2314, 112, 2886, 322],
    "how": "compass rose, disc + starburst + both NW/SE arrow tails in the street strip above the
            2101-2123 block; the whole ornament is one ink component [2346,117,2880,351]; the box top
            sits below the street rule at y~108 and the bottom above the address-numeral row at y~335,
            so it holds the rose and no map ink. ...",
    "cut": true, "covered_fraction": 1.0 }
]
```

`reciplib.Recipe.footprint_native` subtracts each `cut: true` box **grown by 6 px**:

```python
b = f["box"]
g = g.difference(box(b[0] - 6, b[1] - 6, b[2] + 6, b[3] + 6))
```

`112 - 6 = 106`, and the plate's extent top is **118**. The grown box therefore reaches *outside* unit 96's
own footprint, so the difference does not punch an interior hole — **it opens a notch through the north
boundary of 96's footprint**, 572 native px (1181 mosaic px) wide, from the plate edge down to native
row 328 (mosaic y 45551→45559 across mosaic x 33553→34734).

Consequences, in order:

1. `O = base[88] ∩ base[96]` (tools/streetcut.py) inherits the notch as part of its **exterior** ring.
2. `dp_cut` builds its cost mask as `cv2.fillPoly(mask, [O.exterior], 1)` — interiors are ignored, which
   is harmless for a true hole but here bans the whole notch. Measured allowed rows per column:
   `x 33600–34700 → only y 45550…45594` (elsewhere the band is `45394…45594`).
3. The min-ink path is squeezed into that 35–45 px slot, which is exactly where unit 96 letters
   2113–2123. Recorded seam (`outputs/1912/recipe/seams/ownership_city.json`):
   `{"pair": ["88","96"], "axis": "y", "coord": 45353.96, "cut": "min-ink path", "how": "midpoint",
   "kind": "band", "overlap_px2": 1090207, "span_px": 4316}` — the chosen candidate is `off +120`
   (target y 45474), i.e. the seam *wants* to run 90 px north of where it ends up.
4. Where the compass rose's SE arrow tail (last ink at native row 313, x 2845) is dilated by
   `DP_DILATE = 13` cells = 52 mosaic px = 26 native px, the slot's top rows also become expensive, and
   the path drops a further 7 cells to clear the halo. That is the notch that eats the "7".

The resulting boundary in `ownership_city.json` region `{"unit": "88", "source": "street-centreline cut"}`
is axis-aligned because `dp_cut` is quantized to `DP_SCALE = 4` mosaic px (the ±0.448 rounding is
`g.buffer(-1.0).buffer(1.0)` at the end of streetcut):

```
... [34622.813, 45558.448], [34627.345, 45558.495], [34655.006, 45586.155],
    [34682.884, 45586.448], [34683.591, 45586.155], [34710.707, 45559.040],
    [34733.344, 45559.170], [34734.395, 45551.376], [34811.281, 45474.466] ...
```

Reconstructed with `streetcut.dp_cut(R,'88','96','y',45353.96,O,lower='88')` the path is exactly
`(34627,45558) → (34655,45586) → (34683,45586) → (34711,45558)`. It is **not** fillgaps (no `gap_fill`
entry lies in this window), **not** an exclude edge (96's only `exclude_native` is its title box at
[3018,118,3224,268]), and **not** the box's own bottom edge — but the box is what forced the path there.

Control experiment: whitening the rose inside its box in `dp_cut`'s cost changes nothing (the box is
already masked out), while restoring the box as an interior hole moves the path 90–160 px north. The
notch, not the rose ink, is the lever.

## Evidence — native ink profiles

Unit 96, columns x 2314–2886, `frac(grey < 130)` / min grey per row:

| native row | frac<130 | min | what |
|---|---|---|---|
| 104–115 | 0.023 → **0.777** (row 110) | 4 | the plate's border rule; `extent[1] = 118` is its inner edge |
| 119–125 | 0.018–0.038 | 16–22 | uppermost starburst tips (mostly outside the extent) |
| 137–312 | 0.10–0.27 | 0–30 | the compass rose proper |
| 314–330 | 0.253–0.283 | **84–107** | **no ink** — clear gap (the 0.25 is dark paper, not ink) |
| 331–348 | 0.38–0.58 | 0–15 | the 2113–2123 numerals |
| 350–352 | **0.918** | 0 | the 42nd St south frontage rule |

Column detail at the "7" (x 2830): grey 111,111,111,112,113,112 for rows 325–330 (paper), then
104,68,49,53 for rows 340–343 — the numeral. The wrong-owner boundary sits at native row 341.5 here.

Unit 88, columns x 1306–1891, `frac(grey < 140)` / min grey:

| native row | frac<140 | min | what |
|---|---|---|---|
| 3550–3560 | 0.145–0.242 | 0 | north frontage rule + 2102–2122 |
| 3660–3688 | 0.10–0.14 | 0–3 | "42ND ST." label |
| 3690–3782 | **0.0000** | 158–166 | **blank roadway / margin — the disputed strip** |
| 3784 | 0.715 | 3 | border rule (`extent[3] = 3778` is its inner edge) |

Geometry of the squeeze: box bottom 322 + 6 = native 328 → mosaic 45551–45559; unit 88's extent bottom
3778 maps to 96-native row ≈ 345, i.e. **into the middle of 96's numeral row**. The seam's whole
available slot is 96-native rows 328…345 and the numerals occupy 331…348.

## Change

`outputs/1912/recipe/units.json`, unit **`96`**, `furniture_native[2]` (`"kind": "compass rose"`),
field **`box`** — raise the top edge only, so the grown box stays inside the plate's own extent
(`box[1] - 6 > extent[1]`, i.e. `box[1] ≥ 125`):

```
  "box": [2314, 112, 2886, 322]     ->     "box": [2314, 125, 2886, 322]
```

and extend the `how` note with: `top clamped to extent[1]+7 = 125 so the 6 px grow in
footprint_native keeps the cut an interior hole; at 112 the grown box crossed the neatline extent
(118) and severed the 88|96 overlap band (wave-4 win_123).`

No other field changes. `cut` stays `true`; `covered_fraction` recomputes to **1.0** (verified), so the
box still passes the ≥98 % rule in `tools/furncover.py` and the rose is still removed from the mosaic.

Nothing is done to unit 88: its `extent` bottom 3778 is the neatline and carries map ink across most of
the plate, so under the "extents are relaxed/tightened only where the native scan holds no ink and no
border rule" test it cannot be trimmed, and a local `exclude_native` strip on 88 was tested and rejected
(below).

### Verified effect (simulated in memory; no file written)

| | before | after |
|---|---|---|
| `footprint(96)` interior rings | 0 (open notch) | 1 (true hole) |
| `O = f88 ∩ f96` | one polygon with the notch cut out of its exterior | one polygon, box as interior ring |
| dp path over x 33555–34737 | y 45550 → **45586** (dips onto the numerals) | y 45394–45530, 32–96 native px clear of them |
| owner of (34659,45587) | 88 (blank) | **96** ("2117" whole) |
| owner of the rose centre (34100,45300) | 88 | **88** (unchanged — rose still suppressed) |
| new `covered_fraction` | 1.0 | 1.0 |

Rose rows 119–124 are no longer inside the cut box, but they lie ~330 mosaic px north of the corrected
seam and are owned by 88 there, so no rose fragment prints.

### Alternatives tested and rejected

* **`cut: false` on the compass rose** — restores the overlap and saves the numerals, but the seam then
  runs *through* the rose (path y 45394–45530 vs rose ink to y 45528) and 96 would print the lower half
  of the ornament: exactly the half-legend failure `furncover.py`'s docstring warns about.
* **`exclude_native` strip on unit 88** (e.g. `[[1290,3757],[1900,3757],[1900,3778],[1290,3778]]`) — it
  does hand "2117" back to 96, but box + strip together span the full height of the 88|96 band, so
  `O` splits into two polygons (172 970 px² east + 868 615 px² west), `dp_cut` cuts only the larger, the
  chosen candidate flips from `off +120` to `off −120` and the whole 4 316 px seam moves ~300 px north.
  Too big a blast radius for a 28 px defect.
* **Lowering the box bottom (322 → larger)** — makes 88's blank claim reach further into the numerals.
* **Raising the box bottom (322 → 316)** — the numerals stay inside the 26-native-px dilation halo, so
  the path still dips. Does not fix it.

## Side-effects

* **Re-runs required, in order:** `tools/streetcut.py --year 1912 ... --apply` (regenerates
  `seams/ownership_city.json`; the 88|96 seam moves over x 33553–34737 and only there),
  then `tools/fillgaps.py`, then the render / QC crops for win_123 and its neighbours.
* **`tools/furncover.py --apply` need not be re-run** and is safe if it is: it rewrites only `cut` and
  `covered_fraction`, never `box`, and the new box still scores 1.0 ≥ 0.98, so it will not revert the
  edit.
* The seam change is confined to the 88|96 pair; no third unit's footprint covers this ground
  (checked at five points along the box).
* 88 keeps the whole compass box, so the composite still shows 88's blank 42nd St roadway with its own
  "42ND ST." label; unit 88's 2102–2122 row (mosaic y ≈ 45144) stays north of the new path.
* **Same defect class elsewhere (not fixed here, recommend a sweep):** 41 `cut: true` furniture boxes
  cross their plate's extent *mid-edge* and so open the same severing notch. The widest are the 11
  scale bars (645–715 native px: units 8, 11, 16, 19, 27, 28, 33, 49, 53, 56, 72) and this compass rose
  (572 px); the rest are edge numerals ≤203 px. The general repair is the same one-line clamp
  (`box` inset to `extent ± 7`) or, better, doing the clamp inside `footprint_native`.

## Same-edge check along the whole boundary

The wrong-owner strip is the full south edge of the notch: mosaic **(33553, 45551) → (34734, 45559)**,
1181 px long, with 88's blank paper immediately north of 96's whole 2101–2123 number line. Measured
per 5 px column (boundary row vs 96's topmost numeral ink, local paper-relative threshold; 219 columns
carry numeral ink):

* **cut, i.e. clearance < 0:** only mosaic x **34630–34690** — "2117". Worst clearance −8.5 native px
  (−17 mosaic px) at x 34655–34683, y 45586. Affected mosaic points: (34640,45571), (34655,45586),
  (34659,45587), (34670,45586), (34683,45586), (34700,45569).
* **near misses (< 3 native px ≈ 6 mosaic px of clearance):** x 34500 (the "5" of **2115**, 2.8 px);
  x 34420 and 34380 sit at 3–4 px (**2113**).
* the rest of the run clears by 3–22 native px (6–45 mosaic px) — legible but with no margin; the
  boundary is riding the tops of the digits for the entire 1181 px.
* Nothing else is clipped along the edge: the "20'" alley-width label (mosaic x ≈ 34290, y ≈ 45620) and
  the block outlines are south of the strip, and unit 88 draws nothing north of it that 96 could take.
* West of x 33553 and east of x 34734 the seam returns to y 45394–45490 and clearances exceed 100 px
  (2101–2111 and 2119–2123 are untouched — they only *look* endangered in the strip crop).

After the proposed change the minimum clearance along the same 1181 px rises to 32 native px (65 mosaic px).

# Proposal: cut placement and furniture — wave 4 (14|49, 20|20b, 25|25b, 54|54b, 63|70, 63|71, 64|72)

Opus developer-reviewer, wave 4. **Dry-run only.** No tool was run with `--apply`; no file under
`outputs/1912/recipe/` was written. The only working-tree change is `tools/streetcut.py`
(uncommitted, +267/−16), and every behaviour it adds is **off by default** — a plain
`python3 tools/streetcut.py --year 1912 --out <scratch>` still reproduces
`outputs/1912/recipe/seams/ownership_streetcut.json` **byte for byte** (verified, `own_check.json`).

Scratch dir for every dump and crop below:
`/tmp/claude-0/-home-user-claude-code/667180c2-8c6a-5c7c-8f63-764f5714e1d7/scratchpad/`
(abbreviated `$S` from here). Mosaic 5.7966 px/ft. Crops are rendered at 1:1 (`qcrender.render(..., d=1)`)
from a scratch copy of the ownership document, with `Recipe.masks` swapped in memory.

---

## 0. The three mechanisms behind six of the seven seams

Before the per-seam entries, the thing that makes this a class rather than seven accidents.

**(A) A water main is drawn ON the street centreline, and the centreline is where the seam goes.**
A control corridor or an overlap midpoint puts the cut within a few px of the very line both plates
draw. Two failure modes follow, and both are visible here:

| | 63\|71 | 64\|72 |
|---|---|---|
| cut coordinate | y 24502.23 (control, 33rd St) | y 24531.28 (overlap midpoint) |
| plate A's 10"/8" main | 63 at y **24532–24552** (dark-fraction 2.8–5.3 % of rows, x 19739–20679) | 64 at y **24540–24548** (4.0–5.4 %, x 25575–26675) |
| plate B's main | 71: **0.0–0.9 %** everywhere in y 24460–24560 — 71 does not draw it here | 72 at y **24514–24524** (12.2–22.9 %) |
| result | 63's main lies on 71's side of a straight cut; 71 is blank there, so the main **vanishes** over x 1050–1520 of the crop (165 ft) | the cut falls **between** the two copies, 25 px (4.3 ft) apart; each copy lands on the side owned by the plate that does not draw it, so the main vanishes from **both** and two `8" W. PIPE` labels are orphaned |

The isotropic `DP_DILATE = 13` cells cannot see this: it is symmetric in "along the seam" and
"across the seam", so it cannot distinguish a path *crossing* a line from a path *riding* one or
*threading between two copies* of one.

**(B) `kind: "corner"` is decided by a fraction of the sheet, not by how much roadway is shared.**
`band = span >= BAND_FRACTION * across` with `BAND_FRACTION = 0.6` measured against the *shorter
sheet's* width. A diagonal-neighbour pair shares a full block-and-a-half of one street and still
fails the test, so it never reaches `dp_cut` at all and gets an axis-aligned half-plane straight
down the corridor — i.e. straight down the main in (A):

```
63|71  span 2355 px / sheet 6361 px = 0.370  -> CORNER  (overlap 1,145,931 px2 = 406 ft of 33rd St, band 95 ft wide)
64|72  span 2268 px / sheet 6382 px = 0.355  -> CORNER  (overlap 1,128,458 px2 = 391 ft,          band 88 ft wide)
```

This is not two seams. **32 of the 117 "corner" seams have span ≥ 2126 px** (≈ 367 ft) and overlaps
of 0.6–1.3 M px²: `5b|13 5a|9 6|33 71|78 78|86 87|96 68|75 63|71 89|98 76|83 16|68 81|89 80|88
62|70 15|67 74|81 79|87 72|79 70|77 77|85 65|73 82|90 85|94 64|72 73|80 88|97 66|74 86|95 61|69
69|76 77|84 85|93`. Every one of them is currently a straight half-plane on the corridor line.

**(C) A side candidate wins whenever one side is merely *feasible*.**
`sides = [...]; if side >= 40.0 and sides: best = sides[0]`. Where the band is narrow, the
forbidden half-plane makes one side infeasible (`crossed` ≈ 9e8, i.e. the path is forced through
`BIG` cells) and the survivor wins unopposed — **even when it is worse than the centre on both
metrics**. From `$S/cand_base.json` (new `--cand-dump`):

```
20|20b   centre  visible 3,780,075  crossed 142,737     <- better on both
         +109.5  visible 3,835,267  crossed 142,967  *chosen  (+1.46 % worse)
         -109.5  infeasible (crossed 9.10e8)
25|25b   centre  visible 8,593,652  crossed 105,540     <- better on both
         +120    visible 8,633,381  crossed 106,233  *chosen  (+0.46 % worse)
         -120    infeasible (crossed 1.01e7)
63|71    centre  visible 7,361,000  crossed 121,220
         +120    visible 7,434,000  crossed 121,146  *chosen  (+0.99 % worse on visible)
```

Across the whole build, a side is chosen on **149 of 172** min-ink seams, and **59 of those 149
choose a side that is worse than the centre on `visible`** — up to +13.7 % (82|99). So the rule
is doing something `visible` does not measure. Crucially the two pairs the side rule was written
for are in that list too — **57|58 (+8.68 %)** and **76|84 (+1.26 %)** — which is why the blunt
fix is wrong (see §3, `--pick-best`).

---

## 1. Per-seam findings

### 14|49 — score 3, clipped italic annotation at the four-plate crossing

**Cause.** Not a `dp_cut` defect: `14|49` is `"kind": "corner"`, `"cut": "straight"`, overlap only
13,662 px² (286 × 87 px, a 15 ft sliver). The clipped label at mosaic **(3107, 10593)** is owned by
**plate 12**, and the two edges that slice it are **plate 12's region corner at (3127, 10628)** —
i.e. the vertical at crop x ≈ 1257 and the horizontal at crop y ≈ 824 the grader measured.

That corner comes from `seams/masks.json`, not from streetcut: **12 and 49 are both frozen-core
plates**, so `main()` hits `if u in core and v in core: stats["core-core"] += 1; continue` and
`base[12] = core[12] ∩ footprint(12)` keeps the 27×40 master's own cut. `streetcut.py` never places
a 12|49 seam and cannot move that edge.

Six seams meet at this crossing on five different coordinates:

```
12|13  y 10577.3 corner straight   12|14  y 10572.1 band min-ink   12|55  y 10575.4 corner straight
14|49  y 10577.5 corner straight   49|55  y 10579.8 band min-ink   14|55  x  3106.4 band min-ink
plus the master's own 12|49 boundary at x 3127 / y 10628
```

Five y-values spread over 7.7 px (1.3 ft) plus two DP paths that jag independently — that is exactly
the "axis-aligned stair-step patchwork" the grader saw. Each pair is cut in isolation; nothing makes
the cuts meet at one point.

**Fix.** No code flag in this proposal changes it (verified: the 12 ring vertex is (3127, 10628) in
both `own_base.json` and `own_new.json`). Two options for the orchestrator, neither taken here:
(i) accept — the 27×40 master's cuts are frozen by policy and the clipped item is a marginal
annotation, not map content; (ii) a junction-snap pass: where ≥3 pairs carry the same control
corridor within ~10 px (here 27th St, spread 7.7 px), pin them all to the mean before cutting. That
is a new tool, not a `dp_cut` flag, and it still cannot move the core-core edge at x 3127.

**Verified-by.** `$S/crop_14_49_crossing_{before,after}.jpg` (mosaic 2950,10450–3300,10760) —
identical; ownership of (3107,10593) is `['12']` in both.

---

### 20|20b — score 2, duplicated "AVENUE" across the cut

**Cause (two layers).** *Layer 1* is mechanism (C): the band is only **243 px (42 ft)** wide, so
`side = min(120, 243/2 − 12) = 109.5` and `margin = 40`; the west candidate is infeasible and the
east candidate wins although the centre beats it on both metrics (table in §0). The chosen path runs
**x 15349–15425**, i.e. 43–119 px *east* of the control at 15306.78, handing plate 20 the strip that
carries its bold `AVENUE`.

*Layer 2, and this is the finding that matters:* **the duplicate cannot be removed by any cut.**
The two labels are at mosaic **x ≈ 15367 (plate 20)** and **x ≈ 15503 (the inset's complete
"AVENUE L.")**, 136 px = 23 ft apart. The overlap band runs x 15185–15428. I added `--panel-clamp`
(a fourth candidate: the centre line with the panel's side forbidden outright, margin 0 — literally
the regrade's "force the path back to x ≤ 15311") and it is **infeasible**: `crossed = 9.10e8`,
i.e. no continuous path exists west of the centreline inside this overlap polygon. `--panel-centre`
does move the cut (off +109.5 → 0, path x 15285–15425, ownership of (15367,−32303) flips 20 → 20b)
but the DP still jags east to 15425 round the inset's own lettering, and the rendered duplicate
survives.

**Fix.** *Code* `--panel-centre` (moves the cut in the right direction, 132 px). *Recipe, to
actually remove the duplicate*: plate 20's east extent must stop west of its own `AVENUE`. Plate 20
`extent = [86, 91, 3271, 3804]`; its east edge maps to mosaic x 15438, and the letters occupy
mosaic x ≈ 15340–15400 → native x ≈ 3223–3253 (scale 2.026 mosaic px / native px). Trimming
`extent[2]` **3271 → 3218** (mosaic 15438 → 15330) drops the letters and leaves 20b, which maps
that ground, to supply it. **This must not be done on my numbers alone**: the extent is
neatline-derived and the "extents are trimmed only where the native scan holds no ink and no border
rule" test has to be run on plate 20's native scan first. I did not run it.

**Verified-by.** `$S/crop_20_20b_wide_{before,after}.jpg` (mosaic 15100,−32700–15800,−31900):
before shows `AVENUE … L.` twice side by side; after shows the same two runs plus one more restored
glyph of the inset's own `U` — the cut moved, the duplicate did not go. Also
`$S/crop_20_20b_label_{before,after}.jpg`.

---

### 25|25b — score 3, duplicated "80'" 12th St width tick

**Cause — the regrade's location is right and its attribution is wrong.** Converting the grader's
crop coordinates (`window [19781,−27461,22981,−22461]`, 2 mosaic px per crop px):

```
tick A  crop (1187,1620) -> mosaic (22155, -24221)  owner: 25b
tick B  crop (1342,1633) -> mosaic (22465, -24195)  owner: 32     <- not plate 25
```

Both ticks lie **east of plate 25's whole footprint** (25 ends at mosaic x 21820) and east of the
25|25b cut at x 21381. The boundary between them is **25b's own panel frame east edge at mosaic
x 22327** (`region_native` right edge = native 3266). The seam that owns this ground is
`25b|32` (band, min-ink, y −24157.7); both ticks are north of that cut, on either side of 25b's
frame. **The 25|25b cut has nothing to do with it.**

This also disproves the regrade's Gate-A hypothesis: reverting the panel's east edge 3266 → 3239
moves 25b's frame from mosaic 22327 to 22273, still 118 px **east** of 25b's own tick at 22155, so
the duplicate would survive the revert.

**Fix (recipe).** `units.json`, unit `25b`, `region_native`: pull the two east vertices west of
25b's own tick, so plate 32 owns the strip and only 32's tick stands:

```
"region_native": [[2580,83],[3266,83],[3266,1138],[2580,1138]]
              -> [[2580,83],[3170,83],[3170,1138],[2580,1138]]
```

Native 3170 = mosaic 22155 (25b's scale is 2.006 mosaic px / native px over x 2580→3266 =
20951→22327); it sits immediately west of 25b's own `80'`, and 32's raw extent covers the released
strip (32 spans mosaic x 21114–27558). **Ink evidence still owed**: I have the two ticks' mosaic
positions and their owners, but I did not profile 25b's native columns 3170–3266 to confirm nothing
else of value is released there — the regrade itself notes this strip is at the outer edge of source
coverage (seawall band and `GULF OF MEXICO` caption clipped at the inset's east cut), so releasing
it to 32 is likely a net gain, but that must be checked before applying.

**Verified-by.** `$S/crop_25_25b_ticks_{before,after}.jpg` (mosaic 21750,−24400–22600,−24050):
byte-identical — `--panel-centre` moves the 25|25b cut (off +120 → 0, max 152 px) but the ticks are
untouched, exactly as the diagnosis predicts.

---

### 54|54b — score 2, three "T.H." manholes in one intersection

**Cause.** `54|54b` is a band seam, axis y, coord 3536.87, and `dp_cut` chooses **off −120**
(`visible` 6,368,379 vs the centre's 6,420,163 — here the side genuinely wins by 0.8 %). The chosen
path runs y 3334–3494, i.e. 43–203 px **north** of the corridor, and the excursion is what carries
it through the 24th St junction. The two `T.H` copies are a registration split of the same manhole
(12 ft apart on the labels, 23 ft on the dots) and the path passes between them — mechanism (A),
the same failure as 64|72 but on a point symbol instead of a line.

**Why the flags do not fix it.** `--panel-centre` leaves 54|54b alone (the side beats the centre, so
the relaxed test keeps the side). `--line-avoid 1.0` shortens the excursion (`along_line` 4,955 →
3,134 on the −120 candidate) but does not change the choice; at `--line-avoid 3.0` the path pulls
back to y −207..−87, still through the junction. `--panel-clamp` is infeasible here too
(`crossed` 3.88e9).

**Fix.** Not solved. The honest reading is that `DP_SIDE = 120` px (20.7 ft) is smaller than the
registration split at this junction and the band (502 px / 87 ft) is wide enough that the path has
room to wander but no term telling it that a *junction* is the one place it must not. I recommend
the orchestrator treat this as the residual case and, if it wants a fix, add a junction term rather
than tune the existing weights: forbid the path from crossing the corridor's cross-street box
(available from `recipe/intersections.geojson`) anywhere but on a single monotone segment. I did
not implement that — it needs its own evidence pass.

**Verified-by.** `$S/crop_54_54b_intersect_{before,after}.jpg` (mosaic 33300,3400–33750,3850):
byte-identical; three `T.H` symbols in both.

---

### 63|70 — score 2, plate 63's "Scale of Feet" legend in the 33rd St roadway

**Cause (a) — the legend.** Two things have to be true for a plate's furniture to print inside
mapped ground, and both are:

1. `units.json` unit `63`, `furniture_native[1]` (`"kind": "scale bar"`, box native
   `[1920,3622,2557,3718]` → mosaic `[18816, 24445, 20101, 24645]`) has
   **`cut: false`, `covered_fraction: 0.83`** — recomputed independently as **0.830**. See §2 for
   exactly why, and why the 0.98 threshold is *not* the thing at fault.
2. `dp_cut` chooses **off +120** (visible 13,221,401 vs centre 13,417,316 — the side wins by 1.5 %)
   and the chosen path runs y **24550–24714**, i.e. 60–224 px *south* of the corridor, so plate 63's
   region reaches past the box and keeps it.

I tested a fifth switch, `--furniture-visible W`, which weights each plate's own furniture-box
pixels W× in the `visible` score. **It has no effect here and I am reporting that as a negative
result**: both surviving candidates run south of the box (box at −45..+155 relative to the coord;
centre path +60..+224), so both leave it equally visible and the gap between them is constant at
every W tested (1, 2, 5, 20 → 0.196 M in all four). The north side candidate (off −120) is
**geometrically infeasible** (`crossed` 5.85e9): plate 70's footprint does not reach north of the
legend across the whole run. **No cut placement can hand this box to 70.**

**Cause (b) — the doubled 10" W. Pipe at crop x 0–235.** Mosaic x 14758–15228, but plate 63's own
footprint starts at x 15114 — most of that crop range is west of 63 altogether, so the upper dash
run at crop y ≈ 768 comes from a *third* plate (62 or 69, both of which abut here), not from the
63|70 pair. I did not chase it further; it should be graded as a 62|70 / 62|63 item, not as 63|70.

**Fix.** Neither code flag fixes (a); see §2 for the recipe change, and note the important caveat
there — cutting the box is **not sufficient on its own**.

**Verified-by.** `$S/crop_63_70_legend_{before,after,furn}.jpg` (mosaic 18000,24380–19700,24720).
`before` and `after` are identical. `furn` (the simulated recipe edit of §2) removes the caption's
east half but **leaves the graduated bar and the `50 40 30 20 10 0` numerals** — see §2.

---

### 63|71 — score 2, plate 63's 10" W. PIPE erased; legend clipped — **FIXED**

**Cause.** Mechanism (B) then (A). `63|71` is classed `corner` (span ratio 0.370) despite a
1,145,931 px² overlap, so it never reaches `dp_cut` and gets a straight half-plane at the control
coordinate y = 24502.23. Plate 63 draws its 10" main at y 24532–24552 (measured, §0) — 30–50 px
**south** of that line, i.e. on plate 71's side — and 71 draws nothing there (0.0–0.9 % dark). The
main is therefore simply not rendered over the 165 ft the grader measured, and the same straight
line slices the `Scale of Feet` caption through its baseline.

**Fix (code).** `--min-band-span 2000` reclassifies the pair as a band seam; `dp_cut` then routes
the cut south of both the caption and the main.

**Verified-by.** `$S/crop_63_71_pipe_{before,after}.jpg` (mosaic 18750,24300–21500,24720, 2750×420
at 1:1):

* **before** — `Scale of Feet` clipped through its baseline ("Scaie of Feet" with the descenders
  gone), the scale bar truncated at the 0 mark, the `10" W. PIPE` label sliced, and the dash run
  absent across the middle of the crop.
* **after** — `Scale of Feet.` complete with its full bar and the `50 / 100 / 150` numerals, the
  `10" W. PIPE` label and its `80'` tick whole, and the dash run continuous east of the label.
* **but**: the same change gives plate 63 *more* of the band, so the whole legend now prints where
  before only part of it did. **The clipped-label and erased-main defects are fixed; the
  furniture-in-roadway defect is made larger.** 63|71 must be shipped together with the §2
  furniture resolution, or it trades one level-2 item for another.

---

### 64|72 — score 2 (cut half), 8" water main removed from both plates — **FIXED**

**Cause.** Mechanism (B) then (A), in its purest form. Span ratio 0.355 → `corner` → straight
half-plane at the overlap midpoint y = 24531.28. The two plates draw the same main **25 px (4.3 ft)
apart** — 72's at y 24514–24524, 64's at y 24540–24548 — and the midpoint falls exactly between
them, so 72's copy goes to 64 (blank there) and 64's copy goes to 72 (blank there) and **both
disappear**, leaving the two `8" W. PIPE` labels orphaned. The registration half of this seam is
another agent's; the cut half is entirely this.

**Fix (code).** `--min-band-span 2000`.

**Verified-by.** `$S/crop_64_72_main_{before,after}.jpg` (mosaic 25500,24400–26750,24760):

* **before** — the roadway band is blank; only a stub `P` of one orphaned label survives at the
  crop's top-left.
* **after** — `80' 8" W. PIPE ===` complete and unbroken across the crop, on one plate's alignment.
* nothing else in the crop changed: the `1701 1703 … 1717` numeral run and the block face below are
  pixel-identical.

---

## 2. Plate 63's scale-bar furniture: the numbers, and why 0.98 is not the culprit

`units.json` unit `63`, `furniture_native[1]`: `"cut": false`, `"covered_fraction": 0.83`.
Recomputed with `furncover`'s own rule (`unary_union` of every other unit's
`footprint(v, furniture=False)`, panels of 63 excluded): **0.830**. Coverage under three definitions:

| how the neighbours' ground is measured | covered | by |
|---|---|---|
| raw `extent` / `region_native` only | **1.000** | 71: 0.774, 70: 0.467 |
| minus `exclude_native` — **what furncover does** | **0.830** | 71: 0.526, 70: 0.307 |
| minus `exclude_native` and every `cut:true` box | 0.797 | 71: 0.514, 70: 0.283 |

**The whole 0.170 shortfall is two neighbours' own plate-title rectangles**, and they are declared
*twice* — once as `furniture_native` and once as `exclude_native`, which `footprint_native` subtracts
whatever the `cut` flag says:

```
63 scale bar   mosaic [18816, 24445, 20101, 24645]   (257,000 px2 over 33rd St)
70 title       native [3045,118,3227,248]  -> mosaic [19050, 24294, 19417, 24557]   (96,521 px2)
71 title       native [  89, 97, 249,272]  -> mosaic [19106, 24286, 19430, 24640]  (114,696 px2)
```

Three plates' margins meet at one point in 33rd St and all three print furniture there. The result
is a **cycle**, and it is why the rule produces the wrong outcome without being wrong anywhere:

* 70's title is `cut: true`, `covered_fraction 1.000` — covered by **63 alone** (71 covers 0.000).
* 71's title is `cut: true`, `covered_fraction 1.000` — covered by **63** (70 covers only 0.226).
* 63's legend is `cut: false`, 0.830 — because 70's and 71's `exclude_native` blank exactly the
  ground it needs.

So 70 and 71 are cut *because 63 supplies them*, and 63 is kept *because 70 and 71 do not supply
it*. `furncover` evaluates each box independently, so it cannot see the cycle. And the cycle
currently resolves in favour of the **largest** of the three boxes: 63's 257,000 px² legend prints,
rather than 70's 96,521 px² title — 2.7× more furniture over mapped ground than necessary.

**Proposed rule change (box-level, not a lower `COVER`).** Add a cycle-resolution pass to
`tools/furncover.py` after the independent pass: build the graph "box B of unit u depends on unit v"
for every v contributing to B's coverage; where a set of boxes covers each other's ground and no
plate outside the set maps it, keep exactly **one** — the box with the **smallest mosaic area** —
and cut the rest. Deterministic, evidence-driven, and it does not touch the 0.98 threshold. On this
one cycle it keeps 70's title (96,521 px²) and cuts 63's legend and 71's title.

**The two recipe edits that implement it here**, with simulated `covered_fraction` (computed in
memory, `units.json` never written):

```jsonc
// units.json, unit "70"
"exclude_native": [[[3045,118],[3227,118],[3227,248],[3045,248]]]   ->   []
// ...and in unit "70" furniture_native[0] ("plate number and title")
"cut": true   ->   false        // 70 keeps its own title paper and supplies the ground

// units.json, unit "63", furniture_native[1] ("scale bar")
"cut": false, "covered_fraction": 0.83   ->   "cut": true, "covered_fraction": 0.99
```

| variant (simulated) | 63 scale bar | 70 title | 71 title |
|---|---|---|---|
| current | **0.830** | 1.000 | 1.000 |
| A: drop 70's `exclude_native` | **0.990** ✅ ≥ 0.98 | 1.000 | 1.000 |
| B: drop 71's `exclude_native` | 0.975 ✗ | 1.000 | 1.000 |

Variant A clears the threshold; B does not.

**Caveat, and it is a real one — do not apply A expecting the legend to disappear.** I ran the full
build with variant A patched in memory (`$S/run_furn.py` → `$S/own_furn.json`) and rendered
`$S/crop_63_70_legend_furn.jpg`. **The caption's east half goes; the graduated bar and the
`50 40 30 20 10 0` numerals stay.** Two reasons:

1. `furncover` measures coverage against neighbours' **footprints**, but what decides whether a cut
   box is actually supplied is the neighbours' **regions after streetcut**. The 63|70 cut sits at
   off +120 (region boundary y ≈ 24610–24714), *south* of the box (24445–24645), so 63's own region
   still surrounds the hole.
2. `Recipe.interior_unowned()` then makes the renderer fill that hole from a covering plate's scan
   with `furniture=False` — and the covering plate there is 63, so **the legend is painted back**.

The clean statement for the orchestrator: **cutting a furniture box only removes it where a
neighbour's *region* covers it.** Either the cycle fix must be paired with a cut that puts the box
inside 70's region (not possible here — the north candidate is infeasible, §1), or `furncover` must
measure against `ownership_city.json` regions rather than footprints, which makes it a second pass
after `streetcut`. I recommend the latter as the durable fix and have not implemented it.

**Every kept (`cut: false`) box, for context**: 45 boxes; the ones above 0.80 are
`45[2] 0.944, 77[1] 0.926, 23[2] 0.899, 25[0] 0.865, 65[1] 0.850, 24[0] 0.849, 63[1] 0.830`.
Only `63[1]` and `77[1]` are scale bars in the 0.8–0.95 band, i.e. this is a narrow class, not a
threshold that is broadly too tight.

---

## 3. The furniture-notch pinch (coordinator's item), quantified

`dp_cut` fills its cost mask from `O.exterior` only, so a furniture **hole** is harmless but a
furniture **notch** — a `cut:true` box whose 6 px grow reaches past its plate's own extent, so
`footprint_native`'s `difference` opens the boundary instead of punching a hole — is a wall.

**(a) How many boxes, and how many actually pinch a band.**

* **117** `cut: true` boxes whose 6-px-grown box leaves the unit's own base polygon
  (80 plate titles, 25 edge numerals, 12 scale bars, 1 compass rose). Split by cause:
  **83** where the 6 px grow *alone* pushes a box that was inside the extent past it
  (79 titles, 4 scale bars), **34** already flush with or outside the extent.
  (The reviewer's count of 41 uses a narrower criterion; the phenomenon is the same.)
* **22 of the 172 min-ink seams** have a run of band columns pinched below 100 px that a
  furniture-free band mask reopens. Ranked by the length of the pinched run:

```
 88|96   293 cols = 1,172 px (202 ft)   min slot  40 px -> 464-468 px    <- win_123, the "2117" clip
 50|56   329 cols = 1,316 px (227 ft)   min slot  72 px -> 376-380 px
  4|13   150 cols =   600 px (104 ft)   min slot  44 px -> 284-564 px
 83|84    72 cols =   288 px ( 50 ft)   min slot  72 px -> 308-312 px
 13|14    45 cols =   180 px ( 31 ft)   min slot  32 px -> 184-188 px
 47|53     6 cols                       + 17 more seams pinched over 1-3 columns (4-12 px) at a band end
```

Five seams have a materially pinched run (≥ 180 px); the other 17 are 1–3 columns at the taper of
the band and are cosmetic.

**(b) General fix, implemented: `--band-furniture-free`.** `main()` builds a second set of
footprints with `furniture=False` and hands `dp_cut` the overlap of *those* as its band mask, while
ownership is still differenced against `base`, whose furniture is already removed. So the path may
route across a furniture box, and the box still leaves the mosaic — no per-box `units.json` edit is
needed, and the 117 boxes are covered at once rather than 1 of them.

**Verified on win_123** (`rect [33879,45032,35379,46532]`, `$S/crop_win_123_{before,after}.jpg`,
zoom `$S/win123_zoom_{before,after}.png`):

* **before** — `2117` mutilated: a notch of blank neighbour paper eats the `17`, exactly as
  `proposal_win123.md` describes.
* **after** — `2117` **whole**; the ownership boundary is a clean line above the numeral row;
  `2115` and `2119` unchanged. 23,825 px differ in the 1500×1500 window, all of them in that band.
* the 88|96 cut moves 180–188 px max, median 0 — a local correction, not a re-routing.

This makes the `units.json` unit-96 compass-rose `box[1] 112 → 125` edit proposed in
`proposal_win123.md` **unnecessary**; I recommend the code fix instead, since it also fixes 50|56,
4|13, 83|84, 13|14 and the 17 minor cases without 5+ hand edits.

**On 63|70 / 63|71** the notch mechanism is *not* present: 63's scale bar is `cut: false` (never
subtracted) and its box `[1920,3622,2557,3718]` sits well inside `extent [83,91,3231,3810]`, so it
would be a hole, not a notch. Measured min slot 248 px → 260 px with the flag: no pinch. Their
defect is §2's cycle, not this.

---

## 4. Code changes left uncommitted in `tools/streetcut.py`

`git diff --stat`: `tools/streetcut.py | 283 +++…  1 file changed, 267 insertions(+), 16 deletions(-)`.
Nothing else in the working tree is modified. **All six new behaviours default to off**;
`python3 tools/streetcut.py --year 1912 --out <scratch>` reproduces
`recipe/seams/ownership_streetcut.json` exactly (checked after every edit).

| constant (default) | flag | what it does | blast radius, measured |
|---|---|---|---|
| `LINE_AVOID = 0.0`, `LINE_AVOID_K = 36.0` | `--line-avoid W`, `--line-avoid-k PX` | new **anisotropic** cost field built in `grid()`: each plate's ink measured against its own paper tone (`band_ink`'s per-pixel quantity, so grey scan borders do not read as ink) and dilated **only across the seam** by `LINE_AVOID_K`, summed over both plates, charged in `candidate()`'s DP cost as `LINE_AVOID × avoid`. A path *running along* a drawn line pays at every cell; a path *crossing* one pays only at the crossing. Also reported per candidate as `along_line`. | 97 of 172 seams get local jags at W=1.0 (median movement 0 px, max 476 px), **no candidate flips** |
| `PICK_BEST = False` | `--pick-best` | score every feasible candidate, centre included, on `visible + LINE_AVOID × along_line` | **diagnostic only** — 115 of 171 seams move and it reverts the side choice at 57\|58 and 76\|84. Do not ship. |
| `PANEL_CENTRE = False` | `--panel-centre` | at a parent\|panel seam only, a side candidate must beat the centre on `visible` to be preferred (`sides = [c for c in sides if c[2] <= centre[2]]`) | **3 seams**: 20\|20b (+109.5→0), 25\|25b (+120→0), 48\|48b (−120→0) |
| `PANEL_CLAMP = False` | `--panel-clamp` | fourth candidate at a parent\|panel seam: the centreline with the panel's side forbidden outright, `margin_px=0` (needed a new `margin_px` argument on `candidate()`) | **0 seams** — infeasible at all three panel seams tested; kept because that infeasibility is the *evidence* that 20\|20b cannot be cut clean |
| `BAND_FURNITURE_FREE = False` | `--band-furniture-free` | band mask from `footprint(u, furniture=False)`; ownership unchanged | 40 seams move; reopens the 22 pinched bands; fixes win_123 |
| `MIN_BAND_SPAN = None` | `--min-band-span PX` | `band = span ≥ BAND_FRACTION×across or span ≥ MIN_BAND_SPAN` | at 2000: **0 existing seams move**, 31 straight corner cuts become min-ink paths. Cleanest isolation of the five. |
| `FURN_VISIBLE = 1.0` | `--furniture-visible W` | weight a plate's own furniture-box pixels W× in the `visible` score | **no effect at 63\|70 / 63\|71** (negative result, §1); retained for the orchestrator to try elsewhere |
| — | `--out PATH` | where the non-applied ownership document goes (default unchanged). Added so a dry run never writes into `recipe/seams/` | — |
| — | `--cand-dump PATH` | per-seam candidate table: `off`, `crossed`, `visible`, `along_line`, `feasible`, `chosen`, plus the run's option settings | — |

Internal changes needed to support the above: `grid()` returns an extra `avoid` array;
`candidate()` returns a 4-tuple (`avoid_sum` added) and takes `margin_px`; `dp_cut()` takes
`panel=False`; `main()` builds `feet_nf`/`base_nf` only when `--band-furniture-free` is passed and
computes `panel` from `units.json`'s `panel_of`. Every candidate tuple is now 5 long, including the
blank-band candidate.

**Runtime**: a full run is 43 s baseline, 48 s with all flags.

---

## 5. Recommended orchestrator command sequence

```bash
S=/tmp/scratch                      # anywhere outside outputs/1912/recipe/

# 0. baseline, to diff against (also proves the default-off guarantee)
python3 tools/streetcut.py --year 1912 \
        --out $S/own_base.json --dump-cuts $S/cuts_base.json --cand-dump $S/cand_base.json
cmp $S/own_base.json outputs/1912/recipe/seams/ownership_streetcut.json   # must be identical

# 1. the two changes I recommend shipping, one at a time so each is gradeable
python3 tools/streetcut.py --year 1912 --band-furniture-free \
        --out $S/own_ff.json --dump-cuts $S/cuts_ff.json
python3 tools/cutdiff.py $S/cuts_base.json $S/cuts_ff.json --min-move 30 --out $S/moved_ff.json
#   expect: 40 seams moved; regrade 88|96 (win_123), 50|56, 4|13, 83|84, 13|14

python3 tools/streetcut.py --year 1912 --min-band-span 2000 \
        --out $S/own_span.json --dump-cuts $S/cuts_span.json
python3 tools/cutdiff.py $S/cuts_base.json $S/cuts_span.json --min-move 30 --out $S/moved_span.json
#   expect: 0 shared seams moved, 31 pairs newly cut on a min-ink path (listed as "only_after")
#   regrade all 31, not just 63|71 and 64|72 — this is the biggest single change here

# 2. optional, small and targeted
python3 tools/streetcut.py --year 1912 --panel-centre --out $S/own_panel.json --dump-cuts $S/cuts_panel.json
#   expect: exactly 3 seams (20|20b, 25|25b, 48|48b); does NOT remove either duplicate label

# 3. combined, if 1 and 2 grade clean
python3 tools/streetcut.py --year 1912 --band-furniture-free --min-band-span 2000 \
        --panel-centre --line-avoid 1.0 \
        --out $S/own_new.json --dump-cuts $S/cuts_new.json --cand-dump $S/cand_new.json
python3 tools/cutdiff.py $S/cuts_base.json $S/cuts_new.json --min-move 30 --out $S/moved.json

# 4. crops, from the scratch ownership file (never overwrite the recipe copy):
#    Recipe(1912); r.masks = json.load(open("$S/own_new.json")); r._interior_unowned = None
#    then qcrender.render(r, x0,y0,x1,y1, 1)   -- see $S/crops.py
```

Only after grading: `--apply`, then re-run `tools/fillgaps.py` (the recipe's
`ownership_city.json` is streetcut's output *plus* `gap_fill`; the union shrinks by 196 k px²
(0.004 %) under the combined flags, and the dropped-sliver list changes — new large slivers at
units 6 (369 k px²), 81 (153 k) and a second 94 (291 k) become gaps for `fillgaps` to consider).

---

## 6. Summary of what is fixed, and what is not

| seam | cause | fix | state |
|---|---|---|---|
| 63\|71 | corner misclassification → straight cut on plate 63's 10" main | `--min-band-span 2000` | **fixed** (main and label restored; furniture defect grows — pair with §2) |
| 64\|72 | corner misclassification → midpoint cut *between* two copies of the 8" main, 4.3 ft apart | `--min-band-span 2000` | **fixed** (main restored unbroken) |
| win_123 (88\|96) | `cut:true` box notches the footprint → band pinched to 40 px | `--band-furniture-free` | **fixed** ("2117" whole); supersedes the unit-96 box edit |
| 20\|20b | narrow band → unopposed side candidate; **and** no clean path exists | `--panel-centre` moves it; needs plate 20 `extent[2]` 3271→3218 | **not fixed** by code alone |
| 25\|25b | duplicate is at **25b\|32**, across 25b's panel frame at mosaic 22327 — not the 25\|25b cut | `region_native` east 3266→3170 | **not fixed** by code; recipe edit proposed |
| 54\|54b | side path wanders through the 24th St junction between two copies of one manhole | none of the five flags | **not fixed**; needs a junction term |
| 63\|70 | `covered_fraction 0.830` from a three-plate furniture cycle; north candidate infeasible | §2 cycle rule + a coverage test against regions, not footprints | **not fixed**; cutting the box alone is provably insufficient |
| 14\|49 | four-plate crossing; the clipping edge is the **frozen master's** 12\|49 core mask at (3127, 10628) | out of `streetcut.py`'s reach | **not fixable here** |

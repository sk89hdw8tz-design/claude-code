# Proposal: seam 64|71 (and 63|70) — Avenue N at 33rd St

Reviewer task, nothing applied. No edits under `outputs/1912/recipe`; no `--apply`; no commit.
Source: census round 5 `64_71` (score 3, diagnosis "constant ~33 px westward jog, plate 64
misplaced") and `63_70` (score 3, diagnosis "14.6 px = 5.1 ft translation step").

## Short answer

- **63|70 — one control IS value-wrong: `pair_63_70_x.json`, `b_native`.**
  Corrected `a_native 1178.5 → 1178.0`, `b_native 2186.5 → 2172.3`.
  This is the *only* x tie between the 63/64 row and the 70/71/72 row, and its band
  residual is currently −0.1 ft, so nothing in `bandresid` can see the 5 ft it is out by.
- **64|71 — no control is value-wrong, because the pair carries no control at all**
  (nor does 64|72). The 12–13 ft step is real, constant along the seam, and invisible to
  every gate. **Add `pair_64_71_x.json`** (Ave N), `a_native 178.3` (64) / `b_native 1177.6` (71).
- **Plate 64 is NOT the misplaced sheet**, contrary to both graders. Its one strong tie,
  `pair_58_64_x` (Ave O, both faces drawn on both plates, address runs verified, band
  residual −0.4 ft), holds it. Freeing 64 alone leaves 17.5 ft on the new tie.
  The move that works is `--units 64 71 72 --similarity`.
- Two more controls are built on a **trim line / paper edge misread as a block face**
  (`pair_63_64` a_native, `pair_70_71` both values). `pair_70_71`'s error cancels in the
  difference and needs no change; `pair_63_64`'s does not (~2–5 ft). Recorded below.

## 1. The 64|71 step, measured

The cut runs E–W down 33rd St. The shared corridor is **Avenue N**, which both plates draw
complete (both block faces) at the seam, and both letter **`70'`** inside its own roadway —
plate 64 at native ≈(170, 3535), plate 71 at native ≈(1183, 352). Native scale 3.01 px/ft.

| feature (native px, at the seam) | plate 64 (y 3480–3620) | plate 71 (y 24–164) | implied 64→71 offset |
|---|---|---|---|
| Ave N west block face | 73.0 | 1071.5 | 998.5 |
| Ave N east block face | 283.6 | 1283.6 | 1000.0 |
| corridor centre (midpoint) | **178.3** (width 210.6 = 70 ft) | **1177.6** (width 212.1 = 70 ft) | **999.3** |
| water main on the centreline (`6" W. PIPE` / `8" W. PIPE`) | 179.9 | 1182.2 | 1002.3 |
| **T.H. hydrant (width-free tie)** | (257.2, 3554.4) | (1256.2, 98.0) | **999.1** |

Repeated one street south (64 y 3730–3870 / 71 y 274–414): faces 77.0/284.6 vs 1075.0/1285.0,
pipe 180.8 vs 1184.0 — offsets 998.0 / 1000.4 / 1003.2. Normalised cross-correlation of the
whole overlap band at four positions along the seam (64 x = 200, 700, 1200, 1700) gives
dx = 1000, 988, 990, 999 — **constant, i.e. a translation, not a rotation or scale**.

The current placement asserts 64→71 = 1036.6 px (at 64 x=200) to 1041.8 (at x=3160).
Error **37–42 native px = 12.4–13.0 ft**, plate 64's copy EAST of plate 71's, so every N–S
feature jogs west crossing into 71 — exactly the grader's 33 px.

In mosaic coordinates at the seam: Ave N centre X = 21372.9 from plate 64, 21297.5 from
plate 71 → **+13.01 ft**. Cross-seam dy is +0.7 to +0.9 ft throughout; y is fine.

**Not a source disagreement.** Both plates draw Ave N 210.4 px wide and both print `70'` in it.

**Identity (why not one avenue off — a block here is ~1000 px, the error is 37 px).**
33rd St's 1500 block begins east of this corridor on both sheets: plate 64 carries
`1502 1504 1506 1508 1510 1512` on the north side, plate 71 `1501 1503 1505 1507 1509` on the
south side. The avenue frontage changes hundred exactly at 33rd St: plate 64's east face
reads `3223 3225 3227` (3200 block, north), plate 71's reads `3301 3303 3305` with the even
run `3304 3306 3308 3310 3312` on the west face (3300 block, south). The same `T.H.` hydrant
and the same water main (6" north of 33rd, 8" south) sit at the corner on both. One avenue
west on 64 is off-sheet; one east is Ave N 1/2 (centre ≈1091) with the 1500/1600 change.

## 2. The one control that *is* value-wrong: `pair_63_70_x.json`

`observer: "lattice (tools/faces.py)"`, `corridor: "?"`, `a_native 1178.5` (63) /
`b_native 2186.5` (70) → asserted offset **1008.0**. The corridor is **Avenue M** (plate 63's
third x chain, plate 70's third; `pair_57_63_x` independently fixes 63's Ave M at 1189* and
`pair_70_71` reads 70's chain as K 175 / L 1176 / M 2181.5).

Measured on the drawn faces, both plates, both 70 ft wide:

| | plate 63 | plate 70 | offset |
|---|---|---|---|
| at the shared band (63 y 3450–3590 / 70 y 20–160) | 1074.0 / 1282.0 → **1178.0** | 2067.5 / 2277.0 → **2172.3** | **994.3** |
| at mid-sheet (y 1849) | 1075.6 / 1285.4 → 1180.5 | 2075.6 / 2286.2 → 2180.9 | 1000.4 |

`a_native` is right (1178.5 vs 1178.0 measured at the band). **`b_native` is ~14 native px
= 4.7 ft east of where plate 70 actually draws Ave M**; `lattice.json`'s faces for that
chain, `[2083, 2290]`, are not where the lines are. Corroboration on plate 70's own grid:
Ave L 1068.4/1276.0 and Ave M 2067.5/2277.0 give a pitch of 996 px, matching plate 63's.

Verification: with `a 1178.0 / b 2172.3` in a scratch copy of the recipe,
`bandresid --min-ft 0` reports `pair_63_70_x  +4.6 / +4.7 ft` — the same, constant, and
in the same direction as the step the grader measured (14.6 px = 5.1 ft). With the shipped
values it reports `−0.1 / −0.1`, which is why the gate never saw it.

**Change:** `outputs/1912/recipe/controls/pair_63_70_x.json`
`a_native 1178.5 → 1178.0`, `b_native 2186.5 → 2172.3`; record the previous values and this
reason; `corridor "?" → "Ave M"`; keep `cross_axis: true`, `status: ACCEPTED`.
*Identity unchanged and unambiguous:* both plates draw four x corridors on a ~1000 px pitch
(63: L 178 / M 1178 / M 1/2 2182 / N 3177; 70: K 176 / L 1172 / M 2172 / M 1/2 ~3176); the
correction is 14 px against a 1000 px block.

## 3. The control that is missing: `pair_64_71_x.json` (add)

```json
{"pair": [64, 71], "axis": "avenue", "observer": "wave4-64-71",
 "method": "corridor centre = midpoint of the two block faces, both drawn on both plates, read in the shared 33rd St band",
 "corridor": "Ave N", "a_native": 178.3, "b_native": 1177.6,
 "faces": {"64": [73.0, 283.6], "71": [1071.5, 1283.6]},
 "roadway_px": [210.6, 212.1], "disagreement_before_ft": 13.0, "status": "ACCEPTED"}
```

`bandresid` with this file present reports `pair_64_71_x  +13.0 / +13.0 ft` — it reproduces
the measured step exactly and confirms it is constant along the seam. The same corridor also
ties 64 to 72 (`64_72`, graded 3, same 36 px = 12 ft westward step, same cause); a
`pair_64_72_x` on Ave O 1/2 would close that loop but 72 draws only one of its faces, so
Ave N via 71 is the sounder tie and 72 follows from `pair_71_72`.

**Convention caveat, please read before applying.** `bandresid` and `localsolve --similarity`
read a control's `a_native` as the line's native x *in the shared band*; `localsolve` in
translation mode reads it at the plate's `extent` mid-y. For this pair the two differ by
~18 native px, because plates 64 and 71 draw their N–S lines with different tilts
(64 ≈ −0.000 px/px, 71 ≈ +0.005) and the transforms' rotations (0.381° vs 0.328°) do not
carry that difference. The band reading above is the one that reproduces the seam. The
mid-height reading of the same corridor is `a 171.0` (faces 65.8/276.2) / `b 1188.7`
(faces 1083.5/1293.9), if the orchestrator prefers the mid-height convention.

## 4. Expected move (dry runs, `--apply` never passed)

Shipped tree, `python3 tools/localsolve.py --year 1912 --units 64` / `63`:

```
4 controls touch ['64']; residuals after (ft): median 2.7, max 5.4
   pair_58_64_x  x +5.4 | pair_63_64  x -3.4 | pair_64_65  x +2.0 | pair_58_64  y +0.0
unit 64: t [21061.2, 17141.7] -> [21078.1, 17142.5]  move (+3, +0) ft

7 controls touch ['63']; residuals after (ft): median 3.2, max 6.0
   pair_63_70_x x +6.0 | pair_57_63_x x +5.7 | pair_63_71 y -3.9 | pair_63_70 y +3.2
   pair_63_64 x -1.0 | pair_57_63 y -0.8 | pair_62_63 x -0.7
unit 63: t [14985.4, 17127.5] -> [14982.5, 17130.9]  move (-1, +1) ft
```

`--units 64 --similarity` and `--units 63 --similarity` on the shipped tree both come back
clean (median 0.5 / 0.6 ft, max 1.4 ft, centres move 0 ft): **the mosaic satisfies its
controls; the controls assert the wrong values.**

`bandresid --year 1912 --min-ft 0 | grep -E '6[34]_|_7[01]'` (shipped): worst in this
neighbourhood are `pair_71_79 −5.0/−3.7`, `pair_71_72 +4.4/+3.7`, `pair_71_72_y +3.4`,
`pair_70_71 +3.3/+3.2`; `pair_63_70_x −0.1/−0.1`; nothing for 64|71 or 64|72.

Simulated in a scratch copy of the recipe with §2 corrected and §3 added:

| free set | result |
|---|---|
| `--units 64` | 64 moves −3 ft; `pair_64_71_x` still +17.5, `pair_58_64_x` +11.2 — **64 alone cannot be moved** |
| `--units 71 72` | 71 +4 ft east, 72 +2 ft; `pair_64_71_x` still +16.2 |
| `--units 64 71 72 --similarity` | **best**: median 1.3 ft, max 6.0; `pair_64_71_x` 13.0 → **+4.6/+4.5 ft**; 64 −2 ft west (scale +0.28%, rot 0.381°→0.528°), 71 +2 ft east (scale −0.15%, rot 0.328°→0.418°), 72 +0 ft |
| `--units 70 71 72 --similarity` | median 1.2 ft, but `pair_64_71_x` only 13.0 → 6.4 |

Recommended: `python3 tools/localsolve.py --year 1912 --units 64 71 72 --similarity --apply`
(Gate A orchestrator only), after both control edits. Expect the 64|71 and 64|72 steps to
fall from ~12.5 ft to ~4.5 ft and the 63|70 step from 5.1 ft to ~1 ft.

## 5. What the remaining ~4.5 ft is, and why I am not proposing to chase it

Two things, both documented rather than fixed:

**(a) A real scale/tilt difference between the rows.** Measured on the drawn corridors at the
seam, the upper row sits east of the lower row by a *growing* amount:

| corridor at the 33rd St seam | mosaic X | step (upper east of lower) |
|---|---|---|
| Ave L (63 v 70) | 15307 | +3.84 ft |
| Ave M (63 v 70) | 17323 | +4.60 ft |
| Ave M 1/2 (63 v 71) | 19334 | +7.90 ft |
| Ave N (64 v 71) | 21373 | +13.01 ft |

Plate 63's drawn N–S lines tilt −0.0018 px/px and plate 70's +0.0044 (0.36° apart) while
their transforms differ by 0.05°. A translation-only tie cannot absorb that, which is why
`--similarity` is the right mode and why ~1 ft of the 63|70 step and ~4.5 ft of the 64|71
step survive the fix. Net tension / drawing difference — no further control change.

**(b) Two controls built on a trim line or the paper edge.** Both are the 91|92 failure mode
(a half-width laid off a face that is not a face). Recorded here; only the first is worth a
re-read, and neither is the cause of 64|71:

- **`pair_70_71.json`** — `a_native 3127` is the midpoint of "faces 3075 and 3178" on plate 70,
  from which the note infers a 35 ft avenue and then lays 52 px off plate 71's single line at
  185 to get `b_native 133`. Plate 70's line at 3178 is **not a block face**: it runs the full
  sheet height with blank paper east of it to the sheet edge and no address run beyond it
  (crops of u70 x 3020–3327 at y 900–1700 and y 2400–3200); it barely follows the plate's drawn
  tilt (3176.1 at y1500 → 3178.0 at y2700, against +5 px expected); and it sits within 2 px of
  west face 3070 + 105.5, i.e. on the **avenue centreline, where Sanborn sheets are trimmed**.
  Plate 63 draws the same Avenue M 1/2 two blocks north with both faces at 2070 / 2288 =
  218 px = **70 ft**, not 35. **But** because the same wrong half-width was laid off on both
  sides, the error cancels: asserted offset −2994 against −2990 measured (70's trim line 3175.5
  ↔ 71's line 186; NCC of the overlap band agrees, −2990 at mid-sheet). Seam 70|71 grades 5.
  **No change — record the method fault only.** Do not "fix" one side alone; that would
  introduce ~50 px.
- **`pair_63_64.json`** — `a_native 3183` is the midpoint of "sheet 63 faces x=3075 and x=3290".
  Plate 63 does not draw Ave N's east face; the sheet is trimmed on the avenue and the paper /
  mount edge wanders between native 3150 and 3300 with y (fully-dark columns at 3182 @ y500–900,
  3300 @ y1850–2050, 3193 @ y2900–3300). **3290 is that edge.** Plate 63 *does* print `70'` in
  the Ave N roadway (native ≈(3160, 3490)) and draws the 6" main and the same corner T.H.
  hydrant at (3217.5, 3518.0), so the honest construction is west face + 105.5:
  3070 + 105.5 = **3176.5** at mid-sheet (3050–3068 + 105.5 ≈ 3156–3174 at the seam, where
  plate 63's east edge is degraded). Suggested re-read `a_native 3183.0 → 3176.5`, recording
  the previous value and that the "east face" was the trimmed paper edge. Worth ~2 ft; I have
  **medium** confidence in the number and **high** confidence that 3290 is not a face.
  This one is *not* independent of §3 — if `pair_64_71_x` is added, let the solver arbitrate;
  do not apply both hand-tuned in the same pass without re-running `bandresid`.

## Verdict lines

- `63_70` — **registration, value-wrong control**: `pair_63_70_x.b_native` 2186.5 → 2172.3
  (a 1178.5 → 1178.0). Confidence **high** (both plates draw both faces of Ave M, both 70 ft,
  measured at the shared band, reproduces the graded step to 0.5 ft).
- `64_71` — **registration, no control exists**: add `pair_64_71_x` (Ave N, 178.3 / 1177.6).
  Confidence **high** on the 13.0 ft and on the identity (three independent measures including
  a width-free hydrant tie; constant along the seam by NCC and by bandresid's two band ends).
  Confidence **medium** on which sheet moves: the least-squares answer is 64 west ~2 ft *and*
  71 east ~2 ft under `--similarity`, not "plate 64 is the misplaced sheet".
- `64_72` — same corridor family, same cause; expect it to follow without its own control.
- `70_71` — **no change**; method fault recorded, error cancels.
- `63_64` — optional re-read of `a_native` (3183.0 → 3176.5), evidence-backed but small.

# Wave 4 registration evidence: seams 20b_25 and 17_21

Opus evidence agent, session 018fqghgw6. Dry runs only. Nothing applied; no recipe file
edited (`git status outputs/1912/recipe/` clean). Scratch simulation in
`/tmp/.../scratchpad/sim` (controls copy + in-memory transform overrides; `Recipe.dir`
repointed after construction, transforms read from the real recipe).

Scale used throughout: mosaic 5.7966 px/ft; native px/ft = 5.7966 / unit scale in
`transforms_city.json` — 20/20b 2.8839, 24 2.9171, 25 2.9014, 17 2.9202, 21 2.8961.
Seam crops are mosaic/2, so 1 crop px = 0.345 ft.

---

## CLAIM 1 — seam 20b_25 (regraded 2): "the 20b inset sits ~12–13 ft west of plate 25"

### Defect
Real, and larger than the round-5 20_20b note ("inset registration good to ~5 ft"):
the 1200-block features step **12.6–13.5 ft, plate 25 east of the 20b inset**, uniformly
along the whole 1768 px seam. Uniform ⇒ translation, not rotation or scale.

### Which controls tie 20b
**None.** `grep 20b outputs/1912/recipe/controls/` returns nothing; 20b appears only in
`units.json`, `inventory.json`, `render_manifest.json`, `working_sources.json`,
`master_full_manifest.json`, `seams/ownership_*.json`. 20b has no transform of its own:
`reciplib.Recipe.sheet_matrix` derives it as `M20 @ (p_native + shift_native) + t20` with
`shift_native = [966, 2305]`. So 20b's placement = plate 20's placement, and plate 20 is
tied by `pair_19_20` (y), `pair_20_24` (y, 9th St), `pair_20_24_x` (x, Ave K),
`pair_20_25_x` (x, Ave L). Per `seams/index.json` 20b borders only **20** (x seam at
15306.8) and **25** (y seam at −31048.6); it does not border 24 — 24 is reached through
plate 20.

### Measured steps (native → mosaic, evaluated at the seam y = −31048.59)
Line positions are sub-pixel centroids of column-ink profiles over 3–4 latitude bands per
plate (inset u20 y 940–1220; plate 25 y 340–740), each fitted as a mosaic line and
extrapolated to the seam row.

| feature (printed identity) | 20b native | 25 native | 20b mosaic x | 25 mosaic x | step (25 − 20b) |
|---|---|---|---|---|---|
| Ave L east block face (block 1202 W face / block 1201-901 W face) | 2433.0 | 219.8–221.8 | 15669.6 | 15745.3 | **+13.07 ft** |
| 20 ft alley west face (lots 1212 \| 1214 above, 1211 \| 1213 below) | 2799.0–2799.8 | 587.2–590.4 | 16408.0 | 16480.8 | **+12.55 ft** |
| 20 ft alley east face (same alley) | 2858.6–2859.6 | 647.9–650.9 | 16523.8 | 16601.8 | **+13.45 ft** |

No gradient along the 855 px of seam covered (13.07 / 12.55 / 13.45) — mean **13.0 ± 0.5 ft**,
a pure x translation. The 6" W. PIPE dashes lie between the two alley faces on both plates
(20b native 2825–2829, 25 native ~621) and step with them; the T.H. hydrant dot is on the
inset side only, which is a drawing difference, not a step.

### Identity
Both plates letter the same ground and the address runs interlock: the inset carries
`1202 1204 1206 1208 1210 1212` then the alley then `1214 1216 1218 1220 1222` on the north
side of `9TH ST.`, plate 25 carries `1201 1203 1205 1207 1209 1211` then the alley then
`1213 1215 1217` on the south side — the same 1200 block (Ave L → Ave M), odd against even.
Ave L's frontage `821 823 825 827` (inset) faces `901 903 905 907 909` (plate 25) across
9th St. Both print `20'` beside the alley and `80'` in the 9th St roadway. A one-block error
is excluded: the next alley east is ~1000 native px away and the 1300 block starts across
Ave M.

### Not a drawing difference
The two sheets draw this block identically:

* Ave L east face → alley west face: **127.40 ft** on the inset vs **126.88 ft** on plate 25 (0.5 ft apart).
* Alley width: **19.97 ft** (inset) vs **20.87 ft** (25), printed 20' on both.

So the whole 13 ft is placement.

### Width proof that 20b itself must NOT move
The inset's only registrable line against plate 20 is the Ave L corridor. With the current
`shift_native = [966, 2305]`, the inset's Ave L **east** block face (native 2433.0 → 3399.0
in plate-20 coordinates) sits **213.8 native px = 74.1 ft** east of plate 20's own Ave L
**west** block face (native 3185.0–3186.3 by ink profile at y 2750/3000/3500). That is one
printed-70' Galveston avenue at this sheet's drafted scale: Ave K on plate 20 measures
211.0 px = 73.2 ft (faces 2185.1/2396.1), Ave M on plate 25 measures 213.3 px = 73.5 ft
(1013.2/1226.5), plate 57 draws Avenue L complete at 216.5 px. Moving 20b 13 ft east to
close the 20b_25 seam would open Ave L between plate 20 and its own inset to
213.8 + 37.6 = 251.4 px = **87.2 ft** — impossible for a 70' avenue, and it would break the
20_20b seam by the same 13 ft. **`shift_native` is right to ~2–3 native px (≤1 ft).**

### Independent (width-free) tie
The step is exactly the plate-20 ↔ plate-25 x disagreement that the recipe already carries.
`python3 tools/localsolve.py --year 1912 --units 20` (dry) prints
`pair_20_24_x x +6.3 ft` and `pair_20_25_x x −6.3 ft` — equal and opposite, 12.6 ft apart,
with plate 20 already at its optimum (x move 0). Measured directly: plate 20's Ave L west
face and plate 25's Ave L east face are **87.26 ft** apart at the seam latitude (should be
~73.5); plate 24's Ave L west face and plate 25's east face are **87.25 ft** apart at
mid-band. `bandresid` cannot see `pair_20_25_x` at all — plate 20 and plate 25 abut with
zero overlap ("no overlap" row), which is itself the symptom: the two are placed so their
neatlines touch instead of sharing the 14 ft of Ave L roadway both draw.

### Verdict
**NET-TENSION at 20b — VALUE-WRONG one control upstream.**
20b is correctly registered to plate 20 and no control ties it, so nothing about 20b or its
`shift_native` is wrong. The 13 ft step is the Ave L column break between the 20/24/30 row
and the 25/31 row, and it traces to a single control value:

`controls/pair_24_25.json` (axis avenue, corridor Ave L) was revised by **review B** from
`a_native 3205.0 / b_native 114.0` to `3223.0 / 96.0` with the reason *"both plates print
80' in the gutter"*. That 80' is the **numbered-street** width, not Ave L's. On plate 24 the
`80'` glyphs sit beside the horizontal 10th St and 11th St roadway lines (native x ~3070,
y ~1358 and ~2522 — read on the scan), while `AVENUE L` is lettered separately at
y ~1900. Plate 25 and the 20b inset both print `70'` inside the Ave L roadway
(25 native ~158; inset native ~2330), and `pair_20_25_x`'s identity note records the same
70' on sheets 20 and 25. Both plates' own face chains give `roadway_px [206, 206]`
(= 70.6 / 71.0 ft); plate 24's own lattice pitch Ave K→Ave L is 1003 px with an 800 px block,
leaving 203 px = 69.6 ft for Ave L. Review B's 121 px half-width makes Ave L 83 ft.

This is the *same* error the P2-2 Gate-A review already caught and corrected in the sibling
control `pair_30_31.json` ("Review B took the gutter as 80 ft (half-widths 123/120 px), but
the printed 80' in these crops lies in the NUMBERED-STREET corridor … Avenue L measures
213 px … Half-width 106.8 px"). `pair_24_25.json` was missed by that pass.

### Change
**No change to 20b.** Do not touch `units.json` `20b.shift_native`, and do not add a
20b↔25 control: 20b has no independent degrees of freedom.

One control edit, on the plate pair that actually carries the error:

* `outputs/1912/recipe/controls/pair_24_25.json`
  * `a_native` **3223.0 → 3207.7** (`a_native_previous` already records 3205.0, pre-review-B)
  * `b_native` **96.0 → 112.3** (`b_native_previous` already records 114.0)
  * construction, using the P2-2 half-width 106.8 px that `pair_30_31`, `pair_56_57` and
    `pair_25_31_x` already use for Avenue L:
    * plate 24 Ave L **west** block face = 3100.9 (ink profile x 3070–3135, 11 latitude
      bands y 345–3345, fit `x = 0.005096·y + 3091.01`, evaluated at 24's extent y-centre
      1941; review B's own read was 3102) → 3100.9 + 106.8 = **3207.7**
    * plate 25 Ave L **east** block face = 219.1 (ink profile x 195–255, 11 bands
      y 445–3445, fit `x = −0.001605·y + 222.24`, at 25's extent y-centre 1933; lattice 217,
      `pair_20_25_x` 218.4) → 219.1 − 106.8 = **112.3**
  * record the previous values and this reason; corridor identity unchanged (review B's
    1123 \| 1201 frontage match still stands — only the half-width changes).

**No `localsolve … --apply` in wave 4.** See the gate below: the correction is right but
cannot be absorbed by any local move. Hand the Ave L column break to the net solve.

### Dry-run residuals and gate
Baseline (`tools/bandresid.py --year 1912`): 332 accepted controls, 318 with overlap,
median max-abs **1.59 ft**, **11** over 6 ft.

With `pair_24_25` corrected to 3207.7 / 112.3 and no transform change, that control's own
band residual is **−11.7 / −13.0 ft** — i.e. the recipe currently honours the wrong value,
which is the whole 13 ft.

Dry runs (scratch controls dir, real transforms):

| freed units | localsolve residuals | moves | bandresid after (median / >6 ft) | gate |
|---|---|---|---|---|
| `--units 25` | median 4.5, max 5.3 (`pair_20_25_x` +0.5) | 25 → (−7, +1) ft | 1.58 / **12** | **FAIL** — `pair_25_31_x` newly −9.3 / −9.2 |
| `--units 24 25` | median 3.8, max 7.6 | 24 (+2,−0), 25 (−7,+1) | 1.58 / **12** | **FAIL** — `pair_25_31_x` newly −8.8 / −8.6 |
| `--units 25 31` | median 2.9, max 9.5 | 25 (−9,+0), 31 (−5,−0) | 1.60 / 11 | **FAIL** — `pair_25_31_x` newly −6.3 / −6.2 |
| `--units 25 31 32` | median ~3, max ~8 | 25 (−10,−2), 31 (−8,−2), 32 (−9,−7) | 1.58 / **14** | **FAIL** — `pair_32_38`, `pair_31_37_x`, `pair_25_32_y` newly > 6 |
| `--units 20 24 30` | median 4.0, max 7.5 | 20 (+3,−4), 24 (+5,−1), 30 (+3,+2) | 1.60 / 10 | passes the count, but absorbs only ~4 ft of the 12.6 and leaves `pair_24_25` at −7.3 ft |

Every local scope pushes the break one column further east (Ave M, 25\|31) rather than
closing it. Conclusion: correct the control value now (it is a documented misreading, and it
makes the recipe self-consistent with the ruling already applied to `pair_30_31`), and leave
the transforms to a column-scale net solve over {20, 24, 30 | 25, 31, 32, 37, 38}. Until
then seam 20b_25 keeps its ~13 ft step and its score of 2, correctly attributed to plate 25's
x, not to the inset.

---

## CLAIM 2 — seam 17_21 (regraded 3): "~1% differential along-seam scale/rotation"

### Defect
Confirmed, and it is a **scale** difference, not rotation: the lateral step of every
vertical line crossing 9th St grows monotonically from **−6.0 ft at the west end to +4.7 ft
at the east end**, crossing zero at Strand. A rotation difference would put the gradient in
the cross-seam direction; a gradient of x-step with x is differential scale along the seam.

### Measured steps (current transforms, seam y = −31164.66)
Column-ink profiles on `u17.jpg` (4 bands, y 2900–3560, i.e. the block row above 9th St) and
`u21.jpg` (4 bands, y 400–1100, the block row below), each line fitted in mosaic space and
extrapolated to the seam row. Step = plate 21 − plate 17 (positive = 21 east of 17).

| feature | 17 native | 21 native | mosaic x | step |
|---|---|---|---|---|
| west margin line (wharf front) | 230.6 | 240.9 | −8633 | **−5.97 ft** |
| blocks 728/729 20 ft alley, W face | 594.4 | 609.5 | −7914 | −3.21 |
| blocks 728/729 20 ft alley, E face | 653.5 | 669.0 | −7801 | −2.39 |
| block face at 17 x1022 | 1021.8 | 1034.9 | −7065 | −2.81 |
| **AVE. A OR WATER, east casing** | 1232.3 | 1246.9 | −6649 | **−1.39** |
| AVE. B OR STRAND, west casing | 2027.5 | 2039.6 | −5071 | −0.35 |
| AVE. B OR STRAND, east casing | 2267.0 | 2281.5 | −4599 | +1.57 |
| block 668/669 west face | 2634.0 | 2647.5 | −3868 | +2.03 |
| **blocks 608/609 20 ft alley (8" W. PIPE), E face** | 2694.7 | 2706.9 | −3749 | **+2.33** |
| AVE. C OR MECHANIC, west casing | 3057.1 | 3075.0 | −3029 | **+4.65** |

Linear fit: `step_ft = 0.001546·x_mosaic + 8.47` → **10.6 ft of differential over the seam's
6271 px (1082 ft) span = 0.98%**. The regrade's two named locations reproduce: Ave A lines
−1.4 to −2.8 ft (regrade: ~2.6 ft west), the 608/609 alley +2.0 to +2.3 ft (regrade:
3.3–4.5 ft east — their read is off the crop at 3.06 px/ft, mine through the transforms).
The dashed 8" pipe itself has no clean profile peak; its two alley casings bracket it and
step together, so 2.0–2.3 ft is the pipe's step.

### Identity
Settled by the existing accepted controls and re-checked on the scans: both plates letter
`9TH ST.` across the seam and print each other's numeral in the margin (17 prints "21",
21 prints "17"); the north/even faces 102–124 (17, block 668, Ward School No 2) face the
south/odd faces 101–123 (21, Lecture Hall block); `AVE. A OR WATER`, `AVE. B OR STRAND` and
`AVE. C OR MECHANIC` are each lettered in their own roadway on both plates, and the 100\|200
break falls on Strand on both. The ten features above are the same ten lines in the same
left-to-right order with the same printed widths (Strand 240 native px = 80' on both).

### Not a drafting-scale difference — but not a placement error either
Plate-internal spans, measured on the scans, agree to a few tenths of a percent:

| span | 17 native px | 21 native px | 21/17 |
|---|---|---|---|
| west margin → Mechanic W casing | 2826.49 | 2834.13 | +0.27% |
| Ave A E casing → Mechanic W casing | 1824.79 | 1828.11 | +0.18% |
| 728/729 alley W → Mechanic W casing | 2462.68 | 2465.51 | +0.12% |
| Strand W → Mechanic W casing | 1029.60 | 1035.40 | +0.56% |

So the two sheets draw this ground within ~0.3% of each other, and the required transform
ratio is `M21/M17 = k17/k21 = 0.9973`. The recipe has `M21/M17 = 2.001541/1.984968 =
1.008349`. The mismatch is **1.11%** — it is in the transforms, not in the paper. Direction:
plate 21's transform scale is ~1.1% too large relative to plate 17's.

But no control on this seam is violated. `bandresid` baseline:
`pair_17_21` **+0.3 / +2.4 ft**, `pair_17_21_x` **+0.1 / −0.0 ft**, `pair_21_22` −0.6/−0.6,
`pair_21_27` −0.1/−0.4, `pair_21_27_x` +0.6/+0.6. Plate 21's scale is consistent with its
22/27 neighbours and plate 17's with its 18/22 neighbours; the 1% is a scale-family
difference between the two plate rows that no accepted tie constrains.

### Simulation of the proposal_17_18 re-solve
Scratch copy of `controls/pair_17_18_y.json` set to `status ACCEPTED, a_native 2685.4,
b_native 2685.6` (the settled 8th St south-face pair), then
`python3 tools/localsolve.py --year 1912 --units 17 18 --similarity` (dry) — reproduces
proposal_17_18 exactly: 18 line samples, residual median 1.5 / max 3.4 ft;
**17 scale 1.9850 → 1.9894 (+0.22%), rotation +0.425° → +0.329°**; 18 scale −0.04%,
rotation +0.507° → +0.332°.

Recomputing the ten steps with 17's solved matrix, the 17\|21 steps **shrink**:

| location | before | after 17_18 |
|---|---|---|
| west margin line | −5.97 | **−4.38** |
| AVE. A OR WATER | −1.39 | **−0.53** |
| 608/609 alley (8" pipe) | +2.33 | **+2.10** |
| AVE. C MECHANIC | +4.65 | **+4.15** |
| gradient over the seam | 10.6 ft (0.98%) | **7.3 ft (0.68%)** |

Worst single step falls from 6.0 ft to 4.4 ft, and `pair_17_21`'s band residual improves to
−1.6 / −0.8 ft (`pair_17_21_x` −0.1 / −0.1). Independent confirmation of that proposal: the
scan-width ratio above says 17's own correct scale is 5.7966/k17 ≈ **1.9890**, i.e. +0.20%
from its current 1.9850 — the same figure the 17\|18 controls produce.

### Separate action on 21 — dry run, and why not
`python3 tools/localsolve.py --year 1912 --units 21 --similarity` (dry): 14 line samples,
residual median 1.9 / max 6.9 ft; **21 scale 2.0015 → 1.9955 (−0.30%)**, rotation
+0.269° → +0.262°, centre moves (+3, −0) ft. Only −0.30% of the −0.9% the ratio needs, and
the solve buys it by trading the seam's balance for a bias:

| location | current | 21 similarity only | 17_18 + 21 similarity |
|---|---|---|---|
| west margin line | −5.97 | −2.05 | −0.45 |
| AVE. A OR WATER | −1.39 | +1.49 | +2.35 |
| 608/609 alley (8" pipe) | +2.33 | +3.71 | +3.48 |
| AVE. C MECHANIC | +4.65 | **+5.64** | +5.14 |
| gradient over seam | 10.6 ft | 6.4 ft | 4.1 ft |
| worst \|step\| | 5.97 | **5.64** | 5.14 |

The gradient shrinks but the *worst* step barely moves (6.0 → 5.6 ft) because the solve adds
a uniform ~+3 ft eastward offset: it converts a balanced ±5 ft seam into a 0…+5.6 ft one.
Cost: `pair_17_21_x` goes from +0.1/−0.0 to −1.8/−2.0 ft, `pair_21_27_x` from +0.6 to +2.7,
`pair_21_27` from −0.1/−0.4 to −2.0/−2.4. It does buy `pair_6_21` +10.9/+7.1 → +6.9/+3.0.
Gate: median 1.59 → **1.62 ft**, over-6-ft count **11 → 11**, nothing newly over 6 ft — so it
would pass, but it does not fix what the grader sees, it moves it, and it degrades three
satisfied controls to pay for it. Under the wave-4 bar ("change only when the plates prove a
placement wrong") the plates do not prove plate 21's *placement* wrong: they prove a ~1%
scale-family difference between two rows that a single-unit similarity cannot carry.

### Verdict
**NET-TENSION.** Leave plate 21 alone and record the residual.

### Change
**No change on 21 — reason:** all five controls touching 21 are satisfied (max band residual
2.4 ft before, and `pair_17_21` / `pair_17_21_x` at +0.3/+2.4 and +0.1/−0.0); the defect is a
1.11% transform-scale ratio between the 17/18 row and the 21/22/27 row, of which
`--units 21 --similarity` recovers 0.30% while adding a +3 ft uniform bias and degrading
three satisfied controls. No control edit, no new control.

The one action already proposed elsewhere is sufficient and should be applied for its own
reasons:

* `outputs/1912/recipe/controls/pair_17_18_y.json`: `status ACCEPTED`, corridor
  "8th St — SOUTH block face", `a_native 2685.4`, `b_native 2685.6` (per
  `proposal_17_18.md`)
* `python3 tools/localsolve.py --year 1912 --units 17 18 --similarity --apply`

as a side effect it takes seam 17_21 from a 10.6 ft gradient / 6.0 ft worst step to a 7.3 ft
gradient / 4.4 ft worst step, i.e. into "a visible offset up to ~6 ft" comfortably and within
the 3–4 ft band the brief says to absorb and record.

### Dry-run residuals and gate
* `--units 17 18 --similarity` (with the scratch `pair_17_18_y`): 18 line samples,
  median 1.5 / max 3.4 ft. bandresid after: 319 controls with overlap, median max-abs
  **1.62 ft** (from 1.59), **11** over 6 ft (from 11) — none newly over 6 ft.
  `pair_17_21` −1.6/−0.8, `pair_17_21_x` −0.1/−0.1.
* `--units 21 --similarity`: median 1.9 / max 6.9 ft (`pair_6_21`); bandresid median
  **1.62**, 11 over 6 ft, none newly over 6 ft — passes the gate but is **not recommended**
  for the reasons above.
* `--units 21` (translation): median 1.4 / max 7.0 ft, `pair_17_21_x` newly +7.0 and
  `pair_21_27_x` +6.8 for a 2 ft move — clearly worse, rejected.

---

## Residual seams to re-check after any of this
20_20b (unchanged by this proposal — the doubled `AVENUE L.` and the Ave L/9th St wedge are
cut and source-gap items, not registration), 20_23, 24_25, 30_31, 25_31, 17_18, 17_22,
18_19, 18_22, 21_22, 21_27, 6_21.

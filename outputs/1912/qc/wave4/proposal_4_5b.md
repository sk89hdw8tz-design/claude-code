# Proposal: seam 4|5b (and 3|4) — panel 5B has no cross-frontage control at all

Source: Gate C adjudication of seam `4_5b` (`outputs/1912/qc/gatec/seams_1.json`, score 2) and of
seam `3_4` (`outputs/1912/qc/gatec/seams_0.json`, score 2), after HQ-47 moved wharf sheets 4 and 3
~348 ft east. Opus evidence agent; **nothing applied** — every solve below was run in
`/tmp/.../scratchpad/s45|s46|s47`, a copy of the recipe with `tools/` and `work/` symlinked;
`outputs/1912/recipe/` was not written to.

---

## Part A — seam 4|5b

### Defect

Across the true 4|5b cut (near-horizontal junction at crop y≈1018–1026 for x 0–800 of
`seam_4_5b_100.jpg`; plate 5b above, plate 4 below; 1 crop px = 2 mosaic px = 0.1725 ft) every line
jogs by ~48 crop px as a rigid translation, and the slip's italic **"Slip"** annotation is kept
twice — plate 5b's copy sliced to "…i p", plate 4's copy whole 126 ft down-slip. The adjudicator's
reading is confirmed and the direction is *cross-frontage* (mosaic x = perpendicular to Ave. A,
bayward↔landward), not along the frontage.

### Measured steps (native scans warped through `transforms_city.json`, three independent methods)

Method: each plate re-rendered into the same mosaic window from its own `source_image` through its
own transform, then (a) sub-pixel line centres on the crop, (b) 2-D FFT cross-correlation of the
ink, (c) 1-D correlation of the σ=10 blurred column-ink profile. All figures are mosaic x
(1 mosaic px = 0.1725 ft).

| step | feature | measurement | ft |
|---|---|---|---|
| **4 ↔ 5b** at the seam | paired light slip-quay lines, extrapolated to the cut row y=1020: 5b 212.0/230.7 → 4 260.8/279.0 crop px | +48.6 crop px | **+16.8 ft** (4 landward of 5b) |
| 4 ↔ 5b | heavy slip wall 311.9 → 365.5 crop px | +53.6 crop px | +18.5 ft |
| 4 ↔ 5b | 2-D correlation, 4 windows over mosaic y 12650–13500 | +97.2…+98.3 px | **+16.8…+17.0 ft** |
| 4 ↔ 5b | 1-D profile, y 12700/12900/13100/13300 | +102/+102/+99/+98 px | +17.6…+16.9 ft, **constant along the seam** |
| **5b ↔ 13** at 28th St | Ave A **east (landward) block-front line**, mosaic y 13150–13350: 5b −6856.3, 13 −6746.1 | −110 px | **−19.0 ft** (5b bayward of 13) |
| 5b ↔ 13 | 1-D profile, y 10800→13200 | −55 → −89 px | −9.5 → **−15.4 ft, grows westward** |
| **5b ↔ 11** at 26th St | same Ave A east block-front line: 5b −6787.2, 11 −6776.1 | −11 px | **−1.9 ft** |
| **5b ↔ 9** at 23rd St | same line: 5b −6774.6, 9 −6782.5 | +8 px | **+1.4 ft** |
| **4 ↔ 13** (their real shared ground, y 13800–17000) | 1-D profile, 9 strips | +26 → −3 px | **+0.3…+2.4 ft** (HQ-47's elevator check: 1.6 ft) |
| 28th St **south block face** (along-frontage, mosaic y) | 5b 13113.7, 13 13114.5, 4 13124.3 | 0.8 / 10 px | **5b↔13 = 0.14 ft**, 4↔13 = 1.7 ft |

**Which plate is out of place: 5b.** Plate 4 now agrees with plate 13 to 0.3–2.4 ft, and 5b agrees
with 13 to 0.14 ft *along* the frontage — but 5b's Ave A east face swings **69 mosaic px (11.9 ft)
bayward between 26th and 28th St** (4,580 px of frontage) while plates 11 and 13 hold the same line
to 30 px (5.2 ft). The error is **not a constant offset**: it is 1.4 ft at 23rd, −1.9 ft at 26th,
−9.5 ft at 27th and −15…−19 ft at 28th / the 4|5b seam. That is a rotation of ~0.43–0.47°, and it
is the same 0.557° by which 5b's θ (+0.5935°) exceeds plate 13's (+0.0365°) and 11's (+0.0098°).

### Identity

Same ground, same names, no one-block-off risk. In one mosaic window (x −7300…−6350,
y 12500…13750) plate 5b prints **"28TH ST."** over the landward stub block fronts, and plate 13
prints **"AVE. A OR WATER"**, the odd Ave A run **2801 / 2803 / 2805 / 2807 / 2809** and the 28th St
run **101 / 103 / 105** on the same block corner, with **2727 / 102 / 104 / 106** on the block north
of 28th — i.e. **block 748** in both. The two plates' 28th St **south** block faces land 0.8 px
apart. North across the seam plate 13 letters **"747"**, **"GALVESTON WHARF COMPANY'S TERMINAL
TRACKS & YARD"**, the **10" W. PIPE** and **Elevator "B"**, all of which 5b draws too. Plate 4's top
margin prints its adjoining numeral **5** and 5b's bottom margin prints its adjoining numeral
**13** — the plates' own statement of the attachment.

### Which control holds 5b — none, in the axis that is wrong

* `transforms_city.json` gives 5a and 5b `tier: "core"`, `how: "frozen master: sheet-5 joint
  two-panel similarity (transforms_sheet5.json)"`. They are **not** solved from recipe controls.
* `python3 tools/localsolve.py --year 1912 --units 5b` (dry run, sandbox) prints
  **`1 controls touch ['5b']`** — only `pair_5a_5b.json`, axis *street* (y) — and then proposes
  `t [-19385.8,-1775.4] → [0.0,-1775.4]`, a **+3,344 ft** move. The x axis is rank-deficient:
  **no accepted control constrains 5b's cross-frontage position.**
* The six lowercase `pair_5a_*` / `pair_5b_*` files are all `"solve": false` seam-position records
  ("200 native px inside sheet 9/11/13's bay-side neatline"), excluded from `localsolve.py` and
  `bandresid.py`.
* The master controls **do** exist — `pair_05B_09` (22nd, 23rd, 24th), `pair_05B_11` (25th, 26th),
  `pair_05B_13` (27th, 28th), all in `freeze_manifest.json` — but every one of their anchors is a
  street **face line at constant page-y**, so they pin *along-frontage only*. Cross-frontage x enters
  the joint solve only through the tiny `b` coefficient of those y-equations, which is why every
  street face lands within a foot while the distance out from Ave A is 15–19 ft wrong. The master's
  own diagnostics record it: `n_block_rows 29`, `rms_block_px 59.22` (= **10.2 ft**), `downweighted 17`.
* **`pair_05B_13`'s two anchors — 27th St and 28th St, the two nearest the defect — are
  `"status": "CONTEXT_ONLY"`**, "per tasking: sheet 13 is context-only for the Piers 19-25 / 19th-25th
  St target footprint". The westernmost anchor the joint solve actually used is **26th St**. The
  4|5b seam is 4,600 px (790 ft) beyond it — pure extrapolation, and that is exactly where the error
  is 17 ft.

**Are any values wrong or stale?** No. Every `pair_05B_*` anchor value is correct on the printed
evidence (27th: Wm J. Lemp Brewing Co, italic Ave A 2701, odd run 101–111, "11" above 13's neatline;
28th: solid faces at the Ave A corner, dashed stalls 102/106 excluded; drafted-width ratios
1.96–1.99 ≈ 76–78 ft). And **nothing here is stale from plate 4's old placement**: there is no
`pair_4_5a` or `pair_4_5b` control, and none of the six lowercase 5a/5b frontage pairs mentions
plate 4, so `tools/wharfplace.py` (which rewrote `pair_4_13` / `pair_4_15`) never touched them. The
5a/5b frontage pairs listed as "to be re-derived" in `proposal_4_wharf.md` do not in fact carry any
value derived from sheet 4.

### Verdict: **NET-TENSION** (registration real; plate 5b is the misplaced plate; no control value is wrong)

Not VALUE-WRONG (the anchors read correctly), not STALE-DERIVED (no 4↔5b control exists), not
DRAWING-DIFFERENCE (line-pair spacing, wall spacing and the 28th St faces agree; only the drawn
track gauge differs, 6.3 ft on 5b vs 4.4 ft on 13, which is pen weight at 100 vs 50 ft/in). It is a
tension: panel 5B's cross-frontage placement was never observed, and the three block plates it abuts
do not themselves agree on the Ave A east face to better than ~7 ft, so no rigid 5B satisfies all of
them.

### Change lines

1. **`outputs/1912/recipe/controls/pair_5b_9_x.json`** — NEW (5b's first cross-frontage tie)
   `{"pair":["5b","9"],"axis":"avenue","corridor":"Ave. A or Water — east (landward) block-front
   line at 23rd (Tremont) St","a_native":6361.5,"b_native":1280.4,"status":"ACCEPTED"}`
   *previous: none.* Reason: 5b native x 6361.5 and sheet 9 native x 1280.4 are the same drawn line
   (5b's stub block front / 9's "101 103 105" block west face at the 2301 Armour & Co corner),
   read at mosaic y 1475.
2. **`outputs/1912/recipe/controls/pair_5b_11_x.json`** — NEW
   `{"pair":["5b","11"],…,"corridor":"… at 26th St","a_native":6392.6,"b_native":1250.1,
   "status":"ACCEPTED"}` *previous: none.* Read at mosaic y 8670 (26th St south face; 11's
   "MERCHANDISE" block west face, italic Ave A 2601/2603).
3. **`outputs/1912/recipe/controls/pair_5b_13_x.json`** — NEW
   `{"pair":["5b","13"],…,"corridor":"… at 28th St","a_native":6381.8,"b_native":1257.6,
   "status":"ACCEPTED"}` *previous: none.* Read at mosaic y 13250 (28th St south face; 13's
   101/2801 block west face, block 748).
4. **`outputs/1912/recipe/controls/pair_05B_13.json`** — both anchors
   `"status": "CONTEXT_ONLY" → "ACCEPTED"`, adding
   `"status_previous": "CONTEXT_ONLY"` and the reason: the CONTEXT_ONLY tag was scoped to the
   master's *Piers 19-25 / 19th-25th St* target footprint; the 1912 city mosaic uses panel 5B west
   to 28th St, so its west end now needs its own anchors. Values unchanged. (Bookkeeping only — the
   anchors are y-ties and do not fix the x error; they stop 5B's west end being unanchored in *any*
   axis.)
5. **Do NOT** move 5a. **Do NOT** re-run `tools/wharfplace.py` for this: `WHARF` has keys `4`, `6`,
   `3` only, sheet 5's panels are its *source* of rotation and scale, and the tool cannot place them.
   **Do NOT** use a translation-only solve (below).

### Dry-run and gate

All in the sandbox; `--apply` was used only against the scratch copy.

```
# degenerate today — the proof that nothing holds 5b in x:
python3 tools/localsolve.py --year 1912 --units 5b
  → 1 controls touch ['5b'] (pair_5a_5b, y); unit 5b: t → [0.0,-1775.4]  move (+3344, -0) ft

# translation only, with the three new x ties — cannot work, the error grows along the seam:
python3 tools/localsolve.py --year 1912 --units 5b
  → 3 controls; residuals median 4.4, max 4.4 ft; unit 5b moves (+2, -0) ft

# PROPOSED:
python3 tools/localsolve.py --year 1912 --units 5b --similarity
  → 8 line samples touch ['5b']; residuals after (ft): median 3.6, max 7.2
       pair_5b_11_x x@0.15 +7.2 | pair_5b_13_x x@0.85 -5.8 | x@0.15 -4.9
       pair_5b_11_x x@0.85 +4.8 | pair_5a_5b y ±2.5 | pair_5b_9_x x -1.2 / -0.1
  → unit 5b: scale 1.9876 → 1.9874 (-0.01%), rotation +0.593 → +0.163 deg,
             centre moves (-1, +11) ft
```

Effect on the mosaic, measured the same way before and after (median |dx| over identical windows):

| seam | now | after (9+11+13 ties) | after (9+13 ties only) |
|---|---|---|---|
| **4 \| 5b** | **17.3 ft** | **4.5 ft** | **1.6 ft** |
| 5b \| 13 | 10.9 ft | 1.0 ft | 4.0 ft |
| 5b \| 11 | 3.5 ft | 6.1 ft | 9.2 ft |
| 5b \| 9 | 2.1 ft | 3.5 ft | 3.3 ft |

**bandresid gate** (`python3 tools/bandresid.py --year 1912 --min-ft 6`):

* baseline: `334 accepted controls; 7 with a band residual over 6 ft (median of max-abs 1.6 ft)` —
  `pair_6_33 -12.2/-13.9`, `pair_40_41 +12.1/+8.0`, `pair_4_13 +11.9/+5.9`, `pair_6_21 +10.9/+7.1`,
  `pair_52_53_y -8.1`, `pair_26_42 -7.2`, `pair_54_60 -6.9`.
* **9+11+13 variant**: `337 accepted controls; 8 over 6 ft (median 1.6 ft)` — the same seven **plus
  one new: `pair_5b_11_x +7.2 / +4.8 ft`**. Median 1.6 ≤ 1.7 ✔; "none newly > 6 ft" ✘ — the single
  new entry is the *new control itself*, and its 7.2 ft is a real disagreement between plate 11's and
  plate 13's own Ave A east faces, not a degradation of anything existing.
* **9+13 variant**: `336 accepted controls; 7 over 6 ft (median 1.6 ft)` — **identical to baseline,
  gate passes cleanly**, and it is the variant that closes 4|5b hardest (1.6 ft), but it pushes the
  5b|11 seam to 9.2 ft (invisible to bandresid, because `pair_5b_11.json` is `solve:false`).

**Recommendation:** take the **9+11+13 variant** and ask Gate A for the one waiver on
`pair_5b_11_x`. It is the only option under which no 5b seam is worse than 6.1 ft, against a 17.3 ft
step today. If the gate is hard, the 9+13 variant passes unmodified but trades the defect westward.

**Disclosures the change must carry:** (a) it breaks the master's shared-orientation model —
5a stays at θ +0.593° while 5b goes to +0.163° (`relative_rotation_deg` in `transforms_sheet5.json`
is 0.0); (b) it is a change to two `tier: "core"` units, admissible only under the freeze statement's
"unless QA demonstrates the geometry itself is wrong (D-010)"; (c) it does **not** propagate to
sheets 3/4/6 — `wharfplace.py` reads rotation from `transforms_sheet5.json`, which is untouched;
(d) `localsolve.py --units 5a 5b --similarity` must **not** be used: 5a has no x tie of its own and
flies off `+2401 ft`.

### Secondary — the doubled "Slip" label and the cut

Mosaic footprints (crop → mosaic: x = −10767.34 + 2·cx, y = 10658.45 + 2·cy):

* plate **5b**'s "Slip": **x −9787…−9643, y 12554…12692** (clipped to "…i p")
* plate **4**'s "Slip": **x −10167…−9757, y 13058…13484** (whole)
* 4|5b overlap band: mosaic y **12678…13639**; plate 4's coverage begins at y **12606**.

**A cut along the quay wall is not available** — the 4|5b seam is a `seam_axis: "y"` seam, so the cut
is a line of near-constant mosaic y, while the quay walls run at constant mosaic x. **A cut along the
80 ft street does not work either**: 28th St's faces are at mosaic y 12625 and 13118, centreline
**12871**, and both labels straddle it (5b's north of it, plate 4's south of it) — *both* copies would
still survive. Only **one** window leaves one label: a cut at **mosaic y ≈ 13500–13600** (south of
plate 4's label, inside the band's south edge 13639), which gives panel 5B the whole slip mouth and
keeps its single, now-complete "Slip". Moving the cut north instead is impossible: 5b's label starts
at y 12554, i.e. 52 px (9 ft) north of plate 4's neatline, so plate 4 can never cover all of it.

**Verification rect (mosaic): `[-10250, 12500, -9600, 13560]`** — after the registration fix and the
cut move, exactly one "Slip" may appear inside it.

### Logged for seam 5b|13 — the doubled `10" W. PIPE`

Both plates draw *and letter* the same run: plate 13's copy at mosaic **x −9017…−8898, y 11162…11352**
(small), plate 5b's at **x −8969…−8850, y 11662…12138** (larger, clipped by the deckle at crop
(850–1000, 300–600) of `seam_4_5b_100.jpg`). The two letterings are ~110 ft apart along the pipe.
**This is a CUT matter, not registration.** The registration fix moves them ~15 ft closer but both
copies remain; only routing the 5b|13 boundary so one plate owns the whole pipe run removes the
duplicate. Note the same seam is on the wave-4 re-cut list (`5b|13` is one of the 31 pairs newly cut
on a min-ink path), so it must be re-cropped and re-graded regardless.

---

## Part B — seam 3|4

### Defect

The 3|4 ownership boundary is a dead-straight line at **mosaic y = 25305** (the DP path pegged at
`DP_HALF` for its whole 12,570 px span), 55 ft from the tick `tools/seamcrops.py` draws at
`s["coord"]` — which is why two graders checked the wrong line. Across the real boundary the drawing
steps, and the step **reverses sign along the seam**.

### Measured shear (native scans through `transforms_city.json`)

55 windows of 800×800 mosaic px over the 3∩4 overlap (x −17,400…−6,500, y 23,800…27,200), 2-D FFT
correlation, robust (2.2×median) trimming to 32 windows; fitted as a similarity about
(−11000, 25305):

```
plate-3 rendering vs plate-4 rendering:
  dscale +1.090 %   drot -0.064 deg   dt (-2.66, +6.91) ft
  residual median 9.1 px = 1.58 ft, max 23.9 px = 4.12 ft
  before:  median |d| 34.0 px = 5.86 ft, max 81.6 px = 14.08 ft
```

Model step across y = 25305, by along-seam position (dx = across the frontage, dy = along it):

| mosaic x | dx | dy | \|step\| |
|---|---|---|---|
| −17000 (Pier 35, open water) | −13.9 ft | +8.1 ft | **16.1 ft** |
| −14000 (tile b, coal pockets) | −8.3 ft | +7.5 ft | 11.2 ft |
| −11000 (seam centre) | −2.7 ft | +6.9 ft | 7.4 ft |
| −7000 (tile c, 33rd St / Ave A) | +4.9 ft | +6.1 ft | **7.8 ft** |

Sign-flipping along the seam, i.e. a shear, not an offset — consistent with the adjudicator's
"~13–14 ft south at the west end, 6.9 ft north at the east end". (My tile-c figure, 6.1–7.8 ft,
matches theirs exactly; my tile-b figure is 11 ft where they read 14.2 ft.)

### The shear is inherited, and it is not a drawing difference

* `transforms_city.json` scales: **sheet 3 = 4.00958, sheet 4 = 3.97640 — ratio 1.00834 (0.83 %)**,
  which is the fitted 1.09 % to within the measurement.
* Those came straight from the block plates each wharf sheet was fitted to:
  **67 = 2.01096, 75 = 2.00558** (mean 2.0083) against **13 = 1.99048, 15 = 1.99217** (mean 1.9913) —
  a **0.85 % gap in the city solve itself**, the same core-vs-outer gradient that runs through
  9/11/13/15 (≈1.991) versus 21/27/33/67/75 (≈2.006–2.011).
* The two wharf plates **do not** draw at different scales. `WHARF` in `tools/wharfplace.py` records
  their own street pitches in native px: sheet 4 **576 / 580 / 578 / 577**, sheet 3
  **572 / 579 / 580 / 578 / 573 / 574** — identical to ~0.5 %, on identically-produced pct50 copies
  of the same 100 ft/in series. The mosaic then gives the *same drafted pitch* 396.1 ft on sheet 4
  and 398.4 ft on sheet 3. **DRAWING-DIFFERENCE is refuted.**

### Is a similarity fit of sheet 3 against sheet 4 justified?

**Not as a registration change — it is justified by the seam but refuted by the plates.**

* `python3 tools/localsolve.py --year 1912 --units 3` **crashes** (`LinAlgError: 1-dimensional array
  given`) because **zero accepted controls touch sheet 3**: `pair_3_67` and `pair_3_75` are both
  `REJECTED` (disclosed source gap, both plates print the adjoining numeral "0") and no `pair_3_4`
  exists. `--similarity` crashes the same way (`zero-size array`). There is no dry run to give,
  because the tool has nothing to solve from.
* Sheet 3 **does not overlap 67 or 75 at all** — sheet 3's east edge is mosaic x −6538, sheet 67
  begins at −5191 and 75 at −3108, a 232–570 ft unmapped strip. Its only image-overlap neighbour is
  sheet 4. So a 3-against-4 fit would be fitting the one seam that exists — and would then be
  unchecked against everything behind it.
* Forcing it (inventing a `pair_3_4` tie on the 33rd St correspondence sheet 3 native y 235 = sheet 4
  native y 3005) would re-scale sheet 3 by ~1 %. Sheet 3's mosaic half-diagonal is ~10,000 px, so
  that is up to **~19 ft at its 39th St corner** relative to sheet 75's lattice — the very fit
  (`wharfplace.py`, residual median 1.5 / max 6.4 ft against 67 and 75) that places it.
* **Residual after, if it were done anyway: median 1.6 ft, max 4.1 ft at the 3|4 seam** (from
  5.9 / 14.1 ft) — a real improvement at the seam, bought with a 1 % scale error against the block
  plates. Not recommended.

### Verdict for 3|4: **NET-TENSION**

The 3|4 shear is the city solve's own 0.85 % core-vs-outer scale gradient made visible at the one
place where two plates on opposite sides of it overlap. It cannot be removed by moving sheet 3.

### Change lines for 3|4

1. **`tools/seamcrops.py`** — draw the tick on the **actual dp path**, not at `s["coord"]`. It is
   currently `yy = int((s["coord"] - y0)/2)`, so on any seam whose path wanders it can miss the cut
   by up to `DP_HALF` = 320 mosaic px (55 ft). Re-render `3_4` before any re-grade. (This is the
   change that matters most: it is what hid the defect from two graders.) **Already present,
   uncommitted, in the working tree** — `tools/seamcrops.py` now carries `boundary_at()`, which
   samples the buffered intersection of the two ownership polygons and ticks the real cut, keeping
   the nominal coordinate as a blue tick where the two differ by more than 8 px. Not written by this
   review; it only needs the crops re-rendered.
2. **`outputs/1912/recipe/seams/…` cut for 3|4** — give the pair a corridor on **33rd St**, the one
   street both wharf plates draw and the exact tie `wharfplace.py` places sheet 3 from
   (sheet 3 native y 235 = sheet 4 native y 3005, mosaic y ≈ 24560), *or* let the min-ink path reach
   the blank-water band west of Pier 35 (mosaic x −19087…−14087, blank on both plates). Either puts
   the residual shear in a street or in open water instead of doglegging the Pier 33/35 slip edge and
   the Fowler & McVitie coal-pocket track group at 45°.
3. **No transform change to sheet 3.** Record the seam as a disclosed core-vs-outer scale tension,
   with the numbers above, and re-measure the 660 ft wharf source gap at the same time, as
   `proposal_4_wharf.md` asked.

### Do the 5b and the 3 questions interact?

**Through sheet 4 as reference, yes; through the solve, only via the sheet-5 rotation.**

* Sheet 4 is now the plate both are measured against: it agrees with 13 to 0.3–2.4 ft and with 15 to
  0.5–1.7 ft, so a disagreement at 4|5b or 3|4 is the *neighbour's*.
* **Mechanically they are independent.** Sheet 3 reads sheet 4's transform inside `wharfplace.py`
  (`ave_a_from: ("4", 3005)`, `street_from: ("4", 235.0, 3005.0)`), so any further move of sheet 4
  moves sheet 3 — but sheet 5b reads nothing from sheet 4 (no 4↔5a/5b control exists) and is a frozen
  core unit. Re-solving 5b does not move 3; re-fitting 3 does not move 5b.
* **The one shared root is the rotation θ = +0.5935°** taken from the sheet-5 frozen joint solve.
  Panel 5B carries it natively; `wharfplace.py` hands the *same* θ to sheets 3, 4 and 6. The 5b
  defect *is* that θ being ~0.43–0.47° too large against the block plates (13 at +0.0365°,
  11 at +0.0098°). Sheet 4 carries the identical θ and drifts against plate 13 at the same rate
  (measured −0.0091 px/px ≈ 0.52°) — it only escapes visible harm because `wharfplace.py` re-fits its
  translation and scale over a short span, holding the drift to ±2.5 ft. **If the sheet-5 rotation is
  ever corrected at source (`transforms_sheet5.json`), sheets 3, 4 and 6 must all be re-run.** The
  proposed 5b patch deliberately does *not* touch that file, so it stays contained — at the cost of
  5a and 5b no longer sharing an orientation.

---

## Related seams

`4|13`, `4|15`, `3|4`, `3|67`, `3|75` (the 660 ft source gap, still to be re-measured), `5a|5b`,
`5b|9`, `5b|11`, `5b|13` (doubled `10" W. PIPE`; also newly min-ink cut in wave 4), `5a|7`, `5a|9`,
periphery `edge_15` / `edge_08`. `pair_4_13.json` already sits at **+11.9 / +5.9 ft** in the baseline
bandresid list — it is a `solve`-less frontage/cut pair being scored as a feature tie, and should
either be given `"solve": false` like its five siblings or be re-derived as a real tie.

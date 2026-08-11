# Lessons from the 1899 build — with code pointers

Everything here was measured during the build of the delivered 1899 poster.
Each section names the failure, the measurement that exposed it, the fix,
and where the fix lives in `sanborn/`.

---

## 1. Circular verification hides everything

**Failure.** `fit_sheet` residuals stayed under 15 px while sheet 06's
content sat **114 px** out of place, because a uniform per-sheet bias is
absorbed entirely by the translation term. The map printed 22nd Street, its
10-inch water main and its T.H. hydrant twice, 132 px apart. Nothing in the
automated pipeline noticed. A human looking at the picture did.

**Also failed:** a "window reconciliation" pass that re-fit scale and
translation per candidate window and scored by residual — mathematically
unable to discriminate, since it optimized away the very quantity it was
measuring. It left the real errors and corrupted a correct sheet.

**Fix — ground-truth landmarks.** Locate the *same physical object* on both
sheets of a pair, in each sheet's native pixels (a hydrant dot, a block
corner, a numbered lot corner). Map both through the build's own transforms
and take the difference. That difference is the true registration error and
cannot be absorbed by any term in the fit.

- Tool: `SEED_PRE1900/tools/landmark_check.py`
- Schema + worked set: `landmarks.json` (77 features across 19 pairs)
- Fields that matter: `sheet_a`/`a_xy`, `sheet_b`/`b_xy`, optional
  `weight` (raises a feature's pull in the solve), `schematic: true`
  (reported but excluded from pass/fail), `junction: true` (held out of the
  network solve and used for a rigid group placement instead)
- Note the single-knot axis rule in `axis_map`: wharf sheets have one
  avenue line, so the piecewise map extends affinely using the fitted scale.

**Rule.** A build is not aligned until this gate says so. Per-pair *mean*
with *small spread* = rigid misregistration, fixable. Large spread = the
drawings disagree; see §7.

---

## 2. Sheets cut at a shared street print no frame line

**Failure.** `composite.frame_bounds` searches for the strongest dark line
outside the outermost grid line. On an interior edge there is no frame line
to find, so it latched onto interior block walls. The seam logic then capped
each sheet's clip at that fictional frame, and the band between the fake
frame and the real paper edge — content only that sheet draws — rendered as
flat paper.

**What that cost, measured by the content-integrity auditor:**
- every south-side address row along 24th St, Avenue A to the east edge
  (~8,300 px wide), including the **CENTRAL HOTEL** name label
- most of 21st St's south frontage east of Avenue D, including an entire row
  of one-story frontage buildings (addresses 501–523)
- the Avenue D and Avenue G east-kerb address columns between 21st and 24th
- the **LEVY BLDG** west walls (block interiors sliced open)
- a 46/55 px "void" at Avenue D that an earlier report **disclosed as
  authentic never-engraved corridor**. It was not. It was this bug. The
  retraction is in `KNOWN_DEFECTS.md` and in the production report.

**Detection.** Scan the 450 px band inside each edge; if no row/column
carries a dark run longer than ~1500 px, that edge is *frame-open*. Verified
open on **every** interior side of all twelve 1899 sheets; content ran to
within 2–9 px of the paper edge on every h-seam bottom.

**Fix.** `coverage_prior.FRAME_OPEN_SIDES` lists `(unit, side)` pairs;
`run_build.py` substitutes the paper bound for the frame estimate on those
sides, for clips *and* for the `legal_cut` window. Per-edge insets live in
`SCAN_INSETS_1899` (measured; several are 0 because content runs right to
the paper). Result: coverage 98.52% → **98.79%**, all listed content back.

---

## 3. Edge grid-lines are comb-latched — on both axes

**Failure.** The whiteness comb finds corridor centres by phase-fitting at a
fixed pitch. Where a corridor is *cut* by the sheet's own paper edge, only
part of it is visible and the comb settles on the block frontage or kerb
bounding it. Known for Avenue A since early in the build; it turned out to
affect **every** sheet-cut edge line.

**The instrument that works.** For each sheet, fit a line through its
*interior* knots (which are reliable) and extrapolate to the edge slot;
compare to the detected knot. Measured biases: **x −120 to +72 px** across
14 lines, **y up to −41 px** across 9 lines.

**What direct measurement does instead:** picks a different feature on each
sheet (Avenue A came out −73 / −139 / −37 px on sheets 11 / 13 / 15) and
those differences displace whole sheet rows — this was the original cause of
the 48–85 px lateral step across 24th Street.

**Fix.** `line_overrides: {"x": {...}, "y": {...}}` per unit in
`coverage_1899.json` (and mirrored in `coverage_1899_gen.py` so a regenerate
does not lose them). Applied in `run_build.py` before `fit_sheet`.

**Result.** Avenues crossing 24th St: +20 / +25 / **−60** px →
**+4 / +5 / +3**. Crossing 21st: +3 / −5 / −2. Streets crossing Avenue G:
+2 / +9 / +9.

**Related trap.** Simply *dropping* an unreliable control instead of
overriding it took coverage 98.98% → **90.85%** — the sheets drifted off
their interior lines and opened a gap at the wharf junction. Override, don't
drop. And run the guard metrics before believing any cleanup.

---

## 4. Seam placement: owner-on-top, cut at measured paper edges

**Why not cut inside the corridor.** 1899 sheets overlap by hundreds of
pixels and *both* print the whole shared street plus both facing frontages.
Every cut inside that band destroyed something:
- inside a frontage strip → lost the 101–123 address row at 24th, the
  1902–1928 kerb column at Avenue D
- in the dead zone between the two copies of a street name → discarded
  **both** (21ST OR CENTRE, 24TH)
- through the label band at the wharf, where street and pier labels sit only
  ~30 px apart → doubled 22ND ST, or sliced PIER No 22, or halved the "6"
  pointer numeral

**The policy.** `EDITIONS["1899"]["seam_policy"] = "owner-on-top"`: the
owning sheet is laid over the *entire* overlap, capped at its own printed
extent. All horizontal seams then cut at the owner's frame/paper edge
instead of inside the corridor.

**Manual cuts.** `coverage_prior.SEAM_CUTS_1899` — the wharf 22nd entry
(`+177`) is the worked pattern: measured against the scan (sheet 7's content
ends at native 3934, paper at ~3937, the UT citation sits on backing from
3986), and passed with `trust_frame=False` so the synthetic frame estimate
cannot clamp it back into the numeral.

**Also fixed here.** A `paper_bounds` truncation: Avenue A's own frontage
rules are dark enough to split a sheet into two cream runs; taking the
longest ended that sheet's paper 240 px early, which made its frame appear
not to overlap its neighbour's and collapsed the seam to a midpoint
fallback. `composite.paper_bounds` now bridges gaps ≤ 60 px first.

**Scanner white.** An 18 px pure-white bar across the wharf at 19th was a
sheet's scan *background*, exposed because the cut was clamped to a frame
estimate that sits past the paper. Clamp by paper too: pure-white pixels
26,989 → 20.

---

## 5. Measure the lines the eye follows, and close the loop

**Why.** A viewer tracks street dashes, kerbs and corridor centres across a
seam. Those can step visibly even when block corners agree.

**Instrument.** A direct dash-row detector: for each candidate row, ink
fraction between ~0.08 and 0.55 (distinguishes a dashed pipe/centreline from
a solid frontage rule) plus a transition count ≥ 6 (confirms it is dashed,
not a broken solid). Take the row nearest the expected corridor centre on
each side of the boundary; the difference is the step.

**What does NOT work.** The pipeline's built-in phase-correlation seam
refinement returned responses of **0.01–0.26** against a 0.55 gate with
mutually inconsistent offsets (−563, +242, −252 px) — it samples a
quarter-resolution band and squashes it to a fixed 130 px width. Its gate
correctly rejected everything, which is why every automatic translation
correction was zero for the whole build.

**Loop.** Feed measured steps back as weighted landmark features
(`weight` 1.0–2.5 by confidence and visual prominence), rebuild, re-measure.
The solver then parks unavoidable residual inside block interiors rather
than on corridors. Worked example: Strand/Mechanic steps at 24th
+20 / +25 → +12 / +17 via corridor features, then → **+4 / +5** once the
edge-knot overrides (§3) removed the underlying cause.

**Discipline.** Verify a new instrument's *sign* visually once before
trusting a table of its numbers. An early junction measurement paired a
solid frontage line with a dashed pipe and produced confident nonsense.

---

## 6. The bounded network solve

`run_build.py`, `composite_edition`, the `config.LANDMARKS_PATH` block.

- **Variables** per sheet: `tx, ty, sx, sy` about the sheet's landmark
  centroid.
- **Scale bounds ±0.4%.** At ±1% the solver pinned sheet 13 at +1% against
  sheet 15 at −1%, and their 2% differential drift showed up as a 60 px
  corridor jog at 24th. Unbounded, it wanted **±7%** — visibly distorted
  building proportions, bought with a fake improvement in the residuals.
- **Reference-class sheets rigid.** Letting the schematic Avenue A couplings
  push scale onto the wharf sheets distorted their own excellent 22nd St
  pair by 19 px as a side effect. `smax = 1e-9` (scipy `lsq_linear` needs
  strictly `lo < hi`).
- **Iterate 3 rounds.** The gauge-fixing zero-prior on translations shrinks
  a large correction differentially on the first pass (steps went
  184.6 → 9.8 → 0.6 px). Prior weight 0.05.
- **Apply corrections everywhere the renderer looks**: `geo[k]["xkg"]/["ykg"]`
  (the warp knots — this is what actually moves content), `frame_g`,
  `frame_gp`, `paper_g`, the fit terms, **and** the copy dumped to
  `registration.json` so the post-build gate sees rendered reality.
  Writing only to `fit["tx"]` is a **silent no-op**; the warp renders
  through the knots. This trap cost a full build cycle.

---

## 7. Distinguish misregistration from source disagreement

**Misregistration** — consistent `dx/dy` across a pair's landmarks with
small spread. Removable by translation. In 1899 these ran to 208 px and the
whole set was solved out in one repair pass (median 98.4 → 23.5 px).

**Source disagreement** — offsets that vary feature to feature:
- The wharf sheets draw the blocks *east* of Avenue A as schematic outline
  rectangles; corner-pair offsets vary by up to **~100 px** on the same
  pair. Policy: the downtown sheets' surveyed drawing is authoritative
  there; schematic features are `schematic: true` (weight 0.25, excluded
  from the gate) and the mismatch is disclosed.
- The junction offsets group **by wharf sheet** (−55 / +11 / +97 px, each
  coherent within ±8 px) while the pier-side content aligns to ±7 px — so
  the disagreement lives inside the schematic east strips, and any rigid
  correction that fixes the junction tears the good pier seams.
- Two engravers drew the same rail yard with **18 rails on one sheet and 16
  on the other**, spacings differing 3–12 px. No registration reconciles
  differing counts. The fix that *does* work is compositional: place the
  seam so the whole yard renders from one engraver's drawing.
- Sheet 14's block faces sit ~35 px south of sheet 13's where 22nd/23rd
  cross Avenue D, while their *street* lines agree.

**The missing degree of freedom.** The separable piecewise warp maps x
through x-knots and y through y-knots; it cannot express rotation or shear.
Several of the residuals above are rotational in character. Adding a bounded
per-sheet rotation/shear term, solved from the same landmark equations, is
the one piece of new engineering worth doing — with pier-side and every
currently-good pair as regression gates.

---

## 8. Tone: the visible bands are within-scan

**Failure.** Sheet paper *medians* agreed within a few levels (200–209 cream
across twelve sheets), so per-sheet white balance had nothing to correct —
yet a 230 px band along one sheet's edge read as a **white bar** across the
finished map, and a tone cliff crossed the bay.

**Cause.** Each scan carries its own illumination field: edge vignettes and
shading that a single per-sheet gain cannot touch.

**Fix.** `composite.flatten_illumination`:
1. estimate the smooth paper field at 1/8 scale from bright, low-saturation
   pixels — **excluding scanner backing** (`min channel < 225`). Backing is
   near-neutral white and passes a naive brightness test; letting it in
   pulls the last ~200 px of real paper toward white and **inverts** the
   correction at exactly the edges the flattening exists to fix.
2. masked diffusion fills wash and ink holes; low-pass; divide out; multiply
   by the edition cream. Clip ±30–40% so a bad estimate cannot swing a pixel
   far.
3. **second field iteration** — one pass under-corrects large open areas
   (the bay sat 3–5 levels off).
4. **1-D row/column residual pass** — steep edge vignettes in the last
   ~150 px defeat the 2-D field (border reflection biases it bright); masked
   row/column medians of the corrected result close them. Rows with thin
   paper support keep gain 1 so wash bands are never stretched.

**Verification.** Compare **paper-only** pixels (bright, low-saturation,
non-backing); region means that include ink or wash mislead badly. Check
wash hue shift ≤ 2 levels and saturation drift after any change. Final
1899: 254 grid cells all within tolerance, cross-seam deltas ≤ 3 levels,
pure-white 48 → 7.

---

## 9. Water fill (the disclosed stylization)

`tools/tint_bay.py`. Originals print open water as blank paper with only a
blue edging strip along shorelines; the poster fills it.

- **Region**: flood-fill from open-water seeds across paper-like pixels,
  with ink and existing washes as barriers. The flood **will** leak through
  gaps in linework — in 1899 into two vacant yard blocks, the West Platform
  yards, the Fire Limits corridor and the bottom sheet margin, putting
  railroad tracks on pale blue. **Draw the region contour over the map and
  look at it**; add measured exclusion boxes; keep only the component
  connected to open water; fill enclosed islands (lettering, compass) so
  they do not punch holes.
- **Fill**: flat, at the **sampled waterline colour** (median of the printed
  edging strips; 1899 = BGR 208, 214, 199), with a smoothstep blend on
  paper-likeness so ink keeps clean edges.
- **Why flat and not a tint**: a multiplicative tint reproduces every
  residual paper gradient inside the blue and lands paler than the printed
  edging — which then reads as a highlighter outline around mottled water.
  Levelling to the edging colour makes the original strips merge invisibly.
- Region geometry is per-edition; the algorithm is not.

---

## 10. Guard metrics

`tools/build_metrics.py` — coverage %, pure-white px, pure-black %, plus
row-tone jump. Run before and after **every** change, together with the
landmark gate. Justify each regression in writing or revert it.

Nuance: coverage can be *inflated* by misregistered overlap (one sheet's
content covering ground the other should have shown). A coverage **rise**
after an alignment fix deserves the same scrutiny as a fall. And the tool
requires the crop rectangle when the composite is a crop — a mismatch once
reported 34.74% coverage on a healthy build.

---

## 11. Process

- **Checkpoint to disk incrementally.** Several agent runs died to session
  limits having written nothing because they buffered output to the end.
  Write `findings.json` as you go.
- **Adversarial, independent QC lenses beat one thorough pass.** Three
  earlier QC passes missed the amputated frontage bands; a five-lens fleet
  (corridor continuity, street/junction, lettering, tone, content
  integrity) found them in one round.
- **The human reviewer's eye beat the gates repeatedly.** Duplicated
  hydrant, faded buildings at a crop, the white bar at 19th, mottled water,
  un-even bay, misaligned dashes — all human-caught. When the reviewer says
  something looks wrong, **measure it before defending it**.
- **Never report a number a human eye hasn't confirmed is the thing they
  mean.** When two instruments disagree, prefer the direct measurement.
- **Retract cleanly.** This build shipped a disclosure calling a defect
  "authentic"; proving it was our own bug and saying so in the report cost
  nothing and made the rest of the report trustworthy.

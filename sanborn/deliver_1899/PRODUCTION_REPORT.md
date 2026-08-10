# Galveston 1899 — Wharf Front and Downtown

Sanborn-Perris Map Co., 1899 edition. Composited from the University of
Texas (Dolph Briscoe Center) scans.

**Extent** — Avenue A (Water) to Avenue I (Sealy); 19th Street to 25th
(Rosenberg Avenue); Piers 19–25.

**Sheets used (12)** — 6, 7, 8 (wharf front); 11, 12, 41 (18th–21st);
13, 14, 39 (21st–24th); 15, 16, 37 (24th–27th).

**Why these sheets** — the requested area was identified by sheet numbers
read off the **1889** key map (1, 2, 7, 8, 9, 10, 27, 29). Those numbers
denote different ground in 1899, whose atlas divides the city more finely:
94 numbered sheets against 1889's 60. The 1889 selection is a 2×3 downtown
block (7/8/29 over 19th–22nd, 9/10/27 over 22nd–25th, Avenues A–I) plus the
two wharf sheets alongside. The twelve 1899 sheets above cover that same
ground.

## Colour

**Uniform-paper revision:** each scan's illumination field (edge
vignettes, scanner shading) is flattened to the edition's aged-cream
tone before compositing (`flatten_illumination`): the smooth paper
field is estimated from bright low-saturation non-backing pixels and
the sheet is multiplied by target/field, clipped to ±30%. Inks and
washes keep their ratio to the local paper, so the printed colours
survive; the paper reads as one continuous aged sheet. This removed
the pale band south of 19th (sheet 8's edge vignette, which no
per-sheet gain could touch — the sheet paper MEDIANS already agreed
within a few levels) and the tone cliffs at the wharf joins.
Pure-white pixels 48 → 7.

Beneath that, no per-sheet white balance is applied
(`config.PRESERVE_COLORS`). Every
printed wash — pink brick, yellow frame, blue water, green special —
renders exactly as scanned, and the highlight-protection gain is disabled
because unity gain cannot push a highlight anywhere it was not already.

The honest cost: scan-to-scan tone differences remain visible at the joins
rather than being averaged away. This was the explicit requirement.

## Registration

Uniform grid: 1006 px avenue pitch, 1169 px street pitch, measured by
autocorrelation over 62 sheets (IQR 1003–1012 and 1166–1171). Avenue
identities are corridor SLOTS — A=0 … M=12, then the outlot district south
of Avenue M names every corridor, M½=13 … T½=27.

Per sheet: whiteness-comb phase fit at fixed pitch, centre-of-mass
refinement, identity assignment, then a joint least-squares consensus over
all sheets so neighbours agree on each shared line, and a piecewise-linear
warp through those knots (single Lanczos pass).

### Corrections applied, and why

Each of these was measured, not guessed, and each is a case where automatic
detection failed in a way that hid from the automated gates.

1. **Wharf street anchors (sheets 6, 7, 8).** On these sheets the streets
   survive only in a narrow strip beside Avenue A, half-buried in the
   terminal yards, and the comb settles on a block FRONTAGE line rather than
   the corridor centre — on sheet 06 by a uniform +114 px on every line. A
   uniform bias is absorbed by the per-sheet translation, so consensus
   residuals stayed under 15 px while the sheet's CONTENT sat 114 px out: it
   printed 22nd Street, its 10-inch water main and its T.H. hydrant a second
   time, 132 px below sheet 07's copy. Corridor centres are now measured as
   the midpoint of the two block frontage lines bounding each street,
   calibrated against downtown sheet 13 (frontages 1312/1557, centre 1434.5
   against its detected 1438), then refined by matching the wharf terminal
   tracks across each shared street: sheet 06 by (−6, −5), sheet 08 by
   (−28, −4), with sheet 07 held fixed as the reference.

2. **Avenue A on the downtown sheets (11, 13, 15).** Avenue A is cut by
   these sheets' west paper edge, so the comb again settled on the block
   frontage. The avenue centreline landed on the frontage, block 682's
   buildings began at the centreline, and the east half of Water Street
   disappeared beneath them. Set to the measured frontage minus 122 px, half
   the 245 px corridor.

3. **Sheets 52 and 93** (outside this extent, fixed in the same pass) sat
   half a pitch off, locked onto outlot quarter-lot division lines rather
   than avenue corridors.

4. **Sheet 32's east corridor** is printed AVENUE N½ but is the same
   corridor sheet 83 names AVENUE N; registered as N and disclosed.

### Seam placement

Cuts are constrained to the window where BOTH sheets carry printed map —
after the neighbour's frame and paper begin, before the owner's end. 1899
sheets share only ~50–70 px of printed corridor where the 1885 edition
shared several hundred, so an unconstrained cut lands outside that window
routinely: one cut opened a 41 px unfilled gash in the Avenue D corridor,
another rendered a sheet's blank margin and torn scan edge over the map.

The wharf sheets are the exception — they genuinely OVERLAP about 230 px
past the shared street. There the northern sheet is laid over the southern
through the whole overlap rather than cut at the line, which was slicing
warehouse and pier lettering mid-word.

`paper_bounds` bridges narrow gaps before taking the sheet's extent:
Avenue A's frontage rules are dark enough to split sheet 07 into two runs
and truncate its paper 240 px early, which made its frame appear not to
overlap its neighbours' and collapsed that seam to a midpoint fallback.

## Verification

Corridor identities were verified by reading the printed labels on every
unit of the edition — 90 units, ~340 corridor checks plus a street check
each. That fleet found the wharf Avenue A anchors ~700 px off (locked onto
the terminal-track corridor) and sheets 75/76 mis-slotted in opposite
directions, all since corrected.

## Disclosures

- Source coverage of the delivered extent is 98.94%. The remainder is bay
  water beyond the sheets' paper edges at the far west, left as blank paper.
  **No gap is ever filled with generated content.**
- Sheet furniture printed inside the sheets — compass roses, scale bars,
  edge sheet-reference numerals — renders where the original prints it.
  Two compass roses and two scale bars appear in the wharf area because
  two sheets contribute there.
- Where a feature spans a sheet boundary, the atlas letters it on both
  sheets. The seam cut is placed so exactly one copy renders.
- No content anywhere in this composite is generated, inferred, or cloned.
- **Scan tone differences remain at sheet boundaries** (PRESERVE_COLORS
  renders each scan as-is): sheet 7's paper scans darker than sheet 6's —
  visible as a tone line at the wharf 22nd seam and above the compass
  rose in the bay — and sheet 8's paper scans paler than 7's north of
  19th. These are the scans' own tones, not processing.
- Sheet 6's corner numeral "6" at 22nd × Water St sits where downtown
  sheet 13's surveyed drawing takes over and renders only partially;
  sheet 7's "6" pointer at the wharf 22nd seam renders whole.
- TEXAS STAR FLOUR MILLS is lettered by both sheet 7 (in the yards) and
  sheet 11 (on Water St); both render — same class as the duplicated
  compass roses.
- The 12″ W.PIPE rows step ~13 px across the authentic Avenue D void at
  23rd (pair 13|14's drawing scatter — see the repair section).

## Output

38.32 × 25.44 in at 300 dpi (page 39.32 × 26.94 in with caption).

## Seam QC — three independent adversarial passes

Three agents audited the composite: linework continuity, content loss, and
the wharf junction. They walked all seven seams at full resolution (~220
crops) and measured rather than eyeballed. Their findings drove the fixes
below, and the defects they found that REMAIN are listed after them.

### Fixed as a result

- **Seam policy.** Cutting on a single hard line inside the overlap
  destroyed content two ways: the cut landed inside one sheet's frontage
  strip (the 101–123 address row at 24th, the 1902–1928 kerb column at
  Avenue D), or it landed in the dead zone between the two sheets' copies
  of a street name and discarded BOTH (21ST OR CENTRE, 24TH). 1899 sheets
  overlap by hundreds of px, so the owner is now laid over the whole
  overlap, capped at its printed frame. All horizontal seams now cut at
  +167…+174 px — the owner's frame edge — instead of inside the corridor.
- **Frame cap on seam sides.** Sheet extents ran into the margin and pasted
  furniture into the map: sheet 37's blank top margin and its printed "37"
  across the Avenue G × 24th junction, a sliced "39" pointer filling the
  lost south frontage row at 24th.
- **Scanner white.** An 18 px pure-white bar across the wharf at 19th was
  sheet 08's scan background, exposed because the cut was clamped to the
  frame estimate, which sits past the paper. Now clamped by paper too:
  pure-white pixels 26,989 → 20.

### Known defects that REMAIN — measured, not fixed

These are real and were left in rather than papered over.

1. **Lateral step across 24th Street, ~48–85 px** east of Avenue A: the
   24th–27th sheet row sits east of the 21st–24th row. Independently
   confirmed by alley-centreline tracking and by column-profile correlation
   (−45…−58 px at every confident window), against controls elsewhere on
   the same sheet that return 0–1 px.
2. **Vertical steps at Avenue G**: +64 px at 25th, −42 px at 20th, −34 px
   at 22nd.
3. **Rail steps across Avenue A**, 0 → +30 px, growing north to south; 20
   of 28 sampled rows exceed 10 px. Worst at the 24th junction (+29 px).
4. **Avenue A corridor width breathes** +3 to +30 px along its length: its
   west kerb is wharf-surveyed and its east kerb downtown-surveyed.
5. **Stray sheet-reference numerals** inside the map body, and duplicated
   scale bars and compass roses where two sheets contribute.
6. **Ghost rails in the 16 px feather** where two mutually-offset drawings
   of the same track are averaged instead of one being chosen.

**Root cause of 1–4.** The content-level seam refinement, which exists to
correct ±40 px of line-detection noise by phase-correlating neighbouring
sheets' shared bands, produced ZERO usable measurements on this data:
correlation responses came out 0.01–0.26 against a 0.55 gate, with mutually
inconsistent offsets (−563, +242, −252 px). The gate correctly rejects
them — lowering it would inject that noise into the geometry and make
alignment worse. So every per-unit translation correction is zero and the
registration rests on line detection alone.

Fixing this properly means replacing the refinement's patch sampling, which
squashes a quarter-resolution band to a fixed 130 px width before
correlating. That is a real piece of work, not a parameter tweak, and it is
the single highest-value improvement left.

## Repair: landmark-solved per-sheet corrections (this revision)

The ground-truth landmark set (61 features, all 19 pairs, each the same
physical object located on both sheets) exposed rigid pairwise
misregistration far larger than the seam-walking QC could see — median
landmark step **98.4 px** — because a uniform per-sheet placement error is
invisible to fit residuals and mostly hidden by seam cuts.

**Method.** Per-sheet corrections solved from the 61 landmark
correspondences by bounded least squares, iterated to convergence (3
rounds): translation free; per-axis scale hard-bounded to ±1%, the range
the pitch-spacing gates established as physically plausible; wharf sheets
(06/07/08) held rigid — letting the schematic Avenue A couplings push scale
onto them distorted their own excellent 22nd St pair by 19 px as a side
effect. Corrections are applied to every geometry the renderer consumes
(warp knots, frames, paper extents, fits). Unbounded scale was measured and
REJECTED: the solver wanted ±7% x-scale, using distortion to soak up the
drawings' own scatter.

**Result (anti-circular gate, before → after):**
- median landmark step **98.4 → 23.5 px**; max 233.9 → 90.9 (the max is a
  schematic Avenue A feature — source disagreement, not registration)
- surveyed pairs: worst mean **36.7 → 16.6 px**; 9 of 14 within 10 px
- wharf pairs stay excellent: 07|06 (−4.3, +7.3), 08|07 (−3.3, +7.0)
- the five pairs at 11–17 px (11|12, 12|14, 12|41, 13|14, 41|39) sit at
  the level of the drawings' own scatter (their per-pair spreads are
  13–18 px): further improvement requires either rotation (inexpressible
  in the separable warp) or distortion beyond ±1%. Declined.

**Guard metrics — all three moved, each with cause:**
- coverage 98.98 → 98.57%. Two authentic voids opened at Avenue D
  (46 px wide above 24th between sheets 13|14; 55 px below between 15|16):
  with content correctly registered, the neighbouring sheets' printed
  frames genuinely do not meet — each engraver stopped at his border
  mid-corridor. The old coverage was INFLATED by misregistered overlap.
  The voids render as flat paper inside the blank roadway; every kerb
  column and address row is present (sheet 16 prints both kerbs on its
  stretch). Plus more open bay inside the slightly wider crop.
- pure-white 20 → 43 px (bar: ≤50): sheet edges moved; a few more scan
  pixels at the rim.
- pure-black 0.0070 → 0.0078%: more authentic sheet-edge ink rendered.

**Visually verified after repair:** 22nd St runs straight through Avenue G
(was −34 px); the 24th St row shift (48–85 px) is gone; the corridor rows
align across Avenue D above and below 24th.

## Wharf and junction polish (this revision)

Driven by marked-up review crops: the wharf 22nd seam, the Avenue A
(Water St) junction, and Avenue D at 23rd.

1. **Junction placement.** Five street-furniture landmarks (water pipes,
   hydrants, corridor rows at 19th–25th where wharf meets downtown) were
   measured by dashed-row selection. Fed into the network solve they
   dragged downtown toward the wharf's schematic geometry (gate median
   23.5 → 27.4 px — rejected); instead the wharf trio takes ONE common
   translation, the weighted mean of (downtown − wharf) across them:
   (−9.9, +14.9) px. Their residuals disagree street-to-street by up to
   ~95 px against downtown sheets that agree with each other to 3 px —
   the wharf–downtown junction scatter is source-level, and the
   remaining jog at any one street reflects it.
2. **Wharf pair means zeroed.** The schematic couplings left ~7 px of
   uniform step on 07|06 and 08|07. After the junction shift, 06 and 08
   are shifted so their surveyed pair means vanish exactly (07 anchors):
   06 by (+4.3, −7.3), 08 by (−3.3, +7.0). Pier edges, slip water and
   rails now cross the wharf seams with only the drawings' own ±4 px
   scatter.
3. **The 22nd wharf seam cut moved from +142 to +175 (sheet 7's measured
   paper edge).** Sheet 7 draws the entire shared band completely — the
   full Pier 22 warehouse, PIER No 22 and 22ND ST labels, its "6"
   pointer numeral, the NO EXPOSURE note — and its paper ends at native
   3937 with the UT citation printed on backing below. The old cut,
   clamped by a synthetic frame estimate (the wharf sheets print no
   frame line), sliced the pointer numeral in half. The new cut renders
   all of it from one engraver's drawing and excludes the backing.
   Flipping sheet 6 on top was tried and measured out: 6's scan is
   itself cut ~90 px above 22nd, so every candidate cut sliced or
   ghosted a label copy that sheet 7 prints intact.
4. **Post-spacing disagreement (measured).** Where both sheets draw the
   Pier 22 warehouse, their post marks agree at the west end (1–4 px)
   and drift to ~15 px apart at the east end, while the surveyed corner
   landmarks show <0.1% relative scale across the pair: the drift is
   the two engravers' drawings disagreeing, not a scan-scale error.
   With the new cut the warehouse renders from sheet 7 alone, so no
   mixed drawing remains there.

**Guard metrics:** coverage 98.54%, pure-white 48 px (bar ≤50),
pure-black 0.0086% (more authentic sheet-edge ink at the deeper cut).
Wharf pair means after: 07|06 (0.0, 0.0), 08|07 (0.0, 0.0).

**Declined, with cause — Avenue D at 23rd.** The doubled 12″ W.PIPE
appearance across the authentic corridor void is pair 13|14's +13 px
mean, which sits at that pair's own drawing-scatter floor (spread
13 px). Forcing it to zero pushes ~24 px onto the 24th St crossings
via pair 12|14. Left as-is and disclosed; per-sheet rotation (a
rebuild item, inexpressible in the separable warp) is the honest fix.

## Corridor continuity at 24th (uniform-tone revision)

Column-profile NCC measured Strand/Mechanic kerb steps of +20/+25 px
crossing 24th (pair 13|15). The 4-cycle 13-15-16-14 closes with ~25 px
of engraver disagreement, so these steps cannot be zeroed — only moved.
Two corridor-continuity landmarks (weights 2.0/1.2) now bias the solve
toward the corridors the eye follows: Strand +20 → +12, Mechanic
+25 → +17, with the residual pushed into block interiors and a rigid
−18 px absorbed at the 14|39 boundary, where the owner-on-top Avenue G
seam hides it (streets cross Avenue G at +8/+11 px, scatter level).
Scale bounds tightened ±1% → ±0.4% after the ±1% solve pinned sheets
13/15 at opposite bounds.

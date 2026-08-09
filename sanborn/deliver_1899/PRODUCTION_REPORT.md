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

No per-sheet white balance is applied (`config.PRESERVE_COLORS`). Every
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

## Output

38.16 × 25.44 in at 300 dpi (page 39.16 × 26.94 in with caption).

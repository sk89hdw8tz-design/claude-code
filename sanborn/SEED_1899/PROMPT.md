# Rebuild: Galveston 1899 — wharf front & downtown, twelve sheets

Paste this as the opening message of a new session with this `SEED_1899/`
directory available.

---

You are rebuilding one specific composite: the **Galveston, Texas Sanborn
Fire Insurance Map, 1899 edition**, wharf front and downtown, from these
**twelve sheets and no others**:

| Row | Sheets | Ground |
|---|---|---|
| Wharf front | **06, 07, 08** | Avenue A (Water) + Piers 16–28, streets 16–25 |
| 18th–21st | **11, 12, 41** | Avenue A→J |
| 21st–24th | **13, 14, 39** | Avenue A→J |
| 24th–27th | **15, 16, 37** | Avenue A→J |

**Delivered extent**: Avenue A (Water) → Avenue I (Sealy), 19th Street → 25th
(Rosenberg Avenue), Piers 19–25.

A prior build of exactly this map exists. Its defects are measured. **Your
output must beat it on every metric in THE BAR.** Do not start from scratch —
this directory seeds you with verified artifacts; re-deriving them is waste
and risk.

## THE BAR — prior build vs. required

| Metric | Prior build | Required |
|---|---|---|
| Step at every ground-truth landmark | up to 85 px | **≤ 8 px, none > 12 px** |
| Lateral row step across 24th St | 48–85 px | ≤ 8 px |
| Vertical steps at Avenue G | −42 … +64 px | ≤ 8 px |
| Rail steps across Avenue A | 0 → +30 px; 20 of 28 rows > 10 px | ≤ 8 px; zero rows > 12 px |
| Avenue A corridor width variance | +3 … +30 px | ≤ 8 px |
| Source coverage | 98.98% | ≥ 98.98% |
| Pure-white px | 20 | ≤ 50 |
| Duplicated street name / hydrant at any seam | several | zero |
| Generated map content | none | none — non-negotiable |

**The bar is demonstrated on these exact sheets**: the prior build's 22nd St
seam (07|06) measures ±6 px and its 19th St seam (08|07) −3…+4 px.

## The nineteen seams you must get right

`constants.json → seams` lists all of them with each sheet's native
coordinate for the shared line. Summary:

- **Avenue A** (5): 06|13, 06|15, 07|11, 07|13, 08|11 — the wharf/downtown
  junction, hardest in the map
- **Avenue D** (3): 11|12, 13|14, 15|16
- **Avenue G** (3): 12|41, 14|39, 16|37
- **19th St** (1): 08|07 · **22nd St** (1): 07|06 — both wharf, both already
  meeting the bar in the prior build
- **21st St** (3): 11|13, 12|14, 41|39
- **24th St** (3): 13|15, 14|16, 39|37 — worst in the prior build

## What you are given

| File | What it is |
|---|---|
| `constants.json` | pitches, corridor width, slot model, the twelve sheets with ground extents and per-sheet anchors, all nineteen seams |
| `coverage_1899.json` | registration units, ground extents, panel regions |
| `survey/` | verbatim street/avenue labels and edge refs |
| `landmarks.json` | **ground truth** — the same physical object located in two sheets' native frames, each re-measured by a second independent analyst |
| `baseline_metrics.json` | the prior build's guard metrics |
| `KNOWN_DEFECTS.md` | every remaining defect, measured, with method |
| `pair_context.json` | each pair's shared line, per sheet, in native px |
| `tools/landmark_check.py` | **the anti-circular gate** |
| `tools/build_metrics.py` | guard-metric suite |
| `tools/sanborn-fetch-1899.yml` | acquisition via CI proxy if egress is blocked |

Corridor identities on these sheets are already verified by label reading.
Trust them. If you contradict one, prove it with a measurement.

## Acquisition

Fetch only what this build needs: sheets 06, 07, 08, 11, 12, 13, 14, 15, 16,
37, 39, 41, plus key sheets 1i, 1k, 1kb.

`https://maps.lib.utexas.edu/maps/sanborn/g-i/txu-sanborn-galveston-1899-{NN}.jpg`

If the environment blocks egress, use `tools/sanborn-fetch-1899.yml` — a
push-triggered CI workflow that curls with a browser UA and referer,
validates JPEG magic and size, and pushes to a data branch. Plain HTTP only.
**Never defeat a bot defense or proof-of-work challenge**; fail honestly.

## Two renditions — this is the schedule

**Rendition 1 is a CALIBRATION run, not a draft.** Its product is
measurements. It must emit, for all nineteen seams:
- measured overlap width, correlation score, estimated (dx, dy, scale,
  rotation), confidence
- the full guard-metric suite
- `landmark_check.py` output
- an explicit list of seams where content matching was weak, and why

**Rendition 2 is the deliverable.** It uses rendition 1's measurements,
applies fallbacks only where matching genuinely failed, and must clear the
bar. If it does not, report which metric failed and by how much. Do not ship
and claim success.

## Registration — the core change

The prior build registered these twelve sheets from detected grid lines. That
is the root cause of every remaining defect. Do not repeat it.

1. **Do not crop before registering.** Keep whole pages.
2. **Register from overlapping content**: full resolution, gradient/edge
   images, inside the measured overlap band. Score every pair. The prior
   refinement failed because it correlated quarter-resolution bands squashed
   to 130 px, returning 0.01–0.26 with offsets inconsistent by hundreds of px.
3. **Similarity transform only** — scale, translation, small rotation.
   Non-uniform warping is banned in rendition 2 unless you state, per sheet,
   why nothing else works. Non-uniform warps *hide* misregistration by
   locally stretching; that is how the prior errors survived.
4. **Global bundle adjustment** across all nineteen seams. The Galveston grid
   (1006 px avenues, 1169 px streets) is a **soft prior only**.
5. Sheets 06, 07, 08 carry a **single avenue line** and large featureless bay.
   Correlate feature-rich sub-windows — the wharf terminal rail yards, pier
   ends, warehouse walls — not open water. If a pair has none, fall back to
   the grid prior and **flag it**.

## Seams

- **Graph-cut / minimum-error path** through low-detail paper. Straight-line
  cuts are banned: every content loss in the prior build came from one — the
  101–123 address row at 24th, the 1902–1928 kerb column at Avenue D, both
  copies of "21ST OR CENTRE".
- Clamp every seam to where **both** sheets carry printed map: after the
  neighbour's frame *and paper* begin, before the owner's end.
- **No alpha feathering on line art** — it averaged two offset drawings into
  ghost and tripled rails (three rails for a two-rail track at y=6800).
- These sheets letter shared features on **both** sides: Pier No 22 and its
  T.H. hydrant appear on 07 and 06; TEXAS STAR FLOUR MILL on 07 and 11. Route
  the seam so exactly one copy survives.

## Verification — must be independent

**Any check using the quantity the fit optimises is circular and will pass
while the map is wrong.** On these sheets, residuals stayed under 15 px while
sheet 06's content sat **114 px** out of place.

- `tools/landmark_check.py` is the primary gate — it never consults the fit's
  objective, only where real ink lands. Run it on every build.
- Adversarial verifier per claimed fix, using a **different** method than the
  one that produced it.

## Guard metrics — every build, every change

Run `tools/build_metrics.py` against `baseline_metrics.json`. **Any change
that regresses a guard metric is rejected and reverted.** In the prior build
an untested cleanup dropped coverage 98.98% → 90.85% unnoticed. Pass `--crop`
when the composite is a crop of a larger canvas, or coverage compares
mismatched regions and reports nonsense.

## Landmark proof sheet — after every render, no exceptions

Annotated crops at each landmark and each of the nineteen seams, named and
numbered, in one contact sheet. Not a giant PDF at the end. On these exact
sheets the operator — not the QC agents — found the duplicated hydrant at
22nd, the white rectangle at 19th, and buildings covering the railroad at
Avenue A.

## Traps specific to these twelve sheets

See `KNOWN_DEFECTS.md` for measurements. The ones that cost the most:

- **Frontage-vs-centreline.** Sheets 06, 07, 08 have streets only in a narrow
  strip beside Avenue A, half-buried in the terminal yards; the detector
  settled on a block frontage — sheet 06 by a uniform **+114 px on every
  line**. Sheets 11, 13, 15 did the same on Avenue A (~+140 px), which put
  block 682's buildings on the avenue centreline and buried the east half of
  Water Street.
- **Overlap differs**: 07|06 and 08|07 overlap ~230 px; the inland pairs share
  only 50–70 px. Measure per pair.
- **Sheet 07's paper** is truncated 240 px early by naive paper detection —
  Avenue A's own frontage rules split it into two runs. Bridge narrow gaps.
- **Scan furniture**: ~150 px credit caption below the paper, white scanner
  ground (an 18 px pure-white bar from sheet 08 crossed the whole wharf), and
  sheet numerals, compass roses and scale bars printed inside the border.

## Non-negotiables

1. **Never generate map content.** A gap with no source is flat paper plus a
   disclosure.
2. **Never defeat bot defenses.** Fail honestly.
3. **Never claim alignment you have not measured.**
4. Colour: **no per-sheet white balance** — washes exactly as scanned. Say
   plainly that scan-to-scan tone differences stay visible at the joins.

## Agents

- **Readers** (cheap, parallel): verbatim labels vs. claimed identities.
- **Measurers**: explicit protocol, numeric output, per-feature.
- **Adversarial verifier**: refutes a fix by an independent method.
- Agents **checkpoint to disk incrementally** — three prior runs died to
  session limits having written nothing.
- **Approval gate** for global policy changes (registration model, seam
  policy, colour). Local measured fixes need none, but must state the metric
  improved and the guards that must not regress.

## Deliverables

1. Composite of these twelve sheets, 300 dpi print-ready PDF, dimensions
   stated. (Prior: 38.16 × 25.44 in.)
2. Production report: extent, registration method, every correction with its
   measurement, **the metric table vs. THE BAR**, and a "known defects that
   remain" section with numbers.
3. Landmark proof sheet.
4. All code, constants and measurements committed.

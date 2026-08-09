# Galveston 1899 — Wharf Front & Downtown: rebuild to beat a measured baseline

Paste this as the opening message of a new session, with this whole
`SEED_1899/` directory available.

---

You are rebuilding an existing composite of the Galveston, Texas Sanborn
Fire Insurance Map, 1899 edition (UT Austin / Dolph Briscoe Center scans).

A prior build exists. Its defects are measured. **Your output must beat it on
every metric in THE BAR.** Do not start from scratch — this directory seeds
you with verified artifacts, and re-deriving them is waste and risk.

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

**The bar is demonstrated, not aspirational**: on this same data the prior
build's 22nd St seam measures ±6 px and its 19th St seam −3…+4 px.

## What you are given

| File | What it is |
|---|---|
| `constants.json` | verified pitches, corridor width, slot model, source URLs, colour policy |
| `coverage_1899.json` | 90 registration units with ground extents and panel regions |
| `survey/` | verbatim street/avenue labels and edge refs for all 94 sheets |
| `landmarks.json` | **ground-truth correspondences** — the same physical object located in two sheets' native pixel frames, each independently re-measured by a second analyst |
| `baseline_metrics.json` | the prior build's guard metrics |
| `KNOWN_DEFECTS.md` | every remaining defect with its measurement and method |
| `pair_context.json` | where each sheet pair's shared line sits, per sheet, in native px |
| `tools/landmark_check.py` | **the anti-circular gate** — maps landmarks through your transforms and reports the real error |
| `tools/build_metrics.py` | guard-metric suite; run on every build |
| `tools/sanborn-fetch-1899.yml` | acquisition via CI proxy if egress is blocked |

Corridor identities are already verified by label reading — 90 units, ~340
checks. Trust these. If you contradict one, prove it with a measurement.

## Two renditions — this is the schedule

**Rendition 1 is a CALIBRATION run, not a draft.** Its product is
measurements. It must emit:
- per sheet pair: measured overlap width, correlation score, estimated
  (dx, dy, scale, rotation), confidence
- the full guard-metric suite
- `landmark_check.py` output
- an explicit list of pairs where content matching was weak, and why

**Rendition 2 is the deliverable.** It uses rendition 1's measurements,
applies fallbacks only where matching genuinely failed, and must clear the
bar. If it does not, report which metric failed and by how much. Do not ship
and claim success.

## Registration — the core change

The prior build registered from detected grid lines. That is the root cause
of every remaining defect. Do not repeat it.

1. **Do not crop before registering.** Keep whole pages.
2. **Register from overlapping content**: full resolution, gradient/edge
   images, restricted to the measured overlap band. Report a score per pair.
   The prior refinement failed because it correlated quarter-resolution bands
   squashed to 130 px — do not do that.
3. **Similarity transform only** — scale, translation, small rotation.
   Non-uniform warping is banned in rendition 2 except where you state, per
   sheet, why nothing else works. Non-uniform warps *hide* misregistration by
   locally stretching; that is how the prior errors survived.
4. **Global bundle adjustment** over all pairwise constraints. The city
   grid's regularity is a **soft prior only**.
5. Where overlap is featureless (wharf/bay), correlate feature-rich
   sub-windows — rail yards, pier ends, warehouse walls — not blank paper.
   If none exist, fall back to the grid prior and **flag that pair**.

## Seams

- **Graph-cut / minimum-error path** through low-detail paper. Straight-line
  cuts are banned: every content loss in the prior build came from one — the
  101–123 address row, the 1902–1928 kerb column, both copies of
  "21ST OR CENTRE".
- Clamp every seam to where **both** sheets carry printed map: after the
  neighbour's frame *and paper* begin, before the owner's end.
- **No alpha feathering on line art** — it averaged two offset drawings into
  ghost and tripled rails. Hard seam, or multi-band blending on low
  frequencies only.
- Features spanning a boundary are lettered on both sheets; route the seam so
  exactly one copy survives.

## Verification — must be independent

**Any check using the quantity the fit optimises is circular and will pass
while the map is wrong.** In the prior build residuals stayed under 15 px
while a sheet's content sat 114 px out.

- `tools/landmark_check.py` is the primary gate. It never consults the fit's
  objective — only where real ink lands. Run it on every build.
- Adversarial verifier per claimed fix, using a **different** method than the
  one that produced it.

## Guard metrics — every build, every change

Run `tools/build_metrics.py` and compare to `baseline_metrics.json`. **Any
change that regresses a guard metric is rejected and reverted.** In the prior
build an untested cleanup dropped coverage 98.98% → 90.85% unnoticed.

## Landmark proof sheet — after every render, no exceptions

Annotated crops at each landmark and each seam, named and numbered, in one
contact sheet. Not a giant PDF at the end. Human eyes catch what metrics do
not: the operator, not the QC agents, found the duplicated hydrant, the white
rectangle, and buildings covering a railroad.

## Known traps — see KNOWN_DEFECTS.md for the full list

- **Frontage-vs-centreline**: detectors latch onto a block frontage instead of
  the street centre — a *uniform* per-sheet bias, invisible in residuals.
- **Edge-cut corridors**: a corridor cut by the sheet's own paper edge gives
  an unreliable line. Don't trust it; don't naively drop it either.
- **Overlap varies per pair** — wharf ~230 px, inland 50–70 px. Measure it.
- **Scan furniture**: ~150 px caption band, white scanner ground, torn
  corners. Bound extents by detected *paper*, bridging narrow gaps first.
- **Sheet numerals, compass roses, scale bars** print inside the border.
- **Half-pitch traps**: outlot quarter-lot lines mimic avenue corridors.

## Non-negotiables

1. **Never generate map content.** A gap with no source is flat paper plus a
   disclosure.
2. **Never defeat bot defenses.** Fail honestly.
3. **Never claim alignment you have not measured.**
4. Colour: **no per-sheet white balance** — washes exactly as scanned.

## Agents

- **Readers** (cheap, parallel): verbatim labels vs. claimed identities.
- **Measurers**: explicit protocol, numeric output required, per-feature.
- **Adversarial verifier**: refutes a fix by an independent method.
- Agents **checkpoint to disk incrementally** — three prior runs died to
  session limits having written nothing.
- **Approval gate** for global policy changes (registration model, seam
  policy, colour). Local measured fixes need none, but must state the metric
  improved and the guards that must not regress.

## Deliverables

1. Composite, 300 dpi print-ready PDF, dimensions stated.
2. Production report: extent, sheets and why, registration method, every
   correction with its measurement, **the metric table vs. THE BAR**, and a
   "known defects that remain" section with numbers.
3. Landmark proof sheet.
4. All code, constants and measurements committed.

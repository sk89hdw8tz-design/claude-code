# Build: Galveston Sanborn maps, 1877 · 1885 · 1889 — poster set

Paste this as the opening message of a new session.

---

## The job

Build **three** print-ready composite maps of downtown Galveston and its
wharf front — one each from the **1877**, **1885** and **1889** Sanborn Fire
Insurance atlases — covering the same ground as the finished 1899 poster,
styled to match it, and beating its measured alignment numbers.

**1899 is already built. Do not rebuild it.** It is your benchmark and your
worked example: `sanborn/deliver_1899/PRODUCTION_REPORT.md` (copied here as
`REFERENCE_REPORT_1899.md`) documents exactly how it was made, what was
measured, and what remains wrong with it.

### The extent — identical for all three editions

**Avenue A (Water Street) → Avenue I (Sealy); 19th Street → 25th Street
(Rosenberg Avenue); plus the wharf front and piers west of Avenue A.**

That is the 1899 poster's frame. Match it. Where an edition's atlas does not
cover part of that ground, render flat paper and disclose the gap with a
measured coverage figure — **never** generate, infer, clone or extend map
content to fill it. This rule has no exceptions and overrides every
aesthetic consideration in this document.

### Deliverables per edition (six PDFs + three masters total)

| Output | Size | Notes |
|---|---|---|
| Large poster | **40 × 27 in landscape** | 27×40 stock rotated; map prints ~39 × 25.4 in at ~295 dpi from an 11.5k-px master |
| Small poster | **36 × 24 in landscape** | most common poster size, near-exact aspect match (1.50 vs map 1.53); ~329 dpi |
| Master raster | full resolution PNG | the source of both PDFs — never upscale into a poster |

Both PDFs carry a caption bar in the reserved margin: title, edition year,
sheet numbers used, source credit ("University of Texas / Dolph Briscoe
Center" or "Library of Congress" as applicable), and a one-line statement
of any disclosed gap or stylization. Match the 1899 poster's typography.

### Styling — match the 1899 poster exactly

1. **Uniform aged paper.** Every scan's illumination field is flattened to
   the edition's own aged-cream tone before compositing, so the mosaic reads
   as one continuous sheet rather than N scans. `composite.flatten_illumination`.
2. **Original wash colours.** Pink brick, yellow frame, blue water, green
   special — all render as scanned. No white balance. Verify washes shift
   ≤ 2 hue levels after any tone change.
3. **Flat water.** Bay, slips and channels are filled with that edition's
   own sampled waterline colour, flat, with ink and lettering blended
   through. `tools/tint_bay.py`. This is a **disclosed stylization** — the
   originals print open water as blank paper — and it is the only departure
   from as-printed colour that is permitted.

---

## Where everything lives

Repository: `sk89hdw8tz-design/claude-code`, branch `claude/new-session-fxmhgv`.

### The pipeline — USE IT

`sanborn/*.py` is the proven tool: `run_build.py` (registration, landmark
solve, seam placement, compositing), `composite.py` (frame/paper detection,
tone, warp), `coverage_prior.py` (per-edition sheet tables, seam policy),
`config.py` (per-edition constants).

**Read this carefully:** an earlier seed package (`sanborn/SEED_1899/PROMPT.md`)
firewalled this code and demanded a from-scratch rebuild. **That advice is
withdrawn.** The rebuild never happened; instead, iterative *measured repair*
of this pipeline took the 1899 map from a median landmark step of 98 px to
24 px, restored thousands of pixels of amputated content, and produced the
delivered poster. The code now encodes a dozen hard-won corrections that a
fresh implementation would have to rediscover. Extend it; do not replace it.

The one genuine gap: **the separable piecewise warp cannot express per-sheet
rotation or shear.** Several residual defects in 1899 are documented as
needing exactly that. Adding it is the single sanctioned piece of new
engineering — see PLAYBOOK item 7.

### The scans

| Edition | Where | Count | Status |
|---|---|---|---|
| **1877** | UT: `maps.lib.utexas.edu/maps/sanborn/g-i/txu-sanborn-galveston-1877-NN.jpg` (NN = 02–10) | 9 | **not yet fetched** — fetch first |
| **1885** | LoC masters (`tile.loc.gov/.../g085391885/08539_1885-NNNN.tif`, 6450×7650) per `config.py`; UT also has 19 sheets | 19 | partially local; verify |
| **1889** | branch **`origin/sanborn-data-1889`**, `sources/1889/Galveston_1889_NN.jpg` + `SHA256SUMS` | **62 — already fetched** | ready |
| 1899 | branch `origin/sanborn-data-1899`, `sources/1899/` | 102 | reference only |

`origin/sanborn-data-1889:sources/1889/ALL_GALVESTON_LINKS.txt` holds direct
UT links for **every** Galveston edition including 1877 and 1885 — use it
rather than re-scraping. `EDITIONS.txt` on the same branch gives sheet counts
per edition. Verify JPEG magic bytes and sizes against `SHA256SUMS` before
trusting any fetched file. **Do not attempt to defeat bot defenses or
proof-of-work challenges** on any source site; if a fetch is blocked, say so
and use an alternate source (Portal to Texas History, LoC).

### Which sheets cover the extent

Start here, then **verify by reading the printed corridor and street labels
on each sheet** — this verification caught two mis-slotted sheets and a
700 px anchor error in 1899, and it is not optional.

- **1889** — the user's original selection, read off the 1889 key map:
  **sheets 1, 2, 7, 8, 9, 10, 27, 29** (1/2 = wharf; 7/8/29 = 19th–22nd ×
  Avenues A–I; 9/10/27 = 22nd–25th × Avenues A–I). The key sheet is on the
  data branch; confirm against it.
- **1885** — from `coverage_prior.COVERAGE["1885"]`: units **7, 9** (A–D),
  **6, 10** (D–G), **5, 11a** (G–J), **3** (D–G, 18–20), **2** (A–D, 16–19),
  plus **sheet 8, the Avenue A wharf strip** — previously excluded as
  "outside crop", now *in* scope because this extent includes the piers.
  Note the panel geometry already recorded there: sheet 3's upper panel is
  off-scale (excluded), sheet 11 is L-shaped and split into 11a/11b.
- **1877** — units **3, 4** (A–D × 20–26), **9, 10** (D–G × 20–26), and
  check **2** (A–D × 17–20) for the 19th–20th band. Sheet 8 is nine
  disconnected panels (excluded); sheet 10 carries a physical tear through
  blocks 441–442 — **retain it, it is authentic**. Expect this edition to
  cover the extent only partially; measure and disclose rather than pad.

Each edition has its own grid pitch and street/avenue numbering scheme —
1899's "corridor slot" model does not transfer unexamined. `config.py`
already carries measured pitches for 1877 (972 × 1135 at 3400 px) and 1885
(1856 × 2170 at 6450 px). Derive 1889's by autocorrelation over all 62
sheets, the same way 1899's was (median 1006 × 1169, IQR ±5).

---

## THE PLAYBOOK — everything the 1899 build learned

Each item names the failure it prevents. All numbers were measured, not
estimated. Full detail with code pointers in `LESSONS.md`.

**1. Verification must be anti-circular.** Fit residuals lie: a uniform
per-sheet placement error is absorbed by the translation term, so sheet 06
sat **114 px** out of place while its residuals read under 15 px. It was
caught only when a human noticed the same hydrant drawn twice. Gate on
**ground-truth landmarks** — the same physical object located on both sheets
of a pair, in native pixels, mapped through the build's own transforms.
`tools/landmark_check.py`; `landmarks.json` is the 1899 set (77 features,
19 pairs) and shows the schema. Build one per edition. A build is not
"aligned" until this gate says so.

**2. Sheets cut at a shared street print NO frame line.** Verified on every
interior edge of all twelve 1899 sheets: content runs to within **2–9 px** of
the paper edge. Frame detectors latch interior block walls instead, and the
seam caps then amputate the frontage band only that sheet draws. In 1899
this silently deleted every south-side address row along 24th Street
(including the CENTRAL HOTEL label), most of 21st east of Market, the
Avenue D and G kerb columns, and the LEVY BLDG walls — and it manufactured a
"void" I spent a revision disclosing as authentic before proving it my own
artifact. **Test every edge** (no dark run > 1500 px anywhere in the 450 px
edge band ⇒ open), then clip open sides by *paper* bounds with measured
insets. See `coverage_prior.FRAME_OPEN_SIDES` and `SCAN_INSETS_1899`.

**3. Edge grid-lines get comb-latched, on both axes.** Wherever a corridor is
cut by the sheet's own paper edge, the whiteness comb settles on a block
frontage or kerb instead of the corridor centre — measured biases **−120 to
+72 px** across 23 edge lines. The instrument that finds them: extrapolate
each sheet's *own interior pitch* to its edge slot and compare. Override
anything off by more than 12 px (`line_overrides`, x and y). This single fix
took the avenues crossing 24th Street from +20/+25/−60 px to **+4/+5/+3**.
Direct measurement of the truncated corridor does *not* work — it picks a
different feature on each sheet.

**4. Owner-on-top; cut at measured paper edges, never inside the corridor.**
Adjacent sheets both print the whole shared street and both facing frontages.
A cut anywhere inside that band destroys something: it slices a frontage row,
or lands between the two copies of a street name and discards both. Lay the
owning sheet over the entire overlap, capped at its measured paper end
(`SEAM_CUTS_1899`'s +177 entry with `trust_frame=False` is the worked
pattern). Labels sit as little as 30 px apart at the wharf — measure the
actual label rows before choosing a cut, and verify by crop afterward.

**5. Close the loop on the lines the eye follows.** Street dashes, kerbs and
corridor centres are what a viewer tracks across a seam. Measure their step
at **every** crossing with a direct dash-row detector (ink fraction 0.08–0.55
plus a transition count — *not* correlation, which returned 0.01–0.26 garbage
on this data), then feed the measurements back as weighted landmark features
so the solver parks unavoidable residual inside block interiors instead of on
the corridors. Verify any new instrument's sign visually **once** before
trusting a table of its numbers.

**6. Bound the solve.** Translations free; per-axis scale hard-capped at
**±0.4%** (±1% let the solver pin two sheets at opposite bounds and warped a
corridor 60 px; unbounded it wanted ±7% — visible distortion bought with
fake improvement). Hold reference-class sheets rigid. Iterate 3 rounds (the
gauge-fixing zero-prior shrinks the first pass by 10–20%). **Apply
corrections to the warp KNOTS, frames, paper bounds and the registration
dump** — writing them only to the fit's translation terms is a silent no-op,
because the renderer warps through the knots.

**7. Some disagreement is in the sources; find out which.** The 1899 wharf
sheets draw the blocks east of Avenue A as schematic rectangles that
disagree with the surveyed downtown drawings by up to ~100 px, and their
junction offsets group cleanly *by wharf sheet* (−55 / +11 / +97, each ±8).
Two engravers also drew the same rail yard with **18 rails on one sheet and
16 on the other** — no registration can reconcile that. Distinguish
*misregistration* (rigid per-pair offset, small spread ⇒ fixable) from
*source disagreement* (varies feature to feature ⇒ disclose). Then: **add
per-sheet rotation/shear to the warp** and solve it from landmarks under the
same bounds discipline — that is the degree of freedom 1899 lacked, and the
one thing that can close its remaining ~15 px junction residuals. Gate it:
if pier-side or any currently-good pair regresses, the rotation is wrong.

**8. Tone: the bands are within-scan, not between-scan.** Sheet paper
*medians* agreed within a few levels while a 230 px edge vignette on one
sheet read as a white bar across the map. Per-sheet gains cannot touch that.
Use the illumination field (two field iterations plus a 1-D row/column
residual pass), and **exclude scanner backing** from the paper mask (min
channel < 225) or the correction inverts at exactly the edges it exists to
fix. Compare paper-only pixels; ink-contaminated region means mislead.

**9. Water fill.** Flood from open water with ink and existing washes as
barriers; the flood *will* leak through linework gaps into yards and
margins, so verify by drawing the region's contour over the map and add
measured exclusion boxes. Fill flat at the sampled waterline colour with a
smoothstep ink blend — a multiplicative tint reproduces every paper gradient
inside the blue and reads as a highlighter outline around mottled water.
`tools/tint_bay.py` carries the whole algorithm; only the region geometry is
per-edition.

**10. Guard metrics on every single change.** Coverage %, pure-white,
pure-black, plus the landmark gate — before and after, every time. Justify
each regression in writing or revert. Note that coverage can be *inflated*
by misregistered overlap, so treat a rise after an alignment fix with the
same suspicion as a fall.

**11. Process.** Checkpoint findings to disk incrementally — agents that
buffered output to the end lost entire runs to session limits. Never report
a measurement a human eye hasn't confirmed is the thing they're pointing at.
When two instruments disagree, the direct-measurement one wins. And when the
reviewer says something looks wrong, measure before defending it: on this
project the human eye beat the automated gates repeatedly, including on the
missing frontage rows, the mottled water and the un-even bay.

---

## THE TEAM

Run a shared setup phase, then one team per edition. Agents measure and
write findings incrementally to disk; they do not editorialize.

- **Registrar** — grid model and pitch, per-sheet registration, the edge
  audits (items 2–3), the bounded landmark solve (6), and the new
  rotation/shear degree of freedom (7).
- **Seam surgeon** — coverage tables, seam policy, cut placement, clip
  windows (4), label-collision checks before and after every cut.
- **Finisher** — illumination flattening, water region and fill, crop,
  caption bars, both poster PDFs (8–9).
- **Adversarial QC fleet** — five independent lenses, each measuring in
  pixels, each writing `findings.json` as it goes: corridor-continuity
  walker, street/junction walker, lettering auditor (sliced/doubled/ghosted
  text), tone auditor, content-integrity auditor (does anything present in a
  source sheet fail to render?). This fleet found what three earlier QC
  passes had missed, including the amputated frontage bands.
- **Steward loop** — after every build: re-run the dash table, the landmark
  gate, the guard metrics and the QC fleet; convert each *confirmed* finding
  into a concrete fix (an override, a landmark feature, a cut, an exclusion
  box); rebuild; repeat. **Stop when every gate passes on two consecutive
  rounds with no new findings** — then package the posters and write the
  production report. Fire any agent that returns unmeasured opinions.

---

## THE BAR — per edition

| Metric | Requirement |
|---|---|
| Surveyed landmark pair means | ≤ 10 px, none > 20 px |
| Street-dash / kerb step at surveyed crossings | ≤ 8 px |
| Source-contradiction crossings | measured, minimized, disclosed with the number |
| Coverage of the extent | the edition's measured achievable maximum |
| Pure-white pixels | ≤ 50 |
| Sliced or doubled display labels | zero |
| Wash hue shift vs source | ≤ 2 levels |
| Water | flat at the sampled waterline colour, no seam bands |
| Generated map content | **none, ever** |

For reference, the delivered 1899 poster measures: median landmark step
24.3 px; wharf pairs exactly (0.0, 0.0); avenues crossing 24th +4/+5/+3 px;
coverage 98.79%; pure-white 7 px. Its documented remaining defects — the
junction residuals, the 13-vs-14 drawn offset, the differing rail counts —
are in `KNOWN_DEFECTS.md`. **Beat them where they are registration; disclose
them where they are the sources' own disagreement.**

## Reporting

One production report per edition, in the format of
`REFERENCE_REPORT_1899.md`: what was built, every correction with its
measurement, seam policy, verification results, and a disclosures section
that states plainly what remains wrong and why. Retract anything an earlier
draft got wrong — that report contains a retraction of my own "authentic
void" claim, and the honesty cost nothing.

## Files in this seed package

| File | What it is |
|---|---|
| `PROMPT.md` | this document |
| `LESSONS.md` | the playbook in full detail, with code pointers |
| `EXTENT.md` | the extent in grid terms, per-edition sheet mappings, source locations |
| `landmarks.json` | 1899's 77 ground-truth features — schema and worked example |
| `constants.json` | 1899 grid constants, anchors, seam list |
| `KNOWN_DEFECTS.md` | the complete measured history, including retractions |
| `REFERENCE_REPORT_1899.md` | the report format and the benchmark numbers |
| `repaired_metrics.json` | 1899's final guard metrics |
| `tools/landmark_check.py` | the anti-circular gate |
| `tools/build_metrics.py` | coverage / white / black guard metrics |
| `tools/tint_bay.py` | water region + flat waterline fill |

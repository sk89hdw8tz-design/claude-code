# Failed experiments and QA-tool bugs — Galveston 1912

Recorded rather than deleted. Prior Galveston editions showed that the failures and
tooling bugs are as valuable to the next edition as the successes.

## F-004 — Automated seam-control harvesting: three variants, none trustworthy (2026-08-17)

**Goal.** Propose, for each of the 17 pairs, the positions of the block-face lines
flanking each crossing street/avenue near the seam — the along-seam control observables.

**Variant 1: low-ink band detection in the seam strip.** Profiled the outermost 12% of
the page. Failed asymmetrically (0 bands on most A-sides): that strip lies largely inside
the blank shared street, so the profile's own statistics collapse — the threshold is
computed from what is mostly emptiness.

**Variant 2: same, but profiled inside the adjacent block strip (0.58–0.88), first with a
mean-relative threshold, then quantile-based.** Better (6, then 8 of 17 pairs plausible)
but unstable: dense CBD strips and sparse residential strips defeat any single relative
threshold in opposite directions, and detection counts flapped between parameter choices.
A detector whose results flap under small parameter changes is not measuring the plates.

**Variant 3: morphological long-line extraction** (open with a long structuring element,
after cross-axis dilation to bridge line wobble; then streets = line pairs a street-width
apart with low ink between). Two failures found by direct diagnosis on the known-good
7–8 pair: (a) the dashed **water-pipe lines drawn down the street centres** merge under
dilation into long runs and are detected as "block-face lines" mid-street — the very
symbols the brief excludes as control; (b) the between-lines ink check became meaningless
because it was computed from the dilated, loose-threshold image (nearly everything reads
as ink, values 0.95+ in genuine streets).

**Conclusion.** On this material, fully automatic harvesting is the wrong tool: every
variant produced confident, well-formed output whose errors were only caught by reading
the plates. The brief's prescription — *manually verified or semi-manually verified
controls* — is adopted as the workflow, not just a review step: automation generates
annotated A/B seam panels and fine-ruled corner crops; a human reads and records every
control coordinate. Scripts retained for the panel/ crop generation only.

## F-001 — Ink-coverage bbox detector reported total nonsense (2026-08-16)

**What was tried.** Bound each plate's drawn content by thresholding the downsampled
grey image at `< 200` and taking rows/columns whose ink fraction exceeded 2%.

**What happened.** Every one of the 13 plates returned `ink fraction = 1.000` and a
content bbox equal to the whole image — i.e. "the entire scan is ink".

**Why.** The LOC scans photograph the sheet on a **dark gridded backdrop**. That
surround is far darker than 200, so the threshold selected the backdrop as "ink"
along with everything else. The detector ran without error and produced confident,
well-formed output that was entirely meaningless.

**Lesson (and the reason this is written down).** This is precisely the failure the
brief warns about: *do not trust a QA tool because it produced output*. The number
was only caught because 1.000 across all 13 sheets is implausible on its face. Any
threshold-based detector on these scans must first isolate the page from the backdrop.

**Superseded by.** Otsu-based bright-region page detection (`detect_pages.py`), which
finds the paper as the dominant bright component against the dark backdrop.

## F-003 — Edge blank-band detector returned its own floor value (2026-08-17)

**What was tried.** For all four edges of the twelve block plates, find the neatline as
the strongest spike within the outer 10%, then scan inward for the first sustained
drafted content, and report the blank street band between them. The purpose was to
decide whether abutting plates each draw about half the shared street (so they tile) or
the full width (so the cut has a choice).

**What happened.** 40 of 48 edges returned a blank band of exactly **8 px** — which is
precisely `neatline + 4` at the analysis downsample, i.e. the smallest value the search
can possibly emit. Only the bay-facing left edges of sheets 7, 9, 11, 12 (and two bottom
edges) returned anything else, and those are the edges with genuine open water or blank
frontage.

**Why.** The neatline is located by `argmax` inside the outer 10% of the profile. Where
the blank street band falls inside that window, the strongest spike is not the border at
all but the first row of drafted content just inside it. The scan then starts already
within content and reports the floor. The failure is silent: every value is a plausible
small integer, and a reader skimming the table would take 8 px as "the plates tile
tightly" — the opposite of a measurement.

**Tell.** The same value repeating across 40 independent edges, and equalling the search's
own lower bound, is a signature of a degenerate estimator rather than a property of the
plates. This is the third detector in this project to fail by producing confident,
well-formed, meaningless output.

**Status.** Not used. `edge_margins.json` is retained only as evidence of the failure and
must not be read as geometry. Needs rework: locate the neatline as the outermost long
*straight continuous run* spanning the full edge, not as a profile maximum, and validate
against hand-measured edges on two or three plates before any value is trusted.

**Not blocking.** The question it was meant to answer is already settled from stronger
evidence — the 1912 street index states outright which side of each boundary street each
plate carries.

## F-002 — Page skew from `cv2.minAreaRect` was a quantisation artefact (2026-08-16)

**What was tried.** Take the page's minimum-area rectangle and use its angle as the
per-sheet scan skew.

**What happened.** 11 of the 13 plates reported skew of **exactly** `+0.000°`; the
other two reported `+0.106°` and `−0.099°`. The rectangle's width/height also came
back transposed on sheet 44 relative to the rest.

**Why.** `minAreaRect` reports its angle on a restricted range and snaps to the axis
for near-axis-aligned rectangles; the width/height ordering is likewise not stable.
Exactly zero, repeated across 11 independent scans, is not a measurement — real
measurements scatter. The page edges are also genuinely unreliable here: these are
sheets from a **bound** volume, so the paper edge is irregular and curled and does
not represent the drafted geometry anyway.

**Lesson.** Do not measure the map from the paper. Measure the map from the map.

**Superseded by.** `measure_grid_angle.py`, which measures the orientation of the
*drafted street grid* via Canny + Hough length-weighted orientation histogram — the
quantity that actually has to agree between neighbours in the common plane.

**Result after the fix.** Grid deviation from the scan axes is under 0.1° on every
plate (spread 0.092°, median concentration 0.994), so the LOC scans are square to the
drafted grid to a high standard. Sheet 5 alone shows low concentration (0.454) — an
explainable outlier, since it is the wharf plate whose piers are drafted diagonally
to the street grid, not an orthogonal-grid sheet at all. Rotation nevertheless stays
**free per sheet** in the fit, per the brief; this measurement tells us the expected
magnitude is small, not that it may be assumed to be zero.

## F-005 — Final render "succeeded" with exit 0 while writing nothing (2026-08-17)

The first full-resolution render run reported success but produced no file: the renderer
does not create its output directory (`--out ../final` on a nonexistent path raised
FileNotFoundError at file-open), and the invoking shell pipeline (`python ... | tail`)
reported *tail's* exit code, masking the Python failure as exit 0. Two lessons, both of
the silent-success family this project keeps meeting: (1) any tool taking an output path
must create it or fail before doing work; (2) never wrap a correctness-bearing command in
a pipeline that swallows its exit status. Rerun with the directory pre-created; QA's
stale/absence guards (hash-stamped artifacts, stability polling) were designed for
exactly this class of failure and would have refused the missing master anyway.

## F-006 — Automated seam-collision detector: confident nonsense, fifth of its kind (2026-08-18)

**Goal.** Find every place where two plates both letter a shared street across a pooled cut, so
the D-018 survey would be exhaustive rather than a spot check.

**Variant 1: ink density along the cut corridor.** Measured ink fraction in a box centred on the
cut, flagging peaks. It reported 5 hits and MISSED both known Ave. F collisions, whose density
(0.078) fell under the threshold: a tangle of thin lettering simply is not dense.

**Variant 2: "both flanking plates ink the same band".** The right idea, wrongly built. It
reported 41 "collision windows" whose positions were suspiciously regular -- they were the
SEGMENT BOUNDARIES where the flanking sheet pair changes, and the huge ink values came from the
plates' dark page edges inside the corridor, not from lettering. It also had west and east
reversed, because the flanking regions were sampled as `cx - n*160` / `cx + n*160` without
accounting for the normal pointing in -x.

**Conclusion.** Reverted to the brief's prescribed workflow: generate readable panels (every
avenue corridor rotated and laid end-to-end in one image) and READ them. That found the five real
collisions in a single pass, and correctly showed the other six avenues clean. The per-plate
ink-cluster measurement was then used only to place each deviation, with a human deciding which
plate keeps its label.

**Tell.** Regularly spaced hits and values dominated by page edges are the signature of a
detector measuring its own scaffolding. Same family as F-001 (threshold caught the scanner
backdrop), F-003 (estimator returned its own floor) and F-005 (exit 0 while writing nothing).

---

## F-007 — The "ink envelope" content frontier (v2/v3)

**Idea.** Replace the density-based frontier with the block plates' own ink envelope: first drawn
ink per row, closed horizontally to bridge dashed track work, opened to drop specks, backed off
20 px. Intended to stop panel blank apron from erasing block track work in the northern yard.

**Why it failed.** Measured per row, the envelope sits at canvas x 7445-7468 for EVERY row from
y 4000 to y 9000 — a dead-straight vertical line. That is not content: it is the block plates'
page-edge line, which is ink by any threshold and is the westernmost ink on almost every row. The
frontier therefore handed the block plates' page margin to the print, and rendered the Pier 22
slip corner twice at two different scales with a hard step between them.

**Tell.** A "content-following" boundary that is constant to within 23 px over 5000 rows is not
following content. Same family as F-001, F-003, F-004 and F-006: the detector measured its own
scaffolding.

---

## F-008 — Min-cost ownership cut with a pure on-ink objective

**Idea.** Choose the ownership boundary as the path minimising the number of rows where it lands
on drawn ink. It scored beautifully: 13 rows out of 3400 (0.4%), against the delivered frontier's
1257 (37.0%), with a maximum row-to-row wander of 2 px.

**Why it failed.** Rendered, it had sliced the compass rose. A dense ornament has blank gaps
BETWEEN its strokes, and the objective rewarded threading them: the cut ran up the middle of the
star, printing a sliver of spokes with the body suppressed. The number was right and the picture
was wrong.

**Fix.** Add a proximity term — ink fraction within +-40 px of the cut — so the boundary prefers
the middle of a wide blank lane and is repelled by ornament and lettering, plus an explicit
protected box for the compass so the choice to keep or drop it is made deliberately rather than
by the optimiser.

**Tell.** An objective defined on the cut's own pixels cannot see a feature it passes through.
Every candidate boundary in D-020 was rendered and looked at before it was believed.

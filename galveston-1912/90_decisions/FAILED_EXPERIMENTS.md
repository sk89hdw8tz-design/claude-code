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

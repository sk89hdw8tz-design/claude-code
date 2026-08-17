# Failed experiments and QA-tool bugs — Galveston 1912

Recorded rather than deleted. Prior Galveston editions showed that the failures and
tooling bugs are as valuable to the next edition as the successes.

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

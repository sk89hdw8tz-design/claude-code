# Experiment log

Techniques attempted, what happened, and why each was kept or rejected. Recorded
so that later work does not repeat a dead end.

---

## 1. UT Libraries `histmap-autogeoref-tools` — REJECTED

Cloned and audited directly. Four defects verified independently, not taken on
the audit agent's word:

| Finding | Verification |
|---|---|
| The committed script does not run | `python -m py_compile georeferencing-automator.py` → `IndentationError: unexpected indent, line 775` (stray editor scratch `h = 4, w =1`) |
| RMSE is not RMSE | L662 `totalsquarederrorft += abs(disterrorft)*2` — doubles rather than squares, so the QA gate admits far larger error than it reports |
| Tesseract config malformed | L170 builds `'--psm 11-c preserve_interword_spaces=1'`; the missing space destroys `-c` and turns the option into a positional argument |
| Output is lossy | L735 writes the GeoTIFF with `COMPRESS=JPEG, JPEG_QUALITY=90` |

Its detector is SSD MobileNet V2 FPNLite **320×320** applied to a whole sheet in
one pass, so one model pixel is 16–28 scan pixels — a hard floor far above this
project's target. The trained model lives behind a Texas Data Repository DOI.

Kept as ideas: cropping a strip *along* the street axis and rotating it so
vertically-set names become horizontal for OCR; grading outputs into accuracy
categories rather than pass/fail. No code reused.

---

## 2. Transform model selection — SIMILARITY, and the reason is not residuals

Measured on the synthetic fixture, where truth is known exactly:

| model | fit median | held-out median | **error vs ground truth** |
|---|---|---|---|
| similarity | 2.43 px | 3.08 px | **3.81 px** |
| affine | **2.09 px** | **3.07 px** | **66.11 px** (max 412) |

Affine won on every residual measure including cross-validated held-out error,
and was 17× worse against truth. Its extra freedom becomes a slow anisotropic
squeeze and shear that neighbouring sheets agree on locally, so tie residuals
never see it while the far corner walks 400 px out of place.

**Residual quality cannot detect this.** Three gates were added as a result:
rank check, physical plausibility, and similarity-by-default. On the real sheets
the plausibility gate did reject an affine solution outright, and rejected a
projective fit whose residuals were the best of any model (0.83 px) while its
sheets were rotated 97° and mirrored.

---

## 3. Per-sheet affine on abutting sheets — REJECTED, rank deficient

Sheets abut along a street, so every tie point on a seam is collinear. Measured
on a 2×2 test network: per-sheet **affine nullity 4**, **similarity nullity 0**.
There is an exact shear of the plane that fixes the seam lines pointwise while
deforming everything between them, and residuals stay near zero throughout.

The projective rank test initially reused the affine design matrix; that is
unsound in the direction that matters (affine having full rank says nothing
about projective's two extra parameters per sheet) and was replaced with a
proper linearised 8-parameter test.

---

## 4. Street-grid detection — three approaches, only the third worked

| approach | result |
|---|---|
| Hough / morphological detection of the dash-dot centre rules | **Failed.** Locks onto the page border and block edges. The avenues are not drawn as continuous rules at all — they are wide bands of bare paper with the name lettered inside |
| Global low-ink band detection + regular-lattice (RANSAC) fit | **Partial.** Found roughly 70% of streets; the lattice never locked on reliably because railways, wharves and parks break the grid |
| **Windowed refinement from an approximate position** | **Adopted.** Identity comes from the printed street name; only position is measured. 7 of 8 bands correct on first pass |

Supporting fixes, each from an observed failure:

* the density window must be **elongated along the band**, or the street's own
  lettering breaks it;
* the density window must be **narrower than the gap being resolved** — a 33 px
  smoothing kernel cannot see a 35 px corridor;
* slopes are **pooled per sheet** (a scan has one rotation), which turned a
  silently tilted Av. A into a visible outlier (moved 205 px vs <80 px);
* the search must be **clipped to the mapped area**, or a boundary street's
  window reaches the blank collar, which is just as ink-free as a street and
  wins;
* "ink on both flanks" was tried as a collar test and **rejected** — a boundary
  street legitimately has blocks on one side only, and those are exactly the
  tie points needed. Replaced by a flatness test: blank paper fits to <1 px
  while a real street band fits to tens of px.

---

## 5. Automatic Sheet 1 panel segmentation — REJECTED, human-defined instead

Measured on the synthetic fixture: the detector **merged** the two genuinely
separate panels on one sheet *and* **invented** a split on another that does not
exist. One miss and one false positive out of eight sheets.

The Sheet 1 split is therefore human-defined and verified against the Key by
block number, not by OCR of a sheet number: the left panel holds blocks 582–585
with the Texas Standard Oil Mill and the I&GN yard, which is exactly the strip
the Key draws on the western bay shore; the right panel holds blocks 742–744.
A heavy printed rule divides them at x≈1560–1568.

---

## 6. Overlap correspondence search (NCC + RANSAC) — REJECTED for the fit

Motivation: sheets 1 and 2 print only one avenue each, so all their centreline
control is collinear.

* Overlap must be computed from **full sheet extents**, not the rendering masks
  — those are cut at the shared centreline and leave zero overlap by design.
* First run: 86 correspondences over 8 pairs. Sheets 1 and 2 yielded almost
  nothing (1 and 0 candidates); widening the search window to ±150 px did not
  help. Sheet 1's map essentially ends at Avenue A, so the shared band is thin
  and largely non-cartographic. **This is a source-data limitation, not a
  processing failure.**
* Adding the correspondences **fixed sheet 1** (scale 1.048→0.975, rotation
  1.51°→0.01°) but **broke sheet 2** (rotation −5.3°). RANSAC had found an
  internally consistent set that was one block out — indistinguishable from a
  good set by score or inlier count.
* A cross-check against the independent centreline solution was added and
  rejected four pairs disagreeing by 2.3–5.4° and up to 48% in scale.
* **Even after filtering, the surviving correspondences made the fit worse**:
  median 4.90 → 5.75 px, p90 48 → 100 px. They are not precise enough to
  contribute. Kept as a catalogue in `gcps/shared_edges/` and as evidence, but
  excluded from the adjustment.

---

## 7. Seam-quality metrics — two are unreliable and are labelled as such

* **Structural step ratio.** Normalising an absolute step by local variation
  explodes over near-blank paper: a half-grey-level difference in paper tone
  reported as a 20× "step". Now withheld unless the absolute step is visible and
  the surroundings have texture. Scan tone difference is reported separately,
  because it is preserved deliberately — no exposure matching is applied.
* **Line bearing difference.** Measures whatever linear structure dominates each
  crop, not a tracked feature. Near a seam one side is often dominated by the
  roadway and the other by block edges, giving differences approaching 90° with
  nothing wrong. Values near 90 mean "different structure either side", not a
  discontinuity. Tracking an identified rail centreline across the seam would be
  the sound version; not implemented.
* **Loop closure reads exactly 0.000 px and this is arithmetic, not quality.**
  A single global adjustment assigns each sheet one absolute transform, so a
  loop composed from them is the identity by construction. The test is only
  informative for sequential pairwise registration. Per-seam residuals are where
  drift actually shows.

---

## 8. Profile cross-contamination — fixed

Intermediates were written to fixed paths with no provenance, so a
`galveston1889` run silently consumed the synthetic fixture's control points and
exited 0. Every intermediate now carries the profile that produced it and is
refused by any other profile.

---

## 9. Mask strategy — paper bounds rejected, centreline cuts adopted

Masking to the paper bounds left each sheet's blank collar in the mosaic, and
the collars painted white bands over neighbouring cartography — the exact
"collars covering neighbouring maps" failure. Masks are now cut **at the shared
street centreline** wherever a neighbour exists, so sheets butt with each
contributing its own half of the roadway; edges with no neighbour run out to the
mapped-area bound so nothing real is trimmed.

The cut positions and the control points must come from the **same** centreline
refinement run. Computed from different runs they disagree by tens of pixels and
the seams reopen.

---

## 10. "Collinear control is the root cause" — WRONG, retracted

Claimed sheets 1/2 failed because their control lies along Avenue A only. The
project's own rank test already contradicted this: per-sheet **similarity has
nullity 0 with collinear ties**; affine has nullity 4. Two separated points
determine a similarity. Collinearity is fatal to affine, not to similarity.

Do not re-raise collinearity as an explanation for a similarity fit.

## 11. Boundary-street recovery — implemented, partially effective

Two seams (S1_main|S2, S27|S29) had **zero** shared control because a sheet's
boundary street sits at the paper edge where the band search is least reliable
and the quality gates discarded it. Recovery predicts the position from the
sheet's own regular pitch and then MEASURES there in a tight window; a
prediction that cannot be measured is refused rather than recorded as an
observation. Re-running with different gate parameters produced a *worse*
control set overall (83 vs 95 observations), so the 06b set was retained.

## 12. Street-direction constraints — implemented; they expose an evidence conflict

A street drawn on two sheets must run the same way on both. Encoded as a
synthetic correspondence at a 2500 px lever arm from a genuine shared
intersection, pooled over 3–4 streets per sheet.

| solution | real-tie median | direction disagreement | scale spread |
|---|---|---|---|
| intersections only | 5.60 px | — | 4.62% |
| + direction (high) | 14.96 px | 0.189° | 0.83% |
| + direction (low) | 7.18 px | 1.152° | 4.29% |

The classes are mutually inconsistent — directions agree to 0.19°, positions to
5.6 px, and both cannot hold. Residuals must be reported **per class**: a small
angular error becomes a large displacement at a long lever arm, so a combined
median is meaningless.

## 13. Grid-pitch scale check — THE decisive measurement

Pixels per one numbered-street step, on eight sheets of one edition at one
nominal scale scanned to near-identical dimensions, should agree to a fraction
of a percent. Measured spread: **8.24%** (1102–1193 px), larger than either
transform solution's scale spread.

**Therefore the binding constraint is control-point measurement precision** —
several percent, consistent with per-band fit rms of 20–110 px — not the
transform model, not topology, not collinearity. This explains why adding more
automatic correspondences made things worse rather than better, and it means no
amount of further automatic matching of the same kind will fix the failing
seams.

---

## 14. Printed scale bars — MEASURED, and they settle the scale question

The previous entry claimed an 8.24% grid-pitch spread was "physically
impossible" for sheets of one edition. **That claim was wrong and is retracted.**
It conflated the printed map with the digital file: UT's eight JPEGs may have
been independently scanned, cropped, deskewed or resized, so equal nominal
printed scale does NOT imply equal pixels per block. Scale had to be *measured*,
not assumed.

Measured directly off the printed "Scale of Feet" bars at 3x zoom, reading the
0/50/100/150 ft ticks and converting back to source pixels:

| sheet | px per foot | vs nominal (1 in = 100 ft at 300 dpi = 3.000) |
|---|---|---|
| 1 | 3.050 | +1.7% |
| 2 | 3.071 | +2.4% |
| 9 | 3.052 | +1.7% |

**Spread across the measured sheets: 0.68%.** Each sheet is internally
consistent too — sheet 9's 0–100 span gives 3.045 and its 0–150 span 3.052;
sheet 2 gives 3.077 and 3.071.

Independent corroboration: 3.05 px/ft at 300 dpi is 1 inch ≈ 98 ft, i.e. the
standard Sanborn 1 inch = 100 feet, +2% for paper and scanning. These are
ordinary 100 ft/inch sheets scanned at 300 dpi.

Now convert the disputed grid pitch through the measured scale:

| sheet | pitch px | ÷ px/ft | ft per street step | vs expected 380 ft |
|---|---|---|---|---|
| 9 | 1150 | 3.052 | 377.0 | −0.8% |
| 1 | 1193 | 3.050 | 391.2 | +3.0% |
| 2 | 1102 | 3.071 | 359.0 | **−5.5%** |

Expected is a 300 ft block plus an 80 ft street = 380 ft. Sheet 9 lands within
1%; sheet 2 is 5.5% short.

**Conclusion, on measured evidence rather than assumption: the digital scans
DO share a common scale to better than 1%, so the 8.24% pitch spread is error in
the street-band detector — not genuine per-sheet digital resizing.** A
common-scale prior is therefore justified, but it is justified by the scale
bars, not by belonging to the same edition.

This also explains the direction-constraint conflict in entry 12: the
direction-constrained solution collapsed the scale spread to 0.83%, which is
almost exactly the 0.68% the scale bars independently show. The direction
evidence was pulling toward the truth; the intersection positions were pulling
away from it.

---

## 15. All eight scale bars, measured twice — and why the result does NOT do what entry 14 hoped

Entry 14 measured the printed "Scale of Feet" bar on three sheets and concluded
that a common-scale prior on the sheet bodies was justified. All eight sheets
have now been measured, twice, by two independent procedures:

* **pass A** — one examiner per sheet, reading tick centres by eye at 16–30×
  zoom on a 1-source-pixel grid overlay;
* **pass B** — one reviewer over all eight sheets with a single automated
  method (morphological location of the bar, robust line fit to its top edge to
  absorb tilt, ink integration in an 8-row band above that edge so the numerals
  and bar body are excluded, background-subtracted intensity centroid per tick).

The two passes agree to **0.10 % or better on every sheet**. The bar itself is
measured about as well as this material allows.

| sheet | 1 | 2 | 7 | 8 | 9 | 10 | 27 | 29 |
|---|---|---|---|---|---|---|---|---|
| adopted px/ft | 3.0297 | 3.0576 | 3.0570 | 3.0269 | 3.0295 | 3.0487 | 3.0735 | 3.0397 |

Mean 3.0453 px/ft, spread **1.53 %**, every sheet ~1–2.5 % above the nominal
3.000 px/ft of a 1 in = 100 ft plate scanned at 300 dpi. (Entry 14's three
numbers were 0.5–0.7 % high against these; the coarser method, not new sheets.)

**The bar is one engraving, reused.** Normalising each sheet's four 50-ft
interval lengths by their own mean gives the *same* irregular pattern on all
eight sheets to ±0.3 %: ≈ [0.999, 1.002, 1.008, 0.991]. That is a shared
engraving defect reproduced on every plate, not per-sheet measurement noise. So
differences in measured px/ft between sheets are real differences in how the
*page* was reproduced and scanned.

**And that is exactly why it cannot be used as a prior on the map body.**
Compare the bar against a long baseline measured in the drawing itself:

| pair | body scale ratio | scale-bar ratio | contradiction |
|---|---|---|---|
| S9 / S7 | 1.0161 (Av. B → Av. D, 1976 px) | 0.991 | **2.65 %** |
| S29 / S27 | 1.00075 (6 curb/jamb x, rms 2.4 px) | 0.989 | **1.24 %** |

The bar and the body disagree, and they disagree in *opposite directions* on
S7/S9. The bar measures page reproduction; the body measures what the
draughtsman drew. These plates were drawn by hand, and a block laid out as
"300 ft" is not 300.0 ft on every plate.

**Adopted:** the per-sheet similarity scale stays FREE, determined by verified
correspondences. No common-scale prior, no scale-bar prior. Entry 14's
corollary — that the direction-constrained solution's 0.83 % scale spread
"matched" the bars — is withdrawn: it matched a quantity that turns out to
measure something else, on three sheets out of eight.

**Retained from entry 14:** the scans are ordinary, and nothing about them is
physically impossible. That much the bars do establish.

---

## 16. Semantic identification, then measurement — the approach that finally worked

Every automatic correspondence method tried on this material failed the same
way (entries 5, 11, 12): on a repeating street grid, a matcher that searches
finds a confident wrong answer, and adding more of its output makes the fit
worse. The replacement is the opposite order of operations:

1. **identify** the feature from printed evidence — a lettered avenue name, a
   block number, a water-main diameter and the exact point where the main
   changes size, a named building, the terminal end of the drawn area, a
   corridor width that is 70 ft where its neighbours are 20 ft;
2. **argue** why it cannot be one block off, in writing, per point;
3. **measure** it sub-pixel on a 1-source-pixel grid overlay;
4. **state an honest σ** for that measurement.

Result on the seams re-measured this way, against the same seams under the old
automatic control:

| seam | old median | new median (geometric control) |
|---|---|---|
| S7 \| S9 | 22.99 px FAIL | **4.72 px** |
| S10 \| S9 | 36.05 px FAIL | **2.97 px** |
| S27 \| S29 | no shared points at all | 16 correspondences at ±4 px |
| S1_main \| S2 | no shared points at all | 3 correspondences at ±5 px |

The number of points did not go up much. Their *identification* went from
searched to argued.

---

## 17. Two classes of control, and grading a seam on the wrong one condemns a correct map

Fire plugs looked like ideal tie points: small, discrete, unambiguous symbols
printed on both plates of a seam. They are not. Measured on S7 | S9:

| point | σ stated | residual |
|---|---|---|
| block corner, Strand × 22nd, SW | 3.5 px | 0.77 px |
| block corner, Strand × 22nd, NE | 3.0 px | 1.97 px |
| water-main tee, 6-in. alley main | 5.0 px | 2.35 px |
| **fire plug, west end of 22nd St** | 10 px | **37.31 px** |
| **fire plug, east of the 6-in. main** | 14 px | **46.38 px** |

The Sanborn draughtsman placed a hydrant symbol by eye *somewhere in the
street*; he did not survey it. The same plug is drawn up to 46 px — about
15 ft — apart on two plates of one edition. No transform can remove that, and
it is not a defect in the reconstruction.

Including these in the seam grade turned a genuinely good seam into a FAIL
(median 5.39 px, max 46.38 px). Control is therefore split:

* **geometric** — corners, property lines, pipe junctions, termini: places
  where two drawn *lines* meet. Both draughtsmen were copying one survey, so
  these must agree. Seams are graded on these alone.
* **symbol** — plugs, hydrants, valve discs. Kept in the solve at their honest
  (large) σ, where 1/σ² makes them nearly weightless, and reported separately
  as *drafting scatter*. Never graded.

With the split, the same S7 | S9 solve reads median 4.72 px / max 7.34 px on
7 geometric points, with the 5 symbols reported alongside as 9/46 px scatter.
The mosaic cuts at the shared street centreline, so only one plate's hydrant
survives and the scatter is never visible in the output.

This is the same lesson as entries 6 and 12 in a third form: **the residual is
only as meaningful as the observation it is computed from.**

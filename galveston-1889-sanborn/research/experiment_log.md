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

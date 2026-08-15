# Checkpoint — Galveston 1889 selected-sheet reconstruction

State at the end of the UltraCode continuation session. Everything below is
measured, not asserted. **The reconstruction is NOT final and must not be
labelled final.**

---

## 1. The root cause, corrected twice

**First diagnosis (WRONG):** "sheets 1 and 2 have collinear control along
Avenue A; that is the root cause."

That was wrong and the project's own rank test already said so: per-sheet
**similarity has nullity 0 with collinear ties** (affine has nullity 4). Two
separated points determine a similarity. Collinearity is fatal to affine, not
to similarity. The user was right to challenge it.

**Second diagnosis (partly right, incomplete):** two seams had *zero* shared
control. Confirmed by inspection of the control set:

| seam | shared point ids |
|---|---|
| S1_main \| S2 | **NONE** |
| S27 \| S29 | **NONE** |
| S2 \| S9 | 1 (`22nd\|A`) |
| S7 \| S9 | 4, all on 22nd Street |
| S10 \| S9 | 4, all on Avenue D |

Sheet 1 lost its 22nd Street and sheet 29 lost its 22nd/20th to the quality
gates, because a sheet's **boundary** street lies at the very edge of the paper
where the band search is least reliable. A seam with no shared observation
cannot be measured, let alone solved.

**Third and actual root cause (MEASURED):** the control-point measurement
itself is not accurate enough.

Independent evidence — the **grid pitch**, i.e. pixels per one numbered-street
step. This is a fixed ground distance, on eight sheets of one edition, drafted
at one nominal Sanborn scale, scanned on the same equipment to near-identical
pixel dimensions (3400 × ~4100 px, 300 dpi). Their true relative scale should
agree to a fraction of a percent. Measured:

| region | px per street step | implied relative scale |
|---|---|---|
| S1_main | 1193.23 | 1.0269 |
| S2 | 1102.37 | **0.9487** |
| S7 | 1170.29 | 1.0072 |
| S8 | 1138.42 | 0.9797 |
| S9 | 1150.46 | 0.9901 |
| S10 | 1172.77 | 1.0093 |
| S27 | 1153.61 | 0.9928 |
| S29 | 1188.84 | 1.0231 |

**Spread: 8.24%.** — SUPERSEDED, see section 6. Calling this "physically
impossible" was wrong: it assumed the digital files share a scale, which had to
be measured rather than assumed. It has since been measured, and the conclusion
survives for a better reason. It follows that the
street-band positions carry systematic errors of several percent — consistent
with the per-band fit rms of 20–110 px already logged.

**Conclusion: the binding constraint is control-point measurement precision,
not the transform model, not the network topology, not collinearity.** Adding
more correspondences of the same kind cannot fix this, which is exactly why the
overlap-matching experiment made the fit worse.

---

## 2. Direction constraints — implemented, and they expose the conflict

A street drawn on two sheets is the same street and must run the same way on
both. Pooled over 3–4 streets per sheet and anchored at a genuine shared
intersection, this was encoded as a synthetic correspondence at a 2500 px lever
arm (`gcps/tiepoints_direction.csv`, 32 observations over 8 shared-line
families; definitions in `config/line_constraints.yaml`).

Result, with residuals reported **separately by class** because a small angular
disagreement becomes a large displacement at a long lever arm:

| solution | real-tie median | direction disagreement | scale spread | rotation spread |
|---|---|---|---|---|
| intersections only | **5.60 px** | — | 4.62% | 2.08° |
| + direction (high weight) | 14.96 px | 0.189° | **0.83%** | **1.17°** |
| + direction (medium) | 13.84 px | 0.757° | 2.25% | 1.24° |
| + direction (low) | 7.18 px | 1.152° | 4.29% | 1.85° |

**The two evidence classes are mutually inconsistent.** Street directions on
adjacent sheets agree to 0.19°; intersection positions agree to 5.6 px; you
cannot satisfy both. Forcing directions to agree drives intersection residuals
to 15 px, and vice versa. Given the 8.24% pitch spread, the intersection
positions are the less trustworthy of the two.

Notably the direction-constrained solution is the more **physically
defensible**: it collapses the scale spread to 0.83% and removes sheet 1's
suspicious +1.51° rotation (→ −0.40°). This is the same lesson as the earlier
affine-vs-similarity finding — **residuals are not the arbiter of correctness.**

Candidate transforms saved to `working/transforms_candidate.json`
(direction weight chosen by best real-tie median = low) and
`working/transforms_with_direction.json` (high weight).

**Neither has been accepted.** Choosing between them requires control points
whose accuracy is known, which is exactly what is missing.

---

## 3. What is solid and must not be re-derived

* **Topology** — verified from the 1889 Key read at magnification *and*
  reciprocated continuation notes on all ten adjacencies. Row A (19th–22nd St):
  2, 7, 8, 29. Row B (22nd–25th St): 1, 9, 10, 27. West is the bay.
  Sheet 8's right-edge note is **No 29**, not "No 28" (low-resolution misread,
  corrected at full resolution).
* **Sheet 1** — two panels confirmed by block numbers against the Key, not OCR:
  left panel blocks 582–585 (Texas Standard Oil Mill, cattle yards, I&GN yard,
  43rd–45th St) is EXCLUDED; right panel blocks 742–744 (harbour, 22nd–25th St,
  Av. A or Water E.) is RETAINED. Divider is a heavy printed rule at x≈1560–1568.
* **Model** — similarity. Affine is rank deficient on seam-line-only ties
  (nullity 4 vs 0) and, on the synthetic fixture with known truth, beat
  similarity on every residual measure while being 17× worse against truth.
* **Originals** — untouched, verified byte-identical after every run.

---

## 4. Seam status (unchanged, still failing)

`output/qc/seam_matrix.csv` — **9 REVIEW, 5 FAIL**. No seam is unreviewed.
The failures are all explained by section 1.

Two QC metrics are documented as unreliable and must not be quoted as results:
loop closure reads exactly 0.000 px **by construction** (a global solve gives
each sheet one absolute transform, so any loop composes to identity), and the
line-bearing metric measures whichever structure dominates each crop, so values
near 90° mean "different structure either side", not a discontinuity.

---

## 5. The next step that would actually work

Not more automatic correspondences — that has been tried three ways and
documented as failing. What is needed is **a small number of control points
whose accuracy is a few pixels**, which on this material means human-placed
points on unambiguous, non-repeating features:

* wharf and basin corners on sheets 1 and 2 (unique shapes, not grid-repeating)
* the railroad crossing points at Avenue A
* named building corners printed on both sheets of a seam
* the printed scale bar on each sheet, measured directly, to pin relative scale

Three exact correspondences per seam at 2–3 px would outperform everything
attempted so far. The `manual` control path already exists: add rows to
`gcps/tiepoints_manual.csv` with `selected_by` and `reason`, and re-run from
step 06.

Until then the geometry has not passed and the master should not be regenerated.


---

## 6. Printed scale bars — measured, and they settle it (supersedes section 1)

Measured off the printed "Scale of Feet" bars at 3x zoom:

| sheet | px/ft | vs nominal 3.000 (1 in = 100 ft at 300 dpi) |
|---|---|---|
| 1 | 3.050 | +1.7% |
| 2 | 3.071 | +2.4% |
| 9 | 3.052 | +1.7% |

**Spread 0.68%.** The scans share a digital scale to better than 1%, and all sit
~2% above the standard Sanborn 100 ft/inch — ordinary sheets, ordinary scanning.

Converting the disputed grid pitch through the measured scale gives feet per
numbered-street step, against an expected 380 ft (300 ft block + 80 ft street):
sheet 9 → 377.0 ft (−0.8%), sheet 1 → 391.2 ft (+3.0%), sheet 2 → 359.0 ft
(−5.5%).

**So the 8.24% pitch spread is street-band detector error, established on
measured evidence rather than on an assumption about editions.** A common-scale
prior is justified — by the scale bars.

Corollary: the direction-constrained solution's 0.83% scale spread closely
matches the 0.68% the scale bars show independently. The direction constraints
were pulling toward the truth and the intersection positions away from it, which
inverts the earlier reading of that experiment.

# Checkpoint — Galveston 1889 selected-sheet reconstruction

Everything below is measured, not asserted. **The reconstruction is NOT final
and must not be labelled final.** Section 9 lists exactly what is still open.

---

## 1. Where the geometry stands

Ten topology adjacencies, all ten carrying verified control. One joint
similarity solve over eight regions, anchored at S9, weighted by 1/σ² with
per-axis uncertainties.

| | |
|---|---|
| correspondences | 105 (99 graded, 6 ungraded) |
| overall median residual | **2.63 px** |
| held-out (5-fold) median | 3.44 px |
| seam matrix | **10 PASS, 0 REVIEW, 0 FAIL** |
| coverage | 88.2% of the output grid |
| plausibility | every region within limits; no mirroring, shear or gross scale |

| seam | n | median | max | n/σ | verdict |
|---|---|---|---|---|---|
| S10 \| S27 | 7 | 1.50 | 5.58 | 0.50 | PASS |
| S27 \| S29 | 16 | 2.15 | 5.07 | 0.54 | PASS |
| S10 \| S8 | 15 | 2.08 | 8.19 | 0.68 | PASS |
| S1_main \| S9 | 7 | 2.45 | 13.31 | 0.93 | PASS |
| S1_main \| S2 | 3 | 2.83 | 3.96 | 0.59 | PASS |
| S29 \| S8 | 8 | 3.09 | 8.83 | 0.67 | PASS |
| S10 \| S9 | 6 | 3.20 | 8.03 | 0.36 | PASS |
| S7 \| S8 | 7 | 3.30 | 5.32 | 0.66 | PASS |
| S2 \| S7 | 7 | 3.29 | 7.05 | 0.94 | PASS |
| S7 \| S9 | 23 | 4.94 | 12.87 | 1.51 | PASS |

Per-region geometry, with 1σ formal errors from the normal equations — these
say whether the DATA could pin a parameter down, which residuals cannot:

| region | scale | ±% | rotation | ±deg |
|---|---|---|---|---|
| S1_main | 0.99133 | 0.087 | −0.792° | 0.050 |
| S2 | 0.99993 | 0.099 | −0.989° | 0.057 |
| S7 | 1.01220 | 0.052 | −0.545° | 0.030 |
| S8 | 1.00564 | 0.081 | −0.186° | 0.054 |
| S9 | 1.00000 | — | 0.000° | — (anchor) |
| S10 | 0.99839 | 0.086 | −0.003° | 0.060 |
| S27 | 0.99648 | 0.105 | −0.099° | 0.092 |
| S29 | 0.99596 | 0.103 | +0.619° | 0.091 |

Leave-one-seam-out — remove a seam entirely and predict it from the rest of
the network — gives observed-over-predicted misclosure ratios of 0.26 to 2.31.
Only S7 | S9 exceeds 2, and it does so because 23 correspondences now pin both
its plates so tightly that the network predicts them to 3.2 px, against
genuine local drafting variation on that seam of 0.999–1.028 in scale.

---

## 2. What replaced the failed approach

Every automatic correspondence method tried on this material failed the same
way: on a repeating street grid a matcher that *searches* finds a confident
wrong answer, and adding more of its output made the fit worse. The
replacement inverts the order of operations — **identify, then measure**:

1. identify the feature from printed evidence (a lettered avenue name, a block
   number, the exact point where a water main changes diameter, a named
   building, a corridor that is 70 ft where its neighbours are 20 ft);
2. argue in writing why it cannot be one block off;
3. measure it sub-pixel on a 1-source-pixel grid overlay;
4. state an honest σ.

Against the same seams under the old automatic control:

| seam | old | new |
|---|---|---|
| S7 \| S9 | 22.99 px FAIL | 4.94 px, 23 points |
| S10 \| S9 | 36.05 px FAIL | 3.20 px |
| S27 \| S29 | no shared points at all | 2.15 px, 16 points |
| S1_main \| S2 | no shared points at all | 2.83 px, 3 points |

The point count barely rose. Their *identification* went from searched to
argued.

---

## 3. Three classes of observation, and only one is graded

* **geometric** — corners, property lines, pipe junctions: places where two
  drawn *lines* meet. Both draughtsmen copied one survey, so these must agree.
  Seams are graded on these alone.
* **symbol** — fire plugs, hydrants, valve discs. Placed by eye; the same plug
  is drawn up to 46 px (15 ft) apart on two plates of one edition. Kept in the
  solve at honest σ, where 1/σ² makes them nearly weightless. Never graded.
* **loose** — anything, of any category, whose declared σ exceeds the 15 px
  max gate. A water-main tee offered at ±45 px is a semantic confirmation of
  *which* crossing it is, not a claim about position; grading a 15 px gate on
  it would judge a measurement against a precision it never asserted.

Water mains are now dead as control on four independent measurements: the same
pipe crosses at 0.42 vs 0.62 of the street width, 29–67 px apart.

---

## 4. The scale question, settled and then re-settled

All eight printed scale bars measured twice, by an examiner per sheet and by
one uniform automated pass over all eight. **They agree to 0.10% or better on
every sheet.** Adopted values span 3.0269–3.0735 px/ft, a 1.53% spread.

**The bar is one engraving, reused.** Normalising each sheet's four 50-ft
intervals by their own mean gives the same irregular pattern on all eight to
±0.3%. So it faithfully measures how the *page* was reproduced.

**And that is exactly why it cannot govern the drawing.** Against a long
baseline measured in the map body itself:

| pair | body ratio | scale-bar ratio | contradiction |
|---|---|---|---|
| S9 / S7 | 1.0161 | 0.991 | 2.65% |
| S29 / S27 | 1.00075 | 0.989 | 1.24% |
| S7 / S2 | 0.988 (block depths) | 1.0000 | 1.19% |

They disagree, and on S7/S9 in opposite directions. **No common-scale prior,
no scale-bar prior; the per-sheet scale stays free.**

---

## 5. Isotropy, and a calibration error of my own

S7|S8 reported sheet 7 as ~4% anisotropic, which would have forced abandoning
the similarity. It does not survive, but neither did my first rebuttal of it.

**My error (retracted).** I calibrated x from the grid pitch, taking
Av. B → Av. C *west frontage to west frontage* as 330 ft. That step crosses
Av. B, the 80 ft Strand, so it is **340 ft**. Reading 340 as 330 inflated
px/ft in x by 1.5% and made every avenue convert too narrow — hence a
short-lived claim that "avenues are drawn 3% narrow, streets true". A
scale-free test (drawn width ÷ drawn 330 ft pitch, against 70/330, using no
px/ft at all) puts ten 70 ft avenues at **69.4–70.3 ft** and the Strand at
79.8/80.8. **Avenues and streets alike are drawn true.**

**The anisotropy claim (also rejected).** Measured with correct east-to-east
intervals, the sheets appear anisotropic by 0.6–3.5%, and a correction to
sheet 7's x scale was recommended. Applying it would have distorted the
mosaic. A per-plate anisotropy is a property of the plate; a wrong block
dimension is a property of the ground — and the sheets come in vertically
adjacent pairs covering the same avenues, so the predictions separate:

| column | sheets | anisotropy | implied E–W block |
|---|---|---|---|
| Av. A–D | 7, 9 | 2.84% | **269.5 ft** |
| Av. D–G | 8, 10 | 0.75% | 262.5 ft |
| Av. G–J | 27, 29 | 1.01% | 263.4 ft |

Spread within a column 0.63%, between column means 2.09%. It tracks the
geographic column, not the plate: the harbour blocks are about 7 ft wider
east–west than the assumed 260 ft. The seams say the same more bluntly —
S2 | S7 spans 3512 px with a 7.05 px maximum residual, where a 3.6% x-scale
error would put roughly 126 px.

**Similarity stands.** Affine remains refused: rank deficient on
seam-line-only ties (nullity 4 vs 0), and on the synthetic fixture it beat
similarity on every residual measure while being 17× worse against truth.

---

## 6. The one systematic this control cannot see from the inside

Sheets abutting along a lettered avenue share **no inked ground**: each plate
draws only its own frontage and the roadway between is drawn by neither. Their
ties are constructed by stepping half the street width inward, so a wrong step
biases that seam identically at every point — invisible in its own residuals.

Two things were done about it:

* **Per-axis uncertainties.** The across-seam coordinate of a constructed tie
  carries an inflated σ while the along-seam coordinate keeps its measured
  one. Leave-one-seam-out misclosure on S10|S8 fell 2.04σ → 1.40σ, and S10|S9
  went from an untestable bridge to a testable seam.
* **An independent width test** (§7).

Leave-one-seam-out is the honest loop closure. Composing transforms around a
cycle of a global solve returns 0.000 px *by construction*; removing a whole
seam and predicting it from the rest does not.

---

## 7. Street width after assembly

Where observers identified corners on **both** property lines of a shared
street, their separation in the reconstruction plane is the width, measured
from identified features rather than detected ink:

| seam | measured | expected | error | |
|---|---|---|---|---|
| S9 \| S7 | 80.1 ft | 80.5 | −0.5% | PASS |
| S27 \| S29 | 81.5 ft | 80.5 | +1.2% | PASS |
| S10 \| S8 | 83.1 ft | 80.5 | +3.2% | PASS |

The other seven share no inked ground and are reported **NOT TESTABLE** rather
than given an invented number.

An ink-profile version of this test was built and **rejected**: its answer
moved 15% when the search window changed width, because a party wall or a
block of lettering is darker than a street frontage line. Retained as an
opt-in diagnostic, never a gate.

---

## 8. Metrics that must not be quoted as results

* **Loop closure by composition** — 0.000 px by construction. Superseded by
  leave-one-seam-out.
* **Line-bearing difference** — reads whichever structure dominates each crop,
  so a value near 90° means "different structure either side", not a
  discontinuity. Demoted from a gate to informational; using it as a gate is
  what flooded the earlier matrix with REVIEW verdicts.
* **`street_width_discrepancy`** in the seam matrix — same family, same
  problem. Superseded by §7.
* **Ink-profile street width** — see §7.

---

## 9. What is still open

1. **Seven of ten seams have no independent width verification** (§7). They
   share no inked ground, so their across-seam placement rests on the printed
   width. Measuring the drawn avenue widths showed the printed figure is right
   to within 0.13–0.18 px in the relative sense, so no correction is warranted
   — but that is a bound on one mechanism, not a verification of the placement.
2. **The 129 native-resolution panels are generated but only spot-inspected.**
   Five have been examined. A systematic pass over all of them has not been
   done, and it is the one acceptance criterion in the brief that remains
   substantially unmet.
3. **No modern georeferencing has been attempted.** The historical
   reconstruction is the primary product and is deliberately finished first.
4. **S7 | S9 misclosure is 2.31× predicted** — the only seam above 2. Its
   cause is identified (local drafting scale varying 0.999–1.028 within the
   seam, which no similarity can absorb) but not itself independently
   confirmed.
5. **The 260 × 300 ft plat block is an assumption**, inherited rather than
   measured from an external source. §5 shows the east–west figure is wrong
   for the harbour column; the north–south 300 ft is better supported (every
   sheet returns 3.05–3.10 px/ft in y) but rests on the same source.

---

## 10. Solid, and not to be re-derived

* **Topology** — verified from the 1889 Key at magnification *and*
  reciprocated continuation notes on all ten adjacencies. Row A (19th–22nd
  St): 2, 7, 8, 29. Row B (22nd–25th St): 1, 9, 10, 27. West is the bay.
  Sheet 8's right-edge note is **No 29**, not "No 28" (a low-resolution
  misread, corrected at full resolution).
* **Sheet 1** — two panels confirmed by block numbers against the Key, not by
  OCR: left panel (blocks 582–585, Texas Standard Oil Mill, cattle yards, I&GN
  yard, 43rd–45th St) is EXCLUDED; right panel (blocks 742–744, harbour,
  22nd–25th St) is RETAINED. Divider is a heavy printed rule at x≈1560–1568.
  The polygon is hand-verified and tracked in git — it was destroyed once this
  session by regenerating masks from scratch and recovered from version
  control, which is why mask polygons are tracked.
* **Mask cuts** come from the verified control, never from the street-band
  detector. Both sheets of a seam are cut on the same plane line, so they butt
  with no overlap and no gap. The cut is idempotent and byte-reproducible.
* **Originals** — untouched, verified by SHA-256 against
  `data/original/INVENTORY.json`.
* **Privacy** — zero image files in the working tree and none ever added
  anywhere in git history, verified with `--diff-filter=A` across all refs.

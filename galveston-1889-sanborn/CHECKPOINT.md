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
| correspondences | 92 (87 graded, 5 ungraded) |
| overall median residual | **2.82 px** |
| held-out (5-fold) median | 3.89 px |
| seam matrix | **9 PASS, 1 REVIEW, 0 FAIL** |
| coverage | 88.2% of the output grid |
| plausibility | every region within limits; no mirroring, shear or gross scale |

| seam | n | median | max | n/σ | verdict |
|---|---|---|---|---|---|
| S10 \| S27 | 7 | 1.50 | 5.57 | 0.50 | PASS |
| S10 \| S8 | 15 | 2.02 | 8.25 | 0.67 | PASS |
| S27 \| S29 | 16 | 2.17 | 5.09 | 0.54 | PASS |
| S1_main \| S9 | 7 | 2.39 | 13.35 | 0.90 | PASS |
| S1_main \| S2 | 3 | 2.57 | 4.44 | 0.67 | PASS |
| S7 \| S8 | 7 | 3.32 | 5.41 | 0.67 | PASS |
| S29 \| S8 | 8 | 3.15 | 8.88 | 0.68 | PASS |
| S2 \| S7 | 7 | 3.37 | 7.16 | 0.96 | PASS |
| S10 \| S9 | 6 | 4.28 | 8.66 | 0.44 | PASS |
| **S7 \| S9** | 10 | **5.29** | 10.92 | 1.09 | **REVIEW** |

Per-region geometry, with 1σ formal errors from the normal equations — these
say whether the DATA could pin a parameter down, which residuals cannot:

| region | scale | ±% | rotation | ±deg |
|---|---|---|---|---|
| S1_main | 0.99146 | 0.084 | −0.783° | 0.049 |
| S2 | 1.00053 | 0.135 | −0.856° | 0.077 |
| S7 | 1.01250 | 0.113 | −0.416° | 0.064 |
| S8 | 1.00268 | 0.194 | −0.238° | 0.111 |
| S9 | 1.00000 | — | 0.000° | — (anchor) |
| S10 | 0.99574 | 0.184 | −0.048° | 0.106 |
| S27 | 0.99372 | 0.194 | −0.149° | 0.112 |
| S29 | 0.99325 | 0.195 | +0.564° | 0.113 |

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
| S7 \| S9 | 22.99 px FAIL | 5.29 px |
| S10 \| S9 | 36.05 px FAIL | 4.28 px |
| S27 \| S29 | no shared points at all | 2.17 px, 16 points |
| S1_main \| S2 | no shared points at all | 2.57 px, 3 points |

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

## 5. Isotropy — the finding that saved the model

S7|S8 reported sheet 7 as ~4% anisotropic, which would have forced abandoning
the similarity. It is an artifact of calibrating x against printed avenue
widths.

Testing with **grid pitch**, which needs no printed width at all — the
Galveston plat fixes avenue pitch at 260+70 = 330 ft and street pitch at
300+80 = 380 ft — sheet 9 gives 3.0429 px/ft in x and 3.0651 in y:
**isotropic to 0.73%**. Against that scale:

| feature | measured | printed | |
|---|---|---|---|
| 22nd St (horizontal) | 80.5 ft | 80 ft | +0.6% |
| Av. B | 77.2 ft | 80 ft | −3.5% |
| Av. C / Av. D | 68.0 ft | 70 ft | −2.8% |

**Streets are drawn true; avenues are drawn ~3% narrow.** Similarity stands.
Affine remains refused: it is rank deficient on seam-line-only ties (nullity 4
vs 0) and on the synthetic fixture beat similarity on every residual measure
while being 17× worse against truth.

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

1. **S7 | S9 at 5.29 px** is the last REVIEW seam. An independent second pass
   is running, aimed at the doubling that worked on S8|S10 (both plates draw
   the full 80-ft roadway — own kerb as block frontage, far kerb as the outer
   rule of the continuation boxes — which yields 14 corners instead of 7).
2. **Seven seams have no independent width verification** (§7). The drawn
   avenue widths are being measured on every sheet so the three
   printed-width constructions can be rebuilt from measurement.
3. **The 129 native-resolution panels are generated but only spot-inspected.**
   A systematic pass over all of them has not been done.
4. **No modern georeferencing has been attempted.** The historical
   reconstruction is the primary product and is deliberately finished first.
5. **`tests/validate_against_truth.py` has no profile guard** — it reads
   `working/transforms.json` blindly and will happily compare Galveston
   transforms against synthetic truth. Every other script uses
   `require_profile`; this one should too.

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

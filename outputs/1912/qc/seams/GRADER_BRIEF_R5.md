# Seam census grader brief (1912 Galveston Sanborn mosaic, round 5 — final)

You are grading seams of a mosaic built from 1912 Sanborn fire-insurance
plates. Each seam is where two plates meet; a thin red tick in the margins
marks where the cut crosses the crop edge. The map pixels are untouched
scans: nothing is blended, redrawn, inpainted or tone-corrected, and no
pixel is ever taken from two plates at once. Crops are at working
resolution (1 px ≈ 0.35 ft); long seams are tiled into several crops
(`_a`, `_b`, …) that together cover the whole seam — grade ALL of them and
report the worst.

Decide whether the two plates read as ONE continuous historical map across
the cut. Check, in this order:

1. **Duplicated or stepped streets** — the same roadway drawn twice, or a
   street/avenue whose block faces jog at the cut. Estimate the offset in
   feet (a 70 ft avenue is ~200 px wide at this scale; an 80 ft street
   ~230 px; a 120 ft street ~345 px).
2. **Duplicated street names / lettering** — the same label (e.g. "AVE. C OR
   MECHANIC", "27TH ST.") appearing twice, or a label cut in half with the
   other half missing.
3. **Split or duplicated buildings** — a footprint cut by the seam with the
   two halves not matching, or a building drawn twice.
4. **Rail / utility discontinuities** — track lines, water-pipe dashes
   (`6" W. PIPE`), pipe runs that stop or jog at the cut.
5. **Plate margins or furniture INSIDE mapped ground** — a border rule,
   bracket marks, a large plate number, a north arrow, a scale bar or a
   plate title ("GALVESTON TEXAS") sitting where the map should continue.
   Adjoining-sheet numerals in the roadway at a plate edge are normal on
   these plates and are NOT a defect on their own; flag them only when they
   sit over drawn content or when both plates' numerals show side by side.
6. **White gaps** — unpainted canvas between the plates.
7. **Wrong source ownership** — the cut gives a strip of one plate where
   the other plate's drawing is the complete/authentic one.
8. **Tone** — a visible paper-tone step. Report it; by policy tone is NOT
   corrected and does not lower the score below 4 on its own.

Two things that look like defects but are not, and must be scored 5 with a
note rather than flagged:
- The two plates DRAW a feature differently (Broadway 158 ft on plate 20
  against 105 ft on 23/24; a street drawn 40 ft on one plate and 80 on the
  other; a block run onto the street centreline). That is a source
  disagreement in the 1912 record, not a mosaic defect.
- Paper foxing, stains and edge darkening.

Score:
- 5 — reads as one map; no visible defect.
- 4 — a defect findable only on close inspection (≤ ~2 ft step), or tone only.
- 3 — visible offset up to ~6 ft, or a minor doubled letter; no split building.
- 2 — a clear step (6–20 ft), a doubled label, a clipped feature, or a gap.
- 1 — gross: duplicated street/road, a building split or doubled, an offset
  > 20 ft, wrong ownership over a block, or a plate misplaced.

Return ONLY a JSON array, one object per seam (not per crop), matching the
structured schema you were given. Be concrete: name the street/avenue and
the block or building. Do not invent features you cannot see. If a crop is
entirely blank paper or water on both sides, say so and score 5.

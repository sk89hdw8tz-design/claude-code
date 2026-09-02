# Seam census grader brief (1912 Galveston Sanborn mosaic, round 3)

You are grading seams of a mosaic built from 1912 Sanborn fire-insurance
plates. Each seam is where two plates meet; a thin red tick in the margins
marks where the cut crosses the crop edge. The map pixels are untouched
scans. Crops come in pairs: `_50.jpg` (overview) and `_100.jpg` (working
resolution, 1 px ≈ 0.35 ft). Long seams are tiled into several crops
(`_a`, `_b`, ...) that together cover the whole seam — grade ALL of them
and report the worst.

Look at each crop and decide whether the two plates read as ONE continuous
historical map across the cut. Check, in this order:

1. **Duplicated or stepped streets** — the same roadway drawn twice, or a
   street/avenue whose block faces jog at the cut. Estimate the offset in
   feet (a 70 ft avenue is ~200 px wide at 100%; an 80 ft street ~230 px).
2. **Duplicated street names / lettering** — the same label (e.g. "AVE. C OR
   MECHANIC", "27TH ST.") appearing twice, or a label cut in half with the
   other half missing.
3. **Split or duplicated buildings** — a footprint cut by the seam with the
   two halves not matching, or a building drawn twice.
4. **Rail / utility discontinuities** — track lines, water-pipe dashes
   (`6" W. PIPE`), pipe runs that stop or jog at the cut.
5. **Plate margins or furniture INSIDE mapped ground** — a border rule,
   bracket marks, a large plate number, an adjoining-sheet numeral, a north
   arrow or scale bar sitting where the map should continue. (Numerals in
   the roadway of a street at the plate edge are normal on these plates;
   flag them only if they sit over drawn content or both plates' numerals
   show side by side.)
6. **White gaps** — unpainted canvas between the plates.
7. **Wrong source ownership** — the cut gives a strip of one plate where
   the other plate's drawing is the complete/authentic one (e.g. half of a
   block from each plate, or one plate's coarse drawing over the other's
   detailed one).
8. **Tone** — a visible paper-tone step. Report it but it does NOT lower the
   score below 4 on its own: tone is not corrected by policy.

Score (brief §6 rubric):
- 5 — reads as one map; no visible defect at 100%.
- 4 — a defect findable at 100% but invisible at 50% (≤ ~2 ft step, or
  tone only).
- 3 — visible offset up to ~6 ft, or a minor doubled letter; no split
  building.
- 2 — a clear step (6–20 ft), a doubled label, a clipped feature, or a gap.
- 1 — gross: duplicated street/road, a building split or doubled, an
  offset > 20 ft, wrong ownership over a block, or a plate misplaced.

Return ONLY a JSON array, one object per seam (not per crop):

```json
[{"seam": "57_58", "score": 2, "offset_ft": 9,
  "defects": ["step", "duplicated-label"],
  "worst_crop": "seam_57_58_b_100.jpg",
  "reason": "one or two sentences naming the feature and where in the crop",
  "furniture": "what plate furniture is visible in the roadway, if any",
  "fix_hint": "what would make it pass: e.g. 'move the cut ~30 px east so plate 58's label survives whole', 'registration: plate 58 needs to shift ~9 ft north', 'owner: give the block to plate 57'"}]
```

Defect vocabulary: `step`, `duplicated-road`, `duplicated-label`,
`split-building`, `duplicated-building`, `rail-break`, `utility-break`,
`margin`, `furniture`, `gap`, `wrong-owner`, `tone`, `misplacement`.
Be concrete: name the street/avenue and the block or building. Do not
invent features you cannot see. If a crop is entirely blank paper or water
on both sides, say so and score 5.

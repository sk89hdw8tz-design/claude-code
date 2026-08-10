# Prior build — defects that remain, measured

These are the numbers the rebuild must beat. Every one was measured, not
estimated. Where a figure came from two independent methods, both are given.

## Registration

| # | Defect | Measurement | Method |
|---|---|---|---|
| 1 | Lateral row step across 24th St, east of Avenue A | **48–85 px** | alley-centreline tracking (+48, +51, +57, +62, +85 at five x positions) AND column-profile NCC (−45…−58 px at every confident window, ncc 0.53–0.70) |
| 2 | Vertical steps at Avenue G | **+64 px** at 25th, **−42 px** at 20th, **−34 px** at 22nd | centreline / water-main tracking |
| 3 | Rail steps across Avenue A | **0 → +30 px**, growing north to south; 20 of 28 sampled rows > 10 px; worst +29…+31 at 24th | per-rail tracking, 28 rows |
| 4 | 21st St differential warp | −54, −40, −34 px at three x positions but 0.3–6 px at four others | alley tracking — *not* a rigid offset |
| 5 | Avenue A corridor width variance | **+3 … +30 px** along its length | composite width vs single-sheet width |

**Control that proves the method**: where one sheet spans both sides and no
seam exists, the same measurements return **0–1 px at ncc 0.69–0.83**.

**Seams already meeting the bar** (proof ≤8 px is achievable on this data):
- 22nd Street: every crossing within **±6 px** (11 crops walked end to end)
- 19th Street: crossings −3.0, −3.4, +3.8, −2.7, −0.2 px

## Root cause

The content-level seam refinement — the stage whose entire purpose is to
correct ±40 px of line-detection noise — produced **zero usable
measurements**. Correlation responses came out **0.01–0.26** against a 0.55
gate, with mutually inconsistent offsets (−563, +242, −252 px). The gate
correctly rejects them; lowering it would inject that noise into the
geometry. So every per-unit translation correction is zero and the whole
registration rests on grid-line detection alone.

Why the responses were garbage: the stage samples a quarter-resolution band
and squashes it to a fixed 130 px width before correlating. Fix the sampling
(full resolution, gradient images, feature-rich windows inside the measured
overlap) and this becomes the strongest signal available.

## Cosmetic / authentic-but-awkward

- Stray sheet-reference numerals inside the map body (7 instances) — printed
  inside the border on the originals.
- Duplicated scale bars (3) and compass roses (3) where two sheets contribute.
- Ghost/tripled rails inside the 16 px feather: at y=6800 the tile carries
  rails at 3103.3, 3112.4 and 3124.1 — three rails for a two-rail track.
  Alpha blending averaged two mutually-offset drawings.
- 24th St: buildings' north frontage clipped where owner-on-top pushes the
  northern sheet past where the southern sheet draws those walls.

## Failures worth not repeating

1. **Circular verification.** Fit residuals stayed under 15 px while a
   sheet's content sat 114 px out — a uniform bias is absorbed by the
   translation term. Detected only when a human noticed the same hydrant
   drawn twice.
2. **A "fix" that was translation-invariant.** A window-reconciliation pass
   re-fit scale and translation per candidate window, then scored by
   residual — mathematically unable to discriminate. It left the real errors
   and corrupted a correct sheet.
3. **Untested cleanup.** Dropping an unreliable control instead of overriding
   it took coverage 98.98% → 90.85%. No before/after metric was run.
4. **Agents losing work.** Three full agent runs died to session limits
   having written nothing; they buffered output to the end.
5. **`paper_bounds` truncation.** Avenue A's own frontage rules dropped the
   cream fraction below threshold for a few px, splitting a sheet into two
   runs; taking the longest ended that sheet's paper 240 px early, which made
   its frame appear not to overlap its neighbour and collapsed the seam to a
   midpoint fallback.

## Source-level finding: the wharf sheets' east side is SCHEMATIC

Discovered by the landmark-locating fleet, after everything above was
written, and important enough to change how THE BAR reads at Avenue A.

On sheets 06, 07 and 08, the blocks drawn EAST of Avenue A (the harbor-side
block row the downtown sheets survey in detail) are schematic outline
rectangles, not survey drawings. Matching their corners against the same
physical corners on the downtown sheets (11, 13, 15) shows the two drawings
disagree **by up to ~100 px between features on the same pair** — the
disagreement varies corner to corner, so it is not a rigid offset and not a
measurement artifact. The locators' own note: "the schematic east-side
rectangles on 06 are not survey-accurate: corner-pair offsets vary by up to
~100 px between features, which is disagreement between the two drawings,
not misidentification."

Consequences for any rebuild:

- **No registration method can align drawings that disagree.** At the
  Avenue A wharf|downtown seams, some residual mismatch is AUTHENTIC.
- Policy: the downtown sheets' surveyed drawing is authoritative east of
  Avenue A; the wharf sheets' schematic rectangles should lose every
  conflict there, and the report should disclose why.
- The ≤8 px landmark gate applies to surveyed-vs-surveyed pairs.
  Landmarks flagged `schematic: true` in landmarks.json are reported but
  excluded from pass/fail.
- The wharf|wharf pairs (07|06 at 22nd, 08|07 at 19th) are NOT affected —
  both sides are drawn in the same detailed style, and the prior build
  already measures ±6 px there.

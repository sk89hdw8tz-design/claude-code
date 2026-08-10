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

## Landmark baseline — the prior build measured by the anti-circular gate

`tools/landmark_check.py` run against the prior build's transforms with the
complete 61-feature, 19-pair landmark set (full table in
`landmark_baseline.txt`):

- **median step 98.4 px, max 233.9 px, 58 of 61 landmarks over 8 px.**
- The seam-walking QC had measured steps of "only" tens of px because it
  could only see content the seam cuts left visible; the landmark gate sees
  the transforms directly. This is the circularity lesson made concrete.

The per-pair structure matters more than the totals. Wharf pairs are fine
(07|06 mean (+9,+8) spread 11 px; 08|07 mean (+2,+3) spread 9 px). The
downtown pairs carry LARGE mean offsets with SMALL spreads:

| pair | mean dx | mean dy | spread |
|---|---|---|---|
| 13\|14 | −104 | −26 | 15 |
| 14\|39 | −114 | −17 | 54 |
| 14\|16 | +80 | −208 | 18 |
| 13\|15 | +79 | −163 | 71 |
| 39\|37 | +71 | −131 | 25 |
| 41\|39 | −52 | −117 | 20 |
| 12\|14 | −15 | −119 | 19 |
| 11\|13 | +13 | −113 | 44 |
| 11\|12 | −49 | −108 | 39 |

Small spread + large mean = **rigid pairwise misregistration** — removable
by per-sheet translations. With 19 pairwise constraints over 12 sheets this
is a tiny least-squares problem; these landmarks are the measurements it
needs. That materially strengthens the cheap-repair option (solve
translations from landmarks, re-render, re-check), and it is also exactly
the bundle-adjustment input the full rebuild would start from.

Independent cross-validation: the dx means at the 24th St pairs (+71..+80)
match the seam QC's 48–85 px lateral-step measurement made by a completely
different method.

Redraw scatter caveat: the drawings themselves disagree by ~24 px (best
pair) to ~100 px (schematic Avenue A pairs), so post-repair expectations
are bounded by the spread column, not by zero.

## Post-repair state (landmark-solved bounded corrections applied)

The repair (iterated bounded least squares from the 61 landmarks:
translations free, scales ±1%, wharf sheets rigid, applied to warp knots +
frames + fits) moved the gate from median 98.4 px to **23.5 px**; surveyed
per-pair means from worst 36.7 to **16.6 px**, 9 of 14 within 10 px. Full
table in `landmark_after_repair.txt`; guard metrics in
`repaired_metrics.json` (coverage 98.57% — see the Avenue D note below).

Remaining, for any future rebuild:
- Five surveyed pairs at 11–17 px mean (11|12, 12|14, 12|41, 13|14, 41|39),
  at the level of the drawings' own per-pair scatter (13–18 px). The next
  useful degree of freedom is per-sheet ROTATION, which the separable
  piecewise warp cannot express — a genuine rebuild item.
- **Avenue D authentic voids**: with content correctly registered, sheets
  13|14 (above 24th) and 15|16 (below) have printed frames that do not
  meet — 46/55 px of never-engraved corridor centre, rendered as flat
  paper, all kerb and address content present. The prior build hid this
  under misregistered overlap; any content-true rebuild will show it too.
- Schematic Avenue A disagreement and sheet furniture: unchanged, as
  documented above.

## Post-polish state (junction + wharf revision)

Five junction street-furniture landmarks (dashed-row selection, ink
fraction 0.12–0.55) measure the wharf-vs-downtown offset at 19th–25th.
They disagree street-to-street by up to ~95 px while downtown pairs
11|13 agree to 3 px — junction scatter is SOURCE-level. Applied as one
rigid wharf-group shift (weighted mean −9.9, +14.9 px), never as
network couplings (measured regression when coupled: median 23.5→27.4).
Wharf-internal pair means then zeroed exactly against anchor 07
(06 +4.3,−7.3; 08 −3.3,+7.0).

The wharf 22nd seam cuts at +175, sheet 7's measured paper edge
(content to native 3934, paper ~3937, UT citation on backing 3986+),
via a trusted manual cut that bypasses the synthetic frame estimate
(wharf sheets print no frame line; the estimate had clamped the cut to
+142, halving sheet 7's pointer numeral). Sheet 7 draws the whole
shared band; flip variants all sliced or ghosted a label copy because
sheet 6's scan is cut ~90 px above 22nd.

Warehouse post-spacing on 06 vs 07 drifts 1→15 px west→east while
corner landmarks show <0.1% pair scale: engraver disagreement, not
scan scale. Single-drawing rendering removes it from view.

Guard: coverage 98.54%, pure-white 48, black 0.0086%. 13|14 stays at
+13 px dy (its scatter floor; zeroing it costs 24th St ~24 px via
12|14) — the Avenue D pipe step at the void is disclosed, not hidden.

## Uniform-paper + corridor revision (latest)

**Illumination flattening** (`composite.flatten_illumination`): the
sheet paper MEDIANS agree within a few levels, but each scan carries
its own illumination field — sheet 8's pale south band rendered as a
"white bar" at 19th that no per-sheet gain could touch. Each scan is
divided by its low-pass paper field (bright, low-saturation,
non-backing pixels; masked diffusion; σ15 at /8 scale) and multiplied
by the edition cream, clipped ±30%. Washes keep their ratio to local
paper. Pure-white 48 → 7. Two traps found measuring this: scanner
backing passes the brightness test (excluded via min-channel < 225 —
including it INVERTS the correction at edges), and region means with
ink in them mislead — compare paper-only pixels.

**Corridor-continuity landmarks**: Strand/Mechanic kerb steps crossing
24th measured +20/+25 px by column-profile NCC while the 13-15-16-14
cycle closes with ~25 px of engraver disagreement — the steps can only
be RELOCATED. Two weighted features (corridor-strand-24th 2.0,
corridor-mechanic-24th 1.2) bias the solve toward the corridors:
+20→+12, +25→+17, residual parked in block interiors and a rigid
−18 px at 14|39 where the owner-on-top Avenue G seam hides it (streets
cross Avenue G at +8/+11). Scale bounds ±1% → ±0.4% (the ±1% solve
pinned 13/+1% against 15/−1%; their differential drift was the first
corridor-step suspect, but tightening alone did NOT fix the steps —
the cycle contradiction did it; keep both changes).

Current gate table: `landmark_after_polish.txt`; guard metrics:
`repaired_metrics.json` (coverage 98.52%, white 7, black 0.0080%).

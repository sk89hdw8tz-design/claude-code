# Determinability review — 12-sheet block, similarity network

Reviewer: Fable track. Basis: the verified adjacency (17 pairs), the control protocol,
the independent triage and 12 measured controls, and the seam structure (all seams abut;
observables are crossing-feature face lines). No production solve was run; this is a
structural assessment, with quantities from the independent measurements.

## What each observation type actually constrains

At an abutting seam, a crossing-feature control contributes, per measured face line, one
equation in the ALONG-seam direction only. Across-seam separation between two plates is
not observed anywhere; it enters solely as the CONSTRUCTED street-width relation. This
shapes the network's determinability more than control count does:

- **Translation along seams / relative offsets:** richly determined. Two anchors per seam
  (four face lines) redundantly fix the along-seam offset of each pair.
- **Scale:** determined along seams by anchor separation (two anchors ~2,300-2,900 px
  apart), and independently checkable against the ~6.07 px/ft figure the measurements
  reproduce on every plate. Adequate, but see rotation-scale coupling below.
- **Rotation:** the weak axis. A pair of anchors on one seam gives a rotation lever only
  over that seam's extent, and the measured reading noise (±4-10 px over ~2,500 px
  baselines) means per-seam rotation is determined to only ~2-4 mrad. Rotation is instead
  pinned by CLOSURE: each sheet interior to the grid sits on seams in both orientations,
  and loop closure around each 4-sheet junction couples the rotations strongly.
- **Across-seam translation:** entirely constructed (street width × scale). Its sigma
  must stay loose, and the drafted-width disagreements the specialist recorded (470 vs
  482 px for the same street on facing plates) set the honest floor: ~±10-15 px, not ±4.

## Sheet-level risk ranking

| Sheet | Seams (orientations) | Assessment |
|---|---|---|
| 9, 10, 43 | 4 (both) | strongly determined; interior closure |
| 8, 11, 12, 39, 49, 44 | 3 (both) | well determined |
| 7 | 2 (v: 7-8, h: 7-9) | adequate but both seams are its only ties; 7-9 is the rail-yard seam (downgraded controls, +42..+64 px cross-plate scatter). 7's rotation leans on the 7-8 seam plus one noisy horizontal seam |
| 40, 50 | 2 each (one v, one h) | **corner sheets of the weak quadrant** |
| 44 | 3, but all within column 4 / row 2-3 | the column-4 chain 40-44-50 hangs off the block through 39-40, 43-44, 49-50 |

**The principal structural risk is the column-4 chain (40, 44, 50).** All three of its
vertical attachments cross Ave I (Sealy) — the same seam family — and its internal seams
(40-44, 44-50) are short horizontal links. Along-Sealy geometry is well fixed, but the
chain's ACROSS-Sealy placement rests wholly on constructed street-width relations, and
its rotation on closure through only two junctions (21st×Sealy, 24th×Sealy). This matches
the triage: all three HIGH-ambiguity seams are exactly 39-40, 40-44, 44-50. A plausible
failure mode: the whole column translated a few tens of px east-west of truth, and/or
rotated ~2 mrad, with every residual still looking clean — numerically fitted, weakly
determined.

## Recommendations (for the controller)

1. **Long-baseline rotation observation for column 4.** The through-running cross streets
   give it almost free: 19th/20th/21st (and 24th/25th) each cross the ENTIRE block. Chain
   the same street's face line across 39→40 (and 43→44, 49→50) together with its reads on
   columns 1-3, and demand collinearity in the solved plane as a diagnostic (not
   necessarily as a constraint). Any column-4 rotation error shows up as a kink at Sealy.
2. **A second across-seam relation for Sealy.** The Broadway finding (drafted lot-face
   separation ~100 ft vs "150'" annotation) proves annotations cannot be trusted alone.
   For each constructed width used, require the drafted-width measurement from BOTH
   plates (the specialist's method), and set that seam's across sigma from their
   disagreement, per seam, not globally.
3. **Do not tighten sigma_across below ~±12 px** anywhere before the first diagnostic
   solve; the measured plate disagreements justify no better.
4. **Junction closure QA at all six interior 4-sheet junctions**, with the two junctions
   on Sealy (21st×Sealy, 24th×Sealy) first — they carry the weak chain.
5. **Covariance check to run with the solve:** report the marginal covariance of each
   sheet's (θ, s) and flag any sheet whose rotation standard deviation exceeds ~1.5 mrad
   despite low residuals; expected flags per this note: 40, 50, then 7.
6. The 7-9 seam's scatter (+42..+64 px between anchors) is drafting disagreement, not
   measurement error; carry it as inflated sigma on that seam rather than editing either
   plate's readings toward the other.

Classification: **READY FOR OPUS RECONCILIATION** (no blocking gaps; the network is
solvable as designed once recommendations 2-3 are honoured).

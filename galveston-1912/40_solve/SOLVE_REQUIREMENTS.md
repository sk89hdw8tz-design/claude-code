# Solve requirements — adopted from the determinability review (2026-08-17)

Source: `fable_review/FABLE_DETERMINABILITY_NOTES.md`, adopted as binding for the
12-sheet block solve.

## Model and weights

- Per-sheet similarity (tx, ty, θ, s); one sheet fixed as datum.
- Crossing-feature controls contribute along-seam equations only; across-seam relations
  are constructed from drafted lot-face separations **measured on both plates** — never
  from printed width annotations alone (Broadway: drafted ~100 ft vs annotated 150').
- **sigma_across floor: ±12 px** per seam, or half the plates' measured width
  disagreement if larger. No tightening before a diagnostic solve justifies it.
- Seam 7-9 carries inflated sigma (recorded cross-plate scatter +42..+64 px between
  anchors is drafting disagreement, preserved, not reconciled).

## Diagnostics that must run with every solve

1. **Marginal covariance per sheet on (θ, s):** flag rotation σ > 1.5 mrad regardless of
   residuals. Expected flags on first solve: sheets **40, 50, then 7**. Absence of these
   flags is a tooling question before it is reassurance.
2. **Through-street collinearity check:** chain each long cross street (19th, 20th, 21st,
   24th, 25th) across all four columns in the solved plane; a kink at Ave I (Sealy)
   indicates column-4 chain rotation/translation error the residuals cannot see.
3. **Junction closure QA at all six interior 4-sheet junctions**, the two Sealy junctions
   (21st×Sealy, 24th×Sealy) first.
4. Per-control normalised residuals + redundancy numbers; robust down-weighting logged,
   never silent.

## Independent-measurement reconciliation policy

The 12 Fable controls (`fable_review/FABLE_INDEPENDENT_CONTROLS.csv`; 8 high, 4 medium)
are an independent measurement set. Controller measurements on the same seams are taken
without first reading Fable coordinates, then reconciled: diagnose any difference;
average only if neither side shows an identified bias; supersede on demonstrated bias;
otherwise carry the disagreement as uncertainty. Blanket averaging is prohibited.

## Sheet 5 (deferred; on re-entry)

Two regions per `fable_review/sheet05_candidate_regions.geojson`, each with its own
similarity transform, fitted against the frozen block; the duplicated Pier 22 / 22nd St
ground is the cross-panel consistency check. Sheet 9 receives attachment constraints
from BOTH panels.

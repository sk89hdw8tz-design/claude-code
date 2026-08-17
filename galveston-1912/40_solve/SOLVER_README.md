# Network solver — Galveston 1912 12-sheet block

`solver.py` implements the diagnostic least-squares solve specified in
`SOLVE_REQUIREMENTS.md`, consuming the control JSONs written per
`30_controls/MEASUREMENT_BRIEF.md`.

## Model

- **Unknowns.** One 2D similarity per sheet (7, 8, 9, 10, 11, 12, 39, 40, 43,
  44, 49, 50), linear form `(a, b, tx, ty)` with `a = s·cosθ`, `b = s·sinθ`:

      p_mosaic = [[a, -b], [b, a]] · (p_sheet − c) + (tx, ty),   c = (3326, 3898)

  Sheet coordinates are **recentered** by the plate center `c` before the
  normal equations are built (conditioning); `transforms.json` stores both the
  centered parameters and the composed **raw-pixel** transform (`raw.tx/ty`) —
  downstream code operating on raw scan pixels must use the `raw` block.
- **Gauge.** Sheet 10 is fixed to the identity; the mosaic frame is sheet 10's
  centered pixel frame. Sheet 10's zero covariance is a gauge artefact.
- **Kappa.** One global nuisance parameter κ (mosaic px/ft) with Gaussian prior
  6.07 ± 0.15, used only by across-seam constraints. *Identifiability note,
  verified on synthetic data:* the network cancels κ exactly against sheet
  translations (loop contributions cancel), so κ is **prior-determined, not
  measured**; the outputs flag this (`kappa_prior_dominated`) and κ must be
  validated against per-plate drafted widths, not read off the posterior.

## Observations (from ACCEPTED anchors only)

1. **Along-seam coincidence** — per anchor, per face: midpoints of the face
   segment on both plates; residual is the mosaic difference projected on the
   seam direction (`(0,1)` for vertical seams, `(1,0)` for horizontal).
   This axis-aligned `u_along` is a linearization valid because the solution is
   near axis-aligned (sub-degree rotations). Weight `1/(σ_A² + σ_B²)` from each
   side's `sigma_along_px`.
2. **Across-seam constructed separation** — one per anchor (face1 only, to
   avoid double counting): the face1 endpoints nearest the seam on each plate
   (left/top plate: larger x/y; right/bottom plate: smaller) approximate each
   plate's own frontage corners; residual
   `(T_B(p_B) − T_A(p_A))·u_across − W_ft·κ`.
   `σ_across = max(12 px, |drafted_width_px.A − B|/2)` (binding floor).
3. **Seam-street widths.** Defaults: Ave C (Mechanic) 70 ft, Ave F (Church)
   70 ft, Ave I (Sealy) 80 ft, 21st/Center 80 ft, 24th 80 ft. Per seam the
   solver reads `drafted_width_px` and `annotation`; a *consistent* drafted
   evidence set that supports a different width overrides the default
   (annotations alone never override — Broadway precedent). Every width choice
   and discrepancy is logged in `diagnostics.md`.

Left/top vs right/bottom sheet identity comes from `10_key/adjacency.json`,
never from file field order; an `axis` field contradicting adjacency is logged
and overridden.

## Fitting

Weighted linear least squares over all sheet parameters + κ, with IRLS/Huber
(δ = 2.5 σ, 10 iterations). Down-weighted observations are always logged and
never dropped. Covariance = `(JᵀWJ)⁻¹` scaled by the robust variance factor
`s0² = Σ w_h r_n² / (m − rank)`. Sheets with no observation path to the datum
are excluded from the solve and reported (`unsolved_sheets`) — the solver runs
on any partial subset of seams, including a single file.

## Usage

    /home/user/g1912/venv/bin/python solver.py [--controls DIR] [--out DIR]
        [--adjacency PATH] [--loso] [--rot-prior-mrad MRAD]
        [--collinearity] [--collinearity-sigma PX]

Defaults: controls `30_controls/verified/`, output `40_solve/output/`,
adjacency `10_key/adjacency.json`. `--loso` runs leave-one-seam-out (refit
without each seam; prediction error of the held-out along-seam residuals).

`--collinearity` (off by default) promotes the through-street face lines to
observations via a **two-stage solve**: pass 1 is the current model; pass 2
adds, for each street measured on ≥ 2 sheets, one straight line PER FACE
(faces never mixed; membership canonicalized low/high by the pass-1 mosaic
perpendicular coordinate, immune to face1/face2 labeling differences across
files). Each used line adds two unknowns `(c, m)` for
`perp = c + m·(along − mean_along)` — `m` stays a free per-line parameter, so
no street direction is assumed, only straightness. One row per face midpoint,
linearized at the point's pass-1 mosaic along-coordinate;
`sigma_perp = 6 px` by default (`--collinearity-sigma`, drafting scatter).
Collinearity rows are data-class and Huber-subject. Lines with all points on
one sheet, or with < 3 points (their own 2 unknowns fit them exactly),
contribute nothing and are skipped with a log line; the used-line count is
reported. LOSO refits keep the collinearity rows minus the held-out seam's
points.

## Outputs (`40_solve/output/`)

- `transforms.json` — per sheet `a, b, tx, ty, s, theta_deg` (centered) plus
  the composed `raw` transform; κ, its prior/posterior and the
  prior-domination flag; convention block.
- `residuals.json` — per observation: pair, seam, anchor, type, face, residual
  (px), sigma, weight, final Huber weight, normalized residual.
- `covariance.json` — full parameter covariance (scaled), parameter order,
  per-sheet marginal std of θ (mrad) and s (ppm) plus tx/ty (px), rotation
  flags (θ std > 1.5 mrad), rank/dof/s0².
- `diagnostics.md` — human-readable: seams loaded and width decisions, residual
  RMS by seam and by type, flagged sheets, κ posterior + identifiability note,
  down-weighted observations, through-street collinearity (with the Ave I kink
  check), LOSO table, full load/solve log, gauge note.

## Diagnostics

- **Rotation flags**: any sheet with marginal θ std > 1.5 mrad. Expected flags
  on a first full solve: 40, 50, then 7 (corner/edge sheets); their absence is
  a tooling question before it is reassurance.
- **Through-street collinearity**: for each crossing feature measured in ≥ 2
  pairs of the same axis (19th/20th/22nd/23rd/25th/26th across vertical seams;
  avenues across horizontal seams), the per-(pair, sheet) street *center* point
  (mean of the two face midpoints — immune to face1/face2 labeling differences
  between files) is mapped to the mosaic and a total-least-squares line is fit;
  max/RMS perpendicular deviation reported. For numbered streets the **Ave I
  kink** is reported separately: deviation of column-4 (sheets 40/44/50) points
  from the line fit through columns 1–3 alone.
- **Leave-one-seam-out** (`--loso`): each seam's observations removed, network
  refit, held-out along-seam residuals predicted; disconnections caused by the
  removal are detected and reported rather than crashing.

## Self-test

    /home/user/g1912/venv/bin/python test_solver.py

Generates a synthetic 12-sheet ground truth (rotations ≤ 0.5°, scales ±0.5%,
translation jitter), writes control JSONs in the exact brief schema with noise
at the stated sigmas (plus an 8 px across-seam drafting scatter, below the
12 px floor), and asserts: parameter recovery within 3× propagated σ;
rotation-covariance flag fires when corner sheet 40 is weakened (half its
observations dropped) while interior sheet 43 stays unflagged; LOSO refits all
17 seams with bounded prediction error; missing seam files are tolerated with
the disconnected sheet reported; straight-street collinearity constraints
(the generator's face lines are exactly collinear across sheets by
construction — shared global centerlines) shrink every free sheet's rotation
std, ≥ 2× at the median, with recovery still within 3σ and LOSO intact.
Prints PASS/FAIL lines; exit 0 iff all pass.

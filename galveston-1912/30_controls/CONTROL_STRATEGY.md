# Control strategy — Galveston 1912

## The finding that shapes everything: adjacent plates *abut*, they do not overlap

Pair 7–8 shares Avenue C (Mechanic). Examined at 1:1 on the archival originals:

- Sheet 7 carries only the **even** Mechanic addresses (1922, 1924, 1926, 1928 …) —
  the north side of the avenue.
- Sheet 8 carries only the **odd** Mechanic addresses (1921, 1923, 1925, 1927 …) —
  the south side.

The 1912 street index says the same thing in its own notation: Avenue C reads
`1800–2028 → *7` and `1801–2027 → *8`, where the index defines `*` as
**"only one side of street shown"**. Avenues F (Church) and I (Sealy) are marked the
same way, and those are precisely the other two vertical seam avenues.

**Consequence.** There is no band of duplicated cartography along a vertical seam to
match on. Ordinary image correlation has nothing real to lock onto there — it would
be matching blank street paper and the repetitive drafted furniture inside it, which
is exactly the failure mode the brief warns about (a plausible fit that is one block,
or one lot, off). This is a structural property of the source, not a tuning problem.

## What genuinely *is* shared across a vertical seam

The **cross streets**. 18th, 19th, 20th and 21st Streets each run across Avenue C and
are drafted on both plates. Their lot lines are the same physical lines, continued on
each sheet. Measured band centres near the seam (ink-density profile, fraction of page
height):

| Cross street | sheet 7 | sheet 8 | difference |
|---|---|---|---|
| 18th St | 0.096 | 0.055 | 0.041 |
| 19th St | 0.353 | 0.355 | 0.002 |
| 20th St | 0.652 | 0.634 | 0.018 |

The 19th/20th agreement to 0.002–0.018 of page height confirms the pairing is real; the
residual differences are the per-sheet placement the fit has to solve, not noise to be
assumed away. (18th differs most because it sits at the very top of sheet 7, where the
band is clipped by the sheet edge and its measured centre is biased — a measurement
artefact, not a geometric disagreement.)

## Control taxonomy for this edition

Every control record carries `class`, per-axis sigma, and a **disambiguating semantic
anchor** — a named street pair, block number, or address run — so that no control can
be justified by visual similarity alone.

| Class | What it is | Uncertainty |
|---|---|---|
| `observed` | A drafted point both plates genuinely draw: cross-street lot lines where they meet the seam avenue; block corners; a building corner both sheets carry. | small, roughly isotropic |
| `constructed` | Across-seam coordinates built from the plate's own drafted street width (Mechanic is annotated `70'`). Strong along the street, weak across it. | **anisotropic** — tight along-seam, loose across-seam |
| `inferred` | Anything resting on continuity assumptions rather than a drafted mark. | large; carried but heavily down-weighted |

This is why the brief's demand for per-axis, per-point uncertainty is not optional
here: the along-seam direction is constrained by shared cross-street geometry, while
the across-seam direction is constrained only by an annotated street width. Treating
those two directions with one isotropic sigma would silently overstate the across-seam
constraint and produce a confident, wrong fit.

## Explicitly excluded as precision control

Per the brief, and reinforced by what these plates actually show in the street space:
water-main lines (`6" W. PIPE`, `8" W. PIPE`), hydrants, fire-alarm boxes and similar
drafted symbols. They are abundant in exactly the blank street band where a matcher
would be tempted to use them, and their drafted position is schematic rather than
surveyed. They may corroborate, never constrain.

## Horizontal seams differ from vertical ones

The horizontal seams (21st/Center St between 7–9, 8–10, 39–43, 40–44; 24th St between
9–11, 10–12, 43–49, 44–50) are streets that both plates appear to carry in full, unlike
the split avenues. Whether they provide genuine two-sided overlap has to be established
per pair by the same 1:1 examination, not assumed from the vertical-seam result.

## Pooled seam groups (from the verified adjacency graph)

Six shared features carry all 20 internal pairs, so six pooled cut lines are required
rather than 20 independently fitted ones:

| Shared feature | Pairs |
|---|---|
| Ave. A or Water | 5–7, 5–9, 5–11 |
| Ave. C or Mechanic | 7–8, 9–10, 11–12 |
| Ave. F or Church | 8–39, 10–43, 12–49 |
| Ave. I or Sealy | 39–40, 43–44, 49–50 |
| 21st or Center St | 7–9, 8–10, 39–43, 40–44 |
| 24th St | 9–11, 10–12, 43–49, 44–50 |

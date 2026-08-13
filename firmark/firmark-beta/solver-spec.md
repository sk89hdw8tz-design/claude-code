# Sizing Solver Specification — search, heuristics, and the weight model

**Subject:** the search that *proposes* a wood member, the heuristics that make the search cheap
and explainable, and the regional weight model that ranks the members that already passed.

**Companion document:** `calc-spec.md` — the ASD member check itself. This document does not
restate a single capacity equation. It cannot: the solver never computes a capacity.

---

## 0. The two rules

Everything in `solver.js` and `weights.js` exists under two rules. If a change to either file
would break one of them, the change is wrong.

> **Rule 1 — the solver proposes, the engine disposes.**
> Every feasibility verdict comes from `FM.engine.run()`, unmodified, on inputs the solver
> assembled. The solver decides *which* members to ask about and *in what order*. It never
> computes an allowable stress, never adjusts a factor, and never overrides a verdict.

> **Rule 2 — no weight can make a member pass.**
> Feasibility is tested first, against the firm's DCR target, using only engine output. Scoring
> happens afterward, on the survivors. A weight can change which passing member is recommended;
> it cannot promote a failing one. Pinned by the regression test
> *"weights cannot select an overstressed member"*, which drives every weight to an absurd value
> and asserts the feasible set is unchanged.

`calc-spec.md` §8.23 says: *"This is a member check, not a design. It does not select sections,
iterate, or optimize."* That sentence describes the **engine**, and it is still true of the
engine. This document describes a layer built on top of it. The scope boundary has moved by
exactly one step and no further: **the solver selects candidate sections and iterates; it does
not design.** It has no opinion about framing layout, load path, lateral systems, connections,
or anything else in §8. A licensed engineer still owns the result.

---

## 1. Vocabulary

| Term | Meaning |
|---|---|
| **Demand** | What has to be carried: role, span, tributary width or spacing, loads, service conditions, deflection row. Independent of any member. |
| **Candidate** | One concrete member: species, grade, nominal size, spacing. |
| **Family** | All candidates sharing (species, grade, thickness, spacing). Within a family the only free axis is **depth**. |
| **Ladder** | The ordered list of nominal sizes offered for a role — what the yard actually racks. |
| **Palette** | The ordered list of (species, grade) pairs offered in a region. |
| **Policy** | Palette + ladder + spacings + DCR target + weights. Assembled by `FM.weights.policyFor(pack, plan, role)`. |
| **Feasible** | `governing DCR ≤ policy.maxDCR`, where the DCR comes from the engine. |
| **Score** | Dollars. Lower wins. Defined in §5. |

The DCR target is the **firm's**, not the code's. The code's threshold is 1.000
(`calc-spec.md` §6.2, no tolerance band). A firm target of 0.90 leaves the engineer margin to
absorb a field change without re-running the schedule. A member at 0.95 is not failing; it is
outside the firm's envelope, and the solver reports it as such rather than silently offering it.

---

## 2. Where the demand comes from, and the one place it depends on the candidate

`FM.solver.memberInputs(demand, cand, policy)` is the single place engine inputs are assembled,
so a member scored by the solver and the same member re-checked on a sheet cannot disagree.

**Repetitive members** (rafter, joist, ceiling joist) pass `spacing` straight through. Per
`calc-spec.md` §1.3 case (a), self-weight is already inside `q_D` and is **not** added again.

**Beams and headers** are not repetitive. The engine computes `w = psf · spacing/12`, so the
solver passes `spacing = trib_ft × 12`, which makes `w = psf · t_w` — the §1.1 case (b)
tributary rule, expressed in the engine's existing input vocabulary rather than by changing it.

Then, per §1.3 case (b), the beam's own weight is **not** inside `q_D` and has to be added:

```
w_sw = γ · A / 144                    [plf],  γ = 35 pcf default (§1.3, an assumption)
Δq_D = w_sw / t_w                     [psf]   ← what the solver adds to `dead`
```

Substituting back, `Δq_D · t_w = w_sw` exactly, so the engine sees the correct line load without
any new input path.

This is the one genuine feedback term in the search: **`A` is a property of the candidate, so
the demand is a function of the candidate.** A deeper section is heavier, which raises the
demand it must then carry. The search cannot be a single closed-form solve for that reason
alone, and the bounds in §4 are written to stay valid in spite of it.

---

## 3. C_F moves with the depth — the reason `CF: "auto"` exists

`C_F`, the size factor, is a function of depth. A `C_F` typed for a 2x10 is simply wrong on a
2x6, and the error is not small: NDS-S Table 4A runs from 1.5 at 2x4 down to 1.0 at 2x12 for
visually graded dimension lumber. Any search that walks a depth ladder with a fixed `C_F` is
computing a different member than the one it names.

So the solver always passes `CF: "auto"`, and `engine.js` resolves it per candidate through
`FM.engine.sizeFactor(species, grade, nominal)`, which returns the value **and its provenance**:

| basis | meaning | flagged as |
|---|---|---|
| `table_4b` | Southern Pine — the size factor is already inside the tabulated value; `C_F = 1.0` | sourced |
| `repo_partial` | The catalog's threshold helper covers this cell (2"-thick column, 2x4–2x12, SS/No.1/No.2/No.3/Stud) | **repo-partial, not a citable C_F table** |
| `held` | Nothing covers it. `C_F` held at 1.00 and flagged | unsourced |
| *refused* | Nominal width ≥ 14 in | the check returns an error rather than proceed |

The refusal is the important one. Holding `C_F` at 1.00 is **conservative** everywhere the
catalog is silent *except* at 14 in and wider, where Table 4A publishes a factor below 1.00 that
the catalog does not carry (gap register #1). Rather than hold a value it cannot show to be
conservative, the engine refuses the section and says why. The regional ladders in `weights.js`
therefore stop at 12 in, and a 14 in member requires a typed `C_F` and an engineer who takes
responsibility for it.

---

## 4. The heuristics

Seven of them. Each is stated with the argument for why it is *sound* — meaning it cannot
change the answer, only the work done to reach it — or, where it is a genuine heuristic that
only affects ordering, said so plainly.

### H1 — Admissible seed bounds (sound)

Before any candidate reaches the engine, `seedBounds()` computes lower bounds on the section
properties any member in this palette must have:

```
S_req  = max over combinations of   M_c / (Fb_best · C_D,c · C_r · target)
A_req  = max over combinations of   1.5 · V_c / (Fv_best · C_D,c · target)
b_req  = max over combinations of   R_c / (Fc⊥_best · l_b · target)
I_req  = max over the two deflection checks of
                                    5 · w · L_in⁴ / (384 · E_best · Δ_allow · target)
```

Any candidate whose `S_x`, `A`, `b` or `I_x` falls below the corresponding bound is discarded
without an engine call.

**The bounds are computed per spacing and never maxed across spacings.** Spacing is a
*candidate* axis, not a property of the demand: a member at 16 in o.c. carries two-thirds of what
the same member carries at 24 in, and judging it against the 24 in requirement prunes valid —
indeed optimal — candidates. That defect shipped once. The exhaustive-vs-pruned test caught it,
and it is what keeps it caught.

**Admissibility.** The bounds are computed against the *most favourable* material in the palette
and the *most favourable* factor stack. Each optimism is deliberate and each goes in the safe
direction:

| Optimism | Why it is safe |
|---|---|
| `Fb_best` = max over palette × ladder of `F_b · C_F` | No candidate can have a larger `F_b·C_F`, so no candidate needs *less* `S_x` than the bound. |
| `C_r = 1.15` assumed reachable | Overstates capacity → understates `S_req` → prunes less. |
| `C_M = 1.0` even under wet service | Wet service only reduces capacity, so this overstates it → prunes less. |
| `C_L ≤ 1` taken as 1 | Same direction. |
| Self-weight omitted | Self-weight only *adds* demand, so the real requirement is at least this large. |
| `C_D` taken per combination, exactly | Not an approximation; matches the engine's envelope. |
| Bearing bounds **breadth**, not depth, and carries no `C_D` | `C_D` does not apply to `F_c⊥` (NDS Table 4.3.1), and `f_c⊥ = R/(b·l_b)` has no depth term. |

Since every bound understates what is required, a candidate failing a bound fails the real
check. The converse is not claimed and is not needed.

**This is a claim, so it is tested, not asserted.** The regression test
*"pruned candidates are genuinely infeasible"* runs an exhaustive search — every candidate in
ladder × palette × spacing through the real engine — against the pruned search, across a battery
of demands, and asserts the feasible sets and the winner are identical.

### H2 — Dominance within a family (sound, conditionally)

Within a family the only free axis is depth. **Cost is nondecreasing in depth** — more board
feet, more weight to handle, more structural depth. So once a rung is feasible, no deeper rung
of the same family can beat it, and the rest of the family is cut.

Note what this argument does *not* rely on: it says nothing about whether **capacity** is
monotone in depth. It is not, in general —`C_F` falls as depth rises, and an unbraced deep
member loses to `C_L` (`R_B = √(l_e·d/b²)` grows with `d`). A solver that pruned *upward* from a
failing rung on a monotonicity assumption would be wrong. This one prunes on cost, which is a
property of the candidate and not of the check.

The conditional: monotone cost is a property of the *weights*, and a pathological weight set
could break it (a region where a 2x12 is genuinely cheaper than a 2x10, say, during an odd
market). So the solver **computes the family's cost vector first and verifies it is
nondecreasing** before applying dominance to that family. Where it is not, the family is walked
in full. The check costs nothing: cost is engine-free.

### H3 — Branch and bound across families (sound)

Families are ordered by their cheapest admissible rung — a *lower bound* on what that family
could produce — and walked cheapest-first, keeping the best feasible candidate found so far as
the incumbent. A family whose lower bound is at or above the incumbent's score is skipped
entirely.

Soundness: `score = cost + slack ≥ cost ≥ family lower bound`. If the family's lower bound
already equals or exceeds the incumbent's score, every score it could produce does too.

Ordering cheapest-first is what makes this bite: the incumbent gets good on the first family, so
the bound prunes hard immediately.

### H4 — Sensitivity-guided repair (ordering and explanation only)

From the closed forms in `calc-spec.md` §3, each limit state has a known sensitivity to depth:

| Governing check | Goes as | The move that actually helps |
|---|---|---|
| Deflection | `I ∝ d³` | Depth, or tighter spacing. A grade change barely moves `E`. |
| Bending | `S ∝ d²` | Depth, or a grade step — `F_b` varies most between grades. |
| Shear | `A ∝ d¹` | Area. Thicker stock helps as much as deeper. |
| Bearing | no depth term | Bearing length or breadth. **Depth does nothing.** |

This never skips an evaluation. It decides what the solver *tells* the engineer when a candidate
or a whole search fails — which axis to move, and which axis is a waste of time. A solver that
reports "no solution" and stops has told the engineer nothing they did not already know.

### H5 — Deterministic tie-breaking (required)

`calc-spec.md` §6.2 requires deterministic output. Scores are compared at full precision; ties
break in a fixed order: **depth → thickness → palette order → wider spacing → nominal string.**
No clock, no map iteration order, no randomness. Same inputs, same schedule, every run, on every
machine. Pinned by a test that shuffles the palette and ladder order and asserts identical
output.

### H6 — Memoization (sound)

Engine results are cached on the full input signature. The same physical member is reached from
several families and spacings; it is checked once. Reported as `cacheHits` so the search's work
is visible rather than claimed.

### H7 — SKU unification across a plan (the repeatability heuristic)

This is the one that matters for a plan built a hundred times.

Per-mark optimisation produces a schedule where marks land one rung apart — a 2x8 here, a 2x10
there. Each distinct size is a SKU: pallet space on a tight lot, a separate pick, another chance
for a framer to grab the wrong one. `unify()` collapses a group of marks onto the deepest size
in the group when the extra lumber costs less than the modelled cost of the extra SKU:

```
accept if   Σ (cost_raised − cost_own) × count   ≤   (SKUs_before − 1) × skuPenalty
```

Two constraints make this safe:

1. It only ever collapses **upward**, onto a larger member.
2. The raised member must itself appear in that mark's **own feasible set** — a member that
   already passed its own check with its own loads and span. Unification never assumes a member
   is adequate because a sibling mark's was.

So unification can waste lumber. It cannot weaken a member.

---

## 5. The weight model

The objective is **dollars**, not an index. Two reasons, and the second is the important one:

1. A weight with no unit cannot be argued with, and an engineer who cannot argue with a number
   cannot own it.
2. Scores in dollars are comparable **across regions**. Min-max normalisation inside a candidate
   set would make every region's scores look alike and the cross-state comparison in §7
   meaningless.

| Weight | Units | What it is for |
|---|---|---|
| `material` | multiplier | Scale lumber against everything else. |
| `baseBfUSD` | $/board-foot | Fallback price when a pack does not price a species. |
| `waste` | multiplier | The offcut between the span and the stock length it is cut from. Lumber comes in even 2 ft lengths; a 13'-0" rafter is cut from a 14-footer. |
| `laborPerPiece` | $/piece | Cut, place, nail. Independent of size. |
| `laborPerLb` | $/lb | Handling. A 4x12 is a two-man lift. |
| `depthPerInchSf` | $/sf per inch | What structural depth costs downstream — plate height, siding, drywall, HVAC chase, brick coursing. |
| `stockPenaltySf` | $/sf at zero availability | Prorated by availability. A member the yard does not rack is not free. |
| `unsourcedCF` | $/member | Review time when `C_F` is held at 1.00 because the catalog is silent. Not lumber — engineering. |
| `slackPenalty` | $ per unit unused capacity | Breaks ties toward the member that works for its living. Deliberately small; it must never outweigh a real cost difference. |
| `skuPenalty` | $/distinct SKU on the plan | The repeatability lever. Scale it to the subdivision, not the house. |

Per candidate:

```
area      = repetitive ? (spacing_ft × span)   : (trib × span)      [sf served by one piece]
length    = next even 2 ft ≥ span + 0.5, clamped to [8, 24]         [ft]
material  = boardFeet × $/bf × material
labor     = laborPerPiece + laborPerLb × weight_lb
waste     = offcut board-feet × $/bf × waste
depth     = d_in × depthPerInchSf × area
stock     = (1 − availability) × stockPenaltySf × area
risk      = unsourcedCF if C_F is held, else 0

score     = material + labor + waste + depth + stock + risk + slackPenalty(DCR)
```

`slackPenalty` is applied **only after feasibility is established**, which is what makes Rule 2
mechanical rather than a promise.

### 5.1 What the weights are and are not

Every number in `weights.js` carries a class marker:

- **`code`** — a code or standard value, reproduced with its citation. Live loads, the roof live
  load minimum.
- **`site`** — site-specific and unknowable from a state name: ground snow, basic wind speed,
  exposure, seismic. What is carried is a **planning default for laying out a repeatable plan**
  and must be replaced with the ASCE 7 Hazard Tool / AHJ value before anything is stamped.
- **`market`** — prices, availability, labor, the cost of another SKU, dead-load takeoffs. These
  have **no code standing at all**. They are the firm's numbers and they ship as placeholders.

The prices in this build are placeholders and are labelled as such in the UI. They are the first
thing a firm should overwrite with its own purchasing data, and doing so changes only which
passing member is recommended — never whether it passes.

---

## 6. Regional packs

Two packs per state, because the inside of a state is not one market and is certainly not one
load case.

| Pack | Markets | What actually differs |
|---|---|---|
| `tx-i35` | DFW · Austin · San Antonio | Lr governs, `C_D` 1.25. SYP staple, SPF widely stocked, DF-L pays freight. |
| `tx-gulf` | Houston · Beaumont · Corpus Christi | No snow. **Wind governs**, and this engine does not check it. Open porch framing treated as wet service. |
| `nc-piedmont` | Charlotte · Raleigh · Greensboro | Ground snow small enough that the 20 psf roof live load governs — so `C_D` stays 1.25. |
| `nc-mountain` | Asheville · Boone · Brevard | **Snow governs, so `C_D` drops to 1.15.** That is a real capacity reduction, not bookkeeping, and it is the single largest structural difference between the two NC packs. |
| `fl-central` | Orlando · Tampa | No snow. Wind governs. Lanai framing wet-service; PT in contact with masonry. |
| `fl-hvhz` | Miami-Dade · Broward | **Concrete tile roof: 27 psf dead instead of 15.** Tighter DCR target, because the same section is about to be checked for uplift. |

The `roofLoadBasis` field on every pack records *why* the roof load is what it is and which
duration factor follows from it. A pack that declares a roof load as snow instead of roof live
moves `C_D` from 1.25 to 1.15 — an 8% capacity change on every bending check in the plan. That
is not a field to set casually, so it is a field that has to explain itself.

### 6.1 The honesty requirement on the coastal and HVHZ packs

Three of the six packs are in markets where **wind, not gravity, decides the design.** This
engine checks gravity only (`calc-spec.md` §8.11). Those packs carry a `governs: "wind"` flag and
a `governsNote` that the UI surfaces on every result:

> In the HVHZ, gravity sizing is not the design. Uplift, the continuous load path, and product
> approval decide what gets built, and none of those are in this engine. Treat a result from this
> pack as a gravity floor on the member size and nothing more.

A tool that returned a confident rafter size for a Miami tract home without saying that would be
worse than no tool.

---

## 7. The repeat matrix

`FM.solver.compare(plan, packs)` solves one plan against several packs and reports, per mark,
what the member is in each and whether it changed. That is the actual question a production
builder asks: *this plan sells in three states — what has to change?*

The answer is usually "less than you would think, and not the marks you would guess." The value
is not the sizes; it is knowing which marks are **common** across the whole program (build them
the same everywhere, buy them in one order) and which are **regionally forced** — and, for
those, exactly which variable forced them: snow duration in the NC mountains, tile dead load in
the HVHZ, species availability in Florida.

---

## 8. What the solver does not do

Everything in `calc-spec.md` §8 still applies, unchanged. On top of that, specific to the search:

1. **No multi-ply built-up members.** The 2-2x10 header that appears in nearly every tract plan
   in these three states is out of scope, because ply-to-ply load sharing is out of scope
   (§8.6). The ladders therefore offer solid 4x headers, which is not what most of these houses
   are actually built with. **This is the largest single gap between this tool and the work.**
2. **No engineered lumber.** LVL, LSL, PSL, glulam headers, I-joists, open-web trusses (§8.19).
   A 16 ft garage-door header in a production plan is an engineered header; the solver correctly
   finds no solid-sawn solution and says so, and cannot propose the thing that would work.
3. **No trusses.** A production roof in Texas and Florida is usually a truss package designed by
   the truss supplier. The plans in `weights.js` are stick-framed on purpose and say so.
4. **No layout.** The solver sizes the marks it is given. It does not decide spans, tributary
   widths, bearing locations, or where a beam goes.
5. **No connections, uplift, or lateral.** Including on the members it just sized.
6. **No 14 in and wider sawn sections**, per §3.
7. **The weights are placeholders.** Until a firm replaces them, the *ranking* among passing
   members reflects assumed prices — the feasibility does not.

---

## 9. Gap register — additions

Continuing `calc-spec.md` §9. These are the gaps the solver introduced or exposed.

| # | Gap | Status | Action |
|---|---|---|---|
| S1 | **Multi-ply built-up members** (2-2x10, 3-2x12) | Out of scope per §8.6; the dominant real-world header in all three states | Highest-value scope extension. Needs NDS 15.3 / load-sharing treatment, not a fudge factor. |
| S2 | **Engineered lumber** for spans solid sawn cannot reach | Out of scope per §8.19 | Without it the solver cannot answer the garage-header question, which every tract plan asks. |
| S3 | **IBC Table 1604.3 total-load deflection, roof rows** | **Adjudicated — see §9.1.** `engine.js` is correct on the two rows that matter; `calc-spec.md` §5.5 is in error and the fixture `ex1_defl_total = 0.375` is wrong. One cell (`roof_no_ceiling` total) remains open. | Correct §5.5, its fixture, and the `engine.js` comment block in one commit. Do NOT change the engine. |
| S7 | **IRC vs IBC** | Repeatable one- and two-family homes are permitted under the **IRC**, whose deflection table R301.7 has no `D + L` column at all. The total-load row this tool reports for a rafter is an IBC-derived firm overlay, not an IRC requirement. | Region packs now carry `code.family`. The `DEFL` table still needs an IRC/IBC switch and its `cite` strings still say "IBC" unconditionally. |
| S8 | **One roof load, one duration** | The engine carries a single `roofLoad` tagged either snow or roof-live, so `D + Lr` and `D + S` can never be evaluated in the same run. Between roughly 17 and 20 psf roof snow, snow governs strength while roof-live governs deflection — and no single setting produces both. That band is in the North Carolina market. | Carry `q_Lr` and `q_S` separately and enumerate all six §2.1 combinations. `combosFor()` must move in lockstep; the "solver combos match engine combos" test is what catches the drift. |
| S4 | **Region price and availability data** | Placeholders | Replace with the firm's purchasing data. Affects ranking only. |
| S5 | **Ground snow, wind, exposure, seismic per site** | Planning defaults | Replace with ASCE 7 Hazard Tool / AHJ values. `nc-mountain` is the one where this changes the answer, because it changes `C_D`. |
| S6 | **Dead-load takeoffs** (15 psf shingle, 27 psf tile, 12 psf floor, 10 psf ceiling) | Market values, not code | Confirm against the actual assembly schedule per plan. Tile in particular varies widely by product. |

### 9.1 The deflection conflict, adjudicated

Two documents shipped in this repository disagreed, and the disagreement changes
every roof member the solver picks. It has been adjudicated rather than left open.

**IBC Table 1604.3 has three load columns — `L` | `S or W` | `D + L` — and
`calc-spec.md` §5.5 reproduces only two.** It collapsed the identical `L` and
`S or W` columns into "Col 1", then reprinted those same values under a heading
labelled `D + L`. The real `D + L` column was dropped, and every conclusion §5.5
draws from its two-column table follows from that.

| Row | `L` | `S or W` | `D + L` | `engine.js` | Verdict |
|---|---|---|---|---|---|
| Roof, plaster or stucco ceiling | ℓ/360 | ℓ/360 | ℓ/240 | 360 / 240 | **engine correct** |
| Roof, nonplaster ceiling | ℓ/240 | ℓ/240 | ℓ/180 | 240 / 180 | **engine correct** |
| Roof, not supporting a ceiling | ℓ/180 | ℓ/180 | ℓ/120 | 180 / 180 | engine **over-conservative** |
| Floor members | ℓ/360 | — | ℓ/240 | 360 / 240 | both correct |

The engine is therefore not unconservative anywhere against the printed table,
and the spec's `ex1_defl_total = 0.375` is the wrong number — **0.281 is right.**

**What was done, and deliberately not done:**

- **The engine is unchanged.** The test pins `0.281` with the conflict printed
  beside it, so the fixture cannot be quietly "fixed" by tightening the engine —
  which would have made every rafter in the product deeper than any of the three
  states requires.
- **`roof_no_ceiling.total` was left at ℓ/180 and NOT relaxed to ℓ/120.** That
  cell carries medium confidence, not high, and the printed table could not be
  opened directly. Relaxing a deflection limit on medium confidence is the one
  move this product must not make. As shipped it demands about 14.5% more depth
  than the code requires on a deflection-governed porch beam — wrong in the
  direction that costs money rather than the direction that costs buildings.
- **Still open:** `calc-spec.md` §5.5's table, the `ex1_defl_total` fixture, the
  `ex2_glulam_defl_total` / `ex2_overall` fixtures (which fail the same way, and
  whose correction destroys Example 2's stated purpose as the deflection-governed
  case — it needs a new load case, not a new limit), and the comment block above
  `DEFL` in `engine.js`, which recites the wrong rule over correct code. That
  comment is the dangerous one: a maintainer reconciling comment to code would
  break the engine.

**How much it is worth.** `DCR_defl ∝ k/d³`, so ℓ/240 → ℓ/180 permits 33% more
deflection, requires 25% less `I`, and permits a member about 9.1% shallower. On
a discrete 2x ladder the adjacent-rung `I` ratios are 2.08 (2x8→2x10) and 1.80
(2x10→2x12), both larger than 1.333 — so the wrong cell can never move a pick by
more than one nominal depth, and moves it by exactly one in roughly four out of
ten deflection-governed cases.

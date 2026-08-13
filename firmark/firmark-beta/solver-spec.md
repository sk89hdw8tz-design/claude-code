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
> it cannot promote a failing one.

Rule 2 is pinned by **`solver · Rule 2: no weight can make a member pass`**. Read what it
actually does, because the difference matters: it takes one demand, rewrites **every key in
`policy.weights`** to 0 and then to 10⁶, and asserts the feasible set is the same string both
times and that nothing above the DCR target entered it.

It does **not** perturb the gates. `minAvailability` is a field on the *policy*, not a member of
`policy.weights`, so the test never touches it — and raising that floor from 0.10 to 0.90
collapses a feasible set from five members to one. Rule 2 as written is true and is narrower than
it sounds:

> **A market number cannot make a failing member pass. It can make a passing member vanish.**

### 0.1 Where the scope boundary actually is

`calc-spec.md` §8.23 says: *"This is a member check, not a design. It does not select sections,
iterate, or optimize."* That sentence describes the **engine**, and it is still true of the
engine. This document describes a layer built on top of it.

An earlier printing of this section said the boundary had moved "by exactly one step and no
further" and that the solver "has no opinion about framing layout or load path." Both claims were
false as soon as they were read against the files. What is true:

| The claim §8.23 makes about the engine | What this layer adds on top of it |
|---|---|
| Does not select sections | **The solver selects sections and iterates**, walking ladder × palette × spacing. |
| — | **`weights.js` is a framing layout and a load path.** Every mark declares a span, a tributary or a run, what it carries, where it bears and how many jack studs are under it; `HDR-W`'s 23.0 ft tributary is a statement that the trusses bear on that wall, and `HDR-GAR-G` and `HDR-GAR-B` are the same opening under two different truss directions. Those are layout decisions. They are authored by hand, they are the largest single determinant of the answer, and PE-1 and PE-2 were both wrong-tributary defects, not solver defects. |
| — | **Availability decides feasibility before the engine is called.** `eligibility()` runs inside `families()`, ahead of every engine call: a member under `minAvailability` is never checked at all. A market number is therefore in the feasibility path, not only in the ranking. |
| — | **Unification changes the delivered member for economics.** `unify()` raises a mark onto a sibling's size when the modelled SKU saving beats the extra lumber. The raised member passed its own check first, so nothing is weakened — but the member on the schedule is not the member the search chose. |
| — | **The firm's DCR target refuses members the code accepts.** `calc-spec.md` §6.2 passes at DCR ≤ 1.000. A pack target of 0.90 refuses a member at 0.95 that the code permits. That is the firm's envelope, not the code's, and the schedule says so. |

So the honest statement of the boundary is not "one step":

> The **engine** still checks one member against one demand and decides nothing else.
> This layer **authors the demand**, **filters which members are offered on market grounds**,
> **searches**, **ranks on the firm's money**, and **applies the firm's own acceptance
> threshold**. Everything in `calc-spec.md` §8 that the engine does not do, this layer does not
> do either — no lateral, no connections, no multi-ply, no engineered lumber, no layout it was
> not handed. A licensed engineer owns the layout, the loads and the result.

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

**Repetitive members** — `REPETITIVE` in `weights.js` names them, and they are rafter, joist,
ceiling and deck — pass `spacing` straight through. Per `calc-spec.md` §1.3 case (a),
self-weight is already inside `q_D` and is **not** added again.

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

`C_i`, the incising factor, moves the same way and for the same reason. A refractory species must
be incised to take preservative, so a treated mark in one carries `C_i = 0.80` on `F_b`, `F_t`,
`F_v` and `F_c` and 0.95 on `E` (NDS Table 4.3.8). That was once handled by *excluding* those
species from treated marks — a containment, and one keyed on moisture rather than on treatment,
which meant a single price change could route around it. It is now computed.

The refusal is the important one. Holding `C_F` at 1.00 is **conservative** everywhere the
catalog is silent *except* at 14 in and wider, where Table 4A publishes a factor below 1.00 that
the catalog does not carry (gap register #1). Rather than hold a value it cannot show to be
conservative, the engine refuses the section and says why. The regional ladders in `weights.js`
therefore stop at 12 in, and a 14 in member requires a typed `C_F` and an engineer who takes
responsibility for it.

---

## 4. The heuristics

Seven heuristics, H1–H7. Each is stated with the argument for why it is *sound* — meaning it
cannot change the answer, only the work done to reach it — or, where it is a genuine heuristic
that only affects ordering, said so plainly. Three further subsections (§4.8–§4.10) describe
machinery that is not a heuristic but belongs with the search: what comes back when nothing fits,
the two inputs that have no default, and the pass that fills in the ladder for display.

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
| `F_b`, `F_v`, `E` and `F_c⊥` are maximised **independently** across the palette | The bound therefore corresponds to a best-of-all-worlds material that may not exist. Each of the four bounds is independently valid, so this is safe — it is the reason pruning is weaker than it could be, not a hole. |
| Bearing bounds **breadth**, not depth, and carries no `C_D` | `C_D` does not apply to `F_c⊥` (NDS Table 4.3.1), and `f_c⊥ = R/(b·l_b)` has no depth term. |

Since every bound understates what is required, a candidate failing a bound fails the real
check. The converse is not claimed and is not needed.

**Bearing is not a section wall, and is not treated as one.** `passesBounds` still evaluates
`b_req`, but a failure there returns `bearing: true` and is recorded as a bearing gate rather than
a section shortfall. Every rung in a header ladder is the same breadth, so a bearing shortfall
empties the whole ladder at once — and it was then reported as a stiffness problem, in a product
whose own repair table says of bearing *"depth does nothing."* See §4.8.

**The proof is relative, not absolute.** The bounds are admissible with respect to
`FM.engine.run()` — not with respect to the NDS. Where the engine is conservative or silent, the
bound inherits that. `C_i` is no longer an example of it: the engine applies the incising factor,
and `seedBounds()` applies the same 0.80 / 0.95 reductions when building `Fb_best`, `Fv_best` and
`E_best`, taking the maximum across the palette so the bound stays optimistic. There is no longer
an eligibility gate excluding refractory species; the containment became the calculation.

**This is a claim, so it is tested — and the test is weaker than this document used to say.**
The regression suite **`solver · pruning is admissible — exhaustive vs pruned`** builds an
exhaustive reference — every candidate in ladder × palette × spacing through the real engine,
subject to the same policy gates, ranked on the same per-unit objective — and compares it to the
pruned search across a battery of **204 demands** — 6 packs × 5 roles × the spans listed for
each role × braced and unbraced.

What it compares is **the winning candidate and its score**. It does **not** compare the full
feasible sets, and it does not cross `wet`, `treated`, `trib`, `bearing` or `maxDCR`, and its
battery contains no `deck` role. Two earlier printings of this paragraph claimed a full
feasible-set comparison; that claim is what a review specialist was replaced for, and it was
still here after the round that recorded it as corrected. It is written here as what the shipped
test does.

A larger battery has been run against this code by hand — 20,736 demands and 120,841 feasible
rows compared candidate-for-candidate, with zero mismatches — and it is the strongest evidence
the pruning is admissible. It is **not in the suite**, so it does not stop a regression, and it
is not a pin. Two claims, kept separate on purpose.

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
the incumbent. A family whose lower bound is **strictly above** the incumbent's score is skipped
entirely; a family that merely ties is walked, because a tie can still win on tie-break.

Soundness, in the units the code actually compares (§5): both the family bound and the incumbent
score are **per unit of building**, so

```
score = (cost + slack) / unit  ≥  cost / unit  ≥  min over the family of (cost / unit)
```

`slack` is never negative, so no candidate in the family can score below the family's bound.

Ordering cheapest-first is what makes this bite: the incumbent gets good on the first family, so
the bound prunes hard immediately.

The same bound is applied a second time *inside* a family, and that one is guarded: a candidate
costing more than the incumbent ends the family only when `fam.monotone` is true, and otherwise
is skipped while the walk continues. Breaking unguarded on a per-size price vector returned a
member at 5.6× the correct cost. Pinned by
**`solver · incumbent pruning survives a non-monotone price vector`**.

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
machine.

Tie-break decides ties and **not losses** — reaching it on a strictly worse score let a more
expensive candidate take the incumbency, so the incumbent update tests `score < incumbent − ε`
first and only consults `tieBreak` inside `|Δscore| ≤ ε`.

The recommendation is **the head of the ranked list**, not the search incumbent:
`pick = feasible[0]`. Those were two different selections — one made in search order, one by
tie-break — and on an exact score tie they disagreed, so the recommendation could contradict the
table printed beside it. The search still asserts its own optimality afterwards
(`stats.searchOptimal`), comparing incumbent to `feasible[0]` on score **and** tie-break.

Pinned by **`solver · determinism, calc-spec §6.2`** — which re-runs one demand and then reverses
both the palette and the ladder, asserting the same pick — and by
**`solver · the pick is the head of the ranked list`**.

### H6 — Memoization (sound)

Engine results are cached on the full input signature. The same physical member is reached from
several families and spacings; it is checked once. Reported as `cacheHits` so the search's work
is visible rather than claimed.

### H7 — SKU unification across a plan (the repeatability heuristic)

This is the one that matters for a plan built a hundred times.

Per-mark optimisation produces a schedule where marks land one rung apart — a 2x8 here, a 2x10
there. Each distinct size is a SKU: pallet space on a tight lot, a separate pick, another chance
for a framer to grab the wrong one.

Marks are grouped by `skuGroup` (falling back to `role`), and a group of fewer than two marks, or
one that already holds a single SKU, is left alone. **Every distinct size already picked inside
the group is then enumerated as a candidate target** — not just the deepest one. That matters: a
group of {2x8 ×10, 2x10 ×40, 2x12 ×1} should raise the 2x8s to 2x10 and leave the single 2x12
alone. Considering only the deepest member made "collapse all 51 pieces onto 2x12" the only
answer available. The target with the **minimum net cost** wins, and it is accepted only if that
net is at or below zero:

```
delta(target) = Σ over raised marks of (pieceScore_target − pieceScore_own) × pieceCount(mark)
saved(target) = (SKUs_before − SKUs_after) × skuPenalty
                 + UNIFY_BONUS(group)   only if SKUs_after == 1 AND the group had >1 size and now has 1

target is a candidate only if saved > 0
accept the best target if   delta − saved ≤ 0
```

Four constraints make it safe:

1. It never collapses **downward.** A mark whose pick is deeper than the target keeps its own
   pick and contributes its own SKU to the after-count. (A lateral move to the same depth in a
   stronger grade is permitted; the system bonus is not paid for it, because no band and no
   single rim depth is created.)
2. The raised member must appear in that mark's **own feasible set**, at that mark's **own
   spacing** — a member that already passed its own check with its own loads and its own span.
   If it is absent, the whole target is abandoned rather than assumed. Unification never infers
   that a member is adequate because a sibling mark's was.
3. `pieceCount` for a repetitive mark is derived from its `runFt` and the spacing the solver
   chose, not read from a fixed count on the mark — otherwise the arithmetic prices a quantity
   the solver is free to change.
4. It compares **scores**, not raw costs. Raising a member always increases its slack, and
   `slackPenalty` is inside the score; comparing raw costs mispriced every move systematically.

So unification can waste lumber. It cannot weaken a member.

Pinned by **`solver · SKU unification actually fires`** (a move is accepted somewhere across the
18 pack × plan runs, so H7 is reachable rather than structurally dead) and
**`solver · SKU unification only ever collapses upward`** (no raised mark is shallower than its
own pick, none is above the DCR target, and none was raised onto a member absent from its own
feasible set).

`unify()` was once structurally dead: it looked for the raise target in `solution.feasible`, which
held only what the optimiser had evaluated, and the dominance break stopped each family at its
first feasible rung — so a sibling's deeper size was never in the list. The **explain pass**
(§4.10) is what makes H7 reachable.

### 4.8 — What comes back when nothing fits: one escalation classifier

Escalation is a status, not a footnote. A plan carrying one is not a finished schedule and must
not read like one.

There is exactly **one classifier**, and it produces both the `status` and the `note`. Status and
note were once decided independently, in two places, and disagreed: `escalate:strength` was set
first on any evaluated candidate, so three of the four statuses then defined were unreachable
while the note took a different branch in the same object.

| Status | Set when | The note's move |
|---|---|---|
| `ok` | a member was picked | — |
| `escalate:procurement` | a gated-out member was run through the engine **and passed** | name it, and its measured DCR: confirm the yard will supply it, or lower the floor deliberately |
| `escalate:bearing` | the bearing bound emptied the ladder and nothing else was evaluated | lengthen the bearing — a second jack stud. Depth does nothing. |
| `escalate:geometry` | a depth-budget gate emptied the ladder and nothing else was evaluated | raise the plate, drop the head height, or flush-frame it |
| `escalate:strength` | everything else: no section reaches the requirement, or every candidate evaluated was overstressed | the shortfall wall, below |

Order matters and is the point of the fix. Falling through to whichever gate happened to appear
in the rejection list reported a member 4% short on section modulus as a procurement problem,
with the advice *"lower the availability floor"* — which, followed, yields nothing.

A sixth status, **`escalate:input`**, short-circuits ahead of all of them: a non-numeric `dead`,
`live`, `roofLoad`, `span` or `bearing` refuses the **whole search** rather than proposing
members for it. `Number(x) || 0` turns `NaN` into `0` and designs the member for no load; the
engine refuses that, but the solver used to launder it before the engine ever saw it.

**What fires today.** Across all 30 shipped pack × plan runs — 6 packs × 5 plans — three
statuses occur: `ok` (136), `escalate:strength` (37) and `escalate:procurement` (1).
`escalate:bearing`, `escalate:geometry` and `escalate:input` are reachable — each has been
produced from a hand-built demand — but **no shipped pack or plan produces them.** Their
correctness rests on the code path and on those probes, not on the shipped configuration.

**The shortfall wall.** When the status is `escalate:strength`, `boundWall()` names the section
property that emptied the ladder and by how much:

> *"the deepest section in the ladder gives 73.83 in³ of S_x and this member needs 252.84 — short
> by 242% at the firm's DCR target of 0.90"*

It ranks the three section properties by **dimensionless shortfall ratio** — `required ÷ what the
deepest rung in the ladder offers` — and skips any property the ladder already satisfies. Ranking
by raw magnitude compares in³ against in⁴ against in², which `I_x` wins essentially always: it
was named in **17 of 17** reports, seven of them naming a property the ladder cleared by up to
68%. Bearing is excluded from this wall entirely, because it is not a property of the section.
Pinned by **`solver · the reported wall is the one that actually binds`**, which asserts across
every pack × plan that no reported wall has `shortfall ≤ 1` or `required ≤ available`. The
example above is the real `HDR-GAR-B` wall in `tx-i35`; §8 item 2 quotes the same one.

**Nothing is named as passing unless the engine returned a DCR for it.** The procurement gate runs
inside `eligibility()` *before any engine call*, so the note that read *"the member that passes …
The member is adequate"* was an assertion about a member nobody had checked. Measured across 112
escalations, **82% named only overstressed members**, one at DCR 2.025. Gated candidates are now
each run through the engine; only those that actually pass are named, each with its measured DCR,
and the note states how many others were checked and failed. Pinned by
**`solver · nothing is named as passing unless the engine checked it`**, which walks every
procurement note in every pack × plan and asserts that each member named carries a
`checkedDcr` at or below that mark's target.

The general rule, of which that is one instance:

> **No member may be described as adequate unless `FM.engine.run()` returned a finite DCR for it
> at this mark's own demand.** Not a sibling's, not a bound's, not a gate's.

Bound-pruned candidates and gate-excluded candidates both enter the rejection record with their
reason rather than being discarded, because *"we never checked a 4x14"* and *"a 4x14 failed"* are
different statements and an engineer needs to know which.

**`solver · the escalation status and its note come from one classifier`** asserts across every
pack × plan that `ok` always carries a pick, that no escalation does, and that a procurement note
appears **if and only if** the status is `escalate:procurement`.

### 4.9 — The two inputs that have no default

Both were defaults once. Both produced blockers. Both now throw.

**`carries`.** A mark's `role` is a name; its `carries` is the structure. Deriving the load set,
the duration factor and the deflection row from the role string checked `DK-2`, a treated deck
beam, with 15 psf of insulated shingle-roof dead load, **zero** of the 40 psf deck live load,
`C_D` 1.25 instead of 1.00 and ℓ/180 instead of ℓ/360 — and printed a 4x8 at DCR 0.594 for a
member overstressed at 1.047 against the load it actually carries. `GB-1`, a floor girder, had the
same defect.

`CARRIES_DEFAULT` now covers `rafter`, `ceiling`, `joist` and `deck` only. **`header` and `beam`
are deliberately absent**: a joist carries a floor by definition, but a beam carries whatever the
plan puts on it, and guessing `roof` is precisely the defect above. A header or beam that does not
declare `carries` throws, and so does an unrecognised `carries` name — silently returning
`undefined` for a typo laundered into a dead load of zero.

`carries: "roof+floor"` cannot be expressed with one tributary, and its two users meant opposite
things by it. Such a mark must declare **`tribRoof` and `tribFloor`** separately; the two load
paths are then converted into the engine's single-tributary vocabulary as a total line load
`q_roof·t_roof + q_floor·t_floor` expressed as psf over the summed tributary. A mark declaring
`roof+floor` without both throws.

**`bearing`.** Moving headers from a 3.5 in default to a jack stud's 1.5 in was correct — and it
promoted bearing from a benign assumption into a design input. It governs picks, it produced
escalations, and **not one mark declared it.** A header must now declare its jack count as a
bearing length; a header without one throws. Every shipped header declares one, asserted by
**`weights · a header must declare its jack count`**.

One caveat this document owes: `memberInputs()` still falls back to `bearing: 1.5` when a demand
arrives without one. The no-default rule is enforced in `weights.js`, at `demandFor()`, so it
binds every mark on every plan — but a demand assembled by hand in a test or a console still gets
the fallback.

**What pins the pair.** `weights · every mark is checked as the member it actually is` is a
property test over every mark in every plan in every pack. Precisely, it asserts: a roof mark
carries the pack's roof load and zero floor live; a floor or deck mark carries the right live load
and the floor deflection row; an open-roof mark is on the no-ceiling row and a mark with a ceiling
is not; a `roof+floor` mark's two **line** loads reproduce `tribRoof` and `tribFloor` and its
tributary is their sum; and an exterior mark is treated. It does **not** assert the dead load or
`C_D` directly — an earlier printing of this claim was broad enough that mutation testing showed
the literal defect would have passed it.

### 4.10 — The explain pass

The search is an optimiser: it proves which candidate wins while evaluating as few as it can.
That is right for a solver and wrong for a sheet an engineer has to sign, because it can return a
single row with nothing to compare against.

So once the winner is settled, the rest of the admissible ladder is evaluated for display. Those
evaluations are counted separately (`stats.contextEvaluated`) — they are context, not search —
and they are walked in a **fixed order that does not depend on the weights**, so the ladder an
engineer sees is the same ladder whatever the prices are. The pass has a budget
(`policy.explainBudget`, 40 by default) and reports `stats.ladderComplete` when it did not
exhaust the ladder, rather than truncating silently.

The explain pass is also what makes H7 reachable at all, and it is the reason `feasible` is a
usable set rather than a record of what the optimiser happened to touch.

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
| `dropHandling` | multiplier | Sorting, stacking and disposing of the offcut, net of salvage. Material is charged over the **full** stick, because that is what you buy — charging the drop again as "waste" was a double count, and this is **not** an estimating waste factor. |
| `cullRate` | fraction, per palette entry | Crook and twist on re-equilibration, worse in humid markets. Applied to material cost. |
| `laborPerPiece` | $/piece | Cut, place, nail. **Role-keyed** — an interior header is not a floor joist and an exterior lanai beam is neither. |
| `laborPerLb` | $/lb | Handling. A 4x12 is a two-man lift. |
| `depthPerInchSf` | $/sf per inch | What structural depth costs downstream — plate height, siding, drywall, HVAC chase, brick coursing. **Role-keyed**: a floor joist's depth is building height, a rafter's mostly is not. |
| `minAvailability` / `specialOrderBelow` | fraction | **Not a weight — a gate, and it is in the feasibility path.** `minAvailability` is consumed by `eligibility()` before any engine call, so a member below it is never checked at all; `specialOrderBelow` sits above it and only *labels* the pick a special order. Set the floor low: a floor of 0.35 against the dry-4x tier silently excluded every dry 4x in every pack and turned a market placeholder into what read as an engineering finding. It is listed here because it lives beside the weights, and it is the one number in this table that Rule 2 does not cover. |
| `UNIFY_BONUS` | $/plan, per SKU group | The system effect of collapsing a group to ONE SIZE — one rim depth, one hanger SKU, one subfloor elevation. Paid only on a real size collapse, never on a same-size grade swap. |
| `stockPenaltySf` | $/sf at zero availability | Prorated by availability. A member the yard does not rack is not free. |
| `unsourcedCF` | $/member | Review time when `C_F` is held at 1.00 because the catalog is silent. Not lumber — engineering. |
| `slackPenalty` | $ per unit unused capacity | Breaks ties toward the member that works for its living. Deliberately small; it must never outweigh a real cost difference. |
| `skuPenalty` | $/distinct SKU on the plan | The repeatability lever. Scale it to the subdivision, not the house. |

Per candidate:

```
area      = repetitive ? (spacing_ft × span)   : (trib × span)      [sf served by one piece]
length    = next even 2 ft ≥ span + 0.5, floored at 8 — NO UPPER CLAMP     [ft]
material  = boardFeet × $/bf × material × (1 + cullRate)
labor     = laborPerPiece + laborPerLb × weight_lb
drop      = offcut board-feet × $/bf × dropHandling
depth     = d_in × depthPerInchSf × area
stock     = (1 − availability) × stockPenaltySf × area
risk      = unsourcedCF if C_F is held, else 0

cost      = material + labor + drop + depth + stock + risk
unit      = repetitive ? area served : 1 piece
score     = (cost + slackPenalty(DCR)) / unit
```

`slackPenalty` is applied **only after feasibility is established**, which is what makes Rule 2
mechanical rather than a promise.

**`length` has no upper clamp**, and the absence is deliberate. It was clamped at 24 ft, which
billed a 46 ft member as a 24-footer and gave it a **negative** drop cost — `(len − span)` went
negative. The longest stick a yard racks is a supply constraint, which belongs in availability;
it is not a discount. Pinned by **`solver · policy inputs are bounded`**, which also asserts the
DCR-target clamp: a policy may set a target tighter than 1.00 and never looser, because
`calc-spec.md` §6.2 allows no tolerance band.

**The ranking unit is not the piece.** A member at 16 in o.c. and the same member at 24 in o.c.
do not do the same amount of work, so ranking two spacings on per-piece cost silently prefers
the tighter one. That is how the solver came to recommend 16 in o.c. roofs to three markets that
sheathe everything at 24. Repetitive members are ranked **per square foot of framed area**;
single members per piece. SKU unification and the plan cost rollup stay per-piece, because those
are per-piece questions — the two numbers are carried separately as `score` and `pieceScore`.

**And the loads follow what a member carries, not what it is called.** See §4.9 — `carries` and
`bearing` are the two inputs with no default, and what the property test that pins them does and
does not assert is written out there rather than summarised here.

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
| `fl-central` | Orlando · Tampa · Punta Gorda | No snow. Wind governs. Lanai framing wet-service; PT in contact with masonry. |
| `fl-hvhz` | Miami-Dade · Broward | **Concrete tile roof: 22 psf dead instead of 15.** Tighter DCR target, because the same section is about to be checked for uplift. |

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

### 7.1 Master sets and variants

The repeat matrix answers *one plan across several markets*. A master set is the other axis:
**one plan across several versions of itself.** A production plan is stamped once and built as
three to five **elevations** and four to ten structural **options** — tile instead of shingle, a
bonus room over the garage, an extended patio, 8 ft doors on the first floor. Every lot in the
subdivision is one combination of those, and the stamped set has to cover all of them.

`weights.js` carries the master set on the plan and exposes it through five helpers:

| Helper | What it returns |
|---|---|
| `variantsFor(plan)` | The normalised set: `elevations`, `options`, and **`combinations`** — the enumerated configurations the builder actually builds, each with an expected lot count and the marks it `touches`. |
| `planForVariant(plan, id)` | A materialised plan for one combination, with overrides applied and added marks in. Feed it straight to `solvePlan`. |
| `variantPlansFor(plan)` | Every combination, materialised. |
| `markFor(plan, markId, id)` | One mark as it exists in one combination. |
| `envelopeFor(plan, markId, pack)` | The per-mark envelope across combinations: the worst value of each demand driver and which combination supplies it, whether one combination **dominates** every other, and `split: true` when none does. |

An elevation and an option each carry a `takeRate`; an elevation's is the lot mix, an option's is
an attach rate, and both are `[market]` estimates with no code standing. A variant declares its
effect as `overrides` on marks, `add` and `remove` for marks that exist only in some
combinations, and a plan-wide key such as `roofAssemblyKey` — the tile option names no mark and
moves every roof mark on the sheet. `touches` is the resolved answer that accounts for all three.
A variant may also declare `movesNoMember: true`, which is a claim being exercised rather than an
omission.

**What the solver does with them: it sizes one combination.** `size()` optimises one demand per
mark, and the marks it is handed are one combination's. It does not solve an envelope, and
`takeRate` reaches no part of the search. What exists is the **demand envelope**, in
`envelopeFor` — a comparison of *demands*, not of members. It can say that combination
`c+opt-tile` is at least as severe as every other on every driver for `BM-LAN`; it does not size
`BM-LAN` for it.

That distinction is the whole gap, and the export refuses to let it be invisible. A schedule
carries:

- the combination it was solved for, by name, and how many combinations the master set has;
- an explicit **one combination, not an envelope** statement;
- the elevations and options with take rates and what each touches, adds or removes;
- and a per-mark table — **does this combination govern?** — naming the governing combination for
  every mark and marking the ones where the member above was sized against a case that is not the
  worst the builder will build.

On `sunbelt-ranch-1850` in `tx-i35`, solved for its own base elevation, **five of its eight
marks are governed by some other combination** — `BM-LAN` and `BM-LAN-W` by `c+opt-tile`,
`HDR-W` and `HDR-SLD` by `a+opt-tile+opt-8ft`, `HDR-GAR-B` by `a+opt-tile`. That is the D11
finding, printed on the deliverable instead of discovered at framing.

Two honesty constraints on that table, both stated on the export itself:

1. **"Governs" compares demands, not members.** No member is re-solved for another combination,
   so the table says which case *should* have been sized, not what it would have produced.
2. **A mark listed as common is common in its declared inputs.** Nothing is re-checked across
   variants, and a mark no variant names can still move when a shared input does.

**What would close it** is an objective change, not a report: solve each mark against the worst
demand across the combinations it is built in — which `envelopeFor` already identifies — and
report the governing combination per mark. Where `envelopeFor` returns `split: true`, no single
combination dominates and there is no single worst case to size; that mark needs either a
per-combination member or a hand ruling, and the tool should say which.

---

## 8. What the solver does not do

Everything in `calc-spec.md` §8 still applies, unchanged. On top of that, specific to the search:

1. **No multi-ply built-up members.** The 2-2x10 header that appears in nearly every tract plan
   in these three states is out of scope, because ply-to-ply load sharing is out of scope
   (§8.6). The ladders therefore offer solid 4x headers, which is not what most of these houses
   are actually built with. **This is the largest single gap between this tool and the work.**
2. **No engineered lumber.** LVL, LSL, PSL, glulam headers, I-joists, open-web trusses (§8.19).
   A 16 ft garage-door header in a production plan is an engineered header, and the solver cannot
   propose the thing that would work. It does say why: `HDR-GAR-B`, the 16'-8" opening under a
   bearing truss line, escalates on strength with *"the deepest section in the ladder gives 73.83
   in³ of S_x and this member needs 105.67 — short by 43%."* An earlier printing of this bullet
   claimed the same thing about the **gable-end** version of that opening, and that claim was
   false twice over: a placeholder availability floor was suppressing a 4x8 that passes at DCR
   0.896, and the gable-end mark is now refused outright for a different reason — it carries a
   triangular wall load, and there is no wall dead load anywhere in the model (§8.3, and gap S9).
   The scope statement stands. Check the example before repeating it.
3. **No trusses.** A production roof in Texas and Florida is usually a truss package designed by
   the truss supplier. The plans in `weights.js` are stick-framed on purpose and say so.
4. **No layout — but `weights.js` contains one.** The *solver* sizes the marks it is given and
   decides no spans, tributaries, bearing locations or beam positions. The **plans** in
   `weights.js` decide all of them, by hand, and they are the largest single determinant of the
   answer: the two blockers a structural PE found were both wrong tributaries, not solver
   defects. See §0.1. Nobody should read "no layout" as "no layout was assumed."
5. **No envelope across a master set.** One demand per mark, per variant. See §7.1.
6. **No connections, uplift, or lateral.** Including on the members it just sized.
7. **No 14 in and wider sawn sections**, per §3.
8. **The weights are placeholders.** Until a firm replaces them, the *ranking* among passing
   members reflects assumed prices. **Availability is the exception** — it is a gate, not a
   weight, and it decides feasibility (§0.1, §5).

---

## 9. Gap register — additions

Continuing `calc-spec.md` §9. These are the gaps the solver introduced or exposed.

| # | Gap | Status | Action |
|---|---|---|---|
| S1 | **Multi-ply built-up members** (2-2x10, 3-2x12) | Out of scope per §8.6; the dominant real-world header in all three states | Highest-value scope extension. Needs NDS 15.3 / load-sharing treatment, not a fudge factor. |
| S2 | **Engineered lumber** for spans solid sawn cannot reach | Out of scope per §8.19 | Without it the solver cannot answer the garage-header question, which every tract plan asks. |
| S3 | **IBC Table 1604.3 total-load deflection, roof rows** | **Adjudicated — see §9.1.** `engine.js` is correct on the two rows that matter; `calc-spec.md` §5.5 is in error and the fixture `ex1_defl_total = 0.375` is wrong. One cell (`roof_no_ceiling` total) remains open. | Correct §5.5, its fixture, and the `engine.js` comment block in one commit. Do NOT change the engine. |
| S7 | **IRC vs IBC** | Repeatable one- and two-family homes are permitted under the **IRC**, whose deflection table R301.7 has no `D + L` column at all. The total-load row this tool reports for a rafter is an IBC-derived firm overlay, not an IRC requirement. | Region packs carry `code.family`, and `export.js` now derives the deflection statement from it rather than printing "IBC Table 1604.3" flat: on an IRC pack the schedule says the total-load row is a **firm overlay** and prints the engine's rows with their citation strings labelled as the engine's, not as the code's. The `DEFL` table itself still needs an IRC/IBC switch and its `cite` strings still say "IBC" unconditionally — the export can label the problem, it cannot fix it. |
| S8 | **One roof load, one duration** | **Closed in the engine, open in the packs.** `engine.buildCombos()` now enumerates all six §2.1 combinations from separate `roofLive` and `snow`, `solver.combosFor()` delegates to it rather than carrying a second implementation, and the legacy `roofLoad` + `roofType` path is preserved bit-identically. The six **shipped packs still declare one `roofLoad` and one `roofType`**, so no shipped pack yet feeds both terms and the crossover advisory still fires. Pinned by **`engine · all six ASCE 7 §2.4.1 combinations, and C_D from nonzero terms only`** and **`engine · snow and roof live are evaluated in the same run`**. | Migrate the packs to declare `q_Lr` and `q_S` separately; until they do, the capability is unexercised in production and the advisory is what carries the exposure. That advisory is pinned by **`solver · the roof-load crossover is surfaced, not silent`**. (A cross-check test was cited here, and is still cited in a comment in `solver.js`, as *"solver combos match engine combos"* — a name no test has ever had. The comparison it named is now tautological anyway, because the solver delegates rather than duplicating.) |
| S4 | **Region price and availability data** | Placeholders | Replace with the firm's purchasing data. Affects ranking only. |
| S5 | **Ground snow, wind, exposure, seismic per site** | Planning defaults | Replace with ASCE 7 Hazard Tool / AHJ values. `nc-mountain` is the one where this changes the answer, because it changes `C_D`. |
| S6 | **Dead-load takeoffs** (15 psf shingle, 22 psf tile, 12 psf floor, 10 psf ceiling, 10 psf open porch) | Market values, not code | Confirm against the actual assembly schedule per plan. Tile in particular varies widely by product. |
| S9 | **No wall dead load exists anywhere in the model** | `ASSEMBLY{}` has zero wall entries | It is what made the gable-end garage header unrefusable rather than checkable (§8 item 2). Printed in `FM.engine.LIMITS`, and the schedule export renders that array rather than restating it, so an item added there reaches the output. The vocabulary is still missing. |
| S10 | **Slope** | No plan declares a pitch, and the assembly psf mix on-slope and horizontal components with no published split | `calc-spec.md` §1.4 makes the horizontal-projection conversion the user's responsibility and the model gives them nothing to do it with. Also in `LIMITS`. |
| S11 | **The admissibility pin is narrower than the claim it supports** | The shipped exhaustive-vs-pruned test compares the winner and the score over 204 demands; it does not compare feasible sets and does not cross `wet`, `treated`, `trib`, `bearing`, `maxDCR` or the `deck` role | Widen the battery and compare sets. Until then the set-level claim rests on a hand-run battery that is not in the suite (§4, H1). |
| S12 | **Three of the six escalation statuses fire on no shipped configuration** | `escalate:bearing`, `escalate:geometry` and `escalate:input` are reachable from hand-built demands and are produced by no shipped pack × plan | Add fixtures that exercise them, or accept that their notes are unexercised in production. `escalate:geometry` in particular falls through to the generic note branch and advises *"widen the palette or the size ladder"* for a member that physically does not fit — the right move (`GATE_MOVE.geometry`) exists and the note does not use it. |
| S13 | **No envelope across a master set** | The master set is fully modelled in `weights.js` — combinations, take rates, added and removed marks, and a per-mark **demand** envelope in `envelopeFor()`. The **solver** still sizes one combination. On the flagship plan at its base elevation, 5 of 8 marks are governed by a different combination. | §7.1. Size each mark against the worst demand across the combinations it is built in, and rule on the marks where `envelopeFor` returns `split` and no combination dominates. Until then the export names the governing combination per mark — a documentation guarantee, not a structural one. |

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

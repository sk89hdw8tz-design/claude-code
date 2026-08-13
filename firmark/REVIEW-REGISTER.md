# Review register — solver, sizing heuristics, regional weight model

Findings raised by the specialist review panel, each with its disposition and the
evidence for that disposition. Anything marked **OPEN** is unresolved and is not
allowed to be closed silently.

Panel: structural PE (A&E), QA/QC, production-build & estimating, building code
& regulatory (TX/NC/FL), software integration & test.

Test suite: `node firmark-beta/test/run-tests.js` — **104 assertions, 0 failing**.
Bundle freshness gate: `node firmark-beta/build.js --check`.

---

## A. Defects found and fixed

| # | Severity | Finding | Disposition | Pinned by |
|---|---|---|---|---|
| A1 | **BLOCKER** | **Seed bounds were maxed across spacings.** `seedBounds()` took `Math.max` over every spacing in the policy, then `passesBounds()` applied that single bound to a candidate carrying its *own* spacing. A 16″ o.c. candidate was judged against the 24″ o.c. load, pruning valid — and optimal — members. Reproduced at 3 of 4 spacing sets; on one case the solver returned *no solution* where a 2x12 @ 12″ o.c. passed. | Fixed. Bounds are computed **per spacing** (`boundsAt(sp)`), and `passesBounds` looks up `bounds.at(cand.spacing)`. | `solver · pruning is admissible — exhaustive vs pruned` (204 demands, exhaustive reference through the real engine) |
| A2 | **BLOCKER** | **Unguarded incumbent break on a non-monotone family.** The in-family `break` asserted "cost only grows with depth" — the exact property `fam.monotone` exists to verify — but was not guarded by it. With a per-size price vector (short supply on one rung, clearance on another) the solver returned a member at **5.6× the cost** of the correct answer. | Fixed. `if (fam.monotone) break; else continue;` | `solver · incumbent pruning survives a non-monotone price vector` |
| A3 | **MAJOR** | **Treated refractory species were checked without `C_i`.** `calc-spec` §4.8 specifies the incising factor (`C_i = 0.80` on `F_b`/`F_v`, NDS Table 4.3.8); `engine.js` does not implement it. Any wet-service mark solved in DF-L, Hem-Fir or SPF overstated capacity by 20%. This was the only genuinely unconservative path found. | Fixed by exclusion, not by approximation. Species that must be incised to take preservative are gated out of any wet demand, with the reason recorded. Southern Pine survives — it takes treatment without incising, which is why it is the porch-beam species of the Southeast. | `solver · gates are recorded, not silent` |
| A4 | **MAJOR** | **Picking Southern Pine errored every sheet.** `speciesList()` now returns three Table 4B species; their grades sorted alphabetically, so `grades[0]` was `"Construction"` — tabulated at 4″ wide only. `sheet.js` substituted it on species change and every 2x10/2x12 sheet went to "Not evaluated". | Fixed in two places: `GRADE_RANK` extended with the Table 4B spellings (`No.1` vs `No. 1`), and `sheet.js` substitutes the **strongest** available grade rather than the first alphabetically. | UI test `ui · switching to Southern Pine keeps the sheet evaluable` |
| A5 | **MAJOR** | **Waste was double-counted.** `costOf()` charged material over the full stock length *and* charged the drop again as waste. A weight named `waste: 1.10` did not mean what an estimator would assume. | Fixed and renamed. Material is charged over the full stick (that is what you buy); `dropHandling` now prices sorting and disposing of the offcut, net of salvage. | Documented in `solver-spec.md` §5 |
| A6 | **MAJOR** | **`unify()` optimised a different objective than `size()`.** The search ranks on `cost + slackPenalty`; unification compared raw costs. Raising a member always increases its slack, so unification was systematically mispriced. | Fixed — unification compares **scores**. | `solver · SKU unification actually fires` |
| A7 | **MAJOR** | **`unify()` only ever considered the deepest member as the target**, so a group of {2x8, 2x10, 2x12} could only collapse all of it onto 2x12. | Fixed — every distinct size in the group is enumerated as a candidate target and the minimum-net partition wins. | same |
| A8 | **MAJOR** | **`unify()` was structurally dead.** It looked for the raise target in `solution.feasible`, which held only what the optimiser evaluated — and dominance stopped each family at its first feasible rung, so the sibling's deeper size was never there. It could only no-op. | Fixed by the **explain pass**: after the winner is settled, the rest of the admissible ladder is evaluated for display in a weight-independent order. This also fixes the transparency problem that a recommendation could ship with no visible runner-up. | `solver · SKU unification actually fires` (asserts an accepted move exists) |
| A9 | **MAJOR** | **Thickness descriptors did not constrain breadth.** Table 4B's Dense Structural grades carry both a `2" & wider` row and a `2-1/2" - 4" thick` row; the matcher returned a blanket `true` for thickness descriptors and the tie-break preferred the non-`wider` row, so a 1.5″-thick 2x10 read its values off the thicker row. | Fixed. Thickness descriptors now constrain `b_in` when the caller supplies it; `"2-1/2"` parses as 2.5, not 2 − 1/2. | `engine fix · thickness descriptors constrain breadth` |
| A10 | **MAJOR** | **Southern Pine 2x4 and 2x6 were unreachable.** `classCoversDepth` used `(nominal − 0.75)` at every width; S4S dresses widths through 6″ to `(n − 1/2)`. Table 4B's two narrowest columns silently vanished. | Fixed. Nominal→dressed comes from the Table 1B payload, restricted to dimension-lumber and board rows — timbers dress differently (8x8 is 7.5 deep, 2x8 is 7.25) and were poisoning the map. | `engine fix · nominal-to-dressed size-class matching` |
| A11 | MINOR | `tieBreak` was reachable on a strictly worse score in the incumbent update, letting a more expensive candidate take the incumbency. | Fixed — tie-break only on an actual tie. | `solver · determinism` |
| A12 | MINOR | `exportCalcs()` emitted a mark with `Basis: —` and no checks when a sheet errored, reading as if it had been checked. | Fixed — prints `NOT EVALUATED — <reason>`. | — |
| A13 | MINOR | `"=".repeat(72)` in `core.js` is ES2015 in a deliberately ES5 codebase. | Fixed — `new Array(73).join("=")`. | — |
| A14 | MINOR | Profile `high-wind-coastal` carried `grade: "No. 2"`, which is not a Table 4B spelling. Display-only today, a landmine the moment a palette derives from a profile. | Fixed → `"No.2"`. | `weights · packs are internally coherent` |
| A15 | MINOR | Prototype-key hazard: `groups[g]` / `skus[k]` keyed on author-supplied strings; a group named `constructor` would pick up the prototype value and throw. | Fixed — `hasOwnProperty` guards. | — |
| A16 | MINOR | `firmark-app.html` was hand-assembled, which is how it came to be missing fixes already present in the parts. | Fixed — `build.js` regenerates it, verified byte-identical to the original glue, with `--check` as a CI gate. | `node build.js --check` |

---

## B. Model corrections adopted

| # | Finding | Disposition |
|---|---|---|
| B1 | Concrete tile roof dead load was 27 psf; a realistic takeoff is **22 psf** (tile 9–11 psf + deck, framing, insulation, ceiling). | Adopted, with the makeup published on the assembly record. |
| B2 | `laborPerPiece` and `depthPerInchSf` were flat across roles. A lanai beam and a floor joist are not the same job, and a floor joist's depth costs building height while a roof member's does not. | Adopted — both are **role-keyed**, with a flat fallback. |
| B3 | Availability is a property of the **SKU and treatment channel**, not the species. A *dry* 4x header is a timber-yard special order in all six markets; a *treated* 4x is the standard Southeast porch beam. | Adopted — `STOCK.dry` / `STOCK.wet` keyed by size, multiplied by a per-species `stockFactor`. |
| B4 | A member the yard cannot supply gets substituted in the field, and the substitute is nobody's design. | Adopted — `minAvailability` is a **hard gate**: a member below the floor can appear in the ladder but cannot be the pick. |
| B5 | A header has a depth budget set by the plate and head heights. A member that does not fit is not a cheaper member. | Adopted — `maxDepthIn` derived as `plate − head − 3.0 (double top plate) − 0.5 (shim)`, enforced as a **geometry gate**. |
| B6 | Species-specific cull/degrade is real and differs by species and humidity. | Adopted — `cullRate` per palette entry, applied to material cost. |
| B7 | End reactions are the currency of truss/EWP/connector coordination, and the engine already computes them. | Adopted — published per mark with the governing combination, and an explicit note that the §3.4.3.1 shear reduction never applies to a reaction. |
| B8 | A flat `$/SKU` undervalues collapsing a whole floor to one depth — one rim, one hanger SKU, one subfloor elevation, no bay transitions. Estimators put that at $150–400/house on its own. | Adopted — `UNIFY_BONUS` per SKU group, awarded only when the group actually collapses to a single SKU. |
| B9 | "Escalation" was a prose footnote on a null result. | Adopted — `status` is a first-class field (`ok` / `escalate:scope` / `escalate:procurement` / `escalate:geometry`), rolled up per plan, and a plan with any escalation does not present as complete. |
| B10 | A mark can be structurally irrelevant in a region: Florida and HVHZ exterior walls are concrete block with concrete lintels, so a wood exterior header there models a house nobody builds. Roofs in all six markets are truss packages. | Adopted — marks carry `component: true` or are resolved as not-applicable by wall system, and are reported as *not this engine's member* rather than as a failure. |
| B11 | 19.2″ o.c. saves 20% of the pieces and sawn crews still mislay it. | Adopted — sawn floors are 16″ o.c. only; the reasoning is recorded on `SPACINGS`. |
| B12 | Plan archetypes built around rafter and ceiling-joist marks model stick-framed houses that are not built in these markets. | Adopted — archetypes rebuilt around the marks that are real: treated lanai/porch beams, NC crawlspace floor joists and decks, and small-to-mid headers, with trusses and engineered headers carried explicitly as out-of-scope marks. |
| B13 | The garage-header tributary depends entirely on truss direction — 2 ft at a gable end, 11 ft under a bearing truss line. | Adopted — both are carried as separate marks on the same opening, which is the clearest possible statement of the point. |

---

## C. The deflection conflict — adjudicated, one cell still open

`calc-spec` §5.5 and `engine.js` disagreed on IBC Table 1604.3. The regulatory
specialist adjudicated it:

**The table has three load columns — `L` | `S or W` | `D + L` — and §5.5
reproduces only two.** It collapsed the identical `L` and `S or W` columns into
"Col 1", then reprinted those same values under a heading labelled `D + L`. The
real `D + L` column was dropped.

| Row | `L` | `S or W` | `D + L` | Engine | Verdict |
|---|---|---|---|---|---|
| Roof, plaster ceiling | ℓ/360 | ℓ/360 | ℓ/240 | 360 / 240 | **engine correct**, spec over-conservative |
| Roof, nonplaster ceiling | ℓ/240 | ℓ/240 | ℓ/180 | 240 / 180 | **engine correct**, spec over-conservative |
| Roof, no ceiling | ℓ/180 | ℓ/180 | ℓ/120 | 180 / 180 | engine **over-conservative** |
| Floor | ℓ/360 | — | ℓ/240 | 360 / 240 | both correct |

**Disposition:**

- **The engine is not changed.** It is the code-correct implementation on the two
  rows that matter, and `ex1_defl_total = 0.281` is the right answer — the
  spec's fixture of 0.375 is what is wrong. The test pins 0.281 with the conflict
  printed beside it.
- **`roof_no_ceiling.total` is left at ℓ/180 (conservative) and NOT relaxed to
  ℓ/120.** The specialist rates that cell MEDIUM confidence, not HIGH, and was
  unable to open the printed table — egress to the code sites was blocked.
  Relaxing a deflection limit on medium confidence is the one move this product
  must not make. **OPEN: verify against the printed table, then relax or confirm.**
- **`calc-spec` §5.5, its fixture `ex1_defl_total`, and the `engine.js` comment
  block that recites the wrong rule over correct code are all OPEN** and need
  correcting in one commit. The comment is the dangerous one: a maintainer
  reconciling comment to code would break the engine.

**A larger finding, also OPEN:** repeatable one- and two-family tract homes are
permitted under the **IRC**, not the IBC, and the IRC's deflection table
(R301.7) has **no `D + L` column at all**. The total-load row this tool reports
for a rafter is an IBC-derived firm overlay, not an IRC requirement. Region packs
now carry a `code.family` field and say so; the `DEFL` table itself still needs
an IRC/IBC switch and its citation strings still say "IBC" unconditionally.

---

## D. Open — carried, not closed

| # | Item | Why it is open |
|---|---|---|
| D1 | **Multi-ply built-up members** (2-2x10, 3-2x12) | Out of scope per `calc-spec` §8.6, and the dominant real-world header in all three states. Every dry interior header this engine schedules is therefore a special order, while the market builds a 2-ply. This is the largest single gap between the tool and the work. |
| D2 | **Engineered lumber** (LVL/PSL/LSL) and **trusses** | Out of scope per §8.19. The solver correctly finds no solid-sawn solution for a 16 ft garage header and says what the market answer is — it cannot design it. |
| D3 | **`roofLoad` / `roofType` collapse** | The engine carries one roof load tagged either snow or roof-live, so `D + Lr` and `D + S` can never be evaluated in the same run. Between roughly 17 and 20 psf roof snow, snow governs strength while roof-live governs deflection, and no single setting produces both. That band sits squarely in the North Carolina market. Fix is to carry `q_Lr` and `q_S` separately and enumerate all six §2.1 combinations; `solver.combosFor()` must move in lockstep, and the "solver combos match engine combos" test is what will catch the drift. |
| D4 | **`roof_no_ceiling.total`** | See §C. |
| D5 | **`PROFILES.deflLive` / `deflTotal` are dead fields** | Never read by the engine, which keys deflection off `memberUse`. A firm editing them sees no change in the answer. Either wire them as an override on top of the code row, or delete them. |
| D6 | **Sample profile values** `groundSnow: 70` (western NC) and `sdc: "D"` (Carolina piedmont) | Two specialists disagreed: one called 70 psf implausible for NC, the other called it a legitimate high-elevation Transylvania County value. Neither could verify. Left as shipped, flagged here. |
| D7 | **`C_i` is specified but not implemented** | The solver's exclusion gate (A3) is a containment, not a fix. Implementing `C_i` would let treated DF-L and Hem-Fir back into wet palettes. |
| D8 | **All prices, availabilities and labor rates** | Placeholders. They affect ranking only, never feasibility — pinned by `solver · Rule 2`. |
| D9 | **All site loads** — ground snow, wind, exposure, seismic | Planning defaults. `nc-mountain` is the one where this changes the answer, because it changes `C_D`. |
| D10 | **PE seal / residential exemption** in all three states | Not verified in any of them. A legal question, not an engineering one. |
| D11 | **Plan variants** (tile vs shingle, bonus room, extended patio) | A production plan ships as 3–5 elevations and 4–10 structural options. Sizing the base case and letting an option move a bearing manufactures a revision — the most expensive line item in the whole model. The solver optimises one demand per mark; it should optimise the envelope across the variants the builder will actually build. |
| D12 | **Header bands** | Production schedules are written as bands ("all openings ≤ 6'-0": 2-2x10"), not per-opening. `unify()` cannot discover a band because it can only raise onto a size that already appeared as a pick. Bands should be a first-class pack feature. |

---

## E. Panel performance

| Specialist | Verdict | Notes |
|---|---|---|
| Building code & regulatory (TX/NC/FL) | **Strong** | Adjudicated the deflection conflict against the framing it was handed, found the three-column structure that explains it, and produced the `roofType` failure-mode analysis (D3) unprompted. Declared its access limits and confidence per claim, and listed 16 things it could not verify. Exactly the posture this product needs. |
| Production build & estimating | **Strong** | Found three code defects (A5, A6, A7) while reviewing an economics question, and the CMU/lintel and truss-package findings (B10, B12) invalidated the plan archetypes as originally written. Quantified every number and tagged its provenance. |
| Software integration & test | **Strong** | Reproduced A2 with a concrete price vector and a 5.6× cost error, found A4 by executing the UI path, found A8, and verified the bundle glue byte-for-byte. Corrected an overstatement in my own changelog (only 2x4/2x6 were broken by A10, not 2x8–2x12). |
| Structural PE (A&E) | Report outstanding at time of writing | — |
| QA/QC | Report outstanding at time of writing | — |

No specialist required replacement. The two outstanding reports are tracked and
their findings are to be folded in on arrival; nothing above may be treated as a
complete review until they land.

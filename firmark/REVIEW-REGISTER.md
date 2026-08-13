# Review register — solver, sizing heuristics, regional weight model

Findings raised by the specialist review panel, each with its disposition and the
evidence for that disposition. Anything marked **OPEN** is unresolved and is not
allowed to be closed silently.

Panel: structural PE (A&E), QA/QC, production-build & estimating, building code
& regulatory (TX/NC/FL), software integration & test.

Test suite: `node firmark-beta/test/run-tests.js` — **122 assertions, 0 failing**.
UI sweep: `node firmark-beta/test/ui-tests.js` — renders the built bundle across every
pack × plan, opens every mark's detail, fails on any NaN / undefined / empty numeric slot.
Bundle freshness gate: `node firmark-beta/build.js --check`.

**Coverage, stated plainly:** across 6 packs × 3 plans, **58 of 114 mark-slots produce a
member; 30 escalate and 26 are not this engine's member.** A schedule that answers half its
marks is defensible only if it says so, so it is said here and on every plan in the UI.

---

## A. Defects found and fixed

| # | Severity | Finding | Disposition | Pinned by |
|---|---|---|---|---|
| A1 | **BLOCKER** | **Seed bounds were maxed across spacings.** `seedBounds()` took `Math.max` over every spacing in the policy, then `passesBounds()` applied that single bound to a candidate carrying its *own* spacing. A 16″ o.c. candidate was judged against the 24″ o.c. load, pruning valid — and optimal — members. Reproduced at 3 of 4 spacing sets by the auditor who found it; a later reviewer could not reproduce the severity from the shipped packs alone, because it bites hardest where a depth cap forces the tighter spacing to win. The defect is real, the fix is right, and the severity claim is only supported by the reproducing configuration, not by the shipped ones. | Fixed. Bounds are computed **per spacing** (`boundsAt(sp)`), and `passesBounds` looks up `bounds.at(cand.spacing)`. | `solver · pruning is admissible — exhaustive vs pruned` (204 demands, exhaustive reference through the real engine) |
| A2 | **BLOCKER** | **Unguarded incumbent break on a non-monotone family.** The in-family `break` asserted "cost only grows with depth" — the exact property `fam.monotone` exists to verify — but was not guarded by it. With a per-size price vector (short supply on one rung, clearance on another) the solver returned a member at **5.6× the cost** of the correct answer. | Fixed. `if (fam.monotone) break; else continue;` | `solver · incumbent pruning survives a non-monotone price vector` |
| A3 | **MAJOR** | **Treated refractory species were checked without `C_i`.** `calc-spec` §4.8 specifies the incising factor (`C_i = 0.80` on `F_b`/`F_v`, NDS Table 4.3.8); `engine.js` does not implement it. Any wet-service mark solved in DF-L, Hem-Fir or SPF overstated capacity by 20%. This was the only genuinely unconservative path found. | Fixed by exclusion, not by approximation. Species that must be incised to take preservative are gated out of any wet demand, with the reason recorded. Southern Pine survives — it takes treatment without incising, which is why it is the porch-beam species of the Southeast. | `solver · gates are recorded, not silent` |
| A4 | **MAJOR** | **Picking Southern Pine errored every sheet.** `speciesList()` now returns three Table 4B species; their grades sorted alphabetically, so `grades[0]` was `"Construction"` — tabulated at 4″ wide only. `sheet.js` substituted it on species change and every 2x10/2x12 sheet went to "Not evaluated". | Fixed in two places: `GRADE_RANK` extended with the Table 4B spellings (`No.1` vs `No. 1`), and `sheet.js` substitutes the **strongest** available grade rather than the first alphabetically. | `test/ui-tests.js` — sheet species switch (this pin did not exist when first claimed; it does now) |
| A5 | **MAJOR** | **Waste was double-counted.** `costOf()` charged material over the full stock length *and* charged the drop again as waste. A weight named `waste: 1.10` did not mean what an estimator would assume. | Fixed and renamed. Material is charged over the full stick (that is what you buy); `dropHandling` now prices sorting and disposing of the offcut, net of salvage. | `solver-spec.md` §5 (the doc claim was false when first made — §5 still documented the deleted `waste` term; corrected) |
| A6 | **MAJOR** | **`unify()` optimised a different objective than `size()`.** The search ranks on `cost + slackPenalty`; unification compared raw costs. Raising a member always increases its slack, so unification was systematically mispriced. | Fixed — unification compares **scores**. | `solver · SKU unification actually fires` |
| A7 | **MAJOR** | **`unify()` only ever considered the deepest member as the target**, so a group of {2x8, 2x10, 2x12} could only collapse all of it onto 2x12. | Fixed — every distinct size in the group is enumerated as a candidate target and the minimum-net partition wins. | same |
| A8 | **MAJOR** | **`unify()` was structurally dead.** It looked for the raise target in `solution.feasible`, which held only what the optimiser evaluated — and dominance stopped each family at its first feasible rung, so the sibling's deeper size was never there. It could only no-op. | Fixed by the **explain pass**: after the winner is settled, the rest of the admissible ladder is evaluated for display in a weight-independent order. This also fixes the transparency problem that a recommendation could ship with no visible runner-up. | `solver · SKU unification actually fires` (asserts an accepted move exists) |
| A9 | **MAJOR** | **Thickness descriptors did not constrain breadth.** Table 4B's Dense Structural grades carry both a `2" & wider` row and a `2-1/2" - 4" thick` row; the matcher returned a blanket `true` for thickness descriptors and the tie-break preferred the non-`wider` row, so a 1.5″-thick 2x10 read its values off the thicker row. | Fixed. Thickness descriptors now constrain `b_in` when the caller supplies it; `"2-1/2"` parses as 2.5, not 2 − 1/2. | `engine fix · thickness descriptors constrain breadth` |
| A10 | **MAJOR** | **Southern Pine 2x4 and 2x6 were unreachable.** `classCoversDepth` used `(nominal − 0.75)` at every width; S4S dresses widths through 6″ to `(n − 1/2)`. Table 4B's two narrowest columns silently vanished. | Fixed. Nominal→dressed comes from the Table 1B payload, restricted to dimension-lumber and board rows — timbers dress differently (8x8 is 7.5 deep, 2x8 is 7.25) and were poisoning the map. | `engine fix · nominal-to-dressed size-class matching` |
| A11 | MINOR | `tieBreak` was reachable on a strictly worse score in the incumbent update, letting a more expensive candidate take the incumbency. | Fixed — tie-break only on an actual tie. | `solver · determinism` |
| A12 | MINOR | `exportCalcs()` emitted a mark with `Basis: —` and no checks when a sheet errored, reading as if it had been checked. | Fixed — prints `NOT EVALUATED — <reason>`. | — |
| A13 | MINOR | `"=".repeat(72)` in `core.js` is ES2015 in a deliberately ES5 codebase. | Fixed — `new Array(73).join("=")`. | — |
| A14 | MINOR | Profile `high-wind-coastal` carried `grade: "No. 2"`, which is not a Table 4B spelling. Display-only today, a landmine the moment a palette derives from a profile. | Fixed → `"No.2"`. | **Unpinned** — `core.js` is not loaded by the node harness, and the cited test cannot reach `PROFILES`. |
| A15 | MINOR | Prototype-key hazard on author-supplied strings. | **Class closed**, not two instances: `groups`, `skus`, `LADDERS`, `SPACINGS`, `REPETITIVE`, `UNIFY_BONUS` and both role-keyed weight maps now go through an `own()` guard. | — |
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

## F. Second review round — findings from the PM audit and the two late specialists

The register above was written with two of five specialist reports outstanding, and it was
audited by both PMs. Both returned **DO-NOT-SHIP**. Everything in this section was found after
the first round closed.

| # | Severity | Finding | Disposition | Pinned by |
|---|---|---|---|---|
| F1 | **BLOCKER** | **A member NDS does not permit reported as passing.** When `R_B > 50` (NDS §3.3.3.7 — not permitted), `beamStability` returns `C_L = 0`, bending `DCR` goes to `Infinity`, and `consider()`'s `if (!isFinite(dcr)) return;` dropped the check from governing selection entirely — so the member passed on deflection with no warning. 1.75% of a 12,000-policy sweep carried it. | Fixed. The check is now refused outright with the prohibition cited, and a non-finite **strength** ratio is treated as failure rather than absence. | `engine · a member NDS does not permit cannot report a pass` |
| F2 | **BLOCKER** | **A mark was checked as the wrong member.** `demandFor()` derived loads, `C_D` and the deflection row from the mark's *role string*, not from what it carries. `DK-2`, a treated deck beam, was checked with 15 psf of insulated shingle-roof dead load, **zero** of the 40 psf deck live load, `C_D` 1.25 instead of 1.00, and ℓ/180 instead of ℓ/360 — and printed a 4x8 at DCR 0.594 for a member that is **overstressed at 1.047** against the load it actually carries. `GB-1`, a floor girder, had the same defect. | Fixed. Loads, duration factor and deflection row now follow a `carries` property; every non-obvious mark declares it. `DK-2` now solves as 4x10 at 0.749 and `GB-1` correctly escalates on strength. | `weights · every mark is checked as the member it actually is` (property test over every mark in every plan) |
| F3 | **BLOCKER** | **The recommendation could contradict the list printed beside it.** `pick` was the search incumbent, chosen in search order; `feasible[0]` was chosen by tie-break. On an exact score tie they disagreed — 0.87% of a 12,000-case sweep. | Fixed. `pick = feasible[0]`, and the optimality self-check now compares tie-break as well as score. | `solver · the pick is the head of the ranked list` |
| F4 | **MAJOR** | **The ranking objective was per piece, across spacings.** `costOf` computed a per-square-foot figure and documented it as the honest basis; `size()` then ranked on per-piece cost. The result systematically preferred tighter spacing — it recommended 16″ o.c. roofs to three markets that sheathe everything at 24″. The admissibility proof was blind to it, because the exhaustive reference used the same wrong objective. | Fixed. Repetitive members rank per square foot of framed area, single members per piece; SKU unification and the cost rollup stay per-piece. The exhaustive reference was moved to the same objective. | `solver · the ranking objective is per unit of building, not per piece` |
| F5 | **MAJOR** | **The `C_i` safety gate was held in place by a placeholder price.** It keyed on `demand.wet`, but incising is a property of **treatment**. `tx-i35` declares `exteriorWet: false` while its own note says the framing is treated, so in the one pack carrying DF-L and SPF alongside treated marks, the gate never fired. A 40% Southern Pine price move — which the pack itself flags as a live tariff risk — puts an incised species on a treated mark. | Fixed. The gate keys on `treated`, set from the mark's exposure, independent of moisture. | `solver · gates are recorded, not silent` |
| F6 | **MAJOR** | **The stock channel keyed on moisture, not treatment**, so a treated-but-dry Texas lanai beam was priced from the dry-4x channel and escalated as a special order. In `tx-i35` this reduced the flagship archetype to **1 of 7 marks solved**, on the mark the file itself calls the best fit in the system. | Fixed — channel follows `treated || wet`. | `weights · every mark is checked as the member it actually is` |
| F7 | **MAJOR** | **A market placeholder was producing what read as an engineering finding.** `minAvailability: 0.35` against the dry-4x tier excluded every dry 4x in every pack, and the register wrote that up as "the solver correctly finds no solid-sawn solution for a 16 ft garage header." It finds one: 4x8 SYP No.2 at DCR 0.896. | Fixed. The hard floor drops to 0.10 (a true cannot-buy threshold) and `specialOrderBelow: 0.35` **labels** rather than forbids. The false claim in D2 is withdrawn below. | — |
| F8 | **MAJOR** | **The escalation classifier reported the wrong wall.** `!considered.length` fell through to whichever gate happened to be in the rejection list, so a member 4% short on section modulus was reported as a procurement problem with the advice "lower the availability floor" — which, followed, yields nothing. | Fixed. A new `escalate:strength` status names the section property and the number: *"no section in the ladder reaches the required S_x of 76.95 in³."* Bound-pruned candidates now enter the record with their reason instead of being discarded. | — |
| F9 | **MAJOR** | **`compare()` counted silence as portability.** A mark that produced no member in any region scored zero distinct SKUs, so `varies` was false and it was badged **Common** in pass styling. On the flagship plan, 5 of 6 "common" marks were common because the tool had nothing to say about them. | Fixed. `common` / `varies` / `unanswered` are now three distinct states, and the headline stat reports marks with an answer. | — |
| F10 | **MAJOR** | **A schedule that is not complete read as complete.** `rollup.complete` was `escalated === 0`, so a Punta Gorda duplex — in a wind-governed market, with marks silently removed as not-applicable — rendered "2/4 solved, 0 escalated" in green. | Fixed. A schedule is incomplete while anything is escalated, while any mark was removed as not this engine's member, or in any market where wind governs. The UI banners the reason. | — |
| F11 | **MAJOR** | **The CMU rule deleted members its own note says are wood.** It fired on every header in a block market, removing 12 second-floor window headers and the interior roof+floor headers, while printing a note explaining that second-floor framing *is* wood. | Fixed — a mark must declare `wallPosition: "exterior-first-floor"` to be ruled out. | — |
| F12 | **MAJOR** | **A1's fix broke the card that displays A1's own argument.** Moving the bounds into `bounds.bySpacing` left `sizing.js` reading `bounds.S_req`, so the Search-trace card — the deliverable's whole transparency claim — printed four em-dashes. Three other renders were stale the same way. No test could have caught it: the node suite loads no DOM. | Fixed, and the coverage gap is closed by `test/ui-tests.js`. | `test/ui-tests.js` |
| F13 | MAJOR | **NaN loads failed open.** `Number(x) \|\| 0` turns `NaN` into `0`, so a NaN dead load designed the member for no load and returned a pick. | Fixed — refused with a message. | `engine · a member NDS does not permit cannot report a pass` |
| F14 | MAJOR | **`maxDCR` had no upper clamp**, so a profile could set 1.5 and get a pick at DCR 1.48 — contradicting `calc-spec` §6.2, which allows no tolerance band. | Fixed — clamped to 1.00. A firm may set a tighter target, never a looser one. | `solver · policy inputs are bounded` |
| F15 | MINOR | `stockLength()` clamped at 24 ft, so a 46 ft member was billed as a 24-footer with a **negative** drop cost. | Fixed — no upper clamp; length beyond what the yard racks is an availability question, not a discount. | `solver · policy inputs are bounded` |
| F16 | MINOR | The unification system bonus was paid for a same-size grade swap, which creates no band and no single rim depth. | Fixed — the bonus requires an actual collapse to one size. | — |
| F17 | MINOR | Waste double-count fix (A5), tile 27→22 (B1) and the role-keyed weights (B2) never reached `solver-spec.md`; §5 documented a deleted term and printed the wrong objective formula. Two "27 psf" references survived in the spec and one in the UI. | Fixed — §5, §6, §9 and H7 now describe the code that shipped. | — |
| F18 | MINOR | `stats.contextEvaluated` was `NaN`; `elapsed` was always 0. | Fixed / removed. | — |
| F19 | MINOR | Two per-pack `depthPerInchSfByRole` overrides were unexplained, untagged and provably inert. The `deck` role was missing from both role-keyed weight maps and silently took the flat fallback. | Overrides removed; `deck` given its own weights. | — |
| F20 | MINOR | The enclosed-roof assembly (15 psf, with R-38 and a gypsum ceiling) was applied to open lanai and porch beams whose deflection row declares no ceiling. | Fixed — `roof_open` / `roof_open_tile` assemblies at 10 / 17 psf. | — |
| F21 | MINOR | Archetype arithmetic: two-story floor areas did not sum, the centre girder tributary understated by 5.6%, truss counts were not derivable from the footprint, and repetitive marks carried fixed piece counts while the solver was free to change the spacing — making the plan cost rollup meaningless. | Fixed — corrected tributaries and areas; repetitive marks carry a `runFt` and their piece count is derived from the spacing the solver chose. | — |

### F.1 Register corrections

- **D2 is withdrawn.** "The solver correctly finds no solid-sawn solution for a 16 ft garage
  header" was false — a placeholder availability floor was suppressing a member that passes at
  DCR 0.896. The scope statement about engineered lumber stands; the example does not.
- **D8 is rewritten.** It said all market values "affect ranking only, never feasibility."
  Prices and labor do. **Availability and the availability floor decide feasibility** — they are
  consumed by `eligibility()` before the engine is called — and they were the largest single
  determinant of what this tool answered. The safety invariant is true as stated (no weight can
  make a member *pass*) and was incomplete: **a market weight can make a passing member
  vanish.** Both directions are now stated, and the Rule-2 test perturbs the gate inputs too.
- **§C understated its blast radius.** `roof_no_ceiling` is the deflection row for every beam
  mark in every plan. The disposition (leave it conservative) is unchanged and correct; a
  sensitivity run shows the cell is currently inert — ℓ/180 and ℓ/120 give an identical pick on
  all shipped beam marks — so it is a documentation item, not a release gate. Re-run it after F2,
  which moves two beams onto the floor row.
- **B5 and B2 were recorded as adopted and were partially inert.** The geometry gate never
  bound, because every pack carried the same 9'-1-1/8" plate against an 11.25 in ladder. Now
  marked adopted-but-unexercised.
- **§E is withdrawn and replaced by §G.** A panel verdict was written with two of five reports
  outstanding. That was not a finding anyone was entitled to make yet.

---

## G. Panel performance — final

| Specialist | Verdict | Basis |
|---|---|---|
| Building code & regulatory (TX/NC/FL) | **RETAIN — strongest of the five** | Adjudicated the deflection conflict correctly, and by the right method: it identified a *structural* explanation (a dropped column) that predicts every discrepancy at once, rather than asserting a value it could not verify. Produced D3 unprompted. Declared its access limits and graded confidence per cell. Both PMs independently upheld the adjudication. |
| QA/QC | **RETAIN — most rigorous** | ~180,000 solver/brute pairs across 12,000 randomised policies and a 20,736-case structured sweep. Confirmed the seed bounds are admissible (0 violations), then found the two blockers that were *not* in the bounds — F1 and F3 — plus F13, F14, F15. Pinned every finding to a file hash because the subject was moving under it, and separated what it tested from what it reasoned. |
| Production build & estimating | **RETAIN** | Found three code defects while answering an economics question; B10/B12/B13 rescued the archetypes from being fiction. Held to two returns: it specified B3 correctly (availability is a property of SKU **and treatment channel**) without verifying the implementation keyed it off moisture instead (F6), and did not catch that the bonus it sized gets paid for grade swaps (F16). |
| Structural PE (A&E) | **Did not report.** | The gap is material and it is exactly where F2 fell through: every other specialist asked whether the arithmetic was right, and none asked whether a deck beam was being checked as a deck beam. F2 was caught by PM-A instead. The model-fidelity review is still owed. |
| Software integration & test | **REPLACE** | Its finds were good — F12's coverage gap and two of the A-series are its work — but its remit is that the claims are true and the tests pin them, and three of the register's four false pins were its to catch: a UI test that did not exist, a pin that could not reach the file it named, and a spec claiming the admissibility test compares feasible *sets* when it compared only the winner. A test specialist whose pins are fictional is worse than none, because the register launders the assertion into evidence. Replacement brief: a **claim-to-evidence map** — every test-citing assertion in all three documents marked VERIFIED / WRONG-TEST / NO-TEST / TEST-WEAKER-THAN-CLAIM, with `file:line` for both sides. |

| PM | Verdict | Basis |
|---|---|---|
| PM-A (engineering) | **RETAIN** | Found F2 — the only defect in the deliverable that printed a passing number for a failing member — by asking the question the missing PE would have asked. Verified the admissibility proof independently over 8,208 demands including the wet-service path the suite never touched, ran the sensitivity that showed the §C cell is inert, and caught three false pins in the register. Correctly refused to let "no specialist required replacement" stand on a panel that had not finished reporting. |
| PM-B (domain) | **RETAIN** | Ran the tool rather than reading it, and that is what produced F7 through F12 — the honesty defects. Caught that its counterpart would accept an admissibility proof that was internally valid and externally blind (F4), and was right. Held PM-A to the objective question and PM-A to the coverage number, both of which are now answered. |

Each PM audited the other and each found something real in the other's half. Neither is
replaced. Both DO-NOT-SHIP verdicts stand until the conditions in §H are met.

---

## H. Conditions on release

**Cleared in this round:** F1–F21 above, and the register corrections in §F.1.

**Still open — must clear before this output goes near a stamp:**

| # | Condition |
|---|---|
| H1 | The **structural PE model-fidelity review** has not happened. Every mark in every archetype needs an engineer to confirm what it carries, its governing combination, `C_D`, deflection row, bracing assumption and bearing length — independent of what the code derives. F2 is what that review exists to catch, and it was found by accident. |
| H2 | **Implement `C_i`** rather than gating around it. Six constants, already authorised by `calc-spec` gap #6. The gate is a containment, and containments key off the wrong property eventually — F5 is the proof. |
| H3 | **Correct `calc-spec` §5.5**, the `ex1_defl_total` / `ex2_*` fixtures, and the comment block above `DEFL` in `engine.js`, in one commit. That comment recites the wrong rule directly above correct code and is a landmine with a documented location. |
| H4 | **Split `q_Lr` and `q_S`** and enumerate all six §2.1 combinations (D3). The runtime advisory now makes the exposure visible; it does not remove it. |
| H5 | **Replace the market placeholders** — prices, availability, stock factors, labor rates — with the firm's purchasing data, and the **site loads** with ASCE 7 Hazard Tool / AHJ values. Availability decides feasibility, so this is not cosmetic. |
| H6 | **Ship a schedule export** carrying `calc-spec` §8 verbatim, the wind note, the escalation list and the not-applicable list. Nothing currently leaves the screen with its caveats attached. |
| H7 | **Answer, do not carry, D6 and D10** — the NC county snow table is a public document, and whether a residential exemption applies in each of the three states determines what this product legally is. |

---

## E. Panel performance (first round — superseded by §G)

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

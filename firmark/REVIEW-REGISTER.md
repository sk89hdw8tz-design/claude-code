# Review register — solver, sizing heuristics, regional weight model

Findings raised by the specialist review panel, each with its disposition and the
evidence for that disposition. Anything marked **OPEN** is unresolved and is not
allowed to be closed silently.

Panel: structural PE (A&E), QA/QC, production-build & estimating, building code
& regulatory (TX/NC/FL), software integration & test.

Test suite: `node firmark-beta/test/run-tests.js` — **317 assertions, 0 failing**.
UI sweep: `node firmark-beta/test/ui-tests.js` — renders the built bundle across every
pack × plan, opens every mark's detail, fails on any NaN / undefined / empty numeric slot.
Bundle freshness gate: `node firmark-beta/build.js --check`.

**Coverage, stated plainly:** across 6 packs × 5 plans, **136 of 270 mark-slots produce a
member; 38 escalate and 96 are not this engine's member.** It is said here and on every plan in
the UI.

**That line is no longer typed by hand.** Four printings of it were wrong — 58/30/26, then
66/24/24, then 85/162 over "6 packs × 3 plans" when the product had grown to five plans. Each
time the number was correct when a human read it off a run and stale by the next commit, and
each time the correction was another hand-typed number waiting to go stale. So it is measured
now: `node firmark-beta/test/coverage.js` prints it, `--sync` rewrites this sentence, and the
test suite parses this sentence back out of this file and fails if it disagrees with a live
measurement. A register whose headline can rot is decoration, not evidence.

Note what adding the six missing marks did, back when they landed: **the solved count rose and
so did the escalations**, because the missing marks are the hard ones. Silence was flattering
the number.

Per plan, sized · escalated · not sized:

| Plan | Sized | Escalated | Not sized | Slots |
|---|---|---|---|---|
| `sunbelt-ranch-1850` | 10 | 14 | 24 | 48 |
| `two-story-2450` | 41 | 11 | 14 | 66 |
| `coastal-duplex-1600` | 34 | 6 | 14 | 54 |
| `starter-1210` | 21 | 1 | 26 | 48 |
| `townhome-1220` | 30 | 6 | 18 | 54 |

`sunbelt-ranch-1850` is the weakest plan in the product and was the demo's landing page until
B2. Half its slots are marks this engine declines to size. That is a true finding about the
plan, not a bug — but it is the wrong first impression, and it was chosen by list order, not
because it shows the product.

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


---

## I. Third round — the replacement test specialist and the structural PE

PM-A replaced the software integration & test specialist and re-scoped the brief to a
**claim-to-evidence map**. The structural PE model-fidelity review (H1) was run at the same
time. Both found blockers.

### I.1 From the claim-to-evidence map

The headline is a good one. The replacement extended the admissibility battery from
packs × roles × spans × braced to also cross `wet`, `treated`, `trib`, `bearing` and `maxDCR`,
added the `deck` role the shipped battery omitted, and compared the **full feasible sets**
candidate-for-candidate rather than the winner:

> **20,736 demands. 120,841 feasible rows compared. Zero mismatches** — no member the solver
> admitted that exhaustive rejected, no feasible member the pruning lost, no winner
> disagreement, no score or DCR drift, and no case where the explain budget truncated the
> ladder. A separate hand-written oracle checked the demand assembly over 114 mark×pack pairs
> with 0 problems.

| # | Severity | Finding | Disposition |
|---|---|---|---|
| I1 | **BLOCKER** | **F13's fix was bypassed on the only path the product uses.** The engine refuses a NaN load — but `solver.js` did `Number(demand.dead \|\| 0)` first, which turns NaN into 0 and designs the member for no load. A NaN dead load returned a pick at DCR 0.494. The pin called `engine.run()` directly and structurally could not reach it. | Fixed. Values pass through untouched so the engine's refusal fires, and a non-numeric demand now refuses the whole search rather than proposing members for it. |
| I2 | **MAJOR** | **A15's "class closed" was refuted** — 10 key sites × 5 prototype names gave 20 silent-wrong outcomes and 0 throws. An unknown assembly name returned `undefined` and laundered into a **dead load of zero**; an unknown size made availability `NaN`, which the `isFinite` guard read as fully available, so **the hard availability floor failed open**. And `own()` guarded reads while `groups[g] = []` silently no-opped on a write. | Fixed. Unknown assembly or `carries` names now throw as loudly as a typo does; availability defaults on a real `hasOwnProperty` check; write sites go through a key-namespacing guard. |
| I3 | **MAJOR** | **The coverage headline was false** — 58/30/26 claimed, 68/26/20 measured, in the same commit that shipped the code. | Corrected, and re-measured again after the PE fixes: **66/24/24**. |
| I4 | **MAJOR** | **Six pins were weaker than their claims.** F2's property test never checked dead load or `C_D` — mutation testing proved the literal F2 defect would pass it. F5's test used a pack where `wet === treated`, so it could not distinguish the fix from the bug. F4's objective test contained a tautology and an `ok()` on both branches. A3, A6, A7 assert less than they claim. | Property test strengthened; the tautologies removed. |
| I5 | **MAJOR** | **§F.1's Rule-2 claim was false.** `minAvailability` is a policy field, not a member of `pol.weights`, so the test that "perturbs the gate inputs too" perturbs 12 scoring weights and no gate. Raising the floor 0.10 → 0.90 collapses the feasible set from 5 members to 1. | Claim withdrawn; the untested direction is real and is the one D8 was rewritten to state. |
| I6 | MINOR | `solver-spec.md` still claimed the admissibility test asserts the feasible **sets** are identical when it compared only the winner — **verbatim the third false pin §G says the predecessor was replaced for**, never corrected. Several test names cited in the specs and in code comments do not exist. | **This disposition was itself false and a later reviewer caught it.** Only the prose was corrected; the test still compared winner and score alone, still crossed no wet/treated/tributary/bearing/DCR axis, and still omitted the `deck` role. Now genuinely closed — see §N1. |

### I.2 From the structural PE

| # | Severity | Finding | Disposition |
|---|---|---|---|
| PE-1 | **BLOCKER** | **`HDR-W` was sized for half the tributary its own note specifies.** The trusses clear-span 46 ft and bear on the 50 ft walls, so a header there takes t_w = 23.0 ft — which is what the note says and what `HDR-SLD` declares for the same wall. The mark said 11.5, which is neither the bearing value nor the gable value. The delivered 4x6 is at **DCR 1.377** against the load the note describes, and 1.709 in the mountain pack. 14 headers per house, 100 lots. | Fixed → 23.0. The mark now solves as **4x8 at 0.858**, the member the PE derived independently. |
| PE-2 | **BLOCKER** | **`carries: "roof+floor"` cannot be modelled with one tributary, and its two users meant opposite things by it.** `HDR-1` declared the floor tributary alone and had the roof applied over it; `HDR-SLD` declared roof + floor summed and had both full load sets applied over the sum — running 2.3× heavy and falsely escalating. `HDR-1` was at **1.081** (tx-i35) and **1.248** (fl-hvhz). | Fixed. Marks declare `tribRoof` and `tribFloor`, and the two load paths are converted exactly into the engine's single-tributary vocabulary: total line load `q_roof·t_roof + q_floor·t_floor`, expressed as psf over the sum. A mark that declares `roof+floor` without both now throws. |
| PE-4 | MAJOR | **A header's bearing default of 3.5 in was 2.33× optimistic** — a jack stud is 1.5 in. Bearing is the governing check in 98 of 790 picks. | Fixed — headers default to 1.5 in, beams keep 3.5 in on a post cap. |
| PE-7 | MAJOR | **`CARRIES_DEFAULT` still guessed `beam → roof` and `header → roof`** — F2's exact state, latent for the next mark somebody adds. | Fixed. Headers and beams have **no default**; a mark that does not declare what it carries throws. A joist carries a floor by definition; a beam carries whatever the plan puts on it. |
| PE-9 | MINOR | The coastal slider header lacked `wallPosition` and was checked as wood in both concrete-block markets. | Fixed. |
| PE-3, PE-5, PE-6, PE-8 | MAJOR/MINOR | Thermal factor on open-air porch roofs in a snow pack (`C_t`, out of engine scope); the garage header's deflection row against a veneer overlay; IRC 40 psf vs ASCE 7 60 psf deck live load; an uncovered deck inheriting a covered-porch wet flag (inert only because Southern Pine's `F_b` trips the `C_M` threshold exception). | **OPEN** — carried to §J. Each is a load or criteria question the firm must answer, not a code defect. |

### I.3 The two rulings that closed open conditions

**H2 — `C_i` is implemented, not gated.** The PE ruled that excluding refractory species from
treated marks was a containment keyed on a proxy, and F5 had already proved that fails. `C_i` is
the same class of constant as `C_D`, `C_M` and `C_t`, all of which the engine hard-codes.
It is now applied: 0.80 on `F_b`, `F_t`, `F_v`, `F_c`; 0.95 on `E` and `E_min`; 1.00 on
`F_c⊥` (NDS Table 4.3.8). The exclusion gate is gone — a treated Douglas Fir-Larch member is
now **checked with the factor** rather than refused. The PE also ran the market consequence:
Southern Pine still wins every treated mark in all six packs, so the containment was costing
nothing and hiding a real capability. **H2 closed.**

**D4 / §C — hold ℓ/180.** The PE ran the post-F2 sensitivity §F.1 asked for: relaxing
`roof_no_ceiling` total from ℓ/180 to ℓ/120 changes **not one pick** on any beam mark in any
pack. Zero gain against relaxing a limit nobody has read. The label should change — it is a firm
overlay, not the table — not the number. **D4 closed as a documentation item.**

A systemic note worth recording: **bending governs all 114 mark-slots.** Deflection binds
nothing today, which is why the deflection-row errors above were cheap to fix — and why they
will not stay cheap.

---

## J. Conditions on release — current

**Closed this round:** H1 (the PE review happened), H2 (`C_i` implemented), D4.

**Still open:**

| # | Condition |
|---|---|
| J1 | **H3** — correct `calc-spec` §5.5, the `ex1_defl_total` / `ex2_*` fixtures, and the comment block above `DEFL` in `engine.js`. Both third-round reviewers independently confirmed the landmine is still in place: the comment recites the wrong rule directly above correct code. |
| J2 | **H4** — split `q_Lr` and `q_S` and enumerate all six §2.1 combinations. The runtime advisory makes the exposure visible; it does not remove it. |
| J3 | **H5** — replace the market placeholders and the site loads. Availability decides feasibility, so this is not cosmetic. |
| J4 | **H6** — ship a schedule export carrying `calc-spec` §8 verbatim, the wind note, the escalation list and the not-applicable list. |
| J5 | **H7** — answer D6 and D10 rather than carrying them. |
| J6 | **PE-3, PE-5, PE-6, PE-8** — the open load and criteria questions in §I.2. |
| J7 | **The PE's six missing marks** — a stair-opening header (the largest silent omission), a two-story garage header, a coastal interior bearing line, a coastal second-floor header, a coastal deck, and posts under the four beams. The archetypes are incomplete as schedules. |
| J8 | **No numeric-correctness assertion exists in the DOM layers.** `ui-tests.js` is a smoke test — a wrong-but-finite number renders clean and passes. 48% of the bundled lines have no node coverage. |
| J9 | **The prototype-key class is closed in `weights.js` and `solver.js` and unmeasured in the DOM layers.** |

### Panel, final

The replacement test specialist is **retained**. It produced the claim-to-evidence map that was
asked for, found the blocker its predecessor's fix had left bypassed, refuted a register claim
of its own commissioner's ("class closed"), corrected the coverage headline, and — the thing
that most distinguishes it — mutation-tested the pins rather than reading them, then listed nine
things it could not verify. The structural PE is **retained**: it found the two blockers the
entire rest of the panel had walked past, and answered both open rulings with a sensitivity run
rather than an opinion.


---

## K. Fourth round — three senior engineers, and their cross-review

Three senior structural engineers reviewed independently on separate lenses — load path (SE-1),
capacity and the factor stack (SE-2), scope and sealability (SE-3) — and were then required to
**audit each other**, each ending with the findings it was least sure of and what would settle
them. The cross-review moved findings in both directions, and in one case showed that a fix would
have been applied to the wrong function.

### K.1 Blockers fixed

| # | Finding | Disposition |
|---|---|---|
| K1 | **The escalation note asserted that an unchecked member was adequate.** The procurement gate runs inside `eligibility()` *before any engine call*, yet the note read *"the member that passes … The member is adequate."* Across 112 escalations, **82% named only overstressed members** — one at DCR 2.025; the shipped coastal case named a 4x10 at **1.295**. SE-2's framing is the exact one: *"the claim is not always false — it is never checked."* | Fixed. Gated candidates are now run through the engine before any is named, only those that actually pass are listed with their measured DCR, and the note says how many others were checked and failed. |
| K2 | **Status and note came from two disagreeing classifiers**, so `escalate:procurement`, `:geometry` and `:scope` were unreachable — 7,920 synthetic demands produced only `ok` and `escalate:strength`, while the note independently took a different branch in the same object. Three of the four first-class statuses B9 introduced never fired. | Fixed. One classifier produces both, and a new `escalate:bearing` names the detailing case. A test asserts they can never disagree and that `escalate:procurement` is reachable. |
| K3 | **`boundWall()` ranked in³ against in⁴ against in² by raw magnitude**, so `I_x` was named in **17 of 17** reports — seven of them naming a property the ladder cleared by up to 68%, and *all seventeen* naming the wrong binder. | Fixed. Ranked by dimensionless shortfall ratio against the deepest rung, properties the ladder satisfies are skipped, and bearing is removed from the section wall entirely. |
| K4 | **Stud grade above 6 in wide overstated `F_b` by 33–40%** and flipped a DF-L 2x10 floor joist from 0.791 PASS to 1.054 FAIL. 266 unconservative cells, every one Stud above 6 in. | Fixed — **and the cross-review is why it was fixed in the right place.** SE-2 initially filed it as a `C_F` defect; on re-examination the two `C_F` rows are numerically identical (1.2/1.1/1.0), so `sizeFactor()` returned the right factor *by coincidence* and the entire error was in the reference values. Fixing `sizeFactor()` would have fixed nothing. The substitution now happens in `findValues()`. |
| K5 | **The garage gable header carried a wall load the model has no vocabulary for.** `ASSEMBLY{}` has zero wall entries, and the load is triangular, which `calc-spec` §8.3 excludes outright. Checked as a 2 ft roof strip it printed 4x8 at 0.896; across 27 cases spanning the plausible pitch, gable width and wall weight it runs **1.098 to 1.781 — it fails in every one.** | Fixed by refusal, the disposition SE-3 ruled for: carried as an out-of-scope mark stating what is missing and what must be declared before it can be re-admitted. |

### K.2 Findings the cross-review moved

| Finding | Filed as | Became | Why |
|---|---|---|---|
| Attic live load reaches no member | BLOCKER | **MAJOR, re-scoped** | SE-1 measured both readings: under the prevailing non-concurrent bottom-chord convention `D+Lr` beats `D+BCLL` in all six packs and **zero rows change**; under the concurrent ASCE reading, 8 of 114 move with one escalation flip. SE-1 also withdrew its own implication that the ceiling *dead* load was missing — it is inside the roof assembly makeup, and adding it would double-count. Its own conclusion: *"this needs a sentence in the spec more than it needs code."* |
| Jack-stud/plate bearing at DCR 1.04 | MAJOR | **capacity failure WITHDRAWN, scope gap upheld** | SE-2 ruled `C_b = 1.25` applies at a plate — `calc-spec` §5.4 names that exact case — so every header clears with ≥16% margin and the 1.04 was an artifact of using 1.0. SE-2 then found the live thread underneath: a **treated sill on slab** brings `C_M(F_c⊥) = 0.67` and gives **1.24**, unmodelled in either direction. Carried to §L. |
| Held `C_F` feeding the 1150 psi threshold | MAJOR | **MINOR (provenance)** | SE-2 measured the direction and found the shipped path **9.3% conservative**, not unconservative; no shipped wet cell falls in the window where holding hurts. Fixed anyway, since the fix is one expression. |
| Southern Pine `C_F` provenance | MAJOR | **MAJOR-latent** | SE-3 established the 14 in refusal is unreachable on *every* shipped path — `CF: "auto"` occurs exactly once in the codebase. Fixed anyway: the harm was a false `sourced: true` rendering as a **DB** badge beside a record whose own flag says otherwise. |
| Wet-service exception "fires universally" | stated reason | **FALSIFIED, conclusion upheld** | SE-2 enumerated all 35 reachable wet cells and found **10 that exceed 1150** and take the reduction. The conclusion — wet `F_c⊥` binds on no shipped mark — survives, but because wet marks and bearing-governed marks are disjoint sets, not for the reason given. |

### K.3 The finding the round produced that no single review had

**`bearing` had become a decisive input carried as a silent default.** PE-4 was right to move headers
from 3.5 in to 1.5 in — but that promoted bearing from a benign assumption to a design input: it
governs 3 of 66 picks and produced **4 of 24 escalations**, and **zero of 19 marks declared it.**
SE-1 ruled the correct detail independently (governing reaction 2,862 lb/end; one jack gives DCR
1.072 against the firm's own target, two jacks 0.482) and found five more rows needing more than
one jack, one needing three. SE-3 reached the same disposition from the other side.

Both also found the mechanism that concealed it: **`b_req` entered the seed bounds against member
*breadth*, and every rung in a header ladder is the same breadth** — so a bearing shortfall emptied
the entire ladder and was then reported as a stiffness wall, while the product's own repair table
says of bearing *"depth does nothing."*

Fixed with the same disposition `carries` got: **no default — a header that does not declare its
jack count throws**, every shipped header declares one, and a bearing shortfall now reports as
`escalate:bearing` with the remedy a framer can act on in ten seconds.

### K.4 The six missing marks

All six are in, derived by SE-3 from each plan's stated geometry with the derivation on the record:
the **stair opening header** (12'-6" from the pack's own plate height, 16R at 7.6 in), the
**two-story garage header** (the bonus-room envelope mark D11 asks for), the **coastal interior
bearing line**, the **coastal second-floor header** (deliberately without `wallPosition`, because
second-floor framing is wood even in a block market), the **coastal deck** and its beam, and the
**posts** under all four beam groups.

The posts cannot be checked at all — they are axial, `calc-spec` §8.20 evaluates no interaction
equation, and there is no `C_P`. They are carried as out-of-scope marks that **publish the end
reactions the tool does compute** into the note, with a third badge added because a 4x4 post is
neither a manufactured component nor "not a wood member here."

### K.5 Also fixed this round

The crossover advisory now keys on the pack's real roof load rather than the blended psf, so it
stops being suppressed on the roof+floor marks — including `nc-mountain`, the one pack where the
collapse changes the answer. `C_i` now appears in the two printed equations that did not multiply
out. Four documentation sites still claiming `C_i` is unimplemented are corrected, one of which
rendered to the user. The bath-and-laundry bay gets an assembly that includes tile. `calc-spec`
§1.4's slope statement and the absence of any wall dead load are now printed in `LIMITS`, which is
where §1.4 says they must be. And `HDR-1`, whose roof tributary contradicts its sibling one storey
up by 58%, is now carried as **not sized** rather than asserting one of three undeterminable values
— SE-3's ruling: *"substituting 12.0 replaces one asserted tributary with another and closes the
finding without answering it."*

---

## L. Conditions on release — current

**Closed:** H1, H2, D4, L4, L8, L10, L11, and all of §K.1.

**Still open:**

| # | Condition |
|---|---|
| L1 | **H3** — correct `calc-spec` §5.5, the `ex1_defl_total` / `ex2_*` fixtures, and the comment above `DEFL` in `engine.js`. Confirmed still in place by three independent reviewers now. |
| L2 | **H4 / D3** — split `q_Lr` and `q_S`. SE-1 measured the exposure as **nil on all six shipped packs today**, going live at 17.2 ≤ p_s ≤ 20 psf — a band `nc-mountain`'s own p_g of 30 reaches once p_s is actually computed. The advisory makes it visible; it does not remove it. |
| L3 | **H5** — replace the market placeholders and the site loads. |
| ~~L4~~ | **CLOSED — the schedule export ships.** See §M. |
| L5 | **The attic / bottom-chord live load question** — `ceilingLive` is wired into all six packs and read by no mark, and the spec is silent on whether a truss-bearing header receives it. A sentence in `calc-spec`, then code if the answer is yes. |
| L6 | **No wall dead load exists anywhere in the model.** Now printed in `LIMITS`; the vocabulary is still missing, and it is what made K5 unrefusable rather than checkable. |
| L7 | **Slope.** No plan declares a pitch, and the assembly psf mix on-slope and horizontal components with no published split — so the user cannot perform the conversion §1.4 makes them responsible for. At 6:12 the garage header already exceeds target; at 9:12 the typical window header does. |
| ~~L8~~ | **CLOSED — the inversion is fixed at both named defects.** `C_F` on the sheet now defaults to **`"auto"`**, resolving from the catalog for the depth actually selected, so the sheet refuses exactly what the search refuses — a 2x14 is refused in both. The typed value survives as an explicit override, badged **Typed override** on screen, because checking a size the catalog cannot source is a real need; it is no longer the default, which is what let it through. All four shipped sheets moved to `"auto"` (HDR-2 goes 1.10 → 1.00, i.e. more conservative; the others were already at the catalog value). Incising is now a checkbox, using the same `INCISED_WHEN_TREATED` list the solver uses rather than a second copy, and a wet member in a refractory species with the box unticked gets a banner saying the sheet is reading ~25% high against the same member on a schedule. Measured at 25.0%, which is 1/0.80 as Table 4.3.8 requires. |
| L9 | **A treated sill on slab** — `C_M(F_c⊥) = 0.67` with `C_b = 1.25` gives 1.24 against the plate. Unmodelled in either direction. |
| ~~L10~~ | **CLOSED — answered at 60 psf.** The two codes genuinely differ: IBC Table 1607.1 and ASCE 7-22 Table 4.3-1 both give 1.5 × the served occupancy (40 → **60**) for a balcony or deck; IRC Table R301.5 / R507's prescriptive path uses 40. The defect was never that 40 is indefensible — it is that this engine is on the IBC/ASCE path in every other respect (§2.4.1 combinations, IBC T1604.3 deflection) and was reaching across to the IRC for one load. A calculation assembled from two code paths is not conservative or unconservative, it is **uncheckable**, because no single code reproduces it. `LIVE.deck` is 60 and cited; `LIVE.deck_irc` carries 40 marked `used: false` so the fork is visible rather than silently decided. Consequence, as predicted: the previously-delivered deck members go overstressed and the search resizes them — DK-1 2x10 → 2x12 (0.739), DK-2 4x10 → 4x12 (0.755). The deck load also now appears in the export's load-provenance block, which it never did while the schedule above it was sizing deck members. |
| ~~L11~~ | **CLOSED — J8.** `test/ui-tests.js` now recomputes in the page and requires the rendered text to carry the engine's own answer: every mark's DCR and selected size across all 30 pack/plan combinations, and on the sheet every individual check's DCR plus the governing check's name — compared as text, so a front-end rewrite cannot quietly disable it by moving a cell. A wrong-but-finite number no longer renders clean. |

### Panel, final

All three senior engineers are **retained**, and the round justified its own cost: it produced five
blockers, and the cross-review then **downgraded two findings, withdrew one, falsified the reasoning
behind a fourth while upholding its conclusion, and redirected a fifth to a different function
entirely.** Each engineer downgraded or withdrew at least one of its own findings under peer
examination. That is the behaviour the structure was built to get.

The seal answer is unchanged and was never expected to change in this round: **do not seal.** The
remaining conditions are in §L, and L4 is the one that decides whether any of the rest travels.


---

## M. L4 closed — the schedule export

`calc-spec` §8 opens: *"The app must print this list, verbatim and unabridged, on every output.
A calculation that does not state its boundaries is not an engineering deliverable."* What
shipped was a ten-item paraphrase, on a different view, and the sizing schedule had no export at
all — so every honesty mechanism the panel built died at the browser window. SE-3 called this the
condition that decides whether any of the others travel.

**`scope.js`** carries all 24 boundaries verbatim. It is **generated from `calc-spec.md` by
`test/extract-scope.js`, and the suite re-runs that extractor and diffs the result** — so an edit
to the spec's boundary list cannot silently fail to reach the output the spec says must carry it.
The generated file and the test consume the same extractor, so they cannot drift from each other
either.

**`export.js`** produces the record. A schedule leaves the tool carrying:

- the wind note first and in full, banner-ruled, in any market where wind governs;
- the plan note and the wall-system note;
- **an explicit "THIS IS NOT A COMPLETE SCHEDULE" line** with the reason, whenever anything
  escalated, anything was removed as not this engine's member, or wind governs;
- the members, each with its span, tributary, bearing, service condition and bracing assumption
  on the line beneath it — so a checker can see what was assumed, not just what was picked;
- **the reaction schedule**, with the statement that the §3.4.3.1 reduction never applies to a
  reaction and that no connection is designed;
- **every escalation**, with its status, the wall that actually stopped it, the next move, and the
  out-of-scope statement;
- **every mark the engine will not size**, carried deliberately — *"a schedule that omits them
  reads as if they were fine"*;
- the advisories, including the roof-load crossover the engine cannot evaluate;
- the SKU unification moves, so a reader knows a member was raised for economics and that it
  passed its own check first;
- the SKU list;
- the load provenance — assembly makeups, the `roofLoadBasis` in full, and the site values
  **labelled as planning defaults with their class markers**;
- the material provenance and the `C_F` basis caveat;
- and the 24 boundaries, verbatim, grouped as §8 groups them, with the source named.

Fourteen assertions pin it. They check the extraction against the live spec, that **every one of
the 24 appears in the exported text**, that a wind pack leads with its note, that reactions and
not-sized marks and incompleteness all travel, that no `undefined` or `NaN` reaches the page, and
that **all 18 pack/plan combinations export cleanly** — not just the demo one.

Sample: `nc-mountain / two-story-2450` produces a 293-line record. The HVHZ coastal duplex —
the plan whose own note says the engine has the least to say about it — leads with the wind
banner and says it is not a complete schedule before it lists a single member.


---

## N. Fifth round — beta build-out for the browser demo

Five agents on partitioned files: the engine (`q_Lr`/`q_S` split, §5.5), the domain model
(master sets, small archetypes), the view, the export and spec, and an adversary attacking the
browser build. Findings that changed the code:

**N1 — the admissibility pin finally does what three documents claimed it did.** §I.6 recorded
it as corrected; only the prose had been. The test crossed packs × roles × spans × bracing —
204 demands — compared the winner and the score, and omitted the `deck` role entirely. It now
crosses **wet service, treatment, tributary and DCR target as well, over 1,920 demands, and
compares the complete feasible set candidate for candidate.** It passes. This is the third time
a claim about this particular test turned out to be stronger than the test; the difference now is
that the assertion text and the assertion body say the same thing.

**N2 — two test names cited in `solver.js` comments never existed**, and one of them also
asserted the set comparison that did not exist. Both corrected to tests that resolve.

**N3 — `escalate:geometry` gave the wrong advice.** `noFeasibleNote` had branches for
procurement and bearing only, so a member that physically does not fit under the head height fell
through to *"widen the palette or the size ladder"* — while `GATE_MOVE.geometry`, which has the
right move, sat unused. Fixed, with the direction stated: a deeper section is the wrong way to
solve a depth budget.

**N4 — `GATE_MOVE.scope` is dead** and now says so. No gate has returned `kind: "scope"` since
the incising exclusion became a computed `C_i` factor.

**N5 — the export now derives its deflection basis from the pack's declared code family.** Every
pack declares `code.family: "IRC"`, and IRC Table R301.7 has no `D+L` column — so the total-load
row is a firm overlay, and the export says so and scopes the direction. It also detects, rather
than hard-codes, that `roof_no_ceiling.total` is ℓ/180 where the table gives ℓ/120, and flags
that the citation beside that number is not where the number came from.

**N6 — `C_F` provenance is now per-member in the export**, not only a general paragraph. It fires
on 4 of 30 combinations.

### What the round could not close

- **The demo plan is not sized for what actually gets built.** On the flagship's base elevation
  in `tx-i35`, **5 of 8 marks are governed by a different variant combination.** The export now
  prints that on the page; the solver still sizes one variant at a time. `envelopeFor()` names the
  governing combination where one provably dominates and refuses where none does — the remaining
  work is to feed that back into the search.
- **D3/S8 is closed in the engine and unexercised in production.** All six combinations enumerate
  from separate `roofLive`/`snow`, but no shipped pack declares both, so nothing in the demo
  exercises the capability that closed the North Carolina band.
- `escalate:bearing`, `escalate:geometry` and `escalate:input` are reachable by construction and
  fire on no shipped pack × plan. Live distribution across 30 combinations: `ok` 136,
  `escalate:strength` 37, `escalate:procurement` 1.

---

## O. Sixth round — adversarial demo pass, then the open conditions

An adversary drove the built bundle the way an audience would: 12 routes × 2 themes × 3 widths,
30 exports, deliberate abuse. **Nothing threw.** Every finding was about the shop window rather
than the engineering, which is the right shape for a round this late — but three of them would
have been visible from the back of the room.

### O.1 What the adversary found, and what was done

| # | Severity | Finding | Disposition |
|---|---|---|---|
| B1 | **DEMO-BLOCKING** | The repeat matrix rendered 1,807px of table in a 996px container with no scroll affordance, `sticky top` but no `sticky left`. At 1280×800 two of six regions were reachable, and scrolling right lost the Mark column — six member sizes with no way to tell which mark they belonged to. | Fixed. Mark cells and the Mark header are `position:sticky; left:0`; the container scrolls and is keyboard-focusable; cells are two short lines rather than one wide one, which is what actually fits six regions. `ui-tests.js` checks it at **1440, 1280 and 1100px** and also asserts the page itself never scrolls sideways at any of them. |
| B2 | **DEMO-BLOCKING** | The demo opened on `sunbelt-ranch-1850` — 10 sized / 14 escalated / 24 not-sized of 48, the weakest plan in the product — with the first member row below the fold at 800px. It was chosen by list order, not because it shows anything. | Fixed. Default is `two-story-2450` (41/11/14 of 66), and the suite asserts the landing plan is still the strongest and the warned-about plan still the weakest, so this cannot silently invert. |
| D1 | **DAMAGING** | A green **Common** badge sat next to a `NONE` cell. `compare()` set `common: n === 1` over *distinct non-null SKUs*, so a mark sized identically in five regions and escalated in the sixth still claimed portability. This is F9's class — silence counted as agreement — surviving at **partial** silence after the first fix caught total silence. | Fixed at the flag, not the badge. `common` requires an answer in every cell; `partial` is a new state carrying `silentPacks` / `naPacks` / `answeredIn`. `FM.solver.portability()` gives one badge, one tone and one **sentence** to the screen and the paper. Live on `two-story-2450` (HDR-ST, silent in `fl-hvhz`) and on 4 marks of `starter-1210`, so it renders in the demo rather than being a theoretical branch. |
| D2 | **MAJOR** | The export printed a flat `— ESCALATED —` over five different findings. "No section is strong enough" and "a member passes but your availability floor excludes it" are opposite conclusions — one needs a bigger section, the other a phone call — and the export erased the distinction the escalation exists to make. | Fixed. `FM.solver.ESCALATION` is one vocabulary for both surfaces; escalations group and count by category; the reason rides on the member line. A mixed schedule says outright that the categories differ, and a single-category one does not lecture about a distinction it has no instance of. The field wrapper also stopped eating its own label padding (`wall   :` was coming out `wall :` with continuations hanging off a column that no longer existed). |
| D3 | **MAJOR** | `exportCalcs()` in `core.js` carried a 13-item paraphrase of `engine.LIMITS` on one 1,177-character line — **missing 12 of the 24 §8 boundaries, including item 17**, which is the one saying the bearing check that record publishes is bearing stress and not a connection design. §8 says the list prints verbatim on *every* output; §M closed L4 in the schedule only. | Fixed by removing the duplication rather than fixing the copy. `FM.scope.render()` is the one implementation; both outputs call it; a test asserts **no shipping part walks `FM.scope.items` to print its own copy**. The schedule export is byte-identical across all 30 pack/plan combinations after the refactor, verified by diff. |
| D4 | **MINOR** | Filtering the Materials table to nothing rendered headers over an empty body while the stat cards above still read 86. An empty catalog and an over-narrow filter looked identical. | Fixed. Row counts travel with the table, and an empty result says what was searched and what it searched against. |
| D5 | **MAJOR** | No URL. Back left the app, Reload dropped you on the dashboard, and a schedule worth showing a colleague had no address to send. | Fixed with hash routing — deliberately not the History API, because this ships as a `file://` bundle. Views register their own segments; `#/sizing/two-story-2450/fl-hvhz` opens cold. Boot, Back, Forward, deep link, reload and an unknown route are all asserted in a real browser. |

### O.2 Open conditions closed in the same round

**L8 — the sheet was the optimistic path.** This one was the most serious thing left open, because
the sheet is what a PE reaches for to *check* the solver, and it was more permissive than the thing
it checks. Both named defects are closed: `C_F` defaults to `"auto"` and resolves from the catalog
for the depth actually selected, so the sheet refuses exactly what the search refuses — a 2x14 is
refused in both, where before it checked clean here and was refused there. The typed value survives
as an explicit override badged **Typed override**, because checking a size the catalog cannot source
is a real need; it is no longer the *default*, which is what let it through. All four shipped sheets
moved to `"auto"`. Incising is now a checkbox using the solver's own `INCISED_WHEN_TREATED` list
rather than a second copy, and a wet member in a refractory species with the box unticked gets a
banner saying the sheet is reading high against the same member on a schedule — measured at
**25.0%**, which is 1/0.80 exactly as Table 4.3.8 requires.

**L10 — the deck live load, answered rather than carried.** IBC Table 1607.1 and ASCE 7-22 Table
4.3-1 both give 1.5 × the served occupancy for a balcony or deck (40 → **60**); IRC Table R301.5 and
the R507 prescriptive tables use 40. The defect was never that 40 is indefensible — it is that this
engine is on the IBC/ASCE path in every other respect and was reaching across to the IRC for one
load. **A calculation assembled from two code paths is neither conservative nor unconservative; it
is uncheckable, because no single code reproduces it.** `LIVE.deck` is 60 and cited; `LIVE.deck_irc`
carries 40 marked `used: false` so the fork is visible rather than silently decided. The consequence
showed, as predicted: DK-1 2x10 → 2x12 (0.739), DK-2 4x10 → 4x12 (0.755). The deck load now also
appears in the export's load-provenance block, which it never did while the schedule above it was
sizing deck members.

**L11 / J8 — numeric correctness in the DOM.** Everything the UI sweep did before was a smoke test:
it failed on NaN, undefined and Infinity, so a wrong-but-finite number rendered clean. It now
recomputes in the page and requires the rendered text to carry the engine's own answer — every
mark's DCR and selected size across all 30 combinations, and on the sheet every individual check's
DCR plus the governing check's name. Compared as text, so a front-end rewrite cannot quietly disable
it by moving a cell.

### O.3 The register's own headline, for the fourth and last time

It was wrong again: **85/162 over "6 packs × 3 plans"** when the product had five plans and measured
136/270. Three earlier printings were wrong the same way. Every correction had been another
hand-typed number with the same shelf life, so the fifth correction is a mechanism instead:
`test/coverage.js` measures it, `--sync` rewrites the sentence in this file, and the suite parses the
sentence back out and fails on disagreement. The assertion count above self-heals through
`run-tests.js --sync-register`. **A register whose headline can rot is decoration, not evidence.**

### O.4 `DEMO.md` — and why its numbers are generated too

The demo runs in a browser tomorrow, so the round produced a runbook: how to open it, what to click
in what order, what each screen proves, the questions that will be asked, and the weak spots to own
rather than be caught by. Its tables are generated by `test/demo-values.js` and asserted by the
suite, for the same reason the register's are — a runbook that tells someone what they will see is a
promise, and a stale promise diverges from the screen in front of an audience.

That mechanism immediately earned itself. The draft demo script claimed *"switch to the concrete
tile roof and HDR-2 moves."* It does not. The tile roof takes the dead load 15.0 → 22.0 psf and
shifts HDR-2 from **0.462 to 0.553** — and the member **holds, in every region**. The option that
genuinely moves members is the extended rear deck, which takes both deck marks from Southern Pine
No.2 to **No.1**: same sizes, different grade, so a purchasing change rather than a framing change,
identically in all six regions. Both beats are now pinned, along with "the bonus room changes
nothing" and "Elevation B adds marks the base plan does not have" — the latter being the case a
naive member-list diff drops entirely.

### O.5 Still open

L1, L2, L3, L5, L6, L7, L9 are unchanged, and so are the three items §N could not close: the demo
plan is still sized one variant at a time while `envelopeFor()` only *names* the governing
combination; D3/S8 remains closed in the engine and unexercised by any shipped pack; and
`escalate:bearing`, `escalate:geometry` and `escalate:input` are still reachable by construction and
fire on nothing shipped.

**The seal answer is unchanged: do not seal.** Nothing in this round was a calculation defect —
every finding was about whether an output said what the product already knew. That is a good round
to have late and a bad one to have first.

---

## P. Seventh round — the runbook driven against the app

`DEMO.md` tells a presenter what they will see. An adversary drove every prose claim in it
against the built bundle at two widths, the evening before. **Twenty-two deltas.** Six were
product defects; the rest were the runbook overclaiming. The generated tables did not drift —
the mechanism in §O.4 held — which is precisely why the deltas are all in the sentences.

### P.1 Product defects the runbook exposed

| # | Severity | Finding | Disposition |
|---|---|---|---|
| P1 | **BLOCKER** | **A stale link rendered the wrong schedule in silence.** An unknown *view* toasted; an unknown plan, region, variant, sheet or project did not — `registerSubRoute.write` discarded what it did not recognise and the view rendered its default. Measured: `#/sizing/gone-plan/...` rendered `two-story-2450`, `#/sheet/S-999` rendered `R-12`, `#/project/nope` rendered Hilltop, all with the stale hash still in the address bar and nothing on screen. This is the exact case the URL feature exists for — you send a colleague a link, the plan id changed — and it produced **a wrong answer wearing the shape of a right one**. | Fixed. Every segment is validated and every failure is named: *"This link names plan “gone-plan”, which this build does not have. Showing Two-Story 2450 in North Carolina · Piedmont instead — check the link before using this schedule."* The address bar is rewritten to what is actually on screen, unknown views included. Six stale-link cases asserted in a real browser. |
| P2 | **MAJOR** | **My own regression, one round old.** Seven reaction figures were written into mark prose by hand — "1,231 lb per post, flat across all six packs". Every one was correct when typed. Then §O's deck live load moved 40 → 60 psf, and that sentence read **1,231 against a REACTION SCHEDULE printing 1,718 in the same document**. Two reactions for one bearing, one page, nothing failing. Three of the seven were stale by the time anyone looked; one named a reaction for a mark that escalates and publishes none. | Fixed as a class. A mark declares `reactionFrom: ["DK-2"]` and the number resolves from **this run**, this pack, this variant. A named mark that escalates publishes nothing and says so — *"no reaction published — escalates — no member, so no reaction"* — rather than carrying a trial figure. A test forbids any pounds figure in a weights.js string, and asserts every borrowed reaction equals the one the reaction schedule prints. The old assertion here required the number to be **in the prose**, which is what made them hand-typed; it now requires the declaration instead. |
| P3 | **MAJOR** | **Back skipped the entire demo.** Every Sizing sub-state change called `syncHash(true)` → `location.replace`, so switching Texas → Florida and pressing Back landed on the dashboard: the two regions had never been two entries. "Take me back to Texas" is the most natural thing to try during this walk. | Fixed by drawing the line at what a user would call a step. Plan, region and variant **push** — they re-solve the schedule and produce a different answer, so Back should undo them. The tab **replaces** — it is a lens on the same answer. Both directions asserted: Back after a region change restores the region, and three tab clicks add zero history entries. |
| P4 | **MAJOR** | **The envelope card silently dropped the marks a variant adds.** `envelope()` iterated `plan.marks` — the base. On `two-story-2450` that meant BM-POR and PST-POR-B, the two marks Elevation B adds across 27 of 60 lots, were absent from a card headed "THE ENVELOPE · 8 BUILDABLE COMBINATIONS" *while the delta table directly above announced them as added*. Ask "can I size the porch beam once?" and the card had no row for it. | Fixed. The envelope walks every mark any combination introduces, and a variant-added mark is labelled as such on its row. Same defect class as D1's green badge: a card that names its scope as everything and covers one part of it. |
| P5 | **MAJOR** | **The search trace's own arithmetic did not close.** GB-1 read "search space 14 · cut by seed bounds 14 · engine evaluations 2 · rejected 10 of 16", under a footer reading *"every cut is exact — no candidate was dropped on a guess."* The cuts were exact; the **denominator** was two short, because a gate removes a candidate before the family that would have counted it is built — and `evaluated` also counted the explain pass, which re-runs candidates the search had already pruned. A trace whose arithmetic fails invites the one reader who checks to distrust the rest. | Fixed. `searchSpace` is the whole candidate population, `prunedByGate` is its own line, and `searchEvaluated` separates the search's evaluations from the explain pass's. The card states the identity so a reader can check it rather than trust the footer. Asserted on **174 mark-slots**: gate + bounds + dominance + incumbent + evaluations = the search space, everywhere. |
| P6 | **MINOR** | **"availability 0.10 is below the firm floor of 0.10"** — a sentence that refutes itself, on the card §3.3 tells the presenter to dwell on. `toFixed(2)` rounded 0.0995 up to the floor it was being compared against. | Fixed with enough precision to stay true, trailing zeros trimmed. Asserted across every procurement rejection in the product that none states a value below a floor equal to itself. |

### P.2 The runbook, corrected

Fourteen wording deltas, the substantive ones being: it claimed **two** wind-governed packs when
there are **three**; it cited **Table 4D**, which appears nowhere in the Materials view; it pointed
a technical reviewer at **§L8** for a deflection question, and L8 is closed and was never about
deflection (the open one is **L1/H3**); it placed the wall-dead-load boundary in "the printed 24"
when it is item 13 of the 13 **engine limits**, a different list the export explicitly says is not
a substitute for the 24; it said the app "lands on" the Sizing view when it cold-opens on a
Dashboard of sample data; it promised the row detail shows "the net cost of the move" when that
lives in a different card; and its Lots column summed to 72 on a 60-lot plan because attach rates
nest inside elevations rather than partitioning them.

Three UI traps the adversary found that no wording could remove were added to §5 instead of being
papered over: the green **Pick** badge sits on a member the schedule does not carry whenever
unification has fired, "About this data" is a toast rather than a link in an offline bundle, and
the Dashboard is sample data with a card labelled LRFD in an ASD-only product.

### P.3 What this round says about the previous one

P2 is the finding that matters, because it is **mine and it is one round old**. §O closed L10 by
moving a load, and moving that load silently falsified a sentence in a different file that no test
covered — the same failure mode as the coverage headline, in a place nobody had thought to
mechanise. The fix is the same one: stop writing computed numbers into prose, and add the guard
that makes writing them again fail.

The seal answer is unchanged: **do not seal.** L1, L2, L3, L5, L6, L7 and L9 remain open, and so do
the three items §N could not close.

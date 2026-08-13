# Firmark — module contracts

This file is the coordination point for parallel work. **Read it before writing
code and do not change another module's contract without changing it here
first.** Every module below is owned by exactly one author.

## The pipeline this product is

```
  PLAN (drawing / geometry)          cad.js       ← human draws or traces
        │  approval gate 1 — geometry is right
        ▼
  TAKEOFF (spans, tributary, bearing) takeoff.js  ← derived, then human-confirmed
        │  approval gate 2 — the takeoff is what the plan means
        ▼
  DEMANDS (loads, per jurisdiction)  jurisdiction.js + weights.js
        │  approval gate 3 — loads and code basis are right for this site
        ▼
  CALCULATIONS                        solver.js + engine.js   (built)
        │  approval gate 4 — the engineer accepts the members
        ▼
  BILL OF MATERIALS                   bom.js
        │  approval gate 5 — the estimator accepts the takeoff quantities
        ▼
  PACKAGE for a PE to review          planset.js
        │  approval gate 6 — THE PE STAMPS. The software never does.
        ▼
  STAMPED SET (outside this system)
```

`pipeline.js` owns the stage machine and the gates. No stage may be entered
until the previous stage is `approved` by a named person with a timestamp.

## Non-negotiables

1. **The software never stamps.** It produces a package a licensed PE reviews,
   signs and seals. Every output says so. Any wording implying otherwise is a
   defect, not a style choice.
2. **No invented values.** If a number is not derived or sourced, it is refused
   or held-and-flagged. This is the existing discipline in `engine.js` /
   `weights.js` and it extends to every new module. Every number carries a
   provenance class: `code` | `site` | `market` | `derived` | `user`.
3. **No silent fallback.** A thing that could not be computed says so by name.
   Silence has been counted as agreement three times in this codebase already.
4. **ES5 only.** No `let`/`const`/arrow/template literals/`class`. IIFE
   registering onto the global `FM`. No external libraries, no network — the
   product ships as one self-contained HTML file opened over `file://`.
5. **Everything is testable headlessly.** DOM-free logic goes in a module the
   node harness can load; DOM goes in a view. `test/harness.js` loads the
   DOM-free set.

## Ownership

| File | Owns | Author |
|---|---|---|
| `auth.js` | login gate, session, approval identities | main |
| `pipeline.js` | stage machine, gates, audit trail | main |
| `cad.js` | geometry model + drawing canvas + underlay tracing | agent CAD |
| `takeoff.js` | geometry → structural demands | agent TAKEOFF |
| `jurisdiction.js` | TX/FL/NC code adoption + site hazard params | agent JURIS |
| `bom.js` | schedule → bill of materials | agent BOM |
| `planset.js` | the PE review package | agent PLANSET |
| `engine.js` `solver.js` `weights.js` `scope.js` `export.js` | existing calc stack | main — **do not edit** |
| `core.js` `sizing.js` `sheet.js` `materials.js` | existing views | main — **do not edit** |

If you need a change in a file you do not own, say so in your report. Do not
edit it.

---

## `FM.auth` — main

```js
FM.auth.state()            // { user: {id,name,role} | null, at: iso }
FM.auth.login(u, p)        // -> {ok:true, user} | {ok:false, why}
FM.auth.logout()
FM.auth.require()          // true if signed in
FM.auth.ROLES              // { drafter, engineer, estimator, pe }
```
Demo credentials are `Demo` / `Demo`. This is a **closed** system: no view
renders until `FM.auth.require()` is true.

---

## `FM.cad` — agent CAD

The geometry model. Units are **decimal feet**, origin bottom-left, +x right,
+y up. Everything serialisable to JSON.

```js
FM.cad.MODEL_VERSION       // integer, bump on any breaking shape change

// A model:
{
  version: 1,
  name: "Starter 1210",
  levels: [{
    id: "L1", label: "First floor", topPlateFt: 9.0,
    walls: [{
      id: "W1",
      x1, y1, x2, y2,            // feet
      exterior: true,            // exterior vs interior
      bearing: true,             // carries a framing member above
      heightFt: 9.0,
      thicknessIn: 5.5,          // nominal wall thickness
      note: ""
    }],
    openings: [{
      id: "O1", wallId: "W1",
      offsetFt: 4.0,             // from wall start (x1,y1) along the wall
      widthFt: 6.0,
      headHeightFt: 6.83,
      kind: "window" | "door" | "garage" | "slider" | "passage",
                                 // "passage" is a cased opening with no leaf —
                                 // the break a beam or girder spans. A hole in
                                 // an INTERIOR bearing line is one of these and
                                 // is never a window.
      note: ""
    }],
    framing: [{                  // a framed region: which way the joists run
      id: "F1",
      polygon: [[x,y], ...],     // closed region in feet
      kind: "floor" | "roof" | "ceiling" | "deck",
      directionDeg: 0,           // 0 = joists run along +x
      spacingIn: 16,
      bearsOn: ["W1", "W3"],     // wall ids the framing bears on
      note: ""
    }]
  }],
  underlay: {                    // optional traced background
    dataUri: "data:image/png;base64,...",
    calib: { ax, ay, bx, by, knownFt },   // two points + the real distance
    opacity: 0.35
  }
}
```

```js
FM.cad.blank(name)                 // a new empty model
FM.cad.validate(model)             // -> [{level, id, severity, text}] — [] is valid
FM.cad.stats(model)                // { walls, bearingWalls, openings, areaSf, ... }
FM.cad.scaleOf(underlay)           // -> ft per pixel, or null if uncalibrated
FM.cad.toJSON(model) / FM.cad.fromJSON(str)
FM.cad.fromPlan(planId)            // build a model from an existing weights.js plan
```

`validate()` is load-bearing: a wall with no thickness, an opening wider than
its wall, a framing region that bears on nothing, a model with no bearing walls
— all named, with severity `error` (blocks the gate) or `warn` (does not).

View: `FM.VIEWS.cad`. Register a sub-route so a model is addressable.

**Underlay tracing, not PDF parsing.** The human traces over a calibrated
raster; the machine does not guess what a line means. Accept PNG/JPG by file
picker and by drag-drop. A PDF is converted to a traceable PNG by
`tools/pdf-to-underlay.js` (node side) — say so in the UI rather than silently
rejecting a `.pdf` drop.

---

## `FM.takeoff` — agent TAKEOFF

Turns geometry into the demand list `solver.js` already consumes. **This is the
module where a wrong answer is most dangerous**, because a tributary width that
is quietly wrong produces a confident, wrong member.

```js
FM.takeoff.run(model, opts)  // ->
{
  marks: [ /* the same mark shape weights.js PLANS use */ ],
  derivations: [{ markId, field, value, from, how }],   // EVERY number, traced
  unresolved: [{ what, why, need }],                    // what a human must answer
  warnings: [...]
}
```

Rules:
- A span comes from the clear distance between the walls the framing bears on.
- A tributary width is half the span each side, and it is **only** emitted when
  both sides are determined. If a framing region bears on one wall and an
  undetermined edge, the mark is `unresolved`, never assumed.
- A header comes from an opening in a **bearing** wall. Its tributary is the
  framing above it. An opening in a non-bearing wall produces no header mark and
  says why.
- `derivations` must let a reviewer reconstruct every number without reading
  code. This is what makes the takeoff reviewable at gate 2.
- Nothing is rounded up "to be safe". Refuse or report; never pad.

---

## `FM.juris` — agent JURIS

Code adoption and site hazard parameters for **Texas, Florida, North Carolina**.

```js
FM.juris.STATES              // ["TX","FL","NC"]
FM.juris.forState(code)      // adoption, amendments, the authority, provenance
FM.juris.jurisdictions(st)   // [{id, name, county, kind, ...}]
FM.juris.forSite(jurisId)    // {
                             //   codes: [{name, edition, basis, adopted, cite, cls}],
                             //   wind: {vMph, exposure, cls, cite, note},
                             //   snow: {pgPsf, cls, cite},
                             //   seismic: {sdc, ss, s1, cls, cite},
                             //   frostDepthIn, termite, decay, windborneDebris,
                             //   amendments: [{text, cite}],
                             //   mustVerify: [ ... ]        // ALWAYS non-empty
                             // }
FM.juris.checklist(jurisId)  // submittal requirements a package must satisfy
```

**Provenance is the whole job.** Every value carries `cls` (`code` | `site` |
`market`) and a citation. Anything you are not certain of goes in `mustVerify`
with what to check it against — the ASCE 7 Hazard Tool, the AHJ, the state
agency. It is far better to say "verify with the AHJ" than to state an adoption
date that is wrong. Use WebSearch to check current adoptions and **record the
date you checked**.

Things that genuinely matter here and must be modelled, not glossed:
- Texas has **no statewide residential code enforcement**; municipalities adopt.
  Coastal counties have windstorm requirements (TWIA / TDI, WPI-8 inspection).
- Florida is a **statewide** code (Florida Building Code, Residential). HVHZ is
  its own regime and is **Miami-Dade and Broward only**. Product approval / NOA
  is a submittal requirement, not a design load.
- North Carolina has its own Residential Code with state amendments on a fixed
  cycle.
- Wind speed is **not** a single number for a state. Map it to the jurisdiction
  and say it must be confirmed per site.

---

## `FM.bom` — agent BOM

```js
FM.bom.build(planResult, opts)  // ->
{
  lines: [{
    sku, size, species, grade, treatment,
    piecesPerHouse, lengthFt, stockLengthFt, piecesPerStock,
    bf, lf, unitUSD, extUSD,
    marks: ["FJ-1","FJ-3"],       // which marks this line serves
    cls: "derived",
    basis: "…"                     // how the quantity was reached
  }],
  totals: { bf, pieces, usd, byCategory: {...} },
  perLot: {...}, perCommunity: {...},   // × lots, for a tract
  excluded: [{ what, why }],      // marks NOT in the BOM and why — REQUIRED
  waste: { policy, appliedPct, basis }
}
```

**The excluded list is the honest half.** Escalated marks, out-of-scope marks,
connectors, hardware, sheathing, fasteners — anything the calc stack does not
size must be listed as absent with a reason. A BOM that silently omits the
girder reads as a complete order.

Quantities are `derived` from the schedule and the plan's counts. Prices are
`market` placeholders with no code standing — that distinction already exists in
`weights.js` and must survive into the BOM.

---

## `FM.planset` — agent PLANSET

The package a PE reviews. **Not a stamped set — a set ready to be stamped.**

```js
FM.planset.build(ctx)   // ctx = {model, takeoff, planResult, bom, juris, pipeline}
                        // -> { sheets: [{no, title, kind, render(host)}], text() }
FM.planset.render(host, pkg)
FM.planset.text(pkg)    // the printable/exportable form
```

Sheets, at minimum:
- **S0.0 Cover** — project, jurisdiction, code basis, design criteria table, the
  PE seal block **left empty with an explicit "to be sealed by" line**, and the
  approval trail from `pipeline.js`.
- **S0.1 General notes** — the 24 calc-spec §8 boundaries via `FM.scope.render`,
  the engine limits, and what is deferred to others.
- **S1.0 Framing plan** — the CAD geometry with marks placed on it.
- **S2.0 Schedules** — member schedule, header schedule, reaction schedule.
- **S3.0 Calculations** — from `FM.scheduleText`.
- **S4.0 Bill of materials** — from `FM.bom`.
- **S5.0 Open items** — everything unresolved, escalated, excluded or
  must-verify, collected from every stage. **This sheet may never be empty**;
  if it is, the package is claiming completeness it has not earned.

---

## `FM.project` — main (added after the modules were commissioned)

The run. One object holding what the user is working on, with everything
downstream **derived on demand** rather than stored.

```js
FM.project.state()      // {name, model, jurisId, packId, planId, variantId}
FM.project.set(patch)
FM.project.model()      // the CAD model — stored, or derived from planId via FM.cad.fromPlan
FM.project.takeoff()    // FM.takeoff.run(model)
FM.project.site()       // FM.juris.forSite(jurisId)
FM.project.pack()       // the weights.js region pack carrying the loads
FM.project.plan()       // the plan the solver consumes
FM.project.calcs()      // FM.solver.solvePlan(plan, pack)
FM.project.bom()        // FM.bom.build(calcs)
FM.project.planset()    // FM.planset.build(ctx)
```

Derived values are memoised **against a fingerprint of their input**, never
against a dirty flag. There is no `invalidate()` to forget to call. A module
that throws is caught and returned as `{error:true, message, where}` — a stage
that threw and a stage that produced nothing are different facts and the gate
treats them differently.

Modules do **not** need to know about this file. `project.js` reaches into them.

## `FM.pipeline` — main

```js
FM.pipeline.STAGES        // ordered [{id, label, gate, needs}]
FM.pipeline.state()       // { stageId, stages: {id: {status, by, at, note}} }
FM.pipeline.can(stageId)  // -> {ok, blockedBy}
FM.pipeline.approve(stageId, note)   // requires FM.auth user with the right role
FM.pipeline.reject(stageId, note)
FM.pipeline.audit()       // append-only trail
FM.pipeline.reset()

// how a stage gets its content and its blockers — called by project.js,
// NOT by the modules themselves:
FM.pipeline.provide(stageId, function () { return <what the view shows>; })
FM.pipeline.blocksOn(stageId, function () { return ["reason", ...]; })
FM.pipeline.fingerprint(value)   // stable, key-order-insensitive, ignores functions
```
A gate records **who** approved, **when**, and **what they were looking at** (a
hash of the stage's inputs). If an upstream stage changes after approval, every
downstream approval is invalidated and says so — an approval that survives a
change to what was approved is worthless.

---

## Build

`build.js` SCRIPTS order — dependencies load first:

```
core.js, scope.js, engine.js, weights.js, solver.js,
jurisdiction.js, cad.js, takeoff.js, bom.js, export.js, planset.js,
auth.js, pipeline.js,
materials.js, sheet.js, sizing.js, <new views last>
```

Run `node build.js` after any change, and `node build.js --check` in review.

## Tests

Add your assertions to `test/run-tests.js` in your own `suite(...)` block. DOM
behaviour goes in `test/ui-tests.js`. The suite must stay green: run
`node test/run-tests.js` before reporting done. The register's assertion count
self-heals with `--sync-register`.

Run the suite so the exit code is visible:

```
node test/run-tests.js > /tmp/t.txt 2>&1; echo "exit=$?"
```

Never `node test/run-tests.js | tail -2` inside an `&&` chain. A pipe returns
the exit status of the LAST command, so the chain sails past a red suite and
reports it as green. That is not a hypothetical: it is how a commit came to
claim 1,221 passing assertions while five were failing.

### What the node suite does NOT cover

`test/harness.js` loads fourteen modules and **not one of them is a view**:
scope, engine, weights, solver, jurisdiction, cad, dxf, takeoff, bom, export,
planset, auth, pipeline, project. `core.js`, `stages-view.js`,
`pipeline-view.js`, `sheet.js`, `sizing.js` and `materials.js` have no headless
coverage at all. Every assertion in that suite can be green while the user
interface is inoperable, and that has happened: the jurisdiction picker shipped
completely non-functional — choosing a state re-rendered the view, the fresh
`<select>` read back its own empty value, and stage 3 was unreachable through
the only path a human has. The suite was green throughout, because every
end-to-end run that "passed" had set `jurisId` from the console.

So a green `run-tests.js` is necessary and is **not** sufficient to call a build
shippable. Two browser runs stand between green and shippable:

```
node test/ui-tests.js        # behaviour: the gate, the run screen, every pack x plan
node test/ui-controls.js     # every button, link and select, clicked
```

`ui-controls.js` classifies each click against a before/after fingerprint —
route, dialogs, storage, toast — because measuring "did the DOM change" cannot
catch a dead control: **re-rendering the view IS a DOM change.** Detection by
side-effect is not detection of the right side-effect. A bare repaint of the
same view counts as nothing and fails. It also fails any control whose entire
effect is a toast admitting it does nothing — a button that says "not wired up
yet" is a promise the product cannot keep. A control either works, or it is not
there.

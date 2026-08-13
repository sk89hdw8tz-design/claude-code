# Firmark beta — demo runbook

For the person driving tomorrow. Read the first two sections before you open it;
the rest is a script you can follow live.

Every number in this file is **generated from the build**, not typed. `node
firmark-beta/test/demo-values.js` prints them and says whether this file agrees;
`--sync` rewrites the tables. The test suite fails if they drift, so if the demo
shows something different from what is written here, that is a bug in the
product and not a stale document.

---

## 1. Running it

```
open firmark-beta/firmark-app.html
```

That is the whole install. It is one self-contained HTML file — no server, no
build step, no network. Double-click it, or drag it into a browser tab. It works
from `file://`, which is why routing uses the URL hash rather than the History
API.

If you change any part (`core.js`, `engine.js`, `solver.js`, `weights.js`,
`sizing.js`, …) you must rebuild the bundle before demoing:

```
cd firmark-beta
node build.js              # rewrites firmark-app.html from the parts
node build.js --check      # fails loudly if the bundle and parts have drifted
```

**Rebuild before you demo.** The bundle is a build product, and it has shipped
stale before — that is the single most likely way for the demo to disagree with
this runbook.

### Pre-flight, the morning of

```
cd firmark-beta
node test/run-tests.js     # engine, solver, weights, exports
node build.js --check      # bundle matches the parts
node test/ui-tests.js      # real Chromium across every pack × plan
node test/coverage.js      # coverage numbers vs the review register
node test/demo-values.js   # the tables below vs the live build
```

All five clean means what is written here is what will be on screen.

---

## 2. What this is, and what it is not

Firmark is an **NDS 2024 ASD member check** with a sizing search on top of it,
aimed at repeatable residential work — tract homes, cookie-cutter plans, and
master sets reused across lots and regions.

Say this out loud early, because someone will ask:

- It **checks and selects members**. It does not produce sealed engineering. A
  licensed PE reviews and stamps every package.
- It is **gravity only**. No wind, seismic, uplift, or lateral. Three of the six
  region packs — `tx-gulf`, `fl-central`, `fl-hvhz` — are wind-governed and say so
  on screen in their own words — the
  point of that banner is that the thing governing those regions is outside this
  engine.
- It is **simply-supported single spans, sawn dimension lumber**. No continuous
  spans, no cantilevers, no glulam, LVL, PSL, LSL, I-joists or CLT.
- The full boundary list is **calc-spec §8, 24 items, verbatim** — printed on
  the schedule export and on the calc record, unabridged, every time.

The honest framing that lands best: *the value is not that it sizes a joist. The
value is that it tells you, in writing, everything it did not do.*

---

## 3. The five-minute walk

### 3.1 Open on the Sizing view

**It opens on the Dashboard, not on Sizing.** That screen is sample project data
— nine projects, one deliberately marked FAILED, and one labelled *LRFD* even
though this engine is ASD only. None of it is calculated. Either click **Sizing**
in the rail immediately, or open the file with `#/sizing/two-story-2450/nc-piedmont/schedule`
on the end of the URL so you land in the product. The second is better: the
dashboard invites questions you do not want to spend the first minute on.

Sizing defaults to **`two-story-2450`** in **North Carolina · Piedmont** — a
2,450 sf two-storey plan. Both defaults are deliberate: this is the plan with
the most marks the engine can actually size, so the first screen is full rather
than mostly caveats.

Across all six regions this plan is 41 sized, 11 escalated, 14 not-sized of 66
slots. Do not open `sunbelt-ranch-1850` cold in front of an audience — it is
10 / 14 / 24, and the first thing on screen would be refusals.

Read the incompleteness banner out loud before anything else. On this screen it
says: *"Not a complete schedule — 2 marks escalated (GB-1, HDR-GAR-2S); 2 marks
are not this engine's member. Do not read the sized marks as a finished design."*
The escalations are named by mark id; the not-this-engine marks are a count here
and are named individually in the card further down. There is no wind clause on
this screen — `nc-piedmont` is gravity-governed, and that clause only appears in
the three wind markets. **The tool says what it did not do before it says what it
did.** If you say that sentence once during the demo, say it here.

### 3.2 The schedule, in Texas

Switch the region to **Texas · I-35 corridor**.

<!-- fm:schedule-tx-i35 -->
| Mark | Member | Spacing | Governs | DCR | Note |
|---|---|---|---|---|---|
| FJ-1 | `2x12 Southern Pine No.2` | 16″ | Bending | 0.695 | unified onto this SKU |
| FJ-2 | `2x12 Southern Pine No.2` | 16″ | Bending | 0.857 |  |
| FJ-3 | `2x12 Southern Pine No.2` | 16″ | Bending | 0.410 | unified onto this SKU |
| GB-1 | **escalates** | — | — | — | no section strong enough |
| HDR-1 | _not sized_ | — | — | — | underdetermined |
| HDR-2 | `4x6 Southern Pine No.2` | single | Bending | 0.462 |  |
| DK-1 | `2x12 Southern Pine No.2` | 16″ | Bending | 0.739 |  |
| DK-2 | `4x12 Southern Pine No.2` | single | Bending | 0.755 |  |
| HDR-ST | `4x12 Southern Pine No.1` | single | Bending | 0.856 |  |
| HDR-GAR-2S | **escalates** | — | — | — | no section strong enough |
| PST-DK | _not sized_ | — | — | — | out-of-scope |
<!-- /fm:schedule-tx-i35 -->

Three things to point at, in this order:

1. **FJ-3 is at DCR 0.410.** That is not the solver being wasteful. Its own pick
   was a 2x8; it was *unified* onto the 2x12 that FJ-2 needs. Click the row: the
   Result card shows the member the schedule carries and *"Raised by SKU
   unification: yes"*, and in the ranked list below it the 2x8 carries a green
   **Pick** badge — say out loud that Pick is the search's own first choice
   *before* unification raised it, or the two members on one screen will read as
   a contradiction. The net cost of the move is not in the row; it is in the
   **SKU unification** card at the foot of the page — extra lumber against SKU
   saving, for the whole group. **One SKU instead of three is worth more on a
   tract plan than the lumber saved on the short joist**, and that trade is the
   product.
2. **GB-1 escalates.** The centre floor girder wants more section modulus than
   the deepest sawn member in the ladder has, and the card says by how much —
   *"the deepest section gives 73.83 in³ of S_x and this member needs 131.73 —
   short by 78%."* Press **Show the search record** for the rest: that a span
   like this in a tract plan is normally an engineered header, which this engine
   does not select. It refuses instead of guessing. The trace on that record is
   also worth a beat — search space, what each heuristic cut, and evaluations,
   and the five numbers add up to the space they came from.
3. **HDR-1 is not sized, PST-DK is not sized.** Different reason: those are
   carried deliberately rather than dropped. A schedule that omits a mark reads
   as if the mark were fine.

### 3.3 Switch the region to Florida HVHZ

Same plan, same spans, same loads. Change only the region.

<!-- fm:schedule-fl-hvhz -->
| Mark | Member | Spacing | Governs | DCR | Note |
|---|---|---|---|---|---|
| FJ-1 | `2x10 Southern Pine No.1` | 16″ | Bending | 0.734 |  |
| FJ-2 | `2x12 Southern Pine No.1` | 16″ | Bending | 0.643 |  |
| FJ-3 | `2x8 Southern Pine No.2` | 16″ | Bending | 0.801 |  |
| GB-1 | **escalates** | — | — | — | no section strong enough |
| HDR-1 | _not sized_ | — | — | — | underdetermined |
| HDR-2 | `4x6 Southern Pine No.2` | single | Bending | 0.553 |  |
| DK-1 | `2x12 Southern Pine No.2` | 16″ | Bending | 0.739 |  |
| DK-2 | `4x12 Southern Pine No.2` | single | Bending | 0.756 |  |
| HDR-ST | **escalates** | — | — | — | excluded by availability |
| HDR-GAR-2S | _not sized_ | — | — | — | wall-system |
| PST-DK | _not sized_ | — | — | — | out-of-scope |
<!-- /fm:schedule-fl-hvhz -->

Two moments here, and they are the best two in the demo:

1. **The joists stop unifying.** Texas collapses FJ-1 and FJ-3 onto FJ-2's
   2x12; Florida does not. The reason is the palette: Spruce-Pine-Fir is in the
   Texas palette and is not in the HVHZ palette, so the whole cost landscape
   moves and the unification that paid in Texas stops paying in Florida. Nobody
   configured that outcome — it falls out of the weights.
2. **HDR-ST escalates for a completely different reason than GB-1.** It is not
   "no member is strong enough." A member **passes the check** and the region
   pack's availability floor excludes it. The escalation names that member and
   prints its DCR, because that is a phone call to the yard, not a redesign.
   This distinction is the one to labour: an escalation that does not say which
   kind it is has told you nothing.

Also note **HDR-GAR-2S flips from escalating to not-sized** between the two
regions — the mark's applicability is regional.

### 3.4 North Carolina Mountains, briefly

<!-- fm:schedule-nc-mountain -->
| Mark | Member | Spacing | Governs | DCR | Note |
|---|---|---|---|---|---|
| FJ-1 | `2x12 Southern Pine No.2` | 16″ | Bending | 0.695 | unified onto this SKU |
| FJ-2 | `2x12 Southern Pine No.2` | 16″ | Bending | 0.857 |  |
| FJ-3 | `2x12 Southern Pine No.2` | 16″ | Bending | 0.410 | unified onto this SKU |
| GB-1 | **escalates** | — | — | — | no section strong enough |
| HDR-1 | _not sized_ | — | — | — | underdetermined |
| HDR-2 | `4x6 Southern Pine No.2` | single | Bending | 0.573 |  |
| DK-1 | `2x12 Southern Pine No.2` | 16″ | Bending | 0.739 |  |
| DK-2 | `4x12 Southern Pine No.2` | single | Bending | 0.756 |  |
| HDR-ST | `4x12 Southern Pine No.1` | single | Bending | 0.856 |  |
| HDR-GAR-2S | **escalates** | — | — | — | no section strong enough |
| PST-DK | _not sized_ | — | — | — | out-of-scope |
<!-- /fm:schedule-nc-mountain -->

The floor comes back identical to Texas; **HDR-2 moves from 0.462 to 0.573**
because the mountain snow load is real. Use this to make the point that the
plan is portable and the *loads* are not.

### 3.5 The repeat matrix

The tab that answers the question a production builder actually has: *which
marks can I buy once for the whole region set, and which have to be decided per
region?* The tab itself is a mark × region board with four group headings. The
table below is **measured from the build, not read off that tab** — the SKU and
escalation counts live on the Schedule tab's stat cards, one region at a time.

<!-- fm:skus -->
| Region | Distinct SKUs | Marks unified | Escalations |
|---|---|---|---|
| Texas · I-35 corridor (`tx-i35`) | 4 | 2 | 2 |
| Florida · High-Velocity Hurricane Zone (`fl-hvhz`) | 6 | 0 | 2 |
| North Carolina · Mountains (`nc-mountain`) | 4 | 2 | 2 |
<!-- /fm:skus -->

Watch the badges. A mark is **Common** only when *every* region produced a
member. A mark that agrees in five regions and has no member in the sixth reads
**Partial** and names the region it could not answer — on `two-story-2450` that
is `HDR-ST`, silent in `fl-hvhz`. That is deliberate and it is worth calling
out: the badge is not allowed to make a portability claim the row's own cells
contradict.

### 3.6 The master set — the part a production builder came to see

Back to **North Carolina · Piedmont**. There are two chip rows — **Elevation**
first, then **Built with**. Beat 4 below is in the Elevation row, the rest are in
Built with. Note the picker offers one option at a time: there is no "bonus room
*and* tile" chip, because that combination is not declared. If someone asks for
it, the honest answer is that the picker only offers combinations the master set
actually declares and never composes one by hand.

One stamped plan, reused across lots. Elevations are mutually exclusive and
their take rates sum to 1.00; options attach independently. The picker only
offers combinations that are actually buildable — it never composes a variant
id by hand — and selecting one **re-solves the whole schedule**. What you are
looking at is that variant, end to end: its stats, its escalations, its
unification, its cost. Not the base plan with annotations.

Here is what each one does, measured, on the 60 lots of this plan. **The Lots
column is expected attach rates, not a partition** — the 12 bonus-room lots sit
*inside* the 33 Elevation A lots, so the column sums to more than 60 on purpose.
The partition is the two elevations: 33 + 27 = 60. Say that before anyone adds
it up. (The stat line on screen reads "33 lots" because it is describing the
selected elevation, not the plan.)

<!-- fm:variants -->
| Built with | Lots | What it does to the schedule |
|---|---|---|
| Elevation A · as stamped + Bonus room over the garage | 12 | nothing — every member holds |
| Elevation A · as stamped + Extended rear deck · 26 ft × 14 ft | 8 | **moves** DK-1: 2x12 Southern Pine No.2 → 2x12 Southern Pine No.1; DK-2: 4x12 Southern Pine No.2 → 4x12 Southern Pine No.1 |
| Elevation A · as stamped + Concrete tile roof | 5 | same members, DCR shifts: HDR-2 0.462 → 0.553 |
| Elevation B · covered front porch | 27 | **adds** BM-POR (4x8 Southern Pine No.2), PST-POR-B (not sized) |
| Elevation B · covered front porch + Bonus room over the garage | 9 | **adds** BM-POR (4x8 Southern Pine No.2), PST-POR-B (not sized) |
| Elevation B · covered front porch + Extended rear deck · 26 ft × 14 ft | 7 | **adds** BM-POR (4x8 Southern Pine No.2), PST-POR-B (not sized)<br>**moves** DK-1: 2x12 Southern Pine No.2 → 2x12 Southern Pine No.1; DK-2: 4x12 Southern Pine No.2 → 4x12 Southern Pine No.1 |
| Elevation B · covered front porch + Concrete tile roof | 4 | **adds** BM-POR (4x8 Southern Pine No.2), PST-POR-B (not sized)<br>same members, DCR shifts: HDR-2 0.462 → 0.553 |
<!-- /fm:variants -->

Drive it in this order, because it builds:

1. **Bonus room over the garage.** Nothing changes. That is the answer to "can
   we offer this?" — yes, no re-engineering, and here is the evidence rather
   than someone's recollection.
2. **Concrete tile roof.** Still no member changes, but the numbers move: the
   dead load goes 15.0 → 22.0 psf and the window header goes from 0.462 to
   0.553. The delta column says *why* it moved, not just that it did. **The
   member holds** — which is a stronger result than a change, because it is the
   one nobody can confirm from memory.
3. **Extended rear deck, 26 × 14.** Now members move: both deck marks go from
   Southern Pine No.2 to **No.1**. Same sizes, different grade — the *member*
   change is a purchasing change rather than a re-framing, and it is the same
   change in all six regions. Do not say "not a framing change" flatly: the deck
   itself grew, and the delta column says so (`span 12.0 → 14.0 ft`).
   Then open the **PST-DK** accordion under *Not this engine's member*. The deck
   now stands on four posts instead of two, each carrying 7.0 ft of tributary
   instead of 6.0, and the post's design load is printed there as DK-2's live
   end reaction **for this variant** — this engine does not select posts, and it
   hands you the load rather than pretending the question isn't there.
4. **Elevation B.** Two marks appear that the base plan does not have — a porch
   beam, sized, and a porch post, not sized. A variant that *adds* marks is the
   case a naive member-list diff drops entirely.

Then scroll to the **envelope card** — it is always on screen, nothing to open.
It answers the question the whole feature exists for: *can I size this mark once for the whole master set?* It names a
variant only where that variant dominates on **every** driver at once — span,
tributary, load, depth budget — and where no single variant dominates it says
so and prints the marks that have to be sized variant by variant. On
`coastal-duplex-1600` in `fl-hvhz` it comes back **Split**. That is the honesty
slide: the feature refuses to compose a maximum out of parts.

### 3.7 The URL is the deliverable

Copy the address bar and paste it into a second tab. Something like:

```
#/sizing/two-story-2450/nc-piedmont/schedule/b+opt-tile
```

Same plan, same market, same elevation-and-option, cold, in a fresh tab. **That
is what you send the truss supplier.**

Three things about it worth being precise on, because someone will test them:

- **Back and Forward step between the things you would call steps** — a view, a
  region, a plan, a variant. Changing the *tab* refines the address in place and
  does not stack, so Back will not walk you back through Schedule → Region →
  Matrix.
- **Reload lands where you were**, variant and all.
- **A link naming something this build does not have says so.** An unknown view,
  plan, region, variant, sheet or project all fall back *and* toast *and* correct
  the address bar. That matters more than it sounds: a link that silently
  rendered a different plan would be a wrong answer in the shape of a right one.

### 3.8 Export the schedule

Hit the export. Show the text file. The things to scroll to:

- the wind note, banner-ruled and high in the file, on the three wind-governed packs
- **THIS IS NOT A COMPLETE SCHEDULE** near the top
- the reaction schedule (the marks that are out of scope still publish their
  reactions — you cannot size the post here but you can hand someone the load)
- the escalations, **grouped and counted by category**, with the sentence
  saying the categories are not the same finding
- the **24 scope boundaries, verbatim** at the back

The same 24 come out of the calc record on the Calculations view. One renderer
feeds both — they cannot say different things.

---

## 4. Questions you will get

**"Can it do the whole house?"**
No, and it says so per mark rather than quietly. Girders over long spans,
engineered headers, posts, and anything wall-system escalate or come back as
not-sized with a reason. On `two-story-2450` that is 11 escalations and 14
not-sized slots out of 66 across six regions.

**"Why is that member so oversized?"**
Almost always unification. Open the row — the detail shows both the member the
search picked and the member it was moved onto, with the net cost of the move.
If it is not unification, the DCR and governing check are on the row.

**"Where do the loads come from?"**
The export has a load-provenance section with every value tagged `code`, `site`
or `market`. Site loads are labelled **planning defaults, not site values** —
they are placeholders until someone puts the real ground snow and the real
exposure in. Do not let this one slide past; it is an open item, not a feature.

**"Is the material data real?"**
Yes — NDS Supplement Tables 1B, 4A, 4B and 5A, plus the AISC Shapes Database
v16.0, in the Materials view, each tab carrying its own citation. The one gap is deliberate and stated on that
page: the size-factor (`C_F`) table is not in the catalog, so `C_F` is a typed
input and every member that uses an unsourced one is flagged on the schedule
line, not in a footnote. **If you want to show it, switch to `townhome-1220` in
`tx-i35`** — the demo plan happens to have no unsourced-`C_F` member in any
region, so exporting it will not demonstrate the claim.

**"What happens on a bad link / refresh?"**
Routing is in the URL hash. `#/sizing/two-story-2450/fl-hvhz` opens that plan in
that region from cold. Back and Forward step between views, regions, plans and
variants; a tab change refines the address rather than stacking it. Reload lands
where you were. A link naming a view, plan, region, variant, sheet or project
this build does not have falls back, says which part it could not find, and
rewrites the address bar to match what is on screen. Feel free to demonstrate
any of it — all of it is tested in a real browser.

---

## 5. Known-weak spots — steer around or own them

| Thing | What happens | What to say |
|---|---|---|
| `sunbelt-ranch-1850` | 10 sized, 14 escalated, 24 not-sized of 48 | Do not open it cold. If asked, it is a real result about a plan with a lot of long-span and wall-system marks, not a failure to run. |
| Site loads | Ground snow, exposure and wind speed are planning defaults | Say it before they find it. They are labelled everywhere they are used. |
| Total-load deflection | `calc-spec` §5.5 disagrees with the engine, and the engine is right | Open item **§L1 (H3)** in the review register — confirmed still in place by three reviewers. Do not cite §L8 for this; L8 was the sheet-vs-solver `C_F` inversion and it is closed. |
| No wall dead load | A header under a gable end or an upper storey needs that load added by hand | It is item 13 of the 13 **engine limits** in the export — a different list from the 24 calc-spec §8 boundaries, and the export says so itself. |
| Attic bottom-chord live, slope/pitch | Not modelled | Spans are horizontal projections; converting a sloped assembly is the user's job, and the export says so. |
| The **Pick** badge in a search record | On a unified mark it sits on a member the schedule does not carry | Name it when you open the row: Pick is the search's own first choice, before unification raised it. See §3.2 beat 1. |
| "About this data" on Materials | It is a toast, not a link — no network in a `file://` bundle | If someone wants the catalogs, write the URL down; the button will not open anything. |
| The Dashboard | Sample data, one card marked FAILED, one labelled LRFD | Do not linger. §3.1 tells you how to skip it. |

The full list of open release conditions is `REVIEW-REGISTER.md` §L. If someone
technical is in the room, that document is the better thing to hand them than
any slide — it is a register of what is wrong, with dispositions, and it holds
up better than a claim that nothing is.

---

## 6. If something breaks live

- **Blank view / nothing renders** — open the console. If `FM is not defined`,
  the bundle is stale or a part has a syntax error; run `node build.js`.
- **A number reads `NaN` or `—`** — that is a real bug, and `test/ui-tests.js`
  is supposed to catch it across every pack × plan. Note the mark and the
  region; it is reproducible.
- **The demo disagrees with this document** — trust the app, then run
  `node test/demo-values.js` afterwards. Either the tables here are stale (they
  should not be — the suite checks them) or the build changed.
- **Nothing at all works** — `git stash` any local edits and `node build.js`.
  The committed bundle is known green.

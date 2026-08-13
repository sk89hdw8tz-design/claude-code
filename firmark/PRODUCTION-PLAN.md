# Firmark — what stands between the beta and production

Written 13 Aug 2026, against the beta at `1616965`. Every claim about the
current build is measured, not remembered; every gap is named with what it
would take to close it.

Readable version:
<https://claude.ai/code/artifact/06421d7d-ddff-4886-9a64-81b9e815509d>
(private until shared). This file is the source of truth — update it first.

The product goal, in your words: *an architectural plan into calculations, a
bill of materials, and PE-stampable plan sets in minutes, with human approval
gates at every stage* — for cookie-cutter residential, tract homes and master
sets, repeatable across **Texas, Florida and North Carolina**.

---

## 1. What the beta actually does today

Verified, not asserted:

| Capability | State | Evidence |
|---|---|---|
| NDS 2024 ASD member check | works | 1,663 assertions; every rendered DCR re-checked against an independent engine run |
| Six approval gates, fingerprinted | works | approvals invalidate when the content they were given moves |
| Geometry → takeoff → demands | works | 9 of 15 plan × state runs pass all six gates in 0.6 s |
| Bill of materials | works | quantities derived from the schedule; prices are `[market]` placeholders |
| Plan set for PE review | works | 7 sheets, ~105 k characters, seal block deliberately empty |
| DXF framing plan | works | R12/AC1009, 21 AIA layers, ezdxf-clean, 1 unit = 1 inch verified |
| 21 jurisdictions across TX/FL/NC | present, **unverified** | needs the code consultant |
| Runs on a phone | works | all 18 views, no overflow at 393 px |

**The honest headline:** the calculation engine is real and disciplined. What
surrounds it is a demonstration.

---

## 2. The gap that matters most

> **The engine declares 24 scope boundaries. For tract homes in Texas, Florida
> and North Carolina, three of them are not edge cases — they are the job.**

### 2.1 Lateral loads are out of scope

Boundary: *"Lateral loads — wind and seismic."*

This is the single largest blocker, and it is not close. You cannot produce a
PE-stampable structural set for a house in Miami-Dade, coastal North Carolina
or the Texas gulf without lateral. The jurisdictions the beta already
enumerates are precisely the ones where lateral governs:

- FBC 8th Edition adopts ASCE 7-22, whose wind-borne-debris test now keys on an
  Exposure D upwind fetch of ≥5,000 ft rather than the word "coastal" — which
  pulls in large inland lakes nobody used to treat as debris regions.
- NC has a dedicated high-wind chapter (NCRC Ch. 45).
- HVHZ has its own rules again on top of that.

The beta's jurisdiction module already carries the basic wind speeds, the code
edition and the debris-region determinations. **It computes no lateral force
with them** — there is no velocity pressure, no `K_zt`, no `GC_p`, nothing.
That data is currently informational. `bom.js` is candid about the consequence:
wall bracing, shear walls and portal frames are listed as an explicit exclusion
from the bill of materials.

One design constraint the lateral work must respect, and it is already right in
the beta: **`wind.exposure` is null for every jurisdiction, deliberately.**
Exposure is a property of the terrain upwind of the actual site, not of a city,
so publishing it per-city would be an invented value of the worst kind — one
that looks authoritative and silently changes every pressure downstream.
Exposure has to be a per-project, per-site input a human supplies and signs for.
Any lateral module that quietly defaults it has broken non-negotiable 2.

What it takes: a lateral module — wind pressures per ASCE 7-22 Ch. 26–30,
seismic per Ch. 11–12 (low in all three states, but not zero in NC), then
distribution to shear walls, and IRC R602.10 braced-wall-panel checks as the
prescriptive path most tract homes will actually use. Prescriptive first is the
right call: R602.10 covers the overwhelming majority of these houses and is far
less work than a full engineered analysis.

### 2.2 Connections are out of scope

Boundary: *"Connections of every kind — hangers, straps, bolts, screws, nails,
hold-downs, bearing plates as designed elements."*

In a hurricane region the connections **are** the structure. A continuous load
path from roof to foundation — uplift straps, hold-downs, anchor bolts — is
what a plans examiner in Broward County looks for first. A set without it is
not reviewable.

What it takes: NDS Ch. 11–12 fastener capacities, plus a manufacturer catalogue
layer (Simpson/USP) with the same provenance discipline the rest of the
codebase uses. This is well-bounded work and highly repeatable across tract
plans — exactly the kind of thing that pays back on a master set.

### 2.3 Multi-span, built-up and composite members are out of scope

Boundaries: *"Multi-span and continuous members"*, *"Built-up and composite
members — multi-ply nailed or bolted beams, flitch beams, ply-to-ply load
sharing"*, *"Cantilevers"*.

Every tract home has a multi-ply garage header and a continuous girder. Today
those fall out as escalations rather than answers. Of the 264 mark-slots the
register tracks, **90 are "not this engine's member"** — a third of the work
walks out of the door to be sized by hand.

---

## 3. The gap between a demo and a system

These do not need engineering judgement, only building.

**No project intake.** Nothing binds an address, a plan, a jurisdiction and an
owner into a job. The nine projects on the dashboard are sample data. The
button that pretended otherwise was removed rather than faked. Until this
exists there is no such thing as "a job" in the product.

**No durable record.** Everything lives in one browser's `localStorage`. Sign-in
does not survive a reload. An approval trail that a user can clear from
developer tools — or lose by switching phones — is not an engineering record,
and the whole value proposition rests on that trail being trustworthy. This
needs a server, real identity, and an append-only audit log.

**No plan ingestion.** A drawing reaches the model only by a human tracing it
over a calibrated raster. That is honest — the machine does not guess what a
line means — but it is also the slowest step in a pipeline advertised as
"minutes". For tract homes there is a much better answer than PDF parsing:
**a master set is drawn once and reused.** The variant machinery already exists
(elevations A/B, bonus room, extended deck). Investment belongs there, not in a
PDF parser.

**No beams, posts or columns as drawable entities.** `cad.js` has walls,
openings and framing regions. Marks for beams and posts appear in the schedule
and cannot be drawn on the framing plan.

**No wall self-weight.** Register §L6. This is why the townhome stops at
takeoff: a header carrying two storeys of wall above a non-bearing opening
cannot be derived without a wall dead load in psf, so it correctly refuses
rather than inventing one.

---

## 4. Data and verification obligations

**The 21 jurisdictions are unverified.** Two published values were already found
wrong during this build — Austin's code edition (it is the 2024 IRC under
Ordinance 20250410-040, effective 10 Jul 2025, with ASCE 7-22, not the 2021
IRC/ASCE 7-16) and Orange County's wind-borne-debris determination, which was
asserted `false` and is now `null` with a blocking check. Two errors found means
the set has not been audited. **This is the code consultant's work and it gates
everything**: every number downstream inherits the code basis.

**Three garage headers have inconsistent mark data.** They declare `bearing: 4.5`
(three jack studs, from the reaction per §K3) while their span was derived for
two jacks, so each drawn rough opening is 3 in short of the door its own note
names — a 9'-0" door drawing at 8'-11". Sunbelt's `HDR-GAR-B` declares
`bearing: 3.0` and comes out right, which proves the diagnosis. Left unchanged
deliberately: `span` is a solver input across six region packs and moving it
shifts escalation counts. **Your call.**

**`coastal-duplex-1600` does not close** — 1,600 sf declared against
26 × 32 × 2 = 1,664 gross, with no garage or stair deduction stated. 64 sf
unreconciled; the only one of the five plans that fails to reconcile.

---

## 5. Order of work

Sequenced by what unblocks the most, not by what is easiest.

**First — make the record real.** Server, identity, append-only audit log,
project intake. Nothing else is worth hardening while the trail lives in a
browser tab. This is also what turns "a demo I can show" into "a system a firm
can use".

**Second — braced wall panels (IRC R602.10).** The prescriptive lateral path.
Covers most tract homes, uses jurisdiction data already present, and is the
shortest route to a set a plans examiner will accept.

**Third — connections and the continuous load path.** Straps, hold-downs,
anchors. Without it a coastal set is not reviewable regardless of how good the
member check is.

**Fourth — multi-ply and multi-span members.** Recovers a large share of the 90
mark-slots currently escalating out of the engine.

**Fifth — engineered lateral (ASCE 7-22 full).** For the houses R602.10 will not
cover.

**Running alongside all of it — jurisdiction verification.** Consultant-led,
starting with the three states' plan sets you are supplying.

---

## 6. What must not change

`ARCHITECTURE.md` carries **five** non-negotiables, and this section previously
said four — quoting three of them correctly and substituting, as a fourth, a
working rule that is not in that list at all. A peer reviewer caught it. Two
governing documents disagreeing about what governs is a document-control
finding, not a nit, so the list is now reproduced as it actually reads:

1. **The software never stamps.** It produces a package a licensed PE reviews,
   signs and seals. The seal block on S0.0 is empty on purpose.
2. **No invented values.** If a number is not derived or sourced, it is refused
   or held-and-flagged. The townhome stopping at takeoff is this rule working,
   not failing.
3. **No silent fallback.** Anything that could not be computed says so by name.
   Silence has stood in for agreement three times here already.
4. **ES5 only.** No libraries, no network — one self-contained HTML file.
5. **Everything is testable headlessly.** DOM-free logic in a module the node
   harness can load; DOM in a view.

A sixth rule was established during the interface audit and belongs in
`ARCHITECTURE.md` rather than being quoted as though it were already there:
**a control either works, or it is not there.** A button that toasts "not wired
up yet" is a promise the product cannot keep.

A production version that keeps the speed and drops these is a liability
generator. The discipline is the product.

A production version that keeps the speed and drops these is a liability
generator. The discipline is the product.

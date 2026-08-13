/* ============================================================
   FM.juris — jurisdiction and code-adoption assertions.

   Exported as a suite so it can be mounted by the runner without
   four parallel agents editing run-tests.js at once:

       require("./suite-juris.js")(t, FM);

   where `t` is { suite, eq, near, truthy } and FM is a harness
   context loaded with at least weights.js and jurisdiction.js.

   What these assertions are FOR:

   This module's whole value is that it refuses to state things it
   does not know. That refusal is only worth anything if it cannot
   be quietly withdrawn later — if someone adds a jurisdiction next
   month with a confident wind speed and no mustVerify entry, the
   suite has to notice. So the tests here are mostly INVARIANTS ON
   HONESTY rather than fixtures on values:

     - a value with no citation cannot exist
     - a wind speed that does not say "confirm this at the site"
       cannot exist
     - an empty mustVerify cannot exist
     - an exposure category or an S_s cannot be asserted at all
     - a reported pack difference must be a real difference,
       measured against the live pack, not a remembered one

   The last one matters most. `packFor()` claims a pack is wrong
   for a site by a stated amount. If weights.js changes a pack's
   wind speed and this module keeps reporting the old delta, the
   report becomes a confident error about a confident error. So the
   differences are recomputed here from FM.weights.PACKS directly
   and compared, rather than pinned to numbers typed in a test.
   ============================================================ */

"use strict";

module.exports = function (t, FM) {

  var ALL = FM.juris.jurisdictions();

  function packById(id) {
    var hit = FM.weights.PACKS.filter(function (p) { return p.id === id; });
    return hit.length ? hit[0] : null;
  }

  /* ============================================================
     1. The module resolves at all
     ============================================================ */

  t.suite("juris · states and jurisdictions resolve");
  (function () {
    t.eq(FM.juris.STATES.join(","), "TX,FL,NC", "the module covers exactly TX, FL and NC");

    var resolved = FM.juris.STATES.filter(function (s) {
      var st;
      try { st = FM.juris.forState(s); } catch (e) { return false; }
      return !!(st && st.code === s && st.name && st.authority && st.statute &&
                st.statute.length && st.mustVerify && st.mustVerify.length);
    });
    t.eq(resolved.length, FM.juris.STATES.length,
         "every state resolves with an authority, a statute list and its own standing conditions");

    /* lower case must work — a state code is user input somewhere */
    t.eq(FM.juris.forState("tx").code, "TX", "forState is case-insensitive");

    var threw = false;
    try { FM.juris.forState("CA"); } catch (e) { threw = true; }
    t.truthy(threw, "an out-of-scope state throws by name rather than returning a default");

    var threwJ = false;
    try { FM.juris.forSite("nowhere-at-all"); } catch (e) { threwJ = true; }
    t.truthy(threwJ, "an unknown jurisdiction throws — substituting one substitutes a code basis");

    t.truthy(ALL.length >= 20,
             "the table covers the tract-home markets, not a sample (" + ALL.length + " jurisdictions)");

    var perState = FM.juris.STATES.every(function (s) {
      return FM.juris.jurisdictions(s).length >= 6;
    });
    t.truthy(perState, "each state carries at least six jurisdictions");

    var everySiteResolves = ALL.every(function (j) {
      var s;
      try { s = FM.juris.forSite(j.id); } catch (e) { return false; }
      return !!(s && s.codes && s.codes.length && s.wind && s.snow && s.seismic &&
                s.frostDepthIn && s.termite && s.decay && s.windborneDebris && s.amendments);
    });
    t.truthy(everySiteResolves, "forSite() returns the full contract shape for every jurisdiction");

    var everyChecklist = ALL.every(function (j) {
      var c = FM.juris.checklist(j.id);
      return c.length > 0 && c.every(function (i) { return i.item && i.why && i.cite; });
    });
    t.truthy(everyChecklist,
             "checklist() is non-empty everywhere and every item states its reason and its citation");
  })();

  /* ============================================================
     2. mustVerify is never empty — the contract's own rule

     "Anything you are not certain of goes in mustVerify with what
     to check it against." The failure mode this guards is a
     jurisdiction added later that looks complete because nobody
     wrote down what was still open.
     ============================================================ */

  t.suite("juris · mustVerify is never empty and always says what to check against");
  (function () {
    var empty = ALL.filter(function (j) {
      return FM.juris.forSite(j.id).mustVerify.length === 0;
    });
    t.eq(empty.length, 0,
         "every jurisdiction has a non-empty mustVerify" +
         (empty.length ? " — empty in " + empty.map(function (j) { return j.id; }).join(", ") : ""));

    /* an entry with no `check` is a hedge, not a condition */
    var vague = [];
    ALL.forEach(function (j) {
      FM.juris.forSite(j.id).mustVerify.forEach(function (m) {
        if (!m.what || !m.why || !m.check || !m.authority) vague.push(j.id + "/" + (m.id || "?"));
      });
    });
    t.eq(vague.length, 0,
         "every mustVerify entry says WHAT, WHY, what to CHECK it against and WHO the authority is" +
         (vague.length ? " — incomplete: " + vague.slice(0, 5).join(", ") : ""));

    /* the two unconditional ones must be present everywhere */
    var missingWind = ALL.filter(function (j) {
      return !FM.juris.forSite(j.id).mustVerify.some(function (m) {
        return m.id === j.id + "/wind";
      });
    });
    t.eq(missingWind.length, 0, "every jurisdiction carries a wind-confirmation condition");

    var missingAdoption = ALL.filter(function (j) {
      return !FM.juris.forSite(j.id).mustVerify.some(function (m) {
        return m.id === j.id + "/adoption";
      });
    });
    t.eq(missingAdoption.length, 0,
         "every jurisdiction carries an adoption-currency condition — adoption cycles move");

    /* and the state's standing conditions must reach every one of
       its jurisdictions, not just be declared at state level */
    var carriesState = ALL.every(function (j) {
      var stIds = FM.juris.forState(j.state).mustVerify.map(function (m) { return m.id; });
      var mine = FM.juris.forSite(j.id).mustVerify.map(function (m) { return m.id; });
      return stIds.every(function (id) { return mine.indexOf(id) !== -1; });
    });
    t.truthy(carriesState,
             "the state's standing conditions travel down into every one of its jurisdictions");
  })();

  /* ============================================================
     3. Every value carries a class and a citation

     A number with no citation does not ship. `provenance()` walks
     forSite() and returns any number that is not inside a record
     carrying a `cls` — an orphan. There must be none, anywhere.
     ============================================================ */

  t.suite("juris · every value carries cls and cite");
  (function () {
    var orphans = [], uncited = [], noClass = [], undated = [];

    ALL.forEach(function (j) {
      var p = FM.juris.provenance(j.id);
      p.orphans.forEach(function (o) { orphans.push(j.id + p.jurisId + o.path); });
      p.records.forEach(function (r) {
        if (!r.cite) uncited.push(j.id + " " + r.path);
        if (!r.cls) noClass.push(j.id + " " + r.path);
        if (!r.checked) undated.push(j.id + " " + r.path);
      });
    });

    t.eq(orphans.length, 0,
         "no numeric value sits outside a record carrying a provenance class" +
         (orphans.length ? " — orphans: " + orphans.slice(0, 5).join(", ") : ""));

    t.eq(uncited.length, 0,
         "every value-bearing record carries a citation" +
         (uncited.length ? " — uncited: " + uncited.slice(0, 5).join(", ") : ""));

    t.eq(noClass.length, 0, "every value-bearing record carries a provenance class");

    t.eq(undated.length, 0,
         "every value-bearing record carries the date it was checked — an adoption fact with no " +
         "check date cannot be told from a fresh one");

    /* the classes must be the vocabulary weights.js already uses */
    var vocab = { code: 1, site: 1, market: 1, derived: 1, user: 1 };
    var strange = [];
    ALL.forEach(function (j) {
      FM.juris.provenance(j.id).records.forEach(function (r) {
        if (!Object.prototype.hasOwnProperty.call(vocab, r.cls)) strange.push(j.id + " " + r.cls);
      });
    });
    t.eq(strange.length, 0,
         "the provenance vocabulary is the one weights.js and ARCHITECTURE.md already define, " +
         "not a second one");

    /* the module must not claim a confidence it does not have */
    var claimsPrimary = [];
    ALL.forEach(function (j) {
      FM.juris.provenance(j.id).records.forEach(function (r) {
        if (r.confirmed === "primary") claimsPrimary.push(j.id + " " + r.path);
      });
    });
    t.eq(claimsPrimary.length, 0,
         "nothing claims `confirmed: \"primary\"` — no primary document was retrievable from the " +
         "build environment and the module says so rather than implying otherwise");

    t.truthy(FM.juris.RESEARCH && FM.juris.RESEARCH.blocked &&
             FM.juris.RESEARCH.couldNotEstablish.length > 0,
             "the module publishes what it could NOT establish, not only what it could");

    t.truthy(FM.juris.SOURCES.length >= 20 &&
             FM.juris.SOURCES.every(function (s) { return s.id && s.what && s.url && s.retrieved; }),
             "every source is listed with what it is, where it is and how it was obtained");
  })();

  /* ============================================================
     4. HVHZ is two counties. Not "South Florida".
     ============================================================ */

  t.suite("juris · HVHZ is Miami-Dade and Broward and nobody else");
  (function () {
    var hv = ALL.filter(function (j) { return j.hvhz; })
                .map(function (j) { return j.id; }).sort();
    t.eq(hv.join(","), "fl-broward,fl-miamidade",
         "exactly two jurisdictions are flagged HVHZ, and they are the right two");

    t.eq(FM.juris.forSite("fl-miamidade").hvhz, true, "Miami-Dade is HVHZ");
    t.eq(FM.juris.forSite("fl-broward").hvhz, true, "Broward is HVHZ");

    /* the ones most likely to be mis-flagged by analogy */
    ["fl-palmbeach", "fl-lee", "fl-orange", "fl-hillsborough", "fl-duval"].forEach(function (id) {
      t.eq(FM.juris.forSite(id).hvhz, false,
           id + " is NOT HVHZ — near-HVHZ wind speeds do not put a county in the zone");
    });

    /* nothing outside Florida can be HVHZ at all */
    var nonFl = ALL.filter(function (j) { return j.state !== "FL" && j.hvhz; });
    t.eq(nonFl.length, 0, "no Texas or North Carolina jurisdiction is flagged HVHZ");

    t.eq(FM.juris.forState("FL").hvhz.counties.sort().join(","), "Broward,Miami-Dade",
         "the state record names the two HVHZ counties explicitly");

    /* the HVHZ jurisdictions must actually carry the Chapter 44
       submittal, and the non-HVHZ ones must carry the warning not
       to detail to it by analogy */
    var ch44 = FM.juris.checklist("fl-broward").filter(function (c) { return c.id === "fl-hvhz-ch44"; });
    t.eq(ch44.length, 1, "an HVHZ jurisdiction's checklist requires FBC-R Chapter 44 compliance");

    var notCh44 = FM.juris.checklist("fl-palmbeach")
      .filter(function (c) { return c.id === "fl-not-hvhz"; });
    t.eq(notCh44.length, 1,
         "a non-HVHZ Florida jurisdiction's checklist warns against detailing to Chapter 44 by " +
         "analogy to its neighbour");

    /* product approval must differ between the two regimes */
    var pa = function (id) {
      return FM.juris.checklist(id).filter(function (c) {
        return c.id === "fl-product-approval";
      })[0].item;
    };
    t.truthy(pa("fl-miamidade").indexOf("HVHZ endorsement") !== -1,
             "inside the HVHZ the product-approval item demands an NOA or an HVHZ-endorsed approval");
    t.truthy(pa("fl-orange").indexOf("HVHZ endorsement") === -1,
             "outside it, it does not — the two regimes are not collapsed into one sentence");
  })();

  /* ============================================================
     5. Wind is never stated as settled

     "No jurisdiction claims a wind speed without saying it must be
     site-confirmed." Three separate ways, because one of them
     could be edited out.
     ============================================================ */

  t.suite("juris · no wind speed is published as settled");
  (function () {
    var unflagged = [], unnoted = [], noAsce = [], hasExposure = [];

    ALL.forEach(function (j) {
      var w = FM.juris.forSite(j.id).wind;
      if (w.vMph === null) return;
      if (w.siteConfirmRequired !== true) unflagged.push(j.id);
      if (!w.note || w.note.indexOf("MUST BE CONFIRMED FOR THE ACTUAL SITE") === -1) unnoted.push(j.id);
      if (!w.asce) noAsce.push(j.id);
      if (w.exposure !== null) hasExposure.push(j.id);
    });

    t.eq(unflagged.length, 0,
         "every published wind speed carries siteConfirmRequired: true" +
         (unflagged.length ? " — missing on " + unflagged.join(", ") : ""));

    t.eq(unnoted.length, 0,
         "and says so in prose, so it survives into any export that prints the note" +
         (unnoted.length ? " — missing on " + unnoted.join(", ") : ""));

    t.eq(noAsce.length, 0,
         "and names the ASCE 7 edition it is read against — a wind speed is only meaningful " +
         "against its map");

    t.eq(hasExposure.length, 0,
         "no jurisdiction asserts an exposure category; ASCE 7 §26.7 exposure is a fetch " +
         "determination and cannot be a property of a city");

    /* the advisory must not be mistakable for the design value */
    var advisoryLabelled = ALL.every(function (j) {
      var w = FM.juris.forSite(j.id).wind;
      return !w.exposureCommon || (w.exposureNote && w.exposureNote.indexOf("NOT A DESIGN VALUE") === 0);
    });
    t.truthy(advisoryLabelled,
             "where a common exposure is carried as an advisory it is labelled NOT A DESIGN VALUE");

    /* seismic ground motion is not invented either */
    var seismicClean = ALL.every(function (j) {
      var s = FM.juris.forSite(j.id).seismic;
      return s.ss === null && s.s1 === null;
    });
    t.truthy(seismicClean, "no jurisdiction asserts S_s or S_1 — both are coordinate lookups");

    /* the band must contain the planning value where both exist */
    var bandOk = ALL.every(function (j) {
      var w = FM.juris.forSite(j.id).wind;
      if (w.vMph === null || !w.band) return true;
      return w.band[0] <= w.vMph && w.vMph <= w.band[1] && w.band[0] <= w.band[1];
    });
    t.truthy(bandOk, "every planning wind speed sits inside its own published band");

    /* the ASCE edition must follow the adopted code, not the calendar */
    t.eq(FM.juris.forSite("nc-mecklenburg").wind.asce, "ASCE 7-10",
         "North Carolina is on ASCE 7-10 because the 2018 NCRC is, not on the newest map available");
    t.eq(FM.juris.forSite("tx-sanantonio").wind.asce, "ASCE 7-22",
         "San Antonio is on ASCE 7-22 because it adopted the 2024 IRC");
    t.eq(FM.juris.forSite("tx-austin").wind.asce, "ASCE 7-16",
         "Austin is on ASCE 7-16 because it is still on the 2021 IRC — two Texas cities, two maps");
  })();

  /* ============================================================
     6. The wind-borne debris region is not a county flag
     ============================================================ */

  t.suite("juris · windborne debris is a contour, not a county line");
  (function () {
    var fixedByCode = ALL.filter(function (j) {
      return FM.juris.forSite(j.id).windborneDebris.determinedBy === "code";
    }).map(function (j) { return j.id; }).sort();

    t.truthy(fixedByCode.indexOf("fl-miamidade") !== -1 && fixedByCode.indexOf("fl-broward") !== -1,
             "the HVHZ counties have the answer fixed by code, because Chapter 44 fixes it");

    var everyCriterion = ALL.every(function (j) {
      var w = FM.juris.forSite(j.id).windborneDebris;
      return w.criterion && w.criterion.indexOf("NOT by county line") !== -1;
    });
    t.truthy(everyCriterion,
             "every jurisdiction publishes the defining criterion, including the words that say it " +
             "is not a county line");

    /* where the answer is left open, the condition must name it */
    var openOnes = ALL.filter(function (j) {
      return FM.juris.forSite(j.id).windborneDebris.inRegion === null;
    });
    t.truthy(openOnes.length > 0,
             "some jurisdictions leave it open rather than guessing (" + openOnes.length + " do)");

    var allNamed = openOnes.every(function (j) {
      return FM.juris.forSite(j.id).mustVerify.some(function (m) { return m.id === j.id + "/wbd"; });
    });
    t.truthy(allNamed,
             "and every one of them raises a named condition — silence is not counted as 'no'");

    /* the two big coastal counties that span the contour */
    t.eq(FM.juris.forSite("fl-hillsborough").windborneDebris.inRegion, null,
         "Hillsborough is left open — bay frontage and inland farmland are not the same answer");
    t.eq(FM.juris.forSite("nc-newhanover").windborneDebris.inRegion, null,
         "New Hanover is left open — the county runs from barrier island to inland");
  })();

  /* ============================================================
     7. The pack mapping resolves, and its differences are real

     This is the load-bearing suite. packFor() tells a user how
     wrong the pack is for their site. If that report drifts from
     the live pack, it is a confident error about a confident
     error — so every difference is recomputed here from
     FM.weights.PACKS and required to match.
     ============================================================ */

  t.suite("juris · pack mapping resolves to a real pack for every jurisdiction");
  (function () {
    var packIds = FM.weights.PACKS.map(function (p) { return p.id; });

    var unresolved = ALL.filter(function (j) { return !FM.juris.packFor(j.id).resolved; });
    t.eq(unresolved.length, 0,
         "packFor() resolves for every jurisdiction" +
         (unresolved.length ? " — failed on " + unresolved.map(function (j) { return j.id; }).join(", ") : ""));

    var bogus = ALL.filter(function (j) {
      return packIds.indexOf(FM.juris.packFor(j.id).packId) === -1;
    });
    t.eq(bogus.length, 0,
         "and every mapped pack id exists in FM.weights.PACKS — no dangling reference");

    /* the mapping must also be declared on the lightweight listing,
       so a caller does not have to build a full site record to route */
    var listedMatch = ALL.every(function (j) {
      return j.packId === FM.juris.packFor(j.id).packId;
    });
    t.truthy(listedMatch, "jurisdictions() and packFor() agree on the pack id");

    /* every pack must have a reason, not just an id */
    var reasoned = ALL.every(function (j) {
      var pf = FM.juris.packFor(j.id);
      return pf.basis && pf.basis.length > 10 && pf.verdict;
    });
    t.truthy(reasoned, "every mapping states why that pack and what its verdict is");

    /* a missing weights layer must be reported, not defaulted */
    var noWeights = FM.juris.packFor("tx-dallas", []);
    t.eq(noWeights.resolved, false,
         "an empty pack set resolves to false with a reason rather than silently picking something");
    t.truthy(noWeights.why && noWeights.why.length > 20,
             "and says by name what went wrong");
  })();

  t.suite("juris · every reported pack difference is a real difference");
  (function () {
    var fake = [], missed = [], wrongDelta = [];

    ALL.forEach(function (j) {
      var pf = FM.juris.packFor(j.id);
      var pack = packById(pf.packId);
      var site = FM.juris.forSite(j.id);

      pf.differences.forEach(function (d) {
        /* a "difference" whose two sides are equal is noise that
           trains a reader to ignore the list */
        if (JSON.stringify(d.jurisValue) === JSON.stringify(d.packValue)) {
          fake.push(j.id + "/" + d.field);
        }

        /* and where both sides are numbers, the delta must be the
           arithmetic, not a remembered number */
        if (typeof d.jurisValue === "number" && typeof d.packValue === "number") {
          if (d.delta !== d.jurisValue - d.packValue) wrongDelta.push(j.id + "/" + d.field);
        }
      });

      /* the reverse direction: a real difference against the LIVE
         pack that packFor() failed to report */
      if (typeof site.wind.vMph === "number" &&
          site.wind.vMph !== pack.climate.windMph.v &&
          !pf.differences.some(function (d) { return d.field === "wind.vMph"; })) {
        missed.push(j.id + "/wind.vMph");
      }
      if (typeof site.snow.pgPsf === "number" &&
          site.snow.pgPsf !== pack.climate.groundSnow.v &&
          !pf.differences.some(function (d) { return d.field === "snow.pgPsf"; })) {
        missed.push(j.id + "/snow.pgPsf");
      }
      if (site.governs !== pack.governs &&
          !pf.differences.some(function (d) { return d.field === "governs"; })) {
        missed.push(j.id + "/governs");
      }
      if (site.seismic.sdc !== null && site.seismic.sdc !== pack.climate.sdc.v &&
          !pf.differences.some(function (d) { return d.field === "seismic.sdc"; })) {
        missed.push(j.id + "/seismic.sdc");
      }
    });

    t.eq(fake.length, 0,
         "no reported difference has equal values on both sides" +
         (fake.length ? " — " + fake.slice(0, 5).join(", ") : ""));

    t.eq(missed.length, 0,
         "and no real difference against the live pack goes unreported" +
         (missed.length ? " — missed " + missed.slice(0, 8).join(", ") : ""));

    t.eq(wrongDelta.length, 0,
         "every numeric delta is the arithmetic of the two sides, recomputed rather than stored" +
         (wrongDelta.length ? " — " + wrongDelta.slice(0, 5).join(", ") : ""));

    /* the agreements must be real too, or the badge lies in the
       other direction — the same defect O.1/D1 found in compare() */
    var badAgree = [];
    ALL.forEach(function (j) {
      var pf = FM.juris.packFor(j.id);
      var pack = packById(pf.packId);
      var site = FM.juris.forSite(j.id);
      pf.agreements.forEach(function (a) {
        var pv = a.field === "wind.vMph" ? pack.climate.windMph.v
               : a.field === "snow.pgPsf" ? pack.climate.groundSnow.v
               : a.field === "seismic.sdc" ? pack.climate.sdc.v
               : a.field === "governs" ? pack.governs : undefined;
        var jv = a.field === "wind.vMph" ? site.wind.vMph
               : a.field === "snow.pgPsf" ? site.snow.pgPsf
               : a.field === "seismic.sdc" ? site.seismic.sdc
               : a.field === "governs" ? site.governs : undefined;
        if (pv !== jv) badAgree.push(j.id + "/" + a.field);
      });
    });
    t.eq(badAgree.length, 0,
         "and every claimed agreement is an actual agreement against the live pack" +
         (badAgree.length ? " — " + badAgree.slice(0, 5).join(", ") : ""));
  })();

  /* ============================================================
     8. The differences that matter are actually surfaced

     Not a fixture on the numbers — a fixture on the SHAPE of the
     finding, recomputed from the live pack. If someone adds a
     coastal NC pack, these stop firing, which is the correct
     outcome: the gap they describe would be closed.
     ============================================================ */

  t.suite("juris · the packs are approximations and the module says how far off");
  (function () {
    /* coastal North Carolina has no pack of its own */
    ["nc-newhanover", "nc-brunswick"].forEach(function (id) {
      var pf = FM.juris.packFor(id);
      var pack = packById(pf.packId);
      var site = FM.juris.forSite(id);

      var g = pf.differences.filter(function (d) { return d.field === "governs"; })[0];
      t.truthy(g && site.governs === "wind" && pack.governs === "gravity",
               id + " is wind-governed and its nearest pack is gravity-governed — reported, not hidden");

      var w = pf.differences.filter(function (d) { return d.field === "wind.vMph"; })[0];
      t.truthy(w && w.jurisValue > w.packValue,
               id + " carries a higher wind speed than its pack (" + (w ? w.jurisValue : "?") +
               " vs " + (w ? w.packValue : "?") + " mph) and the pack understates it");
    });

    /* south-west and south-east Florida against the central pack */
    ["fl-lee", "fl-palmbeach"].forEach(function (id) {
      var pf = FM.juris.packFor(id);
      var w = pf.differences.filter(function (d) { return d.field === "wind.vMph"; })[0];
      t.truthy(w && w.jurisValue > w.packValue,
               id + " is well above its pack's wind speed (" + (w ? w.jurisValue : "?") + " vs " +
               (w ? w.packValue : "?") + " mph) and is not silently absorbed into fl-central");
      t.truthy(w && w.effect && w.effect.indexOf("LIGHT on wind pressure") !== -1,
               id + " states the consequence in wind PRESSURE, not just speed — the error goes as V²");
    });

    /* the coastal Texas windstorm regime the packs cannot express */
    var cat = ALL.filter(function (j) { return j.catastropheArea; });
    t.truthy(cat.length >= 3,
             "the TDI designated catastrophe area covers more than one jurisdiction here (" +
             cat.length + ")");

    var allReport = cat.every(function (j) {
      return FM.juris.packFor(j.id).differences.some(function (d) {
        return d.field === "catastropheArea";
      });
    });
    t.truthy(allReport,
             "and every one of them reports that its pack has no field for the windstorm regime");

    /* no pack states an edition, so the module must say so rather
       than letting a reader assume the pack agrees with it */
    var everyEdition = ALL.every(function (j) {
      return FM.juris.packFor(j.id).differences.some(function (d) {
        return d.field === "code.edition" && d.packValue === null;
      });
    });
    t.truthy(everyEdition,
             "every mapping records that the pack states no code edition at all — it cannot agree " +
             "or disagree with one");

    /* packAudit must cover the whole surface in one call */
    t.eq(FM.juris.packAudit().length, ALL.length,
         "packAudit() reports the whole approximation surface in one call");
  })();

  /* ============================================================
     9. The three states are modelled as three different machines
     ============================================================ */

  t.suite("juris · the state regimes are modelled, not flattened");
  (function () {
    var tx = FM.juris.forState("TX");
    t.eq(tx.statewide, false, "Texas is not a statewide-enforcement state");
    t.truthy(tx.windstormRegime && tx.windstormRegime.counties.length === 14,
             "the TDI designated catastrophe area lists 14 first-tier counties");
    t.truthy(tx.windstormRegime.partialCounties.length >= 1,
             "and carries Harris County as a PARTIAL county — the boundary is a highway, not a " +
             "county line");
    t.truthy(tx.windstormRegime.counties.indexOf("Galveston") !== -1 &&
             tx.windstormRegime.counties.indexOf("Nueces") !== -1,
             "Galveston and Nueces are in it, matching the coastal jurisdictions carried here");
    t.truthy(tx.windstormRegime.trap && tx.windstormRegime.trap.indexOf("NOT THE SAME CODE") !== -1,
             "and the module states outright that the windstorm code and the city code are two codes");
    t.eq(tx.localAmendments.permitted, true, "Texas municipalities may amend");

    var fl = FM.juris.forState("FL");
    t.eq(fl.statewide, true, "Florida is a statewide code");
    t.eq(fl.localAmendments.direction, "more stringent only",
         "and its local technical amendments may only be more stringent");
    t.truthy(fl.statute.some(function (c) { return c.status.indexOf("PENDING") !== -1; }),
             "the pending 9th Edition is carried as PENDING rather than as the current code");
    t.truthy(fl.productApproval && fl.productApproval.note.indexOf("SUBMITTAL requirement") !== -1,
             "product approval is stated as a submittal requirement, not a design load");

    var nc = FM.juris.forState("NC");
    t.eq(nc.statewide, true, "North Carolina is a statewide code");
    t.eq(nc.localAmendments.permitted, false,
         "with no local technical amendments — the one state here whose code text does not vary");

    /* the delayed 2024 NCRC must be carried as adopted-but-not-in-force */
    var inForce = nc.statute.filter(function (c) { return c.status === "in force"; });
    var pending = nc.statute.filter(function (c) { return c.status.indexOf("NOT IN FORCE") !== -1; });
    t.eq(inForce.length, 1, "exactly one NC edition is marked in force");
    t.eq(inForce[0].edition, "2018 NCRC",
         "and it is the 2018 NCRC — the 2024 edition has been delayed three times");
    t.eq(inForce[0].basis, "2015 IRC", "whose model basis is the 2015 IRC, not the 2021");
    t.eq(inForce[0].asce, "ASCE 7-10", "and whose referenced wind standard is ASCE 7-10");
    t.eq(pending.length, 1, "and the 2024 NCRC is carried explicitly as adopted but not in force");

    /* every NC jurisdiction must be on that same edition — the
       whole point of a statewide code */
    var ncSame = FM.juris.jurisdictions("NC").every(function (j) {
      var c = FM.juris.forSite(j.id).codes[0];
      return c.edition === "2018 NCRC" && c.asce === "ASCE 7-10";
    });
    t.truthy(ncSame, "and every North Carolina jurisdiction carries it — one code, statewide");

    /* Texas, by contrast, must NOT be uniform */
    var txEditions = {};
    FM.juris.jurisdictions("TX").forEach(function (j) {
      txEditions[FM.juris.forSite(j.id).codes[0].edition] = 1;
    });
    t.truthy(Object.keys(txEditions).length >= 2,
             "Texas carries more than one adopted edition across its cities (" +
             Object.keys(txEditions).sort().join(", ") + ") — a Texas pack keyed to the state is " +
             "keyed to the wrong thing");

    /* the unincorporated county record must refuse rather than invent */
    var uninc = FM.juris.forSite("tx-galveston-county-uninc");
    t.eq(uninc.codes[0].edition, "NOT ESTABLISHED",
         "unincorporated Galveston County states no code edition rather than inventing one");
    t.truthy(uninc.mustVerify.some(function (m) { return m.severity === "blocking"; }),
             "and raises a blocking condition about which regime applies at all");
  })();

  /* ============================================================
     10. Submittal checklists carry what this tool does not do
     ============================================================ */

  t.suite("juris · the checklist names what this package is not");
  (function () {
    var everySeal = ALL.every(function (j) {
      return FM.juris.checklist(j.id).some(function (c) {
        return c.id === "seal" && c.item.indexOf("does not seal") !== -1;
      });
    });
    t.truthy(everySeal,
             "every checklist states that the software does not seal — ARCHITECTURE non-negotiable 1");

    var everyConn = ALL.every(function (j) {
      return FM.juris.checklist(j.id).some(function (c) { return c.id === "connections"; });
    });
    t.truthy(everyConn,
             "and that uplift, the load path and every connection are designed by others " +
             "(calc-spec §8.11, §8.17)");

    var noneSatisfied = ALL.every(function (j) {
      return FM.juris.checklist(j.id).every(function (c) { return c.satisfiedByThisTool === false; });
    });
    t.truthy(noneSatisfied,
             "no checklist item claims to be satisfied by this tool — the package satisfies none of " +
             "them by itself");

    /* the coastal Texas double-code trap must reach the checklist */
    var cc = FM.juris.checklist("tx-corpuschristi");
    t.truthy(cc.some(function (c) { return c.id === "tx-wpi1" && c.stage === "design"; }),
             "a designated catastrophe area requires the WPI-1 BEFORE construction, at design stage");
    t.truthy(cc.some(function (c) { return c.id === "tx-wpi8" && c.stage === "closeout"; }),
             "and the WPI-8 certificate at closeout");
    t.truthy(cc.some(function (c) {
      return c.id === "tx-tdi-code" && c.item.indexOf("NEWER EDITION THAN THE CITY ENFORCES") !== -1;
    }), "and states that TDI's code may be newer than the city's — the trap that is found after framing");

    /* Houston's amendment is the module's own discipline in an ordinance */
    var hou = FM.juris.checklist("tx-houston");
    t.truthy(hou.some(function (c) {
      return c.id === "tx-hou-windprint" && c.item.indexOf("ATTACHED TO THE PLANS") !== -1;
    }), "Houston's checklist requires the ASCE 7 Hazard Tool printout attached to the plans");

    /* North Carolina's ASCE 7-10 trap */
    var nc = FM.juris.checklist("nc-wake");
    t.truthy(nc.some(function (c) {
      return c.id === "nc-asce710" && c.item.indexOf("ASCE 7-10") !== -1;
    }), "a North Carolina checklist requires the engineered design to be on ASCE 7-10");
  })();
};

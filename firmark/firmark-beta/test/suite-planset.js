/* ============================================================
   suite-planset.js — the PE review package.

   Wire into test/run-tests.js with:

       require("./suite-planset.js")({ suite: suite, eq: eq, near: near,
                                       truthy: truthy }, FM);

   after loading planset.js into the harness:

       harness.load([... "scope.js", "engine.js", "weights.js", "solver.js",
                     "auth.js", "pipeline.js", "planset.js"])

   WHAT THIS SUITE IS FOR
   ----------------------
   Two of the assertions below are the product's licence to exist, and
   they are written as blanket sweeps over the whole document rather
   than as spot checks, because a spot check only proves the sentence
   someone remembered to look at:

     · nothing anywhere in the package asserts that this software
       stamped, sealed or approved a design, in ANY of the 30 plan ×
       pack combinations; and the "to be sealed by ____, PE" seal
       placeholder IS present in every one of them;

     · S5.0 Open items is never empty, in any of the 30, because a
       package reporting zero open items is claiming a completeness
       this system cannot have.

   The rest prove that a missing upstream module produces a sheet that
   SAYS SO by name rather than a sheet that looks finished.
   ============================================================ */

"use strict";

module.exports = function (t, FM) {
  var suite = t.suite, eq = t.eq, truthy = t.truthy;

  /* ---------------------------------------------------------------
     Fixtures. cad.js / takeoff.js / bom.js / jurisdiction.js are being
     written in parallel and may not exist in this build at all, so the
     "full ctx" case is built from the shapes ARCHITECTURE.md declares
     rather than from the modules. That is the point: planset.js must
     consume the CONTRACT, not an implementation.
     --------------------------------------------------------------- */

  function fixtureModel() {
    return { version: 1, name: "Test model", levels: [{
      id: "L1", label: "First floor", topPlateFt: 9.0,
      walls: [
        { id: "W1", x1: 0, y1: 0, x2: 46, y2: 0, exterior: true, bearing: true, heightFt: 9, thicknessIn: 5.5 },
        { id: "W2", x1: 46, y1: 0, x2: 46, y2: 32, exterior: true, bearing: false, heightFt: 9, thicknessIn: 5.5 },
        { id: "W3", x1: 46, y1: 32, x2: 0, y2: 32, exterior: true, bearing: true, heightFt: 9, thicknessIn: 5.5 },
        { id: "W4", x1: 0, y1: 32, x2: 0, y2: 0, exterior: true, bearing: false, heightFt: 9 }
      ],
      openings: [
        { id: "O1", wallId: "W1", offsetFt: 4, widthFt: 4, headHeightFt: 6.67, kind: "window" },
        { id: "O2", wallId: "W1", offsetFt: 20, widthFt: 9, headHeightFt: 7.0, kind: "garage" },
        { id: "O9", wallId: "NO-SUCH-WALL", offsetFt: 1, widthFt: 2, kind: "door" }
      ],
      framing: [
        { id: "F1", polygon: [[0, 0], [46, 0], [46, 32], [0, 32]], kind: "roof",
          directionDeg: 90, spacingIn: 24, bearsOn: ["W1", "W3"] }
      ]
    }] };
  }

  function fixtureTakeoff(markIds) {
    return {
      marks: (markIds || []).map(function (id) { return { id: id }; }),
      derivations: [
        { markId: "HDR-W", field: "trib", value: 16.0, from: "opening O1",
          how: "half the F1 clear span" },
        { markId: "HDR-GAR", field: "trib", value: 16.0, from: "opening O2",
          how: "half the F1 clear span" }
      ],
      unresolved: [
        { what: "HDR-GBL tributary", why: "the gable end bears no framing region",
          need: "a stated moment-equivalent uniform" }
      ],
      warnings: [{ what: "W4 declares no thickness", why: "the model omits thicknessIn",
                   need: "complete the wall record" }]
    };
  }

  function fixtureBom() {
    return {
      lines: [{ sku: "SP-4X6-8", size: "4x6", species: "Southern Pine", grade: "No.2",
                treatment: "ACQ", piecesPerHouse: 1, lengthFt: 8, stockLengthFt: 8,
                piecesPerStock: 1, bf: 16, lf: 8, unitUSD: 11.2, extUSD: 11.2,
                marks: ["BM-ENT"], cls: "derived",
                basis: "one beam per entry, cut from an 8 ft stock length" }],
      totals: { bf: 16, pieces: 1, usd: 11.2, byCategory: { porch: 11.2 } },
      perLot: { usd: 11.2 }, perCommunity: { usd: 2464 },
      excluded: [
        { what: "every connector, strap and anchor",
          why: "no connection is designed anywhere in this system" },
        { what: "sheathing and fasteners", why: "not sized by the calc stack" }
      ],
      waste: { policy: "cut-list, no blanket percentage", appliedPct: 0,
               basis: "stock lengths chosen to the cut" }
    };
  }

  function fixtureJuris() {
    return {
      id: "fl-miami-dade",
      codes: [{ name: "Florida Building Code, Residential", edition: "8th Edition (2023)",
                basis: "statewide adoption", adopted: "2023-12-31",
                cite: "FBC-R Chapter 44 (HVHZ)", cls: "code" }],
      wind: { vMph: 175, exposure: "C", cls: "site", cite: "FBC-R Figure R301.2(2)",
              note: "Miami-Dade; confirm per site" },
      snow: { pgPsf: 0, cls: "code", cite: "no snow load in this jurisdiction" },
      seismic: { sdc: "A", ss: 0.05, s1: 0.02, cls: "site",
                 cite: "ASCE 7 Hazard Tool, checked 2026-08-01" },
      mustVerify: [
        { what: "whether FBC-R Chapter 44 mandates engineered design",
          why: "unresolved", against: "the authority having jurisdiction" },
        { what: "product approval / NOA for every assembly",
          why: "a submittal requirement", against: "Miami-Dade product control" }
      ]
    };
  }

  function solve(planId, packId) {
    var pl = FM.weights.planById(planId), pk = FM.weights.packById(packId);
    return FM.solver.solvePlan(pl, pk);
  }

  function fullCtx(planId, packId) {
    var res = solve(planId, packId);
    var ids = res.marks.map(function (m) { return m.mark.id; });
    return { model: fixtureModel(), takeoff: fixtureTakeoff(ids), planResult: res,
             bom: fixtureBom(), juris: fixtureJuris(), pipeline: FM.pipeline || null,
             at: "2026-08-13 00:00 UTC" };
  }

  function every(fn) {
    FM.weights.PLANS.forEach(function (pl) {
      FM.weights.PACKS.forEach(function (pk) {
        fn(pl, pk);
      });
    });
  }

  /* ============================================================
     1. It builds — with everything, and with nothing
     ============================================================ */

  suite("planset · the surface, and what it does with a full ctx");
  (function () {
    truthy(FM.planset && typeof FM.planset.build === "function", "FM.planset.build exists");
    truthy(typeof FM.planset.render === "function", "FM.planset.render exists");
    truthy(typeof FM.planset.text === "function", "FM.planset.text exists");

    var pkg = FM.planset.build(fullCtx("starter-1210", "fl-hvhz"));
    eq(pkg.sheets.length, 7, "a package is seven sheets");
    eq(pkg.sheets.map(function (s) { return s.no; }).join(" "),
       "S0.0 S0.1 S1.0 S2.0 S3.0 S4.0 S5.0", "and they are the sheets the contract names");
    var shaped = pkg.sheets.filter(function (s) {
      return s.no && s.title && s.kind && typeof s.render === "function";
    });
    eq(shaped.length, 7, "every sheet carries {no, title, kind, render(host)}");
    eq(pkg.missing.length, 0, "a full ctx reports nothing missing");

    var txt = pkg.text();
    truthy(txt.length > 20000, "the package text is a document, not a stub");
    eq(FM.planset.text(pkg), txt, "FM.planset.text(pkg) is pkg.text()");

    /* the full-ctx content actually reaches the sheets */
    var s10 = pkg.sheetByNo("S1.0").text();
    truthy(s10.indexOf("W1") !== -1 && s10.indexOf("F1") !== -1,
           "S1.0 carries the model's walls and framing regions");
    truthy(/PLACED — 2/.test(s10),
           "S1.0 places exactly the two marks the takeoff located, and no others");
    truthy(/NOT PLACED/.test(s10),
           "and says which marks it could NOT place rather than guessing a location");
    truthy(s10.indexOf("NO SUCH WALL") !== -1,
           "an opening whose host wall does not exist is named on the sheet");

    var s40 = pkg.sheetByNo("S4.0").text();
    truthy(s40.indexOf("SP-4X6-8") !== -1, "S4.0 lists the BOM lines");
    truthy(s40.indexOf("every connector, strap and anchor") !== -1,
           "and prints the exclusion list — the honest half of a bill of materials");

    var s00 = pkg.sheetByNo("S0.0").text();
    truthy(s00.indexOf("8th Edition (2023)") !== -1,
           "S0.0 takes the adopted code edition from the jurisdiction record");
    truthy(s00.indexOf("175 mph") !== -1, "and the design wind speed");
    truthy(s00.indexOf("ASCE 7 Hazard Tool, checked 2026-08-01") !== -1,
           "and the seismic citation, verbatim");
  })();

  suite("planset · every optional input absent — each sheet names what it did not get");
  (function () {
    var res = solve("starter-1210", "fl-hvhz");
    var pkg = FM.planset.build({ planResult: res, at: "2026-08-13 00:00 UTC" });
    eq(pkg.sheets.length, 7, "the package still builds with only a solver result");
    eq(pkg.missing.length, 5,
       "and reports five absent inputs: model, takeoff, bom, juris, pipeline");

    var byModule = pkg.missing.map(function (m) { return m.module; }).sort().join(",");
    eq(byModule, "bom.js,cad.js,jurisdiction.js,pipeline.js,takeoff.js",
       "named by the module that owes them, not by a generic error");

    var s10 = pkg.sheetByNo("S1.0").text();
    truthy(/cad\.js supplied no model/.test(s10), "S1.0 says cad.js supplied no model");
    truthy(/NO FRAMING PLAN/.test(s10), "and does not pretend to be a framing plan");
    truthy(s10.indexOf("north") === -1 || /NOT A DRAWING/.test(s10),
           "and does not draw a north arrow over geometry it does not have");

    var s40 = pkg.sheetByNo("S4.0").text();
    truthy(/bom\.js supplied no bill of materials/.test(s40), "S4.0 says bom.js supplied nothing");
    truthy(/NOT A BILL OF MATERIALS/.test(s40),
           "and labels the member counts it does print as NOT a bill of materials");

    var s00 = pkg.sheetByNo("S0.0").text();
    truthy(/NO JURISDICTION RECORD WAS SUPPLIED/.test(s00),
           "S0.0 says no jurisdiction record was supplied");
    truthy(/PLANNING DEFAULTS, not site values/.test(s00),
           "and demotes the criteria table to planning defaults rather than presenting it as site data");

    var s50 = pkg.sheetByNo("S5.0").text();
    truthy(/takeoff\.js supplied nothing/.test(s50), "S5.0 carries takeoff.js's absence as an open item");
    truthy(/INPUT NOT AVAILABLE — 5/.test(s50), "all five absences are open items, counted");

    /* no solver result at all — the package must still assemble */
    var bare = FM.planset.build({});
    eq(bare.sheets.length, 7, "an entirely empty ctx still produces seven sheets");
    truthy(bare.openItems.length > 0, "and a non-empty open items list");
    truthy(/NOT SUPPLIED/.test(bare.sheetByNo("S0.0").text()),
           "with a cover that says the plan was not supplied");
    truthy(/NOT GENERATED/.test(bare.sheetByNo("S2.0").text()),
           "and schedules that say they were not generated");
    truthy(/NOT GENERATED|NOT AVAILABLE/.test(bare.sheetByNo("S3.0").text()),
           "and calculations that say the same");

    /* a model with no cad.js, and a takeoff with no derivations */
    var noCad = FM.planset.build({ planResult: res, model: fixtureModel(),
                                   takeoff: { unresolved: [], marks: [] } });
    var g = noCad.sheetByNo("S1.0").text();
    truthy(/cad\.js IS NOT LOADED/.test(g) || FM.cad,
           "a model supplied without cad.js says the model was not validated");
    truthy(/No derivation trail was supplied/.test(noCad.sheetByNo("S5.0").text()),
           "a takeoff with no derivations is an open item, not a silent pass");
    eq(noCad.geometry.placed.length, 0,
       "and with no derivations NO mark is placed on the plan — placement is read, never guessed");
  })();

  /* ============================================================
     2. calc-spec §8 — verbatim, unabridged, from the one renderer
     ============================================================ */

  suite("planset · the 24 scope boundaries reach the package, from FM.scope.render");
  (function () {
    var pkg = FM.planset.build(fullCtx("starter-1210", "fl-hvhz"));
    var txt = pkg.text();
    var flat = txt.replace(/\s+/g, " ");

    var absent = FM.scope.items.filter(function (it) {
      return flat.indexOf(it.text.slice(0, 60).replace(/\s+/g, " ")) === -1;
    });
    eq(absent.length, 0, "all 24 calc-spec §8 boundaries appear in text()" +
       (absent.length ? " — missing " + absent.map(function (x) { return x.n; }).join(", ") : ""));
    eq(FM.scope.items.length, 24, "and there are 24 of them");

    /* item 17 is the one that says the bearing check this package publishes is
       a bearing-stress check and not a connection design */
    truthy(flat.indexOf("Bearing is checked as f_c") !== -1,
           "item 17 — the bearing/connection boundary — is in the package, verbatim");
    truthy(flat.indexOf(FM.scope.preamble.slice(0, 60).replace(/\s+/g, " ")) !== -1,
           "and the §8 preamble that says verbatim and unabridged");
    truthy(/ENGINE LIMITS/.test(txt) && /does not replace them/.test(txt),
           "engine.LIMITS prints alongside §8, labelled as not a substitute for it");

    /* it must come from the shared renderer, not a second copy of the list */
    var fs = require("fs"), path = require("path");
    var src = fs.readFileSync(path.join(__dirname, "..", "planset.js"), "utf8")
                .replace(/\/\*[\s\S]*?\*\//g, "");
    truthy(/FM\.scope\.render\(/.test(src), "planset.js calls FM.scope.render");
    truthy(!/FM\.scope\.items\.(forEach|map|filter)\(/.test(src),
           "and does NOT walk FM.scope.items to print a copy of its own");

    /* the boundaries land on S0.1, where the general notes are */
    truthy(pkg.sheetByNo("S0.1").text().indexOf("Bearing is checked as f_c") !== -1,
           "the boundaries are on S0.1 General notes, where a reviewer looks for them");
  })();

  /* ============================================================
     3. THE ONE RULE — swept over every plan × pack
     ============================================================ */

  suite("planset · no output anywhere claims this software sealed, stamped or approved anything");
  (function () {
    /* Two kinds of check.

       ABSOLUTE bans are literal strings that may not appear in the document
       at all, under any reading. "stamped" is the load-bearing one: the whole
       vocabulary of this product is "prepared for PE review", and the word
       must not be in a plan set even in a sentence denying it, because a
       reviewer skimming a cover sheet reads words, not sentences. (This is
       why the package does not reproduce weights.js's elevation labels such
       as "Elevation A · as stamped", and does not embed export.js's schedule
       verbatim — see the notes on planset.js.)

       CLAIM patterns are phrase shapes that would ASSERT a seal. This
       document exists to deny exactly those claims, so a match inside a
       negated sentence is the product working rather than failing; the
       enclosing sentence is tested for a negator before a match counts. The
       window is the sentence, not a character count, so the exemption cannot
       quietly stretch across a full stop. */
    var ABSOLUTE = [
      { re: /stamp/i, why: "\"stamp\" in any form — write \"prepared for PE review\"" },
      { re: /sealed by Firmark/i, why: "\"sealed by Firmark\"" },
      { re: /approved by/i, why: "\"approved by\" — this package confers no approval" },
      { re: /\bPE[- ](stamped|sealed|approved)\b/i, why: "\"PE-stamped\" / \"PE-sealed\"" },
      { re: /\bstamp(ed|s)? (set|plan|design|package)\b/i, why: "a stamped-artefact noun phrase" }
    ];
    var CLAIMS = [
      /* the subject list is the MACHINE only. "A licensed PE reviews this
         package and seals it under their own licence" is the sentence this
         product is for, and a pattern that flags it is measuring the wrong
         thing — what is banned is the software as the actor. */
      { re: /(this|the) (software|system|tool|app|engine)[^.]{0,40}\b(seals|stamps|approves|certifies)\b/i,
        why: "an active claim that the software seals, stamps, approves or certifies" },
      { re: /\bfirmark\b[^.]{0,40}\b(seals|stamps|approves|certifies|sealed|stamped|approved)\b/i,
        why: "a claim with Firmark itself as the actor" },
      { re: /\b(sealed|stamped|approved|certified) (set|design|package|drawings?)\b/i,
        why: "a noun phrase asserting the output is a sealed or approved artefact" },
      { re: /\b(is|are|was|were|has been|have been) (sealed|approved|certified)\b/i,
        why: "a claim that something here has been sealed, approved or certified" },
      { re: /ready to (issue|build|construct)\b/i, why: "a claim of construction readiness" },
      { re: /(engineer|engineering) (is|has been) (complete|certified)\b/i,
        why: "a claim that the engineering is complete or certified" },
      { re: /\bfor construction\b/i, why: "a released-for-construction claim" }
    ];
    var NEGATOR = /\b(no|not|never|nothing|none|cannot|can not|neither|nor|without|empty|refuse[sd]?|absent|unless|until|to be)\b/i;

    function sentenceAround(txt, idx) {
      var starts = [txt.lastIndexOf(".", idx), txt.lastIndexOf("\n\n", idx),
                    txt.lastIndexOf("**", idx), txt.lastIndexOf(":", idx)];
      var start = Math.max.apply(null, starts);
      var end = txt.indexOf(".", idx + 1);
      if (end === -1) end = txt.length;
      return txt.slice(start + 1, end + 1).replace(/\s+/g, " ");
    }
    function scan(txt, list, negatable, where, out) {
      list.forEach(function (b) {
        var re = new RegExp(b.re.source, "gi"), m;
        while ((m = re.exec(txt)) !== null) {
          if (negatable && NEGATOR.test(sentenceAround(txt, m.index))) continue;
          out.push(where + ": " + b.why + " — found \"" + m[0] + "\" in: " +
                   sentenceAround(txt, m.index).slice(0, 110));
          break;
        }
      });
    }

    var hits = [], noPlaceholder = [], n = 0;
    every(function (pl, pk) {
      n++;
      var pkg = FM.planset.build(fullCtx(pl.id, pk.id));
      var txt = pkg.text();
      scan(txt, ABSOLUTE, false, pl.id + "/" + pk.id, hits);
      scan(txt, CLAIMS, true, pl.id + "/" + pk.id, hits);
      if (!/to be sealed by/i.test(txt)) noPlaceholder.push(pl.id + "/" + pk.id);
    });

    /* the negation exemption must not be a hole: a sentence that DOES claim a
       seal is caught even though the surrounding document denies it */
    var planted = [];
    scan("The seal block is empty.\nThis software seals the drawings for you.\n" +
         "Nothing here is sealed.", CLAIMS, true, "planted", planted);
    truthy(planted.length > 0,
           "the sweep catches a planted affirmative claim inside an otherwise honest document");

    eq(n, 30, "the sweep covered all 30 plan × pack combinations");
    eq(hits.length, 0, "no package asserts the software sealed, stamped or approved anything" +
       (hits.length ? " — " + hits.slice(0, 4).join(" | ") : ""));
    eq(noPlaceholder.length, 0, "and every package carries the \"to be sealed by ____, PE\" placeholder" +
       (noPlaceholder.length ? " — missing in " + noPlaceholder.join(", ") : ""));

    /* the placeholder is a blank to be completed, not a name */
    var one = FM.planset.build(fullCtx("starter-1210", "fl-hvhz")).text();
    truthy(/to be sealed by _+/i.test(one), "the seal line is an underscored blank");
    truthy(/licence no\. _+/i.test(one), "with a blank licence number");
    truthy(/State of _+/i.test(one), "and a blank state");
    truthy(/SEAL BLOCK — INTENTIONALLY EMPTY/.test(one),
           "and the seal block says, in its own heading, that it is empty on purpose");

    /* the statement is on the cover, in the general notes, and on every sheet */
    var pkg = FM.planset.build(fullCtx("starter-1210", "fl-hvhz"));
    truthy(/PREPARED FOR PE REVIEW/.test(pkg.sheetByNo("S0.0").text()),
           "the cover carries the statement");
    truthy(/not sealed engineering/i.test(pkg.sheetByNo("S0.1").text()),
           "the general notes carry it");
    var missingFooter = pkg.sheets.filter(function (s) {
      return !/PREPARED FOR PE REVIEW — NOT SEALED ENGINEERING/.test(s.text());
    });
    eq(missingFooter.length, 0, "and every one of the seven sheets carries it in its footer" +
       (missingFooter.length ? " — " + missingFooter.map(function (s) { return s.no; }).join(", ") : ""));

    /* an exported filename may not imply a sealed set either */
    truthy(!/stamp|sealed-set/i.test("firmark-planset-" +
           pkg.head.packageId.replace(/[^\w.-]+/g, "-") + "-for-PE-review.txt"),
           "the export filename says for-PE-review and never implies a seal");
  })();

  /* ============================================================
     4. S5.0 is never empty
     ============================================================ */

  suite("planset · S5.0 Open items is never empty, in any combination");
  (function () {
    var empties = [], thin = [], n = 0;
    every(function (pl, pk) {
      n++;
      var pkg = FM.planset.build(fullCtx(pl.id, pk.id));
      if (!pkg.openItems.length) empties.push(pl.id + "/" + pk.id);
      var s50 = pkg.sheetByNo("S5.0").text();
      if (!/STANDING — 5/.test(s50)) thin.push(pl.id + "/" + pk.id);
    });
    eq(n, 30, "checked all 30 combinations");
    eq(empties.length, 0, "S5.0 has at least one open item in every combination" +
       (empties.length ? " — empty in " + empties.join(", ") : ""));
    eq(thin.length, 0, "and the five standing items print on every one of them" +
       (thin.length ? " — missing in " + thin.join(", ") : ""));

    /* the standing items are the ones this system can never close */
    var s50 = FM.planset.build(fullCtx("starter-1210", "fl-hvhz")).sheetByNo("S5.0").text();
    truthy(/The seal is not applied/.test(s50), "standing: the seal is not applied");
    truthy(/Site loads are not confirmed/.test(s50), "standing: site loads are not confirmed");
    truthy(/No connection of any kind is designed/.test(s50), "standing: no connection is designed");
    truthy(/Lateral design is absent/.test(s50), "standing: no lateral design");
    truthy(/member check, not a design/.test(s50), "standing: this is a member check, not a design");
    truthy(/never empty/.test(s50),
           "and the sheet says out loud why it can never be empty");

    /* it collects from every upstream stage */
    truthy(/HDR-GBL tributary/.test(s50), "S5.0 collects the takeoff's unresolved items");

    /* ARCHITECTURE.md fixes the shape of `unresolved` and `excluded` but says
       only `warnings: [...]`, so the real modules use {kind, text, refs}.
       A finding somebody wrote a sentence for must not come out as
       "(unnamed)" — that loses the finding while looking like a guard. */
    var oddShapes = FM.planset.build({
      planResult: solve("starter-1210", "fl-hvhz"),
      takeoff: { derivations: [{ markId: "X" }], unresolved: [],
                 warnings: [{ kind: "no-header", refs: ["O12", "W4"],
                              text: "No header mark for opening O12: wall W4 is bearing:false." }] },
      bom: { lines: [], excluded: [{ item: "the girder", reason: "escalated, so it has no member" }] },
      juris: { mustVerify: [{ check: "the adopted edition", note: "not confirmed", source: "the AHJ" }] },
      at: "x"
    }).sheetByNo("S5.0").text();
    truthy(/no-header — O12, W4/.test(oddShapes),
           "a warning shaped {kind, text, refs} is reported by its kind and its refs");
    truthy(/wall W4 is bearing:false/.test(oddShapes),
           "and the sentence somebody wrote survives into the sheet");
    truthy(/the girder/.test(oddShapes) && /escalated, so it has no member/.test(oddShapes),
           "an exclusion shaped {item, reason} is read, not dropped as unnamed");
    truthy(/the adopted edition/.test(oddShapes) && /the AHJ/.test(oddShapes),
           "and a must-verify shaped {check, note, source} likewise");
    truthy(oddShapes.indexOf("(unnamed") === -1,
           "none of the three comes out as \"(unnamed)\"");

    /* A framing plan of one document bound to a schedule of another is the
       failure this system exists to prevent, and nothing downstream detects
       it — both sheets look finished. */
    var res2 = solve("starter-1210", "fl-hvhz");
    var mismatched = FM.planset.build({
      planResult: res2,
      takeoff: { marks: [{ id: "RF-F1" }, { id: "HDR-O1" }], derivations: [], unresolved: [] },
      at: "x"
    }).sheetByNo("S5.0").text();
    truthy(/schedule and the takeoff do not describe the same marks/.test(mismatched),
           "a schedule whose marks are not the takeoff's marks is reported as an open item");
    truthy(/0 appear in both/.test(mismatched),
           "counting how many marks the two documents actually share");

    var matched = FM.planset.build({
      planResult: res2,
      takeoff: { marks: res2.marks.map(function (m) { return { id: m.mark.id }; }),
                 derivations: [], unresolved: [] },
      at: "x"
    }).sheetByNo("S5.0").text();
    truthy(!/do not describe the same marks/.test(matched),
           "and it is NOT raised when the schedule was sized from the takeoff's own marks");
    truthy(/every connector, strap and anchor/.test(s50), "and the BOM's excluded items");
    truthy(/FBC-R Chapter 44 mandates engineered design/.test(s50),
           "and the jurisdiction's must-verify items");
    truthy(/NOT SIZED/.test(s50), "and the marks the engine would not size");

    /* an escalating combination surfaces its escalations, by category */
    var esc = null;
    every(function (pl, pk) {
      if (esc) return;
      var r = solve(pl.id, pk.id);
      if (r.rollup.escalated > 0) esc = { pl: pl.id, pk: pk.id };
    });
    truthy(esc, "at least one combination in the book escalates a mark");
    if (esc) {
      var p2 = FM.planset.build(fullCtx(esc.pl, esc.pk));
      truthy(/ESCALATED/.test(p2.sheetByNo("S5.0").text()),
             "and its escalations reach S5.0 (" + esc.pl + "/" + esc.pk + ")");
    }
  })();

  /* ============================================================
     5. Nothing in the document is a leaked internal
     ============================================================ */

  suite("planset · no undefined, NaN or [object Object] in any of the 30 packages");
  (function () {
    var bad = [], n = 0;
    /* case-sensitive on purpose: "provenance" contains "nan", and a
       case-insensitive sweep would fail on the word this package uses most */
    var PROBES = [/undefined/, /NaN/, /\[object Object\]/, /\[object Array\]/, /\bInfinity\b/];
    every(function (pl, pk) {
      n++;
      var txt = FM.planset.build(fullCtx(pl.id, pk.id)).text();
      PROBES.forEach(function (re) {
        var m = re.exec(txt);
        if (!m) return;
        var line = txt.slice(0, m.index).split("\n").length;
        bad.push(pl.id + "/" + pk.id + " line " + line + ": " + m[0]);
      });
    });
    eq(n, 30, "checked all 30 combinations");
    eq(bad.length, 0, "no package leaks an internal value into the document" +
       (bad.length ? " — " + bad.slice(0, 5).join(" | ") : ""));

    /* a ctx full of junk must be absorbed, not printed */
    var junk = FM.planset.build({
      planResult: solve("starter-1210", "fl-hvhz"),
      bom: { lines: [{ sku: undefined, size: null, piecesPerHouse: NaN, extUSD: "x",
                       marks: [undefined], cls: {} }], totals: { bf: NaN, usd: undefined },
             excluded: [{ what: undefined, why: null }] },
      juris: { codes: [{ name: undefined, edition: null, cls: 42 }],
               wind: { vMph: NaN, exposure: undefined, cls: "site" },
               mustVerify: [{ what: {}, why: undefined }] },
      pipeline: { stages: "not a shape this sheet knows" },
      at: "x"
    });
    var jt = junk.text();
    truthy(!/undefined/.test(jt) && !/NaN/.test(jt) && !/\[object Object\]/.test(jt),
           "a ctx full of undefined, NaN and objects produces a document with none of them in it");
    truthy(/—/.test(jt), "the missing values print as an em dash instead");
  })();

  /* ============================================================
     6. The approval trail
     ============================================================ */

  suite("planset · the approval trail renders, and says NOT APPROVED when it is not");
  (function () {
    var res = solve("starter-1210", "fl-hvhz");

    /* --- nothing approved --- */
    var none = FM.planset.build({ planResult: res, pipeline: FM.pipeline || null, at: "x" });
    var s00 = none.sheetByNo("S0.0").text();
    truthy(/NOT APPROVED/.test(s00), "with no approvals the cover says NOT APPROVED");
    truthy(/not approved/.test(s00),
           "and every unapproved stage row reads \"not approved\"");
    truthy(/APPROVAL — NOT APPROVED/.test(none.sheetByNo("S5.0").text()),
           "and every unapproved gate is an open item on S5.0");

    /* --- no pipeline at all --- */
    var absent = FM.planset.build({ planResult: res, at: "x" });
    truthy(/NOT APPROVED — no approval trail is available/.test(absent.sheetByNo("S0.0").text()),
           "with no pipeline at all the cover says the trail is unavailable, not that it is clean");

    /* --- a synthetic snapshot with approvals --- */
    var fake = { stages: [
      { stage: { id: "geometry", label: "Geometry", gate: "The drawn plan is what the set says.", needs: "drafter" },
        status: "approved", rec: { by: "A. Drafter", at: "2026-08-01T10:00:00Z", note: "traced from sheet A2.1" },
        moved: [], blockedBy: [] },
      { stage: { id: "takeoff", label: "Takeoff", gate: "Spans and tributaries are what the plan means.", needs: "engineer" },
        status: "stale", rec: { by: "B. Engineer", at: "2026-08-02T09:30:00Z", note: "" },
        moved: [{ stage: "geometry", label: "Geometry" }], blockedBy: [] },
      { stage: { id: "calcs", label: "Calculations", gate: "The members are accepted.", needs: "engineer" },
        status: "pending", rec: null, moved: [], blockedBy: ["Takeoff is stale — approve it first"] }
    ] };
    var withA = FM.planset.build({ planResult: res, pipeline: fake, at: "x" });
    var cover = withA.sheetByNo("S0.0").text();
    truthy(/1 of 3 gates approved/.test(cover), "the trail counts the gates that are approved");
    truthy(cover.indexOf("A. Drafter") !== -1, "and names who approved, by name");
    truthy(cover.indexOf("2026-08-01T10:00:00Z") !== -1, "and when");
    truthy(cover.indexOf("traced from sheet A2.1") !== -1, "and what they wrote");
    truthy(/VOID \(stale\)/.test(cover),
           "an approval invalidated by a later change is shown VOID, not approved");
    truthy(/invalidated because Geometry moved/.test(cover),
           "and says which upstream stage moved under it");
    truthy(/IT DOES NOT SEAL ANYTHING/.test(cover),
           "and the last gate is explicitly not a seal");
    truthy(!/NOT APPROVED — no stage/.test(cover),
           "with an approval on file the cover no longer says nothing was approved");

    var open = withA.sheetByNo("S5.0").text();
    truthy(/Takeoff \(gate: takeoff\) is stale/.test(open), "the stale gate is an open item");
    truthy(/Calculations \(gate: calcs\) is pending/.test(open), "so is the pending one");
    truthy(open.indexOf("Geometry (gate: geometry)") === -1,
           "and the approved gate is NOT listed as open");

    /* --- the real pipeline, driven end to end --- */
    if (FM.pipeline && FM.auth && typeof FM.pipeline.provide === "function") {
      FM.pipeline.reset();
      FM.auth.login(FM.auth.DEMO.user, FM.auth.DEMO.pass);
      FM.pipeline.provide("geometry", function () { return { walls: 4 }; });
      var ok = FM.pipeline.approve("geometry", "geometry checked against the architectural set");
      truthy(ok.ok, "the real pipeline records a geometry approval (" +
             (ok.ok ? "approved" : (ok.why || []).join("; ")) + ")");
      if (ok.ok) {
        var real = FM.planset.build({ planResult: res, pipeline: FM.pipeline, at: "x" });
        var rc = real.sheetByNo("S0.0").text();
        truthy(/1 of 6 gates approved/.test(rc), "and the cover reports 1 of 6 gates approved");
        truthy(rc.indexOf("Demo User") !== -1, "naming the person who approved it");
        truthy(/AUDIT TRAIL/.test(rc), "and prints the append-only audit trail");
      }
      FM.pipeline.reset();
      FM.auth.logout();
      var after = FM.planset.build({ planResult: res, pipeline: FM.pipeline, at: "x" });
      truthy(/NOT APPROVED/.test(after.sheetByNo("S0.0").text()),
             "and after a reset the trail says NOT APPROVED again");
    }
  })();

  /* ============================================================
     7. Design criteria — provenance, and no invented values
     ============================================================ */

  suite("planset · S0.0 carries the design criteria with a provenance class on every row");
  (function () {
    var pack = FM.weights.packById("fl-hvhz");
    var rows = FM.planset.criteria(pack, null).rows;
    truthy(rows.length >= 12, "the criteria table has the rows a plan reviewer looks for");

    var VALID = { code: 1, site: 1, market: 1, derived: 1, user: 1, "not stated": 1 };
    var badCls = rows.filter(function (r) { return !VALID[r.cls]; });
    eq(badCls.length, 0, "every row carries a provenance class from the fixed vocabulary" +
       (badCls.length ? " — " + badCls.map(function (r) { return r.k + "=" + r.cls; }).join(", ") : ""));

    function row(k) {
      var hit = null;
      rows.forEach(function (r) { if (r.k.indexOf(k) === 0) hit = r; });
      return hit;
    }
    truthy(row("Design wind speed") && row("Design wind speed").v.indexOf("175") === 0,
           "design wind speed comes from the pack, with its class and note");
    eq(row("Design wind speed").cls, "site", "and it is site data, not code data");
    truthy(row("Exposure category"), "exposure category is on the table");
    truthy(row("Ground snow"), "ground snow is on the table");
    truthy(row("Seismic design category"), "seismic design category is on the table");
    truthy(row("Floor live load"), "the live loads used are on the table");
    truthy(row("Deflection"), "the deflection criteria are on the table");

    /* the discipline that matters: a field this build does not carry is
       NOT DECLARED, never a plausible number */
    eq(row("Risk category").v, "NOT DECLARED",
       "risk category is NOT DECLARED — no field carries it, so no value is invented");
    eq(row("Risk category").cls, "not stated", "and its class says so");
    eq(row("Code edition").v, "NOT DECLARED",
       "with no jurisdiction record the code edition is NOT DECLARED");
    eq(row("Wall dead load").v, "NONE CARRIED",
       "the absent wall dead load is stated as absent, on the criteria table itself");

    /* with a jurisdiction record the real values appear */
    var jrows = FM.planset.criteria(pack, fixtureJuris()).rows;
    var ed = null;
    jrows.forEach(function (r) { if (/Florida Building Code/.test(r.k)) ed = r; });
    truthy(ed && ed.v.indexOf("8th Edition (2023)") === 0,
           "with a jurisdiction record the adopted edition is stated and cited");

    /* provenance classes are explained on the sheet, not assumed */
    var s00 = FM.planset.build(fullCtx("starter-1210", "fl-hvhz")).sheetByNo("S0.0").text();
    truthy(/PROVENANCE CLASSES USED ABOVE/.test(s00), "the sheet defines the classes it uses");
    truthy(/NO code standing/.test(s00), "and says plainly that market values have no code standing");
  })();

  /* ============================================================
     8. The sheets carry the engineering they claim to
     ============================================================ */

  suite("planset · the schedules and calculations are the solver's own answer");
  (function () {
    var res = solve("sunbelt-ranch-1850", "nc-mountain");
    var pkg = FM.planset.build({ planResult: res, at: "x" });
    var s20 = pkg.sheetByNo("S2.0").text();
    var s30 = pkg.sheetByNo("S3.0").text();

    res.marks.forEach(function (m) {
      truthy(s20.indexOf(m.mark.id) !== -1, "S2.0 carries mark " + m.mark.id);
    });
    truthy(/MEMBER SCHEDULE/.test(s20) && /HEADER SCHEDULE/.test(s20) && /REACTION SCHEDULE/.test(s20),
           "S2.0 is the member, header and reaction schedules the contract names");
    truthy(/NO CONNECTION IS DESIGNED HERE/.test(s20),
           "and the reaction schedule says the connection is not designed here");

    var sized = res.marks.filter(function (m) { return m.solution && m.solution.pick; });
    truthy(sized.length > 0, "this combination sizes at least one member");
    var one = sized[0];
    truthy(s30.indexOf("MARK " + one.mark.id) !== -1,
           "S3.0 has a calculation block for " + one.mark.id);
    truthy(/DCR = /.test(s30), "showing the DCR of each limit state");
    truthy(/GOVERNING : /.test(s30), "and which one governed");
    truthy(/f_b = M\/S/.test(s30) || /M = wL/.test(s30),
           "with the engine's own working, not just a result");
    truthy(!/</.test(s30.replace(/[^<]/g, "")) || s30.indexOf("<span") === -1,
           "and the engine's markup is stripped for the printed sheet");

    /* escalated and not-sized marks appear as such, never omitted */
    var na = res.marks.filter(function (m) { return m.notApplicable; });
    if (na.length) {
      truthy(/NOT SIZED — /.test(s20), "marks that are not this engine's member are carried, not dropped");
      truthy(s30.indexOf("NOT CHECKED") !== -1, "and S3.0 says NOT CHECKED for each of them");
    }
    var esc = res.marks.filter(function (m) { return !m.notApplicable && m.solution && !m.solution.pick; });
    if (esc.length) {
      truthy(/ESCALATIONS — /.test(s20), "escalated marks are reported with their category");
      truthy(/NO MEMBER —/.test(s30), "and S3.0 says there is no calculation for them");
    }
  })();

  /* ============================================================
     9. It prints
     ============================================================ */

  suite("planset · the package is print-shaped");
  (function () {
    var over = [], n = 0;
    every(function (pl, pk) {
      n++;
      FM.planset.build(fullCtx(pl.id, pk.id)).text().split("\n").forEach(function (l) {
        if (l.length > 80) over.push(pl.id + "/" + pk.id + " [" + l.length + "] " + l.slice(0, 60));
      });
    });
    eq(over.length, 0, "no line in any of the 30 packages exceeds 80 columns" +
       (over.length ? " — e.g. " + over[0] : ""));

    var pkg = FM.planset.build(fullCtx("starter-1210", "fl-hvhz"));
    pkg.sheets.forEach(function (s) {
      var head = s.text().split("\n");
      truthy(head[1].indexOf(s.no) !== -1, s.no + " names itself in its own sheet header");
    });
    var trailing = pkg.text().split("\n").filter(function (l) { return /[ \t]$/.test(l); });
    eq(trailing.length, 0, "and no line carries trailing whitespace into the exported file");
  })();

  /* ============================================================
     10. The drawn form
     ============================================================ */

  suite("planset · the sheets render without a real browser");
  (function () {
    /* The harness supplies inert DOM stubs. Nothing here proves the sheets
       LOOK right — that is ui-tests.js's job against a real browser — but a
       renderer that throws on a document with no <head>, or on an SVG path
       with no geometry, would take the whole view down, and that is worth
       catching here. */
    function node() {
      var n = {
        children: [], style: {}, id: "",
        classList: { add: function () {}, remove: function () {}, toggle: function () {},
                     contains: function () { return false; } },
        appendChild: function (c) { this.children.push(c); return c; },
        setAttribute: function () {}, addEventListener: function () {},
        textContent: "", innerHTML: ""
      };
      return n;
    }

    var withGeom = FM.planset.build(fullCtx("starter-1210", "fl-hvhz"));
    var host = node(), threw = null;
    try { FM.planset.render(host, withGeom); } catch (e) { threw = e; }
    truthy(!threw, "render(host, pkg) does not throw" + (threw ? " — " + threw.message : ""));
    eq(host.children.length, 7, "and appends one node per sheet");

    withGeom.sheets.forEach(function (s) {
      var t2 = null, h = node();
      try { s.render(h); } catch (e) { t2 = e; }
      truthy(!t2, s.no + ".render(host) does not throw" + (t2 ? " — " + t2.message : ""));
    });

    /* the same, with NO geometry: the SVG path must be skipped, not crash */
    var noGeom = FM.planset.build({ planResult: solve("starter-1210", "fl-hvhz"), at: "x" });
    var h2 = node(), t3 = null;
    try { FM.planset.render(h2, noGeom); } catch (e) { t3 = e; }
    truthy(!t3, "a package with no CAD model renders too" + (t3 ? " — " + t3.message : ""));

    /* a model with degenerate coordinates must not produce a broken drawing */
    var junkModel = { version: 1, name: "junk", levels: [{ id: "L1", label: "L1",
      walls: [{ id: "W1", x1: "x", y1: null, x2: undefined, y2: NaN }], openings: [], framing: [] }] };
    var g = FM.planset.geometry(junkModel, null, null);
    eq(g.ok, false, "a model with no usable coordinate is reported as undrawable");
    truthy(g.why.length > 0, "and says why rather than drawing nothing silently");
    var junkPkg = FM.planset.build({ planResult: solve("starter-1210", "fl-hvhz"),
                                     model: junkModel, at: "x" });
    truthy(/THE MODEL COULD NOT BE READ/.test(junkPkg.sheetByNo("S1.0").text()),
           "and S1.0 says the model could not be read");
  })();

  /* ============================================================
     11. Against the real upstream modules, when they are present
     ============================================================ */

  suite("planset · integration with cad.js, takeoff.js and bom.js as they actually are");
  (function () {
    var have = !!(FM.cad && FM.takeoff && FM.bom);
    truthy(true, "cad.js / takeoff.js / bom.js " + (have ? "are loaded — integrating" : "are not loaded — the guarded path is what runs"));
    if (!have) return;

    var problems = [], n = 0;
    every(function (pl, pk) {
      n++;
      var res = FM.solver.solvePlan(pl, pk);
      var model = null, tk = null, bom = null;
      try { model = FM.cad.fromPlan(pl.id); } catch (e) { model = null; }
      try { tk = FM.takeoff.run(model, { plan: pl, pack: pk }); } catch (e) { tk = null; }
      try { bom = FM.bom.build(res, {}); } catch (e) { bom = null; }
      var pkg = FM.planset.build({ model: model, takeoff: tk, planResult: res, bom: bom,
                                   pipeline: FM.pipeline, at: "x" });
      var txt = pkg.text();
      var where = pl.id + "/" + pk.id;
      if (/stamp/i.test(txt)) problems.push(where + ": upstream prose carried \"stamp\" into the package");
      if (/undefined/.test(txt) || /NaN/.test(txt) || /\[object Object\]/.test(txt)) {
        problems.push(where + ": an upstream value leaked as undefined/NaN/[object Object]");
      }
      txt.split("\n").forEach(function (l) {
        if (l.length > 80) problems.push(where + ": upstream text overflows the sheet at " + l.length + " columns");
      });
      if (!pkg.openItems.length) problems.push(where + ": S5.0 came out empty");
    });
    eq(n, 30, "integrated across all 30 combinations");
    eq(problems.length, 0, "real upstream content survives the sheet layout intact" +
       (problems.length ? " — " + problems.slice(0, 3).join(" | ") : ""));
  })();
};

/* ============================================================
   FM.bom — regression suite.

   Wired in by test/run-tests.js as:

       require("./suite-bom.js")(
         { suite: suite, eq: eq, near: near, truthy: truthy }, FM);

   with FM loaded from test/harness.js including "bom.js". Standalone:

       node test/suite-bom.js

   The suite is written against the contract in ARCHITECTURE.md §FM.bom,
   and four of its batteries exist to stop a specific way this module
   could quietly lie:

     · a hand-checked plan, computed on paper in the comments and
       asserted exactly, so the arithmetic is pinned rather than
       described;
     · EVERY escalated mark in ALL 30 plan x pack combinations must
       appear in `excluded`, because a BOM that omits the girder on one
       of thirty combinations is still a BOM that omits the girder;
     · no line anywhere in those 30 may carry a NaN, an undefined or a
       negative quantity;
     · the waste guard for register A5 — the drop appears exactly once,
       inside the stick that was bought, and never again as a
       percentage.
   ============================================================ */

"use strict";

module.exports = function (t, FM) {
  var suite = t.suite, eq = t.eq, near = t.near, truthy = t.truthy;

  function plan(id) { return FM.weights.planById(id); }
  function pack(id) { return FM.weights.packById(id); }
  function bomOf(planId, packId, opts) {
    return FM.bom.build(FM.solver.solvePlan(plan(planId), pack(packId)), opts || {});
  }
  function lineFor(bom, sku, treated, stockFt) {
    return bom.lines.filter(function (g) {
      return g.sku === sku && g.treated === treated && g.stockLengthFt === stockFt;
    })[0] || null;
  }
  function every(fn) {
    FM.weights.PLANS.forEach(function (p) {
      FM.weights.PACKS.forEach(function (k) { fn(p, k); });
    });
  }

  /* ============================================================
     1. THE SURFACE
     ============================================================ */

  suite("bom · surface and contract shape");
  (function () {
    truthy(FM.bom, "FM.bom is registered");
    eq(typeof FM.bom.build, "function", "FM.bom.build is a function");
    eq(typeof FM.bom.text, "function", "FM.bom.text is a function");

    var b = bomOf("starter-1210", "tx-i35");
    ["lines", "totals", "perLot", "perCommunity", "excluded", "waste"].forEach(function (k) {
      truthy(Object.prototype.hasOwnProperty.call(b, k), "build() returns `" + k + "` per the contract");
    });
    truthy(Object.prototype.toString.call(b.lines) === "[object Array]", "lines is an array");
    truthy(Object.prototype.toString.call(b.excluded) === "[object Array]", "excluded is an array");
    eq(b.complete, false, "a BOM from this system never claims completeness");

    var g = b.lines[0];
    ["sku", "size", "species", "grade", "treatment", "piecesPerHouse", "lengthFt",
     "stockLengthFt", "piecesPerStock", "bf", "lf", "unitUSD", "extUSD", "marks",
     "cls", "basis"].forEach(function (k) {
      truthy(Object.prototype.hasOwnProperty.call(g, k), "a line carries `" + k + "` per the contract");
    });
    eq(g.cls, "derived", "line quantities are class `derived`");
    eq(b.totals.cls, "derived", "totals are class `derived`");

    /* the text renderer must survive being pasted into an email */
    var txt = FM.bom.text(b);
    truthy(typeof txt === "string" && txt.length > 2000, "text() returns a substantial string");
    truthy(txt.indexOf("NOT SEALED ENGINEERING") !== -1, "text() says the software never stamps");
    truthy(txt.indexOf("EXCLUDED") !== -1, "text() carries the excluded section");
    truthy(txt.indexOf("[market]") !== -1, "text() marks its money as [market]");
  })();

  /* ============================================================
     2. HAND-CHECKED PLAN — starter-1210 in tx-i35
     ============================================================

     Solved by hand from weights.js and solver.js, then asserted
     exactly. The schedule for this plan/pack is:

       HDR-W    span 4.50 ft  x8   → 4x6  Southern Pine No.2  (dry)
       HDR-ENT  span 3.67 ft  x1   → 4x6  Southern Pine No.2  (dry)
       HDR-SLD  span 6.50 ft  x1   → 4x8  Southern Pine No.1  (dry)
       HDR-GAR  span 9.67 ft  x1   → 4x12 Southern Pine No.1  (dry)
       BM-ENT   span 8.00 ft  x1   → 4x6  Southern Pine No.2  (TREATED)

     STOCK LENGTHS — stockLength(s) = max(8, ceil((s + 0.5)/2) x 2):
       HDR-W    4.50 + 0.5 = 5.00  → ceil(2.5) x 2 = 6 → floored to 8 ft
       HDR-ENT  3.67 + 0.5 = 4.17  → ceil(2.085) x 2 = 6 → floored to 8 ft
       HDR-SLD  6.50 + 0.5 = 7.00  → ceil(3.5) x 2 = 8  → 8 ft
       HDR-GAR  9.67 + 0.5 = 10.17 → ceil(5.085) x 2 = 12 → 12 ft
       BM-ENT   8.00 + 0.5 = 8.50  → ceil(4.25) x 2 = 10 → 10 ft

     LINES — keyed (SKU, treatment, stock length):
       L1  4x6  SYP No.2 dry      8 ft   HDR-W 8 + HDR-ENT 1 = 9 pc
       L2  4x6  SYP No.2 TREATED 10 ft   BM-ENT 1 pc          <- same SKU as L1,
                                                                  different product
       L3  4x8  SYP No.1 dry      8 ft   HDR-SLD 1 pc
       L4  4x12 SYP No.1 dry     12 ft   HDR-GAR 1 pc
       → 4 lines, 12 pieces.

     BOARD FEET — bfPerLF = b x d / 12 on the NOMINAL size:
       4x6  = 4 x 6 /12 = 2.0000 bf/lf
       4x8  = 4 x 8 /12 = 2.6667 bf/lf
       4x12 = 4 x12 /12 = 4.0000 bf/lf
     purchased, over the FULL stick:
       L1  2.0000 x  8 x 9 = 144.0000 bf
       L2  2.0000 x 10 x 1 =  20.0000 bf
       L3  2.6667 x  8 x 1 =  21.3333 bf
       L4  4.0000 x 12 x 1 =  48.0000 bf
       TOTAL              = 233.3333 bf
     in the members (cut length = span + 0.5):
       HDR-W    2.0000 x 5.00  x 8 = 80.0000
       HDR-ENT  2.0000 x 4.17  x 1 =  8.3400   (mark span 3.67 exactly)
       BM-ENT   2.0000 x 8.50  x 1 = 17.0000
       HDR-SLD  2.6667 x 7.00  x 1 = 18.6667
       HDR-GAR  4.0000 x 10.17 x 1 = 40.6800
       TOTAL                       = 164.6867
     drop = 233.3333 - 164.6867 = 68.6467 bf  → 29.42% of the buy.

     MATERIAL [market] — bf x $/bf x material(1.00) x (1 + cullRate):
       tx-i35 palette: SYP No.2 $0.70/bf cull 0.03; SYP No.1 $0.86/bf cull 0.03
       L1  144.0000 x 0.70 x 1.03 = $103.8240
       L2   20.0000 x 0.70 x 1.03 = $ 14.4200
       L3   21.3333 x 0.86 x 1.03 = $ 18.8971
       L4   48.0000 x 0.86 x 1.03 = $ 42.5184
       TOTAL                      = $179.6595
     PER COMMUNITY, base case x 220 lots:
       pieces 12 x 220 = 2,640 ; bf 233.3333 x 220 = 51,333.33
       $179.6595 x 220 = $39,525.09
     ============================================================ */

  suite("bom · hand-checked takeoff — starter-1210 / tx-i35");
  (function () {
    var b = bomOf("starter-1210", "tx-i35");

    eq(b.lines.length, 4, "4 purchase lines (SKU x treatment x stock length)");
    eq(b.totals.pieces, 12, "12 pieces per house, hand-counted 8+1+1+1+1");
    eq(b.totals.skuCount, 4, "4 distinct SKU/treatment products");

    var L1 = lineFor(b, "4x6 Southern Pine No.2", false, 8);
    var L2 = lineFor(b, "4x6 Southern Pine No.2", true, 10);
    var L3 = lineFor(b, "4x8 Southern Pine No.1", false, 8);
    var L4 = lineFor(b, "4x12 Southern Pine No.1", false, 12);
    truthy(L1 && L2 && L3 && L4, "all four hand-derived lines exist");

    eq(L1.piecesPerHouse, 9, "L1 · 4x6 SYP #2 dry @ 8 ft — 9 pc (HDR-W 8 + HDR-ENT 1)");
    eq(L2.piecesPerHouse, 1, "L2 · 4x6 SYP #2 TREATED @ 10 ft — 1 pc (BM-ENT)");
    eq(L3.piecesPerHouse, 1, "L3 · 4x8 SYP #1 dry @ 8 ft — 1 pc (HDR-SLD)");
    eq(L4.piecesPerHouse, 1, "L4 · 4x12 SYP #1 dry @ 12 ft — 1 pc (HDR-GAR)");

    /* stock lengths, hand-derived above and asserted against the helper */
    eq(FM.solver.stockLength(4.50), 8, "stockLength(4.50 ft span) = 8 ft (min applies)");
    eq(FM.solver.stockLength(6.50), 8, "stockLength(6.50) = 8 ft");
    eq(FM.solver.stockLength(8.00), 10, "stockLength(8.00) = 10 ft — a 8 ft beam is a 10 ft stick");
    eq(FM.solver.stockLength(9.67), 12, "stockLength(9.67) = 12 ft");
    eq(L4.stockLengthFt, 12, "HDR-GAR's line buys a 12-footer, not a 9'-8\" member");

    /* board feet, per the hand arithmetic */
    near(L1.bf, 144.0, 1e-9, "L1 bf = 2.0000 bf/lf x 8 ft x 9 pc = 144.0000");
    near(L2.bf, 20.0, 1e-9, "L2 bf = 2.0000 x 10 x 1 = 20.0000");
    near(L3.bf, 64 / 3, 1e-9, "L3 bf = 2.6667 x 8 x 1 = 21.3333");
    near(L4.bf, 48.0, 1e-9, "L4 bf = 4.0000 x 12 x 1 = 48.0000");
    near(b.totals.bf, 233.33333333, 1e-6, "purchased bf = 233.3333 (hand-summed)");
    near(b.totals.cutBf, 164.6867, 1e-4, "bf in the members = 164.6867 (hand-summed)");
    near(b.totals.dropBf, 68.6466, 1e-4, "drop bf = 233.3333 - 164.6867 = 68.6466");

    /* money, per the hand arithmetic, [market] */
    near(L1.extUSD, 103.824, 1e-6, "L1 $ = 144.0 x 0.70 x 1.03 = $103.824 [market]");
    near(L2.extUSD, 14.42, 1e-6, "L2 $ = 20.0 x 0.70 x 1.03 = $14.42 [market]");
    near(L3.extUSD, 18.897066, 1e-5, "L3 $ = 21.3333 x 0.86 x 1.03 = $18.8971 [market]");
    near(L4.extUSD, 42.5184, 1e-6, "L4 $ = 48.0 x 0.86 x 1.03 = $42.5184 [market]");
    near(b.totals.usd, 179.659466, 1e-5, "material total = $179.6595 [market]");
    near(L1.unitUSD, 103.824 / 9, 1e-9, "unitUSD is extUSD / pieces");

    /* lf and the per-community multiply */
    near(L1.lf, 72, 1e-9, "L1 lf = 8 ft x 9 pc = 72 lf purchased");
    eq(b.perCommunity.lots, 220, "starter-1210 declares 220 lots");
    eq(b.perCommunity.pieces, 2640, "perCommunity pieces = 12 x 220 = 2,640");
    near(b.perCommunity.bf, 51333.3333, 1e-3, "perCommunity bf = 233.3333 x 220");
    near(b.perCommunity.usd, 39525.0826, 1e-3, "perCommunity $ = 179.6595 x 220 [market]");

    /* the arithmetic must be READABLE, not just right */
    truthy(L1.basis.indexOf("2.000 bf/lf") !== -1, "the line's basis prints the bf/lf it used");
    truthy(L1.basis.indexOf("FM.solver.stockLength") !== -1,
           "the line's basis names FM.solver.stockLength as the source of the length");
    truthy(L1.basis.indexOf("[market") !== -1, "the line's basis marks its price [market]");
    truthy(L1.basis.indexOf("[derived") !== -1, "the line's basis marks its quantity [derived]");
  })();

  /* ============================================================
     3. REUSE — the BOM must not have a second opinion
     ============================================================ */

  suite("bom · reuses the solver's helpers rather than reimplementing them");
  (function () {
    var checked = 0, mismatched = 0;
    every(function (p, k) {
      var res = FM.solver.solvePlan(p, k);
      var b = FM.bom.build(res, {});
      eqSilent(b);
      function eqSilent(bom) {
        bom.lines.forEach(function (g) {
          checked++;
          if (g.stockLengthFt !== FM.solver.stockLength(g.lengthFt - FM.bom.BEARING_ALLOWANCE_FT) &&
              g.cuts.every(function (c) {
                return FM.solver.stockLength(c.spanFt) !== g.stockLengthFt;
              })) mismatched++;
          if (Math.abs(g.bfPerLf - FM.solver.boardFeetPerLF(g.size)) > 1e-12) mismatched++;
          if (g.sku !== g.size + " " + g.species + " " + g.grade) mismatched++;
        });
      }
    });
    truthy(checked > 0, "there are lines to check across the 30 combinations (" + checked + ")");
    eq(mismatched, 0,
       "every line's stock length, bf/lf and SKU string come from FM.solver, not a local copy");

    /* the module's own self-check must never have fired */
    var fired = 0;
    every(function (p, k) {
      var b = FM.bom.build(FM.solver.solvePlan(p, k), {});
      fired += b.selfChecks.length;
    });
    eq(fired, 0, "the stockLength-vs-costed-stick self-check never fires in 30 combinations");
  })();

  /* ============================================================
     4. EVERY ESCALATED MARK, IN EVERY PLAN x PACK — 30 COMBINATIONS
     ============================================================ */

  suite("bom · every escalated mark in all 30 plan x pack combinations is in `excluded`");
  (function () {
    var combos = 0, escTotal = 0, missing = [], unreasoned = [], claimed = 0;
    every(function (p, k) {
      combos++;
      var res = FM.solver.solvePlan(p, k);
      var b = FM.bom.build(res, {});

      var esc = res.marks.filter(function (m) {
        return !m.notApplicable && m.solution && !m.solution.pick;
      });
      escTotal += esc.length;

      esc.forEach(function (m) {
        var hit = b.excluded.filter(function (e) {
          return e.kind === "escalated" && e.markId === m.mark.id;
        })[0];
        if (!hit) { missing.push(p.id + "/" + k.id + " " + m.mark.id); return; }
        /* a reason, not a shrug: the status and the wall must both be carried */
        if (!hit.why || hit.why.indexOf(m.solution.status) === -1) {
          unreasoned.push(p.id + "/" + k.id + " " + m.mark.id + " (status not in the reason)");
        }
        /* and it must NOT be priced anywhere in the bill */
        b.lines.forEach(function (g) {
          if (g.marks.indexOf(m.mark.id) !== -1) {
            claimed++;
          }
        });
      });

      /* the not-applicable marks are the other half of the honest list */
      res.marks.filter(function (m) { return m.notApplicable; }).forEach(function (m) {
        var hit = b.excluded.filter(function (e) {
          return e.kind === "out-of-scope" && e.markId === m.mark.id;
        })[0];
        if (!hit) missing.push(p.id + "/" + k.id + " " + m.mark.id + " (not-applicable)");
      });
    });

    eq(combos, 30, "all 30 plan x pack combinations were exercised, not one");
    truthy(escTotal >= 30, "the corpus really does escalate (" + escTotal + " escalations across 30)");
    eq(missing.length, 0, "no escalated or out-of-scope mark is missing from `excluded`" +
       (missing.length ? " — " + missing.slice(0, 6).join("; ") : ""));
    eq(unreasoned.length, 0, "every escalation in `excluded` carries its status in the reason" +
       (unreasoned.length ? " — " + unreasoned.slice(0, 4).join("; ") : ""));
    eq(claimed, 0, "no escalated mark is ALSO priced on a line — it is excluded, not both");
  })();

  suite("bom · `excluded` names the structure this system never sizes at all");
  (function () {
    var b = bomOf("starter-1210", "tx-i35");
    var all = b.excluded.map(function (e) { return (e.what + " " + e.why).toLowerCase(); }).join(" | ");

    /* the categories the contract requires by name */
    [["connector", "connectors"], ["hanger", "hangers"], ["strap", "straps"],
     ["hold-down", "hold-downs"], ["anchor bolt", "anchor bolts"], ["sheathing", "sheathing"],
     ["fastener", "fasteners"], ["blocking", "blocking"], ["rim board", "rim board"],
     ["subfloor", "subfloor"], ["roofing", "roofing"], ["stud", "studs and jacks"],
     ["truss", "trusses"], ["shear wall", "shear walls"], ["post", "posts"]
    ].forEach(function (pair) {
      truthy(all.indexOf(pair[0]) !== -1, "`excluded` names " + pair[1]);
    });

    /* the sentence that has to be said plainly */
    truthy(all.indexOf("more of the cost than the lumber") !== -1,
           "`excluded` says plainly that in a wind market the connection package is frequently " +
           "more of the cost than the lumber");

    /* and every entry must actually have a reason */
    var noWhy = b.excluded.filter(function (e) {
      return !e.what || !e.why || String(e.why).length < 20;
    });
    eq(noWhy.length, 0, "every excluded entry carries a real reason, not a label");

    /* a wind-governed pack must escalate the tone rather than repeat it */
    var wind = bomOf("coastal-duplex-1600", "tx-gulf");
    var w = wind.excluded.filter(function (e) { return e.severity === "critical"; })[0];
    truthy(w, "in a wind-governed pack the connection-package exclusion is marked critical");
    truthy(FM.bom.text(wind).indexOf("WIND GOVERNS IN THIS MARKET") !== -1,
           "the wind-governed banner is printed at the top of the text output");
  })();

  /* ============================================================
     5. NO NaN, undefined OR NEGATIVE ANYWHERE IN 30 COMBINATIONS
     ============================================================ */

  suite("bom · no line carries a NaN, undefined or negative quantity — all 30 combinations");
  (function () {
    var NUMERIC = ["piecesPerHouse", "lengthFt", "stockLengthFt", "piecesPerStock",
                   "bf", "cutBf", "dropBf", "lf", "unitUSD", "extUSD", "dropHandlingUSD",
                   "bfPerLf", "bfPerPiece", "bfUSD", "cullRate", "availability", "nestPerStock"];
    var bad = [], lines = 0, combos = 0;

    every(function (p, k) {
      combos++;
      var b = FM.bom.build(FM.solver.solvePlan(p, k), {});
      var where = p.id + "/" + k.id;

      b.lines.forEach(function (g) {
        lines++;
        NUMERIC.forEach(function (f) {
          var v = g[f];
          if (v === undefined || v === null) { bad.push(where + " " + g.sku + "." + f + " = " + v); return; }
          if (typeof v !== "number" || !isFinite(v)) { bad.push(where + " " + g.sku + "." + f + " = " + v); return; }
          if (v < 0) bad.push(where + " " + g.sku + "." + f + " NEGATIVE " + v);
        });
        if (!(g.piecesPerHouse > 0)) bad.push(where + " " + g.sku + " has no pieces");
        if (!g.marks.length) bad.push(where + " " + g.sku + " names no mark");
        if (!g.basis || String(g.basis).indexOf("undefined") !== -1) {
          bad.push(where + " " + g.sku + " basis is empty or leaks `undefined`");
        }
        if (typeof g.treatment !== "string" || !g.treatment) bad.push(where + " " + g.sku + " no treatment");
      });

      ["bf", "cutBf", "dropBf", "lf", "pieces", "usd", "dropHandlingUSD"].forEach(function (f) {
        var v = b.totals[f];
        if (typeof v !== "number" || !isFinite(v) || v < 0) bad.push(where + " totals." + f + " = " + v);
      });
      ["pieces", "bf", "lf", "usd"].forEach(function (f) {
        var v = b.perCommunity[f];
        if (v !== null && (typeof v !== "number" || !isFinite(v) || v < 0)) {
          bad.push(where + " perCommunity." + f + " = " + v);
        }
      });

      /* the rendered form must not leak them either — a sheet is what a human reads */
      var txt = FM.bom.text(b);
      if (/NaN|undefined|\[object Object\]/.test(txt)) {
        bad.push(where + " text() leaks: " + (txt.match(/.{0,40}(NaN|undefined|\[object Object\]).{0,20}/) || [])[0]);
      }
    });

    eq(combos, 30, "30 combinations exercised for the NaN/negative sweep");
    truthy(lines >= 80, "the sweep covered a real population of lines (" + lines + ")");
    eq(bad.length, 0, "no NaN, undefined or negative quantity anywhere" +
       (bad.length ? " — " + bad.slice(0, 8).join(" ; ") : ""));
  })();

  /* ============================================================
     6. UNIFICATION — ONE LINE, BOTH MARKS
     ============================================================ */

  suite("bom · unified marks collapse to ONE line naming both");
  (function () {
    /* starter-1210 in nc-mountain: the solver accepts a header-group
       unification raising HDR-ENT from 4x6 SYP #2 onto HDR-W's sibling
       4x6 SYP #1. Both marks buy an 8 ft stick, so this is the exact
       case the contract's `marks: ["FJ-1","FJ-3"]` example describes. */
    var res = FM.solver.solvePlan(plan("starter-1210"), pack("nc-mountain"));
    var accepted = (res.unified || []).filter(function (u) { return u.accepted; });
    truthy(accepted.length > 0, "the solver accepted a unification on starter-1210 / nc-mountain");

    var b = FM.bom.build(res, {});
    var hit = b.lines.filter(function (g) {
      return g.marks.indexOf("HDR-W") !== -1 && g.marks.indexOf("HDR-ENT") !== -1;
    });
    eq(hit.length, 1, "HDR-W and HDR-ENT produce exactly ONE line, not two");
    eq(hit[0].sku, "4x6 Southern Pine No.1", "that line is the unified SKU both marks landed on");
    eq(hit[0].piecesPerHouse, 9, "the one line carries both marks' pieces: 8 + 1 = 9");
    eq(hit[0].marks.length, 2, "the line NAMES both marks");
    truthy(hit[0].unified > 0, "the line records that a mark on it was raised by unification");
    truthy(hit[0].basis.indexOf("RAISED BY SKU UNIFICATION") !== -1,
           "the line's basis says which mark was raised, so the extra lumber is not silent");

    /* HDR-W and HDR-ENT must not ALSO appear on a second line */
    var strays = b.lines.filter(function (g) {
      return g !== hit[0] &&
             (g.marks.indexOf("HDR-W") !== -1 || g.marks.indexOf("HDR-ENT") !== -1);
    });
    eq(strays.length, 0, "neither unified mark survives on a second line");

    /* ---- the general rule, across all 30 ----
       wherever the solver accepted a unification, every mark in that move
       must end up on ONE SKU. Where their stock lengths differ they are
       one SKU on several LENGTH lines, which is the honest purchase
       (you order 14-footers and 10-footers separately) — so the assertion
       is at the SKU level and the length split is asserted separately. */
    var violations = [], moves = 0;
    every(function (p, k) {
      var r = FM.solver.solvePlan(p, k);
      var bb = FM.bom.build(r, {});
      (r.unified || []).filter(function (u) { return u.accepted; }).forEach(function (u) {
        moves++;
        var ids = u.raised.map(function (x) { return x.mark; });
        var skus = {};
        ids.forEach(function (id) {
          bb.lines.forEach(function (g) {
            if (g.marks.indexOf(id) !== -1) skus[g.sku] = 1;
          });
        });
        var got = Object.keys(skus);
        if (got.length !== 1 || got[0] !== u.target) {
          violations.push(p.id + "/" + k.id + " " + ids.join("+") + " → " + got.join(","));
        }
      });
    });
    truthy(moves > 0, "the corpus contains accepted unifications to check (" + moves + ")");
    eq(violations.length, 0, "every raised mark lands on exactly the unification target SKU" +
       (violations.length ? " — " + violations.join("; ") : ""));

    /* one SKU, several lengths — asserted where it actually happens */
    var ts = FM.bom.build(FM.solver.solvePlan(plan("two-story-2450"), pack("tx-i35")), {});
    var floor = ts.lines.filter(function (g) {
      return g.sku === "2x12 Southern Pine No.2" && !g.treated;
    });
    eq(floor.length, 3, "FJ-1/FJ-2/FJ-3 unified onto ONE SKU buy THREE lengths — 10, 14 and 16 ft");
    var lens = floor.map(function (g) { return g.stockLengthFt; }).sort(function (a, b2) { return a - b2; });
    eq(lens.join(","), "10,14,16", "the three lengths are 10, 14 and 16 ft, as the spans require");
    var sku = ts.totals.bySku["2x12 Southern Pine No.2 · dry"];
    truthy(sku, "the SKU view collapses those three lines back to one product");
    eq(sku.marks.length, 3, "the SKU view names all three marks it serves");
    eq(sku.pieces, floor[0].piecesPerHouse + floor[1].piecesPerHouse + floor[2].piecesPerHouse,
       "the SKU view's piece count is the sum of its length lines");
  })();

  /* ============================================================
     7. TREATMENT IS PART OF THE SKU
     ============================================================ */

  suite("bom · treated and dry never collapse into one line");
  (function () {
    /* two-story-2450 / tx-i35 carries 2x12 SYP #2 as BOTH a dry floor
       joist (FJ-*) and a TREATED deck joist (DK-1). Same size, same
       species, same grade — different product, different rack, and in
       weights.js a different STOCK channel. */
    var b = FM.bom.build(FM.solver.solvePlan(plan("two-story-2450"), pack("tx-i35")), {});
    var same = b.lines.filter(function (g) { return g.sku === "2x12 Southern Pine No.2"; });
    var dry = same.filter(function (g) { return !g.treated; });
    var pt = same.filter(function (g) { return g.treated; });
    truthy(dry.length > 0 && pt.length > 0,
           "the plan really does carry the same SKU in both channels");
    eq(pt.length, 1, "the treated 2x12 is its own line");
    eq(pt[0].marks.join(","), "DK-1", "the treated 2x12 line serves the deck joist and nothing else");
    eq(pt[0].treatment, "TREATED", "it is labelled TREATED on the face of the line");
    eq(dry[0].treatment, "dry", "the floor joists are labelled dry");
    truthy(dry.every(function (g) { return g.marks.indexOf("DK-1") === -1; }),
           "no dry line has absorbed the treated deck joist");
    eq(pt[0].channel, "wet/treated",
       "the treated line records the STOCK channel weights.js priced it from");

    /* the SKU view must keep them apart too — that is where a flattening
       would actually happen, because the size string is identical */
    truthy(b.totals.bySku["2x12 Southern Pine No.2 · dry"], "SKU view has the dry 2x12");
    truthy(b.totals.bySku["2x12 Southern Pine No.2 · TREATED"], "SKU view has the treated 2x12");

    /* and the public maps must use REAL keys — a consumer doing Object.keys()
       has to see "header", not a prefixed sentinel this file uses internally */
    var keys = Object.keys(b.totals.byCategory);
    truthy(keys.length > 0 && keys.every(function (k) { return k === k.replace(/^\s+/, ""); }),
           "public maps expose plain keys, not internal prototype-guard prefixes");
    truthy(keys.every(function (k) { return typeof b.totals.byCategory[k] === "number"; }),
           "byCategory is a scalar per role (material dollars), printable by any consumer");
    truthy(b.totals.byCategoryDetail[keys[0]].pieces > 0,
           "byCategoryDetail carries the pieces/bf/marks behind each category");
    truthy(JSON.parse(JSON.stringify(b)).totals.byCategory[keys[0]] !== undefined,
           "the whole BOM survives a JSON round trip — no functions, no lost keys");

    /* the global rule: no line may ever mix treated and untreated marks */
    var mixed = [];
    every(function (p, k) {
      var res = FM.solver.solvePlan(p, k);
      var bb = FM.bom.build(res, {});
      var byMark = {};
      res.marks.forEach(function (m) {
        if (m.demand) byMark[" " + m.mark.id] = !!m.demand.treated;
      });
      bb.lines.forEach(function (g) {
        g.marks.forEach(function (id) {
          if (byMark[" " + id] !== g.treated) {
            mixed.push(p.id + "/" + k.id + " " + g.sku + " has " + id);
          }
        });
      });
    });
    eq(mixed.length, 0, "across all 30 combinations no line mixes treated and dry marks" +
       (mixed.length ? " — " + mixed.slice(0, 5).join("; ") : ""));
  })();

  /* ============================================================
     8. PER LOT / PER COMMUNITY
     ============================================================ */

  suite("bom · perCommunity = perLot x lots for the base case");
  (function () {
    var off = [], checked = 0;
    every(function (p, k) {
      var b = FM.bom.build(FM.solver.solvePlan(p, k), {});
      if (b.perCommunity.lots === null) return;
      checked++;
      var n = b.perCommunity.lots;
      eqNear("pieces", b.perCommunity.pieces, b.perLot.pieces * n);
      eqNear("bf", b.perCommunity.bf, b.perLot.bf * n);
      eqNear("lf", b.perCommunity.lf, b.perLot.lf * n);
      eqNear("usd", b.perCommunity.usd, b.perLot.usd * n);
      function eqNear(f, a, e) {
        if (Math.abs(a - e) > 1e-6) off.push(p.id + "/" + k.id + " " + f + " " + a + " != " + e);
      }
      if (b.perCommunity.weighted) off.push(p.id + "/" + k.id + " weighted without being asked");
      if (String(b.perCommunity.basis).indexOf("BASE CASE") === -1) {
        off.push(p.id + "/" + k.id + " basis does not declare the base-case assumption");
      }
    });
    eq(checked, 30, "every combination declares a lot count and was checked");
    eq(off.length, 0, "perCommunity is exactly perLot x lots for the base case" +
       (off.length ? " — " + off.slice(0, 5).join("; ") : ""));

    var b0 = bomOf("starter-1210", "tx-i35");
    eq(b0.perLot.lots, 1, "perLot is one house");
    truthy(b0.perLot.basis.indexOf("NONE of the EXCLUDED") !== -1,
           "perLot says out loud that it covers none of the excluded list");
  })();

  suite("bom · take-rate weighting sums against the declared rates, or refuses");
  (function () {
    var b = bomOf("starter-1210", "tx-i35", { takeRates: true });
    var pc = b.perCommunity;
    eq(pc.weighted, true, "take-rate weighting ran when asked");
    eq(pc.lots, 220, "it weights over the plan's 220 lots");
    eq(pc.solvedConfigurations, pc.configurations,
       "every buildable configuration solved (" + pc.configurations + ")");
    eq(pc.failedConfigurations.length, 0, "no configuration failed to solve");

    /* THE arithmetic check: exclusive shares must sum to 1.000000, and the
       lot counts must sum to the community. If either drifts, the weighting
       is a fabrication dressed as a number. */
    var sp = 0, lotSum = 0;
    pc.perConfiguration.forEach(function (c) { sp += c.p; lotSum += c.lotsExpected; });
    near(sp, 1, 1e-9, "the exclusive configuration probabilities sum to exactly 1.000000");
    near(lotSum, 220, 1e-6, "the expected lot counts sum to the declared 220 lots");

    /* and the expectation must be the weighted sum, recomputed independently */
    var handPieces = 0, handUsd = 0;
    pc.perConfiguration.forEach(function (c) {
      handPieces += c.piecesPerLot * c.lotsExpected;
      handUsd += c.usdPerLot * c.lotsExpected;
    });
    near(pc.piecesExpected, handPieces, 1e-6,
         "piecesExpected = Σ P(config) x pieces(config) x lots, recomputed by hand");
    near(pc.usd, handUsd, 1e-6, "usd = Σ P(config) x $(config) x lots [market]");
    eq(pc.pieces, Math.ceil(pc.piecesExpected - 1e-9),
       "the whole-stick buy is ceil(expected) and the rule is stated on the line");
    truthy(pc.lines.every(function (a) { return a.roundingRule; }),
           "every weighted line carries its rounding rule");

    /* the weighting must be visibly DIFFERENT from the base — otherwise it
       is decoration. Elevation C deletes HDR-GAR on a quarter of the lots. */
    truthy(pc.piecesExpected < b.perLot.pieces * 220,
           "the weighted community is smaller than base x lots — elevation C deletes a member");
    eq(pc.takeRateCls, "market", "take rates are declared [market], with no code standing");
    truthy(pc.takeRateBasis.indexOf("INCLUSIVE") !== -1,
           "the basis explains why weights.js's own combination rate cannot simply be summed");

    /* and the escalations only the weighting can see must reach `excluded` */
    var lifted = b.excluded.filter(function (e) { return e.scope === "variant"; });
    truthy(lifted.length >= 2,
           "marks that escalate only on some elevations are lifted into `excluded` (" +
           lifted.length + ")");
    truthy(lifted.some(function (e) { return e.markId === "BM-CAR"; }),
           "BM-CAR — the carport beam that exists only on elevation C and escalates there — " +
           "is named in `excluded`, though it appears nowhere on the base sheet");
    truthy(lifted.every(function (e) { return isFinite(e.lotsExpected) && e.lotsExpected > 0; }),
           "each carries the share of lots it hits");

    /* refusal path: honest base rather than a fudge */
    var noVar = FM.weights.PLANS.filter(function (p) {
      return !(p.elevations && p.elevations.length) && !(p.options && p.options.length);
    })[0];
    if (noVar) {
      var nb = FM.bom.build(FM.solver.solvePlan(noVar, pack("tx-i35")), { takeRates: true });
      eq(nb.perCommunity.weighted, false, "a plan with no variants falls back to the base case");
      truthy(nb.perCommunity.basis.indexOf("REFUSED") !== -1,
             "and says REFUSED in `basis` rather than pretending it weighted");
    } else {
      truthy(true, "every plan in the corpus declares variants — no refusal path to exercise here");
    }
  })();

  /* ============================================================
     9. WASTE — REGISTER A5 GUARD
     ============================================================ */

  suite("bom · waste policy is stated and the drop is not charged twice (guard A5)");
  (function () {
    var b = bomOf("starter-1210", "tx-i35");
    var w = b.waste;

    truthy(w.policy && w.policy.length > 60, "the waste POLICY is stated in full, not implied");
    eq(w.appliedPct, 0, "the applied waste percentage is ZERO — the drop is inside the stick");
    truthy(w.basis.indexOf("A5") !== -1, "the basis cites register A5 by name");
    truthy(w.basis.indexOf("dropHandling") !== -1, "the basis names the weight that replaced it");
    truthy(w.basis.indexOf("double count") !== -1, "the basis says what A5 actually was");
    near(w.dropHandlingRate, FM.weights.BASE.weights.dropHandling, 1e-12,
         "the dropHandling rate reported is the one weights.js carries, not a copy");
    eq(w.dropHandlingCls, "market", "dropHandling is declared [market]");

    /* THE GUARD. bf = cutBf + dropBf exactly: the drop is a SUBSET of what
       was bought, never an addition to it. If a waste multiplier ever
       creeps in, this identity is the first thing it breaks. */
    var broken = [], combos = 0;
    every(function (p, k) {
      combos++;
      var bb = FM.bom.build(FM.solver.solvePlan(p, k), {});
      var T = bb.totals, W = bb.waste;
      if (Math.abs(T.bf - (T.cutBf + T.dropBf)) > 1e-6) {
        broken.push(p.id + "/" + k.id + " bf != cutBf + dropBf");
      }
      if (W.appliedPct !== 0) broken.push(p.id + "/" + k.id + " applied a waste percentage");
      if (Math.abs(W.dropCheck.residualBf) > 1e-6) broken.push(p.id + "/" + k.id + " residual");
      /* material must be charged over the FULL stick and NOT again */
      bb.lines.forEach(function (g) {
        var expect = g.bf * g.bfUSD * (1 + g.cullRate);
        if (Math.abs(g.extUSD - expect) > 1e-6) {
          broken.push(p.id + "/" + k.id + " " + g.sku + " material != bf x $/bf x (1+cull)");
        }
        /* the drop must be inside bf, so cutBf can never exceed it */
        if (g.cutBf > g.bf + 1e-9) broken.push(p.id + "/" + k.id + " " + g.sku + " cutBf > bf");
        if (g.dropBf < -1e-9) broken.push(p.id + "/" + k.id + " " + g.sku + " negative drop");
      });
      /* dropHandling is never folded into the material total */
      if (Math.abs(T.usdWithHandling - (T.usd + T.dropHandlingUSD)) > 1e-9) {
        broken.push(p.id + "/" + k.id + " handling folded into material");
      }
      if (T.dropHandlingUSD > 0 && T.usd >= T.usdWithHandling) {
        broken.push(p.id + "/" + k.id + " handling silently inside usd");
      }
    });
    eq(combos, 30, "the A5 guard ran on all 30 combinations");
    eq(broken.length, 0, "bf = cutBf + dropBf, material is charged once over the full stick, " +
       "and drop handling is never inside it" +
       (broken.length ? " — " + broken.slice(0, 5).join("; ") : ""));

    /* the drop must be REPORTED, since it is deliberately not charged */
    near(w.dropPctOfPurchasedBf, (b.totals.dropBf / b.totals.bf) * 100, 1e-9,
         "the drop percentage reported is the measured one");
    truthy(w.dropPctOfPurchasedBf > 25,
           "and on this plan it is a big number (" + w.dropPctOfPurchasedBf.toFixed(1) +
           "%) that an estimator has a right to see rather than have smoothed away");
    truthy(w.dropLf > 0, "the drop is reported in linear feet too — the unit a cut list is in");
    eq(w.nesting.applied, false, "nesting is REPORTED, never applied");
    truthy(w.nesting.candidates.length > 0,
           "and on this plan there is a real nesting opportunity to report");
    truthy(w.nesting.usdSaved > 0 && w.roundingRules.length >= 4,
           "the un-taken saving is quantified and every rounding rule is stated");

    var txt = FM.bom.text(b);
    truthy(txt.indexOf("APPLIED WASTE 0.0%") !== -1, "the text leads the waste section with 0%");
    truthy(txt.indexOf("A5") !== -1, "the text carries the A5 provenance");
    truthy(txt.indexOf("NOT deducted from any total above") !== -1,
           "the text says the nesting saving was not deducted from anything");
  })();

  /* ============================================================
     10. PROVENANCE — money says what it is, everywhere
     ============================================================ */

  suite("bom · money is [market] and says so on every total that carries it");
  (function () {
    var b = bomOf("starter-1210", "tx-i35");
    eq(b.provenance.prices.indexOf("market") === 0, true, "prices are declared [market] first");
    truthy(b.provenance.prices.indexOf("NO CODE STANDING") !== -1,
           "and explicitly have no code standing");
    truthy(b.provenance.quantities.indexOf("derived") === 0, "quantities are declared derived");
    truthy(b.totals.moneyNote.indexOf("[market]") !== -1, "totals.moneyNote marks the money");
    truthy(b.totals.moneyNote.indexOf("MATERIAL ONLY") !== -1,
           "and says the total is material only, not a framing price");
    truthy(b.totals.modelledSelectionUSD > b.totals.usd,
           "the solver's selection cost is carried for tie-back and is larger than the material");
    truthy(b.totals.selectionTieBack.indexOf("not an invoice") !== -1,
           "and is explained as a ranking objective rather than silently differing");
    truthy(b.provenance.seal.indexOf("never stamps") !== -1, "the seal statement is present");

    var txt = FM.bom.text(b);
    ["Material, per house", "[market — placeholder]"].forEach(function (s) {
      truthy(txt.indexOf(s) !== -1, "the summary marks its money: \"" + s + "\"");
    });
    truthy(txt.indexOf("NOT A PURCHASE ORDER") !== -1, "the text refuses to be read as an order");
  })();

  /* ============================================================
     11. A PLAN WHERE ALMOST NOTHING IS THIS ENGINE'S MEMBER
     ============================================================ */

  suite("bom · a nearly-empty bill still reads as a document, not as a finished house");
  (function () {
    /* starter-1210 in fl-central: every first-floor exterior header is a
       concrete lintel in a block market, so ONE mark survives. The bill is
       one line. That is the truth about the product and it must not read
       like a cheap house. */
    var b = bomOf("starter-1210", "fl-central");
    eq(b.lines.length, 1, "only the treated entry beam survives in a concrete-block market");
    eq(b.lines[0].marks.join(","), "BM-ENT", "and it is BM-ENT");
    eq(b.counts.marksOutOfScope, 7, "seven marks are out of scope, named individually");
    truthy(b.excluded.length > b.lines.length * 5,
           "the excluded list dwarfs the bill, which is the honest shape of this answer");
    var txt = FM.bom.text(b);
    truthy(txt.indexOf("concrete lintel") !== -1 || txt.indexOf("lintel") !== -1,
           "the text says where the deleted headers' cost went — the mason's lintel schedule");
    truthy(txt.indexOf("NOT COMPLETE AND CANNOT BE") !== -1,
           "and states up front that this bill is not complete");
  })();
};

/* standalone runner, so the suite can be developed without touching
   test/run-tests.js while other agents are working in it */
if (require.main === module) {
  var FM = require("./harness.js").load(
    ["scope.js", "engine.js", "weights.js", "solver.js", "export.js", "bom.js"]);
  var pass = 0, fail = 0, current = "", failures = [];
  module.exports({
    suite: function (n) { current = n; console.log("\n" + n); },
    eq: function (a, e, m) {
      if (a === e) { pass++; console.log("  ✓ " + m); }
      else { fail++; failures.push(current + " :: " + m); console.log("  ✗ " + m +
        "\n      expected " + JSON.stringify(e) + ", got " + JSON.stringify(a)); }
    },
    near: function (a, e, tol, m) {
      if (typeof a === "number" && isFinite(a) && Math.abs(a - e) <= tol) { pass++; console.log("  ✓ " + m); }
      else { fail++; failures.push(current + " :: " + m); console.log("  ✗ " + m +
        "\n      expected " + e + " ± " + tol + ", got " + a); }
    },
    truthy: function (v, m) {
      if (v) { pass++; console.log("  ✓ " + m); }
      else { fail++; failures.push(current + " :: " + m); console.log("  ✗ " + m); }
    }
  }, FM);
  console.log("\n" + (fail ? "FAIL" : "PASS") + " — " + pass + " passed, " + fail + " failed");
  if (fail) { failures.forEach(function (f) { console.log("  · " + f); }); process.exit(1); }
}

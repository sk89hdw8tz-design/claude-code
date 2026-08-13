/* ============================================================
   Bill of materials — schedule → what you actually buy.

   Pipeline stage 5 (ARCHITECTURE.md). It consumes FM.solver.solvePlan()
   output and nothing else, and it computes NO capacity, NO load and NO
   member. Every member here was chosen and checked upstream.

   Four rulings shape this file, and each one was a choice that could
   have gone the lazy way:

   1. AN ESTIMATOR BUYS STICKS, NOT BOARD FEET.
      "How many 16-footers" is the first question in the room. A 13'-6"
      joist is bought as a 14 ft stick, and the 6 in of drop is inside
      the stick, already paid for. So the purchase line is keyed by
      (SKU, treatment, STOCK LENGTH) and the pieces-by-stock-length
      table is printed before anything else. FM.solver.stockLength() is
      the one and only source of that length — this file does not have
      a second opinion about it.

   2. WASTE IS NOT CHARGED TWICE.
      Register A5: costOf() once charged material over the full stock
      length AND charged the drop again as `waste: 1.10`. That was a
      double count, it was fixed in solver.js, and it must not come back
      in through the BOM. So: material is charged over the FULL stick,
      the applied waste percentage is ZERO, and the drop is REPORTED —
      in linear feet, in board feet, and as a share of what was bought —
      rather than added. `dropHandling` (a [market] weight) prices
      sorting and disposing of the offcut and is NOT lumber; it is
      carried on its own line and is never folded into the material
      total. An estimator who wants a 10% cover allowance can add one,
      knowing exactly what is and is not already in the number.

   3. TREATMENT IS PART OF THE SKU.
      weights.js keeps the treated and dry channels apart everywhere —
      STOCK.wet vs STOCK.dry, and the incising factor on the member
      itself. A BOM that prints "12 × 2x12 SYP #2" over a treated deck
      beam and a dry floor joist has flattened the one distinction that
      makes the output buyable. Treated and dry are always different
      lines, even at the same size, species, grade and length.

   4. THE EXCLUDED LIST IS THE HONEST HALF.
      A BOM that silently omits the girder reads as a complete order.
      Everything escalated, everything out of scope, and every whole
      CATEGORY this system does not size — connectors, hangers, straps,
      hold-downs, anchor bolts, sheathing, fasteners, blocking, rim
      board, subfloor, roofing, studs and jacks — is listed with a
      reason. In a wind-governed market the connection package is
      frequently more of the cost than the lumber priced here, and that
      sentence is printed rather than implied.

   Provenance, as everywhere in this product: QUANTITIES are `derived`
   and show their arithmetic in `basis`. PRICES are `market` placeholders
   with no code standing, and every total carrying money says so on the
   same line.
   ============================================================ */

(function () {
  "use strict";

  /* The bearing allowance inside FM.solver.stockLength(): it buys
     span + 0.5 ft so the member has bearing at both ends. Named here
     because the BOM has to PRINT the cut length, and a magic 0.5 in a
     basis string is exactly the kind of number this codebase refuses.
     If solver.js ever moves it, the self-check below fails loudly
     rather than printing a cut length that is quietly wrong. */
  var BEARING_ALLOWANCE_FT = 0.5;

  /* author-supplied strings (SKUs, mark ids, roles) are used as map
     keys throughout — a role named "constructor" must not pick up
     Object.prototype, and `groups["__proto__"] = []` must not vanish */
  function K(s) { return " " + String(s); }
  function hasK(o, s) { return Object.prototype.hasOwnProperty.call(o, K(s)); }
  function own(o, k) {
    return (o && Object.prototype.hasOwnProperty.call(o, k)) ? o[k] : undefined;
  }

  /* ---------------- text helpers (same shapes export.js uses) ---------------- */

  function rule(ch) { return new Array(79).join(ch || "="); }
  function pad(s, n) { s = String(s); while (s.length < n) s += " "; return s; }
  function lpad(s, n) { s = String(s); while (s.length < n) s = " " + s; return s; }
  function comma(v) {
    if (FM.comma) return FM.comma(v);
    if (v === null || v === undefined || !isFinite(v)) return "—";
    return String(Math.round(v)).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }
  function n2(v, d) {
    if (v === null || v === undefined || !isFinite(v)) return "—";
    return Number(v).toFixed(d === undefined ? 2 : d);
  }
  function usd(v) {
    if (v === null || v === undefined || !isFinite(v)) return "—";
    return "$" + comma2(v);
  }
  function comma2(v) {
    var s = Number(v).toFixed(2).split(".");
    return s[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",") + "." + s[1];
  }
  function wrap(text, width) {
    if (FM.scope && typeof FM.scope.wrap === "function") return FM.scope.wrap(text, width);
    var words = String(text).split(/\s+/), lines = [], line = "";
    width = width || 70;
    for (var i = 0; i < words.length; i++) {
      if (line && (line + " " + words[i]).length > width) { lines.push(line); line = ""; }
      line = line ? line + " " + words[i] : words[i];
    }
    if (line) lines.push(line);
    return lines;
  }
  function num(v) { return (v === null || v === undefined || !isFinite(Number(v))) ? 0 : Number(v); }

  /* ============================================================
     EXCLUSIONS THIS SYSTEM OWES THE READER REGARDLESS OF THE PLAN

     Not a disclaimer. Each entry is a thing an estimator must go and
     price somewhere else, named specifically enough that they can.
     `kind: "not-sized"` means the calc stack has no method for it at
     all — it is absent from the schedule as well as from this BOM.
     ============================================================ */

  var SYSTEM_EXCLUSIONS = [
    { what: "Connectors and framing hardware — joist and beam hangers, post caps and bases, " +
            "column caps, framing angles, ties, and the nails or structural screws specified " +
            "to each one",
      why: "calc-spec §8.17: no connection of any kind is designed by this engine. The support " +
           "REACTION is published on the schedule in pounds per bearing so a connector designer " +
           "can select from it — selecting the connector is a separate scope and a separate cost. " +
           "Nothing here is counted, sized or priced.",
      kind: "not-sized", cls: "derived" },

    { what: "Uplift straps, hurricane clips, hold-downs, shear-transfer straps and the continuous " +
            "load path from roof to foundation",
      why: "calc-spec §8.11 (no wind or uplift check) and §8.17 (no connection design). This is " +
           "the load path that governs the building in a coastal market, and this system does not " +
           "evaluate one link of it.",
      kind: "not-sized", cls: "derived" },

    { what: "Anchor bolts, hold-down anchors, their embedment, edge distance and the concrete " +
            "they land in",
      why: "Not designed (§8.17) and not counted. Foundation and its reinforcement are outside " +
           "this system entirely.",
      kind: "not-sized", cls: "derived" },

    { what: "Sheathing — roof, wall and floor panels, their thickness, span rating, edge blocking " +
            "and nailing pattern",
      why: "Never sized here. Panel dead weight is inside the ASSEMBLY psf takeoffs the loads come " +
           "from, so the sheathing is CARRIED as a load and never COUNTED as a material. It is one " +
           "of the largest single line items in a real framing package.",
      kind: "not-sized", cls: "derived" },

    { what: "Fasteners of every kind — nails, structural screws, powder-actuated pins, construction " +
            "adhesive, joist-hanger nails",
      why: "Not counted. There is no fastener schedule in this system and no nailing pattern is " +
           "specified for anything, including the members that ARE priced above.",
      kind: "not-sized", cls: "derived" },

    { what: "Blocking, bridging, squash blocks, bearing blocks, fire blocking and drywall backing",
      why: "Not sized and not counted. Blocking is also a stability assumption: a member printed as " +
           "`braced` on the schedule is relying on restraint that this BOM does not buy.",
      kind: "not-sized", cls: "derived" },

    { what: "Rim board, band joist, ledger boards and the ledger's fasteners",
      why: "Not sized and not counted. The ledger connection in particular is the single most " +
           "common deck failure and it is a §8.17 exclusion.",
      kind: "not-sized", cls: "derived" },

    { what: "Subfloor, decking boards, stair treads and underlayment",
      why: "Carried as dead load in the ASSEMBLY takeoff, never counted as material.",
      kind: "not-sized", cls: "derived" },

    { what: "Roofing — shingles, tile, metal panels, underlayment, drip edge, flashing, battens",
      why: "Carried as dead load (roof_shingle 15 psf, roof_tile 22 psf and so on, all [market] " +
           "takeoffs), never counted as material. The tile option that resizes members on this plan " +
           "buys no tile in this BOM.",
      kind: "not-sized", cls: "derived" },

    { what: "Wall framing — studs, top and bottom plates, the treated sill plate, king studs, and " +
            "THE JACK STUDS AND CRIPPLES UNDER EVERY HEADER PRICED ABOVE",
      why: "Not sized and not counted. Each header on the schedule declares a bearing length in " +
           "inches (1.5 in per jack stud), so the schedule states how many jacks each header needs " +
           "and this BOM buys none of them. A header line without its jacks is not a buildable " +
           "opening.",
      kind: "not-sized", cls: "derived" },

    { what: "Posts and columns, and their caps, bases and uplift anchorage",
      why: "AXIAL MEMBERS — calc-spec §4.10 specifies C_P and §8.20 evaluates no interaction " +
           "equation; engine.js implements neither. A post mark on the plan carries the beam " +
           "reaction this system does compute, but no post is sized, so none is bought.",
      kind: "not-sized", cls: "derived" },

    { what: "Roof and floor trusses, and girder trusses",
      why: "Manufactured components, engineered by the supplier as a deferred sealed submittal " +
           "(calc-spec §8.6, §8.19). On a production plan in these three states this is the whole " +
           "roof and it is a larger purchase order than everything above it.",
      kind: "not-sized", cls: "derived" },

    { what: "Engineered lumber — LVL, PSL, LSL, glulam, I-joists, open-web floor trusses — and " +
            "multi-ply built-up sawn members and steel beams",
      why: "calc-spec §8.6 and §8.19 put them out of scope. Every mark that escalates on strength " +
           "is normally answered by one of these in the market, so the escalations listed above are " +
           "not gaps in the house — they are purchases that must be priced from someone else's " +
           "design.",
      kind: "not-sized", cls: "derived" },

    { what: "Wall bracing, shear walls and portal frames (IRC R602.10 / engineered lateral system)",
      why: "No lateral system of any kind is evaluated (§8.11). The braced-wall panels, their " +
           "sheathing, their hold-downs and their anchorage are all unpriced here.",
      kind: "not-sized", cls: "derived" },

    { what: "Foundation — slab, footings, stem walls, reinforcing, and concrete lintels over " +
            "masonry openings",
      why: "Outside this system. In the two concrete-block Florida packs the first-floor exterior " +
           "headers are DELETED from the schedule as not-this-engine's-member — that opening still " +
           "has to be spanned, and the cost simply moves to the mason's lintel schedule.",
      kind: "not-sized", cls: "derived" },

    { what: "Preservative treatment specification — retention level, use category, incising, and " +
            "field end-cut treatment — and termite protection",
      why: "The BOM says TREATED or DRY because that is a different SKU at a different price and " +
           "a different stock channel. It does not specify a retention, a use category or an " +
           "AWPA standard, and it does not detect where code requires treatment.",
      kind: "not-sized", cls: "derived" },

    { what: "Delivery, yard fees, crane or boom time, cull-and-return handling beyond the modelled " +
            "cull rate, theft and damage allowance, and any waste allowance beyond the drop already " +
            "inside the sticks purchased",
      why: "Not modelled. See the WASTE AND DROP section: the applied waste percentage here is " +
           "ZERO by policy, and the drop is reported rather than charged.",
      kind: "not-sized", cls: "market" }
  ];

  function windExclusion(pack) {
    var governsWind = !!(pack && pack.governs === "wind");
    return {
      what: "THE CONNECTION PACKAGE, stated plainly: in a wind-governed market the straps, clips, " +
            "hold-downs and anchors are frequently MORE OF THE COST than the lumber priced above",
      why: (governsWind
              ? "THIS PACK DECLARES governs: \"wind\". "
              : "This pack declares governs: \"" + ((pack && pack.governs) || "not declared") +
                "\", so gravity is the stated driver here — but the sentence holds wherever uplift " +
                "or a windborne-debris region applies. ") +
           "The members above were checked for GRAVITY ONLY. On a coastal or high-wind plan the " +
           "dollars, the engineering and the inspection risk all concentrate in the connection " +
           "package, and this BOM contains none of it — not one strap, not one clip, not one " +
           "anchor bolt. Reading the total below as \"the structural cost of the house\" is the " +
           "specific mistake this line exists to prevent." +
           (governsWind && pack && pack.governsNote ? "  PACK NOTE — " + pack.governsNote : ""),
      kind: "not-sized", cls: "derived",
      severity: governsWind ? "critical" : "standard"
    };
  }

  /* ============================================================
     PIECE COUNTS

     MIRROR of solver.js's private pieceCount(). It is not exported, and
     the BOM cannot invent its own counting rule: a plan cost of
     $1,030.99 and a BOM of a different number of pieces is two answers
     to one question. Kept byte-comparable to the original and flagged
     here so the duplication is visible rather than forgotten.
     REQUEST ON RECORD: export FM.solver.pieceCount and delete this.
     ============================================================ */

  function pieceCountOf(m) {
    var row = m.unifiedTo || (m.solution && m.solution.pick);
    if (row && m.demand && m.demand.repetitive && m.mark.runFt && row.cand.spacing) {
      return Math.ceil(Number(m.mark.runFt) * 12 / row.cand.spacing) + 1;
    }
    return m.mark.count || 1;
  }

  function countBasisOf(m, pieces) {
    var row = m.unifiedTo || (m.solution && m.solution.pick);
    if (row && m.demand && m.demand.repetitive && m.mark.runFt && row.cand.spacing) {
      return "run " + n2(m.mark.runFt, 1) + " ft x 12 / " + row.cand.spacing +
             " in o.c. = " + n2(Number(m.mark.runFt) * 12 / row.cand.spacing, 2) +
             " bays, rounded UP to " + (pieces - 1) + " plus 1 closing member = " + pieces + " pc";
    }
    return "plan count for this mark = " + pieces + " pc (not derived from a run; the plan states it)";
  }

  /* Which procurement channel this member comes out of. Exactly the rule
     weights.js policyFor().priceOf uses — `treated || wet` picks
     STOCK.wet — so the BOM cannot disagree with the price it was given. */
  function treatedOf(d) { return !!(d && d.treated); }
  function channelOf(d) { return (d && (d.treated || d.wet)) ? "wet/treated" : "dry"; }
  function treatmentLabel(treated) { return treated ? "TREATED" : "dry"; }

  /* ============================================================
     ONE HOUSE
     ============================================================ */

  function perHouse(planResult, opts) {
    opts = opts || {};
    var pack = planResult.pack || {};
    var plan = planResult.plan || {};
    var groups = {}, order = [];
    var excluded = [];
    var selfChecks = [];
    var priced = 0;

    (planResult.marks || []).forEach(function (m) {
      var mk = m.mark || {};

      /* --- not this engine's member: trusses, posts, CMU lintels, underdetermined --- */
      if (m.notApplicable) {
        excluded.push({
          what: mk.id + " — " + (mk.label || "(no label)") +
                (mk.count ? "  x" + mk.count : ""),
          why: "OUT OF SCOPE [" + m.notApplicable.reason + "] — " +
               (m.notApplicable.note || "no note supplied by the schedule") +
               reactionSuffix(m.notApplicable.reactions),
          kind: "out-of-scope", markId: mk.id, reason: m.notApplicable.reason, cls: "derived"
        });
        return;
      }

      var row = m.unifiedTo || (m.solution && m.solution.pick);

      /* --- escalated: the schedule proposed no member, so there is nothing to buy --- */
      if (!row) {
        var s = m.solution || {};
        var ei = (FM.solver && FM.solver.escalationOf) ? FM.solver.escalationOf(s.status) : null;
        excluded.push({
          what: mk.id + " — " + (mk.label || "(no label)") +
                (mk.count ? "  x" + mk.count : "") +
                (isFinite(mk.span) ? "  span " + n2(mk.span, 2) + " ft" : ""),
          why: "ESCALATED — NO MEMBER WAS SELECTED [" + (s.status || "escalate") + "]" +
               (ei ? " · " + ei.short : "") +
               ".  WALL: " + ((s.note && s.note.wall) || "not stated") +
               "  NEXT: " + ((s.note && s.note.move) || "not stated") +
               (s.note && s.note.procurement ? "  MEMBER: " + s.note.procurement : "") +
               (s.note && s.note.outOfScope ? "  SCOPE: " + s.note.outOfScope : "") +
               "  Nothing is bought for this mark and nothing is priced — the opening or bay it " +
               "spans still exists and still has to be paid for.",
          kind: "escalated", markId: mk.id, status: s.status || "escalate", cls: "derived"
        });
        return;
      }

      /* --- a real, checked member: it becomes a purchase line --- */
      var cand = row.cand, cost = row.cost || {};
      var d = m.demand || {};
      var pieces = pieceCountOf(m);
      var sku = FM.solver.skuOf(cand);
      var treated = treatedOf(d);
      var stockFt = FM.solver.stockLength(d.span);
      var bfPerLf = FM.solver.boardFeetPerLF(cand.size);
      var cutFt = num(d.span) + BEARING_ALLOWANCE_FT;

      /* solver.costOf priced the very same stick. If the two ever disagree the
         BOM is describing a different purchase than the one that was costed,
         and that must surface as a defect rather than a rounding difference. */
      if (isFinite(cost.lengthFt) && Math.abs(cost.lengthFt - stockFt) > 1e-9) {
        selfChecks.push(mk.id + ": FM.solver.stockLength gives " + stockFt +
                        " ft but the costed stick was " + cost.lengthFt + " ft");
      }

      var bfPerPiece = bfPerLf * stockFt;
      var matPerPiece = num(cost.terms && cost.terms.material);
      var dropPerPiece = num(cost.terms && cost.terms.drop);

      var key = sku + "|" + (treated ? "T" : "D") + "|" + stockFt;
      if (!hasK(groups, key)) {
        groups[K(key)] = {
          sku: sku, size: cand.size, species: cand.species, grade: cand.grade,
          treatment: treatmentLabel(treated), treated: treated,
          channel: channelOf(d),
          stockLengthFt: stockFt, lengthFt: cutFt,
          bfPerLf: bfPerLf, bfPerPiece: bfPerPiece,
          bfUSD: num(cost.bfUSD), cullRate: num(cost.cullRate),
          availability: num(cost.availability),
          piecesPerHouse: 0, bf: 0, cutBf: 0, dropBf: 0, lf: 0,
          extUSD: 0, dropHandlingUSD: 0,
          marks: [], cuts: [], roles: {}, roleOrder: [],
          spacings: {}, wetService: 0, dryService: 0, unified: 0
        };
        order.push(key);
      }
      var g = groups[K(key)];
      g.piecesPerHouse += pieces;
      g.bf += bfPerPiece * pieces;
      g.cutBf += bfPerLf * cutFt * pieces;
      g.dropBf += bfPerLf * (stockFt - cutFt) * pieces;
      g.lf += stockFt * pieces;
      g.extUSD += matPerPiece * pieces;
      g.dropHandlingUSD += dropPerPiece * pieces;
      if (cutFt > g.lengthFt) g.lengthFt = cutFt;
      if (g.marks.indexOf(mk.id) === -1) g.marks.push(mk.id);
      if (d.wet) g.wetService++; else g.dryService++;
      if (m.unifiedTo) g.unified++;
      if (!hasK(g.roles, mk.role || "unclassified")) {
        g.roles[K(mk.role || "unclassified")] = 0;
        g.roleOrder.push(mk.role || "unclassified");
      }
      g.roles[K(mk.role || "unclassified")] += pieces;
      if (cand.spacing) g.spacings[K(String(cand.spacing))] = true;
      g.cuts.push({
        markId: mk.id, label: mk.label || "", role: mk.role || null,
        pieces: pieces, spanFt: num(d.span), cutLengthFt: cutFt,
        dropFt: stockFt - cutFt, spacingIn: cand.spacing || 0,
        unified: !!m.unifiedTo,
        countBasis: countBasisOf(m, pieces),
        dcr: isFinite(row.dcr) ? row.dcr : null,
        governing: row.governing || null
      });
      priced++;
    });

    /* ---- finish the lines ---- */
    var lines = order.map(function (key) {
      var g = groups[K(key)];
      g.unitUSD = g.piecesPerHouse > 0 ? g.extUSD / g.piecesPerHouse : 0;
      g.piecesPerStock = 1;
      /* what a yard-floor nest COULD get out of one stick — reported, never
         applied. Applying it would change a count silently and would also
         disagree with the cost the solver already published. */
      g.nestPerStock = g.lengthFt > 0 ? Math.floor(g.stockLengthFt / g.lengthFt) : 1;
      g.service = g.wetService && g.dryService ? "mixed"
                : (g.wetService ? "wet service" : "dry service");
      g.cls = "derived";
      g.priceCls = "market";
      g.marksLabel = g.marks.join(" + ");
      g.basis = lineBasis(g);
      /* a line is a plain record: no functions, so it survives JSON */
      delete g.roles;
      delete g.wetService;
      delete g.dryService;
      return g;
    });

    lines.sort(function (a, b) {
      if (a.size !== b.size) return a.size < b.size ? -1 : 1;
      if (a.treated !== b.treated) return a.treated ? 1 : -1;
      if (a.sku !== b.sku) return a.sku < b.sku ? -1 : 1;
      return a.stockLengthFt - b.stockLengthFt;
    });

    /* ---- excluded: the plan's own marks, then the whole categories ---- */
    excluded.push(windExclusion(pack));
    SYSTEM_EXCLUSIONS.forEach(function (e) {
      excluded.push({ what: e.what, why: e.why, kind: e.kind, cls: e.cls });
    });

    var totals = totalsOf(lines, planResult);
    var waste = wasteOf(lines, totals, planResult);
    return {
      lines: lines, totals: totals, excluded: excluded, waste: waste,
      pricedMarks: priced, selfChecks: selfChecks
    };
  }

  function reactionSuffix(reactions) {
    if (!reactions || !reactions.length) return "";
    var parts = reactions.map(function (rx) {
      return rx.id + ": " + (rx.perBearingLb === null
        ? "no reaction published — " + (rx.why || "not computed")
        : comma(rx.perBearingLb) + " lb per bearing" + (rx.combo ? " (" + rx.combo + ")" : ""));
    });
    return "  DESIGN LOAD BORROWED FROM THIS RUN — " + parts.join("; ") +
           ". The load is published; the member and its connections are not.";
  }

  function lineBasis(g) {
    var per = g.cuts.map(function (c) {
      return c.markId + " " + c.pieces + " pc (" + c.countBasis + "; span " +
             n2(c.spanFt, 2) + " ft + " + n2(BEARING_ALLOWANCE_FT, 2) + " ft bearing = cut " +
             n2(c.cutLengthFt, 2) + " ft, drop " + n2(c.dropFt, 2) + " ft" +
             (c.unified ? "; RAISED BY SKU UNIFICATION" : "") + ")";
    }).join(" | ");
    return "PIECES [derived] " + per + " → " + g.piecesPerHouse + " pc. " +
           "STOCK [derived] FM.solver.stockLength(span) = " + n2(g.stockLengthFt, 0) +
           " ft — even 2 ft lengths, minimum 8 ft; one stick per piece, no nesting applied" +
           (g.nestPerStock > 1 ? " (a " + g.stockLengthFt + " ft stick could geometrically yield " +
            g.nestPerStock + " of these cuts — NOT taken, see WASTE)" : "") + ". " +
           "BOARD FEET [derived] FM.solver.boardFeetPerLF(" + g.size + ") = " +
           n2(g.bfPerLf, 3) + " bf/lf x " + n2(g.stockLengthFt, 0) + " ft = " +
           n2(g.bfPerPiece, 3) + " bf/pc x " + g.piecesPerHouse + " pc = " + n2(g.bf, 2) +
           " bf purchased (" + n2(g.cutBf, 2) + " bf in the members, " + n2(g.dropBf, 2) +
           " bf drop, already inside the sticks bought). " +
           "PRICE [market — placeholder, no code standing] $" + n2(g.bfUSD, 3) + "/bf x " +
           n2(g.bfPerPiece, 3) + " bf x (1 + " + n2(g.cullRate, 3) + " cull) = " +
           usd(g.unitUSD) + "/pc x " + g.piecesPerHouse + " pc = " + usd(g.extUSD) + ". " +
           "Availability of this size in the " + g.channel + " channel: " +
           n2(g.availability, 3) + " [market].";
  }

  function totalsOf(lines, planResult) {
    var t = {
      bf: 0, cutBf: 0, dropBf: 0, lf: 0, pieces: 0, usd: 0, dropHandlingUSD: 0,
      byCategory: {}, byCategoryOrder: [],
      bySku: {}, bySkuOrder: [],
      byStockLength: {}, byStockLengthOrder: [],
      lineCount: lines.length, skuCount: 0
    };
    lines.forEach(function (g) {
      t.bf += g.bf; t.cutBf += g.cutBf; t.dropBf += g.dropBf;
      t.lf += g.lf; t.pieces += g.piecesPerHouse;
      t.usd += g.extUSD; t.dropHandlingUSD += g.dropHandlingUSD;

      var skuKey = g.sku + " · " + g.treatment;
      if (!hasK(t.bySku, skuKey)) {
        t.bySku[K(skuKey)] = { sku: g.sku, treatment: g.treatment, pieces: 0, bf: 0, usd: 0,
                               lengths: {}, lengthOrder: [], marks: [] };
        t.bySkuOrder.push(skuKey);
      }
      var s = t.bySku[K(skuKey)];
      s.pieces += g.piecesPerHouse; s.bf += g.bf; s.usd += g.extUSD;
      if (!hasK(s.lengths, String(g.stockLengthFt))) {
        s.lengths[K(String(g.stockLengthFt))] = 0;
        s.lengthOrder.push(g.stockLengthFt);
      }
      s.lengths[K(String(g.stockLengthFt))] += g.piecesPerHouse;
      g.marks.forEach(function (id) { if (s.marks.indexOf(id) === -1) s.marks.push(id); });

      var lk = String(g.stockLengthFt);
      if (!hasK(t.byStockLength, lk)) {
        t.byStockLength[K(lk)] = { stockLengthFt: g.stockLengthFt, pieces: 0, bf: 0, usd: 0, skus: [] };
        t.byStockLengthOrder.push(g.stockLengthFt);
      }
      var bl = t.byStockLength[K(lk)];
      bl.pieces += g.piecesPerHouse; bl.bf += g.bf; bl.usd += g.extUSD;
      if (bl.skus.indexOf(g.sku) === -1) bl.skus.push(g.sku);

      g.cuts.forEach(function (c) {
        var r = c.role || "unclassified";
        if (!hasK(t.byCategory, r)) {
          t.byCategory[K(r)] = { role: r, pieces: 0, bf: 0, usd: 0, marks: [] };
          t.byCategoryOrder.push(r);
        }
        var cat = t.byCategory[K(r)];
        var share = g.piecesPerHouse > 0 ? c.pieces / g.piecesPerHouse : 0;
        cat.pieces += c.pieces;
        cat.bf += g.bf * share;
        cat.usd += g.extUSD * share;
        if (cat.marks.indexOf(c.markId) === -1) cat.marks.push(c.markId);
      });
    });
    t.skuCount = t.bySkuOrder.length;
    t.byStockLengthOrder.sort(function (a, b) { return a - b; });
    t.usdWithHandling = t.usd + t.dropHandlingUSD;
    t.modelledSelectionUSD = (planResult && planResult.rollup && isFinite(planResult.rollup.lumberUSD))
      ? planResult.rollup.lumberUSD : null;
    t.moneyNote =
      "EVERY DOLLAR ON THIS BOM IS [market] — a firm placeholder with NO CODE STANDING. " +
      "`usd` is MATERIAL ONLY: purchased board feet x the pack's $/bf for that species and grade " +
      "x (1 + cull rate), over the full stock length. It excludes labor, delivery, tax and every " +
      "category in the EXCLUDED list. `dropHandlingUSD` is NOT lumber — it is the [market] " +
      "`dropHandling` weight pricing the sorting and disposal of the offcut, carried on its own " +
      "line so it can never be mistaken for a waste allowance on the material.";
    t.selectionTieBack =
      "`modelledSelectionUSD` is FM.solver's rollup.lumberUSD — the SELECTION objective, which " +
      "adds labor, a depth-cost term, an availability penalty and an unsourced-C_F risk term to " +
      "the same material. It ranks members; it is not an invoice, and it is deliberately not the " +
      "BOM total. The difference between the two numbers is those non-material weights.";
    t.cls = "derived";
    return t;
  }

  /* ============================================================
     WASTE — register A5 lives here

     A5 (MAJOR): costOf() charged material over the full stock length AND
     charged the drop again as a `waste: 1.10` weight. Double count. Fixed
     in solver.js; `dropHandling` now prices only the handling of the
     offcut, net of salvage, and is explicitly NOT an estimating waste
     factor. The BOM is the natural place to reintroduce that bug — a
     "×1.10 for waste" on top of stock lengths is the most ordinary line
     in the estimating world — so the policy is written down, the applied
     percentage is zero, and the drop is measured and printed instead.
     ============================================================ */

  function wasteOf(lines, totals, planResult) {
    var w = (planResult && planResult.policy && planResult.policy.weights) || {};
    var dropLf = 0, nestable = [];
    lines.forEach(function (g) {
      dropLf += (g.stockLengthFt - g.lengthFt) * g.piecesPerHouse;
      if (g.nestPerStock > 1) {
        nestable.push({
          sku: g.sku, treatment: g.treatment, stockLengthFt: g.stockLengthFt,
          cutLengthFt: g.lengthFt, pieces: g.piecesPerHouse, couldYield: g.nestPerStock,
          sticksIfNested: Math.ceil(g.piecesPerHouse / g.nestPerStock),
          sticksAsBought: g.piecesPerHouse
        });
      }
    });
    var pct = totals.bf > 0 ? (totals.dropBf / totals.bf) * 100 : 0;
    return {
      policy: "FULL-STICK PURCHASE, ZERO ADDED WASTE. One stock stick is bought per piece, at the " +
              "length FM.solver.stockLength() returns (span + 0.5 ft bearing, rounded up to an even " +
              "2 ft length, minimum 8 ft). Material is charged over the FULL stick because that is " +
              "what leaves the yard. The offcut is therefore ALREADY PAID FOR inside the line above " +
              "it, and no waste multiplier is applied on top of it.",
      appliedPct: 0,
      appliedPctCls: "derived",
      basis: "Register A5 (MAJOR): the objective function once charged material over the full stock " +
             "length AND charged the drop a second time through a weight named `waste: 1.10`. That " +
             "was a double count. It was fixed in solver.js and the weight was renamed " +
             "`dropHandling` (" + n2(w.dropHandling, 3) + ", [market]), which prices sorting, " +
             "stacking and disposing of the offcut NET OF SALVAGE and is documented in weights.js " +
             "as explicitly NOT an estimating waste factor. This BOM applies 0% waste for exactly " +
             "that reason: adding a percentage here would restore A5 through the back door. The " +
             "drop is instead MEASURED and reported below, so an estimator can see the real number " +
             "and add a cover allowance deliberately if the firm wants one.",
      guard: "A5 — the drop must appear ONCE, inside the purchased stick, and never again as a " +
             "percentage. dropBf is a SUBSET of bf, not an addition to it: bf = cutBf + dropBf.",
      purchasedBf: totals.bf,
      inMembersBf: totals.cutBf,
      dropBf: totals.dropBf,
      dropLf: dropLf,
      dropPctOfPurchasedBf: pct,
      dropCheck: {
        identity: "bf = cutBf + dropBf",
        residualBf: totals.bf - (totals.cutBf + totals.dropBf)
      },
      dropHandlingRate: isFinite(w.dropHandling) ? w.dropHandling : null,
      dropHandlingCls: "market",
      dropHandlingUSD: totals.dropHandlingUSD,
      dropHandlingNote: "Charged once, on its own line, and never inside `usd`. It is a handling " +
                        "cost, not lumber.",
      nesting: {
        candidates: nestable,
        note: nestable.length
          ? nestable.length + " line(s) have a cut short enough that a stick could geometrically " +
            "yield more than one piece. THIS BOM DOES NOT NEST: it buys one stick per piece, which " +
            "is conservative and matches the cost the solver published. Nesting is a yard-floor " +
            "optimisation that depends on the cut list and the saw, and taking it here would " +
            "silently change a piece count. The opportunity is reported so it can be captured " +
            "deliberately."
          : "No line has a cut short enough for a second piece out of one stick."
      },
      roundingRules: [
        "Repetitive piece counts round UP: ceil(run x 12 / spacing) + 1, one closing member. " +
          "This is the solver's own rule, mirrored, not a BOM invention.",
        "Stock lengths round UP to an even 2 ft, minimum 8 ft (FM.solver.stockLength).",
        "NOTHING is rounded to a bundle, a lift or a unit-of-sale. If your yard sells 2x lumber " +
          "in banded units, that rounding is NOT applied here and will add pieces.",
        "Per-community piece counts are an EXPECTED VALUE and can be fractional; the whole-stick " +
          "buy is reported separately as the ceiling of that expectation, and the rule is stated " +
          "on the line."
      ]
    };
  }

  /* ============================================================
     PER LOT / PER COMMUNITY

     A tract plan is built sixty or two hundred times. Multiplying by
     plan.lots is the base answer and it is honest as long as it says
     that every lot is assumed to be the stamped base case.

     It usually is not. Elevation C of the starter plan DELETES the
     garage header and ADDS a carport beam on a quarter of the lots. So
     when the caller asks for it, the community quantity is the take-rate
     weighted expectation over the buildable configurations, using
     FM.weights.variantsFor() / planForVariant() and the solver
     unmodified.

     The weighting arithmetic, stated rather than assumed:
       weights.js gives INCLUSIVE shares — descriptorFor()'s takeRate is
       "the share of lots that include ALL of these parts", so summing
       the combinations double-counts massively. The share of lots built
       EXACTLY one way is
            P = take(elevation) x Π take(o) x Π (1 - take(o))
                                 o taken       o offered, not taken
       under the same independence assumption weights.js already declares
       for its own combination rates. Those probabilities must sum to
       1.000 across the configuration space. IF THEY DO NOT, the
       weighting is refused and the base case is reported instead, with
       the reason in `basis` — a fudged expectation is worse than an
       honest base.
     ============================================================ */

  function perLotOf(house, lots) {
    return {
      lots: 1,
      pieces: house.totals.pieces,
      bf: house.totals.bf,
      lf: house.totals.lf,
      usd: house.totals.usd,
      dropHandlingUSD: house.totals.dropHandlingUSD,
      byStockLength: house.totals.byStockLength,
      byStockLengthOrder: house.totals.byStockLengthOrder,
      cls: "derived",
      basis: "One house, as solved: " + house.totals.pieces + " pieces / " +
             n2(house.totals.bf, 2) + " bf / " + usd(house.totals.usd) +
             " of material [market]. This is the per-lot column every community number below " +
             "multiplies. It covers " + house.pricedMarks + " sized mark(s) and NONE of the " +
             "EXCLUDED list.",
      lotsOnPlan: lots
    };
  }

  function baseCommunity(house, lots, why) {
    var scale = isFinite(lots) ? lots : null;
    var mul = function (v) { return scale === null ? null : v * scale; };
    var byLen = {}, order = [];
    house.totals.byStockLengthOrder.forEach(function (L) {
      var src = house.totals.byStockLength[K(String(L))];
      byLen[K(String(L))] = {
        stockLengthFt: L,
        pieces: mul(src.pieces), bf: mul(src.bf), usd: mul(src.usd), skus: src.skus
      };
      order.push(L);
    });
    return {
      lots: scale,
      weighted: false,
      pieces: mul(house.totals.pieces),
      bf: mul(house.totals.bf),
      lf: mul(house.totals.lf),
      usd: mul(house.totals.usd),
      dropHandlingUSD: mul(house.totals.dropHandlingUSD),
      byStockLength: byLen,
      byStockLengthOrder: order,
      lines: house.lines.map(function (g) {
        return { sku: g.sku, treatment: g.treatment, stockLengthFt: g.stockLengthFt,
                 pieces: mul(g.piecesPerHouse), piecesExpectedPerLot: g.piecesPerHouse,
                 bf: mul(g.bf), usd: mul(g.extUSD), marks: g.marks };
      }),
      cls: "derived",
      basis: "BASE CASE x LOTS — per-lot quantities multiplied by " +
             (scale === null ? "an undeclared lot count (plan.lots is missing, so no community " +
              "quantity is stated; the fields are null rather than guessed)" : comma(scale) +
              " lots") + ". " +
             "EVERY LOT IS ASSUMED TO BE THE STAMPED BASE CASE. " + why +
             " Lot counts are [market] planning figures from the plan record, not contracts.",
      takeRateBasis: null
    };
  }

  /* the configuration space and its exclusive probabilities, or a refusal */
  function configurations(masterPlan) {
    if (!FM.weights || typeof FM.weights.variantsFor !== "function" ||
        typeof FM.weights.planForVariant !== "function") {
      return { ok: false, why: "FM.weights.variantsFor / planForVariant are not available in this build." };
    }
    var vs;
    try { vs = FM.weights.variantsFor(masterPlan, { combos: "all" }); }
    catch (e) { return { ok: false, why: "variantsFor() threw: " + (e && e.message) }; }

    if (!vs.declaresVariants) {
      return { ok: false, why: "this plan declares no elevations or options, so there is no take " +
                               "rate to weight by — the base case IS every lot." };
    }
    var rateOf = {}, offered = {};
    vs.options.forEach(function (o) {
      rateOf[K(o.id)] = Number(o.takeRate);
      if (o.requiresElevation || o.excludes) offered[K(o.id)] = true;
    });
    if (Object.keys(offered).length) {
      return { ok: false, why: "one or more options declare `requiresElevation` or `excludes`, so " +
               "the configuration space is not a clean product of independent attach rates and the " +
               "exclusive probabilities cannot be derived from the declared rates alone." };
    }
    var elevRate = {};
    vs.elevations.forEach(function (e) { elevRate[K(e.id)] = Number(e.takeRate); });
    var allOptionIds = vs.options.map(function (o) { return o.id; });

    var configs = [], total = 0, bad = null;
    vs.combinations.forEach(function (c) {
      var p = elevRate[K(c.elevationId)];
      if (!isFinite(p)) { bad = "elevation " + c.elevationId + " has no numeric takeRate"; return; }
      var taken = {};
      (c.optionIds || []).forEach(function (id) { taken[K(id)] = true; });
      allOptionIds.forEach(function (id) {
        var r = rateOf[K(id)];
        if (!isFinite(r)) { bad = "option " + id + " has no numeric takeRate"; return; }
        p *= hasK(taken, id) ? r : (1 - r);
      });
      if (bad) return;
      configs.push({ id: c.id, label: c.label, elevationId: c.elevationId,
                     optionIds: c.optionIds || [], isBase: !!c.isBase, p: p });
      total += p;
    });
    if (bad) return { ok: false, why: bad };
    if (!configs.length) return { ok: false, why: "variantsFor() returned no combinations." };
    if (Math.abs(total - 1) > 1e-6) {
      return { ok: false, why: "the exclusive configuration probabilities sum to " + n2(total, 6) +
               ", not 1.000000 — the declared elevation mix and option attach rates do not span " +
               "the buildable set, so a weighted community quantity would be arithmetically wrong. " +
               "Refusing to weight rather than normalising a number nobody checked." };
    }
    return { ok: true, configs: configs, total: total, lots: vs.lots,
             note: vs.note, count: configs.length };
  }

  function weightedCommunity(planResult, house, lots, opts) {
    var plan = planResult.plan || {};
    var pack = planResult.pack;
    var master = plan.ofPlan ? (FM.weights.planById ? FM.weights.planById(plan.ofPlan) : null) : plan;
    if (!master) {
      return baseCommunity(house, lots,
        "TAKE-RATE WEIGHTING WAS REQUESTED AND REFUSED: this result was solved for variant \"" +
        (plan.variant ? plan.variant.id : "?") + "\" of plan \"" + plan.ofPlan +
        "\" and the master plan record could not be found, so the elevation mix is not available.");
    }
    var space = configurations(master);
    if (!space.ok) {
      return baseCommunity(house, lots,
        "TAKE-RATE WEIGHTING WAS REQUESTED AND REFUSED — " + space.why +
        " The base case is reported instead. This is stated rather than fudged: a weighted number " +
        "that does not reconcile with the declared rates is worse than an unweighted one that says " +
        "what it is.");
    }

    var scale = isFinite(lots) ? lots : (isFinite(master.lots) ? master.lots : null);
    if (scale === null) {
      return baseCommunity(house, lots,
        "TAKE-RATE WEIGHTING WAS REQUESTED AND REFUSED: the plan declares no lot count.");
    }

    var acc = {}, order = [], failures = [];
    var pieces = 0, bf = 0, lf = 0, dollars = 0, handling = 0;
    var perConfig = [];

    space.configs.forEach(function (cfg) {
      var vp, vres, vh;
      try {
        vp = FM.weights.planForVariant(master, cfg.id);
        vres = FM.solver.solvePlan(vp, pack);
        vh = perHouse(vres, opts);
      } catch (e) {
        failures.push(cfg.id + ": " + (e && e.message ? e.message : String(e)));
        return;
      }
      var lotsHere = cfg.p * scale;
      pieces += vh.totals.pieces * lotsHere;
      bf += vh.totals.bf * lotsHere;
      lf += vh.totals.lf * lotsHere;
      dollars += vh.totals.usd * lotsHere;
      handling += vh.totals.dropHandlingUSD * lotsHere;
      perConfig.push({
        id: cfg.id, label: cfg.label, p: cfg.p, isBase: cfg.isBase,
        lotsExpected: lotsHere,
        piecesPerLot: vh.totals.pieces, bfPerLot: vh.totals.bf, usdPerLot: vh.totals.usd,
        escalated: vh.excluded.filter(function (x) { return x.kind === "escalated"; }).length
      });
      vh.lines.forEach(function (g) {
        var key = g.sku + "|" + (g.treated ? "T" : "D") + "|" + g.stockLengthFt;
        if (!hasK(acc, key)) {
          acc[K(key)] = { sku: g.sku, size: g.size, species: g.species, grade: g.grade,
                          treatment: g.treatment, stockLengthFt: g.stockLengthFt,
                          piecesExpected: 0, bf: 0, usd: 0, marks: [], onLotsExpected: 0 };
          order.push(key);
        }
        var a = acc[K(key)];
        a.piecesExpected += g.piecesPerHouse * lotsHere;
        a.bf += g.bf * lotsHere;
        a.usd += g.extUSD * lotsHere;
        a.onLotsExpected += lotsHere;
        g.marks.forEach(function (id) { if (a.marks.indexOf(id) === -1) a.marks.push(id); });
      });
    });

    if (failures.length && !perConfig.length) {
      return baseCommunity(house, lots,
        "TAKE-RATE WEIGHTING WAS REQUESTED AND REFUSED: every configuration failed to solve — " +
        failures.join("; "));
    }

    var lines = order.map(function (key) {
      var a = acc[K(key)];
      a.pieces = Math.ceil(a.piecesExpected - 1e-9);
      a.roundingRule = "pieces = ceil(expected) — a whole-stick buy. Expected value " +
                       n2(a.piecesExpected, 3) + " is carried beside it so the rounding is visible.";
      a.marksLabel = a.marks.join(" + ");
      return a;
    });
    lines.sort(function (a, b) {
      if (a.size !== b.size) return a.size < b.size ? -1 : 1;
      if (a.treatment !== b.treatment) return a.treatment < b.treatment ? -1 : 1;
      if (a.sku !== b.sku) return a.sku < b.sku ? -1 : 1;
      return a.stockLengthFt - b.stockLengthFt;
    });

    var byLen = {}, lenOrder = [];
    lines.forEach(function (a) {
      var lk = String(a.stockLengthFt);
      if (!hasK(byLen, lk)) {
        byLen[K(lk)] = { stockLengthFt: a.stockLengthFt, pieces: 0, piecesExpected: 0, bf: 0, usd: 0, skus: [] };
        lenOrder.push(a.stockLengthFt);
      }
      var b = byLen[K(lk)];
      b.piecesExpected += a.piecesExpected;
      b.pieces += a.pieces;
      b.bf += a.bf; b.usd += a.usd;
      if (b.skus.indexOf(a.sku) === -1) b.skus.push(a.sku);
    });
    lenOrder.sort(function (a, b) { return a - b; });

    return {
      lots: scale,
      weighted: true,
      configurations: space.count,
      solvedConfigurations: perConfig.length,
      failedConfigurations: failures,
      perConfiguration: perConfig,
      piecesExpected: pieces,
      pieces: Math.ceil(pieces - 1e-9),
      bf: bf, lf: lf, usd: dollars, dropHandlingUSD: handling,
      byStockLength: byLen, byStockLengthOrder: lenOrder,
      lines: lines,
      cls: "derived",
      basis: "TAKE-RATE WEIGHTED EXPECTATION over " + perConfig.length + " of " + space.count +
             " buildable configuration(s) of the master set, each solved through FM.solver.solvePlan() " +
             "on FM.weights.planForVariant() — the solver is unmodified and does not know variants " +
             "exist. Quantity = Σ P(config) x qty(config) x " + comma(scale) + " lots." +
             (failures.length ? "  " + failures.length + " configuration(s) FAILED TO SOLVE and " +
              "are excluded from the expectation, which therefore understates the community: " +
              failures.join("; ") + "." : ""),
      takeRateBasis: "P(config) = takeRate(elevation) x Π takeRate(o) over options taken x " +
                     "Π (1 - takeRate(o)) over options offered and not taken. weights.js's own " +
                     "combination takeRate is an INCLUSIVE share (\"the share of lots that include " +
                     "ALL of these parts\"), so summing it across combinations double-counts; this " +
                     "is the exclusive share, derived from the same declared rates under the same " +
                     "independence assumption weights.js declares. The probabilities were checked " +
                     "to sum to 1.000000 before any quantity was weighted — the weighting is " +
                     "REFUSED and the base case reported if they do not. Every take rate is " +
                     "[market]: a commercial estimate with NO code standing, and a community " +
                     "quantity built on it is a planning number, not a purchase order.",
      takeRateCls: "market"
    };
  }

  /* ============================================================
     THE ENTRY POINT
     ============================================================ */

  function build(planResult, opts) {
    opts = opts || {};
    if (!planResult || !planResult.marks) {
      throw new Error("FM.bom.build needs the output of FM.solver.solvePlan(plan, pack)");
    }
    if (!FM.solver || !FM.solver.stockLength || !FM.solver.boardFeetPerLF || !FM.solver.skuOf) {
      throw new Error("FM.bom.build requires FM.solver (stockLength, boardFeetPerLF, skuOf)");
    }
    var plan = planResult.plan || {};
    var pack = planResult.pack || {};
    var house = perHouse(planResult, opts);
    var lots = opts.lots !== undefined ? opts.lots : plan.lots;

    var wantWeighted = !!(opts.takeRates || opts.weighted ||
                          opts.perCommunity === "takeRates" || opts.perCommunity === "variants");
    var perCommunity = wantWeighted
      ? weightedCommunity(planResult, house, lots, opts)
      : baseCommunity(house, lots,
          "Take-rate weighting was NOT requested (pass { takeRates: true } for the expectation " +
          "across the master set's elevations and options). Where the plan declares elevations " +
          "that add or delete a member — a carport in place of a garage, a deeper porch — this " +
          "number is the base elevation on every lot and is wrong for the lots that are not it.");

    return {
      lines: house.lines,
      totals: house.totals,
      perLot: perLotOf(house, lots),
      perCommunity: perCommunity,
      excluded: house.excluded,
      waste: house.waste,

      /* context a renderer needs and a reviewer will ask for */
      plan: { id: plan.id, name: plan.name, summary: plan.summary, lots: plan.lots,
              ofPlan: plan.ofPlan || null,
              variant: plan.variant ? { id: plan.variant.id, label: plan.variant.label,
                                        isBase: !!plan.variant.isBase,
                                        takeRate: plan.variant.takeRate } : null },
      pack: { id: pack.id, name: pack.name, markets: pack.markets, governs: pack.governs || null,
              exteriorWall: pack.exteriorWall || null },
      counts: {
        marksOnPlan: (planResult.marks || []).length,
        marksPriced: house.pricedMarks,
        marksEscalated: house.excluded.filter(function (e) { return e.kind === "escalated"; }).length,
        marksOutOfScope: house.excluded.filter(function (e) { return e.kind === "out-of-scope"; }).length,
        categoriesNotSized: house.excluded.filter(function (e) { return e.kind === "not-sized"; }).length
      },
      complete: false,
      completeNote:
        "A BILL OF MATERIALS FROM THIS SYSTEM IS NEVER COMPLETE, and `complete` is hard-coded false " +
        "for that reason. It prices the simple-span solid-sawn members the engine sized and nothing " +
        "else. Read EXCLUDED before reading any total.",
      selfChecks: house.selfChecks,
      at: opts.at || null,
      cls: "derived",
      provenance: {
        quantities: "derived — every count, length and board-foot figure shows its arithmetic in " +
                    "the line's `basis`. Stock lengths come from FM.solver.stockLength(); board " +
                    "feet from FM.solver.boardFeetPerLF(); piece counts mirror the solver's own " +
                    "rule; the SKU string is FM.solver.skuOf().",
        prices: "market — $/bf, cull rates, availability, dropHandling, lot counts and take rates " +
                "are firm placeholders with NO CODE STANDING. They rank members and estimate " +
                "purchases; they cannot make a member pass and they are not a quotation.",
        code: "none — this module reads no code value and states no code requirement. The code " +
              "basis of the MEMBERS is on the schedule (FM.scheduleText), not here.",
        seal: "NOT SEALED ENGINEERING. This is a quantity takeoff of a member schedule that a " +
              "licensed engineer must review. The software never stamps."
      }
    };
  }

  /* ============================================================
     TEXT RENDERER — the house style of export.js, so planset.js can
     drop it onto sheet S4.0 without reformatting it.
     ============================================================ */

  function text(bom, opts) {
    opts = opts || {};
    var L = [];
    function say(s) { L.push(s === undefined ? "" : s); }
    function block(title) { say(); say(rule("=")); say(title); say(rule("=")); say(); }
    function para(t, width, indent) {
      wrap(t, width || 74).forEach(function (x) { say((indent === undefined ? "  " : indent) + x); });
    }

    var t = bom.totals, p = bom.pack || {}, pl = bom.plan || {};

    /* ---- header ---- */
    say("FIRMARK — BILL OF MATERIALS (beta)");
    say(rule("="));
    say("Plan          : " + (pl.name || pl.id || "—") + (pl.summary ? " — " + pl.summary : ""));
    say("Region pack   : " + (p.name || p.id || "—") + (p.markets ? " · " + p.markets : ""));
    if (pl.variant) {
      say("Variant       : " + (pl.variant.label || pl.variant.id) +
          (pl.variant.isBase ? "   [the declared base case]" : "") +
          (isFinite(pl.variant.takeRate) ? "   take " + n2(pl.variant.takeRate * 100, 1) + "% [market]" : ""));
    } else if (pl.ofPlan) {
      say("Variant       : a variant of " + pl.ofPlan + ", descriptor not carried");
    }
    say("Scope         : simple-span solid-sawn members from the member schedule, ONLY");
    if (bom.at || opts.at) say("Generated     : " + (opts.at || bom.at));
    say();
    say("NOT SEALED ENGINEERING AND NOT A PURCHASE ORDER. This is a quantity takeoff");
    say("of a member schedule a licensed engineer must still review. Prices are");
    say("[market] placeholders with no code standing. The software never stamps.");
    say();
    say("** THIS BILL OF MATERIALS IS NOT COMPLETE AND CANNOT BE. **");
    para(bom.completeNote);
    if (p.governs === "wind") {
      say();
      say(rule("!"));
      say("!! WIND GOVERNS IN THIS MARKET — THE CONNECTION PACKAGE IS NOT PRICED HERE");
      say(rule("!"));
      para("The members below were checked for gravity only. Straps, clips, hold-downs " +
           "and anchors are frequently more of the cost than this lumber, and not one of " +
           "them is in this document. See EXCLUDED.");
    }
    if (bom.selfChecks && bom.selfChecks.length) {
      say();
      say(rule("!"));
      say("!! SELF-CHECK FAILED — " + bom.selfChecks.length + " ITEM(S). DO NOT ISSUE.");
      say(rule("!"));
      bom.selfChecks.forEach(function (s) { para(s); });
    }

    /* ---- summary ---- */
    block("SUMMARY");
    say("  Marks on the plan            : " + bom.counts.marksOnPlan);
    say("  Marks priced below           : " + bom.counts.marksPriced);
    say("  Marks ESCALATED (no member)  : " + bom.counts.marksEscalated);
    say("  Marks OUT OF SCOPE           : " + bom.counts.marksOutOfScope);
    say("  Categories not sized at all  : " + bom.counts.categoriesNotSized);
    say();
    say("  Purchase lines               : " + t.lineCount +
        "   (a line is one SKU at one stock length)");
    say("  Distinct SKUs                : " + t.skuCount);
    say("  Pieces per house             : " + comma(t.pieces));
    say("  Board feet purchased         : " + n2(t.bf, 2) +
        "   (" + n2(t.cutBf, 2) + " in the members, " + n2(t.dropBf, 2) + " drop)");
    say("  Material, per house          : " + usd(t.usd) + "   [market — placeholder]");
    say("  Drop handling, per house     : " + usd(t.dropHandlingUSD) +
        "   [market — NOT lumber, see WASTE]");

    /* ---- the estimator's first question ---- */
    block("PIECES BY STOCK LENGTH — PER HOUSE");
    say("  The first question in the room is how many 16-footers, not how many board");
    say("  feet. A member is bought as a stick: span + 0.5 ft of bearing, rounded up to");
    say("  an even 2 ft length, minimum 8 ft (FM.solver.stockLength).");
    say();
    say("  " + pad("STOCK", 10) + lpad("PIECES", 8) + lpad("BOARD FT", 12) +
        lpad("MATERIAL", 13) + "  SKUs ON THIS LENGTH");
    say("  " + rule("-").slice(0, 76));
    t.byStockLengthOrder.forEach(function (Lft) {
      var b = t.byStockLength[K(String(Lft))];
      say("  " + pad(Lft + " ft", 10) + lpad(comma(b.pieces), 8) + lpad(n2(b.bf, 2), 12) +
          lpad(usd(b.usd), 13) + "  " + b.skus.join(", "));
    });
    say("  " + rule("-").slice(0, 76));
    say("  " + pad("TOTAL", 10) + lpad(comma(t.pieces), 8) + lpad(n2(t.bf, 2), 12) +
        lpad(usd(t.usd), 13) + "  [market]");
    if (!t.byStockLengthOrder.length) say("  (no member was sized on this plan in this pack)");

    /* ---- the lines ---- */
    block("BILL OF MATERIALS — PER HOUSE");
    if (!bom.lines.length) {
      say("  NO LINES. Not one mark on this plan produced a member in this pack.");
      say("  That is not an empty house — read EXCLUDED below. Everything the plan");
      say("  needs is there, unpriced.");
    }
    say("  " + pad("SIZE", 7) + pad("SPECIES · GRADE", 28) + pad("TREAT", 9) +
        pad("STOCK", 7) + lpad("PC", 5) + lpad("BD FT", 10) + lpad("EXT $", 11));
    say("  " + rule("-").slice(0, 76));
    bom.lines.forEach(function (g) {
      say("  " + pad(g.size, 7) + pad(g.species + " " + g.grade, 28) +
          pad(g.treatment, 9) + pad(g.stockLengthFt + " ft", 7) +
          lpad(comma(g.piecesPerHouse), 5) + lpad(n2(g.bf, 2), 10) + lpad(usd(g.extUSD), 11));
      say("  " + pad("", 7) + "serves " + g.marksLabel +
          "   · cut " + n2(g.lengthFt, 2) + " ft · " + g.service +
          " · " + usd(g.unitUSD) + "/pc [market]" +
          (g.unified ? " · " + g.unified + " mark(s) RAISED BY UNIFICATION" : ""));
      para(g.basis, 70, "        ");
      say();
    });
    if (bom.lines.length) {
      say("  " + rule("-").slice(0, 76));
      say("  " + pad("TOTAL", 51) + lpad(comma(t.pieces), 5) + lpad(n2(t.bf, 2), 10) +
          lpad(usd(t.usd), 11));
      say();
      para("A LINE IS ONE SKU AT ONE STOCK LENGTH, and it names every mark it serves. " +
           "Two marks that the solver unified onto the same member appear on one line " +
           "when they also buy the same stick; where they do not — a 13'-6\" joist and a " +
           "9'-6\" joist unified onto the same 2x12 — they are one SKU on two lines, " +
           "because you order 14-footers and 10-footers separately. See BY SKU below. " +
           "TREATED AND DRY ARE NEVER THE SAME LINE even at the same size, species and " +
           "grade: they are different products, out of different racks, at different prices.");
    }

    /* ---- SKU view ---- */
    if (t.bySkuOrder.length) {
      block("BY SKU — HOW MANY DISTINCT PRODUCTS THIS PLAN CARRIES");
      say("  " + pad("SKU", 46) + lpad("PC", 6) + lpad("BD FT", 10) + lpad("EXT $", 12));
      say("  " + rule("-").slice(0, 76));
      t.bySkuOrder.forEach(function (k) {
        var s = t.bySku[K(k)];
        say("  " + pad(k, 46) + lpad(comma(s.pieces), 6) + lpad(n2(s.bf, 2), 10) +
            lpad(usd(s.usd), 12));
        var byLen = s.lengthOrder.slice().sort(function (a, b) { return a - b; })
          .map(function (Lft) { return s.lengths[K(String(Lft))] + " @ " + Lft + " ft"; });
        say("      lengths: " + byLen.join(", ") + "   ·   marks: " + s.marks.join(", "));
      });
      say();
      say("  Each distinct SKU is a pallet position, a second pick and a second chance to");
      say("  install the wrong one. The solver already prices that through its skuPenalty");
      say("  weight [market]; this table is the count that weight is about.");
    }

    /* ---- by category ---- */
    if (t.byCategoryOrder.length) {
      block("BY CATEGORY");
      say("  " + pad("ROLE", 14) + lpad("PC", 6) + lpad("BD FT", 11) + lpad("MATERIAL $", 13) +
          "  MARKS");
      say("  " + rule("-").slice(0, 76));
      t.byCategoryOrder.forEach(function (r) {
        var c = t.byCategory[K(r)];
        say("  " + pad(r, 14) + lpad(comma(c.pieces), 6) + lpad(n2(c.bf, 2), 11) +
            lpad(usd(c.usd), 13) + "  " + c.marks.join(", "));
      });
      say();
      say("  Where a line serves marks in more than one role, its board feet and dollars");
      say("  are split across the roles in proportion to the pieces each mark contributes.");
    }

    /* ---- per lot / per community ---- */
    block("PER LOT AND PER COMMUNITY");
    say("  PER LOT");
    para(bom.perLot.basis, 72, "      ");
    say();
    var pc = bom.perCommunity;
    say("  PER COMMUNITY" + (pc.lots === null ? "" : "   —   " + comma(pc.lots) + " lots") +
        (pc.weighted ? "   [TAKE-RATE WEIGHTED]" : "   [BASE CASE x LOTS]"));
    say();
    if (pc.lots === null) {
      say("      No lot count is declared on this plan, so no community quantity is");
      say("      stated. The fields are null rather than guessed.");
    } else {
      say("      " + pad("Pieces", 26) + lpad(comma(pc.pieces), 12) +
          (pc.weighted ? "   (expected " + n2(pc.piecesExpected, 1) + ", rounded up)" : ""));
      say("      " + pad("Board feet", 26) + lpad(n2(pc.bf, 0), 12));
      say("      " + pad("Linear feet", 26) + lpad(n2(pc.lf, 0), 12));
      say("      " + pad("Material [market]", 26) + lpad(usd(pc.usd), 12));
      say("      " + pad("Drop handling [market]", 26) + lpad(usd(pc.dropHandlingUSD), 12));
    }
    say();
    para(pc.basis, 72, "      ");
    if (pc.takeRateBasis) { say(); para(pc.takeRateBasis, 72, "      "); }
    if (pc.weighted && pc.perConfiguration && pc.perConfiguration.length) {
      say();
      say("      CONFIGURATIONS — " + pc.solvedConfigurations + " of " + pc.configurations +
          " solved");
      say("      " + pad("CONFIGURATION", 40) + lpad("SHARE", 8) + lpad("LOTS", 8) +
          lpad("PC/LOT", 8) + lpad("ESC", 5));
      say("      " + rule("-").slice(0, 72));
      pc.perConfiguration.forEach(function (c) {
        say("      " + pad((c.label || c.id).slice(0, 39), 40) +
            lpad(n2(c.p * 100, 2) + "%", 8) + lpad(n2(c.lotsExpected, 1), 8) +
            lpad(comma(c.piecesPerLot), 8) + lpad(String(c.escalated), 5));
      });
      if (pc.failedConfigurations && pc.failedConfigurations.length) {
        say();
        para("** " + pc.failedConfigurations.length + " configuration(s) FAILED TO SOLVE and are " +
             "missing from the expectation above, which therefore UNDERSTATES the community: " +
             pc.failedConfigurations.join("; "), 72, "      ");
      }
    }
    if (pc.weighted && pc.lines && pc.lines.length) {
      say();
      say("      COMMUNITY BUY BY LINE");
      say("      " + pad("SIZE", 7) + pad("SPECIES · GRADE", 26) + pad("TREAT", 9) +
          pad("STOCK", 7) + lpad("PIECES", 9) + lpad("EXPECTED", 11));
      say("      " + rule("-").slice(0, 72));
      pc.lines.forEach(function (a) {
        say("      " + pad(a.size, 7) + pad(a.species + " " + a.grade, 26) +
            pad(a.treatment, 9) + pad(a.stockLengthFt + " ft", 7) +
            lpad(comma(a.pieces), 9) + lpad(n2(a.piecesExpected, 1), 11));
      });
      say();
      say("      Pieces are ceil(expected) — a whole-stick buy. The expectation beside it");
      say("      is the unrounded number, so the rounding is visible and never silent.");
    }

    /* ---- waste ---- */
    var w = bom.waste;
    block("WASTE AND DROP POLICY — APPLIED WASTE " + n2(w.appliedPct, 1) + "%");
    para("POLICY — " + w.policy);
    say();
    para("BASIS — " + w.basis);
    say();
    para("GUARD — " + w.guard);
    say();
    say("  " + pad("Board feet purchased", 34) + lpad(n2(w.purchasedBf, 2), 12));
    say("  " + pad("  of which, in the members", 34) + lpad(n2(w.inMembersBf, 2), 12));
    say("  " + pad("  of which, drop (offcut)", 34) + lpad(n2(w.dropBf, 2), 12) +
        "   = " + n2(w.dropPctOfPurchasedBf, 1) + "% of the buy");
    say("  " + pad("Drop, linear feet", 34) + lpad(n2(w.dropLf, 2), 12));
    say("  " + pad("Identity check " + w.dropCheck.identity, 34) +
        lpad("residual " + n2(w.dropCheck.residualBf, 9), 12));
    say();
    say("  " + pad("dropHandling weight [market]", 34) +
        lpad(w.dropHandlingRate === null ? "—" : n2(w.dropHandlingRate, 3), 12));
    say("  " + pad("Drop handling cost, per house", 34) + lpad(usd(w.dropHandlingUSD), 12));
    para(w.dropHandlingNote, 72, "      ");
    say();
    para("NESTING — " + w.nesting.note);
    if (w.nesting.candidates.length) {
      say();
      say("      " + pad("SKU", 34) + pad("STOCK", 8) + pad("CUT", 8) +
          lpad("PC", 6) + lpad("IF NESTED", 11));
      w.nesting.candidates.forEach(function (c) {
        say("      " + pad(c.sku + " " + c.treatment, 34) + pad(c.stockLengthFt + " ft", 8) +
            pad(n2(c.cutLengthFt, 2) + " ft", 8) + lpad(comma(c.sticksAsBought), 6) +
            lpad(comma(c.sticksIfNested), 11));
      });
    }
    say();
    say("  ROUNDING RULES — stated, because a silent rounding changes a count:");
    w.roundingRules.forEach(function (r, i) {
      var lines = wrap(r, 70);
      say("      " + lpad(i + 1, 2) + ". " + lines[0]);
      lines.slice(1).forEach(function (x) { say("          " + x); });
    });

    /* ---- the honest half ---- */
    var esc = bom.excluded.filter(function (e) { return e.kind === "escalated"; });
    var oos = bom.excluded.filter(function (e) { return e.kind === "out-of-scope"; });
    var sys = bom.excluded.filter(function (e) { return e.kind === "not-sized"; });

    block("EXCLUDED — " + bom.excluded.length + " ITEM(S) NOT IN THE BILL ABOVE");
    para("THIS IS THE HALF OF THE DOCUMENT THAT MAKES THE OTHER HALF SAFE TO READ. " +
         "A bill of materials that silently omits the girder reads as a complete order. " +
         "Everything below still has to be priced — from a supplier's design, from " +
         "another consultant, or from the estimator's own takeoff — before anyone " +
         "believes the totals above are what this house costs to frame.");
    say();

    say("  A. MARKS THAT ESCALATED — " + esc.length + " (the schedule proposed NO member)");
    say("  " + rule("-").slice(0, 76));
    if (!esc.length) say("      (none — every mark this engine accepted produced a member)");
    esc.forEach(function (e) {
      say("      " + e.what);
      para(e.why, 66, "          ");
      say();
    });

    say("  B. MARKS OUT OF SCOPE — " + oos.length + " (not this engine's member)");
    say("  " + rule("-").slice(0, 76));
    if (!oos.length) say("      (none)");
    oos.forEach(function (e) {
      say("      " + e.what);
      para(e.why, 66, "          ");
      say();
    });

    say("  C. STRUCTURE THIS SYSTEM DOES NOT SIZE AT ALL — " + sys.length + " CATEGORIES");
    say("  " + rule("-").slice(0, 76));
    say("      These are not absent from this plan. They are absent from the ENGINE:");
    say("      nothing upstream sized them, so nothing here can count them.");
    say();
    sys.forEach(function (e, i) {
      var head = wrap(e.what, 66);
      say("      " + lpad(i + 1, 2) + ". " + head[0]);
      head.slice(1).forEach(function (x) { say("          " + x); });
      para(e.why, 64, "          → ");
      say();
    });

    /* ---- provenance ---- */
    block("PROVENANCE");
    say("  QUANTITIES  [derived]");
    para(bom.provenance.quantities, 70, "      ");
    say();
    say("  PRICES      [market]");
    para(bom.provenance.prices, 70, "      ");
    say();
    para(t.moneyNote, 70, "      ");
    say();
    say("  Modelled selection cost, for tie-back: " +
        (t.modelledSelectionUSD === null ? "—" : usd(t.modelledSelectionUSD)) + " [market]");
    para(t.selectionTieBack, 70, "      ");
    say();
    say("  CODE        [none]");
    para(bom.provenance.code, 70, "      ");
    say();
    say("  SEAL");
    para(bom.provenance.seal, 70, "      ");

    say();
    say(rule("="));
    say("END OF BILL OF MATERIALS — " + (pl.name || pl.id || "—") + " / " + (p.name || p.id || "—"));
    say("READ 'EXCLUDED' BEFORE READING ANY TOTAL ABOVE IT.");
    say(rule("="));
    return L.join("\n");
  }

  FM.bom = {
    build: build,
    text: text,
    SYSTEM_EXCLUSIONS: SYSTEM_EXCLUSIONS,
    BEARING_ALLOWANCE_FT: BEARING_ALLOWANCE_FT,
    /* exposed so a test can prove the BOM counts what the solver costed */
    pieceCountOf: pieceCountOf
  };
})();

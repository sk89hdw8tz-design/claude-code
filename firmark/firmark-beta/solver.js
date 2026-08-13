/* ============================================================
   Sizing solver — the search that proposes a member; the engine
   is still the only thing that decides whether it passes.

   Two rules govern everything in this file:

     1. The solver never computes a capacity. Every feasibility
        verdict comes from FM.engine.run(), unmodified. The solver
        chooses WHICH members to ask about and in WHAT order.
     2. The weights order the feasible set. They cannot promote an
        infeasible member: feasibility is tested before scoring and
        no weight participates in that test. (Enforced by test
        "weights cannot select an overstressed member".)

   Full derivation of the bounds, the dominance argument and the
   weight model is in solver-spec.md.
   ============================================================ */

(function () {
  "use strict";

  var GAMMA_PCF = 35;          /* calc-spec §1.3 — editable assumption, not a sourced value */
  var EPS = 1e-9;

  /* ---------- small geometry helpers ---------- */

  function nominalDims(nominal) {
    var m = /^(\d+)x(\d+)$/.exec(nominal || "");
    return m ? { b: Number(m[1]), d: Number(m[2]) } : null;
  }

  /* Lumber is bought in even 2-ft lengths. A 13'-0" rafter is cut from a 14-footer,
     so the piece that shows up on the invoice is longer than the span. */
  function stockLength(spanFt) {
    var need = spanFt + 0.5;                  /* bearing at both ends */
    var len = Math.ceil(need / 2) * 2;
    /* No upper clamp. Clamping at 24 ft billed a 46 ft member as a 24-footer and
       gave it a NEGATIVE drop cost — the longest stick the yard racks is a
       supply constraint (availability), not a discount. */
    return Math.max(8, len);
  }

  function boardFeetPerLF(nominal) {
    var n = nominalDims(nominal);
    return n ? (n.b * n.d) / 12 : 0;
  }

  /* ---------- load combinations ----------
     Mirrors the combination set engine.js builds, so the seed bounds in §H1 are
     taken against the same envelope the check will use. Guarded by the test
     "solver combos match engine combos" — if engine.js ever changes its
     combination set, that test fails rather than the bound going quietly wrong. */

  function combosFor(D, L, Lr, roofType) {
    var CD = FM.engine.CD;
    var roofCD = roofType === "roof_live" ? CD.roof_live : CD.snow;
    var out = [{ label: "D", psf: D, cd: CD.dead.v }];
    if (L > 0) out.push({ label: "D + L", psf: D + L, cd: CD.live.v });
    if (Lr > 0) out.push({ label: "D + R", psf: D + Lr, cd: roofCD.v });
    if (L > 0 && Lr > 0) out.push({ label: "D + 0.75L + 0.75R", psf: D + 0.75 * L + 0.75 * Lr, cd: roofCD.v });
    return out;
  }

  /* ---------- demand → engine inputs ----------
     One place builds engine inputs, so the number the solver scored and the
     number the sheet re-checks can never disagree. */

  function tribFt(demand, cand) {
    return demand.repetitive ? cand.spacing / 12 : Number(demand.trib || 0);
  }

  /* calc-spec §1.3 case (b): a beam's own weight is NOT inside q_D, and it
     depends on the section — so the demand is a function of the candidate.
     Expressed as psf over the tributary width, the engine's w = psf · t_w
     reproduces w_sw = γ·A/144 exactly. */
  function selfWeightPsf(demand, cand, policy) {
    if (demand.repetitive) return 0;
    var sec = FM.engine.findSection(cand.size);
    var t = tribFt(demand, cand);
    if (!sec || !(t > 0)) return 0;
    var gamma = (policy && policy.gammaPcf) || GAMMA_PCF;
    return (gamma * sec.A_in2 / 144) / t;
  }

  /* `Number(x) || 0` turns NaN into 0, which designs the member for no load.
     engine.js refuses a NaN load — but only if it ever sees one, and this is the
     only path the product actually uses, so the laundering happened here first.
     Pass the value through untouched and let the engine refuse it. */
  function num(v, dflt) {
    if (v === undefined || v === null) return dflt;
    return Number(v);
  }

  function memberInputs(demand, cand, policy) {
    var sw = selfWeightPsf(demand, cand, policy);
    return {
      species: cand.species, grade: cand.grade, size: cand.size,
      span: demand.span,
      spacing: demand.repetitive ? cand.spacing : Number(demand.trib || 0) * 12,
      dead: num(demand.dead, 0) + sw,
      live: num(demand.live, 0),
      roofLoad: num(demand.roofLoad, 0),
      roofType: demand.roofType || "snow",
      repetitive: !!demand.repetitive,
      wet: !!demand.wet,
      braced: !!demand.braced,
      bearing: num(demand.bearing, 1.5),
      memberUse: demand.memberUse || "floor",
      CF: "auto",                      /* the depth moves, so C_F must move with it */
      /* a refractory species must be incised to take preservative, so a treated
         mark in one carries C_i = 0.80 on F_b and F_v (NDS Table 4.3.8). This
         used to be handled by excluding the species; it is now checked. */
      incised: isIncised(demand, cand, policy),
      selfWeightPsf: sw
    };
  }

  function isIncised(demand, cand, policy) {
    if (!(demand.treated || demand.wet)) return false;
    var m = policy && policy.incisedWhenTreated;
    return !!(m && Object.prototype.hasOwnProperty.call(m, cand.species) && m[cand.species]);
  }

  /* ---------- the weighted objective ----------
     Every term is in dollars, so scores are comparable across regions and
     across candidate sets. Nothing here is a code value; see weights.js. */

  function costOf(demand, cand, policy) {
    var w = policy.weights;
    var sec = FM.engine.findSection(cand.size);
    if (!sec) return null;

    var len = stockLength(demand.span);
    var bf = boardFeetPerLF(cand.size) * len;
    var lb = (policy.gammaPcf || GAMMA_PCF) * sec.A_in2 / 144 * len;

    var priced = policy.priceOf ? policy.priceOf(cand, demand) : null;
    var bfUSD = priced && isFinite(priced.bfUSD) ? priced.bfUSD : w.baseBfUSD;
    var availability = priced && isFinite(priced.availability) ? priced.availability : 1;
    var cullRate = priced && isFinite(priced.cullRate) ? priced.cullRate : 0;

    /* area served by one piece — repetitive framing is compared per square foot
       of floor/roof, which is the only way a spacing change can be scored
       honestly against a size change */
    var area = demand.repetitive ? (cand.spacing / 12) * demand.span
                                 : Number(demand.trib || 1) * demand.span;
    if (!(area > 0)) area = 1;

    /* Material is charged over the FULL stock length, because that is the stick
       you buy — the drop is already paid for. `dropHandling` is therefore not a
       second charge for the lumber (that was a double-count); it prices sorting,
       stacking and disposing of the offcut, net of whatever gets used elsewhere.
       A `waste: 1.10` weight in the estimating sense does not belong here. */
    var material = bf * bfUSD * w.material * (1 + cullRate);
    var labor = laborPerPiece(demand, w) + w.laborPerLb * lb;
    var drop = (len - demand.span) * boardFeetPerLF(cand.size) * bfUSD * w.dropHandling;
    var depth = sec.d_in * depthWeight(demand, w) * area;
    var stock = (1 - Math.max(0, Math.min(1, availability))) * w.stockPenaltySf * area;

    var cf = FM.engine.sizeFactor(cand.species, cand.grade, cand.size);
    var risk = cf.basis === "held" ? w.unsourcedCF : 0;

    var total = material + labor + drop + depth + stock + risk;
    /* THE RANKING UNIT. A piece at 16" o.c. and a piece at 24" o.c. do not do the
       same amount of work, so ranking two spacings on per-piece cost silently
       prefers the tighter one — which is how the solver came to recommend 16" o.c.
       roofs to markets that sheathe everything at 24". Repetitive members are
       ranked per square foot of framed area; single members per piece. */
    var unit = demand.repetitive ? area : 1;
    return {
      totalUSD: total, unitUSD: total / unit, perSF: total / area, area: area, unit: unit,
      lengthFt: len, boardFeet: bf, weightLb: lb,
      terms: { material: material, labor: labor, drop: drop, depth: depth, stock: stock, risk: risk },
      bfUSD: bfUSD, availability: availability, cullRate: cullRate, cfBasis: cf.basis
    };
  }

  /* A lanai beam and a floor joist are not the same job, and a floor joist's
     depth costs building height while a roof member's does not. Both weights are
     therefore keyed by role, falling back to the flat value. */
  function laborPerPiece(demand, w) {
    var byRole = w.laborPerPieceByRole || {};
    var v = own(byRole, demand.role);
    return isFinite(v) ? v : w.laborPerPiece;
  }
  function depthWeight(demand, w) {
    var byRole = w.depthPerInchSfByRole || {};
    var v = own(byRole, demand.role);
    return isFinite(v) ? v : w.depthPerInchSf;
  }
  /* author-supplied strings are used as keys throughout; a mark whose role or
     SKU group is named "constructor" must not pick up Object.prototype */
  function own(o, k) {
    return (o && Object.prototype.hasOwnProperty.call(o, k)) ? o[k] : undefined;
  }
  /* guarding reads is half the job: `groups[g] = []` silently no-ops for a group
     named "__proto__", so the group vanishes from unification with no error */
  function safeKey(k) {
    var s = String(k);
    return (s === "__proto__" || s === "constructor" || s === "prototype") ? "\u0000" + s : s;
  }

  /* slack is scored only after a candidate is known feasible, so it can never
     act on the pass/fail decision — it just stops the search from proposing a
     4x12 where a 2x8 was already inside the firm's DCR target */
  function slackPenalty(dcr, policy) {
    var target = policy.maxDCR;
    var unused = Math.max(0, target - dcr) / target;
    return unused * policy.weights.slackPenalty;
  }

  /* ---------- H1: admissible seed bounds ----------
     Lower bounds on the section properties any member in this palette must have.
     Each bound is taken against the MOST favourable material in the palette and
     the MOST favourable factor stack (C_L = 1, C_M = 1, C_r if reachable), so a
     candidate that fails a bound cannot pass the real check for any material
     offered. Self-weight is deliberately left out: it only adds demand, so
     omitting it keeps the bound low, i.e. safe.

     Test "pruned candidates are genuinely infeasible" runs the full exhaustive
     search against the pruned one and asserts the feasible sets are identical. */

  function seedBounds(demand, policy) {
    var span = Number(demand.span), L_in = span * 12;
    var D = num(demand.dead, 0), L = num(demand.live, 0), Lr = num(demand.roofLoad, 0);
    var combos = combosFor(D, L, Lr, demand.roofType);
    var use = FM.engine.DEFL[demand.memberUse] || FM.engine.DEFL.floor;

    var best = { Fb: 0, Fv: 0, E: 0, Fcp: 0 };
    policy.palette.forEach(function (p) {
      policy.ladder.forEach(function (size) {
        var sec = FM.engine.findSection(size);
        if (!sec) return;
        var mat = FM.engine.findValues(p.species, p.grade, sec.d_in, sec.b_in);
        if (!mat) return;
        var cf = FM.engine.sizeFactor(p.species, p.grade, size);
        var v = mat.values_psi;
        /* the bound is only admissible if it sees every factor the check applies —
           C_i reduces F_b and F_v by 20%, so taking the un-incised value would
           overstate capacity for a species that will be checked incised. Using the
           MAXIMUM across the palette keeps it optimistic, which is the safe side. */
        var inc = isIncised(demand, { species: p.species }, policy);
        var fb = v.Fb * cf.CF * (inc ? 0.80 : 1);
        var fv = v.Fv * (inc ? 0.80 : 1);
        var ee = v.E * (inc ? 0.95 : 1);
        if (fb > best.Fb) best.Fb = fb;
        if (fv > best.Fv) best.Fv = fv;
        if (ee > best.E) best.E = ee;
        if (v.Fc_perp > best.Fcp) best.Fcp = v.Fc_perp;
      });
    });

    /* C_r is reachable only by a repetitive member ≤24" o.c. and ≤4" thick.
       Taken per spacing, because a 24" o.c. candidate can reach it and a 32"
       o.c. one cannot. */
    var target = policy.maxDCR;
    var spacings = demand.repetitive ? policy.spacings : [0];

    /* Bounds are computed PER SPACING and never maxed across them.
       Spacing is a candidate axis, not a property of the demand: a member at
       16" o.c. carries two-thirds of what the same member carries at 24", and
       judging it against the 24" requirement prunes valid — indeed optimal —
       candidates. That defect shipped once; the exhaustive-vs-pruned test in
       test/run-tests.js is what caught it and is what keeps it caught. */
    function boundsAt(sp) {
      var t = demand.repetitive ? sp / 12 : Number(demand.trib || 0);
      var Cr = (demand.repetitive && sp > 0 && sp <= 24) ? 1.15 : 1;
      var S_req = 0, A_req = 0, b_req = 0, I_req = 0;

      combos.forEach(function (c) {
        var w = c.psf * t;                                  /* plf */
        var M = 1.5 * w * span * span;                      /* in-lb, calc-spec §0.2 */
        var Fb_cap = best.Fb * c.cd * Cr;
        if (Fb_cap > 0) S_req = Math.max(S_req, M / (Fb_cap * target));

        var V = w * span / 2;
        var Fv_cap = best.Fv * c.cd;
        if (Fv_cap > 0) A_req = Math.max(A_req, 1.5 * V / (Fv_cap * target));

        /* bearing bounds the BREADTH, not the depth — C_D never touches F_c⊥ */
        var lb = Number(demand.bearing || 1.5);
        if (best.Fcp > 0 && lb > 0) b_req = Math.max(b_req, V / (best.Fcp * lb * target));
      });

      var wVar = (L + Lr) * t / 12;                         /* lb/in, mirrors engine.js */
      var wTot = (D + L + Lr) * t / 12;
      if (best.E > 0) {
        I_req = Math.max(
          5 * wVar * Math.pow(L_in, 4) / (384 * best.E * (L_in / use.live) * target),
          5 * wTot * Math.pow(L_in, 4) / (384 * best.E * (L_in / use.total) * target));
      }
      return { S_req: S_req, I_req: I_req, A_req: A_req, b_req: b_req, Cr: Cr, spacing: sp };
    }

    var bySpacing = {};
    spacings.forEach(function (sp) { bySpacing[String(sp)] = boundsAt(sp); });

    return {
      bySpacing: bySpacing,
      at: function (sp) { return bySpacing[String(sp || 0)] || bySpacing[String(spacings[0])]; },
      best: best, combos: combos, target: target,
      deflection: { row: demand.memberUse || "floor", live: use.live, total: use.total, cite: use.cite }
    };
  }

  function passesBounds(cand, bounds, demandBearing) {
    var s = FM.engine.findSection(cand.size);
    if (!s) return { ok: false, why: "no section properties" };
    var b = bounds.at(cand.spacing);
    if (!b) return { ok: true };
    if (s.Sx_in3 < b.S_req - EPS) return { ok: false, why: "S_x below the palette's best-case bending requirement" };
    if (s.Ix_in4 < b.I_req - EPS) return { ok: false, why: "I_x below the deflection requirement" };
    if (s.A_in2 < b.A_req - EPS) return { ok: false, why: "A below the shear requirement" };
    if (s.b_in < b.b_req - EPS) {
      /* Bearing is NOT a section wall. Every rung in a header ladder is the same
         breadth, so a bearing shortfall empties the whole ladder and then gets
         reported as a stiffness problem — while the solver's own repair table
         says of bearing "depth does nothing". Classify it separately so the
         answer is "this header needs a second jack stud", not "buy an LVL". */
      return { ok: false, why: "breadth " + s.b_in.toFixed(2) + " in is below the " +
               b.b_req.toFixed(3) + " in the bearing reaction needs at l_b = " +
               Number(demandBearing).toFixed(2) + " in", bearing: true };
    }
    return { ok: true };
  }

  /* ---------- enumeration ----------
     A family is one (species, grade, thickness, spacing). Within a family the
     only free axis is depth, and cost is checked to be nondecreasing in depth
     before any dominance pruning is applied to it (see H2 in solver-spec.md). */

  /* ---------- eligibility gates ----------
     Three things disqualify a candidate before any structural question is asked.
     They are gates, not costs, because none of them is a trade-off the weights
     get to make. Each returns the reason in the engineer's language. */

  function eligibility(cand, demand, policy) {
    /* geometry — a header has a depth budget set by the plate and head heights,
       and a member that does not fit is not a cheaper member, it is no member */
    if (demand.maxDepthIn && cand.d_in > Number(demand.maxDepthIn) + EPS) {
      return { ok: false, kind: "geometry",
               why: cand.size + " is " + cand.d_in.toFixed(2) + " in deep; only " +
                    Number(demand.maxDepthIn).toFixed(2) + " in is available above the head height" };
    }

    /* procurement — a member the yard cannot hand the framer gets substituted in
       the field, and the substitute is nobody's design */
    if (policy.minAvailability !== undefined && policy.priceOf) {
      var pr = policy.priceOf(cand, demand);
      if (pr && isFinite(pr.availability) && pr.availability < policy.minAvailability) {
        return { ok: false, kind: "procurement",
                 why: "availability " + pr.availability.toFixed(2) + " is below the firm floor of " +
                      Number(policy.minAvailability).toFixed(2) + " — special order, and the field will substitute" };
      }
    }

    return { ok: true };
  }

  function families(demand, policy) {
    var spacings = demand.repetitive ? policy.spacings : [null];
    var out = [], excluded = [];
    policy.palette.forEach(function (p, pi) {
      spacings.forEach(function (sp) {
        var byThickness = {};
        policy.ladder.forEach(function (size) {
          var sec = FM.engine.findSection(size);
          if (!sec) return;
          var cand = {
            species: p.species, grade: p.grade, size: size,
            spacing: sp === null ? 0 : sp,
            b_in: sec.b_in, d_in: sec.d_in, paletteIndex: pi
          };
          var e = eligibility(cand, demand, policy);
          if (!e.ok) {
            if (sp === null || sp === spacings[0]) excluded.push({ cand: cand, kind: e.kind, why: e.why });
            return;
          }
          var key = String(sec.b_in);
          if (!byThickness[key]) byThickness[key] = [];
          byThickness[key].push(cand);
        });
        Object.keys(byThickness).forEach(function (k) {
          var rungs = byThickness[k].sort(function (a, b) { return a.d_in - b.d_in; });
          out.push({
            id: p.species + " " + p.grade + " · " + k + " in thick" + (sp ? " @ " + sp + " o.c." : ""),
            species: p.species, grade: p.grade, thickness: Number(k),
            spacing: sp === null ? 0 : sp, rungs: rungs
          });
        });
      });
    });
    out.excluded = excluded;
    return out;
  }

  /* ---------- H4: which axis to step when a check fails ----------
     Sensitivity of each limit state to depth, from the closed forms in
     calc-spec §3: deflection goes as d³, bending as d², shear as d¹, bearing
     not at all. Used to explain a failure and to propose the next move — never
     to skip an evaluation. */

  var REPAIR = {
    "Deflection (live)":  { axis: "depth",   exponent: 3, move: "go deeper (I ∝ d³) or tighten spacing" },
    "Deflection (total)": { axis: "depth",   exponent: 3, move: "go deeper (I ∝ d³) or tighten spacing" },
    "Bending":            { axis: "depth",   exponent: 2, move: "go deeper (S ∝ d²) or up a grade — F_b moves most between grades" },
    "Shear":              { axis: "area",    exponent: 1, move: "more area — thicker stock helps as much as deeper" },
    "Bearing (Fc⊥)":      { axis: "bearing", exponent: 0, move: "lengthen the bearing or widen the member — depth does nothing" }
  };

  var GATE_MOVE = {
    geometry:    "raise the plate height, drop the head height, or flush-frame the condition",
    procurement: "confirm the yard will stock it, or lower the availability floor deliberately",
    scope:       "use a species that takes treatment without incising, or check it by hand with C_i"
  };

  /* ---------- the search ---------- */

  function size(demand, policy) {
    if (!FM.engine) throw new Error("solver requires FM.engine");
    /* calc-spec §6.2: DCR <= 1.000 passes, with no tolerance band. A firm may
       set a TIGHTER target; it may not set a looser one. */
    if (!(policy.maxDCR > 0) || policy.maxDCR > 1) {
      policy = shallow(policy);
      policy.maxDCR = Math.min(1, Math.max(0.01, Number(policy.maxDCR) || 0.9));
    }
    var cache = {}, stats = { evaluated: 0, contextEvaluated: 0, cacheHits: 0, prunedByBound: 0, prunedByDominance: 0, prunedByIncumbent: 0, families: 0 };

    /* calc-spec §2.1 wants six combinations built from separate q_Lr and q_S; the
       engine carries ONE roof load tagged either snow or roof-live, so D + Lr and
       D + S can never be evaluated together. Near the 20 psf roof-live minimum
       either tag is unconservative on one limit state: declared roof-live, snow
       understates bending by up to 8.4%; declared snow, roof-live understates
       deflection. Make the exposure visible instead of silent. */
    var advisories = [];
    /* For a roof+floor mark the roof load is blended into an equivalent psf over
       the summed tributary, so `demand.roofLoad` reads ~14.8 where the member
       carries 20. Testing the blended number switched this advisory off on the
       marks that carry two load paths — including nc-mountain, the one pack
       where the collapse changes the answer. */
    var rl = num(demand.roofLoadActual !== undefined ? demand.roofLoadActual : demand.roofLoad, 0);
    if (rl > 0 && rl >= 16 && rl <= 25) {
      advisories.push({
        kind: "roof-load-crossover",
        text: "Roof load " + rl.toFixed(0) + " psf sits near the 20 psf roof-live minimum, where the " +
              "snow and roof-live cases cross. This engine evaluates only the one you declared (" +
              (demand.roofType === "snow" ? "snow, C_D 1.15" : "roof live, C_D 1.25") + "), so " +
              (demand.roofType === "snow"
                ? "the roof-live case — which governs deflection below 20 psf — was not checked."
                : "the snow case — which governs bending above about 18.4 psf — was not checked.") +
              " Check the other case by hand before this member is used."
      });
    }

    /* if the demand itself is not numeric, no candidate can be checked and none
       should be proposed — refuse the whole search rather than the members */
    var badLoad = ["dead", "live", "roofLoad", "span", "bearing"].filter(function (k) {
      return demand[k] !== undefined && demand[k] !== null && !isFinite(Number(demand[k]));
    });
    if (badLoad.length) {
      return { demand: demand, status: "escalate:input", pick: null, feasible: [], rejected: [],
               advisories: advisories, stats: { evaluated: 0 }, searchSpace: 0,
               policy: { id: policy.id, name: policy.name, maxDCR: policy.maxDCR,
                         ladder: policy.ladder, spacings: policy.spacings, palette: [] },
               note: { wall: "the demand is not numeric: " + badLoad.join(", "),
                       move: "correct the input", counts: {},
                       outOfScope: "Nothing was checked. A member was not proposed." } };
    }

    var bounds = seedBounds(demand, policy);
    var boundPruned = [];
    var fams = families(demand, policy);
    stats.families = fams.length;

    function evaluate(cand) {
      var inputs = memberInputs(demand, cand, policy);
      var key = JSON.stringify(inputs);
      if (cache[key]) { stats.cacheHits++; return cache[key]; }
      stats.evaluated++;
      var r = FM.engine.run(inputs);
      cache[key] = { result: r, inputs: inputs };
      return cache[key];
    }

    /* cost is engine-free, so a family's whole cost vector is known before any
       check runs — which is what makes the dominance and incumbent pruning below
       exact rather than heuristic guesses */
    fams.forEach(function (fam) {
      fam.rungs.forEach(function (c) { c.cost = costOf(demand, c, policy); });
      fam.admissible = fam.rungs.filter(function (c) {
        var pb = passesBounds(c, bounds, demand.bearing);
        if (!pb.ok) boundPruned.push({ cand: c, reason: pb.why, bound: !pb.bearing, bearing: !!pb.bearing });
        return pb.ok;
      });
      fam.monotone = true;
      for (var i = 1; i < fam.rungs.length; i++) {
        if (fam.rungs[i].cost && fam.rungs[i - 1].cost &&
            fam.rungs[i].cost.unitUSD < fam.rungs[i - 1].cost.unitUSD - EPS) { fam.monotone = false; break; }
      }
      fam.lowerBoundUSD = fam.admissible.reduce(function (m, c) {
        return c.cost && c.cost.unitUSD < m ? c.cost.unitUSD : m;
      }, Infinity);
      stats.prunedByBound += fam.rungs.length - fam.admissible.length;
    });

    /* H3: cheapest-possible-family first, so the incumbent gets good early and
       prunes hard */
    fams.sort(function (a, b) {
      if (a.lowerBoundUSD !== b.lowerBoundUSD) return a.lowerBoundUSD - b.lowerBoundUSD;
      return a.id < b.id ? -1 : 1;
    });

    var considered = [], rejected = [], incumbent = null;

    /* candidates that never reached the engine because a gate disqualified them.
       They belong in the record: "we did not check a 4x14" is a different
       statement from "a 4x14 failed", and an engineer needs to know which. */
    (fams.excluded || []).forEach(function (x) {
      rejected.push({ cand: x.cand, dcr: null, governing: null, gate: x.kind,
                      reason: x.why, next: GATE_MOVE[x.kind] || null });
    });

    fams.forEach(function (fam) {
      if (incumbent && fam.lowerBoundUSD > incumbent.score + EPS) {
        stats.prunedByIncumbent += fam.admissible.length;
        return;
      }
      for (var i = 0; i < fam.admissible.length; i++) {
        var cand = fam.admissible[i];

        if (incumbent && cand.cost.unitUSD > incumbent.score + EPS) {
          /* "rungs are depth-ordered, so cost only grows" is exactly the
             property fam.monotone verifies — and it is not free. A per-size
             price vector (short supply on one rung, clearance on another) makes
             cost non-monotone, and breaking here on that family skips cheaper
             rungs below. Skip this candidate, but keep walking the family. */
          if (fam.monotone) {
            stats.prunedByIncumbent += fam.admissible.length - i;
            break;
          }
          stats.prunedByIncumbent++;
          continue;
        }

        var ev = evaluate(cand);
        var r = ev.result;

        if (r.error) {
          rejected.push({ cand: cand, reason: r.message, dcr: null, governing: null });
          continue;
        }
        var dcr = r.governing.dcr;
        var ok = isFinite(dcr) && dcr <= policy.maxDCR + EPS;
        var row = {
          cand: cand, dcr: dcr, governing: r.governing.name, combo: r.governing.combo,
          kind: r.governing.kind, cost: cand.cost, feasible: ok,
          warnings: r.warnings || [], inputs: ev.inputs,
          checks: r.checks.map(function (c) { return { name: c.name, dcr: c.dcr }; })
        };
        considered.push(row);

        if (!ok) {
          var rep = REPAIR[r.governing.name] || { move: "no repair rule for this limit state" };
          rejected.push({
            cand: cand, dcr: dcr, governing: r.governing.name,
            reason: (r.governing.kind === "service" ? "exceeds the deflection limit" : "overstressed") +
                    " at DCR " + dcr.toFixed(3) + " (target " + policy.maxDCR.toFixed(2) + ")",
            next: rep.move
          });
          continue;
        }

        /* score is the ranking objective, in $/sf for repetitive members and
           $/piece for single ones. pieceScore stays absolute, because SKU
           unification and the plan cost rollup are per-piece questions. */
        row.pieceScore = cand.cost.totalUSD + slackPenalty(dcr, policy);
        row.score = row.pieceScore / cand.cost.unit;
        /* tieBreak decides ties, not losses — reaching it on a strictly worse
           score would let a more expensive candidate take the incumbency */
        if (!incumbent || row.score < incumbent.score - EPS ||
            (Math.abs(row.score - incumbent.score) <= EPS && tieBreak(row, incumbent) < 0)) {
          incumbent = row;
        }

        /* H2 dominance: within a family, deeper rungs cost at least as much as
           this one, so none of them can win. Only applied where the family's
           cost vector was actually verified nondecreasing. */
        if (fam.monotone) {
          stats.prunedByDominance += fam.admissible.length - i - 1;
          break;
        }
      }
    });

    /* ---- explain pass ----
       The search above is an optimiser: it proves which candidate wins while
       evaluating as few as it can. That is the right behaviour for a solver and
       the wrong behaviour for a sheet an engineer has to sign, because it can
       return a single row with nothing to compare it against.

       So after the winner is settled, fill in the rest of the admissible ladder
       for display. These evaluations are counted separately — they are context,
       not search — and they are walked in a fixed order that does not depend on
       the weights, so the ladder an engineer sees is the same ladder regardless
       of what the prices are set to. */
    var budget = policy.explainBudget === undefined ? 40 : policy.explainBudget;
    var seen = {};
    considered.forEach(function (c) { seen[keyOf(c.cand)] = true; });

    /* bound-pruned candidates enter the record too — "we never checked a 2x6
       because no 2x6 can reach the required S_x" is an answer */
    boundPruned.forEach(function (bp) {
      rejected.push({ cand: bp.cand, dcr: null, governing: null,
                      bound: bp.bound, gate: bp.bearing ? "bearing" : undefined,
                      reason: bp.reason,
                      next: bp.bearing ? "lengthen the bearing — a second jack stud, not a deeper section"
                                       : "a deeper or stronger section" });
    });

    var ordered = fams.slice().sort(function (a, b) { return a.id < b.id ? -1 : (a.id > b.id ? 1 : 0); });
    var context = [], exhausted = true;
    for (var fi = 0; fi < ordered.length; fi++) {
      var frows = ordered[fi].admissible;
      for (var ci = 0; ci < frows.length; ci++) {
        var cc = frows[ci];
        if (seen[keyOf(cc)]) continue;
        if (context.length >= budget) { exhausted = false; fi = ordered.length; break; }
        seen[keyOf(cc)] = true;
        var cev = evaluate(cc);
        stats.contextEvaluated++;
        if (cev.result.error) {
          rejected.push({ cand: cc, reason: cev.result.message, dcr: null, governing: null, context: true });
          continue;
        }
        var cdcr = cev.result.governing.dcr;
        var cok = isFinite(cdcr) && cdcr <= policy.maxDCR + EPS;
        var crow = {
          cand: cc, dcr: cdcr, governing: cev.result.governing.name, combo: cev.result.governing.combo,
          kind: cev.result.governing.kind, cost: cc.cost, feasible: cok, context: true,
          warnings: cev.result.warnings || [], inputs: cev.inputs,
          checks: cev.result.checks.map(function (c) { return { name: c.name, dcr: c.dcr }; })
        };
        if (cok) {
          crow.pieceScore = cc.cost.totalUSD + slackPenalty(cdcr, policy);
          crow.score = crow.pieceScore / cc.cost.unit;
        }
        else {
          var crep = REPAIR[cev.result.governing.name] || { move: "no repair rule for this limit state" };
          rejected.push({
            cand: cc, dcr: cdcr, governing: cev.result.governing.name,
            reason: (crow.kind === "service" ? "exceeds the deflection limit" : "overstressed") +
                    " at DCR " + cdcr.toFixed(3) + " (target " + policy.maxDCR.toFixed(2) + ")",
            next: crep.move, context: true
          });
        }
        context.push(crow);
      }
    }
    stats.ladderComplete = exhausted;

    var feasible = considered.concat(context).filter(function (c) { return c.feasible; })
      .sort(function (a, b) { return a.score - b.score || tieBreak(a, b); });

    /* self-check: the search claimed optimality, the context pass evaluated more.
       Compare on score AND tie-break, because agreeing on score while disagreeing
       on which member won is exactly the defect this guards. */
    stats.searchOptimal = !incumbent || !feasible.length ||
      (feasible[0] === incumbent) ||
      (Math.abs(feasible[0].score - incumbent.score) <= 1e-9 && tieBreak(feasible[0], incumbent) === 0);

    /* The pick is the head of the ranked list, full stop. Returning the search
       incumbent instead let the recommendation disagree with the table printed
       beside it whenever two candidates tied exactly on score — the incumbent
       was chosen in search order, the list by tieBreak. */
    var pick = feasible[0] || null;

    /* End reactions are the currency of coordination. The truss supplier, the
       EWP supplier and the foundation engineer all need the number in pounds at
       each bearing — not the member size — and the engine already computes it.
       Publishing it is nearly free and is the most useful thing this output can
       hand a production builder. */
    var reactions = pick ? endReactions(demand, pick, policy) : null;

    /* Escalation is a status, not a footnote. A plan with an escalation is not
       a finished schedule and must not read like one. */
    /* B-1: a candidate excluded at the procurement gate was rejected BEFORE any
       engine call. Naming it "the member that passes" was an assertion about a
       member nobody checked — and measured across 112 escalations, 82% of those
       named were overstressed, one at DCR 2.025. Check them, then name only the
       ones that actually passed. */
    var gatedPassing = [], gatedFailing = [];
    if (!pick) {
      rejected.forEach(function (r) {
        if (r.gate !== "procurement") return;
        var gev = evaluate(r.cand);
        stats.contextEvaluated++;
        if (gev.result.error || !isFinite(gev.result.governing.dcr)) { r.checkedDcr = null; return; }
        r.checkedDcr = gev.result.governing.dcr;
        r.checkedGoverning = gev.result.governing.name;
        if (r.checkedDcr <= policy.maxDCR + EPS) gatedPassing.push(r); else gatedFailing.push(r);
      });
    }

    /* Report the wall that actually stopped the search, in this order:
         strength   nothing in the ladder reaches the required section, or every
                    evaluated candidate was overstressed — a real engineering wall
         procurement a member PASSED but the availability floor excluded it
         geometry    a member would fit structurally but not physically
       Falling through to whichever gate happened to appear in the rejection list
       produced "lower your availability floor" as the advice for a member that
       was 4% short on section modulus. */
    /* B-2: ONE classifier produces both the status and the note. They used to be
       decided independently and disagreed — `escalate:strength` was set first on
       any evaluated candidate, so three of the four statuses were unreachable
       while the note took a different branch in the same object. */
    var status = "ok", blocked = null;
    if (!pick) {
      var bearingWall = rejected.filter(function (r) { return r.gate === "bearing"; });
      if (gatedPassing.length)        status = "escalate:procurement";
      else if (bearingWall.length && !considered.length) status = "escalate:bearing";
      else if (rejected.some(function (r) { return r.gate === "geometry"; }) && !considered.length)
                                      status = "escalate:geometry";
      else {
        status = "escalate:strength";
        blocked = boundWall(bounds, policy, policy.ladder);
      }
    }

    return {
      demand: demand,
      status: status,
      advisories: advisories,
      blocked: blocked,
      reactions: reactions,
      policy: { id: policy.id, name: policy.name, maxDCR: policy.maxDCR,
                ladder: policy.ladder, spacings: policy.spacings,
                palette: policy.palette.map(function (p) { return p.species + " " + p.grade; }) },
      pick: pick,
      feasible: feasible,
      rejected: rejected,
      bounds: bounds,
      stats: stats,
      searchSpace: fams.reduce(function (n, f) { return n + f.rungs.length; }, 0),
      note: feasible.length ? null
        : noFeasibleNote(demand, policy, rejected, blocked, status, gatedPassing, gatedFailing),
    };
  }

  /* R = w·L/2 per bearing, at the governing combination — calc-spec §3.2.
     Reported unreduced: the §3.4.3.1 d-reduction is a shear allowance and must
     never be applied to a bearing reaction. */
  function endReactions(demand, row, policy) {
    var D = Number(row.inputs.dead || 0), L = Number(row.inputs.live || 0),
        Lr = Number(row.inputs.roofLoad || 0);
    var combos = combosFor(D, L, Lr, row.inputs.roofType);
    var t = row.inputs.spacing / 12;
    var worst = null;
    combos.forEach(function (c) {
      var R = (c.psf * t) * demand.span / 2;
      if (!worst || R > worst.lb) worst = { lb: R, combo: c.label, psf: c.psf };
    });
    return {
      perBearingLb: worst ? worst.lb : null,
      combo: worst ? worst.combo : null,
      note: "Unreduced support reaction at each bearing, governing gravity combination. " +
            "Hand this to the truss, EWP or connector designer — the connection is not designed here."
    };
  }

  /* When the seed bounds emptied the ladder, name the section property that did
     it and by how much — "no section reaches S_x = 76.95 in³" is an answer; a
     gate label is not. */
  /* Rank by how far SHORT the ladder falls, not by which number is numerically
     largest. Comparing in³ against in⁴ against in² meant I_x won essentially
     always — it was named in 17 of 17 reports, including the ones where the
     ladder cleared it with 25% to spare. Bearing is excluded: it is not a
     property of the section. */
  function boundWall(bounds, policy, ladder) {
    var best = { Sx: 0, Ix: 0, A: 0 };
    (ladder || []).forEach(function (sz) {
      var sec = FM.engine.findSection(sz);
      if (!sec) return;
      if (sec.Sx_in3 > best.Sx) best.Sx = sec.Sx_in3;
      if (sec.Ix_in4 > best.Ix) best.Ix = sec.Ix_in4;
      if (sec.A_in2 > best.A) best.A = sec.A_in2;
    });
    var worst = null;
    Object.keys(bounds.bySpacing).forEach(function (k) {
      var b = bounds.bySpacing[k];
      [["S_x", "in³", b.S_req, best.Sx], ["I_x", "in⁴", b.I_req, best.Ix], ["A", "in²", b.A_req, best.A]]
        .forEach(function (t) {
          if (!(t[3] > 0)) return;
          var ratio = t[2] / t[3];
          if (ratio <= 1 + EPS) return;                 /* the ladder satisfies it — not a wall */
          if (!worst || ratio > worst.ratio) {
            worst = { prop: t[0], unit: t[1], value: t[2], available: t[3], ratio: ratio, spacing: k };
          }
        });
    });
    return worst ? {
      property: worst.prop, required: worst.value, available: worst.available,
      unit: worst.unit, shortfall: worst.ratio,
      text: "the deepest section in the ladder gives " + worst.available.toFixed(2) + " " +
            worst.unit + " of " + worst.prop + " and this member needs " +
            worst.value.toFixed(2) + " — short by " + Math.round((worst.ratio - 1) * 100) +
            "% at the firm's DCR target of " + policy.maxDCR.toFixed(2)
    } : null;
  }

  /* deterministic all the way down — same inputs, same schedule, every run */
  function tieBreak(a, b) {
    if (a.cand.d_in !== b.cand.d_in) return a.cand.d_in - b.cand.d_in;
    if (a.cand.b_in !== b.cand.b_in) return a.cand.b_in - b.cand.b_in;
    if (a.cand.paletteIndex !== b.cand.paletteIndex) return a.cand.paletteIndex - b.cand.paletteIndex;
    if (a.cand.spacing !== b.cand.spacing) return b.cand.spacing - a.cand.spacing;
    return a.cand.size < b.cand.size ? -1 : (a.cand.size > b.cand.size ? 1 : 0);
  }

  /* When nothing fits, say which wall the search hit and what would move it.
     A solver that only reports "no solution" is telling the engineer nothing. */
  function noFeasibleNote(demand, policy, rejected, blocked, status, gatedPassing, gatedFailing) {
    if (status === "escalate:procurement") {
      var names = gatedPassing.map(function (r) {
        return skuOf(r.cand) + " (checked, DCR " + r.checkedDcr.toFixed(3) + ")";
      }).join(", ");
      var alsoTried = gatedFailing.length
        ? " " + gatedFailing.length + " other excluded member(s) were checked and do NOT pass." : "";
      return {
        wall: "a solid-sawn member passes this check — your availability floor excludes it",
        counts: {}, procurement: names,
        move: "confirm the yard will supply " + names + ", or lower the availability floor deliberately",
        outOfScope: "This is a PROCUREMENT decision for the member(s) named — each was run through " +
                    "the engine and passed." + alsoTried + " " + OUT_OF_SCOPE
      };
    }
    if (status === "escalate:bearing") {
      var br = rejected.filter(function (r) { return r.gate === "bearing"; })[0];
      return {
        wall: br ? br.reason : "the bearing reaction exceeds what this bearing length can carry",
        counts: {},
        move: "lengthen the bearing — a second jack stud. Depth does nothing for bearing.",
        outOfScope: "This is a DETAILING question, not a member-size question. No section in the " +
                    "ladder is wider, so a deeper member cannot solve it."
      };
    }
    if (blocked) {
      return { wall: blocked.text, counts: {}, move: "a deeper or stronger section than the ladder offers",
               outOfScope: OUT_OF_SCOPE };
    }
    var byCheck = {};
    rejected.forEach(function (r) {
      if (!r.governing) return;
      byCheck[r.governing] = (byCheck[r.governing] || 0) + 1;
    });
    var worst = Object.keys(byCheck).sort(function (a, b) { return byCheck[b] - byCheck[a]; })[0];
    var rep = REPAIR[worst] || null;
    return {
      wall: worst || "no candidate could even be evaluated",
      counts: byCheck,
      move: rep ? rep.move : "widen the palette or the size ladder",
      outOfScope: OUT_OF_SCOPE
    };
  }

  var OUT_OF_SCOPE =
    "Multi-ply built-up members, engineered lumber (LVL/PSL/LSL) and I-joists are outside this " +
    "engine (calc-spec §8.6, §8.19). A span this size in a tract plan is normally an engineered " +
    "header — that selection cannot be made here.";

  /* ---------- plan-level solve ---------- */

  function solvePlan(plan, pack, opts) {
    opts = opts || {};
    var policy = FM.weights.policyFor(pack, plan);
    var marks = plan.marks.map(function (mk) {
      /* A mark can be structurally irrelevant in a region — a wood exterior
         header in a concrete-block market, or a truss. Reporting it as
         "no solution" would be wrong twice over: it is not a failure, and it is
         not this engine's member. Say what it actually is. */
      var appl = FM.weights.applicability ? FM.weights.applicability(mk, pack) : { applicable: true };
      if (!appl.applicable) {
        return { mark: mk, demand: null, solution: null, policy: null,
                 notApplicable: { reason: appl.reason, note: appl.note } };
      }
      var demand = FM.weights.demandFor(mk, plan, pack);
      var rolePolicy = FM.weights.policyFor(pack, plan, mk.role);
      var sol = size(demand, rolePolicy);
      return { mark: mk, demand: demand, solution: sol, policy: rolePolicy };
    });
    var out = { plan: plan, pack: pack, marks: marks, policy: policy };
    out.unified = opts.unify === false ? null : unify(out);
    out.rollup = rollup(out);
    return out;
  }

  /* ---------- H7: SKU unification ----------
     A tract plan is built dozens of times. Two marks that land one rung apart
     cost the builder a second SKU on every lot — pallet space, a second pick,
     a second chance to install the wrong one. Collapse a mark up to a sibling's
     size when the extra lumber costs less than the weights say a distinct SKU
     costs. Only ever collapses UPWARD to a member that already passed its own
     check, so nothing here can weaken a member. */

  function unify(planResult) {
    var w = planResult.policy.weights;
    var bonus = planResult.policy.unifyBonus || {};
    var groups = {};
    planResult.marks.forEach(function (m) {
      if (!m.solution || !m.solution.pick) return;
      var g = safeKey(m.mark.skuGroup || m.mark.role);
      if (!Object.prototype.hasOwnProperty.call(groups, g)) groups[g] = [];
      groups[g].push(m);
    });

    var moves = [];
    Object.keys(groups).forEach(function (g) {
      var members = groups[g];
      if (members.length < 2) return;

      var distinct = {};
      members.forEach(function (m) { distinct[skuOf(m.solution.pick.cand)] = 1; });
      var skusBefore = Object.keys(distinct).length;
      if (skusBefore < 2) return;

      /* Every distinct size in the group is a candidate target, not just the
         deepest. A group of {2x8 ×10, 2x10 ×40, 2x12 ×1} should raise the 2x8s
         to 2x10 and leave the single 2x12 alone — collapsing all 51 pieces onto
         2x12 to kill two SKUs is the expensive answer, and only considering the
         deepest member was the reason it used to be the only answer. */
      var candidates = [];
      members.forEach(function (m) {
        var t = m.solution.pick.cand;
        if (!candidates.some(function (c) { return skuOf(c) === skuOf(t); })) candidates.push(t);
      });

      var best = null;
      candidates.forEach(function (target) {
        var delta = 0, raised = [], ok = true, skusAfter = {};
        members.forEach(function (m) {
          if (!ok) return;
          var pick = m.solution.pick;
          if (skuOf(pick.cand) === skuOf(target)) { skusAfter[skuOf(target)] = 1; return; }
          /* never collapse DOWN, and never onto a member this mark did not
             itself check and pass */
          if (target.d_in < pick.cand.d_in) { skusAfter[skuOf(pick.cand)] = 1; return; }
          var alt = m.solution.feasible.filter(function (f) {
            return f.cand.size === target.size && f.cand.species === target.species &&
                   f.cand.grade === target.grade && f.cand.spacing === pick.cand.spacing;
          })[0];
          if (!alt) { ok = false; return; }
          /* compare on SCORE, the same objective the search optimised. Raising a
             member always increases its slack, and cost alone cannot see that. */
          delta += (alt.pieceScore - pick.pieceScore) * pieceCount(m);
          raised.push({ mark: m.mark.id, from: skuOf(pick.cand), to: skuOf(target), row: m, alt: alt });
          skusAfter[skuOf(target)] = 1;
        });
        if (!ok || !raised.length) return;
        var nAfter = Object.keys(skusAfter).length;
        /* the per-SKU handling charge, plus the system bonus that only exists
           when the group actually collapses to a single size */
        /* the system bonus is for collapsing to ONE SIZE — a same-size grade
           swap creates no band, no single rim depth and no single hanger SKU */
        var sizesBefore = {}, sizesAfter = {};
        members.forEach(function (m) { sizesBefore[m.solution.pick.cand.size] = 1; });
        Object.keys(skusAfter).forEach(function (k) { sizesAfter[k.split(" ")[0]] = 1; });
        var collapsedSizes = Object.keys(sizesBefore).length > 1 && Object.keys(sizesAfter).length === 1;
        var saved = (skusBefore - nAfter) * w.skuPenalty +
                    (nAfter === 1 && collapsedSizes ? (own(bonus, g) || 0) : 0);
        if (saved <= 0) return;
        var net = delta - saved;
        if (!best || net < best.net) {
          best = { net: net, delta: delta, saved: saved, target: target, raised: raised,
                   skusAfter: nAfter };
        }
      });

      if (!best) return;
      moves.push({
        group: g, skusBefore: skusBefore, skusAfter: best.skusAfter, target: skuOf(best.target),
        extraLumberUSD: best.delta, skuSavingUSD: best.saved, accepted: best.net <= 0,
        raised: best.raised.map(function (r) { return { mark: r.mark, from: r.from, to: r.to }; })
      });
      if (best.net <= 0) {
        best.raised.forEach(function (r) { r.row.unifiedTo = r.alt; });
      }
    });
    return moves;
  }

  /* A repetitive mark's piece count follows from the run and the spacing the
     solver chose, so it cannot be a fixed number in the plan: quoting a 12 ft
     deck at 16 marks while the solver picks 12" o.c. (which needs 22) makes the
     plan cost meaningless. Non-repetitive marks keep their literal count. */
  function pieceCount(m) {
    var row = m.unifiedTo || (m.solution && m.solution.pick);
    if (row && m.demand && m.demand.repetitive && m.mark.runFt && row.cand.spacing) {
      return Math.ceil(Number(m.mark.runFt) * 12 / row.cand.spacing) + 1;
    }
    return m.mark.count || 1;
  }

  function skuOf(cand) {
    return cand.size + " " + cand.species + " " + cand.grade;
  }
  function shallow(o) {
    var out = {}, k;
    for (k in o) if (Object.prototype.hasOwnProperty.call(o, k)) out[k] = o[k];
    return out;
  }
  function keyOf(cand) {
    return skuOf(cand) + "@" + (cand.spacing || 0);
  }

  function rollup(planResult) {
    var skus = {}, solved = 0, escalated = 0, notApplicable = 0, flagged = 0, totalUSD = 0;
    planResult.marks.forEach(function (m) {
      if (m.notApplicable) { notApplicable++; return; }
      var row = m.unifiedTo || (m.solution && m.solution.pick);
      if (!row) { escalated++; return; }
      solved++;
      var n = pieceCount(m);
      totalUSD += row.cost.totalUSD * n;
      var k = safeKey(skuOf(row.cand));
      if (!Object.prototype.hasOwnProperty.call(skus, k)) skus[k] = 0;
      skus[k] += n;
      if (row.cost.cfBasis === "held") flagged++;
    });
    var windGoverned = !!(planResult.pack && planResult.pack.governs === "wind");
    return {
      solved: solved, escalated: escalated, unsolved: escalated, notApplicable: notApplicable,
      flaggedCF: flagged,
      /* A schedule is not complete while anything is escalated, while any mark
         was removed as not-this-engine, or in a market where wind governs the
         members this engine only checked for gravity. */
      complete: escalated === 0 && notApplicable === 0 && !windGoverned,
      incompleteBecause: escalated ? "marks escalated"
        : (notApplicable ? "marks removed as not this engine's member"
        : (windGoverned ? "wind governs in this market and is not checked here" : null)),
      skuCount: Object.keys(skus).length, skus: skus, lumberUSD: totalUSD
    };
  }

  /* ---------- the repeat matrix ----------
     One plan, several region packs. This is the whole point of a tract plan:
     what actually has to change when the same house is built in another state. */

  function compare(plan, packs) {
    var runs = packs.map(function (p) { return { pack: p, result: solvePlan(plan, p) }; });
    var rows = plan.marks.map(function (mk) {
      var cells = runs.map(function (r) {
        var m = r.result.marks.filter(function (x) { return x.mark.id === mk.id; })[0];
        if (m && m.notApplicable) {
          return { pack: r.pack.id, sku: null, spacing: null, dcr: null, governing: null,
                   notApplicable: true, note: m.notApplicable.reason };
        }
        var row = m && (m.unifiedTo || (m.solution && m.solution.pick));
        return {
          pack: r.pack.id,
          sku: row ? skuOf(row.cand) : null,
          spacing: row ? row.cand.spacing : null,
          dcr: row ? row.dcr : null,
          governing: row ? row.governing : null,
          note: row ? null : (m && m.solution && m.solution.note ? m.solution.note.wall : "no solution")
        };
      });
      var distinct = {};
      cells.forEach(function (c) { if (c.sku) distinct[c.sku + "@" + c.spacing] = 1; });
      var n = Object.keys(distinct).length;
      /* A mark that produced no member anywhere is NOT portable — it is
         unanswered. Counting it as "common to every region" turned silence into
         evidence for the product's central claim. */
      return { mark: mk, cells: cells, everSolved: n > 0,
               varies: n > 1, common: n === 1, unanswered: n === 0 };
    });
    return {
      plan: plan, runs: runs, rows: rows,
      commonMarks: rows.filter(function (r) { return r.common; }).length,
      varyingMarks: rows.filter(function (r) { return r.varies; }).length,
      unansweredMarks: rows.filter(function (r) { return r.unanswered; }).length,
      solvedMarks: rows.filter(function (r) { return r.everSolved; }).length
    };
  }

  FM.solver = {
    size: size, solvePlan: solvePlan, compare: compare,
    seedBounds: seedBounds, families: families, combosFor: combosFor,
    memberInputs: memberInputs, costOf: costOf, skuOf: skuOf, slackPenalty: slackPenalty,
    eligibility: eligibility,
    stockLength: stockLength, boardFeetPerLF: boardFeetPerLF,
    REPAIR: REPAIR, GAMMA_PCF: GAMMA_PCF
  };
})();

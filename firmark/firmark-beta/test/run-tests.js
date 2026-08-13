#!/usr/bin/env node
/* ============================================================
   Regression suite.  Run:  node test/run-tests.js

   Three jobs:
     1. Pin the calc-spec §7.3 fixtures — the engine's own contract.
     2. Pin the engine fixes this branch made, so they cannot rot.
     3. Prove the solver's pruning claims rather than assert them.
        The admissibility test is the load-bearing one: it runs an
        exhaustive search through the real engine and requires the
        pruned search to agree, candidate for candidate.
   ============================================================ */

"use strict";

var FM = require("./harness.js").load(["engine.js", "weights.js", "solver.js"]);

var pass = 0, fail = 0, current = "";
var failures = [];

function suite(name) { current = name; console.log("\n" + name); }
function ok(msg) { pass++; console.log("  ✓ " + msg); }
function bad(msg, detail) {
  fail++;
  failures.push(current + " :: " + msg + (detail ? "\n      " + detail : ""));
  console.log("  ✗ " + msg + (detail ? "\n      " + detail : ""));
}
function eq(actual, expected, msg) {
  if (actual === expected) ok(msg);
  else bad(msg, "expected " + JSON.stringify(expected) + ", got " + JSON.stringify(actual));
}
function near(actual, expected, tol, msg) {
  if (typeof actual === "number" && isFinite(actual) && Math.abs(actual - expected) <= tol) ok(msg);
  else bad(msg, "expected " + expected + " ± " + tol + ", got " + actual);
}
function truthy(v, msg) { if (v) ok(msg); else bad(msg); }

/* ============================================================
   1. calc-spec §7 — Example 1, 2x10 DF-L No.2 rafter @ 16" o.c.
   ============================================================ */

var EX1 = {
  species: "Douglas Fir-Larch", grade: "No. 2", size: "2x10",
  span: 13.0, spacing: 16, dead: 15, live: 0, roofLoad: 30, roofType: "snow",
  repetitive: true, wet: false, braced: true, bearing: 3.5,
  memberUse: "roof_nonplaster", CF: 1.1
};

function copy(o, over) {
  var out = {}, k;
  for (k in o) if (Object.prototype.hasOwnProperty.call(o, k)) out[k] = o[k];
  for (k in (over || {})) if (Object.prototype.hasOwnProperty.call(over, k)) out[k] = over[k];
  return out;
}
function checkOf(r, name) {
  return r.checks.filter(function (c) { return c.name === name; })[0];
}

suite("calc-spec §7.3 — regression fixtures");
(function () {
  var sec = FM.engine.findSection("2x10");
  near(sec.A_in2, 13.875, 1e-6, "geom_2x10_table1b · A = 13.875 in² read from Table 1B");
  near(sec.Sx_in3, 21.390625, 1e-6, "geom_2x10_table1b · S_x = 21.390625 in³");
  near(sec.Ix_in4, 98.931641, 1e-6, "geom_2x10_table1b · I_x = 98.931641 in⁴");

  var r = FM.engine.run(EX1);
  truthy(!r.error, "ex1 evaluates without error");
  near(checkOf(r, "Bending").dcr, 0.543, 0.001, "ex1_2x10_dfl_no2_rafter · bending DCR 0.543, D + S");
  eq(checkOf(r, "Bending").combo, "D + S", "ex1 bending governed by D + S");
  near(checkOf(r, "Shear").dcr, 0.204, 0.001, "ex1_shear_no_d_reduction · 0.204");
  near(checkOf(r, "Bearing (Fc⊥)").dcr, 0.119, 0.001, "ex1_bearing · 0.119 (C_b = 1.0, no C_D)");
  near(checkOf(r, "Deflection (live)").dcr, 0.250, 0.001, "ex1_defl_live · 0.250 at L/240");

  /* zero-magnitude terms must not set C_D — calc-spec §2.3 rule 1 */
  var dOnly = FM.engine.run(copy(EX1, { roofLoad: 0, live: 0 }));
  near(checkOf(dOnly, "Bending").dcr, 0.231, 0.001,
       "ex1_bending_D_only · 0.231 — C_D = 0.90 because L and Lr are zero, not 1.00");

  /* full C_L derivation, l_u/d > 14.3 band */
  var unb = FM.engine.run(copy(EX1, { braced: false }));
  near(checkOf(unb, "Bending").dcr, 1.252, 0.002, "ex1b_unbraced · 1.252 FAIL via the C_L path");
  truthy(checkOf(unb, "Bending").dcr > 1, "ex1b_unbraced is reported as failing");
})();

suite("calc-spec §5.5 — KNOWN CONFLICT, pinned not resolved");
(function () {
  var r = FM.engine.run(EX1);
  var dt = checkOf(r, "Deflection (total)").dcr;
  near(dt, 0.281, 0.001,
       "ex1_defl_total · engine returns 0.281 (roof_nonplaster total = L/180)");
  console.log("      NOTE: calc-spec §5.5 fixture expects 0.375 (L/240). The two documents");
  console.log("      shipped in this repo disagree on IBC Table 1604.3's D+L column for the");
  console.log("      nonplaster roof row. Engine behaviour is pinned here so the conflict");
  console.log("      cannot be closed silently. See solver-spec.md §9.1.");
})();

/* ============================================================
   2. Engine fixes made on this branch
   ============================================================ */

suite("engine fix · nominal-to-dressed size-class matching");
(function () {
  /* Table 4B is tabulated per nominal width; the matcher used (nominal - 0.75)
     for every width, which is only right at 8" and wider. 2x4 and 2x6 vanished. */
  ["2x4", "2x6", "2x8", "2x10", "2x12"].forEach(function (sz) {
    var sec = FM.engine.findSection(sz);
    var v = FM.engine.findValues("Southern Pine", "No.2", sec.d_in);
    truthy(v && v.values_psi && v.values_psi.Fb > 0, "Southern Pine No.2 resolves at " + sz);
  });
  var sec14 = FM.engine.findSection("2x14");
  eq(FM.engine.findValues("Southern Pine", "No.2", sec14.d_in), null,
     "Southern Pine No.2 correctly NOT found at 2x14 — Table 4B stops at 12\" wide");

  /* the timber rows dress differently (8x8 is 7.5 deep, 2x8 is 7.25) and must
     not seed the map */
  var v8 = FM.engine.findValues("Southern Pine", "No.2", 7.25);
  truthy(v8 && v8.size_class === "8\" wide", "2x8 depth 7.25 maps to the '8\" wide' row, not a timber row");

  /* Table 4A species are unaffected */
  ["2x4", "2x8", "2x12", "2x14"].forEach(function (sz) {
    var s = FM.engine.findSection(sz);
    var v = FM.engine.findValues("Douglas Fir-Larch", "No. 2", s.d_in);
    truthy(v && /wider/.test(v.size_class), "DF-L No. 2 still resolves via '2\" & wider' at " + sz);
  });
})();

suite("engine fix · Southern Pine is selectable");
(function () {
  var list = FM.engine.speciesList();
  var sp = list.filter(function (s) { return s.species === "Southern Pine"; })[0];
  truthy(sp, "speciesList() includes Southern Pine");
  truthy(sp && sp.grades.indexOf("No.2") !== -1, "Southern Pine exposes its No.2 grade");
  truthy(list.filter(function (s) { return s.species === "Douglas Fir-Larch"; })[0],
         "Table 4A species are still listed");
})();

suite("engine · C_F provenance and the 14-inch refusal");
(function () {
  var sp = FM.engine.sizeFactor("Southern Pine", "No.2", "2x10");
  eq(sp.CF, 1, "Southern Pine C_F = 1.00");
  eq(sp.basis, "table_4b", "Southern Pine C_F basis is Table 4B — already in the value");

  var dfl = FM.engine.sizeFactor("Douglas Fir-Larch", "No. 2", "2x10");
  near(dfl.CF, 1.1, 1e-9, "DF-L No. 2 2x10 C_F = 1.10 from the catalog helper");
  eq(dfl.basis, "repo_partial", "and it is flagged repo_partial, not sourced");

  var thick = FM.engine.sizeFactor("Douglas Fir-Larch", "No. 2", "4x10");
  eq(thick.CF, 1, "4x stock holds C_F at 1.00");
  eq(thick.basis, "held", "and says so — the catalog carries the 2\"-thick column only");

  var wide = FM.engine.sizeFactor("Douglas Fir-Larch", "No. 2", "2x14");
  eq(wide.refuse, true, "14\" and wider is refused, not held at 1.00");
  var r = FM.engine.run(copy(EX1, { size: "2x14", CF: "auto" }));
  eq(r.error, true, "run() with CF auto refuses a 2x14 rather than guess");

  var auto = FM.engine.run(copy(EX1, { CF: "auto" }));
  near(checkOf(auto, "Bending").dcr, checkOf(FM.engine.run(EX1), "Bending").dcr, 1e-12,
       "CF auto reproduces the typed C_F = 1.10 exactly");
})();

/* ============================================================
   3. Solver
   ============================================================ */

function policy(role, packId) {
  return FM.weights.policyFor(FM.weights.packById(packId || "nc-piedmont"), null, role || "rafter");
}

suite("solver · load combinations match the engine");
(function () {
  var cases = [
    { D: 15, L: 0, Lr: 20, t: "roof_live" },
    { D: 15, L: 0, Lr: 25, t: "snow" },
    { D: 12, L: 40, Lr: 0, t: "snow" },
    { D: 15, L: 40, Lr: 20, t: "roof_live" },
    { D: 10, L: 0, Lr: 0, t: "snow" }
  ];
  var allMatch = true, detail = "";
  cases.forEach(function (c) {
    var mine = FM.solver.combosFor(c.D, c.L, c.Lr, c.t);
    var r = FM.engine.run({
      species: "Southern Pine", grade: "No.2", size: "2x10", span: 12, spacing: 16,
      dead: c.D, live: c.L, roofLoad: c.Lr, roofType: c.t, repetitive: true,
      wet: false, braced: true, bearing: 3, memberUse: "floor", CF: "auto"
    });
    if (r.error) { allMatch = false; detail += "engine errored on " + JSON.stringify(c) + "; "; return; }
    if (mine.length !== r.combos.length) {
      allMatch = false;
      detail += JSON.stringify(c) + " count " + mine.length + " vs " + r.combos.length + "; ";
      return;
    }
    mine.forEach(function (m, i) {
      if (Math.abs(m.psf - r.combos[i].psf) > 1e-9 || Math.abs(m.cd - r.combos[i].cd) > 1e-9) {
        allMatch = false;
        detail += JSON.stringify(c) + " combo " + i + " " + m.psf + "/" + m.cd +
                  " vs " + r.combos[i].psf + "/" + r.combos[i].cd + "; ";
      }
    });
  });
  truthy(allMatch, "solver combosFor() reproduces engine combinations across " + cases.length + " load cases");
  if (!allMatch) console.log("      " + detail);
})();

suite("solver · self-weight equivalence, calc-spec §1.3(b)");
(function () {
  var demand = { role: "beam", span: 10, trib: 6, repetitive: false, dead: 15, live: 0,
                 roofLoad: 20, roofType: "roof_live", braced: false, wet: false,
                 bearing: 3.5, memberUse: "roof_no_ceiling" };
  var cand = { species: "Southern Pine", grade: "No.2", size: "4x10", spacing: 0 };
  var inp = FM.solver.memberInputs(demand, cand, policy("beam"));
  var sec = FM.engine.findSection("4x10");
  var wswExpected = FM.solver.GAMMA_PCF * sec.A_in2 / 144;          /* plf */
  var wswActual = inp.selfWeightPsf * demand.trib;                   /* psf x ft = plf */
  near(wswActual, wswExpected, 1e-9,
       "beam self-weight added as psf over the tributary width reproduces γA/144 plf exactly");
  near(inp.spacing, demand.trib * 12, 1e-9, "tributary width is passed as spacing = trib x 12");

  var rep = FM.solver.memberInputs(
    { role: "rafter", span: 13, repetitive: true, dead: 15, live: 0, roofLoad: 20,
      roofType: "roof_live", braced: true, wet: false, bearing: 3, memberUse: "roof_nonplaster" },
    { species: "Southern Pine", grade: "No.2", size: "2x8", spacing: 16 }, policy("rafter"));
  eq(rep.selfWeightPsf, 0, "repetitive members add no self-weight — it is already inside q_D");
})();

/* ---- the load-bearing test: pruning cannot change the answer ---- */

function exhaustive(demand, pol) {
  var rows = [];
  pol.palette.forEach(function (p, pi) {
    var spacings = demand.repetitive ? pol.spacings : [0];
    pol.ladder.forEach(function (sz) {
      var sec = FM.engine.findSection(sz);
      if (!sec) return;
      spacings.forEach(function (sp) {
        var cand = { species: p.species, grade: p.grade, size: sz, spacing: sp,
                     b_in: sec.b_in, d_in: sec.d_in, paletteIndex: pi };
        /* the brute-force reference must respect the same POLICY gates the
           solver does — they are deliberate filters, not search heuristics */
        if (!FM.solver.eligibility(cand, demand, pol).ok) return;
        var r = FM.engine.run(FM.solver.memberInputs(demand, cand, pol));
        if (r.error || !isFinite(r.governing.dcr)) return;
        if (r.governing.dcr > pol.maxDCR + 1e-9) return;
        var cost = FM.solver.costOf(demand, cand, pol);
        rows.push({ key: sz + "|" + p.species + "|" + p.grade + "|" + sp,
                    score: cost.totalUSD + FM.solver.slackPenalty(r.governing.dcr, pol),
                    dcr: r.governing.dcr, cand: cand });
      });
    });
  });
  rows.sort(function (a, b) {
    if (Math.abs(a.score - b.score) > 1e-9) return a.score - b.score;
    if (a.cand.d_in !== b.cand.d_in) return a.cand.d_in - b.cand.d_in;
    if (a.cand.b_in !== b.cand.b_in) return a.cand.b_in - b.cand.b_in;
    if (a.cand.paletteIndex !== b.cand.paletteIndex) return a.cand.paletteIndex - b.cand.paletteIndex;
    return b.cand.spacing - a.cand.spacing;
  });
  return rows;
}

function battery() {
  var out = [];
  var packs = FM.weights.PACKS;
  var spans = { rafter: [10, 13.5, 16, 19], ceiling: [9, 12, 15], joist: [10, 14, 17],
                header: [3, 6, 10, 16], beam: [8, 12, 16] };
  packs.forEach(function (pk) {
    ["rafter", "ceiling", "joist", "header", "beam"].forEach(function (role) {
      spans[role].forEach(function (span) {
        [true, false].forEach(function (braced) {
          var mark = { id: "T", label: "t", role: role, span: span, trib: 7, count: 1, braced: braced };
          var d = FM.weights.demandFor(mark, { marks: [] }, pk);
          out.push({ demand: d, pol: FM.weights.policyFor(pk, null, role),
                     label: pk.id + "/" + role + "/" + span + "ft/" + (braced ? "braced" : "unbraced") });
        });
      });
    });
  });
  return out;
}

suite("solver · pruning is admissible — exhaustive vs pruned");
(function () {
  var cases = battery();
  var mismatches = [], checked = 0, totalSaved = 0, totalSpace = 0;
  cases.forEach(function (c) {
    var brute = exhaustive(c.demand, c.pol);
    var sol = FM.solver.size(c.demand, c.pol);
    checked++;
    totalSpace += sol.searchSpace;
    totalSaved += sol.searchSpace - sol.stats.evaluated;

    var bruteWin = brute[0] ? brute[0].key : null;
    var solWin = sol.pick ? (sol.pick.cand.size + "|" + sol.pick.cand.species + "|" +
                             sol.pick.cand.grade + "|" + sol.pick.cand.spacing) : null;
    if (bruteWin !== solWin) {
      mismatches.push(c.label + ": exhaustive picked " + bruteWin + ", solver picked " + solWin);
      return;
    }
    /* and nothing the solver pruned was actually feasible-and-better */
    if (brute[0] && sol.pick) {
      var ds = Math.abs(brute[0].score - sol.pick.score);
      if (ds > 1e-6) mismatches.push(c.label + ": score drift " + ds);
    }
  });
  truthy(mismatches.length === 0,
         "solver agrees with exhaustive search on all " + checked + " demands");
  if (mismatches.length) {
    mismatches.slice(0, 8).forEach(function (m) { console.log("      " + m); });
    console.log("      (" + mismatches.length + " total)");
  }
  console.log("      pruned " + totalSaved + " of " + totalSpace + " candidate evaluations (" +
              Math.round(100 * totalSaved / totalSpace) + "%)");
})();

suite("solver · determinism, calc-spec §6.2");
(function () {
  var pk = FM.weights.packById("fl-central");
  var mark = { id: "R", label: "r", role: "rafter", span: 14, count: 1 };
  var d = FM.weights.demandFor(mark, { marks: [] }, pk);

  var base = FM.solver.size(d, FM.weights.policyFor(pk, null, "rafter"));
  var again = FM.solver.size(d, FM.weights.policyFor(pk, null, "rafter"));
  eq(FM.solver.skuOf(again.pick.cand), FM.solver.skuOf(base.pick.cand), "repeat run gives the same pick");

  /* shuffled palette and ladder must not move the answer */
  var pol = FM.weights.policyFor(pk, null, "rafter");
  pol.palette = pol.palette.slice().reverse();
  pol.ladder = pol.ladder.slice().reverse();
  var shuffled = FM.solver.size(d, pol);
  eq(FM.solver.skuOf(shuffled.pick.cand), FM.solver.skuOf(base.pick.cand),
     "reversing palette and ladder order gives the same pick");
})();

suite("solver · Rule 2: no weight can make a member pass");
(function () {
  var pk = FM.weights.packById("nc-mountain");
  var mark = { id: "R", label: "r", role: "rafter", span: 18, count: 1 };
  var d = FM.weights.demandFor(mark, { marks: [] }, pk);

  var normal = FM.solver.size(d, FM.weights.policyFor(pk, null, "rafter"));
  var normalSet = normal.feasible.map(function (f) { return FM.solver.skuOf(f.cand) + "@" + f.cand.spacing; }).sort().join(",");

  /* drive every weight to an absurd value in both directions */
  [0, 1e6].forEach(function (v) {
    var pol = FM.weights.policyFor(pk, null, "rafter");
    var w = {};
    for (var k in pol.weights) if (Object.prototype.hasOwnProperty.call(pol.weights, k)) w[k] = v;
    w.baseBfUSD = v || 0.01;
    pol.weights = w;
    var wild = FM.solver.size(d, pol);
    var wildSet = wild.feasible.map(function (f) { return FM.solver.skuOf(f.cand) + "@" + f.cand.spacing; }).sort().join(",");
    eq(wildSet, normalSet, "feasible set unchanged with every weight set to " + v);
    wild.feasible.forEach(function (f) {
      if (f.dcr > pol.maxDCR + 1e-9) bad("a member above the DCR target entered the feasible set at weight " + v);
    });
  });
  truthy(normal.feasible.every(function (f) { return f.dcr <= 0.9 + 1e-9; }),
         "every member in the feasible set is at or under the firm DCR target");
})();

suite("solver · SKU unification only ever collapses upward");
(function () {
  var pk = FM.weights.packById("tx-i35");
  var plan = FM.weights.planById("two-story-2450");
  var res = FM.solver.solvePlan(plan, pk);
  var violations = [];
  (res.unified || []).forEach(function (u) {
    if (!u.accepted) return;
    u.raised.forEach(function (r) {
      var m = res.marks.filter(function (x) { return x.mark.id === r.mark; })[0];
      if (!m || !m.unifiedTo) return;
      if (m.unifiedTo.cand.d_in < m.solution.pick.cand.d_in) {
        violations.push(r.mark + " was collapsed DOWN from " + m.solution.pick.cand.size +
                        " to " + m.unifiedTo.cand.size);
      }
      if (m.unifiedTo.dcr > m.policy.maxDCR + 1e-9) {
        violations.push(r.mark + " unified onto a member above the DCR target");
      }
      var inOwnSet = m.solution.feasible.some(function (f) {
        return f.cand.size === m.unifiedTo.cand.size && f.cand.species === m.unifiedTo.cand.species;
      });
      if (!inOwnSet) violations.push(r.mark + " unified onto a member absent from its own feasible set");
    });
  });
  truthy(violations.length === 0, "no mark was weakened, downsized, or unified onto an unchecked member");
  violations.forEach(function (v) { console.log("      " + v); });
})();

suite("solver · every pack solves every plan without throwing");
(function () {
  var problems = [], solved = 0, unsolved = 0;
  FM.weights.PACKS.forEach(function (pk) {
    FM.weights.PLANS.forEach(function (pl) {
      try {
        var res = FM.solver.solvePlan(pl, pk);
        solved += res.rollup.solved;
        unsolved += res.rollup.escalated;
        res.marks.forEach(function (m) {
          if (m.notApplicable) {
            if (!m.notApplicable.note) problems.push(pk.id + "/" + pl.id + "/" + m.mark.id + " not applicable with no reason");
            return;
          }
          var row = m.unifiedTo || m.solution.pick;
          if (row && !isFinite(row.dcr)) problems.push(pk.id + "/" + pl.id + "/" + m.mark.id + " non-finite DCR");
          if (!row && !m.solution.note) problems.push(pk.id + "/" + pl.id + "/" + m.mark.id + " no pick and no explanation");
          if (!row && m.solution.status.indexOf("escalate") !== 0) problems.push(pk.id + "/" + pl.id + "/" + m.mark.id + " unsolved but not escalated");
        });
      } catch (e) {
        problems.push(pk.id + "/" + pl.id + " threw: " + e.message);
      }
    });
  });
  truthy(problems.length === 0,
         FM.weights.PACKS.length + " packs x " + FM.weights.PLANS.length + " plans solve cleanly (" +
         solved + " marks solved, " + unsolved + " escalated, each explained)");
  problems.forEach(function (p) { console.log("      " + p); });
})();

suite("solver · a member with no solid-sawn answer says why");
(function () {
  var pk = FM.weights.packById("tx-i35");
  var plan = FM.weights.planById("sunbelt-ranch-1850");
  var res = FM.solver.solvePlan(plan, pk);
  var garage = res.marks.filter(function (m) { return m.mark.id === "HDR-GAR-B"; })[0];
  truthy(garage && !garage.solution.pick, "the 16 ft garage header finds no solid-sawn solution");
  truthy(garage && garage.solution.note && garage.solution.note.wall,
         "and reports which limit state was the wall");
  truthy(garage && /engineered/i.test(garage.solution.note.outOfScope),
         "and points at the engineered header that is out of this engine's scope");
})();


suite("engine fix · thickness descriptors constrain breadth");
(function () {
  /* Dense Structural 65/72/86 carry both a '2" & wider' row and a
     '2-1/2" - 4" thick' row. Treating the thickness descriptor as a blanket
     match let a 1.5"-thick 2x10 read its values off the thicker row — and the
     tie-break prefers the non-"wider" descriptor, so it won. */
  var thin = FM.engine.findValues("Southern Pine", "Dense Structural 65", 9.25, 1.5);
  truthy(thin && /wider/.test(thin.size_class),
         "a 1.5 in thick 2x10 resolves to the '2\" & wider' row, not the 2-1/2\"-4\" thick row");
  var thick = FM.engine.findValues("Southern Pine", "Dense Structural 65", 9.25, 2.5);
  truthy(thick && /thick/.test(thick.size_class),
         "a 2.5 in thick 3x10 does resolve to the thickness row");
  /* documented side effect of the dressed-depth fix: the 2"-4" wide range now
     spans 1.5-3.5 instead of 1.25-3.25, so 4"-nominal rows resolve at d = 3.5 */
  var c = FM.engine.findValues("Douglas Fir-Larch", "Construction", 3.5, 1.5);
  truthy(c && c.values_psi.Fb > 0, "DF-L Construction resolves at 2x4 (d = 3.5) after the range fix");
})();

suite("solver · incumbent pruning survives a non-monotone price vector");
(function () {
  /* A per-size price vector is a supported input, so cost need not grow with
     depth. Breaking out of a family on the incumbent bound without checking
     monotonicity skipped cheaper deeper rungs. */
  var pk = FM.weights.packById("nc-piedmont");
  var pol = FM.weights.policyFor(pk, null, "joist");
  pol.palette = [{ species: "Southern Pine", grade: "No.2", bfUSD: 0.70, stockFactor: 1, cullRate: 0 }];
  var odd = { "2x8": 0.70, "2x10": 9.00, "2x12": 0.20 };   /* short supply, then clearance */
  pol.priceOf = function (cand) {
    return { bfUSD: odd[cand.size] || 0.7, cullRate: 0, availability: 1 };
  };
  var d = FM.weights.demandFor({ id: "T", role: "joist", span: 11, count: 1 }, { marks: [] }, pk);
  var sol = FM.solver.size(d, pol);
  var brute = exhaustive(d, pol);
  truthy(sol.pick && brute[0], "both searches find a member under the odd price vector");
  eq(sol.pick && (sol.pick.cand.size + "|" + sol.pick.cand.spacing),
     brute[0] && brute[0].key.split("|")[0] + "|" + brute[0].cand.spacing,
     "solver still agrees with exhaustive when cost is not monotone in depth");
})();

suite("solver · SKU unification actually fires");
(function () {
  /* H7 was structurally dead while `feasible` held only what the optimiser
     evaluated: the dominance break stopped each family at its first feasible
     rung, so a sibling mark's deeper size was never in the list to raise onto.
     The explain pass is what makes this reachable. */
  var fired = [], groupsSeen = 0;
  FM.weights.PACKS.forEach(function (pk) {
    FM.weights.PLANS.forEach(function (pl) {
      var res = FM.solver.solvePlan(pl, pk);
      (res.unified || []).forEach(function (u) {
        groupsSeen++;
        if (u.accepted) fired.push(pk.id + "/" + pl.id + "/" + u.group + " -> " + u.target);
      });
    });
  });
  truthy(groupsSeen > 0, "unification evaluated " + groupsSeen + " multi-SKU groups");
  truthy(fired.length > 0, "and accepted " + fired.length + " of them — H7 is reachable, not dead");
  if (fired.length) console.log("      e.g. " + fired[0]);
})();

suite("solver · gates are recorded, not silent");
(function () {
  var pk = FM.weights.packById("nc-mountain");
  /* a treated exterior beam must not be checked in an incised species */
  var d = FM.weights.demandFor(
    { id: "B", role: "beam", span: 10, trib: 6, exposure: "exterior", braced: false },
    { marks: [] }, pk);
  truthy(d.wet, "an exterior mark in this pack is wet service");
  var sol = FM.solver.size(d, FM.weights.policyFor(pk, null, "beam"));
  var incised = sol.rejected.filter(function (r) { return r.gate === "scope"; });
  truthy(incised.length > 0, "treated Douglas Fir-Larch is excluded, with the C_i reason recorded");
  truthy(!sol.pick || !FM.weights.INCISED_WHEN_TREATED[sol.pick.cand.species],
         "and no incised species can be the pick on a wet mark");

  /* the geometry gate */
  var hd = FM.weights.demandFor(
    { id: "H", role: "header", span: 6, trib: 8, headHeightIn: 80 }, { marks: [] }, pk);
  near(hd.maxDepthIn, 109.125 - 80 - 3.5, 1e-9, "header depth budget comes from plate minus head height");
  var hs = FM.solver.size(hd, FM.weights.policyFor(pk, null, "header"));
  truthy(!hs.pick || hs.pick.cand.d_in <= hd.maxDepthIn + 1e-9,
         "no header deeper than the space above the head height is ever picked");
})();

suite("solver · end reactions are published");
(function () {
  var pk = FM.weights.packById("fl-central");
  var d = FM.weights.demandFor({ id: "B", role: "beam", span: 12, trib: 7, exposure: "exterior", braced: false },
                               { marks: [] }, pk);
  var sol = FM.solver.size(d, FM.weights.policyFor(pk, null, "beam"));
  truthy(sol.pick, "the lanai beam solves");
  truthy(sol.reactions && sol.reactions.perBearingLb > 0,
         "and reports its end reaction (" + (sol.reactions ? Math.round(sol.reactions.perBearingLb) : "—") +
         " lb) for the connector designer");
})();

suite("weights · packs are internally coherent");
(function () {
  FM.weights.PACKS.forEach(function (p) {
    truthy(p.loads && FM.weights.ASSEMBLY[p.loads.roofAssembly], p.id + " names a known roof assembly");
    truthy(p.loads.roofType === "snow" || p.loads.roofType === "roof_live", p.id + " declares a roof load type");
    truthy(typeof p.loads.roofLoadBasis === "string" && p.loads.roofLoadBasis.length > 40,
           p.id + " explains where its roof load came from");
    truthy(p.palette.length > 0, p.id + " has a species palette");
    var bad2 = p.palette.filter(function (s) {
      return !FM.engine.speciesList().some(function (e) {
        return e.species === s.species && e.grades.indexOf(s.grade) !== -1;
      });
    });
    truthy(bad2.length === 0, p.id + " palette species/grades all exist in the catalog" +
           (bad2.length ? " — missing: " + bad2.map(function (x) { return x.species + " " + x.grade; }).join(", ") : ""));
    if (p.governs === "wind") {
      truthy(typeof p.governsNote === "string" && p.governsNote.length > 40,
             p.id + " is wind-governed and says so in words the UI can print");
    }
  });
  Object.keys(FM.weights.LADDERS).forEach(function (role) {
    var wide = FM.weights.LADDERS[role].filter(function (sz) {
      return FM.engine.sizeFactor("Douglas Fir-Larch", "No. 2", sz).refuse;
    });
    truthy(wide.length === 0, "the " + role + " ladder offers nothing the engine must refuse for C_F");
  });
})();

/* ============================================================ */

console.log("\n" + (fail ? "✗ " : "✓ ") + pass + " passed, " + fail + " failed");
if (fail) {
  console.log("\nFAILURES");
  failures.forEach(function (f) { console.log("  - " + f); });
  process.exit(1);
}

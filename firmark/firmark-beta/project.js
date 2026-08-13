/* ============================================================
   project.js — the run, and the wiring between stages.

   Everything before this file is a module that does one thing well.
   This is the file that says how they connect: a project holds the
   geometry, the jurisdiction, the takeoff, the calculations and the
   bill of materials, and it recomputes downstream state when
   something upstream changes.

   WHY RECOMPUTE RATHER THAN CACHE
   -------------------------------
   Because a cached downstream result that outlives its input is the
   same defect as an approval that outlives what was approved, and
   this codebase has now been bitten by that shape four times: a stale
   bundle, a stale coverage headline, a stale reaction figure in prose,
   and an approval with no fingerprint. Derived state is derived on
   demand. Where that is too slow, it is memoised against a
   fingerprint of its input and NEVER against a flag someone has to
   remember to clear.

   The pipeline's gates read from here through FM.pipeline.provide(),
   so the fingerprint a gate records is a fingerprint of exactly what
   the stage view displayed.
   ============================================================ */

(function () {
  "use strict";

  var KEY = "fm-project";

  var state = null;

  function blank() {
    return {
      name: "Untitled run",
      /* geometry */
      model: null,
      /* loads and code */
      jurisId: null,
      packId: null,           /* the weights.js region pack that carries the loads */
      planId: null,           /* when the run is driven from a shipped plan */
      variantId: null,
      /* everything else is DERIVED and never stored */
      at: new Date().toISOString()
    };
  }

  function load() {
    if (state) return state;
    try {
      var raw = localStorage.getItem(KEY);
      state = raw ? JSON.parse(raw) : blank();
    } catch (e) { state = blank(); }
    if (!state) state = blank();
    return state;
  }

  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(load())); } catch (e) {}
  }

  function set(patch) {
    var s = load();
    for (var k in patch) if (Object.prototype.hasOwnProperty.call(patch, k)) s[k] = patch[k];
    s.at = new Date().toISOString();
    save();
    return s;
  }

  function reset() { state = blank(); save(); return state; }

  /* ---------------- memoisation, keyed on content ----------------

     A memo entry is valid only while the fingerprint of its input is
     unchanged. There is no invalidate() to forget to call. */

  var memo = {};

  function derive(name, input, fn) {
    if (input === null || input === undefined) return null;
    var fp = FM.pipeline ? FM.pipeline.fingerprint(input) : String(input);
    if (memo[name] && memo[name].fp === fp) return memo[name].value;
    var value;
    try { value = fn(input); }
    catch (e) {
      /* A stage that throws must not look like a stage that produced
         nothing — those are different facts and the gate treats them
         differently. */
      value = { error: true, message: e.message,
                where: name,
                note: "This stage threw rather than returning a result. That is a defect, " +
                      "not an empty input — the gate stays closed and this text is the reason." };
    }
    memo[name] = { fp: fp, value: value };
    return value;
  }

  /* ---------------- the derived chain ---------------- */

  function model() {
    var s = load();
    if (s.model) return s.model;
    /* A run driven from a shipped plan gets its geometry from that plan, so
       the demo has real walls without anyone drawing. This is derived, not
       stored, so editing the plan cannot leave a stale model behind. */
    if (s.planId && FM.cad && FM.cad.fromPlan) {
      return derive("model", { planId: s.planId, variantId: s.variantId }, function (k) {
        return FM.cad.fromPlan(k.planId, k.variantId);
      });
    }
    return null;
  }

  function modelIssues() {
    var m = model();
    if (!m || !FM.cad || !FM.cad.validate) return [];
    return derive("modelIssues", m, function (mm) { return FM.cad.validate(mm); }) || [];
  }

  function takeoff() {
    var m = model();
    if (!m || !FM.takeoff || !FM.takeoff.run) return null;
    return derive("takeoff", m, function (mm) { return FM.takeoff.run(mm, {}); });
  }

  function pack() {
    var s = load();
    if (!FM.weights) return null;
    if (s.packId) return FM.weights.packById(s.packId);
    /* a jurisdiction picks the pack, and says how well it fits */
    if (s.jurisId && FM.juris && FM.juris.packFor) {
      var p = FM.juris.packFor(s.jurisId);
      if (p && p.packId) return FM.weights.packById(p.packId);
    }
    return null;
  }

  function site() {
    var s = load();
    if (!s.jurisId || !FM.juris || !FM.juris.forSite) return null;
    return derive("site", s.jurisId, function (id) { return FM.juris.forSite(id); });
  }

  /* The plan the solver consumes. Either a shipped plan (with its variant) or
     one assembled from the takeoff's marks. */
  function plan() {
    var s = load();
    if (s.planId && FM.weights) {
      var base = FM.weights.planById(s.planId);
      if (!base) return null;
      if (s.variantId && FM.weights.planForVariant) {
        try { return FM.weights.planForVariant(base, s.variantId); } catch (e) { return base; }
      }
      return base;
    }
    var t = takeoff();
    if (!t || t.error || !t.marks || !t.marks.length) return null;
    var m = model();
    return {
      id: "run",
      name: (m && m.name) || s.name || "Untitled run",
      summary: "Assembled from the drawn geometry by the takeoff.",
      lots: 1,
      marks: t.marks,
      geometry: (m && m.geometry) || {},
      note: "This plan was derived from geometry in this session, not from a " +
            "shipped master set. Its marks carry the takeoff's derivations."
    };
  }

  function calcs() {
    var pl = plan(), pk = pack();
    if (!pl || !pk || !FM.solver) return null;
    return derive("calcs", { plan: pl, pack: pk.id }, function () {
      return FM.solver.solvePlan(pl, pk);
    });
  }

  function bom() {
    var c = calcs();
    if (!c || c.error || !FM.bom || !FM.bom.build) return null;
    var s = load();
    return derive("bom", { calcs: c, lots: (plan() || {}).lots }, function () {
      return FM.bom.build(c, { lots: (plan() || {}).lots || 1, variantId: s.variantId });
    });
  }

  function planset() {
    if (!FM.planset || !FM.planset.build) return null;
    var ctx = {
      project: load(), model: model(), takeoff: takeoff(),
      planResult: calcs(), bom: bom(), juris: site(),
      pipeline: FM.pipeline ? FM.pipeline.snapshot() : null
    };
    return derive("planset", {
      m: model(), t: takeoff(), c: calcs(), b: bom(), j: site(),
      /* the approval trail is part of the package, so it is part of the key */
      p: FM.pipeline ? FM.pipeline.state().stages : null
    }, function () { return FM.planset.build(ctx); });
  }

  /* ---------------- wiring the gates ----------------

     Each stage's content provider returns exactly what the stage view shows,
     so the fingerprint recorded at approval is a fingerprint of what the
     approver looked at. Each stage's blockers are the things that must be
     resolved before a person is allowed to put their name on it. */

  function wire() {
    if (!FM.pipeline) return;

    FM.pipeline.provide("geometry", function () { return model(); });
    FM.pipeline.blocksOn("geometry", function () {
      var m = model();
      if (!m) return ["no geometry yet — draw a plan or start from a master set"];
      var errs = modelIssues().filter(function (i) { return i.severity === "error"; });
      return errs.map(function (i) { return "geometry: " + i.text; });
    });

    FM.pipeline.provide("takeoff", function () { return takeoff(); });
    FM.pipeline.blocksOn("takeoff", function () {
      var t = takeoff();
      if (!t) return ["no takeoff yet"];
      if (t.error) return ["the takeoff failed: " + t.message];
      var out = [];
      if (!t.marks || !t.marks.length) out.push("the takeoff produced no marks");
      (t.unresolved || []).forEach(function (u) {
        out.push("unresolved: " + (u.what || "") + " — " + (u.need || u.why || "needs a human answer"));
      });
      return out;
    });

    FM.pipeline.provide("loads", function () {
      var s = load(), pk = pack();
      return pk ? { jurisId: s.jurisId, packId: pk.id, site: site() } : null;
    });
    FM.pipeline.blocksOn("loads", function () {
      var s = load(), out = [];
      if (!s.jurisId) out.push("no jurisdiction chosen — the code edition and site loads depend on it");
      if (!pack()) out.push("no load basis — a region pack must be selected or derived");
      return out;
    });

    FM.pipeline.provide("calcs", function () {
      var c = calcs();
      if (!c) return null;
      /* the marks and their outcomes, not the whole object — a fingerprint
         over transient internals would go stale for no reason */
      return c.marks.map(function (m) {
        var row = m.unifiedTo || (m.solution && m.solution.pick);
        return {
          id: m.mark.id,
          sku: row ? FM.solver.skuOf(row.cand) : null,
          dcr: row ? Math.round(row.dcr * 1000) / 1000 : null,
          status: m.notApplicable ? ("na:" + m.notApplicable.reason)
                : (m.solution ? m.solution.status : "none")
        };
      });
    });
    FM.pipeline.blocksOn("calcs", function () {
      var c = calcs();
      if (!c) return ["nothing has been calculated yet"];
      if (c.error) return ["the calculation failed: " + c.message];
      return [];   /* escalations do NOT block — accepting them is the point of the gate */
    });

    FM.pipeline.provide("bom", function () {
      var b = bom();
      return b && !b.error ? { lines: b.lines, totals: b.totals } : null;
    });
    FM.pipeline.blocksOn("bom", function () {
      var b = bom();
      if (!b) return ["no bill of materials yet"];
      if (b.error) return ["the bill of materials failed: " + b.message];
      return [];
    });

    FM.pipeline.provide("package", function () {
      var p = planset();
      return p ? { sheets: (p.sheets || []).map(function (s) { return s.no + " " + s.title; }) } : null;
    });
    FM.pipeline.blocksOn("package", function () {
      var p = planset();
      if (!p) return ["the package has not been assembled"];
      if (p.error) return ["the package failed to assemble: " + p.message];
      return [];
    });
  }

  FM.project = {
    state: load, set: set, reset: reset,
    model: model, modelIssues: modelIssues,
    takeoff: takeoff, pack: pack, site: site,
    plan: plan, calcs: calcs, bom: bom, planset: planset,
    wire: wire,
    /* exposed so a view can show what is derived vs stored */
    memoKeys: function () { var k = []; for (var n in memo) k.push(n); return k; }
  };

  wire();
})();

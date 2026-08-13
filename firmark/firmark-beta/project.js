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
   this codebase has been bitten by that shape four times: a stale
   bundle, a stale coverage headline, a stale reaction figure in prose,
   and an approval with no fingerprint. Derived state is derived on
   demand, memoised against a KEY, and there is no flag anyone has to
   remember to clear.

   The key is the part to get right, and the first version of this file
   got it wrong: it keyed each stage on a fingerprint of the previous
   stage's OUTPUT. A solver result is not a tree — marks point at
   solutions, solutions at candidates, unification moves back at marks
   — so fingerprinting one walked a graph with shared nodes down every
   path that reached them, and the test suite stopped terminating. Not
   slowly: at all.

   Two changes came out of that, and both are right on their own.
   `stable()` in pipeline.js now has a cycle guard and a node budget,
   so a fingerprint can never hang whatever it is handed. And every
   stage here keys on a short string chained from the small,
   human-authored things upstream — a plan id, a pack id, a fingerprint
   of the drawn model — never on a derived object.

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

  /* ---------------- memoisation, keyed on a CHEAP key ----------------

     A memo entry is valid only while its key is unchanged. There is no
     invalidate() to forget to call.

     The key is a short string the caller builds from the small, human-authored
     things a stage depends on — the plan id, the pack id, the fingerprint of
     the drawn model. It is NEVER the previous stage's output.

     That distinction is not a micro-optimisation, it is the difference between
     a suite that finishes and one that does not. Fingerprinting a whole solver
     result walks a graph with shared nodes and back-references, and the first
     version of this file did exactly that: `bom` keyed on the entire
     `solvePlan` output and `planset` keyed on all of them at once. The test
     run stopped terminating. `stable()` now has a cycle guard and a node
     budget so it can never hang again — but the right fix is to not hand it
     a derived object in the first place.

     So each stage exposes a `*Key()` and the next stage chains it. The keys
     are what change when a human changes something; the outputs are what
     follow from that. */

  var memo = {};

  function derive(name, key, fn) {
    if (key === null || key === undefined) return null;
    if (memo[name] && memo[name].key === key) return memo[name].value;
    var value;
    try { value = fn(); }
    catch (e) {
      /* A stage that threw must not look like a stage that produced nothing —
         those are different facts and the gate treats them differently. */
      value = { error: true, message: e.message, where: name,
                note: "This stage threw rather than returning a result. That is a defect, " +
                      "not an empty input — the gate stays closed and this text is the reason." };
    }
    memo[name] = { key: key, value: value };
    return value;
  }

  function fp(v) {
    return FM.pipeline ? FM.pipeline.fingerprint(v) : JSON.stringify(v);
  }

  /* ---------------- the derived chain ----------------

     Each stage has a KEY (cheap, small, chains from upstream) and a VALUE
     (derived, possibly large, never used as anyone's key). */

  /* WHERE THE GEOMETRY COMES FROM, in precedence order:

       1. an explicit model pinned onto the run
       2. WHATEVER IS ON THE CAD CANVAS RIGHT NOW
       3. derived from a shipped plan id, so a run can start from a master set
          without anyone drawing

     (2) is the one that was missing, and its absence meant the whole product
     could not be started: no file in the build ever wrote the run's model, so
     every one of the six gates sat permanently blocked behind "no geometry
     yet". The CAD view is stage 1 — what is on its canvas IS the geometry the
     run is about — so the run reads it rather than waiting to be told. */

  function canvasModel() {
    if (!FM.cad || typeof FM.cad.currentModel !== "function") return null;
    try { return FM.cad.currentModel(); } catch (e) { return null; }
  }

  function modelKey() {
    var s = load();
    if (s.model) return "pinned:" + fp(s.model);
    var c = canvasModel();
    /* The canvas key includes its SOURCE as well as its content, so loading a
       different plan that happens to produce identical geometry still reads as
       a different thing to approve. */
    if (c) {
      var src = FM.cad.currentSource ? FM.cad.currentSource() : { kind: "?", id: "?" };
      return "canvas:" + src.kind + "/" + src.id + "/" + fp(c);
    }
    if (s.planId) return "plan:" + s.planId + "/" + (s.variantId || "base");
    return null;
  }

  function model() {
    var s = load();
    if (s.model) return s.model;
    var c = canvasModel();
    if (c) return c;
    if (s.planId && FM.cad && FM.cad.fromPlan) {
      return derive("model", modelKey(), function () {
        return FM.cad.fromPlan(s.planId, s.variantId);
      });
    }
    return null;
  }

  function modelIssues() {
    var k = modelKey();
    if (!k || !FM.cad || !FM.cad.validate) return [];
    return derive("modelIssues", k, function () { return FM.cad.validate(model()); }) || [];
  }

  function takeoffKey() {
    var k = modelKey();
    return k ? "t|" + k : null;
  }

  function takeoff() {
    if (!FM.takeoff || !FM.takeoff.run || !model()) return null;
    return derive("takeoff", takeoffKey(), function () { return FM.takeoff.run(model(), {}); });
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
    return derive("site", "j|" + s.jurisId, function () { return FM.juris.forSite(s.jurisId); });
  }

  function planKey() {
    var s = load();
    /* A canvas model outranks a plan id here for the same reason it does in
       model(): if somebody has drawn geometry, the run is about THAT, and
       solving the shipped plan's hand-written marks instead would put a
       different schedule behind the same approval. */
    if (!s.model && !canvasModel() && s.planId) return "p|" + s.planId + "/" + (s.variantId || "base");
    var k = takeoffKey();
    return k ? "p|" + k : null;
  }

  /* The plan the solver consumes: either a shipped plan (with its variant) or
     one assembled from the takeoff's marks. */
  function plan() {
    var s = load();
    if (!s.model && !canvasModel() && s.planId && FM.weights) {
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

  function calcsKey() {
    var pk = pack(), k = planKey();
    return (pk && k) ? k + "|" + pk.id : null;
  }

  function calcs() {
    if (!FM.solver || !calcsKey()) return null;
    return derive("calcs", calcsKey(), function () {
      var pl = plan(), pk = pack();
      if (!pl || !pk) return null;
      return FM.solver.solvePlan(pl, pk);
    });
  }

  function bomKey() {
    var k = calcsKey();
    return k ? k + "|lots:" + ((plan() || {}).lots || 1) : null;
  }

  function bom() {
    if (!FM.bom || !FM.bom.build || !bomKey()) return null;
    return derive("bom", bomKey(), function () {
      var c = calcs();
      if (!c || c.error) return null;
      return FM.bom.build(c, { lots: (plan() || {}).lots || 1, variantId: load().variantId });
    });
  }

  function plansetKey() {
    var s = load();
    var parts = [bomKey() || calcsKey() || takeoffKey() || modelKey() || "empty",
                 s.jurisId || "no-juris"];
    /* the approval trail is printed on the cover, so it is part of the key —
       and it is small, so fingerprinting it is safe */
    if (FM.pipeline) parts.push(fp(FM.pipeline.state().stages));
    return parts.join("|");
  }

  function planset() {
    if (!FM.planset || !FM.planset.build) return null;
    return derive("planset", plansetKey(), function () {
      return FM.planset.build({
        project: load(), model: model(), takeoff: takeoff(),
        planResult: calcs(), bom: bom(), juris: site(),
        pipeline: FM.pipeline ? FM.pipeline.snapshot() : null
      });
    });
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
    keys: function () {
      return { model: modelKey(), takeoff: takeoffKey(), plan: planKey(),
               calcs: calcsKey(), bom: bomKey(), planset: plansetKey() };
    },
    /* exposed so a view can show what is derived vs stored */
    memoKeys: function () { var k = []; for (var n in memo) k.push(n); return k; }
  };

  wire();
})();

/* ============================================================
   pipeline.js — the stage machine and the approval gates.

   The product's claim is "an architectural plan to a review package
   in minutes, with human approval at every stage". The gates are the
   half that makes the speed defensible: fast is only safe if a person
   put their name on each step and the software can prove nothing
   changed under them afterwards.

   THE RULE THAT MAKES A GATE MEAN ANYTHING
   ----------------------------------------
   An approval is recorded against a FINGERPRINT of what was approved.
   If an upstream stage changes after you approved a downstream one,
   your approval is invalidated and says so by name.

   Without that, the gates are theatre: approve the takeoff, then edit
   the geometry, and the calculations carry an approval for a takeoff
   that no longer exists. That is worse than having no gate at all,
   because the audit trail then testifies to a review that did not
   happen. Every serious version of this defect has the same shape —
   evidence outliving the thing it was evidence for.

   The trail is append-only. Rejections and invalidations stay in it;
   a clean-looking history is not the goal, a true one is.
   ============================================================ */

(function () {
  "use strict";

  var KEY = "fm-pipeline";

  /* `needs` is the role required to approve. `inputs` names the stages whose
     fingerprints this stage's approval depends on — change any of them and
     this approval dies. */
  var STAGES = [
    { id: "geometry", label: "Geometry", short: "Plan geometry",
      gate: "The drawn plan is what the architectural set says.",
      needs: "drafter", inputs: [],
      detail: "Walls, bearing lines, openings and framing directions. Nothing " +
              "downstream can be right if this is wrong, and nothing downstream " +
              "can detect that it is wrong." },

    { id: "takeoff", label: "Takeoff", short: "Spans and tributaries",
      gate: "Every span, tributary width and bearing condition is what the plan means.",
      needs: "engineer", inputs: ["geometry"],
      detail: "This is the gate that matters most. A tributary width that is " +
              "quietly wrong produces a confident, wrong member, and every check " +
              "downstream will agree with it." },

    { id: "loads", label: "Loads and code", short: "Design criteria",
      gate: "The code edition, wind speed, snow and live loads are right for this site.",
      needs: "engineer", inputs: ["geometry", "takeoff"],
      detail: "Jurisdiction, adopted code, and the site hazard parameters. The " +
              "defaults are planning values — a site is not designed off a default." },

    { id: "calcs", label: "Calculations", short: "Member selection",
      gate: "The selected members, the escalations, and what was not sized are accepted.",
      needs: "engineer", inputs: ["geometry", "takeoff", "loads"],
      detail: "Including the refusals. Accepting the calculations means accepting " +
              "the list of marks this engine would not size." },

    { id: "bom", label: "Bill of materials", short: "Quantities",
      gate: "The quantities are right and the exclusions are understood.",
      needs: "estimator", inputs: ["geometry", "takeoff", "loads", "calcs"],
      detail: "Approving this means you have read what is NOT in it — connectors, " +
              "sheathing, fasteners and anything escalated." },

    { id: "package", label: "Package for PE", short: "Ready for review",
      gate: "The package is complete enough to hand to a licensed engineer.",
      needs: "pe", inputs: ["geometry", "takeoff", "loads", "calcs", "bom"],
      detail: "This gate does NOT seal anything. It records that a licensed " +
              "engineer received a package and found it reviewable. The seal is " +
              "applied by that engineer, outside this system, under their licence." }
  ];

  function stageById(id) {
    for (var i = 0; i < STAGES.length; i++) if (STAGES[i].id === id) return STAGES[i];
    return null;
  }
  function indexOf(id) {
    for (var i = 0; i < STAGES.length; i++) if (STAGES[i].id === id) return i;
    return -1;
  }

  /* ---------------- fingerprints ----------------

     A cheap, stable, order-insensitive digest of a stage's inputs. It does not
     need to be cryptographic — it is not defending against an adversary, it is
     detecting that the thing under an approval moved. It DOES need to be
     stable across reloads, so it must not depend on object key order or on
     anything with a timestamp in it. */

  function digest(s) {
    /* FNV-1a, 32-bit. Small, deterministic, no dependencies. */
    var h = 0x811c9dc5;
    for (var i = 0; i < s.length; i++) {
      h ^= s.charCodeAt(i);
      h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0;
    }
    return ("0000000" + h.toString(16)).slice(-8);
  }

  /* Stable stringify: sorts keys, so a re-serialised model with the same
     content fingerprints the same. Skips functions and undefined.

     TWO GUARDS, both learned the hard way in one sitting.

     A solver result is not a tree. A mark points at its solution, a solution
     points at candidates, a unification move points back at the marks it
     collapsed — so the graph has shared nodes and back-references. Without a
     seen-set this walk revisits the same subgraph down every path that reaches
     it, and at depth 12 with real branching that does not terminate in any
     useful time. It did not merely get slow: the test suite stopped finishing.

     So: an object already on the current path is emitted as a cycle marker,
     and the whole walk is bounded by a node budget. Both are DETERMINISTIC —
     the same input always produces the same string, including the same
     truncation — because a fingerprint that varied with traversal luck would
     invalidate approvals at random, which is worse than one that is coarse.

     A truncated fingerprint is still sound for what it is used for. It can
     only ever say "these differ" too rarely, never too often, and the callers
     in project.js key on small explicit values precisely so that never bites. */

  var NODE_BUDGET = 20000;

  function stable(v, depth, path, budget) {
    depth = depth || 0;
    path = path || [];
    budget = budget || { n: 0 };
    if (++budget.n > NODE_BUDGET) return '"…budget…"';
    if (depth > 12) return '"…deep…"';
    if (v === null || v === undefined) return "null";
    var t = typeof v;
    if (t === "number") return isFinite(v) ? String(Math.round(v * 1e6) / 1e6) : "null";
    if (t === "boolean" || t === "string") return JSON.stringify(v);
    if (t === "function") return "null";

    for (var c = 0; c < path.length; c++) if (path[c] === v) return '"…cycle…"';
    path.push(v);

    var out;
    if (Object.prototype.toString.call(v) === "[object Array]") {
      var a = [];
      for (var i = 0; i < v.length; i++) a.push(stable(v[i], depth + 1, path, budget));
      out = "[" + a.join(",") + "]";
    } else {
      var keys = [];
      for (var k in v) if (Object.prototype.hasOwnProperty.call(v, k)) keys.push(k);
      keys.sort();
      var parts = [];
      for (var j = 0; j < keys.length; j++) {
        var val = v[keys[j]];
        if (typeof val === "function" || val === undefined) continue;
        parts.push(JSON.stringify(keys[j]) + ":" + stable(val, depth + 1, path, budget));
      }
      out = "{" + parts.join(",") + "}";
    }
    path.pop();
    return out;
  }

  function fingerprint(v) { return digest(stable(v)); }

  /* ---------------- state ----------------

     { stages: { id: {status, by, at, note, fp, sawFp} }, trail: [...] }
       status : "pending" | "approved" | "rejected" | "stale"
       fp     : the fingerprint of THIS stage's own content when approved
       sawFp  : {inputStageId: fp} — what the approver was looking at upstream */

  var state = null;

  function blank() { return { stages: {}, trail: [] }; }

  function load() {
    if (state) return state;
    try {
      var raw = localStorage.getItem(KEY);
      state = raw ? JSON.parse(raw) : blank();
    } catch (e) { state = blank(); }
    if (!state.stages) state.stages = {};
    if (!state.trail) state.trail = [];
    return state;
  }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(load())); } catch (e) {}
  }

  function now() { return new Date().toISOString(); }

  function log(entry) {
    var s = load();
    entry.at = now();
    var u = FM.auth && FM.auth.state().user;
    entry.by = u ? u.name : "(not signed in)";
    s.trail.push(entry);
    /* append-only, but not unbounded — keep the most recent 400 */
    if (s.trail.length > 400) s.trail = s.trail.slice(s.trail.length - 400);
    save();
  }

  /* ---------------- content ----------------

     The pipeline does not own the artefacts; it observes them. A provider is
     registered per stage and returns whatever that stage's content currently
     is. Modules register themselves so pipeline.js does not have to know how
     to reach into any of them. */

  var providers = {};
  function provide(stageId, fn) { providers[stageId] = fn; }

  function contentOf(stageId) {
    if (!providers[stageId]) return null;
    try { return providers[stageId](); } catch (e) { return null; }
  }
  function fpOf(stageId) {
    var c = contentOf(stageId);
    return c === null || c === undefined ? null : fingerprint(c);
  }

  /* ---------------- the rule ----------------

     A stage is APPROVED only if it was approved AND nothing it depends on has
     moved since — including itself. Anything else is stale, and stale says
     exactly which input moved. */

  function statusOf(stageId) {
    var s = load();
    var rec = s.stages[stageId];
    if (!rec || rec.status !== "approved") {
      return { status: rec ? rec.status : "pending", rec: rec || null, moved: [] };
    }
    var moved = [];
    var mine = fpOf(stageId);
    if (mine !== null && rec.fp && mine !== rec.fp) {
      moved.push({ stage: stageId, label: stageById(stageId).label, self: true });
    }
    var st = stageById(stageId);
    for (var i = 0; i < st.inputs.length; i++) {
      var upId = st.inputs[i];
      var upNow = fpOf(upId);
      var upThen = rec.sawFp ? rec.sawFp[upId] : null;
      if (upNow !== null && upThen && upNow !== upThen) {
        moved.push({ stage: upId, label: stageById(upId).label, self: false });
      }
    }
    return { status: moved.length ? "stale" : "approved", rec: rec, moved: moved };
  }

  /* Can this stage be approved right now? */
  function can(stageId) {
    var st = stageById(stageId);
    if (!st) return { ok: false, blockedBy: ["no such stage"] };
    var blocked = [];

    if (!FM.auth || !FM.auth.require()) blocked.push("nobody is signed in");
    else if (!FM.auth.has(st.needs)) {
      blocked.push("this gate needs the " +
        (FM.auth.ROLES[st.needs] ? FM.auth.ROLES[st.needs].label : st.needs) + " role");
    }

    for (var i = 0; i < st.inputs.length; i++) {
      var up = statusOf(st.inputs[i]);
      if (up.status !== "approved") {
        blocked.push(stageById(st.inputs[i]).label + " is " + up.status + " — approve it first");
      }
    }

    if (contentOf(stageId) === null) {
      blocked.push("there is nothing to approve yet — " + st.label.toLowerCase() + " has produced no content");
    }

    /* a stage that declares blocking problems cannot be approved past them */
    var b = blockers(stageId);
    for (var j = 0; j < b.length; j++) blocked.push(b[j]);

    return { ok: blocked.length === 0, blockedBy: blocked };
  }

  /* Stages may register hard blockers — a CAD model with validation errors, a
     takeoff with unresolved items. These are not warnings; they stop the gate. */
  var blockerFns = {};
  function blocksOn(stageId, fn) { blockerFns[stageId] = fn; }
  function blockers(stageId) {
    if (!blockerFns[stageId]) return [];
    try {
      var r = blockerFns[stageId]();
      return Object.prototype.toString.call(r) === "[object Array]" ? r : [];
    } catch (e) { return ["could not check this stage: " + e.message]; }
  }

  function approve(stageId, note) {
    var gate = can(stageId);
    if (!gate.ok) return { ok: false, why: gate.blockedBy };

    var st = stageById(stageId);
    var u = FM.auth.state().user;
    var saw = {};
    for (var i = 0; i < st.inputs.length; i++) saw[st.inputs[i]] = fpOf(st.inputs[i]);

    load().stages[stageId] = {
      status: "approved",
      by: u.name, byId: u.id, role: st.needs,
      at: now(), note: note || "",
      fp: fpOf(stageId), sawFp: saw
    };
    save();
    log({ kind: "approve", stage: stageId, note: note || "", fp: load().stages[stageId].fp });
    return { ok: true };
  }

  function reject(stageId, note) {
    if (!FM.auth || !FM.auth.require()) return { ok: false, why: ["nobody is signed in"] };
    load().stages[stageId] = {
      status: "rejected",
      by: FM.auth.state().user.name, at: now(), note: note || "", fp: null, sawFp: null
    };
    save();
    log({ kind: "reject", stage: stageId, note: note || "" });
    return { ok: true };
  }

  function clear(stageId) {
    delete load().stages[stageId];
    save();
    log({ kind: "clear", stage: stageId });
  }

  function reset() {
    state = blank();
    save();
    log({ kind: "reset", stage: null, note: "pipeline reset" });
  }

  /* The whole picture, for the view and for the package's approval trail. */
  function snapshot() {
    var out = { stages: [], current: null, complete: true, staleCount: 0 };
    for (var i = 0; i < STAGES.length; i++) {
      var st = STAGES[i];
      var s = statusOf(st.id);
      var gate = can(st.id);
      var row = {
        stage: st, status: s.status, rec: s.rec, moved: s.moved,
        can: gate.ok, blockedBy: gate.blockedBy,
        blockers: blockers(st.id),
        hasContent: contentOf(st.id) !== null
      };
      if (s.status === "stale") out.staleCount++;
      if (s.status !== "approved") {
        out.complete = false;
        if (!out.current) out.current = st.id;
      }
      out.stages.push(row);
    }
    if (!out.current) out.current = STAGES[STAGES.length - 1].id;
    return out;
  }

  function audit() { return load().trail.slice(); }

  FM.pipeline = {
    STAGES: STAGES,
    stageById: stageById,
    indexOf: indexOf,
    provide: provide,
    blocksOn: blocksOn,
    contentOf: contentOf,
    fingerprint: fingerprint,
    stableString: stable,
    statusOf: statusOf,
    can: can,
    approve: approve,
    reject: reject,
    clear: clear,
    reset: reset,
    snapshot: snapshot,
    audit: audit,
    state: function () { return load(); }
  };
})();

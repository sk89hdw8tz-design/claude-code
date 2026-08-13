/* ============================================================
   auth.js + pipeline.js — the gates.

   The claim the product makes is "minutes, with human approval at
   every stage". The speed is only defensible if the approvals are
   real, and an approval is only real if it cannot outlive the thing
   it approved. That rule is what these assertions defend.
   ============================================================ */

"use strict";

module.exports = function (t, FM) {

  /* The harness loads the DOM-free set. auth.js and pipeline.js touch
     localStorage at call time, which the harness stubs as permanently empty —
     that is the case worth testing anyway: correct behaviour from a cold start
     with nothing saved. */
  if (!FM.auth || !FM.pipeline) {
    t.suite("pipeline · gates");
    t.bad("auth.js / pipeline.js are not loaded by the harness — the gate logic is untested");
    return;
  }

  t.suite("auth · the closed gate");

  t.eq(FM.auth.require(), false, "nothing is signed in from a cold start");
  var bad = FM.auth.login("Demo", "wrong");
  t.eq(bad.ok, false, "a wrong password does not sign in");
  t.truthy(!/user|username|account exists/i.test(bad.why) || /do not match/.test(bad.why),
    "and the message does not say which half was wrong — " + JSON.stringify(bad.why));
  t.eq(FM.auth.login("Nobody", "Demo").ok, false, "an unknown user does not sign in");
  t.eq(bad.why, FM.auth.login("Nobody", "Demo").why,
    "and both failures give the SAME message, so it cannot be used to enumerate accounts");

  var good = FM.auth.login("Demo", "Demo");
  t.eq(good.ok, true, "Demo / Demo signs in");
  t.eq(FM.auth.require(), true, "and the session is live");
  t.truthy(good.user.name && good.user.initials, "the user has a name to put on an approval");
  t.truthy(good.user.licence === null,
    "the demo user carries NO professional licence — the seal is a person, not an account");
  t.eq(FM.auth.has("pe"), true, "the demo account holds every role so one person can walk the pipeline");

  t.suite("pipeline · a gate cannot be opened out of order");

  FM.pipeline.reset();
  var stages = FM.pipeline.STAGES;
  t.eq(stages.length, 6, "six stages: geometry, takeoff, loads, calcs, bom, package");
  t.eq(stages[0].id, "geometry", "and geometry is first — nothing downstream can be right if it is wrong");
  t.eq(stages[stages.length - 1].id, "package", "and the PE package is last");

  /* every stage after the first declares its upstream dependencies, and they
     are all real stages that come BEFORE it */
  var orderProblems = [];
  stages.forEach(function (st, i) {
    st.inputs.forEach(function (dep) {
      var j = FM.pipeline.indexOf(dep);
      if (j === -1) orderProblems.push(st.id + " depends on unknown stage " + dep);
      else if (j >= i) orderProblems.push(st.id + " depends on " + dep + ", which is not upstream of it");
    });
    if (!st.needs) orderProblems.push(st.id + " does not declare which role may approve it");
    if (!st.gate) orderProblems.push(st.id + " does not state what its gate means");
  });
  t.eq(orderProblems.length, 0, "every dependency is a real, upstream stage and every gate is stated" +
    (orderProblems.length ? " — " + orderProblems.join("; ") : ""));

  /* with no content registered, nothing is approvable and each says why */
  var silent = [];
  stages.forEach(function (st) {
    var c = FM.pipeline.can(st.id);
    if (c.ok) silent.push(st.id + " is approvable with no content");
    if (!c.blockedBy.length) silent.push(st.id + " is blocked but gives no reason");
  });
  t.eq(silent.length, 0, "no stage is approvable from empty, and every refusal states a reason" +
    (silent.length ? " — " + silent.join("; ") : ""));

  t.suite("pipeline · an approval cannot outlive what was approved");

  /* Stand up a fake two-stage chain on the real machinery. `geometry` is
     content we control; `takeoff` depends on it. */
  var geom = { walls: 4, note: "first" };
  var take = { marks: 3 };
  FM.pipeline.provide("geometry", function () { return geom; });
  FM.pipeline.provide("takeoff", function () { return take; });
  FM.pipeline.blocksOn("geometry", function () { return []; });
  FM.pipeline.blocksOn("takeoff", function () { return []; });

  FM.pipeline.reset();
  var a1 = FM.pipeline.approve("geometry", "checked the walls");
  t.eq(a1.ok, true, "geometry approves once it has content and no blockers");
  t.eq(FM.pipeline.statusOf("geometry").status, "approved", "and it reads approved");

  var a2 = FM.pipeline.approve("takeoff", "checked the spans");
  t.eq(a2.ok, true, "takeoff approves once geometry is approved");
  t.eq(FM.pipeline.statusOf("takeoff").status, "approved", "and it reads approved");

  /* THE RULE. Change the geometry after both were approved. */
  geom = { walls: 5, note: "someone moved a wall" };

  var g = FM.pipeline.statusOf("geometry");
  t.eq(g.status, "stale", "changing the geometry withdraws ITS OWN approval");
  t.truthy(g.moved.length && g.moved[0].self, "and says the stage's own content changed");

  var tk = FM.pipeline.statusOf("takeoff");
  t.eq(tk.status, "stale", "and withdraws the DOWNSTREAM approval too");
  t.truthy(tk.moved.length && !tk.moved[0].self && tk.moved[0].stage === "geometry",
    "naming geometry as the input that moved — an approval that survives a change to " +
    "what was approved is worth nothing");

  /* putting it back must restore, not require a re-approval — the fingerprint
     is of content, not of an edit count */
  geom = { walls: 4, note: "first" };
  t.eq(FM.pipeline.statusOf("geometry").status, "approved",
    "restoring the exact prior content restores the approval — the fingerprint is over content");
  t.eq(FM.pipeline.statusOf("takeoff").status, "approved", "and the downstream one with it");

  /* key order must not matter, or approvals would flicker on every reserialise */
  geom = { note: "first", walls: 4 };
  t.eq(FM.pipeline.statusOf("geometry").status, "approved",
    "and reordering the same keys does NOT invalidate it — a reserialised model is the same model");

  t.suite("pipeline · the trail is a record, not a résumé");

  FM.pipeline.reset();
  FM.pipeline.approve("geometry", "one");
  FM.pipeline.reject("geometry", "changed my mind");
  FM.pipeline.approve("geometry", "two");
  var trail = FM.pipeline.audit();
  var kinds = trail.map(function (e) { return e.kind; }).join(",");
  t.truthy(/reset,approve,reject,approve/.test(kinds),
    "approvals, rejections and resets all stay in the trail — got " + kinds);
  t.truthy(trail.every(function (e) { return e.by && e.at; }),
    "and every entry carries who and when");

  var rejected = (function () {
    FM.pipeline.reset();
    FM.pipeline.reject("geometry", "no");
    return FM.pipeline.can("takeoff");
  })();
  t.eq(rejected.ok, false, "a rejected stage keeps everything downstream closed");

  t.suite("pipeline · fingerprints");

  var fp = FM.pipeline.fingerprint;
  t.eq(fp({ a: 1, b: 2 }), fp({ b: 2, a: 1 }), "key order does not change a fingerprint");
  t.truthy(fp({ a: 1 }) !== fp({ a: 2 }), "a changed value does");
  t.eq(fp([1, 2, 3]), fp([1, 2, 3]), "arrays are stable");
  t.truthy(fp([1, 2, 3]) !== fp([3, 2, 1]), "and array ORDER matters, because it does structurally");
  t.eq(fp({ a: 1, f: function () {} }), fp({ a: 1 }),
    "functions are ignored — a rebuilt closure is not a content change");
  t.truthy(fp(null) === fp(null), "null is stable");
  t.eq(typeof fp({ deep: { deep: { deep: 1 } } }), "string", "nested objects fingerprint without throwing");

  /* leave the machinery clean for anything that runs after */
  FM.pipeline.reset();
  FM.auth.logout();

  t.suite("pipeline · an approval cannot outlive the DISAPPEARANCE of what it approved");

  /* The check read `mine !== null && rec.fp && mine !== rec.fp`, so when a
     stage's content became unavailable fpOf() returned null, BOTH comparisons
     were skipped, and the approval stood. Delete the geometry after approving
     all six and the run reported "6/6 STAGES APPROVED · Ready for PE", with one
     card simultaneously reading APPROVED and "cannot be approved: no geometry
     yet" — and the false trail printed on the PE package's cover.

     Disappearing is the most complete change a stage's content can undergo,
     and the guard had a hole in exactly the shape of the thing it guarded. */
  /* the block above ends by signing out, and an approval needs a name on it */
  FM.auth.login("Demo", "Demo");

  var live = { walls: 4 };
  FM.pipeline.reset();
  FM.pipeline.provide("geometry", function () { return live; });
  FM.pipeline.blocksOn("geometry", function () { return []; });
  t.eq(FM.pipeline.approve("geometry", "content present").ok, true, "approves with content");

  live = null;
  var gone = FM.pipeline.statusOf("geometry");
  t.eq(gone.status, "stale", "and goes STALE when that content disappears entirely");
  t.truthy(/no longer there/.test((gone.moved[0] || {}).why || ""),
    "saying the content is no longer there, not merely that something changed");
  t.eq(FM.pipeline.snapshot().complete, false,
    "so the run cannot report itself complete on content that is gone");

  /* an approval with no fingerprint is unfalsifiable — nothing can ever make it
     stale — so it is not an approval, it is a claim */
  FM.pipeline.reset();
  FM.pipeline.state().stages.geometry = { status: "approved", by: "hand-written" };
  t.eq(FM.pipeline.statusOf("geometry").status, "stale",
    "an approval record with no fingerprint reads stale, not approved");

  /* and approve() refuses to create one */
  FM.pipeline.reset();
  FM.pipeline.provide("geometry", function () { return null; });
  var refused = FM.pipeline.approve("geometry", "nothing there");
  t.eq(refused.ok, false, "approve() refuses when the content cannot be read at the moment of approval");

  /* corrupt storage must not throw — it is user-writable */
  FM.pipeline.reset();
  FM.pipeline.state().trail = "not an array";
  var threw = null;
  try { FM.pipeline.audit(); FM.pipeline.snapshot(); } catch (e) { threw = e.message; }
  t.eq(threw, null, "a corrupt trail in storage does not throw and take the audit card with it");

  FM.pipeline.reset();
  FM.pipeline.provide("geometry", function () { return { walls: 4 }; });

  t.suite("product · nothing anywhere claims this software seals");

  /* suite-planset.js sweeps its OWN output for this. That is not enough: the
     word re-entered the product three times from three other modules — a
     permissions row reading "Approve & apply the stamp" (an action this
     software does not have), a meta description calling the output
     "stamp-ready" (a completeness claim it cannot make), and the sizing view
     printing "Nothing here is stamped" forty lines above "AS STAMPED".
     Sweep the SOURCE of every shipping part, so a claim cannot enter through
     a module nobody thought to check. */
  var fs5 = require("fs"), path5 = require("path");
  var dir5 = path5.join(__dirname, "..");
  var parts5 = ["core.js", "engine.js", "weights.js", "solver.js", "export.js", "scope.js",
                "jurisdiction.js", "cad.js", "takeoff.js", "bom.js", "planset.js",
                "auth.js", "pipeline.js", "project.js",
                "materials.js", "sheet.js", "sizing.js", "pipeline-view.js", "stages-view.js"];

  /* Phrases that ASSERT the software's output is sealed or ready to be. Not a
     ban on the word: "a licensed PE reviews and seals every package" and "this
     software never stamps" both contain it and both must survive. */
  var CLAIMS = [
    { re: /stamp-ready|seal-ready|ready to stamp|ready for stamping/i,
      why: "claims the output is ready to be stamped — a completeness claim this system cannot make" },
    { re: /apply the stamp|applies the stamp|apply a seal|applies the seal/i,
      why: "names a stamp-applying action this software does not have" },
    { re: /\bstamped (calc|plan set|package|drawing|set of)/i,
      why: "describes this system's own output as stamped" }
  ];

  var leaks = [];
  parts5.forEach(function (f) {
    var p5 = path5.join(dir5, f);
    if (!fs5.existsSync(p5)) return;
    /* strip block comments — a comment explaining the policy quotes the very
       phrases it forbids, and a sweep that cannot tell code from prose reads
       the fix as the defect */
    var src = fs5.readFileSync(p5, "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
    CLAIMS.forEach(function (c) {
      var m = c.re.exec(src);
      if (m) leaks.push(f + ': "' + m[0] + '" — ' + c.why);
    });
  });
  t.eq(leaks.length, 0, "no shipping part claims this software seals, stamps or produces a stamped set" +
     (leaks.length ? "\n      " + leaks.join("\n      ") : ""));

  /* and the disclaimers that must NOT be sanitised away */
  var keeps = 0;
  parts5.forEach(function (f) {
    var p5 = path5.join(dir5, f);
    if (!fs5.existsSync(p5)) return;
    if (/never (seals|stamps)|does not (seal|stamp)|reviews and seals|To be sealed by/i
        .test(fs5.readFileSync(p5, "utf8"))) keeps++;
  });
  t.truthy(keeps >= 4, "and the statements that say a PE seals it are still there, in " + keeps + " parts");

  FM.pipeline.reset();
  FM.auth.logout();
};

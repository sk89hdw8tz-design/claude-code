#!/usr/bin/env node
/* ============================================================
   Measures what the register claims.

   The coverage headline in REVIEW-REGISTER.md has been wrong four
   times — 58/30/26, then 66/24/24, then 85/162 — every time for the
   same reason: it is a number a human typed after reading an older
   run. A review register whose own headline is stale is not evidence,
   it is decoration.

   So the number is measured here and asserted against the document by
   run-tests.js. `node test/coverage.js` prints it; `--sync` rewrites
   the register's line to match, so correcting it is one command and
   not a re-count.
   ============================================================ */

"use strict";

var fs = require("fs");
var path = require("path");

var REGISTER = path.join(__dirname, "..", "..", "REVIEW-REGISTER.md");

/* The sentence the register carries. Kept as one regex so the document
   and the measurement cannot drift into different shapes either. */
var LINE = /across (\d+) packs × (\d+) plans, \*\*(\d+) of (\d+) mark-slots produce a\nmember; (\d+) escalate and (\d+) are not this engine's member\.\*\*/;

function measure(FM) {
  var out = {
    packs: FM.weights.PACKS.length,
    plans: FM.weights.PLANS.length,
    solved: 0, escalated: 0, notSized: 0, slots: 0,
    byStatus: {}, byPlan: []
  };
  FM.weights.PLANS.forEach(function (p) {
    var row = { id: p.id, name: p.name, solved: 0, escalated: 0, notSized: 0, slots: 0 };
    FM.weights.PACKS.forEach(function (k) {
      FM.solver.solvePlan(p, k).marks.forEach(function (m) {
        row.slots++;
        if (m.notApplicable) row.notSized++;
        else if (m.unifiedTo || (m.solution && m.solution.pick)) row.solved++;
        else {
          row.escalated++;
          var s = (m.solution && m.solution.status) || "escalate";
          out.byStatus[s] = (out.byStatus[s] || 0) + 1;
        }
      });
    });
    out.solved += row.solved; out.escalated += row.escalated;
    out.notSized += row.notSized; out.slots += row.slots;
    out.byPlan.push(row);
  });
  return out;
}

function stated() {
  var md = fs.readFileSync(REGISTER, "utf8");
  var m = LINE.exec(md);
  if (!m) return null;
  return { packs: +m[1], plans: +m[2], solved: +m[3], slots: +m[4],
           escalated: +m[5], notSized: +m[6] };
}

function sentence(c) {
  return "across " + c.packs + " packs × " + c.plans + " plans, **" + c.solved +
         " of " + c.slots + " mark-slots produce a\nmember; " + c.escalated +
         " escalate and " + c.notSized + " are not this engine's member.**";
}

function sync(c) {
  var md = fs.readFileSync(REGISTER, "utf8");
  if (!LINE.test(md)) throw new Error("register no longer carries the coverage sentence");
  fs.writeFileSync(REGISTER, md.replace(LINE, sentence(c)));
}

module.exports = { measure: measure, stated: stated, sentence: sentence, sync: sync, LINE: LINE };

if (require.main === module) {
  var FM = require("./harness.js").load();
  var c = measure(FM);
  c.byPlan.forEach(function (r) {
    console.log("  " + r.id.padEnd(22) + r.solved + " sized · " + r.escalated +
                " escalated · " + r.notSized + " not sized   of " + r.slots);
  });
  console.log("  " + "TOTAL".padEnd(22) + c.solved + " sized · " + c.escalated +
              " escalated · " + c.notSized + " not sized   of " + c.slots);
  console.log("  escalation mix: " + JSON.stringify(c.byStatus));
  var was = stated();
  if (process.argv.indexOf("--sync") !== -1) {
    sync(c);
    console.log("\nregister synced: " + sentence(c).replace("\n", " "));
  } else if (!was) {
    console.log("\nregister does NOT carry the coverage sentence in the expected shape");
  } else {
    var same = ["packs", "plans", "solved", "slots", "escalated", "notSized"]
      .every(function (k) { return was[k] === c[k]; });
    console.log(same ? "\nregister agrees" : "\nregister DISAGREES — it says " +
      was.solved + "/" + was.slots + " over " + was.packs + "×" + was.plans +
      ". Run: node test/coverage.js --sync");
  }
}

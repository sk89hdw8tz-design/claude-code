#!/usr/bin/env node
/* ============================================================
   The numbers printed in DEMO.md, measured.

   Same discipline as coverage.js and for the same reason. A runbook
   that tells someone what they will see on screen is a promise, and a
   hand-typed promise goes stale on the next commit — then it is worse
   than no runbook, because the demo diverges from the script in front
   of an audience.

   `node test/demo-values.js`        prints the tables and says whether
                                     DEMO.md agrees
   `node test/demo-values.js --sync` rewrites DEMO.md's tables

   The suite asserts agreement, so DEMO.md cannot drift from the build.
   ============================================================ */

"use strict";

var fs = require("fs");
var path = require("path");

var DEMO = path.join(__dirname, "..", "..", "DEMO.md");

/* The three regions the runbook walks, on the plan it opens on. */
var PLAN = "two-story-2450";
var WALK = ["tx-i35", "fl-hvhz", "nc-mountain"];
/* the region the app lands on, which is not the first one the walk visits */
var DEFAULT_PACK = "nc-piedmont";

/* Each table is fenced by an HTML comment pair so the prose around it
   stays free text and only the rows are managed. */
function markers(id) {
  return { open: "<!-- fm:" + id + " -->", close: "<!-- /fm:" + id + " -->" };
}

function scheduleRows(FM, packId) {
  var pl = FM.weights.planById(PLAN), pk = FM.weights.packById(packId);
  var res = FM.solver.solvePlan(pl, pk);
  var rows = [];
  res.marks.forEach(function (m) {
    if (m.notApplicable) {
      rows.push([m.mark.id, "_not sized_", "—", "—", "—", m.notApplicable.reason]);
      return;
    }
    var row = m.unifiedTo || (m.solution && m.solution.pick);
    if (!row) {
      var e = FM.solver.escalationOf(m.solution && m.solution.status);
      rows.push([m.mark.id, "**escalates**", "—", "—", "—", e.tag.toLowerCase()]);
      return;
    }
    rows.push([
      m.mark.id,
      "`" + row.cand.size + " " + row.cand.species + " " + row.cand.grade + "`",
      row.cand.spacing ? row.cand.spacing + "″" : "single",
      row.governing,
      row.dcr.toFixed(3),
      m.unifiedTo ? "unified onto this SKU" : ""
    ]);
  });
  return rows;
}

function skuSummary(FM, packId) {
  var pl = FM.weights.planById(PLAN), pk = FM.weights.packById(packId);
  var res = FM.solver.solvePlan(pl, pk);
  var skus = {}, unified = 0, esc = 0;
  res.marks.forEach(function (m) {
    if (m.unifiedTo) unified++;
    if (!m.notApplicable && m.solution && !m.solution.pick) esc++;
    var row = m.unifiedTo || (m.solution && m.solution.pick);
    if (row) skus[FM.solver.skuOf(row.cand)] = 1;
  });
  return { pack: pk, skus: Object.keys(skus).sort(), unified: unified, escalated: esc };
}

function table(head, rows) {
  var L = ["| " + head.join(" | ") + " |",
           "|" + head.map(function () { return "---"; }).join("|") + "|"];
  rows.forEach(function (r) { L.push("| " + r.join(" | ") + " |"); });
  return L.join("\n");
}

/* ---- master set: what each variant actually does to the schedule ----
   The demo's most persuasive moment is the master-set picker, and it is the
   easiest one to overclaim. "Switch to the tile roof and the header moves" is
   a sentence that sounds right and is false: on this plan the tile roof shifts
   HDR-2 from 0.462 to 0.553 and the member holds in every region. The option
   that genuinely moves members is the extended deck. So the runbook prints the
   measured delta rather than a remembered one, and the suite pins it. */
function variantDeltas(FM, packId) {
  var pl = FM.weights.planById(PLAN), pk = FM.weights.packById(packId);
  function snap(variantId) {
    var res = FM.solver.solvePlan(FM.weights.planForVariant(pl, variantId), pk);
    var o = {};
    res.marks.forEach(function (m) {
      var row = m.unifiedTo || (m.solution && m.solution.pick);
      o[m.mark.id] = row
        ? { sku: FM.solver.skuOf(row.cand), dcr: row.dcr }
        : { sku: m.notApplicable ? "(not sized)" : "(escalates)", dcr: null };
    });
    return o;
  }
  var combos = (FM.weights.variantsFor(pl).combinations || []);
  var baseId = (combos.filter(function (c) { return c.isBase; })[0] || combos[0]).id;
  var base = snap(baseId);
  return combos.filter(function (c) { return c.id !== baseId; }).map(function (c) {
    var v = snap(c.id), moves = [], adds = [], drops = [], shifts = [];
    Object.keys(v).forEach(function (k) {
      if (!base[k]) {
        /* sku is already parenthesised for the non-member cases */
        adds.push(k + (v[k].sku.charAt(0) === "(" ? " " + v[k].sku : " (" + v[k].sku + ")"));
        return;
      }
      if (base[k].sku !== v[k].sku) moves.push(k + ": " + base[k].sku + " → " + v[k].sku);
      else if (base[k].dcr !== null && v[k].dcr !== null &&
               Math.abs(base[k].dcr - v[k].dcr) > 0.001) {
        shifts.push(k + " " + base[k].dcr.toFixed(3) + " → " + v[k].dcr.toFixed(3));
      }
    });
    Object.keys(base).forEach(function (k) { if (!(k in v)) drops.push(k); });
    return { combo: c, moves: moves, adds: adds, drops: drops, shifts: shifts };
  });
}

function blocks(FM) {
  var out = {};
  WALK.forEach(function (id) {
    out["schedule-" + id] = table(
      ["Mark", "Member", "Spacing", "Governs", "DCR", "Note"],
      scheduleRows(FM, id));
  });
  out["skus"] = table(
    ["Region", "Distinct SKUs", "Marks unified", "Escalations"],
    WALK.map(function (id) {
      var s = skuSummary(FM, id);
      return [s.pack.name + " (`" + id + "`)", String(s.skus.length),
              String(s.unified), String(s.escalated)];
    }));

  out["variants"] = table(
    ["Built with", "Lots", "What it does to the schedule"],
    variantDeltas(FM, DEFAULT_PACK).map(function (d) {
      var what = [];
      if (d.adds.length) what.push("**adds** " + d.adds.join(", "));
      if (d.drops.length) what.push("**drops** " + d.drops.join(", "));
      if (d.moves.length) what.push("**moves** " + d.moves.join("; "));
      if (d.shifts.length) what.push("same members, DCR shifts: " + d.shifts.join("; "));
      if (!what.length) what.push("nothing — every member holds");
      return [d.combo.label, String(d.combo.lotsExpected), what.join("<br>")];
    }));
  return out;
}

function apply(md, id, body) {
  var m = markers(id);
  var i = md.indexOf(m.open), j = md.indexOf(m.close);
  if (i === -1 || j === -1) return null;
  return md.slice(0, i + m.open.length) + "\n" + body + "\n" + md.slice(j);
}

function extract(md, id) {
  var m = markers(id);
  var i = md.indexOf(m.open), j = md.indexOf(m.close);
  if (i === -1 || j === -1) return null;
  return md.slice(i + m.open.length, j).trim();
}

function check(FM) {
  if (!fs.existsSync(DEMO)) return { missing: true, off: [] };
  var md = fs.readFileSync(DEMO, "utf8");
  var b = blocks(FM), off = [], absent = [];
  Object.keys(b).forEach(function (id) {
    var got = extract(md, id);
    if (got === null) absent.push(id);
    else if (got !== b[id].trim()) off.push(id);
  });
  return { missing: false, off: off, absent: absent, blocks: b };
}

function sync(FM) {
  var md = fs.readFileSync(DEMO, "utf8");
  var b = blocks(FM), done = [], absent = [];
  Object.keys(b).forEach(function (id) {
    var next = apply(md, id, b[id]);
    if (next === null) absent.push(id); else { md = next; done.push(id); }
  });
  fs.writeFileSync(DEMO, md);
  return { done: done, absent: absent };
}

module.exports = { PLAN: PLAN, WALK: WALK, DEFAULT_PACK: DEFAULT_PACK,
                   blocks: blocks, check: check, sync: sync,
                   skuSummary: skuSummary, variantDeltas: variantDeltas, DEMO: DEMO };

if (require.main === module) {
  var FM = require("./harness.js").load();
  if (process.argv.indexOf("--sync") !== -1) {
    var r = sync(FM);
    console.log("synced: " + r.done.join(", "));
    if (r.absent.length) console.log("NO MARKER IN DEMO.md for: " + r.absent.join(", "));
  } else {
    var b = blocks(FM);
    Object.keys(b).forEach(function (id) { console.log("### " + id + "\n" + b[id] + "\n"); });
    var c = check(FM);
    if (c.missing) console.log("DEMO.md does not exist yet");
    else if (c.absent.length) console.log("DEMO.md is missing markers for: " + c.absent.join(", "));
    else if (c.off.length) console.log("DEMO.md DISAGREES on: " + c.off.join(", ") +
      "\nRun: node test/demo-values.js --sync");
    else console.log("DEMO.md agrees");
  }
}

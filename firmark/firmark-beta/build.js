#!/usr/bin/env node
/* ============================================================
   Assembles firmark-app.html from the parts.

   The single-file app is what ships, but it is a BUILD PRODUCT.
   It was hand-assembled before, which is how it came to be missing
   fixes that were already in the parts. Run this after touching any
   part; run `node build.js --check` in review to fail loudly when
   the bundle and the parts have drifted.

   Script order is load-bearing:
     core.js    defines FM and must be first — everything else reads
                FM at load time.
     engine.js  registers FM.engine.
     weights.js registers FM.weights (data only).
     solver.js  registers FM.solver; calls FM.engine and FM.weights
                at call time, so it only has to come after core.
     views      materials / sheet / sizing capture FM helpers into
                locals at load time, so they come last.
   ============================================================ */

"use strict";

var fs = require("fs");
var path = require("path");

var DIR = __dirname;
var OUT = path.join(DIR, "firmark-app.html");

var HEAD =
  '<title>Firmark Structural Harness</title>\n' +
  /* Without this, iOS lays the page out at its default 980px and scales the
     result down to fit the screen — the whole app renders correct and
     unreadable, and every control becomes a pinch-and-aim target. Measured
     at a 393px iPhone viewport: document width 980, viewport 980.
     This bundle is opened off OneDrive on a phone, so it matters. */
  '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n' +
  '<meta name="color-scheme" content="light dark">\n' +
  '<meta name="description" content="Firmark beta — structural calcs prepared for PE review, every value traced to its clause.">\n';

var NOSCRIPT =
  '<noscript><p style="padding:24px;font-family:system-ui">' +
  'The Firmark harness needs JavaScript to run the calculation engine.</p></noscript>\n';

/* Order is dependency order: data and logic first, then views, which capture
   FM helpers into locals at load time. See ARCHITECTURE.md. */
var SCRIPTS = [
  "core.js",
  "scope.js",
  "engine.js",
  "weights.js",
  "solver.js",
  "jurisdiction.js",
  "cad.js",
  "dxf.js",
  "takeoff.js",
  "bom.js",
  "export.js",
  "planset.js",
  "auth.js",
  "pipeline.js",
  "project.js",
  "materials.js",
  "sheet.js",
  "sizing.js",
  "pipeline-view.js",
  "stages-view.js"
];

/* Modules under construction may not exist yet. A missing part is announced
   loudly and skipped rather than crashing the build — but it is NEVER silent,
   because a bundle quietly missing a module is exactly how this project
   shipped a stale app once already. */
var missing = [];

function exists(f) { return fs.existsSync(path.join(DIR, f)); }

function read(f) {
  return fs.readFileSync(path.join(DIR, f), "utf8").replace(/\n+$/, "");
}

function build() {
  var out = "";
  out += HEAD;
  out += "<style>\n" + read("app.css") + "\n\n</style>\n\n";
  out += read("shell.html") + "\n\n";
  out += NOSCRIPT + "\n";

  /* the catalog is injected verbatim — reserialized, never edited */
  var matdata = JSON.parse(fs.readFileSync(path.join(DIR, "matdata.json"), "utf8"));
  out += "<script>window.MATDATA = " + JSON.stringify(matdata) + ";</script>\n";

  missing = [];
  SCRIPTS.forEach(function (f) {
    if (!exists(f)) { missing.push(f); return; }
    out += "<script>\n" + read(f) + "\n\n</script>\n";
  });
  out += "<script>FM.boot();</script>\n";
  return out;
}

function main() {
  var built = build();
  var check = process.argv.indexOf("--check") !== -1;

  if (check) {
    var current = fs.existsSync(OUT) ? fs.readFileSync(OUT, "utf8") : "";
    if (current === built) {
      console.log("firmark-app.html is up to date (" + built.length + " bytes)");
      process.exit(0);
    }
    console.error("firmark-app.html is STALE — it does not match the parts.");
    console.error("  bundle: " + current.length + " bytes");
    console.error("  parts:  " + built.length + " bytes");
    console.error("Run: node build.js");
    process.exit(1);
  }

  fs.writeFileSync(OUT, built);
  console.log("wrote firmark-app.html — " + built.length + " bytes");
  SCRIPTS.forEach(function (f) {
    if (!exists(f)) return;
    console.log("  " + f.padEnd(18) + fs.statSync(path.join(DIR, f)).size + " bytes");
  });
  if (missing.length) {
    console.log("\nNOT IN THE BUNDLE — these parts do not exist yet:");
    missing.forEach(function (f) { console.log("  " + f); });
    console.log("The bundle is INCOMPLETE. Anything depending on them will not work.");
  }
}

main();

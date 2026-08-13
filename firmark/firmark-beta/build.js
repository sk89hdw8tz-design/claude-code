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
  '<meta name="description" content="Firmark beta — stamp-ready structural calcs with every value traced to its clause.">\n';

var NOSCRIPT =
  '<noscript><p style="padding:24px;font-family:system-ui">' +
  'The Firmark harness needs JavaScript to run the calculation engine.</p></noscript>\n';

var SCRIPTS = [
  "core.js",
  "engine.js",
  "weights.js",
  "solver.js",
  "materials.js",
  "sheet.js",
  "sizing.js"
];

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

  SCRIPTS.forEach(function (f) {
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
    console.log("  " + f.padEnd(14) + fs.statSync(path.join(DIR, f)).size + " bytes");
  });
}

main();

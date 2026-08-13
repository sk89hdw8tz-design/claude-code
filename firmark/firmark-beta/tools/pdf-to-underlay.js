#!/usr/bin/env node
/* ============================================================
   pdf-to-underlay — turn one page of a PDF into a PNG you can
   trace over in the Firmark plan canvas.

   The canvas will not take a PDF. That is deliberate: tracing is
   a human reading a drawing, and a PDF page is a container full
   of vectors, clipped rasters and text that a browser would have
   to interpret. Interpreting it is where a machine starts guessing
   what a line means. So the PDF is flattened to pixels HERE, on a
   real rasteriser, and the human traces the pixels.

   This script does not decide anything about the drawing. It has
   no opinion about scale — the two-click calibration in the app is
   the only thing that gives the image a scale, and it needs no help
   from the DPI used here.

   Usage:
     node tools/pdf-to-underlay.js plan.pdf
     node tools/pdf-to-underlay.js plan.pdf --page 3 --dpi 200
     node tools/pdf-to-underlay.js plan.pdf --out /tmp/a3.png
     node tools/pdf-to-underlay.js --check      what this machine has

   Exit codes:  0 wrote a PNG · 2 bad arguments · 3 no rasteriser
   ============================================================ */

"use strict";

var fs = require("fs");
var path = require("path");
var cp = require("child_process");

var NAME = "pdf-to-underlay";

/* ------------------------------------------------------------
   The rasterisers this script knows how to drive, best first.

   poppler leads because it is the one that renders a large
   architectural sheet at 200 dpi without eating the line weights,
   and because pdftoppm's -r flag means the same thing everywhere.
   ------------------------------------------------------------ */

var ENGINES = [
  {
    id: "pdftoppm",
    label: "pdftoppm (poppler)",
    probe: ["pdftoppm", "-v"],
    install: {
      mac: "brew install poppler",
      debian: "sudo apt-get install poppler-utils",
      fedora: "sudo dnf install poppler-utils",
      windows: "choco install poppler   (or scoop install poppler)"
    },
    /* pdftoppm appends -<page>.png to the prefix it is given */
    run: function (pdf, out, page, dpi) {
      var prefix = out.replace(/\.png$/i, "");
      sh("pdftoppm", ["-png", "-r", String(dpi), "-f", String(page), "-l", String(page),
                      "-singlefile", pdf, prefix]);
      return prefix + ".png";
    }
  },
  {
    id: "pdftocairo",
    label: "pdftocairo (poppler)",
    probe: ["pdftocairo", "-v"],
    install: {
      mac: "brew install poppler",
      debian: "sudo apt-get install poppler-utils",
      fedora: "sudo dnf install poppler-utils",
      windows: "choco install poppler"
    },
    run: function (pdf, out, page, dpi) {
      var prefix = out.replace(/\.png$/i, "");
      sh("pdftocairo", ["-png", "-r", String(dpi), "-f", String(page), "-l", String(page),
                        "-singlefile", pdf, prefix]);
      return prefix + ".png";
    }
  },
  {
    id: "mutool",
    label: "mutool (MuPDF)",
    probe: ["mutool", "-v"],
    install: {
      mac: "brew install mupdf-tools",
      debian: "sudo apt-get install mupdf-tools",
      fedora: "sudo dnf install mupdf",
      windows: "scoop install mupdf"
    },
    run: function (pdf, out, page, dpi) {
      sh("mutool", ["draw", "-o", out, "-r", String(dpi), pdf, String(page)]);
      return out;
    }
  },
  {
    id: "magick",
    label: "ImageMagick (magick)",
    probe: ["magick", "-version"],
    note: "ImageMagick delegates PDF reading to Ghostscript, so it needs that installed too.",
    install: {
      mac: "brew install imagemagick ghostscript",
      debian: "sudo apt-get install imagemagick ghostscript",
      fedora: "sudo dnf install ImageMagick ghostscript",
      windows: "choco install imagemagick ghostscript"
    },
    run: function (pdf, out, page, dpi) {
      sh("magick", ["-density", String(dpi), pdf + "[" + (page - 1) + "]",
                    "-background", "white", "-alpha", "remove", "-alpha", "off", out]);
      return out;
    }
  },
  {
    id: "convert",
    label: "ImageMagick (convert)",
    probe: ["convert", "-version"],
    note: "ImageMagick delegates PDF reading to Ghostscript, so it needs that installed too.",
    install: {
      mac: "brew install imagemagick ghostscript",
      debian: "sudo apt-get install imagemagick ghostscript",
      fedora: "sudo dnf install ImageMagick ghostscript",
      windows: "choco install imagemagick ghostscript"
    },
    run: function (pdf, out, page, dpi) {
      sh("convert", ["-density", String(dpi), pdf + "[" + (page - 1) + "]",
                     "-background", "white", "-alpha", "remove", "-alpha", "off", out]);
      return out;
    }
  },
  {
    id: "gs",
    label: "Ghostscript (gs)",
    probe: ["gs", "--version"],
    install: {
      mac: "brew install ghostscript",
      debian: "sudo apt-get install ghostscript",
      fedora: "sudo dnf install ghostscript",
      windows: "choco install ghostscript"
    },
    run: function (pdf, out, page, dpi) {
      sh("gs", ["-dQUIET", "-dNOPAUSE", "-dBATCH", "-sDEVICE=png16m",
                "-r" + dpi, "-dFirstPage=" + page, "-dLastPage=" + page,
                "-sOutputFile=" + out, pdf]);
      return out;
    }
  },
  {
    id: "pdf-to-png-converter",
    label: "npm pdf-to-png-converter",
    probeNode: "pdf-to-png-converter",
    install: {
      mac: "npm install pdf-to-png-converter",
      debian: "npm install pdf-to-png-converter",
      fedora: "npm install pdf-to-png-converter",
      windows: "npm install pdf-to-png-converter"
    },
    run: function (pdf, out, page, dpi) {
      /* the module is promise-based; this script is otherwise synchronous,
         so it hands control to a tiny async tail and exits from there */
      var mod = require("pdf-to-png-converter");
      var scale = dpi / 72;
      mod.pdfToPng(pdf, { pagesToProcess: [page], viewportScale: scale })
        .then(function (pages) {
          if (!pages || !pages.length) {
            fail(3, "pdf-to-png-converter returned no pages for page " + page + " of " + pdf + ".");
          }
          fs.writeFileSync(out, pages[0].content);
          report(out, pdf, page, dpi, "npm pdf-to-png-converter");
          process.exit(0);
        })
        .catch(function (e) {
          fail(3, "pdf-to-png-converter could not render " + pdf + ": " + e.message);
        });
      return null;    /* the async tail reports */
    }
  }
];

/* ---------------- plumbing ---------------- */

function sh(cmd, args) {
  var r = cp.spawnSync(cmd, args, { encoding: "utf8" });
  if (r.error) throw new Error(cmd + " could not be run: " + r.error.message);
  if (r.status !== 0) {
    throw new Error(cmd + " exited with status " + r.status +
                    (r.stderr ? "\n" + String(r.stderr).trim() : ""));
  }
  return r;
}

function available(e) {
  if (e.probeNode) {
    try { require.resolve(e.probeNode); return true; }
    catch (err) { return false; }
  }
  var r = cp.spawnSync(e.probe[0], e.probe.slice(1), { encoding: "utf8" });
  /* -v on poppler tools prints to stderr and exits non-zero on some builds,
     so "it ran at all" is the test, not the exit code */
  return !r.error;
}

function say(s) { process.stdout.write(s + "\n"); }
function err(s) { process.stderr.write(s + "\n"); }

function fail(code, msg) {
  err("");
  err(NAME + ": " + msg);
  err("");
  process.exit(code);
}

function platformKey() {
  if (process.platform === "darwin") return "mac";
  if (process.platform === "win32") return "windows";
  try {
    var rel = fs.readFileSync("/etc/os-release", "utf8");
    if (/fedora|rhel|centos|rocky|alma/i.test(rel)) return "fedora";
  } catch (e) { /* not fatal — fall through to the debian line */ }
  return "debian";
}

/* PNG header: width and height are big-endian 32-bit ints at byte 16 */
function pngSize(file) {
  try {
    var fd = fs.openSync(file, "r");
    var buf = Buffer.alloc(24);
    fs.readSync(fd, buf, 0, 24, 0);
    fs.closeSync(fd);
    if (buf.slice(1, 4).toString("latin1") !== "PNG") return null;
    return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) };
  } catch (e) { return null; }
}

function report(out, pdf, page, dpi, engineLabel) {
  var size = pngSize(out);
  var bytes = 0;
  try { bytes = fs.statSync(out).size; } catch (e) { bytes = 0; }
  say("");
  say(NAME + ": wrote " + out);
  say("  from     " + pdf + ", page " + page + " at " + dpi + " dpi");
  say("  rendered by " + engineLabel);
  say("  size     " + (size ? size.w + " x " + size.h + " px" : "unknown") +
      ", " + Math.round(bytes / 1024) + " KB");
  if (bytes > 6 * 1024 * 1024) {
    say("");
    say("  This is a large file. The app stores the underlay inside the model as a");
    say("  data URI, so it counts against what localStorage will hold. If saving the");
    say("  model fails, re-run with --dpi 120.");
  }
  say("");
  say("  Next: open the Firmark plan view, drop this PNG on the canvas, then press C");
  say("  and click two points a known distance apart — a dimensioned wall is best —");
  say("  and type that distance. Nothing traced off the image means anything until");
  say("  you have done that; the canvas says so until you do.");
  say("");
}

function usage() {
  say("");
  say(NAME + " — rasterise one PDF page to a PNG you can trace over.");
  say("");
  say("  node tools/pdf-to-underlay.js <file.pdf> [options]");
  say("");
  say("  --page N     which page, 1-based        (default 1)");
  say("  --dpi N      render resolution          (default 150)");
  say("  --out FILE   where to write the PNG     (default <file>-p<N>.png beside the PDF)");
  say("  --check      list the rasterisers this machine has, and stop");
  say("  --help       this text");
  say("");
  say("  The DPI does not set the drawing's scale. Only the two-click calibration in");
  say("  the app does that, and it works at any DPI. Higher DPI is a sharper image and");
  say("  a bigger file, nothing more. 150 suits a 24x36 sheet; 200 to 300 if the plan");
  say("  is a photocopy with thin lines.");
  say("");
}

function listEngines(found) {
  say("");
  say(NAME + ": rasterisers on this machine");
  say("");
  ENGINES.forEach(function (e) {
    var ok = found.indexOf(e.id) !== -1;
    say("  " + (ok ? "yes" : " no") + "   " + e.label);
  });
  say("");
}

function noEngineMessage() {
  var key = platformKey();
  err("");
  err(NAME + ": no PDF rasteriser on this machine, so the PDF cannot be flattened here.");
  err("");
  err("Nothing was written and nothing was guessed. Install ONE of these, then run the");
  err("same command again. The first is the one to pick if you have no preference — it");
  err("renders large architectural sheets without thinning the linework.");
  err("");
  ENGINES.forEach(function (e) {
    err("  " + e.label);
    err("      " + (e.install[key] || e.install.debian));
    if (e.note) err("      " + e.note);
  });
  err("");
  err("Checked for: " + ENGINES.map(function (e) {
    return e.probeNode ? e.probeNode + " (node module)" : e.probe[0];
  }).join(", ") + ".");
  err("");
  err("If none of these is available to you, any PDF viewer will do it by hand: open");
  err("the sheet, zoom so the whole page fills the window, and export or screenshot it");
  err("as a PNG. The app only needs pixels — the two-click calibration supplies the");
  err("scale, so a screenshot calibrates exactly as well as a 300 dpi render.");
  err("");
  process.exit(3);
}

/* ---------------- main ---------------- */

function main(argv) {
  var args = argv.slice(2);
  var pdf = null, page = 1, dpi = 150, out = null, check = false;
  var i, a;

  for (i = 0; i < args.length; i++) {
    a = args[i];
    if (a === "--help" || a === "-h") { usage(); return 0; }
    else if (a === "--check" || a === "--list") check = true;
    else if (a === "--page" || a === "-p") { page = parseInt(args[++i], 10); }
    else if (a === "--dpi" || a === "-r") { dpi = parseInt(args[++i], 10); }
    else if (a === "--out" || a === "-o") { out = args[++i]; }
    else if (a.charAt(0) === "-") {
      fail(2, "“" + a + "” is not an option this script has. Run with --help for the list.");
    } else if (pdf === null) pdf = a;
    else fail(2, "Two files were given (“" + pdf + "” and “" + a + "”). This script takes one PDF.");
  }

  var found = [];
  ENGINES.forEach(function (e) { if (available(e)) found.push(e.id); });

  if (check) { listEngines(found); return found.length ? 0 : 3; }

  if (pdf === null) {
    usage();
    err(NAME + ": no PDF was given. Name the file you want to trace over.");
    return 2;
  }
  if (!/\.pdf$/i.test(pdf)) {
    fail(2, "“" + pdf + "” is not a .pdf. This script converts a PDF; a PNG or JPG can be " +
            "dropped straight onto the plan canvas without it.");
  }
  if (!fs.existsSync(pdf)) {
    fail(2, "“" + pdf + "” does not exist. Check the path — it is relative to " + process.cwd() + ".");
  }
  if (!(page >= 1)) {
    fail(2, "--page must be a whole number from 1 up; got “" + page + "”. Page numbering is 1-based.");
  }
  if (!(dpi >= 30 && dpi <= 900)) {
    fail(2, "--dpi must be between 30 and 900; got “" + dpi + "”. 150 suits most sheets.");
  }

  if (!found.length) noEngineMessage();

  if (out === null) {
    out = path.join(path.dirname(pdf),
                    path.basename(pdf).replace(/\.pdf$/i, "") + "-p" + page + ".png");
  }
  if (!/\.png$/i.test(out)) out = out + ".png";

  var dir = path.dirname(out);
  if (!fs.existsSync(dir)) {
    fail(2, "The output folder “" + dir + "” does not exist. Create it, or give --out a path that does.");
  }

  var tried = [];
  for (i = 0; i < ENGINES.length; i++) {
    var e = ENGINES[i];
    if (found.indexOf(e.id) === -1) continue;
    try {
      var wrote = e.run(pdf, out, page, dpi);
      /* An async engine owns the exit from its own promise tail. Returning a
         code here would exit the process before it had written anything —
         which it silently did, once. */
      if (wrote === null) return null;
      if (!fs.existsSync(wrote)) {
        throw new Error("it reported success but wrote no file at " + wrote +
                        " — the page number may be past the end of the document");
      }
      report(wrote, pdf, page, dpi, e.label);
      return 0;
    } catch (ex) {
      tried.push("  " + e.label + " — " + ex.message);
    }
  }

  err("");
  err(NAME + ": every rasteriser on this machine failed on " + pdf + ", page " + page + ".");
  err("");
  tried.forEach(function (t) { err(t); });
  err("");
  err("Most often this is the page number: check how many pages the file has. If the PDF");
  err("is password-protected or damaged, open it in a viewer and export the page as a PNG");
  err("by hand — the app only needs pixels.");
  err("");
  return 3;
}

var code = main(process.argv);
if (code !== null) process.exit(code);

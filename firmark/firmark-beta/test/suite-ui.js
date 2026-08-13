/* ============================================================
   suite-ui.js — the controls, and the claims they make.

   WHY THIS FILE EXISTS
   --------------------
   A finished tool shipped with a button labelled "Plan set (DXF)" that had
   never done anything but toast "isn't wired up yet". It survived every
   review, every suite and every demo, because nothing in this project ever
   asserted the one thing that matters about a control: THAT IT DOES
   SOMETHING. The engine was tested to four decimal places while the UI
   promised a capability the product did not have.

   Two kinds of check live here, and the split is deliberate:

     · Behaviour that is only observable in a browser — a click producing a
       route change, a panel opening, a disabled button carrying its reason —
       is asserted in test/ui-tests.js against real Chromium. It cannot be
       faked here, because harness.js stubs are inert by design and a test
       that passed because a stub returned something would be worthless.

     · The claims a control MAKES are text, and text can be read without a
       browser. That is what this file does: it reads the sources and the
       assembled bundle and refuses the shapes that produced the defect —
       an apology in a toast, a URL offered to an offline bundle, a past-tense
       download claim the page cannot verify, a view with no renderer, a
       shortcut the Help page advertises that the dispatcher does not have.

   The rule these enforce is the one the owner set: a control either works, or
   it is not there. A button that apologises is not honest-by-disclosure — it
   is a promise the product cannot keep, sitting in a UI whose whole
   credibility rests on saying only what it can back up.
   ============================================================ */

"use strict";

var fs = require("fs");
var path = require("path");

var DIR = path.join(__dirname, "..");

/* Comments are stripped before every scan. The fixes in these files quote the
   defective line verbatim so the next reader knows what was there, and a scan
   that cannot tell code from prose reads that quotation as the defect. */
function code(file) {
  return fs.readFileSync(path.join(DIR, file), "utf8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:"'`\\])\/\/[^\n]*/g, "$1");
}
function raw(file) { return fs.readFileSync(path.join(DIR, file), "utf8"); }
function has(file) { return fs.existsSync(path.join(DIR, file)); }

/* every string literal in a file, single or double quoted */
function literals(src) {
  return (src.match(/"[^"\\]*(?:\\.[^"\\]*)*"|'[^'\\]*(?:\\.[^'\\]*)*'/g) || []);
}

/* the view files whose controls this pass owns */
var VIEW_FILES = ["core.js", "materials.js", "sheet.js", "sizing.js", "pipeline-view.js"];
/* every file that renders a control, including the ones owned elsewhere —
   an apology in someone else's view is still an apology in this product */
var ALL_VIEW_FILES = VIEW_FILES.concat(["cad.js", "stages-view.js", "planset.js"]);

module.exports = function (t, FM) {

  /* ============================================================
     1. No control apologises
     ============================================================ */

  t.suite("ui · a control either works or it is not there");

  (function () {
    /* The exact shape that shipped: a button whose entire behaviour is a toast
       saying the button does not work. Three of these were in core.js alone. */
    var APOLOGY = /isn.?t wired|is not wired|not wired up|wired up yet|coming soon|not implemented yet|Beta:\s/i;
    var offenders = [];
    ALL_VIEW_FILES.forEach(function (f) {
      if (!has(f)) return;
      literals(code(f)).forEach(function (lit) {
        if (APOLOGY.test(lit)) offenders.push(f + ": " + lit.slice(0, 72));
      });
    });
    t.eq(offenders.length, 0,
      "no view renders a control whose behaviour is an apology for not working" +
      (offenders.length ? "\n      " + offenders.slice(0, 6).join("\n      ") : ""));
  })();

  (function () {
    /* An offline bundle cannot open a URL. The Materials "About this data"
       button toasted "…published for review at github.com/…" — nothing in it
       could be clicked, nothing checked, and the one question the button
       exists to answer went unanswered while looking answered. */
    var offenders = [];
    ALL_VIEW_FILES.forEach(function (f) {
      if (!has(f)) return;
      var src = code(f);
      /* only literals that are handed to a toast — a URL in a data field or a
         citation string is a fact about a document, not a promise of a link */
      var calls = src.match(/(FM\.)?toast\(\s*("[^"\\]*(?:\\.[^"\\]*)*"|'[^'\\]*(?:\\.[^'\\]*)*')/g) || [];
      calls.forEach(function (c) {
        if (/https?:\/\/|www\.|github\.com|\.com\/|\.org\//i.test(c)) {
          offenders.push(f + ": " + c.slice(0, 80));
        }
      });
    });
    t.eq(offenders.length, 0,
      "no toast offers a web address to a bundle that has no network" +
      (offenders.length ? "\n      " + offenders.slice(0, 5).join("\n      ") : ""));
  })();

  (function () {
    /* A download is a REQUEST, not an outcome. This bundle is opened three
       ways — file://, a local server, and a hosted artefact whose sandbox
       blocks page-initiated downloads outright — and in the third the anchor
       click does nothing at all, with no error to catch. "Calc record
       downloaded." and "Schedule exported —" were both false there, and a
       control that silently does nothing in one deployment is as broken as one
       that does nothing anywhere. */
    var CLAIMS = /\b(downloaded|download complete|saved to your|has been saved|export(ed)? —|exported\.)/i;
    var offenders = [];
    VIEW_FILES.forEach(function (f) {
      if (!has(f)) return;
      var calls = code(f).match(/(FM\.)?toast\(\s*("[^"\\]*(?:\\.[^"\\]*)*"|'[^'\\]*(?:\\.[^'\\]*)*')/g) || [];
      calls.forEach(function (c) { if (CLAIMS.test(c)) offenders.push(f + ": " + c.slice(0, 80)); });
    });
    t.eq(offenders.length, 0,
      "no export claims, in the past tense, a download the page cannot verify" +
      (offenders.length ? "\n      " + offenders.slice(0, 5).join("\n      ") : ""));
  })();

  (function () {
    /* and the mechanism that replaced the claim actually exists */
    var core = code("core.js");
    t.truthy(/function deliver\s*\(/.test(core) && /deliver:\s*deliver/.test(core),
      "core.js exposes FM.deliver — the one path an export hands its artefact over");
    t.truthy(/recordScrim/.test(raw("shell.html")) && /recordText/.test(raw("shell.html")),
      "and the shell carries the panel it renders into, so the artefact is on screen " +
      "wherever the bundle is opened");
    t.truthy(/FM\.deliver\(/.test(code("sizing.js")),
      "the Sizing schedule export goes through it rather than straight at a blob");
    t.truthy(/deliver\(\{/.test(core),
      "so does the calc record");
  })();

  /* ============================================================
     2. The DXF button is conditional on the exporter
     ============================================================ */

  t.suite("ui · the DXF export exists only when the exporter does");

  (function () {
    var core = code("core.js");
    t.truthy(/function dxfReady\s*\(/.test(core),
      "core.js asks whether FM.dxf is in this build before offering a DXF control");
    t.truthy(/if\s*\(dxfReady\(\)\)/.test(core),
      "and the button is pushed onto the toolbar inside that guard, not rendered and apologetic");
    /* the contract, as this build depends on it */
    t.truthy(/FM\.dxf\.fromModel\(/.test(core),
      "the button calls the contracted entry point FM.dxf.fromModel(model, opts)");
    t.truthy(/catch\s*\(e\)\s*\{[\s\S]{0,200}?toast\(/.test(core.slice(core.indexOf("function exportDXF"))),
      "and a refusal from it is published verbatim — a refusal is a fact about the " +
      "model, not an apology for a missing feature");
    /* a disabled control says why, and the reason is a real string */
    t.truthy(/function dxfBlocker\s*\(/.test(core),
      "with no geometry the control is disabled and carries the reason it is disabled");
  })();

  (function () {
    /* A module that exists but was never assembled into the bundle is the
       "stale bundle" failure this project has already shipped once. */
    var manifest = raw("build.js");
    if (has("dxf.js")) {
      t.truthy(manifest.indexOf('"dxf.js"') !== -1,
        "dxf.js is in the build manifest, so FM.dxf actually reaches the page");
      t.truthy(raw("firmark-app.html").indexOf("AC1009") !== -1,
        "and the assembled bundle carries it");
    } else {
      t.truthy(manifest.indexOf('"dxf.js"') === -1,
        "no dxf.js in the tree and none in the manifest — the button will not be rendered");
    }
  })();

  /* ============================================================
     3. Every route reaches a renderer
     ============================================================ */

  t.suite("ui · every view in the shell has something to render");

  (function () {
    var shell = raw("shell.html");
    var ids = (shell.match(/id="view-([a-z-]+)"/g) || []).map(function (s) {
      return s.replace(/id="view-|"/g, "");
    });
    t.truthy(ids.length >= 15, "the shell declares " + ids.length + " view slots");

    var all = "";
    ALL_VIEW_FILES.forEach(function (f) { if (has(f)) all += code(f); });
    var missing = ids.filter(function (id) {
      return all.indexOf("VIEWS." + id + " =") === -1 &&
             all.indexOf("VIEWS[\"" + id + "\"] =") === -1;
    });
    /* A slot with no renderer is a route that switches a class and shows an
       empty box — the exact "tab that sets a class but renders the same
       content" this pass was told to treat as dead. */
    t.eq(missing.length, 0,
      "every view slot has a registered renderer" +
      (missing.length ? " — nothing renders " + missing.join(", ") : ""));
  })();

  (function () {
    /* Every rail destination is a real route. The rail is the primary
       navigation; an entry pointing at a slot that does not exist would be a
       dead control in the one place a user cannot avoid. */
    var core = code("core.js");
    var navBlock = core.slice(core.indexOf("var NAV = ["), core.indexOf("var ICONS"));
    var ids = (navBlock.match(/id:\s*"([a-z-]+)"/g) || []).map(function (s) {
      return s.replace(/id:\s*"|"/g, "");
    });
    var shell = raw("shell.html");
    var orphan = ids.filter(function (id) { return shell.indexOf('id="view-' + id + '"') === -1; });
    t.truthy(ids.length >= 15, "the sidebar rail offers " + ids.length + " destinations");
    t.eq(orphan.length, 0,
      "and every one of them is a view slot in the shell" +
      (orphan.length ? " — " + orphan.join(", ") + " go nowhere" : ""));
  })();

  /* ============================================================
     4. The keyboard: advertised is implemented
     ============================================================ */

  t.suite("ui · the Help page advertises exactly the shortcuts that exist");

  (function () {
    var core = code("core.js");
    var block = core.slice(core.indexOf("var GO_KEYS = ["));
    block = block.slice(0, block.indexOf("];") + 2);
    var keys = (block.match(/key:\s*"([a-z])"/g) || []).map(function (s) { return s.replace(/key:\s*"|"/g, ""); });
    var routes = (block.match(/route:\s*"([a-z-]+)"/g) || []).map(function (s) { return s.replace(/route:\s*"|"/g, ""); });

    t.truthy(keys.length >= 8, "core.js declares " + keys.length + " g-shortcuts in one table");
    t.eq(keys.length, routes.length, "every shortcut names a route");

    /* one table, read by both the dispatcher and the Help page — the Help card
       used to be hand-typed and had silently dropped `g o` and `g s` */
    t.truthy(/goKeyMap\(\)\[e\.key\.toLowerCase\(\)\]/.test(core),
      "the key dispatcher reads that table rather than a second copy of it");
    t.truthy(/GO_KEYS\.map\(/.test(core),
      "and so does the Help page, so the two cannot drift");

    var shell = raw("shell.html");
    var orphan = routes.filter(function (r) { return shell.indexOf('id="view-' + r + '"') === -1; });
    t.eq(orphan.length, 0,
      "every advertised shortcut names a view that exists" +
      (orphan.length ? " — " + orphan.join(", ") : ""));

    var dupes = keys.filter(function (k, i) { return keys.indexOf(k) !== i; });
    t.eq(dupes.length, 0, "and no two shortcuts claim the same key" +
      (dupes.length ? " — " + dupes.join(", ") : ""));
  })();

  /* ============================================================
     5. The router writes the address once
     ============================================================ */

  t.suite("ui · a navigation renders its view once");

  (function () {
    var core = code("core.js");
    /* The boolean was raised and lowered on consecutive lines around
       `location.hash = ...`. hashchange fires on a LATER task, so it always
       arrived with the flag back down, applyHash() ran, and go() re-entered:
       every navigation in this app rendered its view twice. It is why editing
       a mark on a sheet tore the sheet out from under the caret. */
    t.truthy(/applyingHash\s*=\s*true;[\s\S]{0,160}?applyingHash\s*=\s*false;/.test(core) === false,
      "the hash write is not guarded by a flag lowered before the event it guards against");
    t.truthy(/function writingHash\s*\(/.test(core) && /ourWrites\+\+/.test(core),
      "our own hash writes are counted instead");
    t.truthy(/function onHashChange\s*\(/.test(core) && /ourWrites--/.test(core),
      "and the listener decrements one per write, so a Back or a pasted URL still routes");
    t.truthy(/hashTimer\s*=\s*setTimeout/.test(core),
      "with a self-clearing count, so a stray write cannot leave the router deaf to the address bar");
    t.truthy(/addEventListener\("hashchange", onHashChange\)/.test(core),
      "the listener that is registered is the counting one");
  })();

  /* ============================================================
     6. A sheet edit is an edit to the sheet
     ============================================================ */

  t.suite("ui · editing a calculation edits the calculation");

  (function () {
    var sheet = code("sheet.js");
    /* `inputsFor()` exists so "a list row and its sheet can never disagree" —
       but they disagreed the moment anyone touched a control, because the
       sheet edited a private copy and never returned it. */
    t.truthy(/Object\.keys\(sheet\.inputs\)\.forEach/.test(sheet) &&
             /sheet\.inputs\[k\]\s*=\s*inp\[k\]/.test(sheet),
      "the sheet writes its working copy back to the record it came from");
    t.truthy(/if\s*\(inp\.incised !== undefined\) sheet\.inputs\.incised/.test(sheet),
      "including a condition the record predates, rather than dropping it");
    /* and only the record's own keys: deflLive/deflTotal come from the
       project's design profile and are not the sheet's to keep */
    t.truthy(sheet.indexOf("inp.deflLive = prof.deflLive") !== -1,
      "the deflection limits still come from the profile, not from the record");
  })();

  (function () {
    /* New-sheet creation is real, so the record it makes has to be complete
       enough for the engine to run — an incomplete sheet would render "Not
       evaluated" and the button would be a dead control with extra steps. */
    var core = code("core.js");
    var block = core.slice(core.indexOf("function addSheet"));
    block = block.slice(0, block.indexOf("\n  }") + 4);
    ["species", "grade", "size", "span", "spacing", "dead", "live", "roofLoad",
     "roofType", "repetitive", "wet", "braced", "bearing", "memberUse", "CF"].forEach(function (k) {
      t.truthy(new RegExp("\\b" + k + ":").test(block), "a new calculation declares " + k);
    });
    t.truthy(/CF:\s*"auto"/.test(block),
      "and it is created on the catalog C_F path, not the typed override");
    t.truthy(/session:\s*true/.test(block),
      "and it is marked session-only, because nothing stores it and a reload takes it away");

    /* the engine must actually accept those defaults */
    var defaults = {
      species: "Douglas Fir-Larch", grade: "No. 2", size: "2x10", span: 12.0, spacing: 16,
      dead: 15, live: 40, roofLoad: 0, roofType: "snow", repetitive: true, wet: false,
      incised: false, braced: true, bearing: 3.0, memberUse: "floor", CF: "auto",
      deflLive: 360, deflTotal: 240
    };
    var r = FM.engine.run(defaults);
    t.truthy(!r.error, "and the engine evaluates a brand-new sheet rather than refusing it" +
      (r.error ? " — " + r.message : ""));
    if (!r.error) {
      t.truthy(isFinite(r.governing.dcr) && r.governing.dcr > 0,
        "with a finite governing DCR (" + r.governing.dcr.toFixed(3) + ")");
    }
  })();

  /* ============================================================
     7. The stage rail
     ============================================================ */

  t.suite("ui · the stage rail names where it goes");

  (function () {
    var core = code("core.js");
    var block = core.slice(core.indexOf("function stageRail"));
    block = block.slice(0, block.indexOf("\n  }") + 4);
    /* Every chip used to call go("pipeline"): on a stage view that was six
       buttons that all went to the same place, and on the Run page — where the
       row also appears — six buttons that did nothing at all. */
    t.truthy(block.indexOf('go("pipeline")') === -1,
      "no chip navigates to the run regardless of the stage it names");
    t.truthy(/FM\.STAGE_VIEW/.test(block),
      "a chip opens the view of the stage it names");
    t.truthy(/aria-current":\s*here \? "step"/.test(block),
      "and the chip for the stage you are on is marked as the current step");
    t.truthy(/el\("span"/.test(block),
      "rendered as a marker rather than a button, so nothing that looks clickable is inert");
    t.truthy(/cursor:default/.test(block),
      "and without the pointer cursor .stage-chip carries for the button case");
    /* the mapping it depends on */
    var pv = code("pipeline-view.js");
    t.truthy(/FM\.STAGE_VIEW = VIEW_OF/.test(pv), "pipeline-view.js publishes that mapping");
    if (FM.pipeline && FM.pipeline.STAGES) {
      var mapped = (pv.match(/^\s*(\w+|"[\w]+"):\s*"[a-z]+",?$/gm) || []).length;
      t.truthy(mapped >= FM.pipeline.STAGES.length,
        "with a view for each of the " + FM.pipeline.STAGES.length + " stages");
    }
  })();

  (function () {
    var pv = code("pipeline-view.js");
    /* Anything disabled says why, on itself — a screen reader landing on a
       disabled button otherwise reads "Approve, dimmed" and nothing else. */
    t.truthy(/disabled:\s*row\.can \? null : "disabled"/.test(pv),
      "the Approve button is disabled when the gate is shut");
    t.truthy(/title:\s*row\.can \? null/.test(pv),
      "and carries the blockers as its own accessible name detail");
    t.truthy(/"aria-describedby":\s*row\.can \? null : "gate-block-"/.test(pv),
      "tied to the blocked-reason text by id");
    t.truthy(/id:\s*"gate-block-"\s*\+\s*st\.id/.test(pv),
      "and that text is always rendered when the gate is shut, even with no named blocker");
  })();

  /* ============================================================
     8. Materials: the citation is in the page, not in a link
     ============================================================ */

  t.suite("ui · the catalog cites itself offline");

  (function () {
    var m = code("materials.js");
    t.truthy(/aria-expanded/.test(m) && /aria-controls/.test(m),
      "\"About this data\" is a disclosure control and announces itself as one");
    t.truthy(/MATDATA\.meta/.test(m) && /source_file/.test(m) && /dataset_version/.test(m),
      "and it renders the provenance the payload already carries");
    t.truthy(/governing_reference/.test(m),
      "including the governing reference for each dataset");
    t.truthy(m.indexOf("github.com") === -1,
      "with no web address offered to a bundle that cannot open one");

    /* the payload really does carry what the panel promises to show */
    var meta = null;
    try { meta = JSON.parse(raw("matdata.json")).meta; } catch (e) { meta = null; }
    t.truthy(meta && typeof meta === "object", "matdata.json carries a provenance block");
    if (meta) {
      /* The block mixes per-dataset records with two loose strings about the
         extraction as a whole. The panel lists the first kind as datasets and
         puts the second in the footer — listing `repo` and `extracted` as
         datasets would print rows of em-dashes and imply sources that are not
         there. So the assertion distinguishes them the same way the view does. */
      var keys = Object.keys(meta).filter(function (k) {
        return meta[k] && typeof meta[k] === "object";
      });
      t.truthy(keys.length >= 5, "covering " + keys.length + " datasets");
      var bare = keys.filter(function (k) { return !meta[k].source_file; });
      t.eq(bare.length, 0,
        "and every one of them names the seed file it was extracted from" +
        (bare.length ? " — " + bare.join(", ") + " do not" : ""));
      t.truthy(/typeof meta\[k\] === "object" && meta\[k\]\.source_file/.test(m),
        "and the panel selects them the same way, so a loose string is never shown as a dataset");
      t.truthy(/meta\.repo/.test(m) && /meta\.extracted/.test(m),
        "with the repository and the extraction date named in the footer, where they are true");
    }
  })();

  /* ============================================================
     9. ES5, in the files this pass touched
     ============================================================ */

  t.suite("ui · the views stay ES5");

  (function () {
    /* The bundle ships as one self-contained file opened over file://. One
       arrow function is a syntax error in the oldest browser this is expected
       to open in, and a syntax error in a concatenated bundle takes out every
       module after it, not just the one that has it. */
    var offenders = [];
    VIEW_FILES.forEach(function (f) {
      if (!has(f)) return;
      var src = code(f);
      /* strip string literals too — prose inside a string is not syntax */
      src = src.replace(/"[^"\\]*(?:\\.[^"\\]*)*"|'[^'\\]*(?:\\.[^'\\]*)*'/g, '""');
      [[/\blet\s+[A-Za-z_$]/, "let"],
       [/\bconst\s+[A-Za-z_$]/, "const"],
       [/=>/, "arrow function"],
       [/`/, "template literal"],
       [/\bclass\s+[A-Za-z_$]/, "class"],
       [/Object\.assign\s*\(/, "Object.assign"],
       [/\.\.\./, "spread"]].forEach(function (pair) {
        if (pair[0].test(src)) offenders.push(f + ": " + pair[1]);
      });
    });
    t.eq(offenders.length, 0,
      "no ES6 in the view layer" + (offenders.length ? " — " + offenders.join(", ") : ""));
  })();

  /* ============================================================
     10. Accessibility of the controls this pass added
     ============================================================ */

  t.suite("ui · added controls are labelled and reachable");

  (function () {
    var shell = raw("shell.html");
    t.truthy(/role="dialog"/.test(shell) && /aria-modal="true"/.test(shell),
      "the record panel is a dialog and says so");
    t.truthy(/aria-labelledby="recordTitle"/.test(shell),
      "and is named by its own heading");
    t.truthy(/id="recordText"[\s\S]{0,200}aria-label=/.test(shell),
      "its text area carries a label rather than relying on placement");
    t.truthy(/id="recordClose"/.test(shell) && /id="recordSave"/.test(shell) &&
             /id="recordSelect"/.test(shell),
      "and every action in it is a real button");

    var core = code("core.js");
    t.truthy(/function trapDialogTab/.test(core) && /recordScrim/.test(core),
      "Tab is kept inside whichever dialog is open, the palette or the record panel");
    t.truthy(/closeRecord\(\);\s*closePalette\(\)/.test(core),
      "Escape closes it");
    t.truthy(/deliverReturn && document\.contains\(deliverReturn\)/.test(core),
      "and focus goes back where the user left it");

    var sh = code("sheet.js");
    t.truthy(/"aria-label":\s*"Mark"/.test(sh) && /"aria-label":\s*"Description"/.test(sh),
      "the sheet's mark and description fields are labelled");
    t.truthy(/setAttribute\("aria-invalid"/.test(sh),
      "and a mark that would collide with another sheet is announced as invalid rather than " +
      "silently ignored");
  })();
};

/* Headless loader: runs the DOM-free layers (engine, solver, regions,
   jurisdiction, cad model, takeoff, bom, planset text) in a sandbox so they
   can be regression-tested without a browser.

   Some modules pair DOM-free logic with a view in one file — `cad.js` owns
   both the geometry model and the canvas, `planset.js` owns both `text()` and
   the sheet renderer. Those files must LOAD here so their logic is testable,
   which means the sandbox needs enough of a browser for module-scope code to
   run without throwing.

   The stubs below are deliberately INERT and deliberately obvious. They are
   not a fake DOM: `createElement` returns a bag with no behaviour, and every
   storage read misses. If a test ever appears to pass because of something a
   stub returned, that test is wrong — real DOM behaviour is covered by
   test/ui-tests.js against a real browser. */

"use strict";
var fs = require("fs");
var vm = require("vm");
var path = require("path");

/* the DOM-free set, in dependency order */
var DEFAULT = [
  "scope.js", "engine.js", "weights.js", "solver.js",
  "jurisdiction.js", "cad.js", "takeoff.js", "bom.js",
  "export.js", "planset.js",
  "auth.js", "pipeline.js", "project.js"
];

function stubNode() {
  var n = {
    nodeType: 1, style: {}, dataset: {}, children: [], childNodes: [],
    classList: { add: function () {}, remove: function () {}, toggle: function () {}, contains: function () { return false; } },
    appendChild: function (c) { this.children.push(c); return c; },
    removeChild: function () {}, insertBefore: function (c) { return c; },
    setAttribute: function () {}, removeAttribute: function () {}, getAttribute: function () { return null; },
    hasAttribute: function () { return false; },
    addEventListener: function () {}, removeEventListener: function () {},
    querySelector: function () { return null; }, querySelectorAll: function () { return []; },
    focus: function () {}, click: function () {}, remove: function () {},
    textContent: "", innerHTML: "", innerText: "", value: "",
    getBoundingClientRect: function () { return { x: 0, y: 0, width: 0, height: 0, top: 0, left: 0, right: 0, bottom: 0 }; }
  };
  return n;
}

function stubDoc() {
  return {
    documentElement: stubNode(),
    body: stubNode(),
    createElement: function () { return stubNode(); },
    createElementNS: function () { return stubNode(); },
    createTextNode: function () { return stubNode(); },
    getElementById: function () { return null; },
    querySelector: function () { return null; },
    querySelectorAll: function () { return []; },
    addEventListener: function () {}, removeEventListener: function () {},
    title: ""
  };
}

function stubStorage() {
  /* always empty, never persists — a module must behave correctly with no
     saved state, and that is the case worth testing headlessly */
  return {
    getItem: function () { return null; },
    setItem: function () {}, removeItem: function () {}, clear: function () {},
    key: function () { return null; }, length: 0
  };
}

function load(files) {
  var dir = path.join(__dirname, "..");
  var sandbox = {
    console: console, Math: Math, JSON: JSON, Date: Date,
    setTimeout: function () { return 0; }, clearTimeout: function () {},
    isFinite: isFinite, isNaN: isNaN, parseFloat: parseFloat, parseInt: parseInt
  };
  sandbox.window = sandbox;
  sandbox.self = sandbox;
  sandbox.FM = {};
  sandbox.document = stubDoc();
  sandbox.localStorage = stubStorage();
  sandbox.matchMedia = function () { return { matches: false, addEventListener: function () {}, addListener: function () {} }; };
  sandbox.requestAnimationFrame = function () { return 0; };
  sandbox.getComputedStyle = function () { return {}; };
  sandbox.URL = { createObjectURL: function () { return "blob:stub"; }, revokeObjectURL: function () {} };
  sandbox.Blob = function () {};
  sandbox.HEADLESS = true;   /* a module may check this; nothing should NEED to */

  vm.createContext(sandbox);
  sandbox.MATDATA = JSON.parse(fs.readFileSync(path.join(dir, "matdata.json"), "utf8"));

  var list = files || DEFAULT;
  list.forEach(function (f) {
    var p = path.join(dir, f);
    /* A module still being written is skipped, loudly. It is never silent:
       a suite that depends on it will fail on the missing surface, which is
       the correct outcome. */
    if (!fs.existsSync(p)) {
      console.log("  [harness] " + f + " does not exist yet — not loaded");
      return;
    }
    try {
      vm.runInContext(fs.readFileSync(p, "utf8"), sandbox, { filename: f });
    } catch (e) {
      console.log("  [harness] " + f + " THREW while loading: " + e.message);
      throw e;
    }
  });
  return sandbox.FM;
}

module.exports = { load: load, DEFAULT: DEFAULT };

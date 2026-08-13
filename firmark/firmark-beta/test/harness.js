/* Headless loader: runs the DOM-free layers (engine, solver, regions) in a
   sandbox so they can be regression-tested without a browser. */
"use strict";
var fs = require("fs");
var vm = require("vm");
var path = require("path");

function load(files) {
  var dir = path.join(__dirname, "..");
  var sandbox = { console: console, Math: Math, JSON: JSON, Date: Date };
  sandbox.window = sandbox;
  sandbox.FM = {};
  vm.createContext(sandbox);
  sandbox.MATDATA = JSON.parse(fs.readFileSync(path.join(dir, "matdata.json"), "utf8"));
  (files || ["engine.js"]).forEach(function (f) {
    vm.runInContext(fs.readFileSync(path.join(dir, f), "utf8"), sandbox, { filename: f });
  });
  return sandbox.FM;
}

module.exports = { load: load };

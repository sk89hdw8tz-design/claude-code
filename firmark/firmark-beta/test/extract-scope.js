#!/usr/bin/env node
/* Regenerates scope.js from calc-spec.md §8. The suite re-runs this and diffs
   the result, so a change to the spec's boundary list cannot silently fail to
   reach the output the spec says must carry it. */
"use strict";
var fs = require("fs"), path = require("path");
var md = fs.readFileSync(path.join(__dirname, "..", "calc-spec.md"), "utf8");
var sec = md.slice(md.indexOf("## 8. Scope boundaries"),
                   md.indexOf("## 9. Consolidated material-repo gap register"));
function clean(t) {
  return t.join(" ").replace(/\*\*(.+?)\*\*/g, "$1").replace(/\*(.+?)\*/g, "$1")
          .replace(/`/g, "").replace(/\s+/g, " ").trim();
}
var items = [], cur = null;
sec.split("\n").forEach(function (line) {
  var g = /^\*\*(.+?)\*\*\s*$/.exec(line.trim());
  if (g && !/^\d/.test(line.trim())) { cur = g[1]; return; }
  var m = /^(\d+)\.\s+(.*)$/.exec(line);
  if (m) items.push({ n: Number(m[1]), group: cur, text: [m[2].replace(/\s+$/, "")] });
  else if (items.length && /^\s{2,}\S/.test(line)) items[items.length - 1].text.push(line.trim());
});
module.exports = {
  items: items.map(function (i) { return { n: i.n, group: i.group, text: clean(i.text) }; }),
  preamble: clean(sec.slice(0, sec.indexOf("**Structural configuration**")).split("\n")
    .filter(function (l) { return l.trim() && l.charAt(0) !== "#"; }))
};

/* ============================================================
   suite-dxf.js — dxf.js · the CAD model -> AutoCAD DXF

   WHY THIS SUITE IS SHAPED THE WAY IT IS
   --------------------------------------
   A DXF that is wrong does not throw. It opens as an empty
   drawing, or as the right drawing at 1/12 scale, or with every
   wall on layer 0 because the layer it named is not in the
   tables. None of those failures produce an error message
   anywhere, and all of them look like success from the writing
   side: a string was produced, it was long, it began with a 0
   and ended with EOF.

   So this file does not check that a string came back. It
   contains a SECOND, INDEPENDENT DXF READER — group-code/value
   pairs, section structure, table and entity extraction —
   written from the format rather than from dxf.js, and it parses
   the exporter's own output back and asserts against the model
   that produced it. The parser deliberately shares no code with
   the writer: a parser shipped inside dxf.js would agree with a
   writer bug.

   What the assertions below actually pin:

     1. STRUCTURE. Every SECTION is closed by an ENDSEC, every
        TABLE by an ENDTAB, every POLYLINE by a SEQEND, the file
        ends at 0/EOF, and no group code appears without a value.

     2. REFERENTIAL INTEGRITY. Every entity's layer (code 8) is
        in the LAYER table, every layer's linetype (code 6) is in
        the LTYPE table, every TEXT's style (code 7) is in the
        STYLE table. This is the failure that silently moves the
        whole drawing onto layer 0.

     3. UNITS. A wall of known length in feet comes back with the
        length in INCHES, $INSUNITS is 1, and $EXTMIN/$EXTMAX are
        in the same units as the entities. Getting this wrong
        opens the drawing at 12x or 1/12 and is the single most
        common DXF failure there is.

     4. EXTENTS. $EXTMIN/$EXTMAX genuinely bound every coordinate
        of every entity written — including the title block and
        the notes, which sit outside the geometry. A drawing whose
        extents cover only the house opens with its own title
        block off screen.

     5. COUNTS. The number of wall face polylines equals the
        number of walls the model determines faces for; regions,
        openings and placed marks likewise. An exporter that drops
        a wall produces a file that parses perfectly.

     6. REFUSAL. NaN, Infinity, a zero-length wall, a model with
        no drawable geometry — each one is checked for the
        specific behaviour it should have, and the whole-file
        assertion is the blunt one: the output text contains no
        NaN and no Infinity anywhere a number belongs, ever.

   All five shipped plans go through the whole of it.
   ============================================================ */

"use strict";

module.exports = function (t, FM) {
  var suite = t.suite, eq = t.eq, near = t.near, truthy = t.truthy, bad = t.bad;

  /* dxf.js is not in the harness's DEFAULT list unless somebody added it
     there. Rather than depend on that, load a sandbox that definitely
     has it. If FM already carries FM.dxf we use it as-is. */
  if (!FM || !FM.dxf) {
    var harness = require("./harness.js");
    FM = harness.load(harness.DEFAULT.concat(["dxf.js"]));
  }
  var dxf = FM.dxf;

  if (!dxf) {
    suite("dxf · module");
    bad("FM.dxf is not registered — dxf.js did not load");
    return;
  }

  /* ============================================================
     AN INDEPENDENT DXF READER

     Written from the DXF group-code format, not from dxf.js.
     ============================================================ */

  function parse(text) {
    var out = {
      ok: true, problems: [],
      pairs: [], sections: {}, sectionOrder: [],
      header: {}, tables: {}, entities: [], eof: false, lineCount: 0
    };
    if (typeof text !== "string" || !text.length) {
      out.ok = false; out.problems.push("empty or non-string input");
      return out;
    }
    /* DXF is line-oriented: group code on one line, value on the next.
       A file with an odd number of lines is torn. */
    var raw = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n");
    while (raw.length && raw[raw.length - 1] === "") raw.pop();
    out.lineCount = raw.length;
    if (raw.length % 2 !== 0) out.problems.push("odd line count " + raw.length + " — a group code has no value");

    var i;
    for (i = 0; i + 1 < raw.length; i += 2) {
      var codeText = raw[i];
      if (!/^\s*-?\d+\s*$/.test(codeText)) {
        out.ok = false;
        out.problems.push("line " + (i + 1) + " is not a group code: \"" + codeText + "\"");
        return out;
      }
      out.pairs.push({ code: Number(codeText), value: raw[i + 1], line: i + 1 });
    }

    /* ---- sections ---- */
    var depth = 0, cur = null, secStart = 0, p;
    for (i = 0; i < out.pairs.length; i++) {
      p = out.pairs[i];
      if (p.code === 0 && p.value === "SECTION") {
        if (depth !== 0) out.problems.push("SECTION opened inside a SECTION at line " + p.line);
        depth++;
        var nm = out.pairs[i + 1];
        if (!nm || nm.code !== 2) { out.problems.push("SECTION at line " + p.line + " has no name (code 2)"); cur = "(unnamed)"; }
        else cur = nm.value;
        secStart = i + 2;
        continue;
      }
      if (p.code === 0 && p.value === "ENDSEC") {
        if (depth !== 1) out.problems.push("ENDSEC with no open SECTION at line " + p.line);
        depth--;
        out.sections[cur] = out.pairs.slice(secStart, i);
        out.sectionOrder.push(cur);
        cur = null;
        continue;
      }
      if (p.code === 0 && p.value === "EOF") {
        if (depth !== 0) out.problems.push("EOF while a SECTION is still open");
        out.eof = (i === out.pairs.length - 1);
        if (!out.eof) out.problems.push("EOF is not the last pair in the file");
      }
    }
    if (depth !== 0) out.problems.push("a SECTION was never closed by ENDSEC");
    if (!out.eof) out.problems.push("the file does not end at 0/EOF");

    /* ---- header: 9/$NAME then that variable's own codes ---- */
    var hs = out.sections.HEADER || [];
    var name = null;
    for (i = 0; i < hs.length; i++) {
      if (hs[i].code === 9) { name = hs[i].value; out.header[name] = {}; continue; }
      if (name) {
        if (out.header[name][hs[i].code] === undefined) out.header[name][hs[i].code] = hs[i].value;
      } else out.problems.push("a header value appears before any $VARIABLE name");
    }

    /* ---- tables ---- */
    var ts = out.sections.TABLES || [];
    var tName = null, tDepth = 0, entry = null, entryCode = null;
    for (i = 0; i < ts.length; i++) {
      p = ts[i];
      if (p.code === 0 && p.value === "TABLE") {
        if (tDepth !== 0) out.problems.push("TABLE opened inside a TABLE");
        tDepth++;
        var tn = ts[i + 1];
        tName = (tn && tn.code === 2) ? tn.value : "(unnamed)";
        if (!tn || tn.code !== 2) out.problems.push("TABLE with no name");
        out.tables[tName] = [];
        entry = null; entryCode = tName;
        continue;
      }
      if (p.code === 0 && p.value === "ENDTAB") {
        if (tDepth !== 1) out.problems.push("ENDTAB with no open TABLE");
        tDepth--;
        tName = null; entry = null;
        continue;
      }
      if (p.code === 0 && tName) {
        if (p.value !== entryCode) {
          out.problems.push("table " + tName + " holds a \"" + p.value + "\" entry");
        }
        entry = { type: p.value, codes: {}, all: [] };
        out.tables[tName].push(entry);
        continue;
      }
      if (entry) {
        if (entry.codes[p.code] === undefined) entry.codes[p.code] = p.value;
        entry.all.push(p);
      }
    }
    if (tDepth !== 0) out.problems.push("a TABLE was never closed by ENDTAB");

    /* ---- entities: 0/TYPE starts one, its codes run to the next 0 ---- */
    var es = out.sections.ENTITIES || [];
    var ent = null, openPoly = null;
    for (i = 0; i < es.length; i++) {
      p = es[i];
      if (p.code === 0) {
        if (p.value === "VERTEX") {
          if (!openPoly) out.problems.push("VERTEX outside a POLYLINE at line " + p.line);
          ent = { type: "VERTEX", codes: {}, all: [] };
          if (openPoly) openPoly.vertices.push(ent);
          continue;
        }
        if (p.value === "SEQEND") {
          if (!openPoly) out.problems.push("SEQEND with no open POLYLINE at line " + p.line);
          ent = { type: "SEQEND", codes: {}, all: [] };
          if (openPoly) openPoly.sequend = ent;
          openPoly = null;
          out.entities.push(ent);
          continue;
        }
        if (openPoly) { out.problems.push("POLYLINE not closed by SEQEND before " + p.value); openPoly = null; }
        ent = { type: p.value, codes: {}, all: [], vertices: [], sequend: null };
        out.entities.push(ent);
        if (p.value === "POLYLINE") openPoly = ent;
        continue;
      }
      if (!ent) { out.problems.push("entity data before any 0/TYPE at line " + p.line); continue; }
      if (ent.codes[p.code] === undefined) ent.codes[p.code] = p.value;
      ent.all.push(p);
    }
    if (openPoly) out.problems.push("the last POLYLINE was never closed by SEQEND");

    return out;
  }

  /* every coordinate the parser can see, in the file's own units */
  function coordsOf(parsed) {
    var pts = [];
    function take(e) {
      var xs = [10, 11, 12, 13], ys = [20, 21, 22, 23], k;
      for (k = 0; k < xs.length; k++) {
        if (e.codes[xs[k]] !== undefined && e.codes[ys[k]] !== undefined) {
          pts.push([Number(e.codes[xs[k]]), Number(e.codes[ys[k]])]);
        }
      }
    }
    parsed.entities.forEach(function (e) {
      if (e.type === "SEQEND") return;
      take(e);
      (e.vertices || []).forEach(take);
    });
    return pts;
  }

  function entsOfType(parsed, type) {
    return parsed.entities.filter(function (e) { return e.type === type; });
  }
  function onLayer(parsed, layer) {
    return parsed.entities.filter(function (e) { return e.type !== "SEQEND" && e.codes[8] === layer; });
  }
  function textsOn(parsed, layer) {
    return parsed.entities.filter(function (e) { return e.type === "TEXT" && e.codes[8] === layer; })
      .map(function (e) { return e.codes[1] === undefined ? "" : e.codes[1]; });
  }
  function allText(parsed) {
    return entsOfType(parsed, "TEXT").map(function (e) { return e.codes[1] || ""; }).join("\n");
  }
  function hv(parsed, name, code) {
    var h = parsed.header[name];
    return h ? h[code] : undefined;
  }

  /* THE assertion this whole file exists for.

     "The DXF must never contain NaN" cannot be tested by searching the
     text, because cad.js's own validation prose says, correctly and in
     as many words, "W2 carries a value that is not a finite number:
     x2 = NaN" — and that disclosure SHOULD travel with the geometry.
     What must never happen is a non-finite value in a slot where DXF
     requires a double. So the check is made on the parsed pairs: every
     numeric group code holds a real number, and the only pairs whose
     text mentions NaN or Infinity are prose (code 1 text, code 3
     description). */
  var NUMERIC_CODE = /^(1[0-9]|2[0-9]|3[0-7]|4[0-9]|5[0-8])$/;
  function nonNumeric(parsed) {
    var out = [];
    parsed.pairs.forEach(function (p) {
      if (!NUMERIC_CODE.test(String(p.code))) return;
      if (!/^-?(\d+\.?\d*|\.\d+)$/.test(p.value)) out.push(p);
    });
    return out;
  }
  function nanOutsideProse(parsed) {
    var out = [];
    parsed.pairs.forEach(function (p) {
      if (!/NaN|Infinity/.test(p.value)) return;
      if (p.code === 1 || p.code === 3) return;   /* text and description are prose */
      out.push(p);
    });
    return out;
  }

  /* ============================================================
     FIXTURES
     ============================================================ */

  var PLAN_IDS = (FM.weights && FM.weights.PLANS)
    ? FM.weights.PLANS.map(function (p) { return p.id; }) : [];

  /* The calculations have to be solved from the TAKEOFF'S OWN MARKS, the
     way project.js assembles a run, or the mark ids in the schedule are
     the shipped plan's and the mark ids on the drawing are the geometry's
     and nothing matches. That mismatch is a real failure mode of this
     export and it is asserted separately below; here we want the case
     where the drawing and the schedule describe the same house. */
  function ctxFor(planId) {
    var model = FM.cad.fromPlan(planId);
    var takeoff = null, calcs = null;
    try { takeoff = FM.takeoff.run(model); } catch (e) { takeoff = null; }
    try {
      if (takeoff && takeoff.marks && takeoff.marks.length) {
        calcs = FM.solver.solvePlan({
          id: "run", name: model.name, summary: "from the takeoff", lots: 1,
          marks: takeoff.marks, geometry: {}
        }, FM.weights.packById("tx-i35"));
      }
    } catch (e) { calcs = null; }
    return { model: model, takeoff: takeoff, calcs: calcs };
  }

  /* a hand-built model, so an assertion about counts is an assertion about
     a shape somebody can hold in their head */
  function tinyModel(over) {
    var m = {
      version: 1, name: "Tiny",
      levels: [{
        id: "L1", label: "First floor", topPlateFt: 9,
        walls: [
          { id: "W1", x1: 0, y1: 0, x2: 20, y2: 0, exterior: true, bearing: true, thicknessIn: 5.5 },
          { id: "W2", x1: 20, y1: 0, x2: 20, y2: 12, exterior: true, bearing: false, thicknessIn: 5.5 },
          { id: "W3", x1: 20, y1: 12, x2: 0, y2: 12, exterior: true, bearing: true, thicknessIn: 5.5 },
          { id: "W4", x1: 0, y1: 12, x2: 0, y2: 0, exterior: true, bearing: false, thicknessIn: 5.5 }
        ],
        openings: [
          { id: "O1", wallId: "W1", offsetFt: 4, widthFt: 6, headHeightFt: 6.83, kind: "window" }
        ],
        framing: [
          { id: "F1", polygon: [[0, 0], [20, 0], [20, 12], [0, 12]], kind: "floor",
            directionDeg: 90, spacingIn: 16, bearsOn: ["W1", "W3"] }
        ]
      }]
    };
    if (over) over(m);
    return m;
  }

  /* ============================================================
     1. THE PARSER ITSELF

     A test whose parser accepts anything proves nothing. It is
     shown rejecting the three malformations it exists to catch
     before it is trusted with the exporter's output.
     ============================================================ */

  suite("dxf · the test's own DXF reader rejects malformed input");
  (function () {
    var torn = parse("0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\n");
    truthy(torn.problems.length > 0, "an odd line count (a group code with no value) is a problem");

    var unclosed = parse("0\nSECTION\n2\nHEADER\n0\nEOF\n");
    truthy(unclosed.problems.join(" ").indexOf("SECTION") !== -1,
           "a SECTION that is never closed by ENDSEC is a problem");

    var noEof = parse("0\nSECTION\n2\nHEADER\n0\nENDSEC\n");
    truthy(noEof.problems.join(" ").indexOf("0/EOF") !== -1,
           "a file that does not end at 0/EOF is a problem");

    var junk = parse("SECTION\n0\n");
    eq(junk.ok, false, "a line where a group code belongs is rejected outright");

    var loosePoly = parse("0\nSECTION\n2\nENTITIES\n0\nPOLYLINE\n8\nX\n0\nVERTEX\n8\nX\n0\nENDSEC\n0\nEOF\n");
    truthy(loosePoly.problems.join(" ").indexOf("SEQEND") !== -1,
           "a POLYLINE with no SEQEND is a problem — R12's own terminator");

    var good = parse("0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1009\n0\nENDSEC\n0\nEOF\n");
    eq(good.problems.length, 0, "and a minimal well-formed file has no problems at all");
    eq(good.header.$ACADVER[1], "AC1009", "…and its header variable reads back");
  })();

  /* ============================================================
     2. STRUCTURE, TABLES AND REFERENTIAL INTEGRITY
     ============================================================ */

  var REF = ctxFor(PLAN_IDS[0] || "starter-1210");
  var refBuilt = dxf.build(REF.model, { takeoff: REF.takeoff, calcs: REF.calcs, date: "2026-01-02" });
  var refParsed = refBuilt.ok ? parse(refBuilt.dxf) : null;

  suite("dxf · file structure — R12 (AC1009) ASCII");
  (function () {
    truthy(refBuilt.ok, "the reference plan exports" + (refBuilt.ok ? "" : ": " + refBuilt.why));
    if (!refParsed) return;

    eq(refParsed.problems.length, 0, "the exported file has no structural problems" +
       (refParsed.problems.length ? " — " + refParsed.problems.slice(0, 3).join("; ") : ""));
    eq(refParsed.eof, true, "the file ends at 0/EOF, and EOF is the last pair in it");
    eq(hv(refParsed, "$ACADVER", 1), "AC1009",
       "$ACADVER is AC1009 — R12, the revision with no CLASSES, OBJECTS or BLOCK_RECORD to get wrong");

    ["HEADER", "TABLES", "BLOCKS", "ENTITIES"].forEach(function (s) {
      truthy(refParsed.sectionOrder.indexOf(s) !== -1, "the " + s + " section is present");
    });
    eq(refParsed.sectionOrder.join(","), "HEADER,TABLES,BLOCKS,ENTITIES",
       "and the four sections are in the order DXF specifies");

    /* R12 has no LWPOLYLINE and no MTEXT. A file claiming AC1009 that
       contains either is a malformed hybrid — a strict reader drops the
       entity, and the walls it held vanish without a message. */
    eq(entsOfType(refParsed, "LWPOLYLINE").length, 0,
       "no LWPOLYLINE anywhere — it is an R14 entity and this file says R12");
    eq(entsOfType(refParsed, "MTEXT").length, 0,
       "no MTEXT anywhere — it is an R13 entity and this file says R12");
    truthy(entsOfType(refParsed, "POLYLINE").length > 0,
           "closed regions are POLYLINE, which is what R12 actually defines");
    eq(entsOfType(refParsed, "POLYLINE").length, entsOfType(refParsed, "SEQEND").length,
       "every POLYLINE is terminated by exactly one SEQEND");
    refParsed.entities.forEach(function (e) {
      if (e.type !== "POLYLINE") return;
      if (e.codes[66] !== "1") bad("POLYLINE " + (e.codes[8] || "?") + " is missing the 66/1 vertices-follow flag");
    });
    ok_once("every POLYLINE carries the 66/1 vertices-follow flag R12 requires");

    /* every polyline vertex is a real vertex */
    var vCount = 0, badV = 0;
    refParsed.entities.forEach(function (e) {
      (e.vertices || []).forEach(function (v) {
        vCount++;
        if (v.codes[10] === undefined || v.codes[20] === undefined) badV++;
      });
    });
    eq(badV, 0, "all " + vCount + " VERTEX entities carry both 10 and 20");
  })();

  function ok_once(msg) { t.ok(msg); }

  suite("dxf · tables — nothing references a name that is not defined");
  (function () {
    if (!refParsed) return;
    var layers = {}, ltypes = {}, styles = {};
    (refParsed.tables.LAYER || []).forEach(function (e) { layers[e.codes[2]] = e; });
    (refParsed.tables.LTYPE || []).forEach(function (e) { ltypes[e.codes[2]] = e; });
    (refParsed.tables.STYLE || []).forEach(function (e) { styles[e.codes[2]] = e; });

    truthy(Object.keys(layers).length >= 15, "the LAYER table carries the whole scheme — " +
           Object.keys(layers).length + " layers");
    truthy(layers["0"], "layer 0 is defined, as every DXF requires");
    truthy(refParsed.tables.VPORT && refParsed.tables.VPORT.length === 1,
           "a *ACTIVE VPORT is defined — this is what makes a reader open zoomed to the drawing");
    eq((refParsed.tables.VPORT || [{}])[0].codes[2], "*ACTIVE", "…and it is named *ACTIVE");

    /* THE failure this catches: an entity naming a layer the tables do not
       define. AutoCAD silently reassigns it to layer 0, and a plan whose
       bearing walls are on layer 0 cannot be read structurally at all. */
    var missing = {};
    refParsed.entities.forEach(function (e) {
      var l = e.codes[8];
      if (l === undefined) { missing["(no layer at all on " + e.type + ")"] = true; return; }
      if (!layers[l]) missing[l] = true;
    });
    eq(Object.keys(missing).length, 0,
       "every entity names a layer that exists in the LAYER table" +
       (Object.keys(missing).length ? " — missing: " + Object.keys(missing).join(", ") : ""));

    var missLt = {};
    Object.keys(layers).forEach(function (n) {
      var lt = layers[n].codes[6];
      if (lt && lt !== "BYLAYER" && !ltypes[lt]) missLt[lt] = true;
    });
    eq(Object.keys(missLt).length, 0,
       "every layer names a linetype that exists in the LTYPE table" +
       (Object.keys(missLt).length ? " — missing: " + Object.keys(missLt).join(", ") : ""));

    var missSt = {};
    entsOfType(refParsed, "TEXT").forEach(function (e) {
      var s = e.codes[7];
      if (s && !styles[s]) missSt[s] = true;
    });
    eq(Object.keys(missSt).length, 0,
       "every TEXT names a style that exists in the STYLE table" +
       (Object.keys(missSt).length ? " — missing: " + Object.keys(missSt).join(", ") : ""));

    /* a TEXT with 72 non-zero uses the ALIGNMENT point, not the insertion
       point; a writer that omits 11/21 drops that text at the origin */
    var wrong = 0;
    entsOfType(refParsed, "TEXT").forEach(function (e) {
      if (e.codes[72] && e.codes[72] !== "0" && (e.codes[11] === undefined || e.codes[21] === undefined)) wrong++;
    });
    eq(wrong, 0, "every justified TEXT carries its 11/21 alignment point — without it the text lands at the origin");

    /* layer names R12 will actually accept */
    var badName = [];
    Object.keys(layers).forEach(function (n) {
      if (!/^[A-Z0-9$_\-]{1,31}$/.test(n)) badName.push(n);
    });
    eq(badName.length, 0, "every layer name is R12-legal — uppercase, <=31 chars, [A-Z0-9$_-]" +
       (badName.length ? " — bad: " + badName.join(", ") : ""));
  })();

  suite("dxf · the layer scheme separates what a recipient needs to switch off");
  (function () {
    if (!refParsed) return;
    var names = {};
    (refParsed.tables.LAYER || []).forEach(function (e) { names[e.codes[2]] = e; });

    ["S-WALL-BRNG-EXTR", "S-WALL-BRNG-INTR", "S-WALL-NBRG-EXTR", "S-WALL-NBRG-INTR",
     "S-WALL-CNTR", "S-OPNG", "S-FRAM-RGN", "S-FRAM-DIRN", "S-ANNO-MARK",
     "S-ANNO-DIMS", "S-ANNO-NOTE", "S-ANNO-TTLB", "S-ANNO-SEAL", "S-GRID"].forEach(function (n) {
      truthy(names[n], "layer " + n + " is defined");
    });

    /* the structural distinction is a LAYER, not a lineweight: a
       lineweight cannot be switched off and a misread one is a misread
       structure */
    var wallLayers = {};
    REF.model.levels[0].walls.forEach(function (w) {
      wallLayers[(w.bearing ? "BRNG" : "NBRG")] = true;
    });
    var brng = onLayer(refParsed, "S-WALL-BRNG-EXTR").length + onLayer(refParsed, "S-WALL-BRNG-INTR").length;
    var nbrg = onLayer(refParsed, "S-WALL-NBRG-EXTR").length + onLayer(refParsed, "S-WALL-NBRG-INTR").length;
    if (wallLayers.BRNG) truthy(brng > 0, "bearing walls landed on S-WALL-BRNG-*");
    if (wallLayers.NBRG) truthy(nbrg > 0, "non-bearing walls landed on S-WALL-NBRG-*");

    /* not one bearing wall on a non-bearing layer, checked wall by wall
       against the model rather than in aggregate */
    var built = dxf.build(tinyModel(), {});
    var p2 = parse(built.dxf);
    eq(onLayer(p2, "S-WALL-BRNG-EXTR").filter(function (e) { return e.type === "POLYLINE"; }).length, 2,
       "the two bearing walls of the tiny model are the only two on S-WALL-BRNG-EXTR");
    eq(onLayer(p2, "S-WALL-NBRG-EXTR").filter(function (e) { return e.type === "POLYLINE"; }).length, 2,
       "and the two non-bearing walls are the only two on S-WALL-NBRG-EXTR");

    /* S-GRID exists and is EMPTY on purpose: the model declares no
       structural grid and this exporter refuses to invent one */
    truthy(names["S-GRID"], "S-GRID is defined");
    eq(onLayer(refParsed, "S-GRID").length, 0,
       "S-GRID carries not one entity — this model declares no structural grid and none is invented");
    truthy(allText(refParsed).indexOf("S-GRID IS EMPTY ON PURPOSE") !== -1,
           "and the drawing SAYS the grid layer is empty because the model declares none, " +
           "rather than leaving the recipient to guess");

    /* the legend borrows each layer's colour rather than living on it: a
       swatch drawn on S-WALL-BRNG-EXTR is counted as a fifth bearing wall
       by anything reading quantities off this file */
    var legendSwatches = onLayer(refParsed, "S-ANNO-LEGN").filter(function (e) { return e.type === "LINE"; });
    truthy(legendSwatches.length >= 10, "the legend draws a swatch per row — " + legendSwatches.length);
    var withColor = legendSwatches.filter(function (e) { return e.codes[62] !== undefined; });
    eq(withColor.length, legendSwatches.length,
       "…each carrying an explicit colour (code 62) so it looks like the layer it describes " +
       "without being on it");
  })();

  /* ============================================================
     3. UNITS — the 12x failure

     The whole product is decimal feet. The file is inches. If
     that conversion is wrong the drawing opens at 12x or 1/12
     and every dimension a framer takes off it is wrong.
     ============================================================ */

  suite("dxf · units — inches, declared, and the same everywhere");
  (function () {
    var built = dxf.build(tinyModel(), {});
    var p = parse(built.dxf);

    eq(hv(p, "$INSUNITS", 70), "1", "$INSUNITS = 1 — one drawing unit is one INCH");
    eq(hv(p, "$MEASUREMENT", 70), "0", "$MEASUREMENT = 0 — imperial, so a reader picks the imperial linetype file");
    eq(hv(p, "$LUNITS", 70), "4", "$LUNITS = 4 — architectural feet-and-inches display");
    eq(hv(p, "$LUPREC", 70), "4", "$LUPREC = 4 — to 1/16 in");
    eq(hv(p, "$TILEMODE", 70), "1", "$TILEMODE = 1 — the file opens in model space, where the drawing is");

    /* the load-bearing arithmetic: W1 is 20 ft long in the model. Its
       centreline in the file must be 240 units long, not 20 and not 2880. */
    var centre = onLayer(p, "S-WALL-CNTR").filter(function (e) { return e.type === "LINE"; });
    eq(centre.length, 4, "four wall centrelines, one per wall");
    var lengths = centre.map(function (e) {
      var dx = Number(e.codes[11]) - Number(e.codes[10]);
      var dy = Number(e.codes[21]) - Number(e.codes[20]);
      return Math.sqrt(dx * dx + dy * dy);
    }).sort(function (a, b) { return a - b; });
    near(lengths[3], 240, 1e-6, "the 20 ft wall is 240 units long — 12 units to the foot, exactly");
    near(lengths[0], 144, 1e-6, "the 12 ft wall is 144 units long");

    /* wall FACES are offset by half the thickness in INCHES, so a 5.5 in
       wall's two faces are 5.5 units apart — the number that proves the
       thickness conversion is not also multiplied by 12 */
    var faces = onLayer(p, "S-WALL-BRNG-EXTR").filter(function (e) { return e.type === "POLYLINE"; });
    truthy(faces.length > 0, "the bearing walls have face polylines");
    var f0 = faces[0];
    var vy = f0.vertices.map(function (v) { return Number(v.codes[20]); });
    var spread = Math.max.apply(null, vy) - Math.min.apply(null, vy);
    near(spread, 5.5, 1e-6, "a 5.5 in wall's two faces are 5.5 units apart — the thickness is in inches too");

    /* extents are in the same units as the entities. If EXTMAX were in
       feet while the entities were in inches the drawing would open with
       a 1/12 window over a corner of itself. */
    var exMaxX = Number(hv(p, "$EXTMAX", 10));
    truthy(exMaxX >= 240, "$EXTMAX.x (" + exMaxX.toFixed(1) + ") is in the entities' own units, not the model's feet");

    /* and the feet variant, so the conversion is proved to be a single
       switch rather than a constant sprinkled through the file */
    var pf = parse(dxf.build(tinyModel(), { units: "ft" }).dxf);
    eq(hv(pf, "$INSUNITS", 70), "2", "asked for feet, $INSUNITS = 2");
    var cf = onLayer(pf, "S-WALL-CNTR").filter(function (e) { return e.type === "LINE"; })
      .map(function (e) {
        var dx = Number(e.codes[11]) - Number(e.codes[10]), dy = Number(e.codes[21]) - Number(e.codes[20]);
        return Math.sqrt(dx * dx + dy * dy);
      }).sort(function (a, b) { return b - a; });
    near(cf[0], 20, 1e-6, "…and the same 20 ft wall is 20 units long — one conversion, one place");
  })();

  /* ============================================================
     4. EXTENTS
     ============================================================ */

  suite("dxf · $EXTMIN/$EXTMAX bound every coordinate actually written");
  (function () {
    if (!refParsed) return;
    var pts = coordsOf(refParsed);
    truthy(pts.length > 50, "the file carries " + pts.length + " coordinate pairs to bound");
    var minX = null, minY = null, maxX = null, maxY = null;
    pts.forEach(function (p) {
      if (minX === null || p[0] < minX) minX = p[0];
      if (maxX === null || p[0] > maxX) maxX = p[0];
      if (minY === null || p[1] < minY) minY = p[1];
      if (maxY === null || p[1] > maxY) maxY = p[1];
    });
    var eMinX = Number(hv(refParsed, "$EXTMIN", 10)), eMinY = Number(hv(refParsed, "$EXTMIN", 20));
    var eMaxX = Number(hv(refParsed, "$EXTMAX", 10)), eMaxY = Number(hv(refParsed, "$EXTMAX", 20));

    truthy(eMinX <= minX + 1e-6 && eMinY <= minY + 1e-6,
           "$EXTMIN (" + eMinX.toFixed(1) + ", " + eMinY.toFixed(1) + ") is at or below every point drawn");
    truthy(eMaxX >= maxX - 1e-6 && eMaxY >= maxY - 1e-6,
           "$EXTMAX (" + eMaxX.toFixed(1) + ", " + eMaxY.toFixed(1) + ") is at or above every point drawn");
    truthy(eMaxX > eMinX && eMaxY > eMinY, "the extents are a real box, not a point");

    /* extents that cover only the geometry open the drawing with the
       title block and the notes off screen */
    var tb = onLayer(refParsed, "S-ANNO-TTLB").concat(onLayer(refParsed, "S-ANNO-SEAL"));
    truthy(tb.length > 0, "the title block and seal block are in the file");
    var tbMinY = null;
    tb.forEach(function (e) {
      if (e.codes[20] !== undefined) {
        var y = Number(e.codes[20]);
        if (tbMinY === null || y < tbMinY) tbMinY = y;
      }
      (e.vertices || []).forEach(function (v) {
        var y = Number(v.codes[20]);
        if (tbMinY === null || y < tbMinY) tbMinY = y;
      });
    });
    truthy(tbMinY !== null && eMinY <= tbMinY + 1e-6,
           "…and the extents reach below the title block, so it is on screen when the drawing opens");

    /* $LIMMIN/$LIMMAX are outside the extents, as limits should be */
    var lMinX = Number(hv(refParsed, "$LIMMIN", 10)), lMaxX = Number(hv(refParsed, "$LIMMAX", 10));
    var lMinY = Number(hv(refParsed, "$LIMMIN", 20)), lMaxY = Number(hv(refParsed, "$LIMMAX", 20));
    truthy(lMinX <= eMinX && lMinY <= eMinY && lMaxX >= eMaxX && lMaxY >= eMaxY,
           "$LIMMIN/$LIMMAX enclose the extents rather than cropping them");

    /* the *ACTIVE viewport is centred on the same box */
    var vp = (refParsed.tables.VPORT || [])[0];
    if (vp) {
      near(Number(vp.codes[12]), (eMinX + eMaxX) / 2, Math.abs(eMaxX - eMinX) * 0.02 + 1,
           "the *ACTIVE VPORT is centred on the extents in X");
      near(Number(vp.codes[22]), (eMinY + eMaxY) / 2, Math.abs(eMaxY - eMinY) * 0.02 + 1,
           "…and in Y, so the file opens looking at the drawing");
    }
  })();

  /* ============================================================
     5. COUNTS — the file holds the model, all of it
     ============================================================ */

  suite("dxf · entity counts tie back to the model, item by item");
  (function () {
    var m = tinyModel();
    var built = dxf.build(m, {});
    var p = parse(built.dxf);
    var lv = m.levels[0];

    eq(onLayer(p, "S-WALL-CNTR").filter(function (e) { return e.type === "LINE"; }).length,
       lv.walls.length, "one centreline per wall — " + lv.walls.length);

    var facePolys = 0;
    ["S-WALL-BRNG-EXTR", "S-WALL-BRNG-INTR", "S-WALL-NBRG-EXTR", "S-WALL-NBRG-INTR"].forEach(function (L) {
      facePolys += onLayer(p, L).filter(function (e) { return e.type === "POLYLINE"; }).length;
    });
    eq(facePolys, lv.walls.length, "one face polyline per wall that has a thickness — " + lv.walls.length);
    eq(onLayer(p, "S-OPNG").filter(function (e) { return e.type === "POLYLINE"; }).length,
       lv.openings.length, "one rough-opening polyline per opening — " + lv.openings.length);
    eq(onLayer(p, "S-FRAM-RGN").filter(function (e) { return e.type === "POLYLINE"; }).length,
       lv.framing.length, "one boundary polyline per framing region — " + lv.framing.length);

    /* a wall face polyline is a closed rectangle: 4 vertices, 70/1 */
    var anyFace = onLayer(p, "S-WALL-BRNG-EXTR").filter(function (e) { return e.type === "POLYLINE"; })[0];
    eq(anyFace.vertices.length, 4, "a wall's faces are a 4-vertex polyline");
    eq(anyFace.codes[70], "1", "…and it is flagged closed (70 bit 1)");

    /* the region polygon comes back point for point */
    var reg = onLayer(p, "S-FRAM-RGN").filter(function (e) { return e.type === "POLYLINE"; })[0];
    eq(reg.vertices.length, lv.framing[0].polygon.length,
       "the framing region has the same vertex count as the model polygon");
    var roundTripped = reg.vertices.map(function (v) {
      return [Number(v.codes[10]) / 12, Number(v.codes[20]) / 12];
    });
    var maxErr = 0;
    lv.framing[0].polygon.forEach(function (src, i) {
      maxErr = Math.max(maxErr, Math.abs(src[0] - roundTripped[i][0]), Math.abs(src[1] - roundTripped[i][1]));
    });
    near(maxErr, 0, 1e-6, "…and every vertex round-trips back to the model's own feet");

    /* an id per wall, and the ids are the model's */
    var ids = textsOn(p, "S-WALL-IDEN").sort().join(",");
    eq(ids, "W1,W2,W3,W4", "each wall is labelled with its own id");

    /* the region label carries kind, spacing and what it bears on */
    var fl = textsOn(p, "S-FRAM-IDEN").join(" | ");
    truthy(fl.indexOf("F1") !== -1 && fl.indexOf("FLOOR FRAMING") !== -1,
           "the framing region is labelled with its id and kind");
    truthy(fl.indexOf("16\" O.C.") !== -1, "…its spacing");
    truthy(fl.indexOf("BEARS ON W1, W3") !== -1, "…and the walls it bears on");

    /* the direction indicator exists, and it points where the model says */
    var dirLines = onLayer(p, "S-FRAM-DIRN").filter(function (e) { return e.type === "LINE"; });
    truthy(dirLines.length >= 5, "the span-direction indicator is drawn (shaft plus arrowheads)");
    var shaft = dirLines[0];
    var ang = Math.atan2(Number(shaft.codes[21]) - Number(shaft.codes[20]),
                         Number(shaft.codes[11]) - Number(shaft.codes[10])) * 180 / Math.PI;
    near(Math.abs(ang), 90, 0.5, "…and it runs at the region's declared 90 deg, not at a default");
  })();

  /* ============================================================
     6. MEMBER MARKS
     ============================================================ */

  suite("dxf · member marks — placed only where the takeoff located them");
  (function () {
    if (!refParsed || !REF.takeoff) return;

    var boxes = onLayer(refParsed, "S-ANNO-MARK").filter(function (e) { return e.type === "POLYLINE"; });
    var labels = textsOn(refParsed, "S-ANNO-MARK");
    eq(boxes.length, refBuilt.marks.placed.length,
       "one mark box per placed mark — " + refBuilt.marks.placed.length);
    eq(refBuilt.marks.placed.length + refBuilt.marks.unplaced.length, REF.takeoff.marks.length,
       "every takeoff mark is either placed or listed as unplaced — " + REF.takeoff.marks.length +
       ", none silently dropped");

    refBuilt.marks.placed.forEach(function (m) {
      truthy(labels.indexOf(m.id) !== -1, "mark " + m.id + "'s id is drawn on the plan");
    });

    /* the selected member, not just the mark id — a plan with marks and no
       members is a plan the framer still has to look something up for */
    var withMember = labels.filter(function (s) { return /\d+x\d+/.test(s); });
    truthy(REF.calcs ? withMember.length > 0 : true,
           "…and where the calculations carry that mark, the selected member is drawn beside it");

    /* a mark the calculations do not carry SAYS SO rather than reading blank */
    var noCalc = dxf.build(REF.model, { takeoff: REF.takeoff, date: "2026-01-02" });
    var pn = parse(noCalc.dxf);
    var lab2 = textsOn(pn, "S-ANNO-MARK");
    if (noCalc.drawn.marksPlaced > 0) {
      truthy(lab2.indexOf("NO CALCULATIONS SUPPLIED") !== -1,
             "exported with no calculations, every mark box reads NO CALCULATIONS SUPPLIED — not blank");
    }

    /* THE ANCHOR IS EXACT, only the tag moves.

       A header tag drawn on top of its opening hides the opening, so the
       box is nudged clear along the wall normal and a leader runs back.
       The leader's START must be the opening's own centre to the last
       decimal — if the nudge leaked into the anchor, the plan would show
       a header 8 inches off the hole it spans, and nothing would say so. */
    var anchored = dxf.build(tinyModel(), {
      takeoff: {
        marks: [{ id: "HDR-O1" }],
        derivations: [{ markId: "HDR-O1", field: "span", value: 6, from: "opening O1", fromIds: ["O1"] }],
        unresolved: []
      }
    });
    eq(anchored.drawn.marksPlaced, 1, "a mark whose derivation names opening O1 is placed");
    var pa = parse(anchored.dxf);
    var leaders = onLayer(pa, "S-ANNO-MARK").filter(function (e) { return e.type === "LINE"; });
    eq(leaders.length, 1, "…with one leader line back to the opening");
    /* O1 runs 4 ft to 10 ft along W1, which runs (0,0)->(20,0). Its centre
       is at 7 ft, 0 ft — 84, 0 in the file's inches. */
    near(Number(leaders[0].codes[10]), 84, 1e-6, "…whose start is exactly the opening's centre in x (84 in = 7 ft)");
    near(Number(leaders[0].codes[20]), 0, 1e-6, "…and exactly on the wall centreline in y");
    var boxV = onLayer(pa, "S-ANNO-MARK").filter(function (e) { return e.type === "POLYLINE"; })[0].vertices;
    var byMid = boxV.reduce(function (a, v) { return a + Number(v.codes[20]); }, 0) / boxV.length;
    truthy(Math.abs(byMid) > 5, "…and the tag itself sits clear of the wall rather than on top of it");

    /* the refusal that matters: a mark whose derivations name nothing is
       NOT drawn at a plausible point. It is named in the notes. */
    var m2 = tinyModel();
    var fakeTakeoff = {
      marks: [{ id: "GHOST-1" }],
      derivations: [{ markId: "GHOST-1", field: "span", value: 1, from: "a source this drawing has never heard of", fromIds: ["ZZ9"] }],
      unresolved: []
    };
    var g = dxf.build(m2, { takeoff: fakeTakeoff });
    eq(g.drawn.marksPlaced, 0, "a mark whose derivations name no wall, opening or region is not placed");
    eq(g.marks.unplaced.length, 1, "…it is carried on the unplaced list instead");
    var pg = parse(g.dxf);
    truthy(allText(pg).indexOf("GHOST-1") !== -1,
           "…and it is named in the drawing's own notes, so the recipient sees the mark is missing");
    eq(textsOn(pg, "S-ANNO-MARK").length, 0, "…with nothing at all on the mark layer");
  })();

  /* ============================================================
     7. THE STATEMENT THAT TRAVELS WITH THE GEOMETRY
     ============================================================ */

  suite("dxf · every file says it is not sealed engineering, and the seal block is empty");
  (function () {
    PLAN_IDS.forEach(function (id) {
      var c = ctxFor(id);
      var b = dxf.build(c.model, { takeoff: c.takeoff, calcs: c.calcs, date: "2026-01-02" });
      if (!b.ok) { bad(id + " did not export: " + b.why); return; }
      var p = parse(b.dxf);
      var text = allText(p);
      truthy(text.indexOf("PREPARED FOR PE REVIEW - NOT SEALED ENGINEERING") !== -1,
             id + ": the drawing carries PREPARED FOR PE REVIEW - NOT SEALED ENGINEERING");
      truthy(/TO BE SEALED BY _+, PE/.test(text),
             id + ": …and a \"TO BE SEALED BY ____, PE\" line left blank");
      truthy(textsOn(p, "S-ANNO-SEAL").join(" ").indexOf("INTENTIONALLY BLANK") !== -1,
             id + ": …and the seal block itself is drawn empty and labelled so");

      /* nothing anywhere claims the software did the sealing */
      var claim = /\b(SEALED BY FIRMARK|APPROVED BY FIRMARK|THIS DRAWING IS SEALED|STAMPED BY)\b/i.test(text);
      eq(claim, false, id + ": …and nothing in the file claims the software sealed, stamped or approved anything");
    });
  })();

  /* ============================================================
     8. ALL FIVE PLANS, END TO END
     ============================================================ */

  suite("dxf · all five shipped plans: model -> DXF -> parse -> back to the model");
  (function () {
    eq(PLAN_IDS.length, 5, "there are five shipped plans to export");
    PLAN_IDS.forEach(function (id) {
      var c = ctxFor(id);
      var b;
      try { b = dxf.build(c.model, { takeoff: c.takeoff, calcs: c.calcs, date: "2026-01-02" }); }
      catch (e) { bad(id + " threw while exporting", e.message); return; }
      if (!b.ok) { bad(id + " refused to export: " + b.why); return; }

      var p = parse(b.dxf);
      eq(p.problems.length, 0, id + ": parses back with no structural problems" +
         (p.problems.length ? " — " + p.problems.slice(0, 2).join("; ") : ""));

      /* counts, level by level, straight off the model */
      var walls = 0, thickWalls = 0, opens = 0, thickOpens = 0, regions = 0;
      c.model.levels.forEach(function (lv) {
        (lv.walls || []).forEach(function (w) {
          var ok = isFinite(w.x1) && isFinite(w.y1) && isFinite(w.x2) && isFinite(w.y2) &&
                   (w.x1 !== w.x2 || w.y1 !== w.y2);
          if (!ok) return;
          walls++;
          if (isFinite(w.thicknessIn) && w.thicknessIn > 0) thickWalls++;
        });
        (lv.openings || []).forEach(function (o) {
          var host = null;
          (lv.walls || []).forEach(function (w) { if (w.id === o.wallId) host = w; });
          if (!host || !isFinite(o.offsetFt) || !isFinite(o.widthFt) || o.widthFt <= 0) return;
          if (!(isFinite(host.x1) && isFinite(host.x2) && (host.x1 !== host.x2 || host.y1 !== host.y2))) return;
          opens++;
          if (isFinite(host.thicknessIn) && host.thicknessIn > 0) thickOpens++;
        });
        (lv.framing || []).forEach(function (f) {
          if ((f.polygon || []).length >= 3) regions++;
        });
      });

      eq(b.drawn.wallCentres, walls, id + ": " + walls + " walls, " + walls + " centrelines");
      eq(b.drawn.wallFaces, thickWalls, id + ": " + thickWalls + " walls with a thickness, " +
         thickWalls + " face polylines");
      eq(b.drawn.openings + b.drawn.openingCentrelineOnly, opens,
         id + ": " + opens + " locatable openings, all " + opens + " drawn");
      eq(b.drawn.regions, regions, id + ": " + regions + " framing regions, all drawn");

      /* and the same counts survive the round trip through the parser */
      var faceP = 0;
      ["S-WALL-BRNG-EXTR", "S-WALL-BRNG-INTR", "S-WALL-NBRG-EXTR", "S-WALL-NBRG-INTR"].forEach(function (L) {
        faceP += onLayer(p, L).filter(function (e) { return e.type === "POLYLINE"; }).length;
      });
      eq(faceP, thickWalls, id + ": …and the parsed file holds all " + thickWalls + " of them");
      eq(onLayer(p, "S-FRAM-RGN").filter(function (e) { return e.type === "POLYLINE"; }).length,
         regions, id + ": …and all " + regions + " framing regions");

      /* extents bound the file */
      var pts = coordsOf(p), mnX = null, mnY = null, mxX = null, mxY = null;
      pts.forEach(function (q) {
        if (mnX === null || q[0] < mnX) mnX = q[0];
        if (mxX === null || q[0] > mxX) mxX = q[0];
        if (mnY === null || q[1] < mnY) mnY = q[1];
        if (mxY === null || q[1] > mxY) mxY = q[1];
      });
      truthy(Number(hv(p, "$EXTMIN", 10)) <= mnX + 1e-6 && Number(hv(p, "$EXTMAX", 10)) >= mxX - 1e-6 &&
             Number(hv(p, "$EXTMIN", 20)) <= mnY + 1e-6 && Number(hv(p, "$EXTMAX", 20)) >= mxY - 1e-6,
             id + ": $EXTMIN/$EXTMAX bound all " + pts.length + " coordinates in the file");

      /* the model's own validation travels with the geometry */
      var vrows = FM.cad.validate(c.model) || [];
      if (vrows.length) {
        truthy(allText(p).indexOf("MODEL VALIDATION AT EXPORT") !== -1,
               id + ": the model's " + vrows.length + " validation finding(s) travel on the drawing");
      }

      /* pure ASCII, always — R12 declares no encoding, so a byte above
         0x7F means whatever the reader's codepage says it means */
      eq(/[^\x00-\x7F]/.test(b.dxf), false, id + ": the file is pure ASCII end to end");
      eq(nonNumeric(p).length, 0,
         id + ": every numeric group code holds a real number" +
         (nonNumeric(p).length ? " — first bad: code " + nonNumeric(p)[0].code +
          " = \"" + nonNumeric(p)[0].value + "\"" : ""));
      eq(nanOutsideProse(p).length, 0,
         id + ": NaN and Infinity appear nowhere a DXF reader expects a double");
    });
  })();

  /* ============================================================
     9. DEGENERATE CASES

     Each one is a file that has to have a specific, defensible
     behaviour. "It didn't crash" is not one of them.
     ============================================================ */

  suite("dxf · degenerate models — refuse, or draw and say what is missing");
  (function () {

    /* ---- no framing regions ---- */
    var noFram = dxf.build(tinyModel(function (m) { m.levels[0].framing = []; }), {});
    eq(noFram.ok, true, "no framing regions: still exports — walls and openings are a drawing");
    eq(noFram.drawn.regions, 0, "…with no region entities");
    truthy(parse(noFram.dxf).problems.length === 0, "…and it parses clean");

    /* ---- no openings ---- */
    var noOpen = dxf.build(tinyModel(function (m) { m.levels[0].openings = []; }), {});
    eq(noOpen.ok, true, "no openings: still exports");
    eq(noOpen.drawn.openings, 0, "…with nothing on the opening layer");

    /* ---- a single wall ---- */
    var one = dxf.build(tinyModel(function (m) {
      m.levels[0].walls = [m.levels[0].walls[0]];
      m.levels[0].openings = []; m.levels[0].framing = [];
    }), {});
    eq(one.ok, true, "a single wall: exports");
    eq(one.drawn.wallFaces, 1, "…as one face polyline");
    eq(one.drawn.wallCentres, 1, "…and one centreline");
    var op = parse(one.dxf);
    eq(op.problems.length, 0, "…and the file is structurally sound");
    truthy(Number(hv(op, "$EXTMAX", 10)) > Number(hv(op, "$EXTMIN", 10)),
           "…and its extents are still a real box, not a degenerate point");

    /* ---- zero walls, nothing at all ---- */
    var none = dxf.build({ version: 1, name: "Empty", levels: [{ id: "L1", label: "L1", walls: [], openings: [], framing: [] }] }, {});
    eq(none.ok, false, "a model with no walls and no regions REFUSES — there is no drawing to export");
    truthy(none.why.indexOf("no drawable geometry") !== -1, "…and says why: " + none.why);
    eq(none.dxf, null, "…and returns no file at all rather than a file of nothing");
    var threw = false, msg = "";
    try { dxf.fromModel({ version: 1, name: "Empty", levels: [] }, {}); }
    catch (e) { threw = true; msg = e.message; }
    eq(threw, true, "fromModel THROWS rather than returning a drawing that opens blank");
    truthy(/refused/i.test(msg), "…with a message that names the refusal: " + msg.slice(0, 70));

    /* ---- NaN coordinates: the file must never contain them ---- */
    var nanModel = tinyModel(function (m) {
      m.levels[0].walls[1].x2 = NaN;
      m.levels[0].walls[2].y1 = Infinity;
    });
    var nanB = dxf.build(nanModel, {});
    eq(nanB.ok, true, "NaN and Infinity coordinates: the sound walls still export");
    eq(nanB.drawn.wallCentres, 2, "…and the two broken walls are NOT drawn");
    var np = parse(nanB.dxf);
    eq(np.problems.length, 0, "…which still parses clean");
    eq(nonNumeric(np).length, 0,
       "…and every numeric group code in it holds a real number — no NaN, no Infinity, no empty slot");
    eq(nanOutsideProse(np).length, 0,
       "…and the strings NaN and Infinity appear ONLY inside TEXT, never where a double belongs");
    truthy(/NaN/.test(nanB.dxf),
       "…while the word NaN DOES appear in the notes, because cad.js names the broken coordinate " +
       "and that disclosure has to travel with the geometry");
    truthy(nanB.refusals.length >= 2, "…and both broken walls are named in the refusals");
    truthy(allText(np).indexOf("W2") !== -1 && allText(np).indexOf("W3") !== -1,
           "…by name, on the drawing itself, under NOT DRAWN, AND WHY");

    /* every coordinate NaN — nothing is drawable, so refuse */
    var allNan = dxf.build(tinyModel(function (m) {
      m.levels[0].walls.forEach(function (w) { w.x1 = NaN; w.y1 = NaN; w.x2 = NaN; w.y2 = NaN; });
      m.levels[0].framing = [];
    }), {});
    eq(allNan.ok, false, "every coordinate NaN: refuses outright");

    /* ---- a wall with no thickness: centreline, no faces, and it says so ---- */
    var noThick = dxf.build(tinyModel(function (m) {
      delete m.levels[0].walls[0].thicknessIn;
    }), {});
    eq(noThick.ok, true, "a wall with no thickness still exports");
    eq(noThick.drawn.wallCentres, 4, "…with its centreline drawn");
    eq(noThick.drawn.wallFaces, 3, "…and NO faces — this exporter does not assume a stud size");
    eq(noThick.drawn.openingCentrelineOnly, 1,
       "…and the opening in it is drawn on the centreline rather than across an assumed thickness");
    var ntp = parse(noThick.dxf);
    truthy(allText(ntp).indexOf("FACES ARE NOT DRAWN") !== -1,
           "…and the drawing states that the faces are missing and why");

    /* ---- a zero-length wall: end coincident with start ---- */
    var zero = dxf.build(tinyModel(function (m) {
      m.levels[0].walls[3].x2 = m.levels[0].walls[3].x1;
      m.levels[0].walls[3].y2 = m.levels[0].walls[3].y1;
    }), {});
    eq(zero.drawn.wallCentres, 3, "a zero-length wall is not drawn — it has no direction to offset faces along");
    truthy(zero.refusals.filter(function (r) { return r.what.indexOf("W4") !== -1; }).length === 1,
           "…and it is named in the refusals");

    /* ---- a 500-point polygon ---- */
    var big = tinyModel(function (m) {
      var poly = [], i;
      for (i = 0; i < 500; i++) {
        var a = i / 500 * Math.PI * 2;
        poly.push([40 + 18 * Math.cos(a), 40 + 18 * Math.sin(a)]);
      }
      m.levels[0].framing = [{ id: "BIG", polygon: poly, kind: "roof", directionDeg: 0,
                               spacingIn: 24, bearsOn: ["W1"] }];
    });
    var bigB = dxf.build(big, {});
    eq(bigB.ok, true, "a 500-point framing region exports");
    var bp = parse(bigB.dxf);
    eq(bp.problems.length, 0, "…and parses clean — POLYLINE/VERTEX has no vertex limit");
    var bigPoly = onLayer(bp, "S-FRAM-RGN").filter(function (e) { return e.type === "POLYLINE"; })[0];
    eq(bigPoly.vertices.length, 500, "…with all 500 vertices present, not truncated");
    eq(entsOfType(bp, "SEQEND").length, entsOfType(bp, "POLYLINE").length,
       "…and still one SEQEND per POLYLINE");

    /* ---- a 2-point "polygon" is not a region ---- */
    var twoPt = dxf.build(tinyModel(function (m) {
      m.levels[0].framing = [{ id: "SLIVER", polygon: [[0, 0], [1, 1]], kind: "floor",
                               directionDeg: 0, spacingIn: 16, bearsOn: [] }];
    }), {});
    eq(twoPt.drawn.regions, 0, "a 2-point framing polygon is not drawn as a region");
    truthy(twoPt.refusals.filter(function (r) { return r.what.indexOf("SLIVER") !== -1; }).length > 0,
           "…and it is named");

    /* ---- a framing region with no declared direction ---- */
    var noDir = dxf.build(tinyModel(function (m) {
      delete m.levels[0].framing[0].directionDeg;
      delete m.levels[0].framing[0].spacingIn;
    }), {});
    eq(noDir.drawn.regions, 1, "a region with no direction is still drawn as a region");
    eq(noDir.drawn.directionArrows, 0, "…with NO direction arrow, because nothing determines one");
    truthy(textsOn(parse(noDir.dxf), "S-FRAM-IDEN").join(" ").indexOf("SPACING NOT DECLARED") !== -1,
           "…and its label reads SPACING NOT DECLARED rather than a made-up 16 in");

    /* ---- an opening whose host wall is not in the model ---- */
    var orphan = dxf.build(tinyModel(function (m) {
      m.levels[0].openings[0].wallId = "W99";
    }), {});
    eq(orphan.drawn.openings, 0, "an opening naming a wall that does not exist is not drawn");
    truthy(orphan.refusals.filter(function (r) { return r.what.indexOf("O1") !== -1; }).length > 0,
           "…and it is named in the refusals rather than dropped");

    /* ---- an opening that runs off the end of its wall ---- */
    var over = dxf.build(tinyModel(function (m) {
      m.levels[0].openings[0].offsetFt = 18;      /* 18 + 6 > the 20 ft wall */
    }), {});
    eq(over.drawn.openings, 1, "an opening running past the end of its wall is drawn WHERE THE MODEL PUTS IT");
    truthy(over.refusals.filter(function (r) { return /off the end/.test(r.why); }).length > 0,
           "…and flagged, not silently clipped to fit");

    /* ---- a null entry in the arrays ---- */
    var nulls = dxf.build(tinyModel(function (m) {
      m.levels[0].walls.push(null);
      m.levels[0].openings.push(null);
      m.levels[0].framing.push(null);
    }), {});
    eq(nulls.ok, true, "null entries in the arrays do not stop the export");
    truthy(nulls.refusals.length >= 3, "…and each is named");

    /* ---- unicode in a note ---- */
    var uni = dxf.build(tinyModel(function (m) {
      /* the model name reaches the title block, the level label reaches
         the plan title, and the unresolved list reaches the notes — three
         different routes for a high byte to escape */
      m.name = "Maison Étoilée · 20′ × 12′ — 24° pitch · 中文";
      m.levels[0].label = "Rez-de-chaussée ±0";
      m.unresolved = [{ what: "L'ouverture O9 — 幅 undetermined", why: "非決定", need: "Déclarer widthFt" }];
    }), { projectName: "Chantier «Étoile» — 東京" });
    eq(uni.ok, true, "unicode in the model exports");
    eq(/[^\x00-\x7F]/.test(uni.dxf), false,
       "…and the DXF is pure ASCII — R12 declares no encoding, so a high byte means whatever the reader guesses");
    var up = parse(uni.dxf);
    eq(up.problems.length, 0, "…and it parses clean");
    var ut = allText(up);
    truthy(ut.indexOf("Maison") !== -1, "…the Latin text survives");
    truthy(ut.indexOf("Etoilee") !== -1 || ut.indexOf("\\U+00C9") !== -1,
           "…accented letters are transliterated or escaped as \\U+XXXX, never emitted raw");
    truthy(ut.indexOf("\\U+4E2D") !== -1, "…and CJK becomes the \\U+XXXX escape AutoCAD reads back");
    eq(dxf.encodeText("24° ±3 · a—b ×"), "24%%d %%p3 - a--b x",
       "encodeText: degree and plus/minus become the DXF control codes, typography becomes ASCII");
    eq(dxf.encodeText("line one\nline two"), "line one line two",
       "…and a newline is removed, because a newline inside a value tears the group-code pairing");

    /* ---- a note long enough to matter ---- */
    var longNote = "";
    for (var i = 0; i < 60; i++) longNote += "verylongtoken" + i + " ";
    var ln = dxf.build(tinyModel(function (m) { m.levels[0].walls[0].note = longNote; }), {});
    var lp = parse(ln.dxf);
    eq(lp.problems.length, 0, "a very long note does not break the file");
    var tooLong = entsOfType(lp, "TEXT").filter(function (e) { return (e.codes[1] || "").length > 255; });
    eq(tooLong.length, 0, "…and no single TEXT value exceeds the 255 characters R12 allows");

    /* ---- no takeoff at all ---- */
    var bare = dxf.build(tinyModel(), {});
    eq(bare.ok, true, "with no takeoff the geometry still exports");
    eq(bare.drawn.marksPlaced, 0, "…with no marks");
    truthy(allText(parse(bare.dxf)).indexOf("NO MEMBER MARKS") !== -1,
           "…and the drawing says it carries no member marks rather than looking finished");

    /* ---- a coordinate too large to write ----
       Past 1e21 units, toFixed switches to exponent form and several DXF
       readers parse "1e+21" as 1 — a wall silently 21 orders of magnitude
       out of place. It is refused by name instead. */
    var huge = dxf.build(tinyModel(function (m) { m.levels[0].walls[1].x2 = 1e18; }), {});
    eq(huge.drawn.wallCentres, 3, "a coordinate beyond what fixed notation can hold: that wall is not drawn");
    truthy(huge.refusals.filter(function (r) { return r.what.indexOf("W2") !== -1; }).length > 0,
           "…and it is refused by name, not by an anonymous throw at write time");
    eq(/e\+|E\+/.test(huge.dxf), false, "…and no exponent notation reaches the file");

    /* a button in a browser must not be able to throw. Every deliberate
       refusal comes back as ok:false with a stated reason. */
    var threwFromBuild = false;
    try { dxf.build({ version: 1, name: "x", levels: [{ id: "L1", walls: [], openings: [], framing: [] }] }, {}); }
    catch (e) { threwFromBuild = true; }
    eq(threwFromBuild, false, "build() returns a refusal rather than throwing — the UI can render it");

    /* ---- a garbage model ---- */
    [null, undefined, 42, "a model", {}, { levels: "no" }].forEach(function (junk) {
      var r = dxf.build(junk, {});
      eq(r.ok, false, "build(" + JSON.stringify(junk) + ") refuses");
      truthy(r.why.length > 0, "…with a stated reason");
    });
  })();

  /* ============================================================
     10. THE FORMATTER AND THE FILENAME
     ============================================================ */

  suite("dxf · the number formatter is the refusal point, and it holds");
  (function () {
    eq(dxf.fmt(0), "0.0", "0 formats as 0.0 — a DXF real always carries its decimal point");
    eq(dxf.fmt(12), "12.0", "an integer keeps its decimal point");
    eq(dxf.fmt(-0), "0.0", "negative zero is written as zero");
    eq(dxf.fmt(1.5), "1.5", "a decimal keeps its value");
    eq(dxf.fmt(0.0000001).indexOf("e"), -1, "a tiny number never comes out in exponent notation");
    eq(dxf.fmt(1e15), "1000000000000000.0", "a very large coordinate is still written in full");
    /* 1e21 is where toFixed switches to exponent form, and several DXF
       readers parse "1e+21" as 1. A coordinate that size is not a
       building, so it is refused rather than silently misread. */
    var hugeThrew = false;
    try { dxf.fmt(1e21, "a test"); } catch (e) { hugeThrew = e.dxfRefusal === true; }
    eq(hugeThrew, true, "…and one too large to write in fixed notation is REFUSED, not written as 1e+21");
    [NaN, Infinity, -Infinity, undefined, null, "12", {}].forEach(function (v) {
      var threw = false;
      try { dxf.fmt(v, "a test"); } catch (e) { threw = e.dxfRefusal === true; }
      eq(threw, true, "fmt(" + String(v) + ") throws a DxfRefusal rather than writing it");
    });

    eq(dxf.ftIn(13.5), "13'-6\"", "ftIn: 13.5 ft is 13'-6\"");
    eq(dxf.ftIn(0), "0'-0\"", "ftIn: 0");
    eq(dxf.ftIn(1.0104166), "1'-0 1/8\"", "ftIn: rounds to the sixteenth and reduces the fraction");
    eq(dxf.ftIn(NaN), null, "ftIn(NaN) is null — the caller declines to dimension rather than printing NaN'-NaN\"");
    eq(dxf.ftIn("nope"), null, "ftIn of a non-number is null");

    eq(dxf.cleanName("s-wall brng"), "S-WALL-BRNG", "cleanName uppercases and replaces what R12 rejects");
    eq(dxf.cleanName("").length > 0, true, "…and never returns an empty name");
    truthy(dxf.cleanName(new Array(60).join("A")).length <= 31, "…and never exceeds 31 characters");
  })();

  suite("dxf · the filename a browser download will carry");
  (function () {
    var m = FM.cad.fromPlan(PLAN_IDS[0] || "starter-1210");
    var f = dxf.filename(m, { date: "2026-08-13" });
    truthy(/^firmark-framing-[a-z0-9-]+-2026-08-13\.dxf$/.test(f), "filename is " + f);
    truthy(f.indexOf(m.source.planId) !== -1, "…and it carries the plan id, so two exports do not collide");
    var b = dxf.build(m, { date: "2026-08-13" });
    eq(b.filename, f, "…and build() returns the same name, so the caller need not compose one");
  })();

  /* ============================================================
     11. STABILITY

     Two exports of the same model must be byte-identical, or the
     approval fingerprint downstream moves for no reason.
     ============================================================ */

  suite("dxf · the same model exports byte-identical every time");
  (function () {
    var m = FM.cad.fromPlan(PLAN_IDS[0] || "starter-1210");
    var a = dxf.build(m, { date: "2026-01-02" });
    var b = dxf.build(m, { date: "2026-01-02" });
    eq(a.dxf === b.dxf, true, "two exports of one model produce the same bytes");
    eq(a.dxf.length, b.dxf.length, "…and the same length (" + a.dxf.length + " bytes)");
    truthy(a.dxf.indexOf("\r\n") !== -1, "…and line endings are CRLF, which is what DXF has always used");

    /* the contracted entry point is the same file, so a caller can use
       either and the button in core.js is not exercising a second path */
    var direct = dxf.fromModel(m, { date: "2026-01-02" });
    eq(direct, a.dxf, "fromModel() returns exactly what build().dxf holds — one code path, two doors");
    eq(typeof direct, "string", "…and it is a string, which is what the contract says");
    eq(direct.slice(0, 2), "0\r", "…starting at group code 0");
    truthy(/0\r\nEOF\r\n$/.test(direct), "…and ending at 0/EOF");
  })();
};

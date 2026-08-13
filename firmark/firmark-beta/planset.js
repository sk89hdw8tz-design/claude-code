/* ============================================================
   planset.js — the package a licensed engineer reviews.

   THE ONE RULE
   ------------
   This software never seals anything. It assembles a set of sheets
   that a licensed Professional Engineer reads, checks, signs and
   seals under their own licence and their own liability. The seal
   block on S0.0 is EMPTY and carries an explicit "to be sealed by
   ______, PE, licence no. ______, State of ______" line. That
   sentence is on the cover, in the general notes, and in the footer
   of every single sheet — not as boilerplate, but because it is the
   thing that makes this product legitimate rather than a machine
   quietly issuing engineering.

   Nothing in this file — no heading, no button label, no exported
   filename — may say a design here is finished, approved or sealed.
   Where the upstream data carries that wording in its own prose
   (weights.js names an elevation "as stamped"; export.js's provenance
   block says "before anything is stamped"), this file does NOT
   reproduce it verbatim, because a reviewer skimming a cover sheet
   should never meet the word at all. See the report notes.

   WHAT THIS FILE ASSUMES: NOTHING
   -------------------------------
   `build(ctx)` takes {model, takeoff, planResult, bom, juris, pipeline}
   and every one of them is optional, because they come from modules
   that are being written in parallel and any of them may be absent at
   any moment. The package always builds. A sheet whose input is
   missing SAYS WHICH MODULE DID NOT SUPPLY IT and prints nothing that
   could be mistaken for the real thing. That is non-negotiable #3 —
   a thing that could not be computed says so by name — applied to a
   deliverable instead of to a number.

   The sheet that carries the weight is S5.0. It collects every
   unresolved, escalated, excluded and must-verify item from every
   stage, and it MAY NEVER BE EMPTY: the standing items print on every
   package, always, because a set claiming zero open items is claiming
   a completeness this system cannot have.
   ============================================================ */

(function () {
  "use strict";

  var W = 78;                       /* fixed-width sheet body, as export.js */

  /* ---------------- text primitives (house style, export.js) ---------------- */

  function rule(ch) { return new Array(W + 1).join(ch || "="); }
  function pad(s, n) { s = String(s); while (s.length < n) s += " "; return s; }
  function lpad(s, n) { s = String(s); while (s.length < n) s = " " + s; return s; }
  function isArr(v) { return Object.prototype.toString.call(v) === "[object Array]"; }
  function own(o, k) { return !!o && Object.prototype.hasOwnProperty.call(o, k); }

  function str(v, dflt) {
    return (v === null || v === undefined || v === "") ? (dflt === undefined ? "" : dflt) : String(v);
  }

  /* Everything that arrives from a module this file does not own goes through
     safe(). A package that prints "undefined", "NaN" or "[object Object]" has
     stopped being a document and become a stack trace, and a plan reviewer
     cannot tell which of the two they are holding. */
  function safe(v, dflt) {
    var d = dflt === undefined ? "—" : dflt;
    if (v === null || v === undefined || v === "") return d;
    if (typeof v === "number") return isFinite(v) ? String(v) : d;
    if (typeof v === "boolean") return v ? "yes" : "no";
    if (typeof v === "function") return d;
    if (typeof v === "object") return d;
    var s = String(v);
    return s === "undefined" || s === "NaN" || s === "[object Object]" ? d : s;
  }

  function n2(v, d) {
    if (v === null || v === undefined || v === "" || !isFinite(Number(v))) return "—";
    return Number(v).toFixed(d === undefined ? 2 : d);
  }
  function comma(v) {
    if (v === null || v === undefined || v === "" || !isFinite(Number(v))) return "—";
    return String(Math.round(Number(v))).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }
  /* money keeps its cents: a bill of materials rounded to the dollar stops
     reconciling against the quote it will be checked against */
  function usd(v) {
    if (!isFinite(Number(v))) return "—";
    var n = Number(v), sign = n < 0 ? "-" : "";
    n = Math.abs(n);
    var whole = Math.floor(n);
    var cents = Math.round((n - whole) * 100);
    if (cents === 100) { whole += 1; cents = 0; }
    return sign + "$" + String(whole).replace(/\B(?=(\d{3})+(?!\d))/g, ",") +
           "." + (cents < 10 ? "0" : "") + cents;
  }

  /* wrap() collapses runs of whitespace, exactly as export.js's does, so a
     label with column padding in it cannot be passed through — pad outside. */
  function wrap(text, width, indent) {
    var words = String(text).split(/\s+/), lines = [], line = "";
    width = width || (W - 2);
    for (var i = 0; i < words.length; i++) {
      if (line && (line + " " + words[i]).length > width) { lines.push(line); line = ""; }
      line = line ? line + " " + words[i] : words[i];
    }
    if (line) lines.push(line);
    if (!lines.length) lines.push("");
    return lines.map(function (l, i) { return (i && indent ? indent : "") + l; });
  }

  /* the engine writes its check lines with markup for the sheet view */
  function plain(s) { return String(s).replace(/<[^>]+>/g, ""); }

  /* A labelled field with a hanging indent under the TEXT, not under the
     label. export.js learned this the hard way: wrap() normalises runs of
     whitespace, so a label padded inside the wrapped string comes back out
     one column narrower and every continuation line hangs off a column that
     is no longer there. Wrap the value, then lay the label alongside it. */
  function fielder(emit, indent, labelWidth) {
    var lead = new Array((indent === undefined ? 2 : indent) + 1).join(" ");
    return function (label, value) {
      var head = lead + pad(label, labelWidth || 6) + ": ";
      var body = new Array(head.length + 1).join(" ");
      var lines = wrap(value === undefined || value === null || value === "" ? "—" : String(value),
                       W - head.length);
      emit(head + lines[0]);
      lines.slice(1).forEach(function (x) { emit(body + x); });
    };
  }

  /* ---------------- the sentence this product exists to keep ---------------- */

  var NOT_SEALED =
    "This package is PREPARED FOR PE REVIEW. It is not sealed engineering. No " +
    "part of it has been checked, signed or sealed by a licensed engineer, and " +
    "this software does not and cannot do any of those things. A licensed " +
    "Professional Engineer must read the inputs, the assumptions and the results " +
    "and take professional responsibility for them under their own licence.";

  var SEAL_LINES = [
    "To be sealed by ______________________________, PE,",
    "licence no. ____________________, State of ____________.",
    "Date: ______________"
  ];

  var FOOTER =
    "PREPARED FOR PE REVIEW — NOT SEALED ENGINEERING. No seal is applied by this " +
    "software. The seal block on S0.0 is empty and is to be completed by the " +
    "licensed engineer who reviews this package and takes responsibility for it.";

  /* ---------------- provenance vocabulary ---------------- */

  var CLS_TEXT = {
    code:    "code — from an adopted code or standard, cited",
    site:    "site — a property of this site, must be confirmed for the site",
    market:  "market — a regional takeoff or price, NO code standing",
    derived: "derived — computed here from the inputs above",
    user:    "user — a firm policy or a typed input, not a code requirement"
  };
  function clsOf(v) {
    var s = str(v);
    return own(CLS_TEXT, s) ? s : "not stated";
  }

  /* ============================================================
     WHAT IS ACTUALLY HERE

     Every optional member of ctx is probed once, and what is absent is
     named — by module, by the sheet it damages, and by what it means
     for a reader. The sheets consult this rather than testing ctx
     themselves, so a missing module cannot be reported one way on one
     sheet and another way on another.
     ============================================================ */

  function probe(ctx) {
    ctx = ctx || {};
    var p = { missing: [], have: {} };

    function look(key, value, module, sheet, effect) {
      var present = !!value;
      p.have[key] = present ? value : null;
      if (!present) p.missing.push({ key: key, module: module, sheet: sheet, effect: effect });
      return present;
    }

    look("planResult", ctx.planResult && ctx.planResult.marks ? ctx.planResult : null,
         "solver.js", "S2.0, S3.0",
         "no member schedule, no reactions and no calculations — the package carries " +
         "no sized member at all");
    look("model", ctx.model && ctx.model.levels ? ctx.model : null,
         "cad.js", "S1.0",
         "no framing plan is drawn; the geometry a reviewer checks the spans against " +
         "is not in this package");
    look("takeoff", ctx.takeoff ? ctx.takeoff : null,
         "takeoff.js", "S1.0, S2.0, S5.0",
         "no derivation trail: no span, tributary or bearing on this set can be " +
         "reconstructed without reading code, and the unresolved list is unknown");
    look("bom", ctx.bom ? ctx.bom : null,
         "bom.js", "S4.0",
         "no bill of materials and — the half that matters — no list of what the " +
         "bill of materials excludes");
    look("juris", ctx.juris ? ctx.juris : null,
         "jurisdiction.js", "S0.0, S5.0",
         "no adopted code edition, no site hazard parameters and no submittal " +
         "checklist; the design criteria fall back to the region pack's PLANNING " +
         "DEFAULTS, which are not site values");
    look("pipeline", ctx.pipeline ? ctx.pipeline : null,
         "pipeline.js", "S0.0",
         "no approval trail — nobody is recorded as having approved any stage of " +
         "the work this package presents");

    /* the calc stack itself, which is not part of ctx but can still be absent */
    p.engine = (FM.engine && typeof FM.engine.run === "function") ? FM.engine : null;
    p.scope = (FM.scope && typeof FM.scope.render === "function") ? FM.scope : null;
    p.cad = (FM.cad && typeof FM.cad.validate === "function") ? FM.cad : null;
    p.weights = FM.weights || null;
    p.solver = FM.solver || null;
    return p;
  }

  /* ============================================================
     THE APPROVAL TRAIL

     pipeline.js may hand us its module, its snapshot(), or its raw
     state(). All three are accepted and normalised, because a package
     that cannot read the approval trail must say "not approved"
     rather than say nothing.
     ============================================================ */

  function pipeRows(pipeline) {
    var out = { available: false, rows: [], approved: 0, stale: 0, of: 0, audit: [], why: "" };
    if (!pipeline) {
      out.why = "pipeline.js supplied no approval state to this package.";
      return out;
    }

    var snap = null;
    try {
      if (typeof pipeline.snapshot === "function") snap = pipeline.snapshot();
      else if (isArr(pipeline.stages)) snap = pipeline;
    } catch (e) { snap = null; }

    var stages = (FM.pipeline && isArr(FM.pipeline.STAGES)) ? FM.pipeline.STAGES
               : (isArr(pipeline.STAGES) ? pipeline.STAGES : null);

    if (snap && isArr(snap.stages)) {
      out.available = true;
      snap.stages.forEach(function (row) {
        var st = row.stage || {};
        var rec = row.rec || {};
        out.rows.push({
          id: safe(st.id, "(unnamed stage)"),
          label: safe(st.label, safe(st.id, "(unnamed stage)")),
          gate: safe(st.gate, ""),
          needs: safe(st.needs, ""),
          status: safe(row.status, "pending"),
          by: safe(rec.by, ""),
          at: safe(rec.at, ""),
          note: safe(rec.note, ""),
          moved: isArr(row.moved) ? row.moved.map(function (m) { return safe(m.label, safe(m.stage, "?")); }) : [],
          blockedBy: isArr(row.blockedBy) ? row.blockedBy.map(function (b) { return safe(b, ""); }) : []
        });
      });
    } else {
      /* the raw state() shape from the contract: {stageId, stages:{id:{...}}} */
      var raw = null;
      try { raw = (typeof pipeline.state === "function") ? pipeline.state() : pipeline; } catch (e) { raw = null; }
      var map = raw && raw.stages && !isArr(raw.stages) ? raw.stages : null;
      if (!map && !stages) {
        out.why = "the approval state supplied is not a shape this sheet recognises.";
        return out;
      }
      out.available = true;
      var ids = stages ? stages.map(function (s) { return s.id; })
                       : (map ? Object.keys(map) : []);
      ids.forEach(function (id) {
        var st = null;
        if (stages) {
          stages.forEach(function (s) { if (s.id === id) st = s; });
        }
        var rec = (map && own(map, id)) ? map[id] : null;
        out.rows.push({
          id: safe(id),
          label: safe(st && st.label, safe(id)),
          gate: safe(st && st.gate, ""),
          needs: safe(st && st.needs, ""),
          status: safe(rec && rec.status, "pending"),
          by: safe(rec && rec.by, ""),
          at: safe(rec && rec.at, ""),
          note: safe(rec && rec.note, ""),
          moved: [], blockedBy: []
        });
      });
      if (raw && isArr(raw.trail)) out.audit = raw.trail;
    }

    try {
      if (!out.audit.length && typeof pipeline.audit === "function") out.audit = pipeline.audit() || [];
    } catch (e) { out.audit = out.audit || []; }

    out.of = out.rows.length;
    out.rows.forEach(function (r) {
      if (r.status === "approved") out.approved++;
      if (r.status === "stale") out.stale++;
    });
    return out;
  }

  /* ============================================================
     DESIGN CRITERIA

     What a plan reviewer opens the set to find, each value with its
     provenance class and its citation. Read from FM.juris where the
     jurisdiction module supplied one, and from the region pack's own
     declarations where it did not — in which case every row says, in
     terms, that it is a planning default and not a site value.

     Nothing on this table is invented. A criterion this build does not
     carry as a field prints as NOT DECLARED and becomes an open item
     on S5.0; it never receives a plausible number.
     ============================================================ */

  function criteria(pack, juris) {
    var rows = [], notes = [];
    function row(k, v, cls, cite) {
      rows.push({ k: k, v: v, cls: cls, cite: cite || "" });
    }
    var jur = juris && typeof juris === "object" ? juris : null;

    /* ---- the code ---- */
    if (jur && isArr(jur.codes) && jur.codes.length) {
      jur.codes.forEach(function (c) {
        row(safe(c.name, "Code"),
            safe(c.edition, "edition NOT DECLARED") +
              (c.adopted ? " · adopted " + safe(c.adopted) : ""),
            clsOf(c.cls),
            safe(c.cite, "") + (c.basis ? "  " + safe(c.basis) : ""));
      });
    } else if (pack && pack.code) {
      row("Governing code family", safe(pack.code.family, "NOT DECLARED"), clsOf(pack.code.cls),
          "The region pack declares a code FAMILY, not an edition.");
      row("Code edition", "NOT DECLARED", "not stated",
          "No jurisdiction record was supplied, so no adopted edition is stated here. " +
          "Confirm the adopted edition with the authority having jurisdiction.");
      if (pack.code.note) notes.push({ k: "CODE NOTE (region pack, verbatim)", t: pack.code.note });
    } else {
      row("Governing code", "NOT DECLARED", "not stated",
          "Neither a jurisdiction record nor a region pack was supplied.");
    }

    /* ---- wind ---- */
    if (jur && jur.wind) {
      row("Design wind speed", safe(jur.wind.vMph) + " mph", clsOf(jur.wind.cls), safe(jur.wind.cite, ""));
      row("Exposure category", safe(jur.wind.exposure), clsOf(jur.wind.cls), safe(jur.wind.note, ""));
    } else if (pack && pack.climate) {
      row("Design wind speed", safe(pack.climate.windMph && pack.climate.windMph.v) + " mph",
          clsOf(pack.climate.windMph && pack.climate.windMph.cls),
          safe(pack.climate.windMph && pack.climate.windMph.note, ""));
      row("Exposure category", safe(pack.climate.exposure && pack.climate.exposure.v),
          clsOf(pack.climate.exposure && pack.climate.exposure.cls),
          safe(pack.climate.exposure && pack.climate.exposure.note, ""));
    }
    row("Risk category", "NOT DECLARED", "not stated",
        "This build carries no risk-category field on either the region pack or the " +
        "jurisdiction record. Confirm against ASCE 7 Table 1.5-1 before the wind " +
        "speed above is used for anything.");

    /* ---- snow ---- */
    if (jur && jur.snow) {
      row("Ground snow p_g", safe(jur.snow.pgPsf) + " psf", clsOf(jur.snow.cls), safe(jur.snow.cite, ""));
    } else if (pack && pack.climate && pack.climate.groundSnow) {
      row("Ground snow p_g", safe(pack.climate.groundSnow.v) + " psf",
          clsOf(pack.climate.groundSnow.cls), safe(pack.climate.groundSnow.note, ""));
    }

    /* ---- seismic ---- */
    if (jur && jur.seismic) {
      row("Seismic design category", safe(jur.seismic.sdc), clsOf(jur.seismic.cls), safe(jur.seismic.cite, ""));
      row("S_s / S_1", safe(jur.seismic.ss) + " / " + safe(jur.seismic.s1), clsOf(jur.seismic.cls),
          safe(jur.seismic.cite, ""));
    } else if (pack && pack.climate && pack.climate.sdc) {
      row("Seismic design category", safe(pack.climate.sdc.v), clsOf(pack.climate.sdc.cls),
          safe(pack.climate.sdc.note, ""));
      row("S_s / S_1", "NOT DECLARED", "not stated",
          "No jurisdiction record was supplied; the mapped spectral accelerations are " +
          "not carried by a region pack. Look them up on the ASCE 7 Hazard Tool.");
    }

    /* ---- live loads ---- */
    var LIVE = FM.weights && FM.weights.LIVE;
    if (pack && pack.loads) {
      row("Floor live load", safe(pack.loads.floorLive) + " psf", "code",
          LIVE && LIVE.floor_residential ? safe(LIVE.floor_residential.cite) : "");
      if (pack.climate && pack.climate.roofLive) {
        row("Roof live load L_r", safe(pack.climate.roofLive.v) + " psf",
            clsOf(pack.climate.roofLive.cls), safe(pack.climate.roofLive.note, ""));
      }
      if (pack.loads.ceilingLive !== undefined) {
        row("Attic / ceiling live", safe(pack.loads.ceilingLive) + " psf", "code",
            LIVE && LIVE.attic_no_storage ? safe(LIVE.attic_no_storage.cite) : "");
      }
      if (pack.loads.deckLive !== undefined) {
        row("Deck live load", safe(pack.loads.deckLive) + " psf", "code",
            LIVE && LIVE.deck ? safe(LIVE.deck.cite) : "");
      }
      row("Design roof load used", safe(pack.loads.roofLoad) + " psf · " +
          (pack.loads.roofType === "snow" ? "snow, C_D 1.15" : "roof live, C_D 1.25"), "derived",
          "One roof load, tagged. See the roof-load basis below.");
      if (pack.loads.roofLoadBasis) notes.push({ k: "ROOF LOAD BASIS (region pack, verbatim)", t: pack.loads.roofLoadBasis });
    }

    /* ---- dead loads ---- */
    var A = FM.weights && FM.weights.ASSEMBLY;
    if (A && pack && pack.loads) {
      ["roofAssembly", "floorAssembly", "ceilingAssembly"].forEach(function (k) {
        var key = pack.loads[k];
        if (!key || !own(A, key)) return;
        row(k === "roofAssembly" ? "Roof dead load" : (k === "floorAssembly" ? "Floor dead load" : "Ceiling dead load"),
            safe(A[key].psf) + " psf · " + safe(A[key].label), clsOf(A[key].cls),
            safe(A[key].makeup, ""));
      });
    }
    row("Wall dead load", "NONE CARRIED", "not stated",
        "The engine carries no wall dead load of any kind. A header under a gable end " +
        "or an upper storey must have that load added by hand — see S0.1 engine limits.");

    /* ---- serviceability ---- */
    var D = FM.engine && FM.engine.DEFL;
    if (D) {
      Object.keys(D).forEach(function (k) {
        var r = D[k] || {};
        row("Deflection · " + k,
            "live ℓ/" + safe(r.live) + " · total ℓ/" + safe(r.total),
            "code",
            safe(r.cite, "") + (r.totalCite ? "   TOTAL ROW: " + safe(r.totalCite) : ""));
      });
    }
    if (pack) {
      row("Firm DCR target", n2(pack.maxDCR, 2), "user",
          safe(pack.maxDCRBasis, "Firm policy. calc-spec §6.2 permits a tighter target than 1.000, never a looser one."));
    }
    return { rows: rows, notes: notes };
  }

  /* ============================================================
     GEOMETRY FOR S1.0

     DOM-free: this reduces the cad.js model to drawing primitives and
     to a placement for each member mark, so the text form and the SVG
     form are the same answer rendered twice. The SVG lives in the
     view; nothing here touches the DOM.

     Mark placement is READ, never guessed. A mark lands on a framing
     region or an opening only where the takeoff's own derivations name
     one; everything else is reported as UNPLACED, in the legend, with
     the reason. A mark drawn at a plausible-looking spot on a framing
     plan is a lie that a plan reviewer has no way to detect.
     ============================================================ */

  function geometry(model, takeoff, cad) {
    var g = { ok: false, why: "", levels: [], bounds: null, validation: null, stats: null,
              placed: [], unplaced: [], northDeclared: false };

    if (!model || !isArr(model.levels)) {
      g.why = "no CAD model was supplied to this package";
      return g;
    }

    if (cad) {
      try { g.validation = cad.validate(model) || []; } catch (e) { g.validation = null; }
      try { g.stats = cad.stats(model) || null; } catch (e) { g.stats = null; }
    }

    var minX = null, minY = null, maxX = null, maxY = null;
    function seen(x, y) {
      x = Number(x); y = Number(y);
      if (!isFinite(x) || !isFinite(y)) return;
      if (minX === null || x < minX) minX = x;
      if (maxX === null || x > maxX) maxX = x;
      if (minY === null || y < minY) minY = y;
      if (maxY === null || y > maxY) maxY = y;
    }

    model.levels.forEach(function (lv) {
      if (!lv) return;
      var L = { id: safe(lv.id, "(level)"), label: safe(lv.label, safe(lv.id, "(level)")),
                topPlateFt: lv.topPlateFt, walls: [], openings: [], framing: [] };
      (isArr(lv.walls) ? lv.walls : []).forEach(function (w) {
        if (!w) return;
        var x1 = Number(w.x1), y1 = Number(w.y1), x2 = Number(w.x2), y2 = Number(w.y2);
        var ok = isFinite(x1) && isFinite(y1) && isFinite(x2) && isFinite(y2);
        if (ok) { seen(x1, y1); seen(x2, y2); }
        L.walls.push({
          id: safe(w.id, "(wall)"), x1: x1, y1: y1, x2: x2, y2: y2, drawable: ok,
          exterior: !!w.exterior, bearing: !!w.bearing,
          lengthFt: ok ? Math.sqrt((x2 - x1) * (x2 - x1) + (y2 - y1) * (y2 - y1)) : null,
          thicknessIn: w.thicknessIn, heightFt: w.heightFt, note: safe(w.note, "")
        });
      });
      (isArr(lv.openings) ? lv.openings : []).forEach(function (o) {
        if (!o) return;
        var host = null;
        L.walls.forEach(function (w) { if (w.id === safe(o.wallId)) host = w; });
        var mid = null;
        if (host && host.drawable && host.lengthFt > 0 && isFinite(Number(o.offsetFt))) {
          var t = (Number(o.offsetFt) + (Number(o.widthFt) || 0) / 2) / host.lengthFt;
          if (t >= 0 && t <= 1.5) {
            mid = { x: host.x1 + (host.x2 - host.x1) * t, y: host.y1 + (host.y2 - host.y1) * t };
          }
        }
        L.openings.push({
          id: safe(o.id, "(opening)"), wallId: safe(o.wallId, "—"), kind: safe(o.kind, "—"),
          offsetFt: o.offsetFt, widthFt: o.widthFt, headHeightFt: o.headHeightFt,
          at: mid, hostFound: !!host, note: safe(o.note, "")
        });
      });
      (isArr(lv.framing) ? lv.framing : []).forEach(function (f) {
        if (!f) return;
        var poly = [], cx = 0, cy = 0, n = 0;
        (isArr(f.polygon) ? f.polygon : []).forEach(function (p) {
          if (!isArr(p) || p.length < 2) return;
          var x = Number(p[0]), y = Number(p[1]);
          if (!isFinite(x) || !isFinite(y)) return;
          poly.push([x, y]); seen(x, y); cx += x; cy += y; n++;
        });
        L.framing.push({
          id: safe(f.id, "(region)"), kind: safe(f.kind, "—"), polygon: poly,
          at: n ? { x: cx / n, y: cy / n } : null,
          directionDeg: f.directionDeg, spacingIn: f.spacingIn,
          bearsOn: isArr(f.bearsOn) ? f.bearsOn.map(function (b) { return safe(b); }) : [],
          note: safe(f.note, "")
        });
      });
      g.levels.push(L);
    });

    if (minX === null) {
      g.why = "the model carries no coordinate this sheet can draw";
      return g;
    }
    g.ok = true;
    g.bounds = { minX: minX, minY: minY, maxX: maxX, maxY: maxY,
                 wFt: maxX - minX, hFt: maxY - minY };
    g.underlay = model.underlay ? {
      calibrated: !!(model.underlay.calib && isFinite(Number(model.underlay.calib.knownFt))),
      opacity: model.underlay.opacity
    } : null;

    /* ---- north ----
       The model contract has an origin and axes and NO true-north bearing.
       So the arrow on the sheet is labelled as an assumption, not drawn as a
       fact, and it becomes an open item. */
    g.northDeclared = false;
    g.northNote = "PLAN NORTH IS ASSUMED to be the model's +y axis. The model declares " +
                  "no true-north bearing, so the arrow on this sheet is an assumption of " +
                  "this drawing and not a property of the geometry. Confirm the " +
                  "orientation against the architectural site plan.";

    /* ---- placement ---- */
    /* Order matters: an opening is a more specific place than the framing
       region over it, and a framing region is more specific than a wall, so
       the search that follows tries them in that order and stops at the
       first. A header drawn at the centroid of the whole roof is not wrong
       by a little, it is on the wrong part of the house. */
    var index = {}, order = [];
    function put(id, at, on, kind) {
      if (!at || own(index, id)) return;
      index[id] = { at: at, on: on, kind: kind };
      order.push(id);
    }
    g.levels.forEach(function (L) {
      L.openings.forEach(function (o) { put(o.id, o.at, "opening " + o.id, "opening"); });
    });
    g.levels.forEach(function (L) {
      L.framing.forEach(function (f) { put(f.id, f.at, "framing region " + f.id, "framing"); });
    });
    g.levels.forEach(function (L) {
      L.walls.forEach(function (w) {
        if (!w.drawable) return;
        put(w.id, { x: (w.x1 + w.x2) / 2, y: (w.y1 + w.y2) / 2 }, "wall " + w.id, "wall");
      });
    });
    g.index = index;
    g.indexOrder = order;

    var derivs = (takeoff && isArr(takeoff.derivations)) ? takeoff.derivations : null;
    g.placementBasis = derivs
      ? "each mark is placed where the takeoff's own derivations say it came from"
      : "no takeoff derivations were supplied, so no mark can be placed on the geometry";
    g.derivationsAvailable = !!derivs;
    return g;
  }

  function placeMarks(g, markIds, takeoff) {
    if (!g || !g.ok) return;
    var derivs = (takeoff && isArr(takeoff.derivations)) ? takeoff.derivations : [];
    var keys = g.indexOrder || Object.keys(g.index || {});
    function findIn(text) {
      for (var j = 0; j < keys.length; j++) {
        if (text.indexOf(keys[j]) === -1) continue;
        /* the whole token, not a prefix: W1 must not match W11 */
        var re = new RegExp("(^|[^A-Za-z0-9_-])" +
                            keys[j].replace(/[.*+?^${}()|[\]\\]/g, "\\$&") +
                            "([^A-Za-z0-9_-]|$)");
        if (re.test(text)) return g.index[keys[j]];
      }
      return null;
    }
    markIds.forEach(function (id) {
      var hit = null, how = "";
      for (var i = 0; i < derivs.length && !hit; i++) {
        var d = derivs[i];
        if (!d || safe(d.markId) !== id) continue;
        /* `from` is the derivation's own statement of where the number came
           from and is authoritative; `how` is prose and is only consulted
           when `from` names nothing this drawing knows about */
        hit = findIn(safe(d.from, ""));
        if (!hit) hit = findIn(safe(d.how, ""));
        if (hit) how = safe(d.field, "") + (d.field ? " " : "") + "from " + safe(d.from, "the takeoff");
      }
      if (hit) g.placed.push({ id: id, x: hit.at.x, y: hit.at.y, on: hit.on, how: how });
      else g.unplaced.push({ id: id, why: g.derivationsAvailable
        ? "no takeoff derivation names a wall, opening or framing region for this mark"
        : "no takeoff was supplied, so nothing says where this mark sits on the plan" });
    });
  }

  /* ============================================================
     OPEN ITEMS

     Collected from every stage, and the standing items ALWAYS print.
     They are not padding: they are true of every package this system
     produces, and a set that reported zero open items would be
     claiming a completeness the system cannot have.
     ============================================================ */

  function collectOpen(ctx, p, res) {
    var items = [];
    function add(group, what, why, need) {
      items.push({ group: group, what: what, why: why, need: need });
    }

    /* ---- 1. standing ---- */
    add("STANDING", "The seal is not applied.",
        "This software never seals a design. The seal block on S0.0 is empty by " +
        "construction and no output of this system may say otherwise.",
        "A licensed PE reviews this package and seals it under their own licence.");
    add("STANDING", "Site loads are not confirmed for this site.",
        "The wind speed, exposure, ground snow and seismic values on S0.0 are " +
        "planning values carried by a region pack or a jurisdiction record. They are " +
        "not a site determination.",
        "Confirm every one of them against the ASCE 7 Hazard Tool and the AHJ, and " +
        "re-run the package if any of them moves.");
    add("STANDING", "No connection of any kind is designed.",
        "calc-spec §8 item 17: hangers, straps, bolts, screws, nails, hold-downs and " +
        "bearing plates as designed elements are all outside this engine. Bearing is " +
        "checked as f_c-perp on wood only.",
        "The reactions on S2.0 are published unreduced so a connection designer can " +
        "use them. Somebody must do that work.");
    add("STANDING", "Lateral design is absent — wind and seismic are not checked.",
        "calc-spec §8 item 11. No uplift, no net-uplift reversal, no lateral " +
        "combinations, no combined bending and axial from drift.",
        "A separate lateral design is required, and in a wind-governed market it " +
        "governs the members checked here as well.");
    add("STANDING", "This is a member check, not a design.",
        "calc-spec §8 item 23. The engine checks members that are proposed to it; it " +
        "does not lay out a structure, choose a framing scheme or design a system.",
        "The reviewing engineer owns the design. This package is evidence, not a decision.");

    /* ---- 2. what did not exist ---- */
    p.missing.forEach(function (m) {
      add("INPUT NOT AVAILABLE", m.module + " supplied nothing (ctx." + m.key + ")",
          m.effect, "Sheet " + m.sheet + " states this in place of the content. Re-run " +
          "the package once " + m.module + " has produced its output.");
    });

    /* ---- 3. the takeoff ---- */
    if (p.have.takeoff) {
      var tk = p.have.takeoff;
      (isArr(tk.unresolved) ? tk.unresolved : []).forEach(function (u) {
        add("TAKEOFF — UNRESOLVED", safe(u.what, "(unnamed)"), safe(u.why, "no reason given"),
            safe(u.need, "a human must answer this before the takeoff is complete"));
      });
      (isArr(tk.warnings) ? tk.warnings : []).forEach(function (wn) {
        add("TAKEOFF — WARNING", safe(wn && wn.what ? wn.what : wn, "(unnamed warning)"),
            safe(wn && wn.why, ""), safe(wn && wn.need, "review before gate 2 is approved"));
      });
      if (!isArr(tk.derivations) || !tk.derivations.length) {
        add("TAKEOFF — UNRESOLVED", "No derivation trail was supplied.",
            "The contract requires every span, tributary and bearing to be traced so a " +
            "reviewer can reconstruct it without reading code. None was supplied.",
            "Produce derivations before gate 2 (the takeoff gate) is approved.");
      }
    }

    /* ---- 4. the calculations ---- */
    if (res && isArr(res.marks)) {
      var esc = res.marks.filter(function (m) { return !m.notApplicable && m.solution && !m.solution.pick; });
      var byReason = {};
      esc.forEach(function (m) {
        var k = (m.solution && m.solution.status) || "escalate";
        if (!own(byReason, k)) byReason[k] = [];
        byReason[k].push(m);
      });
      Object.keys(byReason).sort().forEach(function (k) {
        var e = FM.solver && FM.solver.escalationOf ? FM.solver.escalationOf(k)
              : { tag: k, short: "no member was selected" };
        add("CALCULATIONS — ESCALATED",
            byReason[k].length + " mark(s): " + byReason[k].map(function (m) { return safe(m.mark.id); }).join(", ") +
            "  [" + safe(e.tag) + "]",
            safe(e.short),
            k === "escalate:procurement"
              ? "A member passes the engine and the availability floor excludes it — confirm the yard will stock it, or lower the floor deliberately."
              : "These marks have NO member in this package. Somebody must size them by another method.");
      });
      res.marks.filter(function (m) { return m.notApplicable; }).forEach(function (m) {
        add("CALCULATIONS — NOT SIZED",
            safe(m.mark.id) + " — " + safe(m.mark.label),
            "[" + safe(m.notApplicable.reason) + "] " + safe(m.notApplicable.note, ""),
            "Carried deliberately. This mark is not this engine's member and nothing in " +
            "this package checks it.");
      });
      var adv = [];
      res.marks.forEach(function (m) {
        ((m.solution && m.solution.advisories) || []).forEach(function (a) {
          adv.push({ id: safe(m.mark.id), text: safe(a.text) });
        });
      });
      adv.forEach(function (a) {
        add("CALCULATIONS — NOT CHECKED", a.id, a.text,
            "The search flagged this case as one it did not check. Check it by hand.");
      });
      if (res.rollup && !res.rollup.complete) {
        add("CALCULATIONS — INCOMPLETE", "This is not a complete schedule.",
            "Reported by the solver: " + safe(res.rollup.incompleteBecause, "not stated") + ".",
            "Do not read the members on S2.0 as a finished design.");
      }
      if (res.pack && res.pack.governs === "wind") {
        add("CALCULATIONS — INCOMPLETE", "Wind governs in this market and is not checked here.",
            safe(res.pack.governsNote, "This engine checks gravity only."),
            "A gravity-passing member in this market is not a finished design.");
      }
    }

    /* ---- 5. the bill of materials ---- */
    if (p.have.bom) {
      var bom = p.have.bom;
      var exc = isArr(bom.excluded) ? bom.excluded : null;
      if (!exc) {
        add("BILL OF MATERIALS — EXCLUDED", "The bill of materials declares no exclusion list.",
            "The contract requires one: anything the calc stack does not size must be " +
            "listed as absent with a reason. A BOM that silently omits the girder reads " +
            "as a complete order.",
            "bom.js must publish `excluded` before the quantities are used to buy anything.");
      } else {
        exc.forEach(function (x) {
          add("BILL OF MATERIALS — EXCLUDED", safe(x.what, "(unnamed)"),
              safe(x.why, "no reason given"),
              "Not in the quantities on S4.0. Price and buy it separately.");
        });
      }
    }

    /* ---- 6. the jurisdiction ---- */
    if (p.have.juris) {
      var j = p.have.juris;
      var mv = isArr(j.mustVerify) ? j.mustVerify : null;
      if (!mv || !mv.length) {
        add("JURISDICTION — MUST VERIFY", "The jurisdiction record published no must-verify list.",
            "The contract says this list is ALWAYS non-empty. An empty one means the " +
            "record has not been checked, not that everything is certain.",
            "Check the adoption and the site hazard values with the AHJ.");
      } else {
        mv.forEach(function (v) {
          add("JURISDICTION — MUST VERIFY",
              safe(v && v.what ? v.what : v, "(unnamed)"),
              safe(v && v.why, ""),
              safe(v && v.against, safe(v && v.need, "Verify with the authority having jurisdiction.")));
        });
      }
    } else {
      add("JURISDICTION — MUST VERIFY", "Every design criterion on S0.0 is unverified.",
          "No jurisdiction record was supplied, so the adopted code edition, the wind " +
          "speed, the exposure, the snow and the seismic values are the region pack's " +
          "PLANNING DEFAULTS.",
          "Confirm each of them with the AHJ and the ASCE 7 Hazard Tool.");
    }

    /* ---- 7. the gates ---- */
    var pipe = pipeRows(p.have.pipeline);
    if (!pipe.available) {
      add("APPROVAL — NOT APPROVED", "No approval trail is available.",
          pipe.why || "pipeline.js supplied no state.",
          "Every stage gate must be approved by a named person before this package is issued.");
    } else {
      pipe.rows.forEach(function (r) {
        if (r.status === "approved") return;
        add("APPROVAL — NOT APPROVED", r.label + " (gate: " + r.id + ") is " + r.status,
            r.status === "stale"
              ? "An input this approval depended on has moved since it was given" +
                (r.moved.length ? " — " + r.moved.join(", ") : "") + ". The approval is void."
              : (r.blockedBy.length ? r.blockedBy.join("; ") : "No named person has approved this stage."),
            safe(r.gate, "This gate must be approved before the next stage is entered."));
      });
    }

    /* ---- 8. the geometry ---- */
    if (p.have.model) {
      add("GEOMETRY", "Plan north is not declared by the model.",
          "The CAD model carries an origin and axes but no true-north bearing, so the " +
          "north arrow on S1.0 is an assumption of the drawing.",
          "Confirm the orientation against the architectural site plan.");
    }
    if (!p.cad && p.have.model) {
      add("GEOMETRY", "The model was not validated.",
          "cad.js was not loaded, so FM.cad.validate() did not run against this model. " +
          "A wall with no thickness, an opening wider than its wall or a framing region " +
          "bearing on nothing would not have been caught.",
          "Load cad.js and re-run the package.");
    }
    return items;
  }

  /* ============================================================
     SHEETS
     ============================================================ */

  function sheetFrame(pkg, sheet, body) {
    var L = [];
    var no = sheet.no;
    L.push(rule("="));
    L.push(pad("FIRMARK · PLAN SET PREPARED FOR PE REVIEW", W - no.length) + no);
    L.push(String(sheet.title).toUpperCase());
    L.push(rule("-"));
    var f = fielder(function (x) { L.push(x); }, 0, 9);
    f("Project", pkg.head.project);
    f("Region", pkg.head.region);
    f("Package", pkg.head.packageId + " generated " + pkg.head.at);
    L.push(rule("="));
    L.push("");
    body.forEach(function (x) { L.push(x === undefined ? "" : x); });
    L.push("");
    L.push(rule("-"));
    L.push(no + " · " + String(sheet.title).toUpperCase() + " · sheet " + sheet.seq + " of " + pkg.sheets.length);
    wrap(FOOTER, W).forEach(function (x) { L.push(x); });
    return L;
  }

  /* ---- S0.0 COVER ---- */

  function sheetCover(ctx, p, res, pkg) {
    var L = [];
    function say(s) { L.push(s === undefined ? "" : s); }
    function block(t) { say(); say(rule("-")); say(t); say(rule("-")); say(); }
    var field = fielder(say, 2, 22);

    var plan = res ? res.plan : (ctx.plan || null);
    var pack = res ? res.pack : (ctx.pack || null);

    block("PROJECT");
    field("Plan", plan ? safe(plan.name) : "NOT SUPPLIED — no solver result and no plan");
    if (plan) {
      field("Summary", safe(plan.summary, "not declared"));
      field("Plan id", safe(plan.id));
      field("Lots (declared)", plan.lots === undefined ? "not declared" : comma(plan.lots));
      if (plan.geometry) {
        var gm = plan.geometry;
        if (isArr(gm.footprintFt) && gm.footprintFt.length === 2) {
          field("Footprint", n2(gm.footprintFt[0], 0) + " ft × " + n2(gm.footprintFt[1], 0) + " ft  [declared]");
        }
        if (gm.underRoofSf !== undefined) field("Area under roof", comma(gm.underRoofSf) + " sf  [declared]");
        if (gm.roofForm) field("Roof form", safe(gm.roofForm));
        if (gm.bearingLines) {
          wrap("Bearing lines: " + safe(gm.bearingLines), W - 6).forEach(function (x) { say("      " + x); });
        }
      }
    }
    field("Region pack", pack ? safe(pack.name) + " · " + safe(pack.markets) : "NOT SUPPLIED");
    field("Prepared", pkg.head.at + "  (generation time, not an issue date)");

    /* ---- the statement, first, before any number ---- */
    block("WHAT THIS PACKAGE IS");
    wrap(NOT_SEALED, W - 2).forEach(function (x) { say("  " + x); });
    say();
    wrap("It is a GRAVITY MEMBER CHECK of the marks listed on S2.0, against the design " +
         "criteria below, produced by an automated tool whose boundaries are printed in " +
         "full on S0.1. It is not a design, it is not a complete structural submittal, " +
         "and the open items on S5.0 are part of it — read them before the members.", W - 2)
      .forEach(function (x) { say("  " + x); });

    /* ---- design criteria ---- */
    var crit = criteria(pack, p.have.juris);
    block("DESIGN CRITERIA");
    if (p.have.juris) {
      say("  Source: the jurisdiction record supplied by jurisdiction.js" +
          (p.have.juris.id ? " for " + safe(p.have.juris.id) : "") + ".");
    } else {
      say("  ** NO JURISDICTION RECORD WAS SUPPLIED (jurisdiction.js). The values below");
      say("     come from the region pack and are PLANNING DEFAULTS, not site values.");
      say("     Every one of them is an open item on S5.0. **");
    }
    say();
    var KW = 26, VW = 30;
    say("  " + pad("CRITERION", KW) + pad("VALUE", VW) + "PROVENANCE");
    say("  " + rule("-").slice(0, W - 2));
    crit.rows.forEach(function (r) {
      /* a criterion or a value that does not fit its column takes its own
         line rather than running into the next one — a design criteria table
         whose columns collide is the one table on the set a plan reviewer
         reads first */
      if (r.k.length <= KW && r.v.length <= VW) {
        say("  " + pad(r.k, KW) + pad(r.v, VW) + r.cls);
      } else {
        say("  " + r.k);
        say("  " + pad("", KW) + pad(r.v, Math.max(VW, r.v.length + 2)) + r.cls);
      }
      if (r.cite) {
        wrap(r.cite, W - 12).forEach(function (x) { say("        " + x); });
      }
    });
    say();
    say("  PROVENANCE CLASSES USED ABOVE");
    Object.keys(CLS_TEXT).forEach(function (k) {
      say("      " + pad(k, 12) + CLS_TEXT[k].slice(k.length + 3));
    });
    wrap("this build carries no field for it — it is NOT a value, and it is an open item",
         W - 20).forEach(function (x, i) { say("      " + pad(i ? "" : "not stated", 12) + x); });
    crit.notes.forEach(function (nt) {
      say();
      say("  " + nt.k);
      wrap(safe(nt.t), W - 6).forEach(function (x) { say("      " + x); });
    });

    /* ---- the seal block ---- */
    block("SEAL BLOCK — INTENTIONALLY EMPTY");
    var box = W - 4;
    say("  +" + new Array(box).join("-") + "+");
    function boxLine(t) { say("  |" + pad(" " + t, box - 1) + "|"); }
    boxLine("");
    boxLine("ENGINEER OF RECORD — SEAL AND SIGNATURE");
    boxLine("");
    boxLine("");
    boxLine("");
    boxLine("");
    boxLine("");
    SEAL_LINES.forEach(function (x) { boxLine(x); });
    boxLine("");
    boxLine("This block is empty because this software does not seal, sign or");
    boxLine("approve engineering. It is completed by the licensed engineer who");
    boxLine("reviews this package, under their own licence and liability.");
    boxLine("");
    say("  +" + new Array(box).join("-") + "+");
    say();
    var who = null;
    try { who = FM.auth && FM.auth.state ? FM.auth.state().user : null; } catch (e) { who = null; }
    if (who) {
      field("Prepared in session by", safe(who.name) + "  [" +
            (isArr(who.roles) ? who.roles.join(", ") : safe(who.roles, "no role")) + "]");
      field("Professional licence", who.licence ? safe(who.licence) :
            "NONE ON FILE — the person who prepared this package holds no professional " +
            "licence in this system, which is why the block above is empty");
    } else {
      field("Prepared in session by", "nobody is signed in — this package carries no " +
            "preparer name at all");
    }

    /* ---- approval trail ---- */
    var pipe = pipeRows(p.have.pipeline);
    block("APPROVAL TRAIL");
    if (!pipe.available) {
      say("  ** NOT APPROVED — no approval trail is available. **");
      wrap(pipe.why + " No stage of the work behind this package is recorded as " +
           "approved by a named person, so nothing here has been through a gate.", W - 6)
        .forEach(function (x) { say("     " + x); });
    } else {
      say("  " + pipe.approved + " of " + pipe.of + " gates approved" +
          (pipe.stale ? "   ·   " + pipe.stale + " INVALIDATED by a later change" : ""));
      if (!pipe.approved) say("  ** NOT APPROVED — no stage of this work has been approved. **");
      say();
      say("  " + pad("STAGE", 22) + pad("STATUS", 14) + pad("APPROVER", 18) + "WHEN");
      say("  " + rule("-").slice(0, W - 2));
      pipe.rows.forEach(function (r) {
        var status = r.status === "approved" ? "APPROVED"
                   : (r.status === "stale" ? "VOID (stale)"
                   : (r.status === "rejected" ? "REJECTED" : "not approved"));
        say("  " + pad(r.label, 22) + pad(status, 14) +
            pad(r.by || "—", 18) + (r.at || "—"));
        if (r.status === "stale" && r.moved.length) {
          wrap("invalidated because " + r.moved.join(", ") + " moved after it was given — " +
               "an approval that survives a change to what was approved is worthless", W - 8)
            .forEach(function (x) { say("      " + x); });
        }
        if (r.note) wrap("note: " + r.note, W - 8).forEach(function (x) { say("      " + x); });
      });
      say();
      wrap("The last gate in this pipeline records that a licensed engineer received a " +
           "package and found it reviewable. IT DOES NOT SEAL ANYTHING. The seal is " +
           "applied by that engineer, outside this system, under their licence.", W - 4)
        .forEach(function (x) { say("  " + x); });
      if (pipe.audit && pipe.audit.length) {
        say();
        say("  AUDIT TRAIL — last " + Math.min(8, pipe.audit.length) + " of " + pipe.audit.length + " entries");
        pipe.audit.slice(Math.max(0, pipe.audit.length - 8)).forEach(function (a) {
          say("      " + pad(safe(a.at, "—"), 26) + pad(safe(a.kind, "—"), 10) +
              pad(safe(a.stage, "—"), 12) + safe(a.by, "—"));
        });
      }
    }

    /* ---- master set ---- */
    if (plan && FM.weights && typeof FM.weights.variantsFor === "function") {
      var vi = null;
      try { vi = FM.weights.variantsFor(plan); } catch (e) { vi = null; }
      if (vi && vi.declaresVariants) {
        block("MASTER SET — WHAT THIS PACKAGE COVERS");
        wrap("This plan is a master set: " + (isArr(vi.elevations) ? vi.elevations.length : 0) +
             " elevation(s) × " + (isArr(vi.options) ? vi.options.length : 0) + " option(s)" +
             (isArr(vi.combinations) ? " = " + vi.combinations.length + " buildable combination(s)" : "") +
             (isFinite(Number(vi.lots)) ? " over " + comma(vi.lots) + " lots" : "") + ".", W - 4)
          .forEach(function (x) { say("  " + x); });
        say();
        var solvedId = plan.variant || plan.variantId || (vi.solvedFor && vi.solvedFor.id) || null;
        if (!solvedId && isArr(vi.combinations)) {
          vi.combinations.forEach(function (c) { if (!solvedId && c.isBase) solvedId = c.id; });
        }
        say("  Combination solved for : " + (solvedId ? safe(solvedId) : "NOT DECLARED"));
        say();
        wrap("** ONE COMBINATION, NOT AN ENVELOPE. The members on S2.0 were solved for the " +
             "combination named above. If an elevation or an option moves a bearing, a span " +
             "or a tributary, the member for that lot was not checked here. Variant labels " +
             "are the plan's own sales names and are deliberately not reproduced on this " +
             "sheet; take them from the plan record. **", W - 4)
          .forEach(function (x) { say("  " + x); });
      }
    }

    /* ---- index ---- */
    block("SHEET INDEX");
    pkg.sheets.forEach(function (s) {
      wrap(s.indexNote, W - 38).forEach(function (x, i) {
        say("  " + pad(i ? "" : s.no, 8) + pad(i ? "" : s.title, 26) + x);
      });
    });
    say();
    wrap("Every sheet in this set carries the same footer, and it is the point of the set:",
         W - 4).forEach(function (x) { say("  " + x); });
    wrap(FOOTER, W - 6).forEach(function (x) { say("      " + x); });

    /* ---- what was not available ---- */
    block("INPUTS THIS PACKAGE DID NOT HAVE — " + p.missing.length);
    if (!p.missing.length) {
      say("  Every input this package expects was supplied. That is a statement about the");
      say("  inputs and not about the result: read S5.0 before anything else.");
    } else {
      p.missing.forEach(function (m) {
        say("  " + pad("ctx." + m.key, 14) + "not supplied by " + m.module + "  (affects " + m.sheet + ")");
        wrap(m.effect, W - 8).forEach(function (x) { say("      " + x); });
      });
    }
    return L;
  }

  /* ---- S0.1 GENERAL NOTES ---- */

  function sheetNotes(ctx, p, res) {
    var L = [];
    function say(s) { L.push(s === undefined ? "" : s); }
    function block(t) { say(); say(rule("-")); say(t); say(rule("-")); say(); }
    var pack = res ? res.pack : (ctx.pack || null);

    block("G1 — THE STATUS OF THIS PACKAGE");
    wrap(NOT_SEALED, W - 2).forEach(function (x) { say("  " + x); });
    say();
    say("  " + SEAL_LINES[0]);
    say("  " + SEAL_LINES[1]);
    say();
    wrap("No heading, no table, no filename and no button anywhere in this system says " +
         "that a design here is finished, approved or sealed, because none of that would " +
         "be true. What this system does is assemble, honestly, everything a licensed " +
         "engineer needs in order to decide.", W - 2).forEach(function (x) { say("  " + x); });

    block("G2 — WHAT THIS PACKAGE COVERS");
    say("  Included:");
    say("      · a gravity check of the marks on S2.0, simply supported, uniformly loaded");
    say("      · the members proposed, their DCRs and the governing limit state");
    say("      · unreduced support reactions, for whoever designs the connections");
    say("      · the marks this engine REFUSED to size, and why (S5.0)");
    say("      · the design criteria and the provenance of every load (S0.0)");
    say();
    say("  Deferred to others — NOT in this package, by name:");
    [
      ["Truss / EWP package", "designed by its supplier as a deferred sealed submittal. This " +
        "package does not check a truss, and the truss reactions it would impose are the " +
        "supplier's output, not this tool's."],
      ["All connections", "hangers, straps, hold-downs, anchors, bearing plates, fasteners. " +
        "calc-spec §8 item 17. The reactions on S2.0 are the input to that work."],
      ["Lateral system", "wind and seismic, uplift and the continuous load path. §8 item 11."],
      ["Foundation and geotech", "no footing, slab, pier or soil-bearing check of any kind."],
      ["Shear walls and diaphragms", "not modelled, not checked."],
      ["Product approval", "NOA, Florida product approval, evaluation reports. A submittal " +
        "requirement, not a design load, and nothing here carries one."],
      ["Fire, energy, MEP", "outside this system entirely."]
    ].forEach(function (r) {
      say("      " + r[0]);
      wrap(r[1], W - 12).forEach(function (x) { say("          " + x); });
    });

    /* ---- deflection basis, derived from the pack's own declaration ---- */
    if (pack) {
      var fam = (pack.code && str(pack.code.family)) || "not declared";
      block("G3 — DEFLECTION BASIS");
      say("  Code family declared by this region pack : " + fam);
      say("  Deflection rows used by the engine       : IBC Table 1604.3");
      say();
      if (fam !== "IBC") {
        wrap("This package reports a TOTAL-LOAD (D + L) deflection row against every member. " +
             "IRC Table R301.7 — the table that governs one- and two-family dwellings, which " +
             "is what these plans are — has NO total-load column at all. That row is a FIRM " +
             "OVERLAY this tool applies on top of the code, not a code requirement. It adds a " +
             "check the code does not ask for, so on that row this package is more " +
             "conservative than the code and not less. The live-load rows do have counterparts " +
             "in R301.7; they are not reproduced here and must be verified against the adopted " +
             "edition.", W - 4).forEach(function (x) { say("  " + x); });
        say();
      }
      if (pack.code && pack.code.deflectionTable) {
        wrap("REGION PACK STATEMENT — " + safe(pack.code.deflectionTable), W - 6)
          .forEach(function (x) { say("      " + x); });
      }
    }

    /* ---- material provenance ---- */
    var meta = (typeof window !== "undefined" && window.MATDATA && window.MATDATA.meta) || null;
    block("G4 — MATERIAL PROVENANCE");
    if (!meta) {
      say("  The material catalog metadata is not available to this package, so the");
      say("  reference design values behind every member on S3.0 cannot be cited here.");
      say("  Do not accept a member until the catalog revision is stated.");
    } else {
      [["Reference design values", meta.species_grades],
       ["Section properties", meta.sections],
       ["Southern Pine", meta.southern_pine]].forEach(function (r) {
        say("  " + r[0]);
        say("      " + safe(r[1] && r[1].source_file));
        say("      revision " + safe(r[1] && r[1].dataset_version));
      });
    }
    say();
    wrap("Prices, availability, labor and SKU weights anywhere in this package are FIRM " +
         "PLACEHOLDERS with no code standing. They rank members that already passed; they " +
         "cannot make a member pass. Availability, however, decides which members are " +
         "offered at all — see the procurement escalations on S5.0.", W - 4)
      .forEach(function (x) { say("  " + x); });

    /* ---- the boundaries, from the one renderer ---- */
    if (!p.scope) {
      block("G5 — SCOPE BOUNDARIES");
      say("  ** NOT AVAILABLE — scope.js did not load, so the calc-spec §8 boundaries");
      say("     cannot be printed. calc-spec §8 requires them verbatim and unabridged on");
      say("     EVERY output: without them this package is not an engineering deliverable");
      say("     and must not be issued. **");
    } else {
      say();
      wrap("G5 — the boundaries below are rendered by FM.scope.render, the single " +
           "implementation shared with the schedule export and the calculation record, so " +
           "no output of this system can carry a stale or abridged copy of them.", W - 2)
        .forEach(function (x) { say("  " + x); });
      FM.scope.render(say, {
        heading: function (t) { say(); say(rule("-")); say(t); say(rule("-")); say(); }
      });
    }
    return L;
  }

  /* ---- S1.0 FRAMING PLAN ---- */

  function sheetFraming(ctx, p, res, g) {
    var L = [];
    function say(s) { L.push(s === undefined ? "" : s); }
    function block(t) { say(); say(rule("-")); say(t); say(rule("-")); say(); }

    if (!p.have.model) {
      block("NO FRAMING PLAN — THE GEOMETRY WAS NOT SUPPLIED");
      wrap("This sheet is empty of geometry. cad.js supplied no model to this package " +
           "(ctx.model), so there is no plan to draw, no member mark can be located, and a " +
           "reviewer cannot check a single span on this set against a drawing.", W - 4)
        .forEach(function (x) { say("  " + x); });
      say();
      wrap("A framing plan is not decoration. Without it the spans and tributaries on S2.0 " +
           "are numbers with nothing behind them, and this package cannot be reviewed as a " +
           "plan set. It is listed as an open item on S5.0.", W - 4)
        .forEach(function (x) { say("  " + x); });
      var plan = res ? res.plan : null;
      if (plan && plan.geometry) {
        block("WHAT THE PLAN RECORD DECLARES — TEXT ONLY, NOT A DRAWING");
        say("  These are the plan's own declared dimensions. They are NOT a framing plan and");
        say("  nothing below was drawn, checked or located.");
        say();
        Object.keys(plan.geometry).forEach(function (k) {
          var v = plan.geometry[k];
          if (v === null || v === undefined) return;
          if (typeof v === "object" && !isArr(v)) return;
          var val = isArr(v) ? v.map(function (x) { return safe(x); }).join(" × ") : safe(v);
          if (val.length > 40) {
            say("      " + k);
            wrap(val, W - 12).forEach(function (x) { say("          " + x); });
          } else {
            say("      " + pad(k, 20) + val);
          }
        });
      }
      return L;
    }

    if (!g.ok) {
      block("NO FRAMING PLAN — THE MODEL COULD NOT BE READ");
      wrap("A model was supplied but " + g.why + ". Nothing is drawn on this sheet.", W - 4)
        .forEach(function (x) { say("  " + x); });
      return L;
    }

    block("FRAMING PLAN — " + safe(ctx.model.name, "unnamed model"));
    if (!p.cad) {
      say("  ** cad.js IS NOT LOADED. The model below was read directly against the");
      say("     documented shape; FM.cad.validate() and FM.cad.stats() did NOT run, so a");
      say("     wall with no thickness, an opening wider than its wall or a framing region");
      say("     bearing on nothing would not have been caught. **");
      say();
    }
    say("  Model version : " + safe(ctx.model.version));
    say("  Levels        : " + g.levels.length);
    say("  Extents       : " + n2(g.bounds.wFt, 1) + " ft × " + n2(g.bounds.hFt, 1) + " ft" +
        "   (origin " + n2(g.bounds.minX, 1) + ", " + n2(g.bounds.minY, 1) + ")");
    if (g.stats) {
      say("  cad.stats     : " + Object.keys(g.stats).map(function (k) {
        return k + " " + safe(g.stats[k]);
      }).join(" · "));
    }
    if (g.underlay) {
      say("  Underlay      : present, " + (g.underlay.calibrated ? "calibrated" :
          "NOT CALIBRATED — no scale can be taken from it"));
    }
    say();
    wrap("The drawn form of this sheet — on screen and in print — carries this same " +
         "geometry to scale with a graphic scale bar, a north arrow and a legend. This " +
         "text form carries it as tables so the package survives being pasted into an " +
         "email. Neither form adds anything the model does not contain.", W - 4)
      .forEach(function (x) { say("  " + x); });
    say();
    var nn = wrap(g.northNote, W - 10);
    nn.forEach(function (x, i) {
      say("  " + (i ? "     " : "  ** ") + x + (i === nn.length - 1 ? " **" : ""));
    });

    if (g.validation && g.validation.length) {
      block("MODEL VALIDATION — " + g.validation.length + " FINDING(S) FROM cad.validate()");
      g.validation.forEach(function (v) {
        say("  [" + safe(v.severity, "?") + "] " + safe(v.level, "—") + " " + safe(v.id, "—"));
        wrap(safe(v.text), W - 8).forEach(function (x) { say("      " + x); });
      });
    } else if (g.validation) {
      say();
      say("  cad.validate() returned no findings against this model.");
    }

    g.levels.forEach(function (lv) {
      block("LEVEL " + lv.id + " — " + lv.label +
            (lv.topPlateFt === undefined ? "" : "   top plate " + n2(lv.topPlateFt, 2) + " ft"));
      say("  WALLS — " + lv.walls.length);
      say("  " + pad("ID", 8) + pad("FROM", 16) + pad("TO", 16) + pad("LENGTH", 10) +
          pad("TYPE", 18) + "THK");
      say("  " + rule("-").slice(0, W - 2));
      lv.walls.forEach(function (w) {
        say("  " + pad(w.id, 8) +
            pad(w.drawable ? n2(w.x1, 1) + ", " + n2(w.y1, 1) : "—", 16) +
            pad(w.drawable ? n2(w.x2, 1) + ", " + n2(w.y2, 1) : "—", 16) +
            pad(w.lengthFt === null ? "—" : n2(w.lengthFt, 2) + " ft", 10) +
            pad((w.exterior ? "exterior" : "interior") + (w.bearing ? "/bearing" : ""), 18) +
            (w.thicknessIn === undefined ? "—" : n2(w.thicknessIn, 2) + " in"));
      });
      var noThk = lv.walls.filter(function (w) { return w.thicknessIn === undefined || w.thicknessIn === null; });
      if (noThk.length) {
        say("      " + noThk.length + " wall(s) declare no thickness — listed as an open item.");
      }

      say();
      say("  OPENINGS — " + lv.openings.length);
      if (!lv.openings.length) say("      (none declared)");
      else {
        say("  " + pad("ID", 8) + pad("WALL", 8) + pad("KIND", 10) + pad("OFFSET", 10) +
            pad("WIDTH", 10) + "HEAD");
        say("  " + rule("-").slice(0, W - 2));
        lv.openings.forEach(function (o) {
          say("  " + pad(o.id, 8) + pad(o.wallId, 8) + pad(o.kind, 10) +
              pad(o.offsetFt === undefined ? "—" : n2(o.offsetFt, 2) + " ft", 10) +
              pad(o.widthFt === undefined ? "—" : n2(o.widthFt, 2) + " ft", 10) +
              pad(o.headHeightFt === undefined ? "—" : n2(o.headHeightFt, 2) + " ft", 10) +
              (o.hostFound ? "" : "** NO SUCH WALL **"));
        });
      }

      say();
      say("  FRAMING REGIONS — " + lv.framing.length);
      if (!lv.framing.length) say("      (none declared)");
      else {
        say("  " + pad("ID", 8) + pad("KIND", 10) + pad("DIRECTION", 12) +
            pad("SPACING", 12) + "BEARS ON");
        say("  " + rule("-").slice(0, W - 2));
        lv.framing.forEach(function (f) {
          say("  " + pad(f.id, 8) + pad(f.kind, 10) +
              pad(f.directionDeg === undefined ? "—" : n2(f.directionDeg, 0) + "°", 12) +
              pad(f.spacingIn === undefined ? "—" : n2(f.spacingIn, 0) + " in o.c.", 12) +
              (f.bearsOn.length ? f.bearsOn.join(", ") : "** NOTHING DECLARED **"));
        });
      }
    });

    block("MEMBER MARKS ON THE PLAN");
    wrap(g.placementBasis.charAt(0).toUpperCase() + g.placementBasis.slice(1) + ".", W - 4)
      .forEach(function (x) { say("  " + x); });
    say();
    if (g.placed.length) {
      say("  PLACED — " + g.placed.length);
      say("  " + pad("MARK", 12) + pad("AT (ft)", 18) + "LOCATED BY");
      say("  " + rule("-").slice(0, W - 2));
      g.placed.forEach(function (m) {
        say("  " + pad(m.id, 12) + pad(n2(m.x, 1) + ", " + n2(m.y, 1), 18) + m.on);
        if (m.how) wrap(m.how, W - 16).forEach(function (x) { say("              " + x); });
      });
      say();
    }
    if (g.unplaced.length) {
      say("  NOT PLACED — " + g.unplaced.length + ". These marks appear in the legend only.");
      g.unplaced.forEach(function (m) {
        wrap(m.why, W - 20).forEach(function (x, i) {
          say("      " + pad(i ? "" : m.id, 12) + x);
        });
      });
      say();
      wrap("A mark is drawn on this plan only where the takeoff says which wall, opening " +
           "or framing region it came from. Nothing is placed by guessing: a member mark " +
           "sitting on a plausible-looking bay is a claim a reviewer has no way to check.", W - 4)
        .forEach(function (x) { say("  " + x); });
    }
    return L;
  }

  /* ---- S2.0 SCHEDULES ---- */

  function sheetSchedules(ctx, p, res) {
    var L = [];
    function say(s) { L.push(s === undefined ? "" : s); }
    function block(t) { say(); say(rule("-")); say(t); say(rule("-")); say(); }

    if (!res) {
      block("SCHEDULES — NOT GENERATED");
      wrap("solver.js supplied no plan result to this package (ctx.planResult), so there " +
           "is no member schedule, no header schedule and no reaction schedule. No member " +
           "on this project has been checked by this package.", W - 4)
        .forEach(function (x) { say("  " + x); });
      return L;
    }

    var r = res.rollup || {};
    block("SUMMARY");
    say("  " + pad("Marks on the plan", 32) + lpad(safe(isArr(res.marks) ? res.marks.length : "—"), 6));
    say("  " + pad("Members proposed", 32) + lpad(safe(r.solved), 6));
    say("  " + pad("Escalated — no member", 32) + lpad(safe(r.escalated), 6));
    say("  " + pad("Not this engine's member", 32) + lpad(safe(r.notApplicable), 6));
    say("  " + pad("Distinct SKUs", 32) + lpad(safe(r.skuCount), 6));
    say();
    if (r.complete === false) {
      wrap("** THIS IS NOT A COMPLETE SCHEDULE — " +
           String(safe(r.incompleteBecause, "reason not stated")).toUpperCase() + " **", W - 4)
        .forEach(function (x) { say("  " + x); });
      say("  Do not read the members below as a finished design.");
      say();
    }
    if (res.pack && res.pack.governs === "wind") {
      say("  " + rule("!").slice(0, W - 2));
      say("  !! GRAVITY ONLY — WIND GOVERNS IN THIS MARKET");
      say("  " + rule("!").slice(0, W - 2));
      wrap(safe(res.pack.governsNote, "This engine checks gravity only."), W - 4)
        .forEach(function (x) { say("  " + x); });
      say();
    }

    /* Column widths are set by the widest thing the catalog can actually
       produce — "4x12 Southern Pine Select Structural" is 36 characters — so
       the table cannot collide with itself on a plan that picks it. */
    block("MEMBER SCHEDULE");
    say("  " + pad("MARK", 12) + pad("MEMBER", 40) + pad("SPACING", 12) +
        pad("QTY", 5) + lpad("DCR", 7));
    say("  " + rule("-").slice(0, W - 2));
    res.marks.forEach(function (m) {
      var id = safe(m.mark && m.mark.id, "—");
      var qty = (m.mark && isFinite(Number(m.mark.count))) ? String(m.mark.count) : "—";
      if (m.notApplicable) {
        say("  " + pad(id, 12) + pad("— not sized —", 40) + pad("", 12) + pad(qty, 5));
        say("  " + pad("", 12) + "not this engine's member [" +
            safe(m.notApplicable.reason) + "] — see NOT SIZED, below");
        return;
      }
      var row = m.unifiedTo || (m.solution && m.solution.pick);
      if (!row) {
        var e = (FM.solver && FM.solver.escalationOf)
              ? FM.solver.escalationOf(m.solution && m.solution.status)
              : { badge: "escalate", tag: "ESCALATED", short: "" };
        say("  " + pad(id, 12) + pad("— ESCALATED: " + safe(e.badge) + " —", 40) +
            pad("", 12) + pad(qty, 5));
        wrap(safe(e.tag) + " — " + safe(e.short), W - 16)
          .forEach(function (x) { say("  " + pad("", 12) + x); });
        return;
      }
      say("  " + pad(id, 12) +
          pad(safe(row.cand.size) + " " + safe(row.cand.species) + " " + safe(row.cand.grade), 40) +
          pad(row.cand.spacing ? safe(row.cand.spacing) + "\" o.c." : "single", 12) +
          pad(qty, 5) + lpad(n2(row.dcr, 3), 7));
      wrap("governs " + safe(row.governing) + " · " + safe(m.mark.label) +
           " · span " + n2(m.mark.span, 1) + " ft" +
           (m.demand && m.demand.trib ? " · tributary " + n2(m.demand.trib, 2) + " ft" : "") +
           (m.demand ? " · bearing " + n2(m.demand.bearing, 2) + " in" : "") +
           (m.demand ? " · " + (m.demand.wet ? "wet service" : "dry") : "") +
           (m.demand && m.demand.treated ? ", treated" : "") +
           (m.demand ? (m.demand.braced ? ", braced" : ", UNBRACED") : "") +
           (m.unifiedTo ? " · RAISED FOR SKU UNIFICATION, not for capacity" : ""), W - 16)
        .forEach(function (x) { say("  " + pad("", 12) + x); });
    });

    /* ---- headers ---- */
    var hdrs = res.marks.filter(function (m) { return m.mark && m.mark.role === "header"; });
    block("HEADER SCHEDULE — " + hdrs.length + " MARK(S)");
    if (!hdrs.length) say("  No mark on this plan is a header.");
    else {
      say("  " + pad("MARK", 12) + pad("SPAN", 10) + pad("TRIB", 10) + pad("BEARING", 10) +
          "HEAD HEIGHT");
      say("  " + rule("-").slice(0, W - 2));
      hdrs.forEach(function (m) {
        var row = m.unifiedTo || (m.solution && m.solution.pick);
        var member = m.notApplicable ? "— not sized (" + safe(m.notApplicable.reason) + ") —"
                   : (row ? safe(row.cand.size) + " " + safe(row.cand.species) + " " + safe(row.cand.grade)
                          : "— ESCALATED, no member —");
        say("  " + pad(safe(m.mark.id), 12) +
            pad(n2(m.mark.span, 2) + " ft", 10) +
            pad(m.mark.trib === undefined ? "—" : n2(m.mark.trib, 2) + " ft", 10) +
            pad(m.mark.bearing === undefined ? "—" : n2(m.mark.bearing, 2) + " in", 10) +
            (m.mark.headHeightIn === undefined ? "—" : n2(m.mark.headHeightIn, 0) + " in"));
        wrap("→ " + member, W - 16).forEach(function (x) { say("  " + pad("", 12) + x); });
      });
      say();
      wrap("Bearing is the declared jack-stud length, and it is a DESIGN INPUT on a header " +
           "— it governs the check often enough that a silent default produced false " +
           "escalations. Head height is what limits the depth available.", W - 4)
        .forEach(function (x) { say("  " + x); });
    }

    /* ---- reactions ---- */
    block("REACTION SCHEDULE");
    say("  Unreduced support reaction at each bearing, governing gravity combination.");
    say("  The §3.4.3.1 shear reduction is a shear allowance and is never applied to a");
    say("  reaction. NO CONNECTION IS DESIGNED HERE (calc-spec §8 item 17).");
    say();
    say("  " + pad("MARK", 12) + pad("REACTION", 14) + "GOVERNING COMBINATION");
    say("  " + rule("-").slice(0, W - 2));
    var anyRx = false;
    res.marks.forEach(function (m) {
      var rx = m.solution && m.solution.reactions;
      if (!rx || !isFinite(Number(rx.perBearingLb))) return;
      anyRx = true;
      say("  " + pad(safe(m.mark.id), 12) + pad(comma(rx.perBearingLb) + " lb", 14) + safe(rx.combo));
    });
    if (!anyRx) say("  No mark on this plan published a reaction.");
    /* borrowed reactions — a post's design load is the beam's end reaction */
    res.marks.forEach(function (m) {
      var borrowed = m.notApplicable && m.notApplicable.reactions;
      if (!borrowed || !borrowed.length) return;
      say();
      say("  " + safe(m.mark.id) + " — design load borrowed from the member above it:");
      borrowed.forEach(function (rx) {
        wrap("from " + safe(rx.id) + ": " +
             (rx.perBearingLb === null || !isFinite(Number(rx.perBearingLb))
               ? "NO REACTION PUBLISHED — " + safe(rx.why, "not computed")
               : comma(rx.perBearingLb) + " lb per bearing" +
                 (rx.combo ? "  (" + safe(rx.combo) + ")" : "")), W - 10)
          .forEach(function (x, i) { say("      " + (i ? "  " : "") + x); });
      });
    });

    /* ---- what has no member ---- */
    var esc = res.marks.filter(function (m) { return !m.notApplicable && m.solution && !m.solution.pick; });
    if (esc.length) {
      var byReason = {};
      esc.forEach(function (m) {
        var k = safe(m.solution.status, "escalate");
        if (!own(byReason, k)) byReason[k] = [];
        byReason[k].push(m);
      });
      var reasons = Object.keys(byReason).sort();
      block("ESCALATIONS — " + esc.length + " MARK(S) HAVE NO MEMBER, IN " +
            reasons.length + " CATEGOR" + (reasons.length === 1 ? "Y" : "IES"));
      reasons.forEach(function (k) {
        var e = FM.solver && FM.solver.escalationOf ? FM.solver.escalationOf(k) : { tag: k, short: "" };
        var head = byReason[k].length + " × " + safe(e.tag);
        wrap(safe(e.short), W - 38).forEach(function (x, i) {
          say("  " + pad(i ? "" : head, 34) + x);
        });
      });
      if (reasons.length > 1) {
        say();
        wrap("These are not the same finding. A procurement escalation names a member that " +
             "was run through the engine and passed; a strength escalation means no section " +
             "in the ladder passes at all. Read the category before the mark.", W - 4)
          .forEach(function (x) { say("  " + x); });
      }
      say();
      esc.forEach(function (m) {
        var s = m.solution;
        var ei = FM.solver && FM.solver.escalationOf ? FM.solver.escalationOf(s.status) : { tag: safe(s.status) };
        wrap(safe(m.mark.id) + " — " + safe(m.mark.label) + "   [" + safe(ei.tag) + "]", W - 4)
          .forEach(function (x, i) { say("  " + (i ? "    " : "") + x); });
        if (s.note && s.note.wall) wrap("wall : " + safe(s.note.wall), W - 10).forEach(function (x) { say("      " + x); });
        if (s.note && s.note.move) wrap("next : " + safe(s.note.move), W - 10).forEach(function (x) { say("      " + x); });
        say();
      });
    }

    var na = res.marks.filter(function (m) { return m.notApplicable; });
    if (na.length) {
      block("NOT SIZED — " + na.length + " MARK(S) ARE NOT THIS ENGINE'S MEMBER");
      say("  Carried deliberately. A schedule that omits them reads as if they were fine.");
      say();
      na.forEach(function (m) {
        wrap(safe(m.mark.id) + " — " + safe(m.mark.label) +
             "   [" + safe(m.notApplicable.reason) + "]", W - 4)
          .forEach(function (x, i) { say("  " + (i ? "    " : "") + x); });
        wrap(safe(m.notApplicable.note), W - 8).forEach(function (x) { say("      " + x); });
        say();
      });
    }
    return L;
  }

  /* ---- S3.0 CALCULATIONS ---- */

  function sheetCalcs(ctx, p, res) {
    var L = [];
    function say(s) { L.push(s === undefined ? "" : s); }
    function block(t) { say(); say(rule("-")); say(t); say(rule("-")); say(); }

    if (!res) {
      block("CALCULATIONS — NOT GENERATED");
      wrap("solver.js supplied no plan result (ctx.planResult), so no member was checked " +
           "and there is no calculation to show. This sheet is empty of engineering.", W - 4)
        .forEach(function (x) { say("  " + x); });
      return L;
    }
    if (!p.engine) {
      block("CALCULATIONS — NOT AVAILABLE");
      wrap("engine.js is not loaded, so the check behind each member on S2.0 cannot be " +
           "reproduced here. A schedule whose calculations cannot be shown is not " +
           "reviewable — do not accept the members on S2.0 without this sheet.", W - 4)
        .forEach(function (x) { say("  " + x); });
      return L;
    }

    block("HOW TO READ THIS SHEET");
    wrap("One block per mark that has a member, showing the engine's own working: the " +
         "inputs it was given, every limit state it evaluated with the numbers in the " +
         "equation, and the combination that governed. Every DCR on S2.0 is the governing " +
         "line of the block below it. A mark with no member has no calculation, and says " +
         "so rather than being omitted.", W - 4).forEach(function (x) { say("  " + x); });
    say();
    say("  Basis: NDS 2024 ASD · ASCE 7 §2.4 gravity combinations · IBC Table 1604.3 rows");
    say("  (see S0.1 G3 for what the deflection rows are and are not).");

    res.marks.forEach(function (m) {
      var id = safe(m.mark && m.mark.id, "—");
      say();
      say(rule("="));
      wrap("MARK " + id + " — " + safe(m.mark && m.mark.label), W)
        .forEach(function (x, i) { say(i ? "     " + x : x); });
      say(rule("="));

      if (m.notApplicable) {
        say("  NOT CHECKED — [" + safe(m.notApplicable.reason) + "]");
        wrap(safe(m.notApplicable.note), W - 6).forEach(function (x) { say("      " + x); });
        return;
      }
      var row = m.solution && m.solution.pick;
      if (!row) {
        var e = FM.solver && FM.solver.escalationOf ? FM.solver.escalationOf(m.solution && m.solution.status)
              : { tag: "ESCALATED", short: "" };
        wrap("NO MEMBER — [" + safe(e.tag) + "] " + safe(e.short), W - 4)
          .forEach(function (x, i) { say("  " + (i ? "  " : "") + x); });
        say("  There is no calculation for this mark because nothing was selected for it.");
        if (m.solution && m.solution.note && m.solution.note.wall) {
          wrap("wall: " + safe(m.solution.note.wall), W - 6).forEach(function (x) { say("      " + x); });
        }
        return;
      }

      var inputs = row.inputs;
      var r = null;
      try { r = inputs ? FM.engine.run(inputs) : null; } catch (err) { r = null; }
      if (!r || r.error) {
        say("  THE CHECK COULD NOT BE REPRODUCED ON THIS SHEET" +
            (r && r.message ? " — " + safe(r.message) : "") + ".");
        say("  Do not accept the member on S2.0 for this mark until it can be.");
        return;
      }

      say("  Member    : " + safe(row.cand.size) + " " + safe(row.cand.species) + " " +
          safe(row.cand.grade) + (row.cand.spacing ? " @ " + safe(row.cand.spacing) + " in o.c." : " (single)"));
      say("  Span      : " + n2(m.mark.span, 2) + " ft" +
          (m.demand && m.demand.trib ? "   tributary " + n2(m.demand.trib, 2) + " ft" : "") +
          (m.demand ? "   bearing " + n2(m.demand.bearing, 2) + " in" : ""));
      say("  Loads     : dead " + n2(inputs.dead, 2) + " psf · live " + n2(inputs.live, 2) +
          " psf · roof " + n2(inputs.roofLoad, 2) + " psf (" + safe(inputs.roofType) + ")");
      say("  Service   : " + (inputs.wet ? "wet" : "dry") +
          (inputs.incised ? ", incised" : "") + (inputs.braced ? ", braced" : ", UNBRACED") +
          "   C_F " + safe(inputs.CF));
      wrap(safe(r.basis), W - 16).forEach(function (x, i) {
        say("  " + pad(i ? "" : "Basis", 10) + (i ? "  " : ": ") + x);
      });
      say();
      (isArr(r.checks) ? r.checks : []).forEach(function (c) {
        say("  " + String(safe(c.name)).toUpperCase() +
            (c.combo ? "   [" + safe(c.combo) + "]" : ""));
        (isArr(c.lines) ? c.lines : []).forEach(function (ln) {
          wrap(plain(ln), W - 8).forEach(function (x, i) { say("      " + (i ? "  " : "") + x); });
        });
        say("      DCR = " + n2(c.dcr, 3) + (Number(c.dcr) <= 1 ? "   OK" : "   NG"));
        say();
      });
      if (r.governing) {
        say("  GOVERNING : " + safe(r.governing.name) + " · DCR " + n2(r.governing.dcr, 3) +
            " · combination " + safe(r.governing.combo));
      }
      if (isArr(row.warnings) && row.warnings.length) {
        row.warnings.forEach(function (wn) {
          wrap("WARNING — " + safe(wn && wn.text ? wn.text : wn), W - 6).forEach(function (x) { say("  " + x); });
        });
      }
    });

    say();
    say(rule("-"));
    wrap("These calculations are reproducible: every one of them re-runs from the inputs " +
         "printed in its own block. They are not, and cannot be made into, a sealed " +
         "design — see the footer of this sheet and S0.1.", W - 2).forEach(function (x) { say("  " + x); });
    return L;
  }

  /* ---- S4.0 BILL OF MATERIALS ---- */

  function sheetBom(ctx, p, res) {
    var L = [];
    function say(s) { L.push(s === undefined ? "" : s); }
    function block(t) { say(); say(rule("-")); say(t); say(rule("-")); say(); }
    var bom = p.have.bom;

    if (!bom) {
      block("BILL OF MATERIALS — NOT GENERATED");
      wrap("bom.js supplied no bill of materials to this package (ctx.bom). There are no " +
           "quantities, no lengths, no waste policy, no prices — and, the half that " +
           "matters, no list of what a bill of materials would EXCLUDE.", W - 4)
        .forEach(function (x) { say("  " + x); });
      say();
      wrap("Nothing on this sheet may be used to order material. What follows is the " +
           "solver's SKU rollup — a count of members it proposed — printed so the sheet " +
           "is not silently blank. It has no lengths, no stock lengths, no waste, no cull " +
           "and no price basis, and it omits every mark that escalated or was not sized.", W - 4)
        .forEach(function (x) { say("  " + x); });
      if (res && res.rollup && res.rollup.skus) {
        say();
        say("  NOT A BILL OF MATERIALS — member counts only");
        say("  " + rule("-").slice(0, W - 2));
        var keys = Object.keys(res.rollup.skus).sort();
        if (!keys.length) say("      (the solver proposed no member at all)");
        keys.forEach(function (k) { say("      " + lpad(safe(res.rollup.skus[k]), 5) + "  " + k); });
        say();
        say("  Marks NOT represented above: " + safe(res.rollup.escalated, "0") +
            " escalated, " + safe(res.rollup.notApplicable, "0") + " not this engine's member.");
      }
      return L;
    }

    block("BILL OF MATERIALS");
    var lines = isArr(bom.lines) ? bom.lines : null;
    if (!lines) {
      say("  ** The bill of materials supplied carries no `lines` array. Nothing can be");
      say("     listed here. **");
    } else {
      say("  " + pad("SKU", 22) + pad("SIZE/SPECIES", 24) + pad("PCS", 6) +
          pad("LENGTH", 9) + lpad("EXT", 10));
      say("  " + rule("-").slice(0, W - 2));
      lines.forEach(function (ln) {
        say("  " + pad(safe(ln.sku), 22) +
            pad(safe(ln.size) + " " + safe(ln.species, "") + " " + safe(ln.grade, ""), 24) +
            pad(safe(ln.piecesPerHouse), 6) +
            pad(ln.lengthFt === undefined ? "—" : n2(ln.lengthFt, 1) + " ft", 9) +
            lpad(usd(ln.extUSD), 10));
        var sub = [];
        if (ln.treatment) sub.push("treatment " + safe(ln.treatment));
        if (ln.stockLengthFt !== undefined) sub.push("stock " + n2(ln.stockLengthFt, 1) + " ft");
        if (ln.bf !== undefined) sub.push(n2(ln.bf, 1) + " bf");
        if (isArr(ln.marks) && ln.marks.length) sub.push("marks " + ln.marks.map(function (x) { return safe(x); }).join(", "));
        if (ln.cls) sub.push("[" + clsOf(ln.cls) + "]");
        if (sub.length) wrap(sub.join(" · "), W - 8).forEach(function (x) { say("      " + x); });
        if (ln.basis) wrap("basis: " + safe(ln.basis), W - 8).forEach(function (x) { say("      " + x); });
      });
    }

    if (bom.totals) {
      say();
      say("  TOTALS");
      say("      " + pad("Board feet", 20) + comma(bom.totals.bf));
      say("      " + pad("Pieces", 20) + comma(bom.totals.pieces));
      say("      " + pad("Modelled cost", 20) + usd(bom.totals.usd) +
          "   [market placeholders — no code standing]");
      if (bom.totals.byCategory && typeof bom.totals.byCategory === "object") {
        Object.keys(bom.totals.byCategory).forEach(function (k) {
          say("      " + pad("  " + k, 20) + safe(bom.totals.byCategory[k]));
        });
      }
    }
    if (bom.waste) {
      say();
      say("  WASTE POLICY : " + safe(bom.waste.policy) + " · applied " +
          (bom.waste.appliedPct === undefined ? "—" : n2(bom.waste.appliedPct, 1) + "%"));
      if (bom.waste.basis) wrap("basis: " + safe(bom.waste.basis), W - 8).forEach(function (x) { say("      " + x); });
    }
    if (bom.perLot || bom.perCommunity) {
      say();
      say("  SCALED QUANTITIES");
      if (bom.perLot) say("      per lot       : " + safe(bom.perLot.usd !== undefined ? usd(bom.perLot.usd) : bom.perLot, "supplied"));
      if (bom.perCommunity) say("      per community : " + safe(bom.perCommunity.usd !== undefined ? usd(bom.perCommunity.usd) : bom.perCommunity, "supplied"));
    }

    block("WHAT THIS BILL OF MATERIALS DOES NOT CONTAIN");
    var exc = isArr(bom.excluded) ? bom.excluded : null;
    if (!exc) {
      say("  ** THE EXCLUSION LIST IS MISSING. The contract requires it: anything the calc");
      say("     stack does not size must be listed as absent, with a reason. Without it,");
      say("     this reads as a complete order and it is not one. **");
    } else if (!exc.length) {
      say("  ** The exclusion list is EMPTY. Nothing in this system produces a complete");
      say("     material order — connectors, hardware, sheathing and fasteners are not");
      say("     sized anywhere — so an empty exclusion list is a defect, not a clean bill. **");
    } else {
      exc.forEach(function (x) {
        say("  · " + safe(x.what, "(unnamed)"));
        wrap(safe(x.why, "no reason given"), W - 8).forEach(function (y) { say("      " + y); });
      });
    }
    say();
    wrap("Quantities are DERIVED from the schedule and the plan's counts. Prices are " +
         "MARKET placeholders with no code standing — they rank members that already " +
         "passed and they cannot make a member pass.", W - 4).forEach(function (x) { say("  " + x); });
    return L;
  }

  /* ---- S5.0 OPEN ITEMS ---- */

  function sheetOpen(ctx, p, res, items) {
    var L = [];
    function say(s) { L.push(s === undefined ? "" : s); }
    function block(t) { say(); say(rule("-")); say(t); say(rule("-")); say(); }

    var standing = items.filter(function (i) { return i.group === "STANDING"; }).length;
    block("OPEN ITEMS — " + items.length);
    wrap("Everything unresolved, escalated, excluded, unverified or unapproved, collected " +
         "from every stage of the work behind this package. " + standing + " of them are " +
         "STANDING items: no package this system produces can close them, and they print " +
         "on every set. This sheet is never empty, because a package reporting zero open " +
         "items would be claiming a completeness this system cannot have.", W - 4)
      .forEach(function (x) { say("  " + x); });

    var groups = [], seen = {};
    items.forEach(function (i) {
      if (own(seen, " " + i.group)) return;
      seen[" " + i.group] = true;
      groups.push(i.group);
    });

    var n = 0;
    var field = fielder(say, 8, 5);
    groups.forEach(function (gname) {
      var mine = items.filter(function (i) { return i.group === gname; });
      block(gname + " — " + mine.length);
      mine.forEach(function (it) {
        n++;
        wrap(safe(it.what), W - 10).forEach(function (x, i) {
          say("  " + pad(i ? "" : "[" + n + "]", 6) + x);
        });
        if (it.why) field("why", safe(it.why));
        if (it.need) field("close", safe(it.need));
        say();
      });
    });

    say(rule("-"));
    wrap("An open item is not a defect in the package — it is the package being honest " +
         "about what it is. The list above is what the reviewing engineer inherits, and " +
         "the standing items at the top of it are inherited on every project this system " +
         "will ever produce.", W - 2).forEach(function (x) { say("  " + x); });
    return L;
  }

  /* ============================================================
     BUILD
     ============================================================ */

  function build(ctx) {
    ctx = ctx || {};
    var p = probe(ctx);
    var res = p.have.planResult;
    var plan = res ? res.plan : (ctx.plan || null);
    var pack = res ? res.pack : (ctx.pack || null);

    var at = str(ctx.at) || (function () {
      try { return new Date().toISOString().slice(0, 16).replace("T", " ") + " UTC"; }
      catch (e) { return "generation time not available"; }
    })();

    var pkg = {
      ctx: ctx,
      probe: p,
      missing: p.missing,
      head: {
        project: plan ? safe(plan.name) + " — " + safe(plan.summary) : "NOT SUPPLIED",
        region: pack ? safe(pack.name) + " · " + safe(pack.markets) : "NOT SUPPLIED",
        packageId: (plan ? safe(plan.id) : "no-plan") + " / " + (pack ? safe(pack.id) : "no-region"),
        at: at
      },
      sheets: []
    };

    /* geometry once, shared by the text form and the drawn form */
    var g = geometry(p.have.model, p.have.takeoff, p.cad);
    if (g.ok) {
      var ids = [];
      if (res && isArr(res.marks)) res.marks.forEach(function (m) { if (m.mark) ids.push(safe(m.mark.id)); });
      else if (p.have.takeoff && isArr(p.have.takeoff.marks)) {
        p.have.takeoff.marks.forEach(function (m) { ids.push(safe(m.id)); });
      }
      placeMarks(g, ids, p.have.takeoff);
    }
    pkg.geometry = g;

    var items = collectOpen(ctx, p, res);
    pkg.openItems = items;

    var defs = [
      { no: "S0.0", title: "Cover", kind: "cover",
        note: "project, jurisdiction, design criteria, EMPTY seal block, approval trail",
        lines: function () { return sheetCover(ctx, p, res, pkg); } },
      { no: "S0.1", title: "General notes", kind: "notes",
        note: "status of the package, what is deferred to others, calc-spec §8 in full",
        lines: function () { return sheetNotes(ctx, p, res); } },
      { no: "S1.0", title: "Framing plan", kind: "plan",
        note: p.have.model ? "geometry, member marks, north arrow, scale bar, legend"
                           : "NO MODEL SUPPLIED — see the sheet",
        lines: function () { return sheetFraming(ctx, p, res, g); } },
      { no: "S2.0", title: "Schedules", kind: "schedules",
        note: res ? "member, header and reaction schedules; escalations; marks not sized"
                  : "NOT GENERATED — no solver result",
        lines: function () { return sheetSchedules(ctx, p, res); } },
      { no: "S3.0", title: "Calculations", kind: "calcs",
        note: res ? "the engine's working, mark by mark, reproducible from its own inputs"
                  : "NOT GENERATED — no solver result",
        lines: function () { return sheetCalcs(ctx, p, res); } },
      { no: "S4.0", title: "Bill of materials", kind: "bom",
        note: p.have.bom ? "quantities, totals, waste policy, and what is EXCLUDED"
                         : "NOT GENERATED — bom.js supplied nothing",
        lines: function () { return sheetBom(ctx, p, res); } },
      { no: "S5.0", title: "Open items", kind: "open",
        note: items.length + " item(s) — never empty, by construction",
        lines: function () { return sheetOpen(ctx, p, res, items); } }
    ];

    defs.forEach(function (d, i) {
      var sheet = {
        no: d.no, title: d.title, kind: d.kind, seq: i + 1,
        indexNote: d.note,
        body: null,
        lines: function () {
          /* trailing spaces are invisible on screen and land in the exported
             text file, where a diff of two packages reports a change that is
             not one */
          if (!this.body) {
            this.body = d.lines().map(function (x) {
              return String(x === undefined ? "" : x).replace(/[ \t]+$/, "");
            });
          }
          return this.body;
        }
      };
      sheet.text = function () { return sheetFrame(pkg, sheet, sheet.lines()).join("\n"); };
      sheet.render = function (host) { return renderSheet(host, pkg, sheet); };
      pkg.sheets.push(sheet);
    });

    pkg.text = function () { return packageText(pkg); };
    pkg.sheetByNo = function (no) {
      var hit = null;
      pkg.sheets.forEach(function (s) { if (s.no === no) hit = s; });
      return hit;
    };
    return pkg;
  }

  function packageText(pkg) {
    var L = [];
    L.push(rule("="));
    L.push("FIRMARK — PLAN SET PREPARED FOR PE REVIEW");
    L.push(rule("="));
    var f = fielder(function (x) { L.push(x); }, 0, 9);
    f("Project", pkg.head.project);
    f("Region", pkg.head.region);
    f("Package", pkg.head.packageId);
    f("Prepared", pkg.head.at);
    f("Sheets", String(pkg.sheets.length));
    L.push("");
    wrap(NOT_SEALED, W).forEach(function (x) { L.push(x); });
    L.push("");
    SEAL_LINES.forEach(function (x) { L.push(x); });
    L.push("");
    L.push(rule("-"));
    pkg.sheets.forEach(function (s) {
      wrap(s.indexNote, W - 34).forEach(function (x, i) {
        L.push(pad(i ? "" : s.no, 8) + pad(i ? "" : s.title, 26) + x);
      });
    });
    L.push(rule("-"));
    pkg.sheets.forEach(function (s) {
      L.push("");
      L.push("");
      sheetFrame(pkg, s, s.lines()).forEach(function (x) { L.push(x); });
    });
    L.push("");
    L.push(rule("="));
    L.push("END OF PACKAGE — " + pkg.head.packageId + " · " + pkg.sheets.length + " sheets");
    L.push("PREPARED FOR PE REVIEW. NOT SEALED ENGINEERING.");
    L.push(rule("="));
    return L.join("\n");
  }

  function text(pkg) {
    if (!pkg) return "";
    if (typeof pkg.text === "function" && pkg.sheets) return packageText(pkg);
    return "";
  }

  /* ============================================================
     THE DRAWN FORM

     Everything below this line touches the DOM and is skipped
     entirely in the headless harness. Nothing above it does.
     ============================================================ */

  var SVGNS = "http://www.w3.org/2000/svg";
  function svg(tag, attrs, kids) {
    var n = document.createElementNS(SVGNS, tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (attrs[k] === null || attrs[k] === undefined) return;
      if (k === "text") n.textContent = attrs[k];
      else n.setAttribute(k, attrs[k]);
    });
    (kids || []).forEach(function (c) { if (c) n.appendChild(c); });
    return n;
  }

  /* Print rules live here rather than in app.css: this is the only view in the
     product that is meant to come out of a printer, and app.css is not this
     file's to edit. Injected once, marked, idempotent. */
  var PRINT_CSS =
    "@media print {" +
    "  .rail, .topbar, .scrim, .palette-scrim, .toast, .skip, .beta-strip," +
    "  .fm-ps-nav, .page-head-actions { display: none !important; }" +
    "  .main, .main-inner, .shell { display: block !important; padding: 0 !important;" +
    "    margin: 0 !important; overflow: visible !important; }" +
    "  .fm-ps-sheet { page-break-after: always; break-after: page; border: none !important; }" +
    "  .fm-ps-sheet:last-child { page-break-after: auto; break-after: auto; }" +
    "  .fm-ps-foot { border-top: 1pt solid #000; }" +
    "  .fm-ps-pre { font-size: 8pt; line-height: 1.25; white-space: pre-wrap; }" +
    "  * { color: #000 !important; background: #fff !important; }" +
    "}" +
    ".fm-ps-pre { font-family: var(--mono, monospace); font-size: .74rem; line-height: 1.42;" +
    "  white-space: pre; overflow-x: auto; margin: 0; }" +
    ".fm-ps-sheet { border: 1px solid var(--line, #ccc); border-radius: 6px; padding: 16px;" +
    "  margin-bottom: 18px; }" +
    ".fm-ps-head { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;" +
    "  border-bottom: 1px solid var(--line, #ccc); padding-bottom: 8px; margin-bottom: 12px; }" +
    ".fm-ps-no { font-family: var(--mono, monospace); font-weight: 700; font-size: 1.1rem; }" +
    ".fm-ps-foot { margin-top: 14px; padding-top: 8px; border-top: 1px solid var(--line, #ccc);" +
    "  font-size: .76rem; }" +
    ".fm-ps-seal { border: 2px solid currentColor; padding: 18px; margin: 10px 0;" +
    "  min-height: 150px; }" +
    ".fm-ps-nav { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 14px; }";

  function ensurePrintCss() {
    if (typeof document === "undefined") return;
    if (document.getElementById("fm-planset-css")) return;
    var s = document.createElement("style");
    s.id = "fm-planset-css";
    s.textContent = PRINT_CSS;
    document.head.appendChild(s);
  }

  function el(tag, attrs, kids) {
    if (FM.el) return FM.el(tag, attrs, kids);
    var n = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === "class") n.className = attrs[k];
      else if (k === "text") n.textContent = attrs[k];
      else if (k.slice(0, 2) === "on") n.addEventListener(k.slice(2), attrs[k]);
      else if (attrs[k] !== null && attrs[k] !== undefined) n.setAttribute(k, attrs[k]);
    });
    (kids || []).forEach(function (c) { if (c) n.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
    return n;
  }

  function sheetHeadDom(pkg, sheet) {
    return el("div", { class: "fm-ps-head" }, [
      el("span", { class: "fm-ps-no", text: sheet.no }),
      el("span", { class: "card-title", text: sheet.title }),
      el("span", { class: "clause", text: pkg.head.packageId + " · " + pkg.head.at +
        " · sheet " + sheet.seq + " of " + pkg.sheets.length })
    ]);
  }

  function sheetFootDom() {
    return el("div", { class: "fm-ps-foot" }, [
      el("strong", { text: "Prepared for PE review — not sealed engineering. " }),
      el("span", { text: "No seal is applied by this software. The seal block on S0.0 is " +
        "empty and is to be completed by the licensed engineer who reviews this package " +
        "and takes responsibility for it." })
    ]);
  }

  /* the framing plan, drawn */
  function planSvg(g) {
    var wrapEl = el("div", { style: "overflow-x:auto" });
    if (!g || !g.ok) return null;
    var M = 46, SW = 720;
    var ftW = Math.max(1, g.bounds.wFt), ftH = Math.max(1, g.bounds.hFt);
    var s = (SW - 2 * M) / ftW;
    var SH = ftH * s + 2 * M + 54;
    function X(x) { return M + (x - g.bounds.minX) * s; }
    function Y(y) { return (SH - 54) - M - (y - g.bounds.minY) * s; }

    var kids = [];
    kids.push(svg("rect", { x: 0, y: 0, width: SW, height: SH, fill: "none" }));

    g.levels.forEach(function (lv) {
      lv.framing.forEach(function (f) {
        if (f.polygon.length < 3) return;
        kids.push(svg("polygon", {
          points: f.polygon.map(function (p) { return X(p[0]) + "," + Y(p[1]); }).join(" "),
          fill: "currentColor", "fill-opacity": ".06",
          stroke: "currentColor", "stroke-opacity": ".35", "stroke-dasharray": "4 3"
        }));
        if (f.at) {
          kids.push(svg("text", { x: X(f.at.x), y: Y(f.at.y) - 4, "text-anchor": "middle",
            "font-size": "10", fill: "currentColor", "fill-opacity": ".7",
            text: f.id + " · " + f.kind }));
          kids.push(svg("text", { x: X(f.at.x), y: Y(f.at.y) + 8, "text-anchor": "middle",
            "font-size": "9", fill: "currentColor", "fill-opacity": ".55",
            text: (f.spacingIn === undefined ? "spacing —" : f.spacingIn + " in o.c.") +
                  " · " + (f.directionDeg === undefined ? "dir —" : f.directionDeg + "°") }));
        }
      });
      lv.walls.forEach(function (w) {
        if (!w.drawable) return;
        kids.push(svg("line", {
          x1: X(w.x1), y1: Y(w.y1), x2: X(w.x2), y2: Y(w.y2),
          stroke: "currentColor", "stroke-width": w.bearing ? 4 : 1.6,
          "stroke-opacity": w.exterior ? 1 : 0.55,
          "stroke-linecap": "square"
        }));
      });
      lv.openings.forEach(function (o) {
        if (!o.at) return;
        kids.push(svg("circle", { cx: X(o.at.x), cy: Y(o.at.y), r: 4,
          fill: "var(--bg, #fff)", stroke: "currentColor", "stroke-width": 1.4 }));
      });
    });

    /* marks, only where the takeoff located them */
    g.placed.forEach(function (m) {
      kids.push(svg("rect", { x: X(m.x) - 22, y: Y(m.y) - 9, width: 44, height: 18, rx: 3,
        fill: "var(--bg, #fff)", stroke: "currentColor", "stroke-width": 1.2 }));
      kids.push(svg("text", { x: X(m.x), y: Y(m.y) + 4, "text-anchor": "middle",
        "font-size": "10", "font-weight": "700", fill: "currentColor", text: m.id }));
    });

    /* north arrow — declared as an ASSUMPTION, never as a fact */
    var nx = SW - 30, ny = M + 6;
    kids.push(svg("line", { x1: nx, y1: ny + 26, x2: nx, y2: ny, stroke: "currentColor", "stroke-width": 1.6 }));
    kids.push(svg("polygon", { points: (nx - 5) + "," + (ny + 8) + " " + nx + "," + (ny - 4) + " " + (nx + 5) + "," + (ny + 8),
      fill: "currentColor" }));
    kids.push(svg("text", { x: nx, y: ny + 40, "text-anchor": "middle", "font-size": "10",
      fill: "currentColor", text: "N (assumed)" }));

    /* scale bar — genuinely derived from the model's own feet */
    var target = ftW / 5, step = 1;
    [1, 2, 5, 10, 20, 25, 50, 100].forEach(function (v) { if (v <= target) step = v; });
    var y0 = SH - 30, x0 = M;
    kids.push(svg("line", { x1: x0, y1: y0, x2: x0 + step * s, y2: y0, stroke: "currentColor", "stroke-width": 2 }));
    kids.push(svg("line", { x1: x0, y1: y0 - 4, x2: x0, y2: y0 + 4, stroke: "currentColor", "stroke-width": 2 }));
    kids.push(svg("line", { x1: x0 + step * s, y1: y0 - 4, x2: x0 + step * s, y2: y0 + 4,
      stroke: "currentColor", "stroke-width": 2 }));
    kids.push(svg("text", { x: x0, y: y0 + 18, "font-size": "10", fill: "currentColor",
      text: "0" }));
    kids.push(svg("text", { x: x0 + step * s, y: y0 + 18, "text-anchor": "middle", "font-size": "10",
      fill: "currentColor", text: step + " ft" }));

    var node = svg("svg", {
      viewBox: "0 0 " + Math.round(SW) + " " + Math.round(SH),
      width: "100%", role: "img",
      "aria-label": "Framing plan: " + g.levels.length + " level(s), " +
        g.placed.length + " mark(s) placed, " + g.unplaced.length + " not placed"
    }, kids);
    wrapEl.appendChild(node);
    return wrapEl;
  }

  function legendDom(g) {
    var rows = [
      ["heavy line", "bearing wall"],
      ["light line", "non-bearing wall (lighter still = interior)"],
      ["open circle", "opening, at its centre on the host wall"],
      ["dashed region", "framed region, labelled with its spacing and direction"],
      ["boxed label", "member mark, placed ONLY where the takeoff located it"],
      ["N arrow", "ASSUMED plan north (+y). The model declares no true-north bearing."]
    ];
    var body = el("div", { class: "dl" });
    rows.forEach(function (r) {
      body.appendChild(el("div", { class: "dl-row" }, [
        el("span", { class: "dl-k", text: r[0] }),
        el("span", { class: "dl-v", text: r[1] })
      ]));
    });
    if (g && g.unplaced && g.unplaced.length) {
      body.appendChild(el("div", { class: "dl-row" }, [
        el("span", { class: "dl-k", text: "not placed" }),
        el("span", { class: "dl-v", text: g.unplaced.map(function (m) { return m.id; }).join(", ") })
      ]));
    }
    return FM.card ? FM.card("Legend", null, body) : body;
  }

  function sealDom() {
    var box = el("div", { class: "fm-ps-seal" }, [
      el("div", { class: "eyebrow", text: "Engineer of record — seal and signature" }),
      el("div", { style: "height:70px" }),
      el("p", { style: "margin:0 0 6px", text: SEAL_LINES[0] + " " + SEAL_LINES[1] }),
      el("p", { style: "margin:0 0 10px", text: SEAL_LINES[2] }),
      el("p", { class: "clause", style: "margin:0", text:
        "This block is empty because this software does not seal, sign or approve " +
        "engineering. It is completed by the licensed engineer who reviews this package, " +
        "under their own licence and liability." })
    ]);
    return box;
  }

  function renderSheet(host, pkg, sheet) {
    ensurePrintCss();
    var wrapEl = el("div", { class: "fm-ps-sheet" });
    wrapEl.appendChild(sheetHeadDom(pkg, sheet));

    if (sheet.kind === "cover") {
      wrapEl.appendChild(el("div", { class: "banner banner-gold" }, [
        el("strong", { text: "Prepared for PE review — " }),
        el("span", { text: "the seal block below is intentionally empty. This software " +
          "never seals, signs or approves a design." })
      ]));
      wrapEl.appendChild(sealDom());
    }
    if (sheet.kind === "plan" && pkg.geometry && pkg.geometry.ok) {
      var art = planSvg(pkg.geometry);
      if (art) wrapEl.appendChild(art);
      wrapEl.appendChild(legendDom(pkg.geometry));
    }
    if (sheet.kind === "open") {
      wrapEl.appendChild(el("div", { class: "banner banner-warn" }, [
        el("strong", { text: pkg.openItems.length + " open item(s) — " }),
        el("span", { text: "this sheet is never empty. A package reporting none would be " +
          "claiming a completeness this system cannot have." })
      ]));
    }

    wrapEl.appendChild(el("pre", { class: "fm-ps-pre", text: sheet.lines().join("\n") }));
    wrapEl.appendChild(sheetFootDom());
    host.appendChild(wrapEl);
    return wrapEl;
  }

  function render(host, pkg) {
    if (!host || !pkg) return;
    ensurePrintCss();
    pkg.sheets.forEach(function (s) { renderSheet(host, pkg, s); });
  }

  function download(t, filename) {
    var blob = new Blob([t], { type: "text/plain" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
  }

  /* ---------------- the screen view ---------------- */

  var viewState = null;
  function vstate() {
    if (viewState) return viewState;
    var plan = FM.weights && FM.weights.PLANS && FM.weights.PLANS[0];
    var pack = FM.weights && FM.weights.PACKS && FM.weights.PACKS[0];
    viewState = { planId: plan ? plan.id : null, packId: pack ? pack.id : null, sheet: "S0.0" };
    return viewState;
  }

  function ctxFromState(s) {
    var plan = FM.weights && FM.weights.planById ? FM.weights.planById(s.planId) : null;
    var pack = FM.weights && FM.weights.packById ? FM.weights.packById(s.packId) : null;
    var res = null;
    if (plan && pack && FM.solver && FM.solver.solvePlan) {
      try { res = FM.solver.solvePlan(plan, pack); } catch (e) { res = null; }
    }
    /* Every one of these is read defensively: the module may not be loaded in
       this build, and the package must say so rather than fail to open. */
    var juris = null;
    if (FM.juris && typeof FM.juris.forSite === "function" && s.jurisId) {
      try { juris = FM.juris.forSite(s.jurisId); } catch (e) { juris = null; }
    }
    var model = null;
    if (FM.cad && typeof FM.cad.fromPlan === "function" && plan) {
      try { model = FM.cad.fromPlan(plan.id); } catch (e) { model = null; }
    }
    var takeoff = null;
    if (model && FM.takeoff && typeof FM.takeoff.run === "function") {
      try { takeoff = FM.takeoff.run(model, {}); } catch (e) { takeoff = null; }
    }
    var bom = null;
    if (res && FM.bom && typeof FM.bom.build === "function") {
      try { bom = FM.bom.build(res, {}); } catch (e) { bom = null; }
    }
    return { model: model, takeoff: takeoff, planResult: res, bom: bom,
             juris: juris, pipeline: FM.pipeline || null };
  }

  if (FM.VIEWS) {
    FM.VIEWS.planset = function (host) {
      ensurePrintCss();
      var s = vstate();
      if (!FM.weights || !FM.solver) {
        host.appendChild(FM.pageHead ? FM.pageHead("Plan set", "PE review package")
                                     : el("h1", { text: "Plan set" }));
        host.appendChild(el("div", { class: "empty", text:
          "The calculation stack failed to load, so no package can be assembled." }));
        return;
      }

      var pkg = build(ctxFromState(s));

      host.appendChild(FM.pageHead("Plan set",
        "The package a licensed engineer reviews. Not a sealed set — a set ready to be reviewed and sealed.", [
          el("button", { class: "btn", text: "Print / PDF", onclick: function () {
            if (typeof window !== "undefined" && window.print) window.print();
          } }),
          el("button", { class: "btn btn-primary", text: "Export package for PE review",
            onclick: function () {
              download(pkg.text(), "firmark-planset-" + pkg.head.packageId.replace(/[^\w.-]+/g, "-") +
                       "-for-PE-review.txt");
              if (FM.toast) FM.toast("Package exported — prepared for PE review, not sealed.");
            } })
        ]));

      host.appendChild(FM.betaStrip(
        "This software never seals anything. The seal block on S0.0 is empty and carries a " +
        "\"to be sealed by\" line for the licensed engineer who takes responsibility for the " +
        "package. Every sheet says so in its footer, and S5.0 lists what is still open."));

      var planSel = el("select", { "aria-label": "Plan" }, FM.weights.PLANS.map(function (pl) {
        return el("option", { value: pl.id, text: pl.name,
                              selected: pl.id === s.planId ? "selected" : null });
      }));
      var packSel = el("select", { "aria-label": "Region pack" }, FM.weights.PACKS.map(function (pk) {
        return el("option", { value: pk.id, text: pk.name + " · " + pk.markets,
                              selected: pk.id === s.packId ? "selected" : null });
      }));
      planSel.addEventListener("change", function () { s.planId = this.value; FM.go("planset"); });
      packSel.addEventListener("change", function () { s.packId = this.value; FM.go("planset"); });
      host.appendChild(el("div", { class: "filter-bar", style: "margin-bottom:14px" }, [planSel, packSel]));

      if (pkg.missing.length) {
        host.appendChild(el("div", { class: "banner banner-warn" }, [
          el("strong", { text: pkg.missing.length + " input(s) not available — " }),
          el("span", { text: pkg.missing.map(function (m) { return m.module; }).join(", ") +
            " supplied nothing. Each affected sheet says so in place of the content; " +
            "every one of them is an open item on S5.0." })
        ]));
      }

      var nav = el("div", { class: "fm-ps-nav" });
      var body = el("div");
      pkg.sheets.forEach(function (sh) {
        var b = el("button", {
          class: "btn btn-sm", "aria-pressed": sh.no === s.sheet ? "true" : "false",
          text: sh.no + " " + sh.title,
          onclick: function () { s.sheet = sh.no; FM.go("planset"); }
        });
        nav.appendChild(b);
      });
      nav.appendChild(el("button", {
        class: "btn btn-sm", "aria-pressed": s.sheet === "ALL" ? "true" : "false",
        text: "All sheets", onclick: function () { s.sheet = "ALL"; FM.go("planset"); }
      }));
      host.appendChild(nav);
      host.appendChild(body);

      if (s.sheet === "ALL") render(body, pkg);
      else {
        var sheet = pkg.sheetByNo(s.sheet) || pkg.sheets[0];
        renderSheet(body, pkg, sheet);
      }
    };
  }

  if (typeof FM.registerSubRoute === "function") {
    FM.registerSubRoute("planset", {
      read: function () { var s = vstate(); return [s.planId, s.packId, s.sheet]; },
      write: function (args) {
        var s = vstate();
        args = args || [];
        if (args[0] && FM.weights && FM.weights.planById(args[0])) s.planId = args[0];
        if (args[1] && FM.weights && FM.weights.packById(args[1])) s.packId = args[1];
        if (args[2]) s.sheet = args[2];
      }
    });
  }

  FM.planset = {
    build: build,
    render: render,
    renderSheet: renderSheet,
    text: text,
    /* exposed so the tests and any other reader can assert on the pieces
       rather than on a 3,000-line string */
    criteria: criteria,
    geometry: geometry,
    pipeRows: pipeRows,
    probe: probe,
    NOT_SEALED: NOT_SEALED,
    SEAL_LINES: SEAL_LINES,
    FOOTER: FOOTER
  };
})();

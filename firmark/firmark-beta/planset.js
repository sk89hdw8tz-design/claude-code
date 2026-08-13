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

  /* Reads the first field an upstream record actually carries, from a list of
     the names that record might plausibly use. ARCHITECTURE.md fixes the shape
     of `unresolved` and `excluded` but says only `warnings: [...]` — so a
     warning arrives as {kind, text, refs} from one module and as {what, why}
     from another, and printing "(unnamed)" over a sentence somebody wrote is
     losing the finding, not guarding against it. Returns the default only when
     the record genuinely carries nothing readable. */
  function pick(o, keys, dflt) {
    if (o === null || o === undefined) return dflt;
    if (typeof o !== "object") return safe(o, dflt);
    for (var i = 0; i < keys.length; i++) {
      if (!own(o, keys[i])) continue;
      var v = o[keys[i]];
      if (v === null || v === undefined || v === "" || typeof v === "object") continue;
      return String(v);
    }
    return dflt;
  }
  function refsOf(o) {
    if (!o || !isArr(o.refs)) return "";
    var r = o.refs.filter(function (x) { return x !== null && x !== undefined && typeof x !== "object"; });
    return r.length ? r.map(String).join(", ") : "";
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

  /* A timestamp a person reads. pipeline.js records `at` as a full ISO
     instant — "2026-08-13T15:13:46.862Z" — and pipeline-view.js already
     shortens it for the screen. The package was printing the raw string, so
     the same approval read one way on screen and another on the document
     going to a plan reviewer, milliseconds and all, in a 24-column cell that
     also overflowed the 78-column sheet.

     One implementation, and it never invents: anything that is not an ISO
     instant is printed exactly as it arrived, because a timestamp this file
     cannot parse is a fact about the trail and not a formatting problem. */
  function when(v) {
    var s = str(v);
    if (!s) return "—";
    var m = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})(?::\d{2}(?:\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?$/.exec(s);
    if (!m) return s;
    return m[1] + " " + m[2] + " " + (m[3] === undefined || m[3] === "Z" ? "UTC" : m[3]);
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

     The second half of that sentence was not true. The table printed
     "Risk category  NOT DECLARED", "Wall dead load  NONE CARRIED" and
     an em-dash under Exposure category on every package this product
     has ever produced, the legend under it said in terms "it is NOT a
     value, and it is an open item" — and NOT ONE of them reached S5.0.
     Risk category is the input that chooses the wind map; a cover that
     says it is undeclared and an open-items sheet that never mentions
     it again is the sheet claiming a collection it did not make.

     So an undeclared row is now MARKED, here, at the point where the
     absence is known, and collectOpen() reads the mark. A row is
     undeclared when this build has no field behind it — never because
     a string happened to look empty.
     ============================================================ */

  var NOT_DECLARED = "NOT DECLARED";

  function criteria(pack, juris) {
    var rows = [], notes = [];
    function row(k, v, cls, cite, undeclared) {
      rows.push({ k: k, v: v, cls: cls, cite: cite || "", undeclared: !!undeclared });
    }
    /* a value this build does not carry: print NOT DECLARED and mark it */
    function val(k, v, unit, cls, cite, whenMissing) {
      var s = safe(v, "");
      if (s === "" || s === "—") {
        row(k, NOT_DECLARED, "not stated",
            whenMissing || (cite ? cite + "  " : "") +
            "This build carries no value for it on either the region pack or the " +
            "jurisdiction record.", true);
        return;
      }
      row(k, s + (unit ? " " + unit : ""), cls, cite);
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
      val("Design wind speed", jur.wind.vMph, "mph", clsOf(jur.wind.cls), safe(jur.wind.cite, ""));
      val("Exposure category", jur.wind.exposure, "", clsOf(jur.wind.cls), safe(jur.wind.note, ""),
          "The jurisdiction record carries no exposure category. ASCE 7 §26.7 makes it a " +
          "fetch determination at the actual site — it is not a regional constant and " +
          "nothing here may supply one.");
    } else if (pack && pack.climate) {
      val("Design wind speed", pack.climate.windMph && pack.climate.windMph.v, "mph",
          clsOf(pack.climate.windMph && pack.climate.windMph.cls),
          safe(pack.climate.windMph && pack.climate.windMph.note, ""));
      val("Exposure category", pack.climate.exposure && pack.climate.exposure.v, "",
          clsOf(pack.climate.exposure && pack.climate.exposure.cls),
          safe(pack.climate.exposure && pack.climate.exposure.note, ""),
          "The region pack carries no exposure category, and ASCE 7 §26.7 makes it a " +
          "fetch determination at the actual site rather than a regional constant.");
    }
    row("Risk category", NOT_DECLARED, "not stated",
        "This build carries no risk-category field on either the region pack or the " +
        "jurisdiction record. Confirm against ASCE 7 Table 1.5-1 before the wind " +
        "speed above is used for anything.", true);

    /* ---- snow ---- */
    if (jur && jur.snow) {
      row("Ground snow p_g", safe(jur.snow.pgPsf) + " psf", clsOf(jur.snow.cls), safe(jur.snow.cite, ""));
    } else if (pack && pack.climate && pack.climate.groundSnow) {
      row("Ground snow p_g", safe(pack.climate.groundSnow.v) + " psf",
          clsOf(pack.climate.groundSnow.cls), safe(pack.climate.groundSnow.note, ""));
    }

    /* ---- seismic ---- */
    if (jur && jur.seismic) {
      val("Seismic design category", jur.seismic.sdc, "", clsOf(jur.seismic.cls),
          safe(jur.seismic.cite, ""));
      var ss = safe(jur.seismic.ss, ""), s1 = safe(jur.seismic.s1, "");
      if (ss === "" || s1 === "") {
        row("S_s / S_1", NOT_DECLARED, "not stated",
            "The jurisdiction record carries " +
            (ss === "" && s1 === "" ? "neither S_s nor S_1"
              : (ss === "" ? "S_1 = " + s1 + " but no S_s" : "S_s = " + ss + " but no S_1")) +
            ". Look the pair up on the ASCE 7 Hazard Tool for this site.", true);
      } else {
        row("S_s / S_1", ss + " / " + s1, clsOf(jur.seismic.cls), safe(jur.seismic.cite, ""));
      }
    } else if (pack && pack.climate && pack.climate.sdc) {
      val("Seismic design category", pack.climate.sdc.v, "", clsOf(pack.climate.sdc.cls),
          safe(pack.climate.sdc.note, ""));
      row("S_s / S_1", NOT_DECLARED, "not stated",
          "No jurisdiction record was supplied; the mapped spectral accelerations are " +
          "not carried by a region pack. Look them up on the ASCE 7 Hazard Tool.", true);
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
        "or an upper storey must have that load added by hand — see S0.1 engine limits.",
        true);

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
     WHICH OPENINGS AND WHICH WALLS A MARK ACTUALLY COVERS

     The takeoff groups openings that are identical in every derived value
     into ONE mark built n times, and it traces the group in the mark's
     `count` derivation: HDR-O1, count 8, "from openings O1, O2, O3, O4, O7,
     O8, O9, O10".

     The mark's LABEL names only the first opening's wall — "Header · window
     4.00 ft · wall W1 · First floor" — because the mark id is taken from the
     first opening in the group. The schedule printed that label beside QTY 8,
     so S2.0 read "wall W1 … QTY 8" on a wall that has six openings, while
     four of the eight were in W3. The takeoff's own derivation names both
     walls. A schedule that names one wall for a mark covering two sends a
     framer to the wrong elevation, and the count no longer ties to the wall
     it is printed against.

     Nothing here is inferred from prose: it reads `fromIds` off the count
     derivation and resolves each id against the model's own opening → wall
     map. An id the model does not carry is NAMED as unresolved rather than
     quietly dropped, because a partial list under a total is the same defect
     one level down.
     ============================================================ */

  function spreadOf(g, takeoff) {
    var out = { available: false, byMark: {} };
    if (!g || !isArr(g.levels) || !takeoff || !isArr(takeoff.derivations)) return out;

    var wallOf = {}, isOpening = {};
    g.levels.forEach(function (L) {
      L.openings.forEach(function (o) {
        wallOf[" " + o.id] = o.hostFound ? o.wallId : null;
        isOpening[" " + o.id] = true;
      });
    });

    takeoff.derivations.forEach(function (d) {
      if (!d || safe(d.field) !== "count") return;
      var id = safe(d.markId, "");
      if (!id || id === "—" || own(out.byMark, " " + id)) return;
      var ids = isArr(d.fromIds) ? d.fromIds.map(function (x) { return safe(x); }) : [];
      var openings = [], walls = [], unresolved = [], hostless = [];
      ids.forEach(function (x) {
        if (!own(isOpening, " " + x)) { unresolved.push(x); return; }
        openings.push(x);
        var w = wallOf[" " + x];
        if (w === null || w === undefined || w === "—") { hostless.push(x); return; }
        if (walls.indexOf(w) === -1) walls.push(w);
      });
      /* a count derived from a run names its framing region, not openings —
         that is a different derivation and this table has nothing to add */
      if (!openings.length && !unresolved.length) return;
      out.available = true;
      out.byMark[" " + id] = {
        markId: id, openings: openings, walls: walls,
        unresolved: unresolved, hostless: hostless,
        count: d.value, from: safe(d.from, "")
      };
    });
    return out;
  }

  function spreadFor(spread, markId) {
    if (!spread || !spread.available) return null;
    return own(spread.byMark, " " + markId) ? spread.byMark[" " + markId] : null;
  }

  /* The openings a mark stands for, and the wall each of them is in. */
  function spreadWhere(s) {
    if (!s) return "";
    var all = s.openings.concat(s.unresolved);
    return "opening" + (all.length === 1 ? " " : "s ") + all.join(", ") +
           (s.walls.length
             ? " · wall" + (s.walls.length === 1 ? " " : "s ") + s.walls.join(", ")
             : " · no wall is resolved for any of them");
  }

  /* The sentence a schedule row needs when its mark is more than one opening.
     Returns "" when the mark is a single opening and the row already says
     everything true about it. */
  function spreadNote(spread, markId, labelText) {
    var s = spreadFor(spread, markId);
    if (!s) return "";
    var n = s.openings.length + s.unresolved.length;
    if (n < 2) return "";
    var parts = ["QTY " + safe(s.count, String(n)) + " is " + n + " openings — " +
                 s.openings.concat(s.unresolved).join(", ") + " —"];
    if (s.walls.length > 1) {
      parts.push("in " + s.walls.length + " walls: " + s.walls.join(", ") + ".");
      /* only worth saying when the row's own label names one of them */
      var named = null;
      s.walls.forEach(function (w) {
        if (named) return;
        var re = new RegExp("(^|[^A-Za-z0-9_-])" + w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") +
                            "([^A-Za-z0-9_-]|$)");
        if (re.test(String(labelText || ""))) named = w;
      });
      if (named) {
        parts.push("The label names " + named + " only, because the mark id is taken from " +
                   "the first opening in the group — do not read this quantity against " +
                   named + " alone.");
      }
    } else if (s.walls.length === 1) {
      parts.push("all in wall " + s.walls[0] + ".");
    } else {
      parts.push("and the model resolves no wall for any of them.");
    }
    if (s.hostless.length) {
      parts.push("Opening(s) " + s.hostless.join(", ") + " name a wall the model does not carry.");
    }
    if (s.unresolved.length) {
      parts.push("Id(s) " + s.unresolved.join(", ") + " are named by the takeoff's count " +
                 "derivation but are not openings in this model, so their wall is unknown.");
    }
    return parts.join(" ");
  }

  /* ============================================================
     OPEN ITEMS

     Collected from every stage, and the standing items ALWAYS print.
     They are not padding: they are true of every package this system
     produces, and a set that reported zero open items would be
     claiming a completeness the system cannot have.
     ============================================================ */

  function collectOpen(ctx, p, res, g) {
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
        var head = pick(u, ["what", "item", "mark", "markId", "title", "kind"], "");
        var refs = refsOf(u);
        add("TAKEOFF — UNRESOLVED",
            (head || pick(u, ["text", "why", "message"], "(unnamed)")) + (refs ? " — " + refs : ""),
            pick(u, ["why", "reason", "text", "message", "detail"], "no reason given"),
            pick(u, ["need", "action", "resolve", "fix"],
                 "a human must answer this before the takeoff is complete"));
      });
      (isArr(tk.warnings) ? tk.warnings : []).forEach(function (wn) {
        var head = pick(wn, ["what", "title", "item", "kind"], "");
        var refs = refsOf(wn);
        add("TAKEOFF — WARNING",
            (head || pick(wn, ["text", "message", "why"], "(unnamed warning)")) + (refs ? " — " + refs : ""),
            pick(wn, ["why", "reason", "text", "message", "detail"], "no detail given"),
            pick(wn, ["need", "action"], "review before gate 2 (the takeoff gate) is approved"));
      });
      if (!isArr(tk.derivations) || !tk.derivations.length) {
        add("TAKEOFF — UNRESOLVED", "No derivation trail was supplied.",
            "The contract requires every span, tributary and bearing to be traced so a " +
            "reviewer can reconstruct it without reading code. None was supplied.",
            "Produce derivations before gate 2 (the takeoff gate) is approved.");
      }
    }

    /* ---- 3b. does the schedule describe the house on the framing plan? ----

       ctx.planResult and ctx.takeoff arrive independently. Solve a catalogue
       plan while the takeoff derives its marks from a drawn model and the two
       carry different mark ids — the schedule then belongs to a different
       document than the framing plan bound behind it. Nothing downstream
       detects that, and both sheets look perfectly finished. So it is
       checked here and named. */
    if (p.have.takeoff && isArr(p.have.takeoff.marks) && p.have.takeoff.marks.length &&
        res && isArr(res.marks) && res.marks.length) {
      var tkSet = {}, tkList = [];
      p.have.takeoff.marks.forEach(function (m) {
        var id = safe(m && m.id, "");
        if (id && id !== "—") { tkSet[" " + id] = 1; tkList.push(id); }
      });
      var reList = res.marks.map(function (m) { return safe(m.mark && m.mark.id, "—"); });
      var shared = reList.filter(function (id) { return own(tkSet, " " + id); });
      if (shared.length !== reList.length || shared.length !== tkList.length) {
        add("GEOMETRY", "The schedule and the takeoff do not describe the same marks.",
            "The schedule on S2.0 carries " + reList.length + " mark(s) (" +
            reList.join(", ") + ") and the takeoff behind S1.0 carries " + tkList.length +
            " (" + tkList.join(", ") + "). " + shared.length + " appear in both. The " +
            "members on S2.0 were therefore not sized from the takeoff drawn on S1.0, " +
            "and the two sheets are describing the same house through two different " +
            "documents.",
            "Solve the marks the takeoff produced, or reconcile the mark ids, before " +
            "this package is issued. Until then read S1.0 as geometry and S2.0 as a " +
            "schedule, and do not read a span off one against a member on the other.");
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
      /* bom.js's own DO-NOT-ISSUE signal, which this sheet did not collect.
         A stick bought short is a framing-day problem and it is the loudest
         thing bom.js can say; a sheet billed as the collection point that
         omits it is claiming a completeness it does not have. */
      if (isArr(bom.selfChecks) && bom.selfChecks.length) {
        bom.selfChecks.forEach(function (s) {
          add("BILL OF MATERIALS — SELF-CHECK FAILED",
              "bom.js self-check: " + safe(s, "(no detail supplied)"),
              "The bill of materials checked its own arithmetic against solver.js and the " +
              "two disagree. bom.js prints DO NOT ISSUE on its own export for this.",
              "Resolve it before any quantity on S4.0 is used to order material.");
        });
      }
      var exc = isArr(bom.excluded) ? bom.excluded : null;
      if (!exc) {
        add("BILL OF MATERIALS — EXCLUDED", "The bill of materials declares no exclusion list.",
            "The contract requires one: anything the calc stack does not size must be " +
            "listed as absent with a reason. A BOM that silently omits the girder reads " +
            "as a complete order.",
            "bom.js must publish `excluded` before the quantities are used to buy anything.");
      } else {
        exc.forEach(function (x) {
          add("BILL OF MATERIALS — EXCLUDED",
              pick(x, ["what", "item", "sku", "markId", "text"], "(unnamed)"),
              pick(x, ["why", "reason", "note", "text"], "no reason given"),
              "Not in the quantities on S4.0. Price and buy it separately.");
        });
      }
    }

    /* ---- 5b. the design criteria this build does not carry ----

       criteria() has always printed NOT DECLARED / NONE CARRIED rows, and
       the legend beneath the table has always read "not stated — this build
       carries no field for it — it is NOT a value, AND IT IS AN OPEN ITEM".
       It was not one. Risk category — the input that chooses which wind map
       to read — said NOT DECLARED on the cover of every package this product
       has produced and appeared nowhere on S5.0. Each undeclared row is
       marked at the point where the absence is known, and every marked row
       lands here. */
    (function () {
      var crit = criteria(res ? res.pack : (ctx.pack || null), p.have.juris);
      crit.rows.forEach(function (r) {
        if (!r.undeclared) return;
        add("DESIGN CRITERIA — NOT DECLARED", r.k + " is " + r.v + " on S0.0.",
            safe(r.cite, "This build carries no field for it."),
            "Establish it before the members on S2.0 are relied on. A criterion the " +
            "cover prints as undeclared is one the reviewing engineer has to supply, " +
            "not one the package resolved.");
      });
    })();

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
              pick(v, ["what", "item", "title", "text", "check"], "(unnamed)"),
              pick(v, ["why", "reason", "note", "detail"], "not stated"),
              pick(v, ["against", "source", "verifyWith", "need", "how"],
                   "Verify with the authority having jurisdiction."));
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

    /* ---- 8. the geometry ----

       EVERY cad.validate() FINDING IS AN OPEN ITEM. This sheet is billed as
       the collection point for every stage, and stage 1 is the geometry — so
       for a long time it collected exactly one geometry item, and that item
       was one this file wrote itself. Meanwhile cad.validate() returned seven
       findings on `starter-1210` — four walls whose thickness was ASSUMED and
       four walls carrying openings at PLACEHOLDER offsets, "no dimension off
       them is real" — and every one of them printed on S1.0 and NOWHERE on
       S5.0. They were not hidden from the package; they were absent from the
       sheet a PE reads to know what they are inheriting, which is worse than
       hidden, because the sheet claims to have looked.

       The findings are carried verbatim, with cad.js's own severity, and an
       `error` says outright that it blocks gate 1. Nothing is summarised: a
       validator's sentence is the finding. */
    if (p.have.model) {
      var val = g && isArr(g.validation) ? g.validation : null;
      if (val) {
        val.forEach(function (v) {
          var sev = safe(v.severity, "").toLowerCase();
          var where = [];
          if (str(v.level)) where.push("level " + safe(v.level));
          if (str(v.id)) where.push(safe(v.id));
          add("GEOMETRY",
              "cad.validate [" + (sev || "severity not stated") + "] " +
                (where.length ? where.join(" · ") : "location not stated") +
                (str(v.code) ? "  (" + safe(v.code) + ")" : ""),
              safe(v.text, "cad.js reported this finding with no text."),
              sev === "error"
                ? "An ERROR from cad.validate() blocks approval gate 1 (geometry). The " +
                  "package cannot be issued until the model is corrected and the takeoff re-run."
                : "A WARNING from cad.validate(). It does not block gate 1, so approving " +
                  "the geometry means a named person read this and accepted it.");
        });
        if (!val.length) {
          add("GEOMETRY", "cad.validate() returned no findings against this model.",
              "That is a statement about the checks cad.js performs, not a statement that " +
              "the geometry is right. Nothing here confirms the model against the " +
              "architectural set.",
              "Check the drawn geometry against the architectural set before gate 1.");
        }
      } else if (p.cad) {
        add("GEOMETRY", "The model could not be validated.",
            "cad.js is loaded but FM.cad.validate() did not return a finding list for this " +
            "model — it threw, or returned something this package could not read. A wall " +
            "with no thickness, an opening wider than its wall or a framing region bearing " +
            "on nothing would not have been caught.",
            "Run FM.cad.validate() against this model directly and fix what it reports.");
      }
      add("GEOMETRY", "Plan north is not declared by the model.",
          "The CAD model carries an origin and axes but no true-north bearing, so the " +
          "north arrow on S1.0 is an assumption of the drawing. This is this package's " +
          "own finding, not one of cad.validate()'s.",
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
    /* Which document the members were sized from, and which one the framing
       plan was drawn from. They are not always the same document, and the
       answer is derived by comparing the two mark lists rather than taken on
       trust from a flag somebody has to remember to set. */
    var tkMarks = (p.have.takeoff && isArr(p.have.takeoff.marks)) ? p.have.takeoff.marks : null;
    var sameMarks = null;
    if (tkMarks && tkMarks.length && res && isArr(res.marks) && res.marks.length) {
      var tkSet = {};
      tkMarks.forEach(function (m) { tkSet[" " + safe(m && m.id, "")] = 1; });
      var shared = res.marks.filter(function (m) {
        return own(tkSet, " " + safe(m.mark && m.mark.id, ""));
      }).length;
      sameMarks = (shared === res.marks.length && shared === tkMarks.length);
    }
    field("Marks on the schedule", res && isArr(res.marks)
          ? res.marks.length + (sameMarks === true
              ? ", sized from the takeoff's own marks — S1.0 and S2.0 are the same house"
              : (sameMarks === false
                  ? ", from the plan record " + (plan ? safe(plan.id) : "") +
                    " — NOT the takeoff's marks, see S5.0"
                  : ", from the plan record " + (plan ? safe(plan.id) : "")))
          : "none — no solver result was supplied");
    field("Marks from the takeoff", tkMarks
          ? tkMarks.length + ", derived from the geometry on S1.0"
          : "no takeoff was supplied — nothing on this set is traced to the drawing");
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
            pad(r.by || "—", 18) + when(r.at));
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
          say("      " + pad(when(a.at), 22) + pad(safe(a.kind, "—"), 10) +
              pad(safe(a.stage, "—"), 12) + safe(a.by, "—"));
        });
      }
    }

    /* ---- master set ---- */
    if (plan && FM.weights && typeof FM.weights.variantsFor === "function") {
      var vi = null, viWhy = "";
      try { vi = FM.weights.variantsFor(plan); }
      catch (e) { vi = null; viWhy = safe(e && e.message, "the declarations could not be read"); }

      /* A plan set that does not say which combination of a master set it
         covers is the defect this section exists to prevent, so it must not
         disappear just because the variant declarations could not be resolved
         against the mark list that was actually solved. Read the plan record
         back and say what it declares even then. */
      var cat = null;
      if (typeof FM.weights.planById === "function") {
        try { cat = FM.weights.planById(safe(plan.id)); } catch (e2) { cat = null; }
      }
      var catDeclares = !!(cat && ((isArr(cat.elevations) && cat.elevations.length) ||
                                   (isArr(cat.options) && cat.options.length)));

      if ((!vi || !vi.declaresVariants) && catDeclares) {
        block("MASTER SET — WHAT THIS PACKAGE COVERS");
        wrap("The plan record " + safe(plan.id) + " declares " +
             (isArr(cat.elevations) ? cat.elevations.length : 0) + " elevation(s) and " +
             (isArr(cat.options) ? cat.options.length : 0) + " option(s), so this is a " +
             "MASTER SET: one plan built several ways.", W - 4)
          .forEach(function (x) { say("  " + x); });
        say();
        wrap("** THIS PACKAGE DOES NOT STATE WHICH COMBINATION IT COVERS. The variant " +
             "declarations could not be resolved against the marks this package was " +
             "solved from" + (viWhy ? " — " + viWhy : "") + ". Treat the members on S2.0 " +
             "as ONE combination and confirm which one before this set is issued: a " +
             "master set whose sheets do not name their combination is how a revision " +
             "gets manufactured after permit. **", W - 4)
          .forEach(function (x) { say("  " + x); });
      }

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
      wrap(Object.keys(g.stats).map(function (k) {
        return k + " " + safe(g.stats[k]);
      }).join(" · "), W - 18).forEach(function (x, i) {
        say("  " + pad(i ? "" : "cad.stats", 14) + (i ? "  " : ": ") + x);
      });
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

  function sheetSchedules(ctx, p, res, spread) {
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
      var sn = spreadNote(spread, id, safe(m.mark.label));
      if (sn) wrap(sn, W - 16).forEach(function (x) { say("  " + pad("", 12) + x); });
    });

    /* ---- headers ---- */
    var hdrs = res.marks.filter(function (m) { return m.mark && m.mark.role === "header"; });
    block("HEADER SCHEDULE — " + hdrs.length + " MARK(S)");
    if (!hdrs.length) say("  No mark on this plan is a header.");
    else {
      /* QTY belongs on this schedule. A header schedule of four marks over a
         house with eleven openings is not a lie only if it says which of the
         two numbers it is counting — and the openings each mark stands for
         are named underneath, with their walls, because the mark id names
         one opening and the group can straddle several walls. */
      say("  " + pad("MARK", 12) + pad("SPAN", 9) + pad("TRIB", 9) + pad("BEARING", 9) +
          pad("HEAD", 8) + "QTY");
      say("  " + rule("-").slice(0, W - 2));
      var openingsCovered = 0, spreadKnown = 0;
      hdrs.forEach(function (m) {
        var row = m.unifiedTo || (m.solution && m.solution.pick);
        var member = m.notApplicable ? "— not sized (" + safe(m.notApplicable.reason) + ") —"
                   : (row ? safe(row.cand.size) + " " + safe(row.cand.species) + " " + safe(row.cand.grade)
                          : "— ESCALATED, no member —");
        say("  " + pad(safe(m.mark.id), 12) +
            pad(n2(m.mark.span, 2) + " ft", 9) +
            pad(m.mark.trib === undefined ? "—" : n2(m.mark.trib, 2) + " ft", 9) +
            pad(m.mark.bearing === undefined ? "—" : n2(m.mark.bearing, 2) + " in", 9) +
            pad(m.mark.headHeightIn === undefined ? "—" : n2(m.mark.headHeightIn, 0) + " in", 8) +
            (isFinite(Number(m.mark.count)) ? String(m.mark.count) : "—"));
        wrap("→ " + member, W - 16).forEach(function (x) { say("  " + pad("", 12) + x); });
        var hs = spreadFor(spread, safe(m.mark.id));
        if (hs) {
          spreadKnown++;
          openingsCovered += hs.openings.length + hs.unresolved.length;
          var line = spreadWhere(hs);
          if (hs.walls.length > 1) {
            line += ". The mark id and the label name " + hs.openings[0] + " and its wall " +
                    "only — the group straddles " + hs.walls.length + " walls and this " +
                    "quantity may not be read against one of them.";
          }
          if (hs.hostless.length) {
            line += " Opening(s) " + hs.hostless.join(", ") + " name a wall the model does not carry.";
          }
          if (hs.unresolved.length) {
            line += " Id(s) " + hs.unresolved.join(", ") + " are named by the count derivation " +
                    "but are not openings in this model.";
          }
          wrap(line, W - 16).forEach(function (x) { say("  " + pad("", 12) + x); });
        }
      });
      say();
      if (spreadKnown) {
        wrap(hdrs.length + " header mark(s) on this schedule stand for " + openingsCovered +
             " drawn opening(s)" +
             (spreadKnown === hdrs.length ? ""
               : " — " + (hdrs.length - spreadKnown) + " of the marks carry no takeoff count " +
                 "derivation, so the openings behind them are not named here") +
             ". The mark count and the opening count are different numbers and both are " +
             "printed, because a schedule row is a member and an elevation is a hole.", W - 4)
          .forEach(function (x) { say("  " + x); });
        say();
      }
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
      /* The SKU a real bill of materials carries IS the member description —
         "2x12 Spruce-Pine-Fir No. 1/No. 2" — so a separate size/species
         column repeats it and collides. One wide SKU column, and everything
         else on the line under it. */
      say("  " + pad("SKU", 42) + pad("PCS", 7) + pad("LENGTH", 10) + lpad("EXTENDED", 9));
      say("  " + rule("-").slice(0, W - 2));
      lines.forEach(function (ln) {
        wrap(safe(ln.sku, "(unnamed SKU)"), 40).forEach(function (x, i) {
          if (i) { say("  " + x); return; }
          say("  " + pad(x, 42) + pad(safe(ln.piecesPerHouse), 7) +
              pad(ln.lengthFt === undefined ? "—" : n2(ln.lengthFt, 1) + " ft", 10) +
              lpad(usd(ln.extUSD), 9));
        });
        var sub = [];
        var desc = (safe(ln.size, "") + " " + safe(ln.species, "") + " " + safe(ln.grade, "")).replace(/\s+/g, " ").replace(/^ | $/g, "");
        if (desc && safe(ln.sku).indexOf(desc) === -1) sub.push(desc);
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
      say("      " + pad("Board feet", 20) + comma(bom.totals.bf) + " bf");
      say("      " + pad("Pieces", 20) + comma(bom.totals.pieces) + " pc");
      /* THE LABEL HAS TO NAME WHAT THE NUMBER IS. bom.js states outright that
         `usd` is MATERIAL ONLY and carries `dropHandlingUSD` on its own line
         so it can never be read as a waste allowance on the material. This
         sheet was calling the same figure "Modelled cost", which is the name
         of a larger thing, and was dropping the handling line entirely — so
         the package and the materials export disagreed by the handling
         figure and neither said why. */
      say("      " + pad("Material cost", 20) + usd(bom.totals.usd) +
          "   [market placeholders — no code standing]");
      if (bom.totals.dropHandlingUSD !== undefined) {
        say("      " + pad("Drop handling", 20) + usd(bom.totals.dropHandlingUSD) +
            "   [market — NOT lumber]");
        wrap("Drop handling prices sorting and disposing of the offcut, net of salvage. " +
             "It is NOT an estimating waste allowance and it is NOT inside the material " +
             "figure above — the two are added only where a reader wants them added.", W - 10)
          .forEach(function (x) { say("        " + x); });
      }
      if (isFinite(Number(bom.totals.modelledSelectionUSD))) {
        say("      " + pad("Selection objective", 20) + usd(bom.totals.modelledSelectionUSD) +
            "   [market — RANKS members, not an invoice]");
        wrap(safe(bom.totals.selectionTieBack, "This is FM.solver's ranking objective, not " +
             "the bill of materials total, and the difference between them is the " +
             "non-material weights inside it."), W - 10)
          .forEach(function (x) { say("        " + x); });
      }
      /* byCategory is MATERIAL DOLLARS by member role. It was printed as the
         raw stored number — "header 149.39733333333334" under a line reading
         "Modelled cost $149.40" — which is a float with no unit on a document
         a plan reviewer reads, and two spellings of one figure on consecutive
         lines. Money is money here, and the parts are stated to TIE to the
         whole: a breakdown a reader cannot add up is worse than no breakdown,
         because it looks checked. */
      if (bom.totals.byCategory && typeof bom.totals.byCategory === "object") {
        var catKeys = isArr(bom.totals.byCategoryOrder)
          ? bom.totals.byCategoryOrder.filter(function (k) { return own(bom.totals.byCategory, k); })
          : Object.keys(bom.totals.byCategory);
        if (catKeys.length) {
          say();
          say("      " + pad("  by member role", 20) + "material dollars [market]");
          var catSum = 0, catAllNumeric = true;
          catKeys.forEach(function (k) {
            var v = Number(bom.totals.byCategory[k]);
            if (isFinite(v)) catSum += v; else catAllNumeric = false;
            say("      " + pad("    " + safe(k, "(unnamed role)"), 20) +
                (isFinite(v) ? usd(v) : "** NOT A NUMBER — bom.js supplied " +
                 safe(bom.totals.byCategory[k], "nothing readable") + " **"));
          });
          var tot = Number(bom.totals.usd);
          if (catAllNumeric && isFinite(tot)) {
            if (Math.abs(catSum - tot) > 0.005) {
              wrap("** THE ROLES DO NOT TIE TO THE TOTAL. They add to " + usd(catSum) +
                   " against a material cost of " + usd(tot) + ", a difference of " +
                   usd(tot - catSum) + ". One of the two numbers is wrong and this sheet " +
                   "cannot say which — do not reconcile a quote against either until " +
                   "bom.js is checked. **", W - 8)
                .forEach(function (x) { say("      " + x); });
            } else {
              say("      " + pad("    (they tie)", 20) + usd(catSum) +
                  "   = the material cost above");
            }
          }
        }
      }
    }
    if (bom.waste) {
      say();
      wrap(safe(bom.waste.policy) + " · applied " +
           (bom.waste.appliedPct === undefined ? "—" : n2(bom.waste.appliedPct, 1) + "%"), W - 18)
        .forEach(function (x, i) { say("  " + pad(i ? "" : "WASTE POLICY", 14) + (i ? "  " : ": ") + x); });
      if (bom.waste.basis) wrap("basis: " + safe(bom.waste.basis), W - 8).forEach(function (x) { say("      " + x); });
    }
    /* A COMMUNITY TOTAL WITH NO DIVISOR IS NOT CHECKABLE.
       This printed "per community : $110,953.25" and nothing else — no lot
       count, no multiplier, no statement of whether take rates were applied.
       $110k on a PE package that a reader cannot divide by anything is a
       number with no unit wearing a dollar sign; the lot count is right there
       on the record bom.js hands over, along with the arithmetic. */
    if (bom.perLot || bom.perCommunity) {
      say();
      say("  SCALED QUANTITIES");
      var pl0 = bom.perLot && typeof bom.perLot === "object" ? bom.perLot : null;
      var pc0 = bom.perCommunity && typeof bom.perCommunity === "object" ? bom.perCommunity : null;
      if (bom.perLot) {
        say("      " + pad("per lot", 16) + ": " +
            (pl0 && pl0.usd !== undefined ? usd(pl0.usd) : safe(bom.perLot, "supplied")) +
            (pl0 && isFinite(Number(pl0.pieces))
              ? "   " + comma(pl0.pieces) + " pc · " + comma(pl0.bf) + " bf" : ""));
      }
      if (bom.perCommunity) {
        var lots = pc0 && isFinite(Number(pc0.lots)) ? Number(pc0.lots) : null;
        say("      " + pad("per community", 16) + ": " +
            (pc0 && pc0.usd !== undefined ? usd(pc0.usd) : safe(bom.perCommunity, "supplied")) +
            (pc0 && isFinite(Number(pc0.pieces))
              ? "   " + comma(pc0.pieces) + " pc · " + comma(pc0.bf) + " bf" : ""));
        var overField = fielder(say, 6, 16);
        overField("over",
            lots === null
              ? "** THE LOT COUNT IS NOT DECLARED. The community figure above cannot be "
                + "checked against the per-lot figure without it. **"
              : comma(lots) + " lot(s)" +
                (pc0.weighted === true
                  ? ", WEIGHTED by the variants' [market] take rates — not one house × " +
                    comma(lots)
                  : (pc0.weighted === false
                      ? ", as one house × " + comma(lots) + " — every lot priced as the " +
                        "combination solved on S2.0, take rates NOT applied"
                      : ", and this record does not say whether take rates were applied")));
        if (pc0 && pc0.basis) {
          wrap("basis: " + safe(pc0.basis), W - 10).forEach(function (x) { say("        " + x); });
        }
      }
      if (pl0 && pc0 && isFinite(Number(pl0.usd)) && isFinite(Number(pc0.usd)) &&
          isFinite(Number(pc0.lots)) && pc0.weighted !== true) {
        var expect = Number(pl0.usd) * Number(pc0.lots);
        if (Math.abs(expect - Number(pc0.usd)) > 0.01) {
          wrap("** THE TWO SCALED FIGURES DO NOT TIE. Per lot × " + comma(pc0.lots) +
               " lots is " + usd(expect) + " against a community figure of " +
               usd(pc0.usd) + ". Do not use either until bom.js is checked. **", W - 8)
            .forEach(function (x) { say("      " + x); });
        }
      }
    }

    /* WHAT THE LINES ABOVE DO AND DO NOT COVER — the tie back to S2.0.
       bom.js counts this for itself and prints it at the top of the materials
       export; the sheet dropped it, so a reader of S4.0 saw three purchase
       lines with no statement of how many marks on the schedule are behind
       them and how many are not in them at all. */
    if (bom.counts && typeof bom.counts === "object") {
      say();
      say("  WHAT THESE LINES COVER");
      say("      " + pad("Marks on the plan", 30) + lpad(safe(bom.counts.marksOnPlan), 5));
      say("      " + pad("Marks priced above", 30) + lpad(safe(bom.counts.marksPriced), 5));
      say("      " + pad("Marks ESCALATED — no member", 30) + lpad(safe(bom.counts.marksEscalated), 5));
      say("      " + pad("Marks OUT OF SCOPE", 30) + lpad(safe(bom.counts.marksOutOfScope), 5));
      say("      " + pad("Whole categories not sized", 30) + lpad(safe(bom.counts.categoriesNotSized), 5));
      var onPlan = Number(bom.counts.marksOnPlan);
      var accounted = Number(bom.counts.marksPriced) + Number(bom.counts.marksEscalated) +
                      Number(bom.counts.marksOutOfScope);
      if (isFinite(onPlan) && isFinite(accounted) && onPlan !== accounted) {
        wrap("** " + onPlan + " mark(s) are on the plan and " + accounted + " are accounted " +
             "for as priced, escalated or out of scope. " + Math.abs(onPlan - accounted) +
             " mark(s) are in neither column, and this sheet cannot say which. **", W - 8)
          .forEach(function (x) { say("      " + x); });
      }
      if (bom.complete === false) {
        say();
        wrap("** " + safe(bom.completeNote, "This bill of materials is not complete."), W - 6)
          .forEach(function (x, i) { say("  " + (i ? "   " : "") + x); });
      }
    }

    /* bom.js's own DO-NOT-ISSUE signal. It reads "SELF-CHECK FAILED — n
       ITEM(S). DO NOT ISSUE." in the materials export and did not appear on
       this sheet at all, which meant the one document going to a PE was the
       one document that did not carry it. */
    if (isArr(bom.selfChecks) && bom.selfChecks.length) {
      say();
      say("  " + rule("!").slice(0, W - 2));
      say("  !! BILL OF MATERIALS SELF-CHECK FAILED — " + bom.selfChecks.length +
          " ITEM(S). DO NOT ISSUE.");
      say("  " + rule("!").slice(0, W - 2));
      bom.selfChecks.forEach(function (s) {
        wrap(safe(s, "(no detail supplied)"), W - 8).forEach(function (x, i) {
          say("      " + (i ? "  " : "· ") + x);
        });
      });
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
        wrap(pick(x, ["what", "item", "sku", "markId", "text"], "(unnamed)"), W - 6)
          .forEach(function (y, i) { say("  " + (i ? "    " : "· ") + y); });
        wrap(pick(x, ["why", "reason", "note", "text"], "no reason given"), W - 8)
          .forEach(function (y) { say("      " + y); });
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

    /* `at` may arrive as an ISO instant (project.js stores one) or already
       formatted; when() shortens the first and passes the second through. */
    var at = str(ctx.at) ? when(ctx.at) : (function () {
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

    /* which openings and which walls each grouped mark actually covers */
    var spread = spreadOf(g, p.have.takeoff);
    pkg.spread = spread;

    var items = collectOpen(ctx, p, res, g);
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
        lines: function () { return sheetSchedules(ctx, p, res, spread); } },
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

  /* Returning "" for something that is not a package would be a silent
     fallback: the caller writes an empty file and nothing says why. */
  function text(pkg) {
    if (pkg && pkg.sheets && typeof pkg.text === "function") return packageText(pkg);
    return "FIRMARK — NO PACKAGE\n" + rule("=") + "\n" +
           "FM.planset.text() was called with something that is not a package built by\n" +
           "FM.planset.build(). Nothing is printed here because there is nothing to print.\n";
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

  /* Injected once, into whichever of head/body this document actually has.
     The stylesheet is a nicety; a build without a <head> (the headless
     harness has none) must render the sheets anyway rather than throw. */
  function ensurePrintCss() {
    try {
      if (typeof document === "undefined" || !document) return;
      if (document.getElementById && document.getElementById("fm-planset-css")) return;
      var into = document.head || document.body;
      if (!into || typeof into.appendChild !== "function") return;
      var s = document.createElement("style");
      s.id = "fm-planset-css";
      s.textContent = PRINT_CSS;
      into.appendChild(s);
    } catch (e) { /* no stylesheet; the sheets still render */ }
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
    /* Every one of these is read defensively — the module may not be loaded
       in this build, may not have grown the entry point yet, and may throw.
       Any of those produces `null`, and the package SAYS the input was not
       supplied rather than failing to open. This is the whole guard strategy
       in one function. */
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
      try { takeoff = FM.takeoff.run(model, { plan: plan, pack: pack }); } catch (e) { takeoff = null; }
    }

    /* ARCHITECTURE.md's pipeline is geometry → takeoff → demands → calcs, so
       when the takeoff has produced marks the schedule is solved from THOSE —
       otherwise the framing plan on S1.0 and the schedule on S2.0 describe the
       same house through two different documents, and a reviewer reading a
       span off one against a member on the other is reading two drawings.
       If that solve fails the catalogue plan stands, and S5.0 names the
       discrepancy rather than the package hiding it. */
    if (takeoff && isArr(takeoff.marks) && takeoff.marks.length && plan && pack &&
        FM.solver && FM.solver.solvePlan) {
      /* The elevations and options are deliberately NOT carried across: they
         patch the catalogue's mark ids, and weights.js correctly refuses a
         variant that overrides a mark the list does not have. S0.0 reads the
         master-set declarations back off the plan record instead, and says
         when it could not resolve them against this mark list. */
      var derived = { id: plan.id, name: plan.name, summary: plan.summary,
                      lots: plan.lots, note: plan.note, geometry: plan.geometry,
                      marks: takeoff.marks };
      try {
        var r2 = FM.solver.solvePlan(derived, pack);
        if (r2 && isArr(r2.marks) && r2.marks.length) res = r2;
      } catch (e) { /* the catalogue plan's result stands; S5.0 says the two differ */ }
    }
    var bom = null;
    if (res && FM.bom && typeof FM.bom.build === "function") {
      /* the takeoff goes in so a piece count that came out of the takeoff's
         grouping rule can name that rule, instead of the BOM attributing it
         to a plan record that states nothing about it */
      try { bom = FM.bom.build(res, { takeoff: takeoff }); } catch (e) { bom = null; }
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
              var name = "firmark-planset-" +
                         pkg.head.packageId.replace(/[^\w.-]+/g, "-") + "-for-PE-review.txt";
              /* THE RECORD PANEL, not a bare download.

                 A page-initiated download is a REQUEST, not an outcome.
                 This bundle is opened three ways — off disk over file://,
                 off a local server, and as a hosted artefact whose sandbox
                 blocks page-initiated downloads outright. In the third the
                 anchor click does nothing whatsoever and nothing tells the
                 page so.

                 This button called download() directly, so wherever that
                 was blocked it did VISIBLY NOTHING: no panel, no file, and
                 the toast beneath it never ran either. A control audit
                 across the built bundle flagged it dead in both the empty
                 and the fully-approved run, and it was right to.

                 shell.html states the rule for the whole product: an export
                 puts the artefact ON SCREEN, always, and offers the file
                 alongside it. */
              if (FM.deliver) {
                FM.deliver({
                  title: "Plan set for PE review · " + safe(pkg.head.packageId, "package"),
                  filename: name,
                  text: pkg.text(),
                  note: "The package in full. It is NOT a sealed set — the seal block on S0.0 " +
                        "is empty and carries a “to be sealed by” line for the licensed engineer " +
                        "who takes responsibility for it. “Save as file” asks your browser for a " +
                        "copy; some hosted sandboxes block page-initiated downloads and this page " +
                        "cannot tell when yours has, so copy the text if no file appears."
                });
                return;
              }
              download(pkg.text(), name);
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
      var controls = [planSel, packSel];

      /* The jurisdiction selector appears only once jurisdiction.js publishes
         both entry points. Until then the cover says, in terms, that no
         jurisdiction record was supplied and that the criteria table is the
         region pack's planning defaults — which is the truth, and better than
         a selector that silently returns nothing. */
      if (FM.juris && typeof FM.juris.forSite === "function" &&
          typeof FM.juris.jurisdictions === "function" && isArr(FM.juris.STATES)) {
        var opts = [el("option", { value: "", text: "No jurisdiction — region pack defaults" })];
        FM.juris.STATES.forEach(function (st) {
          var list = [];
          try { list = FM.juris.jurisdictions(st) || []; } catch (e) { list = []; }
          list.forEach(function (j) {
            opts.push(el("option", { value: safe(j.id), text: st + " · " + safe(j.name, safe(j.id)),
                                     selected: j.id === s.jurisId ? "selected" : null }));
          });
        });
        var jurSel = el("select", { "aria-label": "Jurisdiction" }, opts);
        jurSel.addEventListener("change", function () {
          s.jurisId = this.value || null; FM.go("planset");
        });
        controls.push(jurSel);
      }
      host.appendChild(el("div", { class: "filter-bar", style: "margin-bottom:14px" }, controls));

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

  /* the addressable sheets, so a link naming one that does not exist is caught
     rather than silently ignored */
  var SHEET_NOS = ["S0.0", "S0.1", "S1.0", "S2.0", "S3.0", "S4.0", "S5.0", "all"];

  if (typeof FM.registerSubRoute === "function") {
    FM.registerSubRoute("planset", {
      read: function () { var s = vstate(); return [s.planId, s.packId, s.sheet]; },
      /* A segment this build does not have was DISCARDED IN SILENCE, and this
         is the worst screen in the product for that to happen on.
         `#/planset/nope` rendered a different plan's package; a substituted
         REGION PACK changes every load, every member and the whole design
         criteria table on the cover sheet — and the reader has a URL in the
         address bar saying otherwise. That is a wrong answer wearing the shape
         of a right one, on the document a licensed engineer is being asked to
         seal.

         The same defect was fixed for #/sizing, #/sheet, #/project and #/cad
         and it came straight back here, because each view spells its own
         codec. Name what could not be found, correct the address bar, and say
         what is actually on screen instead. */
      write: function (args) {
        var s = vstate();
        args = args || [];
        var lost = [];

        if (args[0]) {
          if (FM.weights && FM.weights.planById(args[0])) s.planId = args[0];
          else lost.push("plan “" + args[0] + "”");
        }
        if (args[1]) {
          if (FM.weights && FM.weights.packById(args[1])) s.packId = args[1];
          else lost.push("region “" + args[1] + "”");
        }
        if (args[2]) {
          /* a sheet number only means something if this package has it */
          var known = false, i;
          for (i = 0; i < SHEET_NOS.length; i++) if (SHEET_NOS[i] === args[2]) known = true;
          if (known) s.sheet = args[2];
          else lost.push("sheet “" + args[2] + "”");
        }

        if (lost.length && FM.toast) {
          var pl = FM.weights && FM.weights.planById(s.planId);
          var pk = FM.weights && FM.weights.packById(s.packId);
          FM.toast("This link names " + lost.join(" and ") + ", which this build does not have. " +
                   "Showing " + ((pl && pl.name) || s.planId) + " in " +
                   ((pk && pk.name) || s.packId) + " instead — a package is not the one the link " +
                   "named, so check the link before reading or issuing it.");
          if (FM.syncHash) setTimeout(function () { FM.syncHash(true); }, 0);
        }
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

/* ============================================================
   Schedule export.

   calc-spec §8 opens: "The app must print this list, verbatim and
   unabridged, on every output. A calculation that does not state
   its boundaries is not an engineering deliverable."

   Until now nothing left the sizing view at all, and what the sheet
   exported carried a ten-item paraphrase instead of the 24. So every
   honesty mechanism the product has — the escalations, the marks it
   refuses, the wind note, the advisories, the provenance — died at
   the browser window, and a schedule arrived at the next desk as a
   bare list of members.

   This is the artifact that carries them. It is deliberately plain
   text: it has to survive being pasted into an email.
   ============================================================ */

(function () {
  "use strict";

  function rule(ch) { return new Array(79).join(ch || "="); }
  function pad(s, n) { s = String(s); while (s.length < n) s += " "; return s; }
  function lpad(s, n) { s = String(s); while (s.length < n) s = " " + s; return s; }
  /* core.js supplies these in the browser; the text generator must also run in
     the headless harness, which loads only the DOM-free layers. */
  function comma(v) {
    if (FM.comma) return FM.comma(v);
    if (v === null || v === undefined || !isFinite(v)) return "—";
    return String(Math.round(v)).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }
  function n2(v, d) {
    if (v === null || v === undefined || !isFinite(v)) return "—";
    return Number(v).toFixed(d === undefined ? 2 : d);
  }
  function wrap(text, width, indent) {
    var words = String(text).split(/\s+/), lines = [], line = "";
    width = width || 76;
    for (var i = 0; i < words.length; i++) {
      if (line && (line + " " + words[i]).length > width) { lines.push(line); line = ""; }
      line = line ? line + " " + words[i] : words[i];
    }
    if (line) lines.push(line);
    return lines.map(function (l, i) { return (i && indent ? indent : "") + l; });
  }

  /* ---------------- the record ---------------- */

  function scheduleText(plan, pack, opts) {
    opts = opts || {};
    var res = FM.solver.solvePlan(plan, pack);
    var L = [];
    function say(s) { L.push(s === undefined ? "" : s); }
    function block(title) { say(); say(rule("=")); say(title); say(rule("=")); say(); }

    /* ---- header ---- */
    say("FIRMARK — MEMBER SCHEDULE (beta)");
    say(rule("="));
    say("Plan          : " + plan.name + " — " + plan.summary);
    say("Region pack   : " + pack.name + " · " + pack.markets);
    say("Code family   : " + (pack.code ? pack.code.family : "—") +
        "   Firm DCR target: " + n2(pack.maxDCR));
    say("Basis         : NDS 2024 ASD · ASCE 7 §2.4 · deflection per IBC Table 1604.3");
    if (opts.at) say("Generated     : " + opts.at);
    say();
    say("NOT SEALED ENGINEERING. A licensed engineer must review the inputs, the");
    say("assumptions and the results and take professional responsibility for them.");
    say("This schedule is a gravity member check and is not a design (see SCOPE).");

    /* ---- the thing a wind-governed market must read first ---- */
    if (pack.governs === "wind") {
      say();
      say(rule("!"));
      say("!! GRAVITY ONLY — WIND GOVERNS IN THIS MARKET");
      say(rule("!"));
      wrap(pack.governsNote, 76).forEach(say);
    }
    if (plan.note) { say(); wrap("PLAN NOTE — " + plan.note, 76, "  ").forEach(say); }
    if (pack.exteriorWallNote) { say(); wrap("WALL SYSTEM — " + pack.exteriorWallNote, 76, "  ").forEach(say); }

    /* ---- what was and was not answered ---- */
    var r = res.rollup;
    block("SUMMARY");
    say("  Marks on the plan          : " + plan.marks.length);
    say("  Members proposed           : " + r.solved);
    say("  Escalated (no member)      : " + r.escalated);
    say("  Not this engine's member   : " + r.notApplicable);
    say("  Distinct SKUs              : " + r.skuCount);
    say("  Modelled cost per house    : $" + comma(r.lumberUSD) + "   (market placeholders — see PROVENANCE)");
    say();
    if (!r.complete) {
      say("  ** THIS IS NOT A COMPLETE SCHEDULE — " + String(r.incompleteBecause).toUpperCase() + " **");
      say("  Do not read the members below as a finished design.");
    }

    /* ---- the members ---- */
    block("MEMBER SCHEDULE");
    say("  " + pad("MARK", 12) + pad("MEMBER", 34) + pad("SPACING", 10) +
        pad("GOVERNS", 14) + lpad("DCR", 6));
    say("  " + rule("-").slice(0, 76));
    res.marks.forEach(function (m) {
      if (m.notApplicable) {
        say("  " + pad(m.mark.id, 12) + pad("— not sized —", 34) + "see NOT SIZED below");
        return;
      }
      var row = m.unifiedTo || (m.solution && m.solution.pick);
      if (!row) {
        say("  " + pad(m.mark.id, 12) + pad("— ESCALATED —", 34) + "see ESCALATIONS below");
        return;
      }
      say("  " + pad(m.mark.id, 12) +
          pad(row.cand.size + " " + row.cand.species + " " + row.cand.grade, 34) +
          pad(row.cand.spacing ? row.cand.spacing + "\" o.c." : "single", 10) +
          pad(row.governing, 14) + lpad(n2(row.dcr, 3), 6) +
          (m.unifiedTo ? "  [unified]" : ""));
      say("  " + pad("", 12) + m.mark.label + " · span " + n2(m.mark.span, 1) + " ft" +
          (m.demand.trib ? " · tributary " + n2(m.demand.trib, 2) + " ft" : "") +
          " · bearing " + n2(m.demand.bearing, 2) + " in" +
          " · " + (m.demand.wet ? "wet service" : "dry") +
          (m.demand.treated ? ", treated" : "") +
          (m.demand.braced ? ", braced" : ", UNBRACED"));
    });

    /* ---- reactions: the number the next designer actually needs ---- */
    block("REACTION SCHEDULE");
    say("  Unreduced support reaction at each bearing, governing gravity combination.");
    say("  The §3.4.3.1 shear reduction is a shear allowance and is never applied to a");
    say("  reaction. NO CONNECTION IS DESIGNED HERE (calc-spec §8 item 17).");
    say();
    say("  " + pad("MARK", 12) + pad("REACTION", 14) + "GOVERNING COMBINATION");
    say("  " + rule("-").slice(0, 76));
    res.marks.forEach(function (m) {
      var rx = m.solution && m.solution.reactions;
      if (!rx || !rx.perBearingLb) return;
      say("  " + pad(m.mark.id, 12) + pad(comma(rx.perBearingLb) + " lb", 14) + rx.combo);
    });

    /* ---- what it refused to answer, and why ---- */
    var esc = res.marks.filter(function (m) { return !m.notApplicable && m.solution && !m.solution.pick; });
    if (esc.length) {
      block("ESCALATIONS — " + esc.length + " MARK(S) HAVE NO MEMBER");
      esc.forEach(function (m) {
        var s = m.solution;
        say("  " + m.mark.id + " — " + m.mark.label);
        say("    status : " + s.status);
        wrap("wall   : " + (s.note ? s.note.wall : "—"), 74, "             ").forEach(function (x) { say("    " + x); });
        wrap("next   : " + (s.note ? s.note.move : "—"), 74, "             ").forEach(function (x) { say("    " + x); });
        if (s.note && s.note.outOfScope) {
          wrap(s.note.outOfScope, 74, "             ").forEach(function (x) { say("             " + x); });
        }
        say();
      });
    }

    /* ---- and what it declined to treat as its own member ---- */
    var na = res.marks.filter(function (m) { return m.notApplicable; });
    if (na.length) {
      block("NOT SIZED — " + na.length + " MARK(S) ARE NOT THIS ENGINE'S MEMBER");
      say("  Carried deliberately. A schedule that omits them reads as if they were fine.");
      say();
      na.forEach(function (m) {
        say("  " + m.mark.id + " — " + m.mark.label + "   [" + m.notApplicable.reason + "]");
        wrap(m.notApplicable.note, 72, "    ").forEach(function (x) { say("    " + x); });
        say();
      });
    }

    /* ---- anything the search flagged as not checked ---- */
    var adv = [];
    res.marks.forEach(function (m) {
      (m.solution && m.solution.advisories || []).forEach(function (a) {
        adv.push({ id: m.mark.id, text: a.text });
      });
    });
    if (adv.length) {
      block("ADVISORIES — CASES THIS ENGINE DID NOT CHECK");
      adv.forEach(function (a) {
        wrap(a.id + " — " + a.text, 74, "    ").forEach(function (x) { say("  " + x); });
        say();
      });
    }

    /* ---- unification, so the reader knows a member was raised for economics ---- */
    var moves = (res.unified || []).filter(function (u) { return u.accepted; });
    if (moves.length) {
      block("SKU UNIFICATION");
      say("  Members raised for repeatability, not for capacity. Every raised member");
      say("  passed its own check at its own span and load before it was raised.");
      say();
      moves.forEach(function (u) {
        say("  " + u.group + " → " + u.target + "   (extra lumber $" + n2(u.extraLumberUSD) +
            " vs modelled SKU saving $" + n2(u.skuSavingUSD) + ")");
        u.raised.forEach(function (x) { say("      " + x.mark + ": " + x.from + " → " + x.to); });
      });
    }

    /* ---- purchase list ---- */
    block("SKU LIST");
    Object.keys(r.skus).sort().forEach(function (k) {
      say("  " + lpad(r.skus[k], 5) + "  " + k);
    });

    /* ---- where the loads came from ---- */
    block("DESIGN LOADS AND THEIR PROVENANCE");
    var A = FM.weights.ASSEMBLY;
    say("  Roof assembly    : " + A[pack.loads.roofAssembly].label + " · " +
        A[pack.loads.roofAssembly].psf + " psf  [market takeoff, not code]");
    say("      " + A[pack.loads.roofAssembly].makeup);
    say("  Floor assembly   : " + A[pack.loads.floorAssembly].label + " · " +
        A[pack.loads.floorAssembly].psf + " psf  [market takeoff, not code]");
    say("  Floor live       : " + pack.loads.floorLive + " psf  [code — " + FM.weights.LIVE.floor_residential.cite + "]");
    say("  Design roof load : " + pack.loads.roofLoad + " psf · " +
        (pack.loads.roofType === "snow" ? "snow, C_D 1.15" : "roof live, C_D 1.25"));
    say();
    wrap("ROOF LOAD BASIS — " + pack.loads.roofLoadBasis, 74, "    ").forEach(function (x) { say("  " + x); });
    say();
    say("  SITE VALUES BELOW ARE PLANNING DEFAULTS, NOT SITE VALUES. Replace them from");
    say("  the ASCE 7 Hazard Tool and the AHJ before anything is stamped.");
    ["groundSnow", "roofLive", "windMph", "exposure", "sdc"].forEach(function (k) {
      var c = pack.climate[k];
      if (!c) return;
      say("      " + pad(k, 14) + pad(String(c.v), 10) + "[" + c.cls + "]" + (c.note ? "  " + c.note : ""));
    });
    say();
    if (pack.code && pack.code.note) {
      wrap("CODE — " + pack.code.note, 74, "    ").forEach(function (x) { say("  " + x); });
    }
    if (pack.code && pack.code.deflectionTable) {
      say();
      wrap("DEFLECTION TABLE — " + pack.code.deflectionTable, 74, "    ").forEach(function (x) { say("  " + x); });
    }
    say();
    say("  Prices, availability, labor and SKU weights are FIRM PLACEHOLDERS with no");
    say("  code standing. They rank members that already passed; they cannot make a");
    say("  member pass. Availability, however, decides which members are offered at all.");

    /* ---- provenance of the material values ---- */
    var meta = (typeof window !== "undefined" && window.MATDATA && window.MATDATA.meta) || {};
    block("MATERIAL PROVENANCE");
    say("  Reference design values : " + ((meta.species_grades && meta.species_grades.source_file) || "—"));
    say("                            revision " + ((meta.species_grades && meta.species_grades.dataset_version) || "—"));
    say("  Section properties      : " + ((meta.sections && meta.sections.source_file) || "—"));
    say("                            revision " + ((meta.sections && meta.sections.dataset_version) || "—"));
    say("  Southern Pine           : " + ((meta.southern_pine && meta.southern_pine.source_file) || "—"));
    say();
    say("  C_F basis is printed per member on its calculation sheet. A value shown as");
    say("  'repo-partial' comes from a catalog field the catalog itself declares is for");
    say("  threshold testing only, and is not a citable published size-factor table.");

    /* ---- the 24, verbatim ---- */
    block("SCOPE BOUNDARIES — calc-spec §8, VERBATIM AND UNABRIDGED");
    wrap(FM.scope.preamble, 76).forEach(say);
    say();
    var group = null;
    FM.scope.items.forEach(function (it) {
      if (it.group !== group) { group = it.group; say(); say("  " + group.toUpperCase()); say(); }
      var head = "  " + lpad(it.n, 3) + ". ";
      var lines = wrap(it.text, 70);
      say(head + lines[0]);
      lines.slice(1).forEach(function (x) { say("       " + x); });
    });
    say();
    say("  Source: " + FM.scope.source + ". Reproduced in full, not paraphrased.");

    say();
    say(rule("="));
    say("END OF SCHEDULE — " + plan.name + " / " + pack.name);
    say(rule("="));
    return L.join("\n");
  }

  function download(text, filename) {
    var blob = new Blob([text], { type: "text/plain" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
  }

  function exportSchedule(plan, pack) {
    var text = scheduleText(plan, pack, { at: new Date().toISOString().slice(0, 16).replace("T", " ") + " UTC" });
    download(text, "firmark-schedule-" + plan.id + "-" + pack.id + ".txt");
    if (FM.toast) FM.toast("Schedule exported — carries calc-spec §8 in full.");
  }

  FM.exportSchedule = exportSchedule;
  FM.scheduleText = scheduleText;
})();

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

   Three things it must not do, each of which it did once:

   1. State the deflection basis as "IBC Table 1604.3" flat. Every pack
      declares code.family "IRC", and IRC Table R301.7 has no D + L
      column at all — so the total-load row is a firm overlay, not a
      code citation. It is now derived from the pack's own declaration.
   2. Keep the C_F provenance caveat as a paragraph at the back. C_F is
      a function of depth, so it is a fact about the member that was
      picked; it is printed on the member.
   3. Restate engine.js's LIMITS in prose. That list is maintained
      elsewhere and it grows, so it is rendered from the array.

   And a schedule for a MASTER SET — one stamped plan reused across
   elevations and options — that does not say which variant it covers is
   not a usable document. Where weights.js exposes variantsFor(), the
   record names the variant and partitions the marks that move across
   the set from the ones that do not. Where it does not, none of that
   is guessed at and the record is unchanged.
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
  function isArr(v) { return Object.prototype.toString.call(v) === "[object Array]"; }
  function str(v, dflt) {
    return (v === null || v === undefined || v === "") ? (dflt === undefined ? "" : dflt) : String(v);
  }

  /* ---------------- the deflection basis ----------------

     This line used to read "deflection per IBC Table 1604.3", unconditionally,
     on every schedule. Every region pack in the product declares
     `code.family: "IRC"` — repeatable one- and two-family homes are permitted
     under the IRC — and IRC Table R301.7 has NO total-load (D + L) column at
     all. So the total-load row this tool reports against every member is a
     FIRM OVERLAY, an IBC-derived limit carried on top of what the IRC asks
     for. Printing it as a code citation asserted a basis these markets do not
     have. The pack tells us which family it is; say what follows from that. */

  function codeFamily(pack) {
    return (pack && pack.code && str(pack.code.family)) || "not declared";
  }
  function deflHeadline(pack) {
    var fam = codeFamily(pack);
    if (fam === "IBC") return "IBC Table 1604.3 — the code family this pack declares";
    if (fam === "not declared")
      return "IBC Table 1604.3 rows — this pack declares no code family (see DEFLECTION BASIS)";
    return "IBC Table 1604.3 rows, applied as a FIRM OVERLAY — this market builds " +
           "under the " + fam + " (see DEFLECTION BASIS)";
  }

  /* C_F moves with the depth, so it is a property of the picked member and not
     of the schedule. Returns the record only where the basis is one the reader
     has to act on — `held` (catalog silent, held at 1.00) or `repo_partial` (a
     threshold-testing field, not a citable table). */
  function cfBasisOf(cand) {
    if (!FM.engine || typeof FM.engine.sizeFactor !== "function") return null;
    var cf;
    try { cf = FM.engine.sizeFactor(cand.species, cand.grade, cand.size); } catch (e) { return null; }
    if (!cf || (cf.basis !== "held" && cf.basis !== "repo_partial")) return null;
    return { CF: Number(cf.CF), basis: String(cf.basis), note: str(cf.note) };
  }

  /* ---------------- master sets ----------------

     A production plan is one stamped set reused across elevations and options.
     `weights.js` exposes them as FM.weights.variantsFor(plan). The helper is
     not in every build, so everything below is written to return null rather
     than guess — a schedule with no variant section is the old schedule,
     byte for byte. When it IS present, a schedule that does not name the
     elevation and option set it covers is not a usable document, and the
     solver optimises one demand per mark, so it is not an envelope either. */

  function normVariant(v, kind) {
    if (!v || typeof v !== "object") return null;
    var over = v.overrides || v.markOverrides || v.marks || null, ids = [];
    if (over && typeof over === "object") {
      if (isArr(over)) {
        over.forEach(function (o) {
          var mid = o && (o.mark || o.markId || o.id);
          if (mid) ids.push(String(mid));
        });
      } else {
        Object.keys(over).forEach(function (k) { ids.push(String(k)); });
      }
    }
    var tr = Number(v.takeRate);
    return {
      id: str(v.id, str(v.name, str(v.label, "(unnamed)"))),
      label: str(v.label, str(v.name, str(v.id, ""))),
      kind: kind,
      takeRate: isFinite(tr) && v.takeRate !== undefined && v.takeRate !== null ? tr : null,
      base: !!(v.base || v.isBase || v['default']),
      marks: ids
    };
  }

  function variantInfo(plan, opts) {
    if (!FM.weights || typeof FM.weights.variantsFor !== "function") return null;
    var raw;
    try { raw = FM.weights.variantsFor(plan); } catch (e) { return null; }
    if (!raw || typeof raw !== "object") return null;

    var elevations = [], options = [];
    function take(v) {
      /* an entry that prices a take rate is an option; anything else is an
         elevation. Classify from the entry, not from the key we found it under,
         so a flat list works too. */
      var kind = str(v && (v.kind || v.type)) ||
                 ((v && v.takeRate !== undefined && v.takeRate !== null) ? "option" : "elevation");
      var n = normVariant(v, kind === "option" ? "option" : "elevation");
      if (!n) return;
      (n.kind === "option" ? options : elevations).push(n);
    }
    if (isArr(raw)) raw.forEach(take);
    else {
      if (isArr(raw.elevations)) raw.elevations.forEach(function (v) { take(v); });
      if (isArr(raw.options)) raw.options.forEach(function (v) { take(v); });
      if (isArr(raw.variants)) raw.variants.forEach(take);
    }
    if (!elevations.length && !options.length) return null;

    /* which one the members below were actually solved for */
    var sf = (opts && opts.variant) || (!isArr(raw) && (raw.solvedFor || raw.current)) ||
             plan.variant || plan.variantId || plan.elevation || null;
    var solvedFor = null;
    if (sf && typeof sf === "object") solvedFor = str(sf.label, str(sf.name, str(sf.id, "")));
    else if (sf) solvedFor = String(sf);
    if (!solvedFor) {
      var b = elevations.filter(function (e) { return e.base; })[0];
      if (b) solvedFor = b.label || b.id;
    }

    /* a mark any variant overrides is a mark that moves across the set */
    var by = {}, order = [];
    elevations.concat(options).forEach(function (v) {
      v.marks.forEach(function (mid) {
        var k = " " + mid;                     /* author strings as keys */
        if (!Object.prototype.hasOwnProperty.call(by, k)) { by[k] = []; order.push(mid); }
        by[k].push((v.kind === "option" ? "option " : "elevation ") + (v.label || v.id));
      });
    });
    var changing = order.map(function (mid) { return { mark: mid, by: by[" " + mid] }; });
    var changed = {};
    order.forEach(function (mid) { changed[" " + mid] = true; });
    var common = plan.marks.filter(function (mk) {
      return !Object.prototype.hasOwnProperty.call(changed, " " + mk.id);
    }).map(function (mk) { return mk.id; });

    return { elevations: elevations, options: options, solvedFor: solvedFor,
             declared: !!sf, changing: changing, common: common };
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
    var vi = variantInfo(plan, opts);
    if (vi) {
      say("Variant       : " + (vi.solvedFor ? vi.solvedFor : "NOT DECLARED — base marks as the plan carries them") +
          "   (master set — see MASTER SET)");
    }
    say("Code family   : " + codeFamily(pack) +
        "   Firm DCR target: " + n2(pack.maxDCR));
    say("Basis         : NDS 2024 ASD · ASCE 7 §2.4");
    /* wrap() collapses runs of whitespace, so the label cannot go through it */
    wrap(deflHeadline(pack), 60).forEach(function (x, i) {
      say((i ? pad("", 16) : "Deflection    : ") + x);
    });
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

    /* ---- which of the master set's variants this actually is ---- */
    if (vi) {
      block("MASTER SET — WHAT THIS SCHEDULE COVERS");
      say("  Solved for   : " + (vi.solvedFor ? vi.solvedFor : "NOT DECLARED"));
      say("  Master set   : " + vi.elevations.length + " elevation(s), " + vi.options.length + " option(s)");
      say();
      if (!vi.declared && !vi.solvedFor) {
        say("  ** THE VARIANT IS NOT DECLARED. The members were solved from the plan's");
        say("     base marks. Do not issue this against a specific elevation or option");
        say("     set until the variant is named. **");
        say();
      }
      say("  ** ONE VARIANT, NOT AN ENVELOPE. The solver optimises one demand per mark.");
      say("     The members above are sized for the variant named here and for nothing");
      say("     else. Sizing a base elevation and letting an option move a bearing is");
      say("     how a revision gets manufactured. **");
      say();
      if (vi.elevations.length) {
        say("  ELEVATIONS");
        vi.elevations.forEach(function (e) {
          say("      " + pad(e.label || e.id, 26) + (e.base ? "[base]  " : "        ") +
              (e.marks.length ? "overrides " + e.marks.length + " mark(s): " + e.marks.join(", ")
                              : "no mark overrides declared"));
        });
        say();
      }
      if (vi.options.length) {
        say("  OPTIONS");
        vi.options.forEach(function (o) {
          say("      " + pad(o.label || o.id, 26) +
              pad(o.takeRate === null ? "take rate —" : "take rate " + n2(o.takeRate * 100, 0) + "%", 18) +
              (o.marks.length ? "overrides " + o.marks.length + " mark(s): " + o.marks.join(", ")
                              : "no mark overrides declared"));
        });
        say();
      }
      say("  MARKS THAT CHANGE ACROSS THE MASTER SET — " + vi.changing.length);
      if (!vi.changing.length) say("      (none declared)");
      vi.changing.forEach(function (c) {
        var onPlan = plan.marks.filter(function (mk) { return mk.id === c.mark; })[0];
        /* wrap() collapses whitespace, so the mark column is applied outside it */
        wrap((onPlan ? "" : "(not a mark on this plan) ") + "moved by: " + c.by.join(", "), 58)
          .forEach(function (x, i) { say("      " + (i ? pad("", 14) : pad(c.mark, 14)) + x); });
      });
      say();
      say("  MARKS COMMON TO EVERY VARIANT — " + vi.common.length);
      if (!vi.common.length) say("      (none)");
      else wrap(vi.common.join(", "), 68).forEach(function (x) { say("      " + x); });
      say();
      say("  A mark is listed as common because NO variant declares an override on it.");
      say("  That is a statement about the declared inputs, not a re-check: nothing here");
      say("  was re-solved against every variant, and a shared input that moves — a plate");
      say("  height, a truss direction — still moves a mark nobody overrode.");
    }

    /* ---- the members ---- */
    block("MEMBER SCHEDULE");
    say("  " + pad("MARK", 12) + pad("MEMBER", 34) + pad("SPACING", 10) +
        pad("GOVERNS", 14) + lpad("DCR", 6));
    say("  " + rule("-").slice(0, 76));
    var cfFlagged = 0;
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
      /* The C_F caveat used to live only in a general paragraph at the back of
         the record, which made it a disclaimer rather than a fact about a
         member. C_F is a function of depth, so it is a property of THIS pick —
         print its basis on the mark that carries it. */
      var cf = cfBasisOf(row.cand);
      if (cf) {
        cfFlagged++;
        wrap("C_F " + n2(cf.CF, 3) + " · basis " + cf.basis + (cf.note ? " — " + cf.note : ""), 60, "  ")
          .forEach(function (x) { say("  " + pad("", 12) + x); });
      }
    });
    if (cfFlagged) {
      say();
      say("  C_F BASIS, printed above on the " + cfFlagged + " member(s) whose size factor is");
      say("  not sourced. 'repo_partial' is a catalog field the catalog itself declares is");
      say("  for threshold testing only — it is not a citable published size-factor table.");
      say("  'held' means the catalog is silent and C_F is held at 1.00, which is");
      say("  conservative below 14 in; 14 in and wider is refused outright, not held.");
    }

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
    say();
    say("  Prices, availability, labor and SKU weights are FIRM PLACEHOLDERS with no");
    say("  code standing. They rank members that already passed; they cannot make a");
    say("  member pass. Availability, however, decides which members are offered at all.");

    /* ---- the deflection basis, which is not the citation it used to print ---- */
    var fam = codeFamily(pack);
    block("DEFLECTION BASIS");
    say("  Code family declared by this pack : " + fam);
    say("  Deflection rows used by the engine: IBC Table 1604.3");
    say();
    if (fam !== "IBC") {
      var famReq = fam === "not declared" ? "a code requirement" : "an " + fam + " requirement";
      wrap("This schedule reports a TOTAL-LOAD (D + L) deflection row against every " +
           "member. IRC Table R301.7 — the table that governs one- and two-family " +
           "dwellings, which is what these plans are — has NO total-load column at all. " +
           "That row is therefore a FIRM OVERLAY this tool applies on top of the code, " +
           "not " + famReq + ". It adds a check the code does not ask for, so on that row " +
           "this schedule is more conservative than the code and not less: a member " +
           "governed by total-load deflection is deeper than the code compels. The " +
           "live-load rows do have counterparts in R301.7 — they are not reproduced here " +
           "and must be verified against the adopted edition.", 74, "  ")
        .forEach(function (x) { say("  " + x); });
      say();
    }
    /* rendered from the engine's own table, not restated, so a row that moves
       moves here too */
    var D = FM.engine && FM.engine.DEFL;
    if (D) {
      say("  Rows as the engine carries them (its citation strings, verbatim):");
      Object.keys(D).forEach(function (k) {
        var row = D[k] || {};
        say("      " + pad(k, 18) +
            pad("live ℓ/" + str(row.live, "—"), 12) +
            pad("total ℓ/" + str(row.total, "—"), 13) + str(row.cite, "—"));
      });
      say();
      if (D.roof_no_ceiling && Number(D.roof_no_ceiling.total) === 180) {
        wrap("NOTE — the roof/no-ceiling total row is carried at ℓ/180 where the " +
             "printed table gives ℓ/120. That is a firm overlay held deliberately and " +
             "in the conservative direction; the citation string beside it names the " +
             "table, which is not where the number comes from.", 74, "  ")
          .forEach(function (x) { say("  " + x); });
        say();
      }
    }
    if (pack.code && pack.code.deflectionTable) {
      wrap("PACK STATEMENT — " + pack.code.deflectionTable, 74, "    ").forEach(function (x) { say("  " + x); });
    } else {
      say("  This pack carries no `code.deflectionTable` statement of its own, so the");
      say("  paragraph above is derived from its declared code family alone. Read it");
      say("  against the pack's CODE note under DESIGN LOADS — a state that amends the");
      say("  deflection table (Florida does) amends what is written here.");
    }

    /* ---- provenance of the material values ---- */
    var meta = (typeof window !== "undefined" && window.MATDATA && window.MATDATA.meta) || {};
    block("MATERIAL PROVENANCE");
    say("  Reference design values : " + ((meta.species_grades && meta.species_grades.source_file) || "—"));
    say("                            revision " + ((meta.species_grades && meta.species_grades.dataset_version) || "—"));
    say("  Section properties      : " + ((meta.sections && meta.sections.source_file) || "—"));
    say("                            revision " + ((meta.sections && meta.sections.dataset_version) || "—"));
    say("  Southern Pine           : " + ((meta.southern_pine && meta.southern_pine.source_file) || "—"));
    say();
    say("  C_F basis is printed PER MEMBER in the schedule above, on every mark whose");
    say("  size factor is held or repo_partial, and again on that member's calculation");
    say("  sheet. A value shown as 'repo_partial' comes from a catalog field the catalog");
    say("  itself declares is for threshold testing only, and is not a citable published");
    say("  size-factor table.");

    /* ---- the engine's own boundaries, as the engine declares them ----
       LIMITS is maintained in engine.js and grows: it is where calc-spec §1.4's
       slope statement and the absence of any wall dead load were put. Rendering
       the array rather than restating it means an item added there reaches the
       schedule without anyone remembering to copy it. It is NOT a summary of
       the 24 below — the two lists overlap and neither replaces the other. */
    var lim = (FM.engine && FM.engine.LIMITS) || null;
    if (lim && lim.length) {
      block("ENGINE LIMITS — " + lim.length + " ITEM(S), AS engine.js DECLARES THEM");
      say("  Printed from FM.engine.LIMITS, the check's own list. This is not a summary");
      say("  of the calc-spec §8 boundaries below and does not replace them — read both.");
      say();
      lim.forEach(function (t, i) {
        var lines = wrap(String(t), 70);
        say("  " + lpad(i + 1, 3) + ". " + lines[0]);
        lines.slice(1).forEach(function (x) { say("       " + x); });
      });
    }

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

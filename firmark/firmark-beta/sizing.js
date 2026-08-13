/* ============================================================
   Sizing — the solver's surface.

   Four questions this view has to answer, in order:
     1. What member did it pick, and by how much did it pass?
     2. What did it reject, and why — including what it never
        evaluated, and on what grounds.
     3. What changes when the same plan is built in another state?
     4. What changes when the buyer picks the other elevation, or
        the tile roof, or the bonus room?

   A recommendation with no visible runner-up is a black box, which
   is the thing this product exists not to be. The same applies to
   an option that moves a bearing: a schedule that only sizes the
   base case is how a post-permit revision gets manufactured.

   MASTER-SET CONTRACT (weights.js) — read defensively, all of it
   optional. Nothing extra renders unless BOTH of these are true:
     · FM.weights.variantsFor(plan) exists and returns variants;
     · FM.weights.demandFor accepts a 4th argument (variant id),
       or a probe shows a variant actually moves a demand.
   variantsFor(plan) may return {elevations:[], options:[]},
   {variants:[]}, or a flat array. An entry may be a string id or
   an object with id|key|code|name, label|name|title, takeRate
   (0-1 or 0-100), note|description, and marks|overrides (object
   keyed by mark id, or an array of ids) — every field optional.
   demandFor(mark, plan, pack, variantId) takes one id; whether it
   also takes an ARRAY of ids (an elevation + an option together)
   is probed at runtime and the picker falls back to one-at-a-time
   when it is not honoured.
   ============================================================ */

(function () {
  "use strict";

  var el = FM.el, card = FM.card, dl = FM.dl, fmt = FM.fmt, esc = FM.esc;

  function usd(n) {
    if (n === null || n === undefined || !isFinite(n)) return "—";
    return "$" + Number(n).toFixed(2);
  }
  function usd0(n) {
    if (n === null || n === undefined || !isFinite(n)) return "—";
    return "$" + FM.comma(n);
  }
  function utilClass(d) { return d > 1 ? "is-fail" : (d > 0.9 ? "is-warn" : "is-pass"); }
  function plural(n, one, many) { return String(n) + " " + (n === 1 ? one : many); }
  function own(o, k) {
    return o && Object.prototype.hasOwnProperty.call(o, k) ? o[k] : undefined;
  }
  /* author-supplied ids never touch a bare object key */
  function key(s) { return "k:" + String(s); }
  function isArr(x) { return Object.prototype.toString.call(x) === "[object Array]"; }

  /* every number in a pack says what kind of number it is */
  var CLASSES = {
    code:   { c: "b-blue", t: "Code" },
    site:   { c: "b-warn", t: "Site" },
    market: { c: "b-mute", t: "Market" }
  };
  function classBadgeHtml(cls) {
    var m = own(CLASSES, cls);
    if (!m) return "";
    return " <span class='badge " + m.c + "' style='margin-left:6px'>" + m.t + "</span>";
  }

  function spacingText(cand) {
    return cand.spacing ? cand.spacing + "″ o.c." : "single";
  }
  function skuText(cand) {
    return cand.size + " " + cand.species + " " + cand.grade;
  }
  var SHORT = [["Southern Pine", "SYP"], ["Spruce-Pine-Fir", "SPF"],
               ["Douglas Fir-Larch", "DF-L"], ["Hem-Fir", "Hem-Fir"]];
  function shortSku(s) {
    var out = String(s), i;
    for (i = 0; i < SHORT.length; i++) out = out.replace(SHORT[i][0], SHORT[i][1]);
    return out;
  }
  /* six column headings have to fit on one board */
  function shortPack(p) {
    var parts = String(p.name).split(" · ");
    var region = parts.length > 1 ? parts[1] : parts[0];
    region = region.replace("High-Velocity Hurricane Zone", "HVHZ")
                   .replace(" corridor", "").replace("Mountains", "Mtns");
    var st = p.states && p.states.length ? p.states.join("/") : "";
    return (st ? st + " " : "") + region;
  }

  /* the four first-class escalation statuses, each named for what a
     reader has to DO about it */
  var ESC = {
    "escalate:strength":    { t: "No section reaches it", b: "strength" },
    "escalate:bearing":     { t: "Bearing — a detailing fix, not a bigger member", b: "bearing" },
    "escalate:geometry":    { t: "Will not fit the depth budget", b: "geometry" },
    "escalate:procurement": { t: "Procurement, not engineering", b: "procurement" },
    "escalate:scope":       { t: "Beyond solid sawn", b: "scope" },
    "escalate:input":       { t: "Nothing was checked — the demand is not numeric", b: "input" }
  };
  function escInfo(status) {
    return own(ESC, status) ||
      { t: "Beyond solid sawn", b: String(status || "escalate").replace("escalate:", "") };
  }

  var NA = {
    component:       { t: "Manufactured component", c: "b-blue" },
    "wall-system":   { t: "Not a wood member here", c: "b-blue" },
    "out-of-scope":  { t: "Out of this engine's scope", c: "b-warn" },
    underdetermined: { t: "Not sized — tributary not derivable", c: "b-warn" }
  };
  function naInfo(reason) {
    return own(NA, reason) || { t: "Not this engine's member", c: "b-blue" };
  }

  /* a DCR bar with the firm's own target marked on it */
  function dcrMeter(dcr, target, governing) {
    var kids = [el("span", {
      class: "meter-fill " + (dcr > 1 ? "fail" : (dcr > 0.9 ? "warn" : "")),
      style: "display:block;width:" + Math.max(0, Math.min(100, dcr * 100)) + "%"
    })];
    if (isFinite(target)) {
      kids.push(el("span", { class: "meter-cap",
        style: "left:" + Math.max(0, Math.min(100, target * 100)) + "%" }));
    }
    return el("div", { class: "meter" }, [
      el("div", { class: "meter-bar" }, kids),
      el("div", { class: "meter-legend" }, [
        el("span", { text: "0.00" }),
        el("span", { text: "DCR " + fmt(dcr, 3) + " · " + (governing || "governing") +
                           (isFinite(target) ? " · firm target " + fmt(target, 2) : "") }),
        el("span", { text: "1.00" })
      ])
    ]);
  }

  /* ============================================================
     Master set — elevations and options
     ============================================================ */

  var MAX_VARIANTS = 8;      /* an envelope, not a combinatorial explosion */
  var MCACHE = {};           /* plan+pack -> computed envelope; the data is static */

  function normVariant(v, kind) {
    if (v === null || v === undefined) return null;
    if (typeof v === "string") {
      return { id: v, label: v, kind: kind, takeRate: null, note: null, marks: null };
    }
    if (typeof v !== "object") return null;
    var id = v.id || v.key || v.code || v.name;
    if (!id) return null;
    var tr = Number(v.takeRate);
    if (!isFinite(tr)) tr = null; else if (tr > 1) tr = tr / 100;
    var marks = null, mv = v.marks || v.overrides || v.markOverrides;
    if (mv && typeof mv === "object") {
      marks = isArr(mv)
        ? mv.map(function (x) { return typeof x === "string" ? x : (x && (x.id || x.mark)); })
        : Object.keys(mv);
      marks = marks.filter(Boolean);
    }
    return {
      id: String(id),
      label: String(v.label || v.name || v.title || id),
      kind: kind,
      takeRate: tr,
      note: v.note || v.description || null,
      marks: marks && marks.length ? marks : null
    };
  }

  function variantGroups(plan) {
    if (!FM.weights || typeof FM.weights.variantsFor !== "function") return null;
    var raw;
    try { raw = FM.weights.variantsFor(plan); } catch (e) { return null; }
    if (!raw) return null;

    var groups = [];
    function add(kind, label, list) {
      if (!isArr(list)) return;
      var items = [];
      list.forEach(function (v) { var n = normVariant(v, kind); if (n) items.push(n); });
      if (items.length) groups.push({ kind: kind, label: label, items: items });
    }
    if (isArr(raw)) {
      var elev = [], opts = [], other = [];
      raw.forEach(function (v) {
        var k = (v && (v.kind || v.type)) || "";
        if (k === "elevation") elev.push(v);
        else if (k === "option") opts.push(v);
        else other.push(v);
      });
      add("elevation", "Elevation", elev);
      add("option", "Option", opts);
      add("variant", "Variant", other);
    } else if (typeof raw === "object") {
      add("elevation", "Elevation", raw.elevations);
      add("option", "Option", raw.options);
      add("variant", "Variant", raw.variants);
    }
    return groups.length ? groups : null;
  }

  /* Compared on a fixed field list rather than on object identity, so a
     re-ordered demand object is not reported as a change. */
  var DFIELDS = [
    ["span", "span", " ft", 1], ["trib", "tributary", " ft", 1],
    ["tribRoof", "roof tributary", " ft", 1], ["tribFloor", "floor tributary", " ft", 1],
    ["dead", "dead", " psf", 1], ["live", "floor live", " psf", 0],
    ["roofLoad", "roof load", " psf", 0], ["bearing", "bearing", " in", 2],
    ["maxDepthIn", "depth budget", " in", 2]
  ];
  var DFLAGS = [["carries", "carries"], ["memberUse", "deflection row"], ["roofType", "roof case"],
                ["wet", "wet service"], ["treated", "treated"], ["braced", "braced"],
                ["repetitive", "repetitive"]];

  function demandSig(d) {
    if (!d) return "";
    var out = [], i;
    for (i = 0; i < DFIELDS.length; i++) out.push(String(d[DFIELDS[i][0]]));
    for (i = 0; i < DFLAGS.length; i++) out.push(String(d[DFLAGS[i][0]]));
    return out.join("|");
  }
  function demandDelta(a, b) {
    var out = [];
    if (!a || !b) return out;
    DFIELDS.forEach(function (f) {
      var x = Number(a[f[0]]), y = Number(b[f[0]]);
      if (!isFinite(x) && !isFinite(y)) return;
      if (x === y) return;
      out.push(f[1] + " " + fmt(x, f[3]) + " → " + fmt(y, f[3]) + f[2]);
    });
    DFLAGS.forEach(function (f) {
      if (a[f[0]] === b[f[0]]) return;
      if (a[f[0]] === undefined && b[f[0]] === undefined) return;
      out.push(f[1] + " " + String(a[f[0]]) + " → " + String(b[f[0]]));
    });
    return out;
  }

  function safeDemand(mark, plan, pack, vid) {
    try {
      return vid === null || vid === undefined
        ? FM.weights.demandFor(mark, plan, pack)
        : FM.weights.demandFor(mark, plan, pack, vid);
    } catch (e) { return null; }
  }

  /* Solve one mark under one variant, mirroring solvePlan's own order:
     applicability first, then demand, then the search. */
  function solveOne(mark, plan, pack, vid) {
    var appl = FM.weights.applicability
      ? FM.weights.applicability(mark, pack) : { applicable: true };
    if (!appl.applicable) return { na: appl.reason };
    var d = safeDemand(mark, plan, pack, vid);
    if (!d) return { error: true };
    var sol;
    try { sol = FM.solver.size(d, FM.weights.policyFor(pack, plan, mark.role)); }
    catch (e) { return { error: true, demand: d }; }
    return { demand: d, sol: sol, pick: sol && sol.pick ? sol.pick : null };
  }

  /* Does this build accept an elevation AND an option in one call? If a
     single id moves a demand but the pair does not, it does not — and the
     picker becomes one-at-a-time rather than quietly reporting "nothing
     moves" for a combination it never actually asked about. */
  function comboHonoured(plan, pack, groups) {
    if (groups.length < 2) return false;
    function mover(items) {
      var i, j, m, base, alt;
      for (i = 0; i < items.length; i++) {
        for (j = 0; j < plan.marks.length; j++) {
          m = plan.marks[j];
          base = safeDemand(m, plan, pack, null);
          if (!base) continue;
          alt = safeDemand(m, plan, pack, items[i].id);
          if (alt && demandSig(alt) !== demandSig(base)) return { v: items[i], mark: m, base: base };
        }
      }
      return null;
    }
    var a = mover(groups[0].items), b = mover(groups[1].items);
    if (!a || !b) return false;
    var pair = safeDemand(a.mark, plan, pack, [a.v.id, b.v.id]);
    return !!(pair && demandSig(pair) !== demandSig(a.base));
  }

  /* one variant (or one combination) against the base case */
  function deltaFor(plan, pack, vid, base) {
    var rows = [], moved = 0, escalated = 0, recovered = 0, demandOnly = 0;
    plan.marks.forEach(function (mk) {
      var b = own(base, key(mk.id));
      if (!b || b.na) return;                       /* not this engine's member either way */
      var r = solveOne(mk, plan, pack, vid);
      if (r.na || r.error) return;
      var was = b.pick ? skuText(b.pick.cand) : null;
      var now = r.pick ? skuText(r.pick.cand) : null;
      var why = demandDelta(b.demand, r.demand);
      var state = null;
      if (was && !now) { state = "escalates"; escalated++; }
      else if (!was && now) { state = "recovers"; recovered++; }
      else if (was && now && (was !== now ||
               (b.pick.cand.spacing || 0) !== (r.pick.cand.spacing || 0))) { state = "moves"; moved++; }
      else if (why.length) { state = "holds"; demandOnly++; }
      if (!state) return;
      rows.push({
        mark: mk, state: state, was: was, now: now,
        wasSpacing: b.pick ? b.pick.cand.spacing : null,
        nowSpacing: r.pick ? r.pick.cand.spacing : null,
        wasDcr: b.pick ? b.pick.dcr : null, nowDcr: r.pick ? r.pick.dcr : null,
        why: why, note: r.sol && r.sol.note ? r.sol.note : null
      });
    });
    var order = { escalates: 0, moves: 1, recovers: 2, holds: 3 };
    rows.sort(function (x, y) { return order[x.state] - order[y.state]; });
    return { rows: rows, moved: moved, escalated: escalated,
             recovered: recovered, demandOnly: demandOnly };
  }

  /* The envelope: every variant on record, solved, cached per plan+pack. */
  function masterSet(plan, pack, groups) {
    var ck = key(plan.id + "|" + pack.id);
    var hit = own(MCACHE, ck);
    if (hit) return hit;

    var flat = [];
    groups.forEach(function (g) {
      g.items.forEach(function (it) { if (flat.length < MAX_VARIANTS) flat.push(it); });
    });
    var truncated = 0;
    groups.forEach(function (g) { truncated += g.items.length; });
    truncated = truncated - flat.length;

    var base = {};
    plan.marks.forEach(function (mk) {
      var r = solveOne(mk, plan, pack, null);
      base[key(mk.id)] = { na: r.na || null, pick: r.pick || null, demand: r.demand || null };
    });

    var perVariant = flat.map(function (v) {
      return { variant: v, delta: deltaFor(plan, pack, v.id, base) };
    });

    /* union across the whole master set — the envelope a builder buys to */
    var envelope = {};
    perVariant.forEach(function (pv) {
      pv.delta.rows.forEach(function (r) {
        if (r.state === "holds") return;
        var k = key(r.mark.id);
        if (!own(envelope, k)) envelope[k] = { mark: r.mark, hits: [] };
        envelope[k].hits.push({ variant: pv.variant, state: r.state, now: r.now,
                                nowSpacing: r.nowSpacing, why: r.why });
      });
    });
    var envRows = [];
    plan.marks.forEach(function (mk) {
      var e = own(envelope, key(mk.id));
      if (e) envRows.push(e);
    });

    var out = { base: base, groups: groups, variants: flat, perVariant: perVariant,
                envRows: envRows, truncated: truncated,
                combo: comboHonoured(plan, pack, groups) };
    MCACHE[ck] = out;
    return out;
  }

  /* Is the variant argument actually wired through? If demandFor does not
     take it and no probe moves a demand, this whole surface stays dark
     rather than reporting a master set nobody solved. */
  function masterAvailable(plan, pack, groups) {
    if (!groups || !FM.weights || typeof FM.weights.demandFor !== "function") return false;
    if (FM.weights.demandFor.length >= 4) return true;
    var i, j, base, alt;
    for (i = 0; i < groups.length; i++) {
      for (j = 0; j < groups[i].items.length; j++) {
        var m = plan.marks[0];
        if (!m) return false;
        base = safeDemand(m, plan, pack, null);
        alt = safeDemand(m, plan, pack, groups[i].items[j].id);
        if (base && alt && demandSig(base) !== demandSig(alt)) return true;
      }
    }
    return false;
  }

  /* ============================================================
     The view
     ============================================================ */

  FM.VIEWS.sizing = function (host) {
    if (!FM.solver || !FM.weights) {
      host.appendChild(FM.pageHead("Sizing", "Solver"));
      host.appendChild(el("div", { class: "empty", text: "The sizing solver failed to load." }));
      return;
    }

    var state = FM.state.sizing || (FM.state.sizing = {
      packId: "nc-piedmont", planId: "sunbelt-ranch-1850", open: null, tab: "schedule", sel: {}
    });
    if (!state.sel) state.sel = {};

    host.appendChild(FM.pageHead("Sizing",
      "One plan, solved against a region. The engine decides what passes; the weights only rank what already did.", [
        el("button", { class: "btn", onclick: function () { FM.go("materials"); }, text: "Materials" }),
        el("button", { class: "btn btn-primary", text: "Export schedule", onclick: function () {
          var pk = FM.weights.packById(state.packId), pl = FM.weights.planById(state.planId);
          if (pk && pl) FM.exportSchedule(pl, pk);
        } })
      ]));

    host.appendChild(FM.betaStrip(
      "The solver proposes members and shows its work. Prices, availability and site loads in the region packs are " +
      "placeholders — replace them with your own before reading any dollar figure as real. Nothing here is stamped. " +
      "Export carries the escalations, the marks this engine will not size, the reactions, the load provenance and " +
      "calc-spec §8 in full — nothing that qualifies a member should stay in this tab."));

    /* ---------- controls ---------- */

    var packSel = el("select", { "aria-label": "Region pack" }, FM.weights.PACKS.map(function (p) {
      return el("option", { value: p.id, text: p.name + " · " + p.markets, selected: p.id === state.packId ? "selected" : null });
    }));
    var planSel = el("select", { "aria-label": "Plan" }, FM.weights.PLANS.map(function (p) {
      return el("option", { value: p.id, text: p.name + " — " + p.summary, selected: p.id === state.planId ? "selected" : null });
    }));

    var tabs = el("div", { class: "seg", role: "group", "aria-label": "View" }, [
      el("button", { "data-tab": "schedule", text: "Schedule" }),
      el("button", { "data-tab": "region", text: "Region pack" }),
      el("button", { "data-tab": "matrix", text: "Repeat matrix" })
    ]);

    var bar = el("div", { class: "filter-bar", style: "margin-bottom:14px" }, [packSel, planSel,
      el("span", { style: "margin-left:auto" }, [tabs])]);
    host.appendChild(bar);

    var body = el("div");
    host.appendChild(body);

    packSel.addEventListener("change", function () { state.packId = this.value; state.open = null; draw(); });
    planSel.addEventListener("change", function () {
      state.planId = this.value; state.open = null; state.sel = {}; draw();
    });
    Array.prototype.forEach.call(tabs.querySelectorAll("button"), function (b) {
      b.addEventListener("click", function () { state.tab = b.getAttribute("data-tab"); draw(); });
    });

    /* a table row that opens a detail is a disclosure, and announces as one */
    function openRow(id, label, cells) {
      var isOpen = state.open === id;
      function toggle() { state.open = isOpen ? null : id; draw(); }
      return el("tr", {
        class: "clickable", tabindex: "0", role: "button",
        "aria-expanded": isOpen ? "true" : "false",
        "aria-label": (isOpen ? "Hide" : "Show") + " the search record for " + id + " " + label,
        onclick: toggle,
        onkeydown: function (e) {
          if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); }
        }
      }, cells);
    }

    function line(text, note) {
      var kids = [el("span", { text: text })];
      if (note) kids.push(el("span", { class: "clause", text: note }));
      return el("p", { style: "font-size:.85rem;color:var(--muted);margin:12px 0 8px" }, kids);
    }

    /* ---------- schedule ---------- */

    function drawSchedule(res, pack, plan) {
      /* The wind note leads. It is the largest single thing this engine does
         not do in three of the six markets, and it does not get to be a
         footnote under a table of members. */
      if (pack.governs === "wind") {
        body.appendChild(el("div", { class: "banner banner-warn" }, [
          el("strong", { text: "Gravity only — " }),
          el("span", { text: pack.governsNote })
        ]));
      }
      if (plan.note) {
        body.appendChild(el("div", { class: "banner banner-info" }, [
          el("strong", { text: "Plan — " }), el("span", { text: plan.note })
        ]));
      }

      var r = res.rollup;
      var escMarks = res.marks.filter(function (m) {
        return !m.notApplicable && !(m.unifiedTo || (m.solution && m.solution.pick));
      });
      var naMarks = res.marks.filter(function (m) { return m.notApplicable; });

      if (!r.complete) {
        var reasons = [];
        if (r.escalated) {
          reasons.push(plural(r.escalated, "mark", "marks") + " escalated (" +
            escMarks.map(function (m) { return m.mark.id; }).join(", ") + ")");
        }
        if (r.notApplicable) {
          reasons.push(plural(r.notApplicable, "mark is", "marks are") + " not this engine's member");
        }
        if (pack.governs === "wind") reasons.push("wind governs in this market and is not checked here");
        /* if the solver ever adds a reason this view does not model, say it anyway */
        var known = { "marks escalated": 1, "marks removed as not this engine's member": 1,
                      "wind governs in this market and is not checked here": 1 };
        if (r.incompleteBecause && !own(known, r.incompleteBecause)) reasons.push(r.incompleteBecause);
        if (!reasons.length) reasons.push(r.incompleteBecause || "see the notes below");

        body.appendChild(el("div", { class: "banner banner-warn" }, [
          el("strong", { text: "Not a complete schedule — " }),
          el("span", { text: reasons.join("; ") + ". Do not read the sized marks as a finished design." })
        ]));
      }

      body.appendChild(el("div", { class: "grid g5", style: "margin-bottom:6px" }, [
        FM.statCard(String(r.solved) + "/" + plan.marks.length, "Marks sized", r.complete ? "pass" : "gold"),
        FM.statCard(String(r.escalated), "Escalated", r.escalated ? "fail" : ""),
        FM.statCard(String(r.notApplicable), "Not this engine", "blue"),
        FM.statCard(String(r.skuCount), "Distinct SKUs"),
        FM.statCard(usd0(r.lumberUSD), "Lumber $ / house")
      ]));

      body.appendChild(line(
        plural(plan.marks.length, "mark", "marks") + " on this plan" +
        (plan.lots ? ", built on " + plural(plan.lots, "lot", "lots") : "") + ". " +
        r.solved + " sized, " + r.escalated + " escalated, " + r.notApplicable +
        " not this engine's member. " + plural(r.skuCount, "distinct SKU", "distinct SKUs") +
        " across the sized marks.",
        "lumber $ is placeholder-priced and covers the sized marks only"));

      /* ---- master set: what an elevation or an option does to this schedule ---- */
      var groups = variantGroups(plan);
      var ms = groups && masterAvailable(plan, pack, groups)
        ? masterSet(plan, pack, groups) : null;
      var current = ms ? drawMasterSet(ms, plan, pack) : null;

      var tb = el("tbody");
      res.marks.forEach(function (m) {
        var row = m.unifiedTo || (m.solution && m.solution.pick);
        var cells, tr;

        if (m.notApplicable) {
          var na = naInfo(m.notApplicable.reason);
          cells = [
            el("td", { class: "k", text: m.mark.id }),
            el("td", { text: m.mark.label }),
            el("td", { colspan: "4" }, [
              el("span", { class: "badge " + na.c, text: na.t }),
              el("span", { class: "clause", text: "carried below, not dropped" })
            ]),
            el("td", { class: "n", text: "—" })
          ];
          /* nothing opens for these — so they are not announced as buttons */
          tb.appendChild(el("tr", {}, cells));
          return;
        }

        if (!row) {
          var info = escInfo(m.solution.status);
          cells = [
            el("td", { class: "k", text: m.mark.id }),
            el("td", { text: m.mark.label }),
            el("td", { colspan: "4" }, [
              el("span", { class: "badge b-fail", text: "Escalate · " + info.b }),
              el("span", { class: "clause", text: m.solution.note ? m.solution.note.move : info.t })
            ]),
            el("td", { class: "n", text: "—" })
          ];
          tr = openRow(m.mark.id, m.mark.label, cells);
          tb.appendChild(tr);
          return;
        }

        var moveNote = current ? own(current.byMark, key(m.mark.id)) : null;
        var sel = el("td", {}, [
          el("span", { text: skuText(row.cand) }),
          m.unifiedTo ? el("span", { class: "badge b-blue", style: "margin-left:6px", text: "Unified" }) : null,
          moveNote ? el("span", {
            class: "badge " + (moveNote.state === "escalates" ? "b-fail" : "b-gold"),
            style: "margin-left:6px",
            text: moveNote.state === "escalates" ? "escalates on " + current.label
                : (moveNote.state === "moves" ? "→ " + shortSku(moveNote.now) : "load moves")
          }) : null
        ]);

        cells = [
          el("td", { class: "k", text: m.mark.id }),
          el("td", { text: m.mark.label }),
          sel,
          el("td", { class: "n", text: spacingText(row.cand) }),
          el("td", {}, [el("span", { class: "util " + utilClass(row.dcr) }, [
            el("span", { class: "util-k", text: row.governing }),
            el("span", { class: "util-v", text: fmt(row.dcr, 3) })
          ])]),
          el("td", { class: "n", text: fmt(m.mark.span, 1) + " ft" }),
          el("td", { class: "n", text: usd(row.cost.totalUSD) })
        ];
        tb.appendChild(openRow(m.mark.id, m.mark.label, cells));
      });

      body.appendChild(el("div", { class: "tw", tabindex: "0", role: "region", "aria-label": "Member schedule" }, [
        el("table", {}, [
          el("thead", {}, [el("tr", {}, [
            el("th", { text: "Mark" }), el("th", { text: "Member" }), el("th", { text: "Selected" }),
            el("th", { class: "n", text: "Spacing" }), el("th", { text: "Governs · DCR" }),
            el("th", { class: "n", text: "Span" }), el("th", { class: "n", text: "Cost / pc" })
          ])]),
          tb
        ])
      ]));
      body.appendChild(el("p", { class: "src-note", style: "margin-top:8px", text:
        "DCR is demand ÷ capacity at the governing check — 1.00 is the code limit and this pack's firm target is " +
        fmt(pack.maxDCR, 2) + ". Cost is per piece at placeholder prices. Open any sized or escalated row for the full search record." }));

      /* ---- the actionable sentence, above the fold rather than inside a row ---- */
      if (escMarks.length) {
        var eBody = el("div", { style: "display:grid;gap:10px" });
        escMarks.forEach(function (m) {
          var info = escInfo(m.solution.status);
          var n = m.solution.note || {};
          eBody.appendChild(el("div", { style: "display:grid;gap:4px" }, [
            el("div", {}, [
              el("span", { class: "badge b-fail", text: m.mark.id }),
              el("span", { style: "margin-left:8px;font-weight:650", text: m.mark.label }),
              el("span", { class: "clause", text: info.t })
            ]),
            el("p", { style: "font-size:.86rem" }, [
              el("strong", { text: "Next move: " }),
              el("span", { text: n.move || "escalate to an engineer" })
            ]),
            el("p", { class: "src-note", text: "Wall: " + (n.wall || "—") }),
            el("button", {
              class: "btn btn-sm", style: "justify-self:start",
              text: state.open === m.mark.id ? "Hide the search record" : "Show the search record",
              onclick: function () { state.open = state.open === m.mark.id ? null : m.mark.id; draw(); }
            })
          ]));
        });
        body.appendChild(el("div", { style: "margin-top:16px" }, [
          card("Escalated — " + plural(escMarks.length, "mark", "marks"),
            el("span", { class: "badge b-fail", text: "Action required", style: "margin-left:auto" }),
            eBody,
            "An escalation is a member this engine could not deliver, not a member that failed quietly. Each one names the wall it hit and the move that clears it.")
        ]));
      }

      /* ---- and the marks it will not size at all ---- */
      if (naMarks.length) {
        var nBody = el("div", { style: "display:grid;gap:8px" });
        naMarks.forEach(function (m) {
          var na = naInfo(m.notApplicable.reason);
          var note = String(m.notApplicable.note || "");
          var head = el("summary", {}, [
            el("span", { class: "badge " + na.c, text: m.mark.id }),
            el("span", { style: "font-weight:650", text: m.mark.label }),
            el("span", { class: "clause", text: na.t })
          ]);
          nBody.appendChild(el("details", { class: "acc" }, [
            head, el("div", { class: "acc-body" }, [el("p", { style: "font-size:.84rem", text: note })])
          ]));
        });
        body.appendChild(el("div", { style: "margin-top:16px" }, [
          card("Not this engine's member — " + plural(naMarks.length, "mark", "marks"),
            el("span", { class: "badge b-blue", text: "Carried", style: "margin-left:auto" }),
            nBody,
            "Carried deliberately. A schedule that omits them reads as if they were fine — each one is somebody's design, just not this engine's.")
        ]));
      }

      /* the open mark's full search record */
      var openMark = res.marks.filter(function (m) {
        return m.mark.id === state.open && !m.notApplicable;
      })[0];
      if (openMark) body.appendChild(drawSearch(openMark, pack));

      /* SKU unification */
      if (res.unified && res.unified.length) {
        var uRows = res.unified.map(function (u) {
          return {
            k: esc(u.group) + " <span class='clause'>" + u.skusBefore + " SKUs → " +
               (u.accepted ? u.skusAfter : u.skusBefore) + "</span>",
            v: (u.accepted ? "unified to " + esc(u.target) : "kept separate") +
               " · extra lumber " + usd(u.extraLumberUSD) + " vs SKU saving " + usd(u.skuSavingUSD),
            cls: u.accepted ? "pass" : ""
          };
        });
        body.appendChild(el("div", { style: "margin-top:16px" }, [
          card("SKU unification", el("span", { class: "badge b-mute", text: "Repeatability", style: "margin-left:auto" }),
            dl(uRows),
            "Collapses upward only, and only onto a member that already passed its own check")
        ]));
      }
    }

    /* ---------- master set: the option envelope ---------- */

    function drawMasterSet(ms, plan, pack) {
      var wrap = el("div", { style: "display:grid;gap:12px" });

      /* the picker */
      var picks = el("div", { style: "display:grid;gap:8px" });
      ms.groups.forEach(function (g) {
        var seg = el("div", { class: "seg", role: "group", "aria-label": g.label });
        var chosen = own(state.sel, key(g.kind)) || null;
        seg.appendChild(el("button", {
          text: "Base", "aria-pressed": chosen ? "false" : "true",
          onclick: function () { state.sel[key(g.kind)] = null; draw(); }
        }));
        g.items.forEach(function (it) {
          seg.appendChild(el("button", {
            text: it.label + (it.takeRate !== null ? " · " + Math.round(it.takeRate * 100) + "%" : ""),
            "aria-pressed": chosen === it.id ? "true" : "false",
            title: it.note || (it.takeRate !== null ? "Take rate " + Math.round(it.takeRate * 100) + "% of lots" : it.label),
            onclick: function () {
              if (!ms.combo) {
                /* one variant per solve in this build — do not imply otherwise */
                ms.groups.forEach(function (o) { state.sel[key(o.kind)] = null; });
              }
              state.sel[key(g.kind)] = chosen === it.id ? null : it.id;
              draw();
            }
          }));
        });
        picks.appendChild(el("div", { style: "display:flex;flex-wrap:wrap;gap:8px;align-items:center" }, [
          el("span", { class: "badge b-mute", text: g.label }), seg
        ]));
      });
      wrap.appendChild(picks);

      /* what is selected, and what it does */
      var selIds = [], selLabels = [];
      ms.groups.forEach(function (g) {
        var id = own(state.sel, key(g.kind));
        if (!id) return;
        var it = g.items.filter(function (x) { return x.id === id; })[0];
        if (!it) return;
        selIds.push(it.id); selLabels.push(it.label);
      });

      var label = selLabels.join(" + ");
      var delta = null, byMark = {};
      if (selIds.length === 1) {
        var pv = ms.perVariant.filter(function (p) { return p.variant.id === selIds[0]; })[0];
        delta = pv ? pv.delta : deltaFor(plan, pack, selIds[0], ms.base);
      } else if (selIds.length > 1) {
        delta = deltaFor(plan, pack, selIds, ms.base);
      }
      if (delta) {
        delta.rows.forEach(function (row) {
          byMark[key(row.mark.id)] = { state: row.state, now: row.now };
        });
      }

      var sizeable = plan.marks.filter(function (mk) {
        var b = own(ms.base, key(mk.id));
        return b && !b.na;
      }).length;

      if (!selIds.length) {
        wrap.appendChild(el("p", { style: "font-size:.86rem" }, [
          el("strong", { text: "Base case. " }),
          el("span", { text: "Pick an elevation or an option above to see what it does to the schedule below. " +
            "Across the " + plural(ms.variants.length, "variant", "variants") + " on record, " +
            (ms.envRows.length
              ? plural(ms.envRows.length, "mark moves", "marks move") + " at least once."
              : "no mark moves off the base member.") })
        ]));
      } else {
        var moved = delta ? (delta.moved + delta.escalated + delta.recovered) : 0;
        wrap.appendChild(el("p", { style: "font-size:.86rem" }, [
          el("strong", { text: label + " — " }),
          el("span", { text: moved
            ? moved + " of " + sizeable + " sizeable marks change member" +
              (delta.escalated ? ", and " + plural(delta.escalated, "mark", "marks") + " no longer solve at all" : "") +
              (delta.demandOnly ? ". " + plural(delta.demandOnly, "mark carries", "marks carry") + " a different load and holds its member" : "") + "."
            : "no mark changes member" +
              (delta && delta.demandOnly ? "; " + plural(delta.demandOnly, "mark carries", "marks carry") + " a different load and holds it" : "") +
              ". This combination is buildable off the base schedule." })
        ]));
      }

      /* the delta table */
      if (delta && delta.rows.length) {
        var dtb = el("tbody");
        delta.rows.forEach(function (row) {
          var badge = row.state === "escalates"
            ? el("span", { class: "badge b-fail", text: "no member" })
            : (row.state === "moves" ? el("span", { class: "badge b-gold", text: "moves" })
            : (row.state === "recovers" ? el("span", { class: "badge b-pass", text: "now solves" })
            : el("span", { class: "badge b-mute", text: "holds" })));
          dtb.appendChild(el("tr", {}, [
            el("td", { class: "k" }, [el("span", { text: row.mark.id }),
              el("span", { class: "clause", text: row.mark.label })]),
            el("td", {}, [badge]),
            el("td", { text: row.was ? shortSku(row.was) + (row.wasSpacing ? " @ " + row.wasSpacing + "″" : "") : "escalated" }),
            el("td", {}, [
              el("span", { text: row.now ? shortSku(row.now) + (row.nowSpacing ? " @ " + row.nowSpacing + "″" : "") : "—" }),
              row.now && row.nowDcr !== null ? el("span", { class: "clause", text: "DCR " + fmt(row.nowDcr, 2) }) : null
            ]),
            el("td", { text: row.why.length ? row.why.join(" · ")
                             : (row.note ? row.note.wall : "the same demand ranks differently") })
          ]));
        });
        wrap.appendChild(el("div", { class: "tw", tabindex: "0", role: "region", "aria-label": "Variant deltas" }, [
          el("table", {}, [
            el("thead", {}, [el("tr", {}, [
              el("th", { text: "Mark" }), el("th", { text: "" }), el("th", { text: "Base" }),
              el("th", { text: label || "Variant" }), el("th", { text: "What changed in the demand" })
            ])]), dtb
          ])
        ]));
      }

      /* the envelope across the whole master set */
      if (ms.envRows.length) {
        wrap.appendChild(dl(ms.envRows.map(function (e) {
          var names = {}, out = [];
          e.hits.forEach(function (h) {
            var t = h.state === "escalates" ? "no member" : shortSku(h.now || "");
            if (!own(names, key(t))) { names[key(t)] = 1; out.push(t); }
          });
          var b = own(ms.base, key(e.mark.id));
          return {
            k: esc(e.mark.id) + " <span class='clause'>" + esc(e.mark.label) + "</span>",
            v: (b && b.pick ? esc(shortSku(skuText(b.pick.cand))) : "escalated") +
               " → " + esc(out.join(" / ")) +
               " <span class='clause'>" + esc(e.hits.map(function (h) { return h.variant.label; }).join(", ")) + "</span>",
            cls: e.hits.filter(function (h) { return h.state === "escalates"; }).length ? "fail" : "gold"
          };
        })));
      }

      if (!ms.combo && ms.groups.length > 1) {
        wrap.appendChild(el("p", { class: "src-note", text:
          "One variant at a time: this build of the weights model takes a single variant per solve, so an elevation " +
          "and an option cannot be stacked here. The envelope above is the union over each variant taken alone." }));
      }
      if (ms.truncated > 0) {
        wrap.appendChild(el("p", { class: "src-note", text:
          ms.truncated + " further variant(s) on this plan are not shown — this view solves the first " +
          MAX_VARIANTS + "." }));
      }

      body.appendChild(el("div", { style: "margin-bottom:16px" }, [
        card("Master set · elevations and options",
          el("span", { class: "badge b-gold", text: plural(ms.variants.length, "variant", "variants"), style: "margin-left:auto" }),
          wrap,
          "Each variant is an independent solve against its own demand — no cell is inferred from the base case. " +
          "Sizing the base and letting an option move a bearing is how a post-permit revision gets manufactured; " +
          "this is where you find it first.")
      ]));

      return { byMark: byMark, label: label, ids: selIds };
    }

    /* ---------- the search record for one mark ---------- */

    function drawSearch(m, pack) {
      var sol = m.solution, b = sol.bounds, st = sol.stats || {};
      var wrap = el("div", { style: "margin-top:14px;display:grid;gap:12px" });
      var pick = m.unifiedTo || sol.pick;

      /* the answer first: what was picked, or what stopped it */
      if (pick) {
        wrap.appendChild(card("Result · " + m.mark.id + " " + m.mark.label,
          el("span", { class: "badge b-pass", text: "Sized", style: "margin-left:auto" }),
          el("div", { style: "display:grid;gap:12px" }, [
            dcrMeter(pick.dcr, sol.policy ? sol.policy.maxDCR : NaN, pick.governing),
            dl([
              { k: "Member", v: esc(skuText(pick.cand)) + " <span class='clause'>" + esc(spacingText(pick.cand)) + "</span>" },
              { k: "Governing check", v: esc(pick.governing) + " · " + esc(pick.combo || "—"), cls: "gold" },
              { k: "Cost", v: usd(pick.cost.totalUSD) + " / piece <span class='clause'>placeholder price</span>" },
              m.unifiedTo ? { k: "Raised by SKU unification", v: "yes <span class='clause'>it passed its own check first</span>" } : null
            ].filter(Boolean))
          ]),
          "The engine decided the DCR. The weights only chose between members that had already passed."));
      } else if (sol.note) {
        var info = escInfo(sol.status);
        wrap.appendChild(card("Escalated · " + m.mark.id + " — " + info.t,
          el("span", { class: "badge b-fail", text: info.b, style: "margin-left:auto" }),
          el("div", { style: "display:grid;gap:9px;font-size:.86rem" }, [
            el("p", {}, [el("strong", { text: "Next move: " }), el("span", { text: sol.note.move })]),
            el("p", {}, [el("strong", { text: "Wall: " }), el("span", { text: sol.note.wall })]),
            sol.note.procurement
              ? el("p", {}, [el("strong", { text: "The member that passes: " }),
                             el("span", { text: sol.note.procurement })]) : null,
            sol.note.counts && Object.keys(sol.note.counts).length
              ? el("p", { class: "clause", text: "checked and failed — " +
                  Object.keys(sol.note.counts).map(function (k) {
                    return k + " " + sol.note.counts[k]; }).join(" · ") }) : null,
            el("p", { class: "src-note", text: sol.note.outOfScope })
          ].filter(Boolean)), null));
      }

      /* what the search was asked to do */
      wrap.appendChild(card("Demand · " + m.mark.id + " " + m.mark.label, null, dl([
        { k: "Span", v: fmt(m.demand.span, 1) + " ft" },
        { k: m.demand.repetitive ? "Spacings searched" : "Tributary width",
          v: m.demand.repetitive ? sol.policy.spacings.join("″, ") + "″ o.c." : fmt(m.demand.trib, 1) + " ft" },
        { k: "Ladder", v: esc(sol.policy.ladder.join(" · ")) },
        { k: "Palette", v: esc(sol.policy.palette.join(" · ")) },
        { k: "Dead", v: fmt(m.demand.dead, 1) + " psf" + (m.demand.repetitive ? " <span class='clause'>includes member self-weight, §1.3(a)</span>" : "") },
        { k: "Floor live", v: fmt(m.demand.live, 0) + " psf" },
        { k: "Roof load", v: fmt(m.demand.roofLoad, 0) + " psf <span class='clause'>" + (m.demand.roofType === "snow" ? "snow · C_D 1.15" : "roof live · C_D 1.25") + "</span>" },
        { k: "Bearing length", v: fmt(m.demand.bearing, 2) + " in <span class='clause'>" + (m.demand.role === "header" ? "jack studs × 1.5 in — declared, never defaulted" : "on a post cap") + "</span>" },
        b && b.deflection ? { k: "Deflection row", v: esc(b.deflection.row) + " <span class='clause'>L/" + b.deflection.live + " variable, L/" + b.deflection.total + " total</span>" } : null,
        { k: "Service", v: m.demand.wet ? "Wet · MC &gt; 19%" : "Dry" },
        { k: "Treatment", v: m.demand.treated ? "Treated <span class='clause'>C_i applies · NDS T4.3.8</span>" : "Untreated" },
        { k: "Compression edge", v: m.demand.braced ? "Continuously braced — C_L = 1.0" : "Unbraced — C_L computed from R_B" },
        { k: "Firm DCR target", v: fmt(sol.policy.maxDCR, 2), cls: "gold" },
        !m.demand.repetitive ? { k: "Self-weight added", v: "§1.3(b) · &gamma; = " + FM.solver.GAMMA_PCF + " pcf <span class='clause'>assumption</span>" } : null
      ].filter(Boolean)), "Every value here came from the plan mark and the region pack — none of it is a solver default."));

      /* the seed bounds and what they cost the search */
      if (b && b.bySpacing) {
        wrap.appendChild(card("Search trace", el("span", { class: "badge b-blue", text: (st.evaluated || 0) + " engine calls", style: "margin-left:auto" }),
          el("div", { style: "display:grid;gap:10px" }, [
            el("div", { class: "eq", html:
              Object.keys(b.bySpacing).map(function (sp) {
                var x = b.bySpacing[sp];
                return (sp === "0" ? "single member" : "at " + sp + "&Prime; o.c.") +
                       ": S_x &ge; " + fmt(x.S_req, 2) + " in&sup3; · I_x &ge; " + fmt(x.I_req, 1) +
                       " in&#8308; · A &ge; " + fmt(x.A_req, 2) + " in&sup2; · b &ge; " + fmt(x.b_req, 3) + " in";
              }).join("<br>") + "<br>" +
              "computed per spacing — a member at 16&Prime; o.c. carries two-thirds of what it carries at 24&Prime;<br>" +
              "computed against the best material in the palette, C_L = 1, C_M = 1, self-weight omitted — so a section " +
              "below a bound cannot pass for any material offered"
            }),
            dl([
              { k: "Search space", v: sol.searchSpace + " candidates in " + (st.families || 0) + " families" },
              { k: "Cut by seed bounds", v: String(st.prunedByBound || 0) + " <span class='clause'>H1 · admissible</span>" },
              { k: "Cut by cost dominance", v: String(st.prunedByDominance || 0) + " <span class='clause'>H2 · deeper rung of a family already beaten</span>" },
              { k: "Cut by incumbent", v: String(st.prunedByIncumbent || 0) + " <span class='clause'>H3 · branch and bound</span>" },
              { k: "Engine evaluations", v: String(st.evaluated || 0) + (st.cacheHits ? " (+" + st.cacheHits + " cached)" : ""), total: true }
            ])
          ]), "Every cut is exact — no candidate was dropped on a guess"));
      }

      /* the feasible ladder */
      if (sol.feasible.length) {
        var shownF = Math.min(8, sol.feasible.length);
        var ftb = el("tbody");
        sol.feasible.slice(0, shownF).forEach(function (f, i) {
          ftb.appendChild(el("tr", {}, [
            el("td", { class: "k" }, [
              el("span", { text: skuText(f.cand) }),
              i === 0 ? el("span", { class: "badge b-pass", style: "margin-left:6px", text: "Pick" }) : null
            ]),
            el("td", { class: "n", text: spacingText(f.cand) }),
            el("td", { class: "n", text: fmt(f.dcr, 3) }),
            el("td", { text: f.governing }),
            el("td", { class: "n", text: usd(f.cost.totalUSD) }),
            el("td", { class: "n", text: usd(f.score) })
          ]));
        });
        var unit = m.demand.repetitive ? "sf" : "pc";
        wrap.appendChild(card("Passed the check · ranked",
          el("span", { class: "badge b-mute", text: shownF + " of " + sol.feasible.length, style: "margin-left:auto" }),
          el("div", { class: "tw", tabindex: "0", role: "region", "aria-label": "Feasible members" }, [
            el("table", {}, [
              el("thead", {}, [el("tr", {}, [
                el("th", { text: "Member" }), el("th", { class: "n", text: "Spacing" }), el("th", { class: "n", text: "DCR" }),
                el("th", { text: "Governs" }), el("th", { class: "n", text: "Cost / pc" }), el("th", { class: "n", text: "Score / " + unit })
              ])]), ftb
            ])
          ]),
          "Score = cost per " + (m.demand.repetitive ? "square foot of framed area" : "piece") +
          " plus a small penalty for unused capacity — which is why the cheapest piece is not always the top row. " +
          "The engine decided the DCR column; the weights only ordered the rows."));
      }

      /* why the rest did not make it */
      if (sol.rejected.length) {
        var shownR = Math.min(10, sol.rejected.length);
        var rtb = el("tbody");
        sol.rejected.slice(0, shownR).forEach(function (rj) {
          rtb.appendChild(el("tr", {}, [
            el("td", { class: "k", text: skuText(rj.cand) }),
            el("td", { text: rj.reason }),
            el("td", { text: rj.next || "—" })
          ]));
        });
        wrap.appendChild(card("Rejected",
          el("span", { class: "badge b-warn", text: shownR + " of " + sol.rejected.length, style: "margin-left:auto" }),
          el("div", { class: "tw", tabindex: "0", role: "region", "aria-label": "Rejected members" }, [
            el("table", {}, [
              el("thead", {}, [el("tr", {}, [
                el("th", { text: "Member" }), el("th", { text: "Why" }), el("th", { text: "What would move it" })
              ])]), rtb
            ])
          ]),
          "Sensitivity from the closed forms: deflection goes as d³, bending as d², shear as d, bearing not at all"));
      }

      /* the roof-load crossover and anything else the search wants flagged */
      (sol.advisories || []).forEach(function (a) {
        wrap.appendChild(el("div", { class: "banner banner-warn" }, [
          el("strong", { text: "Not checked — " }), el("span", { text: a.text })
        ]));
      });

      /* end reactions — the number the truss and connector designers need */
      if (sol.reactions && sol.reactions.perBearingLb) {
        wrap.appendChild(card("End reactions", el("span", { class: "badge b-blue", text: "Coordination", style: "margin-left:auto" }),
          dl([
            { k: "Reaction each bearing", v: FM.comma(sol.reactions.perBearingLb) + " lb", total: true },
            { k: "Governing combination", v: FM.esc(sol.reactions.combo) },
            { k: "Reduction applied", v: "none <span class='clause'>the §3.4.3.1 d-reduction is a shear allowance and never applies to a reaction</span>" }
          ]), sol.reactions.note));
      }

      /* the weight breakdown for the pick */
      if (pick) {
        var t = pick.cost.terms;
        var perUnit = pick.cost.unitUSD, slack = pick.score - perUnit;
        var unitName = m.demand.repetitive ? "sf of framed area" : "piece";
        wrap.appendChild(card("Why this one — weight breakdown", null, dl([
          { k: "Material <span class='clause'>" + fmt(pick.cost.boardFeet, 1) + " bf @ " + usd(pick.cost.bfUSD) + "/bf</span>", v: usd(t.material) },
          { k: "Labor <span class='clause'>per piece + " + fmt(pick.cost.weightLb, 0) + " lb handling</span>", v: usd(t.labor) },
          { k: "Drop handling <span class='clause'>cut from a " + pick.cost.lengthFt + " ft stick</span>", v: usd(t.drop) },
          { k: "Structural depth <span class='clause'>plate height, chases, finishes</span>", v: usd(t.depth) },
          { k: "Stock risk <span class='clause'>availability " + fmt(pick.cost.availability, 2) + "</span>", v: usd(t.stock) },
          { k: "Unsourced C_F review <span class='clause'>" + pick.cost.cfBasis + "</span>", v: usd(t.risk) },
          { k: "Cost per piece", v: usd(pick.cost.totalUSD), total: true },
          { k: "Cost per " + unitName, v: usd(perUnit) },
          { k: "Unused capacity <span class='clause'>score − cost, per " + unitName + "</span>", v: usd(slack) },
          { k: "Score <span class='clause'>the ranked number, per " + unitName + "</span>", v: usd(pick.score), cls: "gold" }
        ]), "Market weights, not code values — they rank passing members and can never promote a failing one"));
      }

      return wrap;
    }

    /* ---------- region pack ---------- */

    function drawRegion(pack) {
      var c = pack.climate;

      /* same note, same prominence as the schedule tab — it is not a footnote */
      if (pack.governs === "wind" && pack.governsNote) {
        body.appendChild(el("div", { class: "banner banner-warn" }, [
          el("strong", { text: "Gravity only — " }), el("span", { text: pack.governsNote })
        ]));
      }

      body.appendChild(el("div", { class: "grid g2" }, [
        card("Site conditions · " + pack.name, el("span", { class: "badge " + (pack.governs === "wind" ? "b-warn" : "b-mute"), text: pack.governs === "wind" ? "Wind governs" : "Gravity governs", style: "margin-left:auto" }),
          el("div", {}, [
            dl([
              { k: "Markets", v: esc(pack.markets) },
              { k: "Code family", v: esc(pack.code ? pack.code.family : "—") + classBadgeHtml(pack.code && pack.code.cls) },
              { k: "Ground snow", v: c.groundSnow.v + " psf" + classBadgeHtml(c.groundSnow.cls) },
              { k: "Roof live", v: c.roofLive.v + " psf" + classBadgeHtml(c.roofLive.cls) },
              { k: "Basic wind", v: c.windMph.v + " mph" + classBadgeHtml(c.windMph.cls) },
              { k: "Exposure", v: esc(c.exposure.v) + classBadgeHtml(c.exposure.cls) },
              { k: "Seismic (SDC)", v: esc(c.sdc.v) + classBadgeHtml(c.sdc.cls) },
              { k: "Foundation", v: esc(pack.foundation || "—") },
              { k: "Exterior wall", v: esc(pack.exteriorWall || "—") },
              { k: "Roof framing", v: esc(pack.roofFraming || "—") },
              { k: "Plate height", v: fmt(pack.plateHeightIn, 2) + " in" },
              { k: "Firm DCR target", v: fmt(pack.maxDCR, 2), cls: "gold" }
            ]),
            el("p", { class: "src-note", style: "margin-top:10px", text:
              "Code is a published requirement; Site is a value somebody must confirm for the address; Market is a " +
              "purchasing assumption. Snow, wind, exposure and seismic are PLANNING DEFAULTS for laying out a " +
              "repeatable plan — not site values. Replace them from the ASCE 7 Hazard Tool and the AHJ before " +
              "anything is stamped." })
          ]), pack.climate.groundSnow.note || null),

        card("Design loads handed to the engine", null, el("div", {}, [
          dl([
            { k: "Roof assembly <span class='clause'>" + esc(pack.loads.roofAssembly) + "</span>",
              v: esc(FM.weights.ASSEMBLY[pack.loads.roofAssembly].label) + " · " + FM.weights.ASSEMBLY[pack.loads.roofAssembly].psf + " psf" },
            { k: "Floor assembly", v: esc(FM.weights.ASSEMBLY[pack.loads.floorAssembly].label) + " · " + FM.weights.ASSEMBLY[pack.loads.floorAssembly].psf + " psf" },
            { k: "Ceiling assembly", v: esc(FM.weights.ASSEMBLY[pack.loads.ceilingAssembly].label) + " · " + FM.weights.ASSEMBLY[pack.loads.ceilingAssembly].psf + " psf" },
            { k: "Floor live", v: pack.loads.floorLive + " psf" },
            { k: "Deck live", v: pack.loads.deckLive + " psf" },
            { k: "Attic live", v: pack.loads.ceilingLive + " psf <span class='clause'>wired, read by no mark</span>" },
            { k: "Design roof load", v: pack.loads.roofLoad + " psf · " + (pack.loads.roofType === "snow" ? "snow, C_D 1.15" : "roof live, C_D 1.25"), cls: "gold" }
          ]),
          el("p", { class: "src-note", style: "margin-top:10px", text: pack.loads.roofLoadBasis })
        ]), "Dead loads are assembly makeups, not single numbers — the makeup travels with the export.")
      ]));

      var ptb = el("tbody");
      pack.palette.forEach(function (p) {
        ptb.appendChild(el("tr", {}, [
          el("td", { class: "k", text: p.species }),
          el("td", { text: p.grade }),
          el("td", { class: "n", text: usd(p.bfUSD) + "/bf" }),
          el("td", { class: "n", text: fmt(p.stockFactor, 2) }),
          el("td", { class: "n", text: p.cullRate === undefined ? "—" : fmt(p.cullRate * 100, 0) + "%" }),
          el("td", { text: p.note || "" })
        ]));
      });
      body.appendChild(el("div", { style: "margin-top:16px" }, [
        card("Species palette", el("span", { class: "badge b-mute", text: "Market", style: "margin-left:auto" }),
          el("div", { class: "tw", tabindex: "0", role: "region", "aria-label": "Species palette" }, [
            el("table", {}, [
              el("thead", {}, [el("tr", {}, [
                el("th", { text: "Species" }), el("th", { text: "Grade" }), el("th", { class: "n", text: "Price $/bf" }),
                el("th", { class: "n", text: "Stock factor 0–1" }), el("th", { class: "n", text: "Cull" }), el("th", { text: "Note" })
              ])]), ptb
            ])
          ]),
          "Placeholder prices — replace with your yard's quoted $/bf; price changes the ranking, never the pass/fail. " +
          "Stock factor does decide feasibility: a member below the availability floor cannot be the pick.")
      ]));

      var w = FM.weights.policyFor(pack, null).weights;
      body.appendChild(el("div", { style: "margin-top:16px" }, [
        card("Model weights", el("span", { class: "badge b-mute", text: "Firm-calibrated", style: "margin-left:auto" }), dl([
          { k: "Material multiplier", v: fmt(w.material, 2) + " <span class='clause'>× quoted $/bf</span>" },
          { k: "Base price fallback", v: usd(w.baseBfUSD) + " /bf" },
          { k: "Labor per piece", v: usd(w.laborPerPiece) + " /pc" },
          { k: "Labor per lb handled", v: usd(w.laborPerLb) + " /lb" },
          { k: "Structural depth", v: usd(w.depthPerInchSf) + " /sf per inch" },
          { k: "Stock risk at zero availability", v: usd(w.stockPenaltySf) + " /sf" },
          { k: "Unsourced C_F review", v: usd(w.unsourcedCF) + " /member" },
          { k: "Unused capacity", v: usd(w.slackPenalty) + " per unit of slack" },
          { k: "Distinct SKU on the plan", v: usd(w.skuPenalty) + " /SKU", cls: "gold" }
        ]), "Every weight has a unit. A weight with no unit is one nobody can argue with, which is worse than one that is wrong.")
      ]));

      if (pack.service && pack.service.note) {
        body.appendChild(el("div", { style: "margin-top:16px" }, [
          card("Service condition", el("span", { class: "badge " + (pack.service.exteriorWet ? "b-warn" : "b-mute"), text: pack.service.exteriorWet ? "Exterior wet" : "Dry", style: "margin-left:auto" }),
            el("p", { style: "font-size:.86rem", text: pack.service.note }), null)
        ]));
      }
    }

    /* ---------- repeat matrix ---------- */

    /* Descriptive, never causal: these are the fields on which two packs
       differ. The pack is what forced the member; this says how it differs. */
    function packDelta(a, b) {
      var out = [];
      if (!a || !b) return out;
      if (a.loads.roofAssembly !== b.loads.roofAssembly) {
        out.push(FM.weights.ASSEMBLY[b.loads.roofAssembly].label.toLowerCase() + " " +
                 FM.weights.ASSEMBLY[b.loads.roofAssembly].psf + " psf vs " +
                 FM.weights.ASSEMBLY[a.loads.roofAssembly].psf + " psf");
      }
      if (a.loads.roofType !== b.loads.roofType) {
        out.push("roof case " + b.loads.roofType.replace("_", " ") +
                 " · C_D " + (b.loads.roofType === "snow" ? "1.15" : "1.25"));
      }
      if (a.loads.roofLoad !== b.loads.roofLoad) out.push("roof load " + b.loads.roofLoad + " psf vs " + a.loads.roofLoad);
      if (a.loads.floorLive !== b.loads.floorLive) out.push("floor live " + b.loads.floorLive + " psf vs " + a.loads.floorLive);
      if (a.maxDCR !== b.maxDCR) out.push("DCR target " + fmt(b.maxDCR, 2) + " vs " + fmt(a.maxDCR, 2));
      if (a.service.exteriorWet !== b.service.exteriorWet) out.push(b.service.exteriorWet ? "exterior wet service" : "exterior dry service");
      var pa = a.palette.map(function (p) { return p.species + " " + p.grade; }).join(", ");
      var pb = b.palette.map(function (p) { return p.species + " " + p.grade; }).join(", ");
      if (pa !== pb) out.push("a different species palette");
      if (a.exteriorWall !== b.exteriorWall) out.push("exterior wall " + b.exteriorWall);
      return out;
    }

    function drawMatrix(plan) {
      var packs = FM.weights.PACKS;
      var cmp = FM.solver.compare(plan, packs);

      /* A mark that is not this engine's member in every region is not
         "unanswered" — nobody asked this engine the question. Splitting the
         two keeps a truss out of the same bucket as a girder the solver
         could not size, without ever letting either read as Common. */
      var rows = cmp.rows.map(function (row) {
        var na = 0, none = 0, answered = 0, sizes = {}, mats = {}, spacings = {};
        row.cells.forEach(function (c) {
          if (c.notApplicable) { na++; return; }
          if (!c.sku) { none++; return; }
          answered++;
          sizes[key(c.sku.split(" ")[0])] = 1;
          mats[key(c.sku.split(" ").slice(1).join(" "))] = 1;
          spacings[key(String(c.spacing || 0))] = 1;
        });
        var axes = [];
        if (Object.keys(sizes).length > 1) axes.push("size");
        if (Object.keys(mats).length > 1) axes.push("grade");
        if (Object.keys(spacings).length > 1) axes.push("spacing");
        var group = row.varies ? "varies"
          : (row.common ? "common"
          : (na === row.cells.length ? "na" : "none"));
        /* the member every region agrees on, so a deviating cell can be marked */
        var tally = {}, modal = null;
        row.cells.forEach(function (c) {
          if (!c.sku) return;
          var k = key(c.sku + "@" + (c.spacing || 0));
          tally[k] = (own(tally, k) || 0) + 1;
          if (!modal || tally[k] > tally[modal]) modal = k;
        });
        return { row: row, na: na, none: none, answered: answered,
                 axes: axes, group: group, modal: modal };
      });

      var nCommon = rows.filter(function (r) { return r.group === "common"; }).length;
      var nVaries = rows.filter(function (r) { return r.group === "varies"; }).length;
      var nNone   = rows.filter(function (r) { return r.group === "none"; }).length;
      var nNa     = rows.filter(function (r) { return r.group === "na"; }).length;

      body.appendChild(el("div", { class: "grid g5", style: "margin-bottom:6px" }, [
        FM.statCard(String(nCommon), "Same member everywhere", nCommon ? "pass" : ""),
        FM.statCard(String(nVaries), "Regionally forced", nVaries ? "gold" : ""),
        FM.statCard(String(nNone), "No member anywhere", nNone ? "fail" : ""),
        FM.statCard(String(nNa), "Not this engine, anywhere", "blue"),
        FM.statCard(String(cmp.solvedMarks) + "/" + plan.marks.length, "Marks with an answer")
      ]));

      body.appendChild(line(
        "One master set, solved independently in " + plural(packs.length, "region pack", "region packs") +
        " across " + plural(3, "state", "states") + ". " + nCommon + " marks are the same member in every region " +
        "where they apply — buy those in one order. " + nVaries + " are regionally forced. " +
        (nNone + nNa) + " have no member on this board: " + nNone + " nobody could size and " + nNa +
        " are not this engine's member anywhere.",
        "each cell is an independent solve — no cell is inferred from another"));

      var GROUPS = [
        { id: "varies", t: "Regionally forced — the member changes with the market", c: "b-gold" },
        { id: "common", t: "The same member in every region where it applies", c: "b-pass" },
        { id: "none",   t: "No member in any region — unanswered, not portable", c: "b-fail" },
        { id: "na",     t: "Not this engine's member in any region", c: "b-blue" }
      ];

      var tb = el("tbody");
      var nCols = packs.length + 1;
      GROUPS.forEach(function (g) {
        var mine = rows.filter(function (r) { return r.group === g.id; });
        if (!mine.length) return;
        tb.appendChild(el("tr", {}, [
          el("td", { colspan: String(nCols), style: "background:var(--surface-2)" }, [
            el("span", { class: "badge " + g.c, text: String(mine.length) }),
            el("span", { class: "clause", text: g.t })
          ])
        ]));
        mine.forEach(function (r) {
          var row = r.row;
          var badge;
          if (g.id === "varies") badge = el("span", { class: "badge b-gold", style: "margin-left:6px", text: "varies · " + (r.axes.join(" + ") || "member") });
          else if (g.id === "common") badge = el("span", { class: "badge b-pass", style: "margin-left:6px", text: "common" });
          else if (g.id === "none") badge = el("span", { class: "badge b-fail", style: "margin-left:6px", text: "no member" });
          else badge = el("span", { class: "badge b-blue", style: "margin-left:6px", text: "not this engine" });

          var cells = [el("td", { class: "k" }, [
            el("span", { text: row.mark.id }),
            badge,
            r.none && r.answered ? el("span", { class: "badge b-fail", style: "margin-left:6px", text: r.none + " unsolved" }) : null,
            el("span", { class: "clause", text: row.mark.label })
          ])];
          row.cells.forEach(function (c) {
            if (c.notApplicable) {
              cells.push(el("td", {}, [el("span", { class: "badge b-blue", text: c.note === "component" ? "component" : "n/a" })]));
              return;
            }
            if (!c.sku) {
              cells.push(el("td", {}, [el("span", { class: "badge b-fail", text: "none" })]));
              return;
            }
            var deviates = r.group === "varies" && r.modal && key(c.sku + "@" + (c.spacing || 0)) !== r.modal;
            cells.push(el("td", {}, [
              deviates ? el("span", { class: "badge b-gold", style: "margin-right:6px", text: "Δ" }) : null,
              el("span", { style: "white-space:nowrap", text: shortSku(c.sku) }),
              el("span", { class: "clause", style: "white-space:nowrap",
                           text: (c.spacing ? c.spacing + "″ · " : "") + "DCR " + fmt(c.dcr, 2) })
            ]));
          });
          tb.appendChild(el("tr", {}, cells));
        });
      });

      body.appendChild(el("div", { class: "tw", tabindex: "0", role: "region", "aria-label": "Cross-region member matrix" }, [
        el("table", {}, [
          el("thead", {}, [el("tr", {}, [el("th", { text: "Mark" })].concat(
            packs.map(function (p) {
              return el("th", {}, [
                el("span", { text: shortPack(p) }),
                p.governs === "wind" ? el("span", { class: "badge b-warn", style: "margin-left:6px", text: "wind" }) : null
              ]);
            })
          ))]),
          tb
        ])
      ]));
      body.appendChild(el("p", { class: "src-note", style: "margin-top:8px", text:
        "Δ marks the region that departs from what the other packs agree on. A pack badged wind governs on uplift, " +
        "which this engine does not check — a member in that column is a gravity floor, not a design." }));

      /* which pack departed, and how that pack differs */
      var forced = rows.filter(function (r) { return r.group === "varies"; });
      if (forced.length) {
        var fRows = [];
        forced.forEach(function (r) {
          var modalPacks = [], oddPacks = [];
          r.row.cells.forEach(function (c, i) {
            if (!c.sku) return;
            if (key(c.sku + "@" + (c.spacing || 0)) === r.modal) modalPacks.push(packs[i]);
            else oddPacks.push({ pack: packs[i], sku: c.sku, spacing: c.spacing });
          });
          var ref = modalPacks[0];
          oddPacks.forEach(function (o) {
            var diff = packDelta(ref, o.pack);
            fRows.push({
              k: esc(r.row.mark.id) + " <span class='clause'>" + esc(shortPack(o.pack)) + "</span>",
              v: esc(shortSku(o.sku)) + " <span class='clause'>where the others take " +
                 esc(shortSku(r.modal ? r.modal.replace("k:", "").split("@")[0] : "—")) + "</span>",
              cls: "gold"
            });
            fRows.push({
              k: "<span class='clause'>that pack differs in</span>",
              v: diff.length ? esc(diff.join(" · ")) : "no modelled difference — the ranking broke a near-tie"
            });
          });
        });
        body.appendChild(el("div", { style: "margin-top:16px" }, [
          card("What forced the change", el("span", { class: "badge b-gold", text: "Regional", style: "margin-left:auto" }),
            dl(fRows),
            "These are the fields on which the packs differ, read off the packs themselves — the attribution is " +
            "descriptive, not a sensitivity study. Run the mark in both packs to see which field carries it.")
        ]));
      }

      var mGroups = variantGroups(plan);
      body.appendChild(el("div", { style: "margin-top:16px" }, [
        card("Reading this", null, el("div", { style: "display:grid;gap:9px;font-size:.86rem" }, [
          el("p", { text: "A mark with no member in any region is not portable and it is not common — it is unanswered. Counting it as common would turn silence into evidence for this product's central claim." }),
          el("p", { text: "A mark marked common is the same member in every region on this board — build it the same everywhere and buy it in one order. A mark marked varies is regionally forced, and the badge names the axis: size, grade or spacing." }),
          el("p", { text: "The three forcings that actually move members across these six packs are: snow duration in the Carolina mountains, which drops C_D from 1.25 to 1.15; concrete tile dead load in the HVHZ, which is 22 psf against 15 for shingle; and species availability, which decides what the yard can hand the framer." }),
          mGroups ? el("p", { text: "This board is the base case of the master set. What an elevation or an option does to it is on the Schedule tab." }) : null,
          el("p", { class: "src-note", text: "Every cell is an independent solve against that region's palette, ladder, loads and DCR target. No cell is inferred from another." })
        ].filter(Boolean)), null)
      ]));
    }

    /* ---------- draw ---------- */

    function draw() {
      body.innerHTML = "";
      Array.prototype.forEach.call(tabs.querySelectorAll("button"), function (b) {
        b.setAttribute("aria-pressed", b.getAttribute("data-tab") === state.tab ? "true" : "false");
      });

      var pack = FM.weights.packById(state.packId);
      var plan = FM.weights.planById(state.planId);
      if (!pack || !plan) {
        body.appendChild(el("div", { class: "empty", text: "That region pack or plan is not loaded." }));
        return;
      }

      if (state.tab === "region") { drawRegion(pack); return; }
      if (state.tab === "matrix") { drawMatrix(plan); return; }

      var res = FM.solver.solvePlan(plan, pack);
      drawSchedule(res, pack, plan);
    }

    draw();
  };
})();

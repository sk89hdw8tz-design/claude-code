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
  /* a .clause dropped onto its own line — two short lines beat one wide cell
     when six regions have to fit on one board */
  var BLOCK = "display:block;margin:2px 0 0;padding-left:0;border-left:0;";
  /* six regions do not fit a narrow container, so the board scrolls and the
     mark it belongs to stays on screen */
  var STICKY   = "position:sticky;left:0;z-index:1;background:var(--surface);" +
                 "max-width:250px;min-width:170px;white-space:normal;";
  var STICKY_H = "position:sticky;left:0;z-index:4;background:var(--surface-2);min-width:170px;";

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

  /* Escalation labels come from FM.solver.escalationOf() — the export prints
     from the same source, and a screen that disagrees with the paper about
     what an escalation means is the defect, not the wording. */
  function escInfo(status) {
    var e = FM.solver.escalationOf ? FM.solver.escalationOf(status) : null;
    return e || { badge: String(status || "escalate").replace("escalate:", ""),
                  tag: "ESCALATED", short: "no member was selected" };
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

     Consumed from weights.js, every entry point optional and every
     call guarded, so a build without master sets renders exactly
     what it rendered before:

       variantsFor(plan)   -> { elevations[], options[], combinations[],
                                lots, note, declaresVariants }
         combinations[] is the BUILDABLE list — each one an elevation
         with a compatible set of options — carrying id, label,
         elevationId, optionIds[], isBase, takeRate, lotsExpected,
         touches[] and movesNoMember.
       planForVariant(plan, id) -> a plain plan with the overrides
         applied, the removals gone and the additions in. It goes
         straight to FM.solver.solvePlan(); the solver never learns
         that variants exist, so every number on a variant schedule
         is produced by the same path as the base one.
       envelopeFor(plan, markId, pack) -> whether ONE variant governs
         the mark across the whole set, or whether the set is split
         and each variant has to be sized.

     This view never composes a variant id by hand: a combination the
     builder cannot build is not on the picker.
     ============================================================ */

  var MCACHE = {};   /* plan+pack -> master-set report; the inputs are static */

  function variantSet(plan) {
    var W = FM.weights;
    if (!W || typeof W.variantsFor !== "function" || typeof W.planForVariant !== "function") return null;
    var v;
    try { v = W.variantsFor(plan); } catch (e) { return null; }
    if (!v || !isArr(v.combinations) || v.combinations.length < 2) return null;
    if (v.declaresVariants === false) return null;
    return v;
  }

  function comboById(v, id) {
    var out = null;
    v.combinations.forEach(function (c) { if (c.id === id) out = c; });
    return out;
  }
  function baseCombo(v) {
    var out = null;
    v.combinations.forEach(function (c) { if (!out && c.isBase) out = c; });
    return out || v.combinations[0];
  }
  /* an option set, named the way a sales sheet names it */
  function optionLabel(v, combo) {
    if (!combo.optionIds || !combo.optionIds.length) {
      return combo.isBase ? "Base case" : "Elevation only";
    }
    return combo.optionIds.map(function (id) {
      var hit = null;
      v.options.forEach(function (o) { if (o.id === id) hit = o; });
      return hit ? hit.label : id;
    }).join(" + ");
  }
  function elevationOf(v, id) {
    var hit = null;
    v.elevations.forEach(function (e) { if (e.id === id) hit = e; });
    return hit;
  }

  function solveVariant(plan, pack, comboId) {
    try {
      var vp = FM.weights.planForVariant(plan, comboId);
      return { plan: vp, res: FM.solver.solvePlan(vp, pack) };
    } catch (e) { return null; }
  }

  function pickOf(m) {
    if (!m || m.notApplicable) return null;
    var row = m.unifiedTo || (m.solution && m.solution.pick);
    return row || null;
  }

  /* base schedule vs the selected combination, mark for mark — including the
     marks a variant adds and the ones it deletes, which are the two cases a
     diff of two member lists is most likely to drop on the floor */
  function scheduleDelta(baseRes, varRes) {
    var byId = {}, rows = [], counts = { moves: 0, escalates: 0, recovers: 0, added: 0, removed: 0 };
    baseRes.marks.forEach(function (m) { byId[key(m.mark.id)] = m; });
    var seen = {};

    varRes.marks.forEach(function (vm) {
      var id = vm.mark.baseMarkId || vm.mark.id;
      seen[key(id)] = 1;
      var bm = own(byId, key(id));
      var vp = pickOf(vm), bp = bm ? pickOf(bm) : null;
      if (!bm) {
        rows.push({ id: vm.mark.id, label: vm.mark.label, state: "added",
                    was: null, now: vp ? skuText(vp.cand) : null,
                    nowSpacing: vp ? vp.cand.spacing : null,
                    nowDcr: vp ? vp.dcr : null,
                    why: vm.notApplicable ? "not this engine's member" : (vp ? "" : "escalates") });
        counts.added++;
        return;
      }
      if (bm.notApplicable && vm.notApplicable) return;
      var why = demandDelta(bm.demand, vm.demand);
      if (bp && !vp) {
        rows.push({ id: id, label: vm.mark.label, state: "escalates", was: skuText(bp.cand), now: null,
                    wasSpacing: bp.cand.spacing, why: why.join(" · ") ||
                    (vm.solution && vm.solution.note ? vm.solution.note.wall : "") });
        counts.escalates++;
      } else if (!bp && vp) {
        rows.push({ id: id, label: vm.mark.label, state: "recovers", was: null, now: skuText(vp.cand),
                    nowSpacing: vp.cand.spacing, nowDcr: vp.dcr, why: why.join(" · ") });
        counts.recovers++;
      } else if (bp && vp && (skuText(bp.cand) !== skuText(vp.cand) ||
                 (bp.cand.spacing || 0) !== (vp.cand.spacing || 0))) {
        rows.push({ id: id, label: vm.mark.label, state: "moves",
                    was: skuText(bp.cand), wasSpacing: bp.cand.spacing,
                    now: skuText(vp.cand), nowSpacing: vp.cand.spacing, nowDcr: vp.dcr,
                    why: why.join(" · ") });
        counts.moves++;
      } else if (why.length) {
        rows.push({ id: id, label: vm.mark.label, state: bp ? "holds" : "stuck",
                    was: bp ? skuText(bp.cand) : null, wasSpacing: bp ? bp.cand.spacing : null,
                    now: vp ? skuText(vp.cand) : null, nowSpacing: vp ? vp.cand.spacing : null,
                    nowDcr: vp ? vp.dcr : null, why: why.join(" · ") });
      }
    });

    baseRes.marks.forEach(function (m) {
      if (own(seen, key(m.mark.id))) return;
      var bp = pickOf(m);
      rows.push({ id: m.mark.id, label: m.mark.label, state: "removed",
                  was: bp ? skuText(bp.cand) : (m.notApplicable ? "not this engine's member" : "escalated"),
                  wasSpacing: bp ? bp.cand.spacing : null, now: null,
                  why: "this variant does not build it" });
      counts.removed++;
    });

    var order = { escalates: 0, added: 1, removed: 2, moves: 3, recovers: 4, holds: 5, stuck: 6 };
    rows.sort(function (a, b) { return order[a.state] - order[b.state]; });
    return { rows: rows, counts: counts,
             changed: counts.moves + counts.escalates + counts.recovers + counts.added + counts.removed };
  }

  /* Per-mark envelope. weights.js will only name a governing variant when one
     dominates every other on every driver at once — otherwise it returns
     split and says the set has to be sized variant by variant. Both answers
     are reported here; neither is summarised away. */
  /* The envelope answers "can I size this mark once for the whole master set?"
     — so it has to be asked about every mark the master set contains, not
     every mark the BASE plan contains.

     It iterated `plan.marks`, which is the base. On two-story-2450 that meant
     BM-POR and PST-POR-B — the two marks Elevation B adds, 27 of the 60 lots —
     were absent from a card headed "THE ENVELOPE · 8 BUILDABLE COMBINATIONS",
     while the delta table directly above announced them as added. A card that
     names its scope as every combination and then silently covers only one of
     them is the same defect as a green badge over an empty cell. */
  function envelope(plan, pack) {
    if (typeof FM.weights.envelopeFor !== "function") return null;
    var rows = [], seen = {}, added = [];

    function consider(mk, isAdded) {
      if (own(seen, key(mk.id))) return;
      seen[key(mk.id)] = true;
      var e;
      try { e = FM.weights.envelopeFor(plan, mk.id, pack); } catch (err) { return; }
      if (!e) return;
      rows.push({ mark: mk, env: e, addedByVariant: isAdded || null });
    }

    plan.marks.forEach(function (mk) { consider(mk, null); });

    /* then everything any variant introduces */
    var v = variantSet(plan);
    (v && v.combinations || []).forEach(function (c) {
      var vp;
      try { vp = FM.weights.planForVariant(plan, c.id); } catch (err) { return; }
      (vp && vp.marks || []).forEach(function (mk) {
        if (own(seen, key(mk.id))) return;
        added.push(mk.id);
        consider(mk, c.label);
      });
    });
    if (!rows.length) return null;
    rows.addedByVariant = added;
    return rows;
  }

  function masterSet(plan, pack) {
    var ck = key(plan.id + "|" + pack.id);
    var hit = own(MCACHE, ck);
    if (hit) return hit;
    var v = variantSet(plan);
    if (!v) return null;
    var out = { v: v, base: baseCombo(v), envelope: envelope(plan, pack) };
    MCACHE[ck] = out;
    return out;
  }

  /* which demand fields moved, for the "what changed" column */
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

  function safeDemand(mark, plan, pack) {
    try { return FM.weights.demandFor(mark, plan, pack); } catch (e) { return null; }
  }


  /* ============================================================
     State and the address bar

     The view's state lives on FM.state.sizing so a link can carry it:
       #/sizing/<planId>/<packId>/<tab>/<combinationId>
     Everything after the plan is optional and every segment is validated —
     a stale link degrades to the default rather than to a blank view.
     ============================================================ */

  var TABS = { schedule: 1, region: 1, matrix: 1 };

  function sizingState() {
    var s = FM.state.sizing;
    if (!s) {
      s = FM.state.sizing = {
        packId: "nc-piedmont", planId: "two-story-2450",
        open: null, tab: "schedule", combo: null
      };
    }
    return s;
  }

  if (typeof FM.registerSubRoute === "function") {
    FM.registerSubRoute("sizing", {
      read: function () {
        var s = sizingState();
        var out = [s.planId, s.packId, s.tab];
        if (s.combo) out.push(s.combo);      /* last, so it can simply be absent */
        return out;
      },
      /* A segment this build does not recognise used to be discarded in
         silence, which is the worst possible handling for the case the URL
         exists to serve. You send a colleague a link, the plan id changes, and
         they open a schedule that renders perfectly and is NOT the one you
         sent — a wrong answer wearing the shape of a right one. An unknown
         VIEW toasted; an unknown plan, region or variant did not.

         So every segment is reported. The state still falls back, because a
         blank screen helps nobody, but it falls back out loud. */
      write: function (args) {
        var s = sizingState();
        args = args || [];
        var lost = [];

        if (args[0]) {
          if (FM.weights && FM.weights.planById(args[0])) {
            if (s.planId !== args[0]) s.combo = null;
            s.planId = args[0];
          } else lost.push("plan “" + args[0] + "”");
        }
        if (args[1]) {
          if (FM.weights && FM.weights.packById(args[1])) s.packId = args[1];
          else lost.push("region “" + args[1] + "”");
        }
        if (args[2]) {
          if (own(TABS, args[2])) s.tab = args[2];
          else lost.push("tab “" + args[2] + "”");
        }
        if (args[3]) {
          /* a combination id only means anything against its own plan */
          var v = variantSet(FM.weights.planById(s.planId));
          if (v && comboById(v, args[3])) s.combo = args[3];
          else { s.combo = null; lost.push("variant “" + args[3] + "”"); }
        }
        s.open = null;

        if (lost.length && FM.toast) {
          FM.toast("This link names " + lost.join(" and ") + ", which this build does not have. " +
                   "Showing " + (FM.weights.planById(s.planId) || {}).name + " in " +
                   ((FM.weights.packById(s.packId) || {}).name || s.packId) + " instead — " +
                   "check the link before using this schedule.");
        }
        /* and correct the address bar, so what it says is what is on screen */
        if (lost.length && FM.syncHash) setTimeout(function () { FM.syncHash(true); }, 0);
      }
    });
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

    var state = sizingState();

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

    /* Every sub-state change used to REPLACE the address, on the reasoning
       that flipping through six regions should not bury the Back button.
       Driving it proved that wrong: switching Texas → Florida and pressing
       Back landed on the dashboard, because the two regions had never been
       two entries. "Take me back to Texas" is the single most natural thing to
       try during this demo and it threw you out of the walk.

       So the line is drawn at what the user would call a step. Changing the
       PLAN, the REGION or the VARIANT is a step — it re-solves the schedule
       and produces a different answer, and Back should undo it. Changing the
       TAB is a lens on the same answer; it refines the address in place. */
    function redraw(step) { draw(); if (FM.syncHash) FM.syncHash(!step); }

    packSel.addEventListener("change", function () {
      state.packId = this.value; state.open = null; redraw(true);
    });
    planSel.addEventListener("change", function () {
      state.planId = this.value; state.open = null; state.combo = null; redraw(true);
    });
    Array.prototype.forEach.call(tabs.querySelectorAll("button"), function (b) {
      b.addEventListener("click", function () { state.tab = b.getAttribute("data-tab"); redraw(); });
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

    function drawSchedule(res, pack, plan, ms, sel, baseRes) {
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

      var lots = sel && sel.lotsExpected ? sel.lotsExpected : plan.lots;
      body.appendChild(line(
        plural(plan.marks.length, "mark", "marks") + " on " +
        (sel && !sel.isBase ? "this variant" : "this plan") +
        (lots ? ", built on " + plural(lots, "lot", "lots") : "") + ". " +
        r.solved + " sized, " + r.escalated + " escalated, " + r.notApplicable +
        " not this engine's member. " + plural(r.skuCount, "distinct SKU", "distinct SKUs") +
        " across the sized marks.",
        "lumber $ is placeholder-priced and covers the sized marks only"));

      /* ---- master set: what an elevation or an option does to this schedule ---- */
      var delta = (ms && baseRes) ? scheduleDelta(baseRes, res) : null;
      var escIds = {};
      escMarks.forEach(function (m) { escIds[key(m.mark.baseMarkId || m.mark.id)] = 1; });
      var current = ms ? drawMasterSet(ms, sel, delta, plan, escIds) : null;

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

        /* this row is the SELECTED variant's member; the badge says how it
           departs from the base case */
        var mv = current ? own(current.byMark, key(m.mark.baseMarkId || m.mark.id)) : null;
        function deltaBadge() {
          if (!mv) return null;
          if (mv.state === "moves") {
            return el("span", { class: "badge b-gold", style: "margin-left:6px",
                                text: "base: " + shortSku(mv.was) });
          }
          if (mv.state === "added") {
            return el("span", { class: "badge b-gold", style: "margin-left:6px", text: "added by this variant" });
          }
          if (mv.state === "recovers") {
            return el("span", { class: "badge b-pass", style: "margin-left:6px", text: "escalates on the base" });
          }
          if (mv.state === "escalates") {
            return el("span", { class: "badge b-fail", style: "margin-left:6px",
                                text: "the base sizes it — " + shortSku(mv.was) });
          }
          if (mv.state === "holds") {
            return el("span", { class: "badge b-mute", style: "margin-left:6px", text: "same member, different load" });
          }
          return null;
        }

        if (!row) {
          var info = escInfo(m.solution.status);
          cells = [
            el("td", { class: "k", text: m.mark.id }),
            el("td", { text: m.mark.label }),
            el("td", { colspan: "4" }, [
              el("span", { class: "badge b-fail", text: "Escalate · " + info.badge }),
              deltaBadge(),
              el("span", { class: "clause", text: m.solution.note ? m.solution.note.move : info.short })
            ]),
            el("td", { class: "n", text: "—" })
          ];
          tr = openRow(m.mark.id, m.mark.label, cells);
          tb.appendChild(tr);
          return;
        }

        var selCell = el("td", {}, [
          el("span", { text: skuText(row.cand) }),
          m.unifiedTo ? el("span", { class: "badge b-blue", style: "margin-left:6px", text: "Unified" }) : null,
          deltaBadge()
        ]);

        cells = [
          el("td", { class: "k", text: m.mark.id }),
          el("td", { text: m.mark.label }),
          selCell,
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

      /* the open mark's full search record, next to the row that opened it */
      var openMark = res.marks.filter(function (m) {
        return m.mark.id === state.open && !m.notApplicable;
      })[0];
      if (openMark) body.appendChild(drawSearch(openMark));

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
              el("span", { class: "clause", text: info.short })
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
          var accBody = [el("p", { style: "font-size:.84rem", text: note })];
          /* The design load this mark borrows from a beam above it, resolved
             from THIS run rather than restated in the note. A hand-written
             "1,231 lb per post" went stale the moment the deck live load
             moved and sat next to a reaction schedule saying 1,718. */
          (m.notApplicable.reactions || []).forEach(function (rx) {
            accBody.push(el("div", { class: "dl-row", style: "font-size:.84rem" }, [
              el("span", { class: "clause", text: "Design load from " + rx.id }),
              rx.perBearingLb === null
                ? el("span", { class: "badge b-mute", text: "no reaction published — " + (rx.why || "not computed") })
                : el("span", { style: "font-weight:650",
                               text: FM.comma(Math.round(rx.perBearingLb)) + " lb per bearing" +
                                     (rx.combo ? "  ·  " + rx.combo : "") })
            ]));
          });
          nBody.appendChild(el("details", { class: "acc" }, [
            head, el("div", { class: "acc-body" }, accBody)
          ]));
        });
        body.appendChild(el("div", { style: "margin-top:16px" }, [
          card("Not this engine's member — " + plural(naMarks.length, "mark", "marks"),
            el("span", { class: "badge b-blue", text: "Carried", style: "margin-left:auto" }),
            nBody,
            "Carried deliberately. A schedule that omits them reads as if they were fine — each one is somebody's design, just not this engine's.")
        ]));
      }

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


    /* ---------- master set: elevations, options, and the envelope ---------- */

    function drawMasterSet(ms, sel, delta, basePlan, escIds) {
      var v = ms.v, wrap = el("div", { style: "display:grid;gap:12px" });
      var elevId = sel ? sel.elevationId : null;

      /* Elevation — mutually exclusive, and the take rates are the lot mix */
      var eSeg = el("div", { class: "seg", role: "group", "aria-label": "Elevation" });
      v.elevations.forEach(function (e) {
        /* selecting an elevation lands on that elevation with no options */
        var plain = null;
        v.combinations.forEach(function (c) {
          if (!plain && c.elevationId === e.id && (!c.optionIds || !c.optionIds.length)) plain = c;
        });
        eSeg.appendChild(el("button", {
          text: e.label + (isFinite(e.takeRate) ? " · " + Math.round(e.takeRate * 100) + "%" : ""),
          "aria-pressed": elevId === e.id ? "true" : "false",
          title: e.note || e.label,
          onclick: function () { state.combo = plain ? plain.id : null; state.open = null; redraw(true); }
        }));
      });

      /* Built with — only combinations the builder can actually build */
      var mine = v.combinations.filter(function (c) { return c.elevationId === elevId; });
      var oSeg = el("div", { class: "seg", role: "group", "aria-label": "Options" });
      mine.forEach(function (c) {
        oSeg.appendChild(el("button", {
          text: optionLabel(v, c) + (c.lotsExpected ? " · " + c.lotsExpected + " lots" : ""),
          "aria-pressed": sel && sel.id === c.id ? "true" : "false",
          title: c.label,
          onclick: function () { state.combo = c.id; state.open = null; redraw(true); }
        }));
      });

      wrap.appendChild(el("div", { style: "display:flex;flex-wrap:wrap;gap:8px;align-items:center" },
        [el("span", { class: "badge b-mute", text: "Elevation" }), eSeg]));
      wrap.appendChild(el("div", { style: "display:flex;flex-wrap:wrap;gap:8px;align-items:center" },
        [el("span", { class: "badge b-mute", text: "Built with" }), oSeg]));

      /* what the selection does to the schedule below */
      if (!sel || sel.isBase) {
        wrap.appendChild(el("p", { style: "font-size:.86rem" }, [
          el("strong", { text: "The base case. " }),
          el("span", { text: "The schedule below is this combination, solved end to end — not the base with a " +
            "note attached. Pick another elevation or an option and every number below re-solves. " +
            plural(v.combinations.length, "combination is", "combinations are") + " buildable off this master set." })
        ]));
      } else if (delta) {
        var c = delta.counts;
        var bits = [];
        if (c.moves) bits.push(plural(c.moves, "mark moves", "marks move") + " to a different member");
        if (c.escalates) bits.push(plural(c.escalates, "mark", "marks") + " NO LONGER SOLVES");
        if (c.recovers) bits.push(plural(c.recovers, "mark", "marks") + " solves here but not on the base");
        if (c.added) bits.push(plural(c.added, "mark is", "marks are") + " added");
        if (c.removed) bits.push(plural(c.removed, "mark is", "marks are") + " deleted");
        wrap.appendChild(el("p", { style: "font-size:.86rem" }, [
          el("strong", { text: sel.label + " — " }),
          el("span", { text: (bits.length ? bits.join(", ") + "." : "nothing moves off the base case.") +
            (sel.lotsExpected ? " Expected on " + plural(sel.lotsExpected, "lot", "lots") + " of " +
              (v.lots || basePlan.lots) + "." : "") }),
          el("span", { class: "clause", text: "the schedule below IS this variant" })
        ]));
      }

      /* the delta table */
      if (delta && delta.rows.length) {
        var BADGE = {
          escalates: ["b-fail", "loses its member"], moves: ["b-gold", "moves"],
          recovers: ["b-pass", "now solves"], added: ["b-gold", "added"],
          removed: ["b-blue", "not built"], holds: ["b-mute", "member holds"],
          stuck: ["b-fail", "no member either way"]
        };
        var dtb = el("tbody");
        delta.rows.forEach(function (row) {
          var b = own(BADGE, row.state) || ["b-mute", row.state];
          dtb.appendChild(el("tr", {}, [
            el("td", { class: "k" }, [el("span", { text: row.id }),
              el("span", { class: "clause", style: BLOCK, text: row.label })]),
            el("td", {}, [el("span", { class: "badge " + b[0], text: b[1] })]),
            el("td", { text: row.was ? shortSku(row.was) + (row.wasSpacing ? " @ " + row.wasSpacing + "″" : "")
                                     : (row.state === "added" ? "not on the base plan" : "no member on the base") }),
            el("td", {}, [
              el("span", { text: row.now ? shortSku(row.now) + (row.nowSpacing ? " @ " + row.nowSpacing + "″" : "")
                                         : "—" }),
              row.now && isFinite(row.nowDcr)
                ? el("span", { class: "clause", style: BLOCK, text: "DCR " + fmt(row.nowDcr, 2) }) : null
            ]),
            el("td", { text: row.why || "—" })
          ]));
        });
        wrap.appendChild(el("div", { class: "tw", tabindex: "0", role: "region", "aria-label": "Variant deltas" }, [
          el("table", {}, [
            el("thead", {}, [el("tr", {}, [
              el("th", { text: "Mark" }), el("th", { text: "Change" }), el("th", { text: "Stamped base" }),
              el("th", { text: "This variant" }), el("th", { text: "What changed in the demand" })
            ])]), dtb
          ])
        ]));
      }

      /* the envelope: does one variant cover the whole master set, per mark */
      if (ms.envelope) {
        var gov = [], split = [], none = [];
        ms.envelope.forEach(function (e) {
          if (!e.env.sizedOn) { none.push(e); return; }
          if (e.env.split || !e.env.governedBy) split.push(e); else gov.push(e);
        });
        var eBody = el("div", { style: "display:grid;gap:10px" });
        if (gov.length) {
          eBody.appendChild(dl(gov.map(function (e) {
            var g = e.env.governing;
            /* the governing variant says which DEMAND covers the set. It does
               not say a member exists — a mark that escalates must never read
               as covered because its envelope resolved. */
            var stuck = own(escIds || {}, key(e.mark.id));
            return {
              k: esc(e.mark.id) + " <span class='clause'>" + esc(e.mark.label) +
                 (e.addedByVariant
                    ? " · not on the base sheet — added by " + esc(e.addedByVariant) : "") + "</span>",
              v: (stuck ? "no member on the current selection <span class='clause'>governing demand: "
                        : "size it for <strong>") +
                 esc(g ? g.label : e.env.governedBy) + (stuck ? "</span>" : "</strong>"),
              cls: stuck ? "fail" : "gold"
            };
          })));
        }
        if (split.length) {
          eBody.appendChild(el("p", { style: "font-size:.86rem" }, [
            el("strong", { text: "No single variant covers " +
              split.map(function (e) { return e.mark.id; }).join(", ") + ". " }),
            el("span", { text: "One variant is worse on one driver and better on another, so there is no member " +
              "that provably passes them all — these have to be sized variant by variant, which is what the " +
              "picker above is for." })
          ]));
        }
        if (none.length) {
          eBody.appendChild(el("p", { class: "src-note", text:
            none.map(function (e) { return e.mark.id; }).join(", ") +
            " — not sized on any variant, so there is nothing to envelope. They are listed below with the reason." }));
        }
        var anyStuck = gov.filter(function (e) { return own(escIds || {}, key(e.mark.id)); }).length;
        wrap.appendChild(card("The envelope · " + plural(v.combinations.length, "buildable combination", "buildable combinations"),
          el("span", { class: "badge " + (split.length ? "b-warn" : (anyStuck ? "b-fail" : "b-gold")),
                       text: split.length ? "Split" : (anyStuck ? "Escalations remain" : "Covered"),
                       style: "margin-left:auto" }),
          eBody,
          "A governing variant is named only where it is at least as severe as every other on span, tributary, " +
          "dead, live and roof load at once, gives away no bearing and no depth budget, and is the same kind of " +
          "member. Under those conditions a member that passes it passes all of them — the envelope is proved, " +
          "not assembled out of the worst number in each column."));
      }

      if (v.note) wrap.appendChild(el("p", { class: "src-note", text: v.note }));

      body.appendChild(el("div", { style: "margin-bottom:16px" }, [
        card("Master set · " + plural(v.elevations.length, "elevation", "elevations") + ", " +
             plural(v.options.length, "option", "options"),
          el("span", { class: "badge b-gold", text: plural(v.combinations.length, "combination", "combinations"), style: "margin-left:auto" }),
          wrap,
          "Every variant is solved by the same path as the base — the plan is resolved first and handed to the " +
          "solver, which does not know variants exist. Sizing the base and letting an option move a bearing is " +
          "how a post-permit revision gets manufactured; this is where you find it first.")
      ]));

      var byMark = {};
      if (delta) delta.rows.forEach(function (row) { byMark[key(row.id)] = row; });
      return { byMark: byMark, label: sel ? sel.label : "" };
    }


    /* ---------- the search record for one mark ---------- */

    function drawSearch(m) {
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
        wrap.appendChild(card("Escalated · " + m.mark.id + " — " + info.tag,
          el("span", { class: "badge b-fail", text: info.badge, style: "margin-left:auto" }),
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
        b && b.deflection ? { k: "Deflection row <span class='clause'>" + esc(b.deflection.cite || b.deflection.row) + "</span>",
          v: "L/" + b.deflection.live + " variable · L/" + b.deflection.total + " total" +
             /* keyed on the number, not on the row name, so it disappears by itself
                if the engine ever relaxes the cell */
             (b.deflection.row === "roof_no_ceiling" && b.deflection.total === 180
               ? " <span class='clause'>total is a FIRM OVERLAY — the table allows L/120</span>" : "") } : null,
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
            /* These have to ADD UP, and for a while they did not: the space
               counted only what survived the gates, so gate + bound + evaluated
               came to more than the space it was drawn from. The gate line is
               explicit now and the footer states the identity, so a reader can
               check the arithmetic instead of trusting the footer's word. */
            dl([
              { k: "Search space", v: sol.searchSpace + " candidates in " + (st.families || 0) + " families" },
              { k: "Cut by a gate", v: String(st.prunedByGate || 0) + " <span class='clause'>geometry or procurement · never reached the engine</span>" },
              { k: "Cut by seed bounds", v: String(st.prunedByBound || 0) + " <span class='clause'>H1 · admissible</span>" },
              { k: "Cut by cost dominance", v: String(st.prunedByDominance || 0) + " <span class='clause'>H2 · deeper rung of a family already beaten</span>" },
              { k: "Cut by incumbent", v: String(st.prunedByIncumbent || 0) + " <span class='clause'>H3 · branch and bound</span>" },
              { k: "Engine evaluations", v: String(sol.searchEvaluated || 0) +
                   (st.contextEvaluated ? " <span class='clause'>+" + st.contextEvaluated +
                    " more evaluated afterwards, to fill in the ladder below</span>" : "") +
                   (st.cacheHits ? " (+" + st.cacheHits + " cached)" : ""), total: true }
            ])
          ]), "gate + bounds + dominance + incumbent + evaluations = the search space. " +
              "Every cut is exact — no candidate was dropped on a guess"));
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
              "a licensed engineer seals anything." })
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

    /* Descriptive, never causal — and scoped to what could actually reach THIS
       mark. Listing every field on which two packs differ puts the tile roof
       next to a floor joist, and the eye draws the inference the caption
       disclaims. So: diff the two DEMANDS the engine was handed, then add the
       two policy inputs that never appear in a demand. */
    function markDelta(mark, plan, a, b) {
      var out = [];
      if (!a || !b) return out;
      var da = safeDemand(mark, plan, a, null), db = safeDemand(mark, plan, b, null);
      if (da && db) out = demandDelta(da, db);
      if (a.maxDCR !== b.maxDCR) {
        out.push("firm DCR target " + fmt(a.maxDCR, 2) + " → " + fmt(b.maxDCR, 2));
      }
      var seen = {}, added = [], dropped = [];
      a.palette.forEach(function (p) { seen[key(p.species + " " + p.grade)] = 1; });
      b.palette.forEach(function (p) {
        var k = key(p.species + " " + p.grade);
        if (!own(seen, k)) added.push(shortSku(p.species + " " + p.grade));
        else seen[k] = 2;
      });
      Object.keys(seen).forEach(function (k) {
        if (seen[k] === 1) dropped.push(shortSku(k.replace("k:", "")));
      });
      if (added.length) out.push("palette adds " + added.join(", "));
      if (dropped.length) out.push("palette drops " + dropped.join(", "));
      return out;
    }

    function drawMatrix(plan) {
      var packs = FM.weights.PACKS;
      var cmp = FM.solver.compare(plan, packs);

      /* common / varies / partial / unanswered come from solver.compare(), and
         the badge and its sentence come from solver.portability() — the screen
         and the exported record must not be able to disagree about whether a
         mark is portable. */
      var rows = cmp.rows.map(function (row) {
        var sizes = {}, mats = {}, spacings = {};
        row.cells.forEach(function (c) {
          if (c.notApplicable || !c.sku) return;
          sizes[key(c.sku.split(" ")[0])] = 1;
          mats[key(c.sku.split(" ").slice(1).join(" "))] = 1;
          spacings[key(String(c.spacing || 0))] = 1;
        });
        var axes = [];
        if (Object.keys(sizes).length > 1) axes.push("size");
        if (Object.keys(mats).length > 1) axes.push("grade");
        if (Object.keys(spacings).length > 1) axes.push("spacing");
        /* the member most regions agree on, so a deviating cell can be marked */
        var tally = {}, modal = null;
        row.cells.forEach(function (c) {
          if (!c.sku) return;
          var k = key(c.sku + "@" + (c.spacing || 0));
          tally[k] = (own(tally, k) || 0) + 1;
          if (!modal || tally[k] > tally[modal]) modal = k;
        });
        var port = FM.solver.portability(row);
        return { row: row, axes: axes, modal: modal, port: port, group: port.key,
                 silent: (row.silentPacks || []).length, na: (row.naPacks || []).length };
      });

      body.appendChild(el("div", { class: "grid g5", style: "margin-bottom:6px" }, [
        FM.statCard(String(cmp.commonMarks), "One member everywhere", cmp.commonMarks ? "pass" : ""),
        FM.statCard(String(cmp.varyingMarks), "Regionally forced", cmp.varyingMarks ? "gold" : ""),
        FM.statCard(String(cmp.partialMarks), "Answered in some regions", cmp.partialMarks ? "gold" : ""),
        FM.statCard(String(cmp.unansweredMarks), "Unanswered anywhere", cmp.unansweredMarks ? "fail" : ""),
        FM.statCard(String(cmp.solvedMarks) + "/" + plan.marks.length, "Marks with an answer")
      ]));

      var st8 = {}, nStates = 0;
      packs.forEach(function (p) {
        (p.states || []).forEach(function (s) {
          if (!own(st8, key(s))) { st8[key(s)] = 1; nStates++; }
        });
      });
      body.appendChild(line(
        "One master set, solved independently in " + plural(packs.length, "region pack", "region packs") +
        " across " + plural(nStates, "state", "states") + ". " +
        plural(cmp.commonMarks, "mark is", "marks are") + " one member in every region — buy those in a " +
        "single order. " + plural(cmp.varyingMarks, "is", "are") + " regionally forced, " +
        cmp.partialMarks + " answered in some regions and silent in others, and " +
        cmp.unansweredMarks + " with no member anywhere on this board.",
        "each cell is an independent solve — no cell is inferred from another"));

      var GROUPS = [
        { id: "varies", t: "Regionally forced — the member changes with the market" },
        { id: "common", t: "One member in every region — the whole point of a master set" },
        { id: "partial", t: "Answered in some regions, silent in others — not portable as it stands" },
        { id: "unanswered", t: "No member anywhere on this board" }
      ];

      var tb = el("tbody");
      var nCols = packs.length + 1;
      GROUPS.forEach(function (g) {
        var mine = rows.filter(function (r) { return r.group === g.id; });
        if (!mine.length) return;
        tb.appendChild(el("tr", {}, [
          el("td", { colspan: String(nCols), style: "background:var(--surface-2)" }, [
            el("span", { class: "badge " + mine[0].port.tone, text: String(mine.length) }),
            el("span", { class: "clause", text: g.t })
          ])
        ]));
        mine.forEach(function (r) {
          var row = r.row;
          var cells = [el("td", { class: "k", style: STICKY }, [
            el("span", { text: row.mark.id }),
            el("span", { class: "badge " + r.port.tone, style: "margin-left:6px",
                         title: r.port.text,
                         text: r.port.badge + (g.id === "varies" && r.axes.length ? " · " + r.axes.join(" + ") : "") }),
            /* the sentence, not just the colour — it has to survive being read on paper */
            el("span", { class: "clause", style: BLOCK, text: r.port.text }),
            el("span", { class: "clause", style: BLOCK, text: row.mark.label })
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
            cells.push(el("td", { style: "vertical-align:top" }, [
              deviates ? el("span", { class: "badge b-gold", style: "margin-right:6px", text: "Δ" }) : null,
              el("span", { style: "white-space:nowrap", text: shortSku(c.sku) }),
              el("span", { class: "clause", style: BLOCK + "white-space:nowrap;",
                           text: (c.spacing ? c.spacing + "″ · " : "") + "DCR " + fmt(c.dcr, 2) })
            ]));
          });
          tb.appendChild(el("tr", {}, cells));
        });
      });

      body.appendChild(el("div", { class: "tw", tabindex: "0", role: "region", "aria-label": "Cross-region member matrix" }, [
        el("table", {}, [
          el("thead", {}, [el("tr", {}, [el("th", { text: "Mark", style: STICKY_H })].concat(
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
        "Six regions: the board scrolls sideways and the Mark column stays put. Δ marks the region that departs " +
        "from what the other packs agree on. A pack badged wind governs on uplift, which this engine does not " +
        "check — a member in that column is a gravity floor, not a design." }));

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
            var diff = markDelta(r.row.mark, plan, ref, o.pack);
            fRows.push({
              k: esc(r.row.mark.id) + " <span class='clause'>" + esc(shortPack(o.pack)) +
                 " vs " + esc(shortPack(ref)) + "</span>",
              v: esc(shortSku(o.sku)) + " <span class='clause'>where the others take " +
                 esc(shortSku(r.modal ? r.modal.replace("k:", "").split("@")[0] : "—")) + "</span>",
              cls: "gold"
            });
            fRows.push({
              k: "<span class='clause'>what this mark saw differently</span>",
              v: diff.length ? esc(diff.join(" · "))
                             : "nothing — same demand, same policy; the ranking broke a near-tie"
            });
          });
        });
        body.appendChild(el("div", { style: "margin-top:16px" }, [
          card("What forced the change", el("span", { class: "badge b-gold", text: "Regional", style: "margin-left:auto" }),
            dl(fRows),
            "The demand this mark was handed in each pack, diffed, plus the two policy inputs that never appear in " +
            "a demand. It is what the two solves saw differently — not a sensitivity study proving which one carried it.")
        ]));
      }

      var mSet = variantSet(plan);
      body.appendChild(el("div", { style: "margin-top:16px" }, [
        card("Reading this", null, el("div", { style: "display:grid;gap:9px;font-size:.86rem" }, [
          el("p", { text: "A mark with no member in any region is not portable and it is not common — it is unanswered. Counting it as common would turn silence into evidence for this product's central claim." }),
          el("p", { text: "A mark marked common is the same member in every region on this board — build it the same everywhere and buy it in one order. A mark marked varies is regionally forced, and the badge names the axis: size, grade or spacing." }),
          /* read off ASSEMBLY rather than quoted, so a change to the makeup
             cannot leave a stale number on the screen */
          el("p", { text: "The three forcings that actually move members across these six packs are: snow duration " +
            "in the Carolina mountains, which drops C_D from 1.25 to 1.15; concrete tile dead load in the HVHZ, " +
            "which is " + FM.weights.ASSEMBLY.roof_tile.psf + " psf against " +
            FM.weights.ASSEMBLY.roof_shingle.psf + " for shingle; and species availability, which decides what " +
            "the yard can hand the framer." }),
          mSet ? el("p", { text: "This board is the STAMPED BASE of the master set — the elevation the plan.marks are. " +
            mSet.combinations.length + " combinations of elevation and option are buildable off it, and what each one does to the schedule is on the Schedule tab." }) : null,
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

      /* A variant schedule is a full solve of a resolved plan, not the base
         schedule with annotations bolted on — so every stat, banner and
         escalation below belongs to the combination that is selected. */
      var ms = masterSet(plan, pack);
      var sel = ms ? (comboById(ms.v, state.combo) || ms.base) : null;
      var shown = plan, res = null, baseRes = null;
      if (sel && !sel.isBase) {
        var sv = solveVariant(plan, pack, sel.id);
        if (sv) {
          shown = sv.plan; res = sv.res;
          baseRes = FM.solver.solvePlan(plan, pack);
        } else {
          sel = ms.base;      /* the variant would not resolve — fall back, visibly */
          FM.toast("That variant could not be resolved — showing the base case.");
        }
      }
      if (!res) res = FM.solver.solvePlan(plan, pack);
      drawSchedule(res, pack, shown, ms, sel, baseRes);
    }

    draw();
  };
})();

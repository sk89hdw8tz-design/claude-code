/* ============================================================
   Firmark beta — shell, router, state, and the non-calc views.
   The calculation engine lives in engine.js and registers
   itself on FM.engine.
   ============================================================ */

var FM = (function () {
  "use strict";

  /* ---------------- state ---------------- */

  var PROFILES = [
    {
      id: "firm-standard", name: "Firm Standard", active: 14,
      exposure: "C", groundSnow: 40, wind: 115, sdc: "D",
      deflLive: 360, deflTotal: 240, spacing: 16,
      species: "Douglas Fir-Larch", grade: "No. 2", maxDCR: 0.90,
      note: "Default envelope for inland residential work."
    },
    {
      id: "high-wind-coastal", name: "High-Wind Coastal", active: 3,
      exposure: "D", groundSnow: 0, wind: 150, sdc: "B",
      deflLive: 360, deflTotal: 240, spacing: 16,
      species: "Southern Pine", grade: "No.2", maxDCR: 0.85,
      note: "Coastal exposure D; uplift governs more often than gravity."
    },
    {
      id: "snow-country", name: "Snow Country", active: 2,
      exposure: "C", groundSnow: 70, wind: 115, sdc: "C",
      deflLive: 360, deflTotal: 240, spacing: 16,
      species: "Douglas Fir-Larch", grade: "No. 1", maxDCR: 0.90,
      note: "Ground snow 70 psf; C_D 1.15 governs most roof members."
    }
  ];

  /* Projects mirror the product dashboard exactly (see the app screenshot):
     9 total · 4 active · 1 in review · 1 pipeline running · 1 failed. */
  var PROJECTS = [
    { id: "hilltop",        name: "Hilltop Estate",             addr: "15 Summit Crest Dr, Brevard, NC 28712",      status: "Draft",     stage: 0, failedAt: null, inputs: 0, updated: "in 5 hours",   profile: "snow-country",      basis: "Residential Engineered Wood — ASD Default", who: "" },
    { id: "mountain-view",  name: "Mountain View Custom",       addr: "310 Elk Ridge Rd, Asheville, NC 28801",      status: "Draft",     stage: 0, failedAt: null, inputs: 3, updated: "3 days ago",   profile: "snow-country",      basis: "Residential Engineered Wood — ASD Default", who: "" },
    { id: "lot-17",         name: "Lakefront Cottage",          addr: "22 Willow Lake Ln, Hendersonville, NC 28792", status: "Active",   stage: 2, failedAt: null, inputs: 5, updated: "last week",    profile: "firm-standard",     basis: "Residential Engineered Wood — ASD Default", who: "MT", running: true },
    { id: "downtown-1",     name: "Downtown Townhomes Phase 1", addr: "700 Commerce St, Greenville, SC 29601",      status: "Active",    stage: 3, failedAt: 3,    inputs: 5, updated: "3 weeks ago",  profile: "firm-standard",     basis: "Hybrid Prescriptive + Engineered",          who: "SC" },
    { id: "riverside",      name: "Riverside Residence",        addr: "142 River Oak Dr, Forest City, NC 28043",    status: "Active",    stage: 4, failedAt: null, inputs: 5, updated: "last month",   profile: "firm-standard",     basis: "Residential Engineered Wood — ASD Default", who: "J" },
    { id: "coastal-a",      name: "Coastal Duplex A",           addr: "88 Shoreline Blvd, Punta Gorda, FL 33950",   status: "In Review", stage: 6, failedAt: null, inputs: 5, updated: "2 months ago", profile: "high-wind-coastal", basis: "Residential Engineered Wood — LRFD",        who: "SC" },
    { id: "coastal-b",      name: "Coastal Duplex B",           addr: "90 Shoreline Blvd, Punta Gorda, FL 33950",   status: "Active",    stage: 5, failedAt: null, inputs: 5, updated: "2 months ago", profile: "high-wind-coastal", basis: "Residential Engineered Wood — LRFD",        who: "MT" },
    { id: "suburban-ranch", name: "Suburban Ranch Renovation",  addr: "455 Meadow Creek Way, Charlotte, NC 28270",  status: "Approved",  stage: 6, failedAt: null, inputs: 5, updated: "3 months ago", profile: "firm-standard",     basis: "Residential Engineered Wood — ASD Default", who: "J" },
    { id: "pinecrest",      name: "Pinecrest Single Family",    addr: "203 Pine Needle Ct, Spartanburg, SC 29302",  status: "Archived",  stage: 6, failedAt: null, inputs: 5, updated: "5 months ago", profile: "firm-standard",     basis: "Residential Engineered Wood — ASD Default", who: "J" }
  ];

  var ACTIVITY = [
    { text: "Lakefront Cottage pipeline started — Stage 2", when: "3 hours ago" },
    { text: "Downtown Townhomes Phase 1 — sizing stage failed", when: "3 weeks ago", bad: true },
    { text: "Coastal Duplex A submitted for PE review", when: "2 months ago" }
  ];

  var STAGES = ["Site & plan", "Framing", "Sizing", "Load path", "Checks", "Stamped set"];

  /* Calculation sheets. `inputs` drive the engine; results are computed live. */
  var SHEETS = [
    { id: "R-12",  project: "lot-17", role: "Rafter", label: "Roof rafter",
      inputs: { species: "Douglas Fir-Larch", grade: "No. 2", size: "2x10", span: 14.0, spacing: 16,
                dead: 15, live: 0, roofLoad: 20, roofType: "roof_live", repetitive: true, wet: false,
                braced: true, bearing: 3.0, memberUse: "roof_nonplaster", CF: "auto" } },
    { id: "FJ-1",  project: "lot-17", role: "Floor joist", label: "Floor joist · great room",
      inputs: { species: "Douglas Fir-Larch", grade: "No. 2", size: "2x10", span: 14.0, spacing: 16,
                dead: 15, live: 40, roofLoad: 0, roofType: "snow", repetitive: true, wet: false,
                braced: true, bearing: 3.0, memberUse: "floor", CF: "auto" } },
    { id: "HDR-2", project: "lot-17", role: "Header", label: "Window header · south wall",
      inputs: { species: "Douglas Fir-Larch", grade: "No. 2", size: "4x10", span: 6.0, spacing: 96,
                dead: 12, live: 0, roofLoad: 30, roofType: "snow", repetitive: false, wet: false,
                braced: true, bearing: 3.0, memberUse: "roof_nonplaster", CF: "auto" } },
    { id: "R-08",  project: "riverside", role: "Rafter", label: "Roof rafter · main span",
      inputs: { species: "Hem-Fir", grade: "No. 2", size: "2x12", span: 16.0, spacing: 24,
                dead: 15, live: 0, roofLoad: 30, roofType: "snow", repetitive: true, wet: false,
                braced: true, bearing: 3.0, memberUse: "roof_nonplaster", CF: "auto" } }
  ];

  var LOG = [
    { kind: "Assumed", text: "Roof live load 20 psf (no snow at this site)", cite: "ASCE 7 §4.3", sheet: "R-12" },
    { kind: "Assumed", text: "Wind exposure C · suburban terrain", cite: "ASCE 7 §26.7", sheet: null },
    { kind: "Learned", text: "Default to glulam ridge beams for this firm", cite: "From your last 6 projects", sheet: null },
    { kind: "Asked",   text: "Two load paths within 3%: which governs the ridge?", cite: "Flagged for review", sheet: "RB-1" }
  ];

  var AUDIT = [
    { what: "Uploaded Lot 17 floor plan", who: "R. Builder", role: "Builder", at: "09:14" },
    { what: "Overrode ridge → glulam", who: "M. Alvarez", role: "Eng", at: "10:02" },
    { what: "Requested PE review", who: "M. Alvarez", role: "Eng", at: "10:05" },
    { what: "Approved calc package", who: "J. Haberer", role: "PE", at: "14:20" },
    { what: "Applied stamp", who: "J. Haberer", role: "PE", at: "14:21" }
  ];

  var state = {
    route: "dashboard",
    projectId: null,
    sheetId: null,
    density: "detailed",
    locked: false,
    profileId: "firm-standard"
  };

  /* ---------------- tiny DOM helpers ---------------- */

  function el(tag, attrs, kids) {
    var n = document.createElement(tag);
    if (tag === "button" && !(attrs && attrs.type)) n.type = "button";
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === "class") n.className = attrs[k];
      else if (k === "text") n.textContent = attrs[k];
      else if (k === "html") n.innerHTML = attrs[k];
      else if (k.slice(0, 2) === "on") n.addEventListener(k.slice(2), attrs[k]);
      else if (attrs[k] !== null && attrs[k] !== undefined) n.setAttribute(k, attrs[k]);
    });
    (kids || []).forEach(function (c) { if (c) n.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
    return n;
  }
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]; }); }
  function fmt(n, d) {
    if (n === null || n === undefined || isNaN(n)) return "—";
    var v = Number(n).toFixed(d === undefined ? 2 : d);
    return v.replace(/\B(?=(\d{3})+(?!\d)\.)/g, ",");
  }
  function comma(n) { return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ","); }

  function toast(msg) {
    var t = document.getElementById("toast");
    t.textContent = msg;
    t.classList.add("on");
    clearTimeout(t._t);
    t._t = setTimeout(function () { t.classList.remove("on"); }, 2600);
  }

  function dcrClass(d) { return d > 1 ? "fail" : (d > 0.9 ? "warn" : "pass"); }

  /* never render a pass badge for an errored or non-finite result */
  function dcrBadge(r) {
    if (!r || r.error || !isFinite(r.governing.dcr)) {
      return el("span", { class: "badge b-warn", text: "—", title: r && r.message ? r.message : "not evaluated" });
    }
    return el("span", { class: "badge b-" + dcrClass(r.governing.dcr), text: fmt(r.governing.dcr) });
  }

  /* ---------------- sidebar ---------------- */

  var NAV = [
    { group: "Navigation", items: [{ id: "dashboard", label: "Dashboard", ico: "grid" }] },
    /* The pipeline, in the order it runs. A rail that lists the stages in
       sequence is the cheapest possible statement of what this product is:
       geometry, takeoff, loads, calcs, quantities, package. */
    { group: "Pipeline", items: [
      { id: "pipeline", label: "Run", ico: "shield" },
      { id: "cad", label: "1 · Geometry", ico: "ruler" },
      { id: "takeoff", label: "2 · Takeoff", ico: "calc" },
      { id: "jurisdiction", label: "3 · Loads & code", ico: "shield" },
      { id: "sizing", label: "4 · Calculations", ico: "ruler",
        count: function () { return FM.weights ? FM.weights.PACKS.length : 0; } },
      { id: "bom", label: "5 · Materials list", ico: "layers" },
      { id: "planset", label: "6 · PE package", ico: "doc" }
    ] },
    { group: "Manage", items: [
      { id: "projects", label: "Projects", ico: "folder", count: function () { return PROJECTS.length; } },
      { id: "calculations", label: "Calculations", ico: "calc", count: function () { return SHEETS.length; } },
      { id: "policies", label: "Policies", ico: "shield", count: function () { return PROFILES.length; } },
      { id: "materials", label: "Materials", ico: "layers" },
      { id: "output", label: "Output & Docs", ico: "doc" }
    ] },
    { group: "Firmark", items: [
      { id: "admin", label: "Admin", ico: "shield" }
    ] },
    { group: "System", items: [
      { id: "settings", label: "Settings", ico: "gear" },
      { id: "help", label: "Help", ico: "help" }
    ] }
  ];

  var ICONS = {
    grid:   '<rect x="1.5" y="1.5" width="5" height="5" rx="1"/><rect x="9.5" y="1.5" width="5" height="5" rx="1"/><rect x="1.5" y="9.5" width="5" height="5" rx="1"/><rect x="9.5" y="9.5" width="5" height="5" rx="1"/>',
    folder: '<path d="M1.5 4a1 1 0 011-1h3.2l1.3 1.5h6.5a1 1 0 011 1v7a1 1 0 01-1 1h-11a1 1 0 01-1-1V4z"/>',
    calc:   '<rect x="2.5" y="1.5" width="11" height="13" rx="1.2"/><path d="M5 5h6M5 8h2M5 11h2M9.5 8v3M8 9.5h3"/>',
    ruler:  '<rect x="1.5" y="5" width="13" height="6" rx="1"/><path d="M4.2 5v2.2M6.9 5v3.2M9.6 5v2.2M12.3 5v3.2"/>',
    shield: '<path d="M8 1.5l5.5 2v4.2c0 3.2-2.3 5.6-5.5 6.8-3.2-1.2-5.5-3.6-5.5-6.8V3.5l5.5-2z"/>',
    layers: '<path d="M8 1.8L14.5 5 8 8.2 1.5 5 8 1.8z"/><path d="M2.2 8L8 10.9 13.8 8"/><path d="M2.2 11L8 13.9 13.8 11"/>',
    doc:    '<path d="M3.5 1.8h6l3 3v9.4a1 1 0 01-1 1h-8a1 1 0 01-1-1V2.8a1 1 0 011-1z"/><path d="M9.3 1.9v3.2h3.1"/>',
    gear:   '<circle cx="8" cy="8" r="2.3"/><path d="M8 1.6v1.8M8 12.6v1.8M14.4 8h-1.8M3.4 8H1.6M12.5 3.5l-1.3 1.3M4.8 11.2l-1.3 1.3M12.5 12.5l-1.3-1.3M4.8 4.8L3.5 3.5"/>',
    help:   '<circle cx="8" cy="8" r="6.3"/><path d="M6.2 6.2a1.9 1.9 0 013.6.7c0 1.3-1.8 1.6-1.8 2.7"/><circle cx="8" cy="12" r=".7" fill="currentColor" stroke="none"/>'
  };

  function icon(name) {
    return '<svg class="rail-ico" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (ICONS[name] || "") + "</svg>";
  }

  function renderRail() {
    var rail = document.getElementById("rail");
    rail.innerHTML = "";

    /* Inside a sheet the same slot shows that project's nav instead. */
    if (state.route === "sheet" && state.sheetId) {
      var sheet = SHEETS.filter(function (s) { return s.id === state.sheetId; })[0];
      var proj = PROJECTS.filter(function (p) { return p.id === (sheet && sheet.project); })[0];
      rail.appendChild(el("button", { class: "rail-back", onclick: function () { go("calculations"); } },
        [el("span", { html: "&larr;" }), " All calculations"]));
      var g = el("div", { class: "rail-group" });
      g.appendChild(el("div", { class: "rail-label", text: proj ? proj.name : "Project" }));
      SHEETS.filter(function (s) { return s.project === (sheet && sheet.project); }).forEach(function (s) {
        var label = s.id + " · " + s.role;
        var b = el("button", {
          class: "rail-item", onclick: function () { go("sheet", { sheetId: s.id }); },
          "aria-label": label, title: label,
          "aria-current": s.id === state.sheetId ? "page" : null
        }, [el("span", { html: icon("calc") }), el("span", { text: label })]);
        g.appendChild(b);
      });
      rail.appendChild(g);
      var g2 = el("div", { class: "rail-group" });
      g2.appendChild(el("div", { class: "rail-label", text: "Project" }));
      g2.appendChild(el("button", { class: "rail-item", "aria-label": "Project overview", title: "Project overview",
        onclick: function () { go("project", { projectId: sheet && sheet.project }); } },
        [el("span", { html: icon("folder") }), el("span", { text: "Overview" })]));
      g2.appendChild(el("button", { class: "rail-item", "aria-label": "Member schedule", title: "Member schedule",
        onclick: function () { go("output"); } },
        [el("span", { html: icon("doc") }), el("span", { text: "Member schedule" })]));
      rail.appendChild(g2);
      return;
    }

    NAV.forEach(function (grp) {
      var g = el("div", { class: "rail-group" });
      g.appendChild(el("div", { class: "rail-label", text: grp.group }));
      grp.items.forEach(function (it) {
        var kids = [el("span", { html: icon(it.ico) }), el("span", { text: it.label })];
        if (it.count) kids.push(el("span", { class: "rail-count", text: String(it.count()) }));
        g.appendChild(el("button", {
          class: "rail-item", "aria-label": it.label, title: it.label,
          onclick: function () { go(it.id); },
          "aria-current": (state.route === it.id || (it.id === "projects" && state.route === "project")) ? "page" : null
        }, kids));
      });
      rail.appendChild(g);
    });
  }

  /* ---------------- router ----------------

     The app had no URL. Every route was in-memory, so Back left the app
     entirely and Reload dropped you on the dashboard — during a demo, the
     browser's own controls were a cliff. Worse for this product than for
     most: a schedule you want a colleague to look at had no address to send.

     Hash routing, not History API, deliberately. This ships as a single
     file that people open with file:// — pushState throws a SecurityError
     on a file: origin in some browsers and silently does nothing useful in
     others. The hash works everywhere the bundle does.

     Shape:  #/sizing/two-story-2450/fl-hvhz     #/sheet/S-102
     Views own their own segments; the router just carries them. */

  var VIEWS = {};
  var ROUTE_PARAM = { project: "projectId", sheet: "sheetId" };
  var applyingHash = false;   /* suppresses the hashchange we cause ourselves */

  function hashFor(route, opts) {
    var seg = ["#", route];
    var key = ROUTE_PARAM[route];
    if (key && opts[key] !== undefined && opts[key] !== null) seg.push(String(opts[key]));
    else if (key && state[key]) seg.push(String(state[key]));
    if (opts.sub && opts.sub.length) opts.sub.forEach(function (s) { seg.push(String(s)); });
    return seg.join("/");
  }

  function parseHash() {
    var raw = String(location.hash || "").replace(/^#\/?/, "");
    if (!raw) return null;
    var parts = raw.split("/").filter(function (s) { return s !== ""; })
                   .map(function (s) { return decodeURIComponent(s); });
    if (!parts.length) return null;
    return { route: parts[0], args: parts.slice(1) };
  }

  /* A view that carries its own state past the route — which plan and which
     region the Sizing view is showing — registers a codec here rather than
     reaching into the router. Nothing breaks if a view registers nothing. */
  var subRoute = {};
  function registerSubRoute(route, o) { subRoute[route] = o; }

  function go(route, opts) {
    opts = opts || {};
    state.route = route;
    if (opts.projectId !== undefined) state.projectId = opts.projectId;
    if (opts.sheetId !== undefined) state.sheetId = opts.sheetId;

    Array.prototype.forEach.call(document.querySelectorAll(".view"), function (v) {
      v.classList.toggle("active", v.id === "view-" + route);
    });

    /* set a default title first so a view (e.g. the sheet) can override it */
    document.title = "Firmark · " + route.charAt(0).toUpperCase() + route.slice(1);

    var host = document.getElementById("view-" + route);
    if (host && VIEWS[route]) { host.innerHTML = ""; VIEWS[route](host); }

    renderRail();
    var main = document.getElementById("main");
    main.scrollTop = 0;
    /* move focus to the new view so a screen reader lands in the fresh content */
    if (host) { host.setAttribute("tabindex", "-1"); host.focus({ preventScroll: true }); }
    closeRailDrawer();

    /* Normally a hash-driven navigation does not write the hash back — it came
       from there. The exception is a CORRECTION: we landed here because the
       link named something this build does not have, so the address bar is
       lying and has to be rewritten to what is actually on screen. */
    if (!opts.fromHash || opts.replace) {
      var sub = subRoute[route] && subRoute[route].read ? subRoute[route].read() : null;
      var want = hashFor(route, { projectId: opts.projectId, sheetId: opts.sheetId, sub: sub });
      if (location.hash !== want) {
        applyingHash = true;
        /* replace, not push, when the view is only correcting or refining
           itself — that should not fill the Back stack */
        if (opts.replace) location.replace(location.href.split("#")[0] + want);
        else location.hash = want;
        applyingHash = false;
      }
    }
  }

  /* Called by a view when its own sub-state changes (plan, region, tab) so the
     URL keeps up without the view knowing how the URL is spelled. */
  function syncHash(replace) {
    if (applyingHash) return;
    var sub = subRoute[state.route] && subRoute[state.route].read ? subRoute[state.route].read() : null;
    var want = hashFor(state.route, { sub: sub });
    if (location.hash === want) return;
    applyingHash = true;
    if (replace) location.replace(location.href.split("#")[0] + want);
    else location.hash = want;
    applyingHash = false;
  }

  function applyHash() {
    if (applyingHash) return;
    var h = parseHash();
    /* No hash at all — a cold open. Go to the dashboard and WRITE the hash, so
       the address bar describes the app from the first paint and the first
       navigation has something to come back to. `replace` so the empty-hash
       entry is not left behind as a Back target that lands nowhere. */
    if (!h) { go("dashboard", { replace: true }); return; }
    /* an unknown route is a typo or a stale link, not a crash */
    if (!VIEWS[h.route] && !document.getElementById("view-" + h.route)) {
      toast("No such view: " + h.route);
      /* replace so the address bar stops naming a view that does not exist */
      go("dashboard", { fromHash: true, replace: true });
      return;
    }
    var opts = { fromHash: true };
    var key = ROUTE_PARAM[h.route];
    if (key && h.args.length) {
      /* Validate the id rather than handing an unknown one to a view that
         will quietly render its first row. A link naming a sheet or project
         that no longer exists must say so — a stale link that renders the
         WRONG record perfectly is worse than one that renders nothing. */
      var pool = h.route === "sheet" ? SHEETS : PROJECTS;
      var found = pool.filter(function (x) { return x.id === h.args[0]; })[0];
      if (found) opts[key] = h.args[0];
      else {
        toast("This link names " + h.route + " “" + h.args[0] + "”, which this build does not have. " +
              "Showing " + (pool[0] && pool[0].id) + " instead.");
        opts[key] = pool[0] && pool[0].id;
        opts.replace = true;
      }
    }
    /* hand the view its own segments BEFORE it renders, so it draws the
       right thing once rather than drawing the default and then correcting */
    var sr = subRoute[h.route];
    if (sr && sr.write) {
      try { sr.write(key ? h.args.slice(1) : h.args); }
      catch (e) { toast("That link points at something this build does not have."); }
    }
    go(h.route, opts);
  }

  /* ---------------- shared bits ---------------- */

  function pageHead(title, sub, actions) {
    var copy = el("div", { class: "page-head-copy" }, [el("h1", { text: title })]);
    if (sub) copy.appendChild(el("p", { text: sub }));
    var head = el("div", { class: "page-head" }, [copy]);
    if (actions && actions.length) head.appendChild(el("div", { class: "page-head-actions" }, actions));
    return head;
  }

  function betaStrip(text) {
    return el("div", { class: "beta-strip" }, [
      el("span", { class: "badge b-gold", text: "Beta" }),
      el("span", { text: text })
    ]);
  }

  function statCard(v, l, cls) {
    return el("div", { class: "card stat" }, [
      el("span", { class: "stat-v" + (cls ? " " + cls : ""), text: v }),
      el("span", { class: "stat-l", text: l })
    ]);
  }

  function dl(rows) {
    var d = el("div", { class: "dl" });
    rows.forEach(function (r) {
      if (!r) return;
      d.appendChild(el("div", { class: "dl-row" + (r.total ? " total" : "") }, [
        el("span", { class: "dl-k", html: r.k }),
        el("span", { class: "dl-v" + (r.cls ? " " + r.cls : ""), html: r.v })
      ]));
    });
    return d;
  }

  function card(title, badge, bodyNode, footText) {
    var c = el("div", { class: "card" });
    if (title) {
      var h = el("div", { class: "card-head" }, [el("span", { class: "card-title", text: title })]);
      if (badge) h.appendChild(badge);
      c.appendChild(h);
    }
    c.appendChild(el("div", { class: "card-body" }, [bodyNode]));
    if (footText) c.appendChild(el("div", { class: "card-foot", text: footText }));
    return c;
  }

  /* M2: a table row that navigates must be reachable and operable by keyboard */
  function rowLink(label, onActivate, cells) {
    return el("tr", {
      class: "clickable", tabindex: "0", role: "button", "aria-label": label,
      onclick: onActivate,
      onkeydown: function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onActivate(); }
      }
    }, cells);
  }

  function statusBadge(s) {
    var m = { "Draft": "b-mute", "Active": "b-blue", "In Review": "b-gold", "Approved": "b-pass", "Archived": "b-mute" };
    return el("span", { class: "badge " + (m[s] || "b-mute"), text: s });
  }

  function pipe(stage, failedAt) {
    var p = el("div", { class: "pipe" });
    for (var i = 0; i < 6; i++) {
      var cls = "pipe-seg";
      if (failedAt && i === failedAt - 1) cls += " bad";
      else if (i < stage - 1) cls += " on";
      else if (i === stage - 1) cls += " cur";
      p.appendChild(el("span", { class: cls }));
    }
    return p;
  }

  /* Strongest first. Table 4A writes "No. 1"; Table 4B writes "No.1" with no
     space — both spellings have to be here or every Southern Pine grade falls to
     the bottom of the list and the three weakest grades in the book sort above
     No.1. That is not cosmetic: the sheet substitutes grades[0] when a species
     changes, so an unranked list hands the user "Construction". */
  var GRADE_RANK = [
    "Dense Select Structural", "Select Structural", "Non-Dense Select Structural",
    "Dense Structural 86", "Dense Structural 72", "Dense Structural 65",
    "No. 1 & Btr", "No. 1 Dense", "No.1 Dense", "No. 1", "No.1", "No.1 Non-Dense",
    "No. 1/No. 2",
    "No. 2 Dense", "No.2 Dense", "No. 2", "No.2", "No.2 Non-Dense",
    "No. 3", "No.3", "No.3 and Stud", "Stud",
    "Construction", "Standard", "Utility"
  ];
  function gradeRank(g) {
    var i = GRADE_RANK.indexOf(g);
    return i === -1 ? GRADE_RANK.length : i;
  }

  function getProfile(id) {
    return PROFILES.filter(function (p) { return p.id === id; })[0] || PROFILES[0];
  }

  /* Single source of engine inputs, so a list row and its sheet can never disagree. */
  function inputsFor(sheet) {
    var out = {};
    Object.keys(sheet.inputs).forEach(function (k) { out[k] = sheet.inputs[k]; });
    return out;
  }

  /* ---------------- views: dashboard ---------------- */

  VIEWS.dashboard = function (host) {
    host.appendChild(pageHead("Dashboard", "Every lot on one board, intake to sealed set.", [
      el("button", { class: "btn", onclick: function () { go("materials"); }, text: "Materials" }),
      el("button", { class: "btn btn-primary", onclick: function () { toast("Beta: project intake isn’t wired up yet."); }, text: "+ New project" })
    ]));

    host.appendChild(betaStrip("Demonstration build — not for construction. Projects are sample data; the calculation engine is live and computes from sourced NDS values."));

    var c = { total: PROJECTS.length, active: 0, review: 0, running: 0, failed: 0 };
    PROJECTS.forEach(function (p) {
      if (p.status === "Active") c.active++;
      if (p.status === "In Review") c.review++;
      if (p.running) c.running++;
      if (p.failedAt) c.failed++;
    });

    host.appendChild(el("div", { class: "grid g5", style: "margin-bottom:16px" }, [
      statCard(String(c.total), "Total projects"),
      statCard(String(c.active), "Active", "blue"),
      statCard(String(c.review), "In review", "gold"),
      statCard(String(c.running), "Pipelines running", "blue"),
      statCard(String(c.failed), "Failed", "fail")
    ]));

    /* filter bar */
    var q = "", statusFilter = "All statuses", layout = "grid";
    var bar = el("div", { class: "filter-bar", style: "margin-bottom:14px" });
    var search = el("input", { type: "text", placeholder: "Search projects…", "aria-label": "Search projects", style: "min-width:210px" });
    var sel = el("select", { "aria-label": "Filter by status" },
      ["All statuses", "Draft", "Active", "In Review", "Approved", "Archived"].map(function (o) { return el("option", { text: o }); }));
    var seg = el("div", { class: "seg", role: "group", "aria-label": "Layout" }, [
      el("button", { "data-lay": "grid", "aria-pressed": "true", text: "Grid" }),
      el("button", { "data-lay": "table", "aria-pressed": "false", text: "Table" })
    ]);
    bar.appendChild(search); bar.appendChild(sel);
    bar.appendChild(el("span", { style: "margin-left:auto" }, [seg]));
    host.appendChild(bar);

    var listHost = el("div");
    host.appendChild(listHost);

    function visible() {
      var ql = q.trim().toLowerCase();
      return PROJECTS.filter(function (p) {
        if (statusFilter !== "All statuses" && p.status !== statusFilter) return false;
        if (ql && (p.name + " " + p.addr).toLowerCase().indexOf(ql) === -1) return false;
        return true;
      });
    }

    function draw() {
      listHost.innerHTML = "";
      var rows = visible();
      if (!rows.length) {
        listHost.appendChild(el("div", { class: "empty", text: "No projects match that filter." }));
        return;
      }
      if (layout === "table") {
        var tb = el("tbody");
        rows.forEach(function (p) {
          tb.appendChild(rowLink("Open project " + p.name, function () { go("project", { projectId: p.id }); }, [
            el("td", { class: "k", text: p.name }),
            el("td", { text: p.addr }),
            el("td", {}, [statusBadge(p.status)]),
            el("td", { class: "n", text: p.stage ? "Stage " + p.stage + "/6" : "Not started" }),
            el("td", { class: "n", text: p.inputs + "/5" }),
            el("td", { class: "n", text: p.updated })
          ]));
        });
        listHost.appendChild(el("div", { class: "tw", tabindex: "0", role: "region", "aria-label": "Scrollable table" }, [el("table", {}, [
          el("thead", {}, [el("tr", {}, [
            el("th", { text: "Project" }), el("th", { text: "Site" }), el("th", { text: "Status" }),
            el("th", { class: "n", text: "Pipeline" }), el("th", { class: "n", text: "Inputs" }), el("th", { class: "n", text: "Updated" })
          ])]), tb
        ])]));
        return;
      }
      var grid = el("div", { class: "grid g3" });
      rows.forEach(function (p) {
        grid.appendChild(el("div", {
          class: "card proj", tabindex: "0", role: "button",
          onclick: function () { go("project", { projectId: p.id }); },
          onkeydown: function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go("project", { projectId: p.id }); } }
        }, [
          el("div", { class: "proj-top" }, [
            el("div", {}, [el("div", { class: "proj-name", text: p.name }), el("div", { class: "proj-addr", text: p.addr })]),
            el("span", { style: "margin-left:auto" }, [statusBadge(p.status)])
          ]),
          el("div", { class: "proj-foot", style: "margin-bottom:-3px" }, [
            el("span", { text: "Pipeline" }),
            el("span", { style: "margin-left:auto", text: p.stage ? "Stage " + p.stage + "/6" : "Not started" })
          ]),
          pipe(p.stage, p.failedAt),
          el("div", { class: "proj-foot" }, [
            el("span", { text: "Inputs" }),
            el("span", { style: "margin-left:auto", text: p.inputs + "/5" })
          ]),
          el("div", { class: "meter-bar", style: "height:4px" }, [
            el("span", { class: "meter-fill", style: "display:block;width:" + (p.inputs / 5 * 100) + "%" })
          ]),
          el("div", { class: "proj-foot", style: "border-top:1px solid var(--line);padding-top:8px;margin-top:2px" }, [
            el("span", { text: p.updated }),
            el("span", { style: "margin-left:auto;text-align:right", text: p.basis })
          ])
        ]));
      });
      listHost.appendChild(grid);
    }

    search.addEventListener("input", function () { q = this.value; draw(); });
    sel.addEventListener("change", function () { statusFilter = this.value; draw(); });
    Array.prototype.forEach.call(seg.querySelectorAll("button"), function (b) {
      b.addEventListener("click", function () {
        layout = b.getAttribute("data-lay");
        Array.prototype.forEach.call(seg.querySelectorAll("button"), function (x) {
          x.setAttribute("aria-pressed", x === b ? "true" : "false");
        });
        draw();
      });
    });
    draw();

    /* recent activity */
    var act = el("div", { class: "dl" });
    ACTIVITY.forEach(function (a) {
      act.appendChild(el("div", { class: "dl-row" }, [
        el("span", { class: "dl-k" }, [
          el("span", { class: "badge " + (a.bad ? "b-fail" : "b-blue"), text: a.bad ? "Failed" : "Run" }),
          el("span", { text: " " + a.text })
        ]),
        el("span", { class: "dl-v", text: a.when })
      ]));
    });
    host.appendChild(el("div", { style: "margin-top:18px" }, [
      card("Recent activity", null, act, null)
    ]));

    var logBody = el("div", { class: "dl" });
    LOG.forEach(function (l) {
      var kindCls = l.kind === "Asked" ? "b-gold" : (l.kind === "Learned" ? "b-blue" : "b-mute");
      logBody.appendChild(el("div", { class: "dl-row" }, [
        el("span", { class: "dl-k" }, [el("span", { class: "badge " + kindCls, text: l.kind }), el("span", { text: " " + l.text })]),
        el("span", { class: "dl-v", text: l.cite })
      ]));
    });

    host.appendChild(el("div", { class: "grid g2", style: "margin-top:14px" }, [
      card("Decision log", el("span", { class: "badge b-mute", text: "Sample", style: "margin-left:auto" }), logBody,
        "Every question, assumption, and learned preference, each tied to a clause"),
      card("Audit trail · Lot 17", el("span", { class: "badge b-mute", text: "Sample", style: "margin-left:auto" }),
        dl(AUDIT.map(function (a) {
          return { k: esc(a.what), v: esc(a.who) + " · " + esc(a.role) + " · " + esc(a.at), cls: a.role === "PE" ? "gold" : "" };
        })),
        "Append-only · exportable · retained with the project")
    ]));
  };

  VIEWS.admin = function (host) {
    host.appendChild(pageHead("Admin", "Org roles and tenant boundary."));
    host.appendChild(el("div", { class: "grid g2" }, [
      card("Members", null, dl([
        { k: "J. Haberer", v: "PE of record", cls: "gold" },
        { k: "M. Alvarez", v: "Engineer" },
        { k: "S. Cole", v: "Engineer" },
        { k: "R. Builder", v: "Builder" }
      ]), "Least privilege by default · the stamp is the PE’s alone"),
      card("Tenant", null, dl([
        { k: "Organization", v: "Sample Structural PC" },
        { k: "Isolation", v: "Per-organization boundary" },
        { k: "Cross-tenant reads", v: "Never", cls: "gold" },
        { k: "Audit", v: "Append-only" }
      ]), "Switching firms switches the whole data boundary")
    ]));
  };

  /* ---------------- views: projects ---------------- */

  VIEWS.projects = function (host) {
    host.appendChild(pageHead("Projects", PROJECTS.length + " projects · reuse a master plan across every lot"));

    var tb = el("tbody");
    PROJECTS.forEach(function (p) {
      tb.appendChild(rowLink("Open project " + p.name, function () { go("project", { projectId: p.id }); }, [
        el("td", { class: "k", text: p.name }),
        el("td", { text: p.addr }),
        el("td", {}, [statusBadge(p.status)]),
        el("td", { style: "min-width:110px" }, [pipe(p.stage, p.failedAt)]),
        el("td", { class: "n", text: p.stage + "/6" }),
        el("td", { text: getProfile(p.profile).name }),
        el("td", { class: "n", text: p.updated })
      ]));
    });

    host.appendChild(el("div", { class: "tw", tabindex: "0", role: "region", "aria-label": "Scrollable table" }, [
      el("table", {}, [
        el("thead", {}, [el("tr", {}, [
          el("th", { text: "Project" }), el("th", { text: "Site" }), el("th", { text: "Status" }),
          el("th", { text: "Pipeline" }), el("th", { class: "n", text: "Stage" }),
          el("th", { text: "Design profile" }), el("th", { class: "n", text: "Updated" })
        ])]),
        tb
      ])
    ]));
  };

  VIEWS.project = function (host) {
    var p = PROJECTS.filter(function (x) { return x.id === state.projectId; })[0] || PROJECTS[0];
    var prof = getProfile(p.profile);
    var sheets = SHEETS.filter(function (s) { return s.project === p.id; });

    host.appendChild(pageHead(p.name, p.addr, [
      statusBadge(p.status),
      el("button", { class: "btn", onclick: function () { go("projects"); }, text: "All projects" })
    ]));

    host.appendChild(el("div", { class: "card", style: "margin-bottom:16px" }, [
      el("div", { class: "card-body" }, [
        el("div", { class: "lbl", text: "Pipeline · " + STAGES[Math.max(0, p.stage - 1)] }),
        el("div", { style: "margin:8px 0 6px" }, [pipe(p.stage, p.failedAt)]),
        el("div", { class: "proj-foot" }, STAGES.map(function (s, i) {
          return el("span", { style: "flex:1;color:" + (i < p.stage ? "var(--pass)" : "var(--faint)"), text: s });
        }))
      ])
    ]));

    var sheetRows = el("tbody");
    if (!sheets.length) {
      sheetRows.appendChild(el("tr", {}, [el("td", { colspan: "4", text: "No calculation sheets on this project yet." })]));
    }
    sheets.forEach(function (s) {
      var r = FM.engine ? FM.engine.run(inputsFor(s)) : null;
      sheetRows.appendChild(rowLink("Open sheet " + s.id, function () { go("sheet", { sheetId: s.id }); }, [
        el("td", { class: "k", text: s.id }),
        el("td", { text: s.role + " · " + s.inputs.size + " " + s.inputs.species + " " + s.inputs.grade }),
        el("td", { text: r && !r.error ? r.governing.name : "—" }),
        el("td", { class: "n" }, [dcrBadge(r)])
      ]));
    });

    host.appendChild(el("div", { class: "grid g2" }, [
      el("div", {}, [
        el("div", { class: "lbl", style: "margin-bottom:7px", text: "Member schedule" }),
        el("div", { class: "tw", tabindex: "0", role: "region", "aria-label": "Scrollable table" }, [el("table", {}, [
          el("thead", {}, [el("tr", {}, [el("th", { text: "Mark" }), el("th", { text: "Member" }), el("th", { text: "Governs" }), el("th", { class: "n", text: "DCR" })])]),
          sheetRows
        ])])
      ]),
      card("Design profile · " + prof.name, null, dl([
        { k: "Exposure", v: prof.exposure },
        { k: "Ground snow", v: prof.groundSnow + " psf" },
        { k: "Wind speed", v: prof.wind + " mph" },
        { k: "Seismic (SDC)", v: prof.sdc },
        { k: "Live-load defl.", v: "&le; L/" + prof.deflLive },
        { k: "Default spacing", v: prof.spacing + "&quot; o.c." },
        { k: "Species / grade", v: esc(prof.species) + " " + esc(prof.grade) },
        { k: "Max DCR", v: fmt(prof.maxDCR), cls: "gold" }
      ]), "Applied to " + prof.active + " active projects · override anytime, every change logged")
    ]));
  };

  /* ---------------- views: calculations ---------------- */

  VIEWS.calculations = function (host) {
    host.appendChild(pageHead("Calculations", SHEETS.length + " sheets · every check cites its clause", [
      el("button", { class: "btn btn-primary", onclick: function () { toast("Beta: new-sheet creation isn’t wired up yet."); }, text: "+ New calculation" })
    ]));

    var tb = el("tbody");
    SHEETS.forEach(function (s) {
      var proj = PROJECTS.filter(function (p) { return p.id === s.project; })[0];
      var r = FM.engine ? FM.engine.run(inputsFor(s)) : null;
      tb.appendChild(rowLink("Open sheet " + s.id + " — " + s.label, function () { go("sheet", { sheetId: s.id }); }, [
        el("td", { class: "k", text: s.id }),
        el("td", { text: s.label }),
        el("td", { text: proj ? proj.name : "—" }),
        el("td", { class: "n", text: s.inputs.size }),
        el("td", { text: s.inputs.species + " " + s.inputs.grade }),
        el("td", { text: r && !r.error ? r.governing.name : "—" }),
        el("td", { class: "n" }, [dcrBadge(r)])
      ]));
    });

    host.appendChild(el("div", { class: "tw", tabindex: "0", role: "region", "aria-label": "Scrollable table" }, [el("table", {}, [
      el("thead", {}, [el("tr", {}, [
        el("th", { text: "Mark" }), el("th", { text: "Sheet" }), el("th", { text: "Project" }),
        el("th", { class: "n", text: "Size" }), el("th", { text: "Material" }), el("th", { text: "Governs" }), el("th", { class: "n", text: "DCR" })
      ])]),
      tb
    ])]));
  };

  /* ---------------- views: policies ---------------- */

  VIEWS.policies = function (host) {
    host.appendChild(pageHead("Policies", "Design profiles — the envelope the engine designs within."));
    host.appendChild(betaStrip("Editing a profile is read-only in this build; the values below drive the live calculations."));

    var g = el("div", { class: "grid g3" });
    PROFILES.forEach(function (p) {
      var body = dl([
        { k: "Exposure", v: p.exposure },
        { k: "Ground snow", v: p.groundSnow + " psf" },
        { k: "Wind speed", v: p.wind + " mph" },
        { k: "Seismic (SDC)", v: p.sdc },
        { k: "Live-load defl.", v: "&le; L/" + p.deflLive },
        { k: "Total-load defl.", v: "&le; L/" + p.deflTotal },
        { k: "Default spacing", v: p.spacing + "&quot; o.c." },
        { k: "Species / grade", v: esc(p.species) + " " + esc(p.grade) },
        { k: "Max DCR", v: fmt(p.maxDCR), cls: "gold" }
      ]);
      var c = card(p.name, el("span", { class: "badge b-mute", text: p.active + " projects", style: "margin-left:auto" }), body, p.note);
      g.appendChild(c);
    });
    host.appendChild(g);
  };

  /* ---------------- views: output ---------------- */

  VIEWS.output = function (host) {
    host.appendChild(pageHead("Output & Docs", "Calc-report packages and plan sets prepared for PE review."));

    var rows = el("tbody");
    SHEETS.forEach(function (s) {
      var r = FM.engine ? FM.engine.run(inputsFor(s)) : null;
      var proj = PROJECTS.filter(function (p) { return p.id === s.project; })[0];
      rows.appendChild(el("tr", {}, [
        el("td", { class: "k", text: s.id }),
        el("td", { text: proj ? proj.name : "—" }),
        el("td", { text: s.inputs.size + " " + s.inputs.species + " " + s.inputs.grade }),
        el("td", { text: r && !r.error ? r.governing.name : "—" }),
        el("td", { class: "n" }, [dcrBadge(r)]),
        el("td", { text: r && !r.error ? r.basis : "—" })
      ]));
    });

    host.appendChild(el("div", { class: "tw", tabindex: "0", role: "region", "aria-label": "Scrollable table", style: "margin-bottom:16px" }, [el("table", {}, [
      el("thead", {}, [el("tr", {}, [
        el("th", { text: "Mark" }), el("th", { text: "Project" }), el("th", { text: "Member" }),
        el("th", { text: "Governs" }), el("th", { class: "n", text: "DCR" }), el("th", { text: "Basis" })
      ])]),
      rows
    ])]));

    host.appendChild(el("div", { class: "grid g2" }, [
      card("Export", null, el("div", {}, [
        el("p", { style: "font-size:.86rem;margin-bottom:10px", text: "A calc-report package and a plan set prepared for PE review, assembled straight from the design. A licensed PE reviews and seals every package; this software never does, and the seal block it produces is empty." }),
        el("div", { class: "chips" }, [
          el("button", { class: "btn btn-sm", onclick: function () { FM.exportCalcs(); }, text: "Download calc record (.txt)" }),
          el("button", { class: "btn btn-sm", onclick: function () { toast("Beta: DXF plan-set export isn’t wired up yet."); }, text: "Plan set (DXF)" })
        ])
      ]), "Nothing ships without your licensed PE’s review and seal"),
      card("Approval gate", el("span", { class: "badge b-gold", text: "PE only", style: "margin-left:auto" }),
        dl([
          { k: "Design & run the engine", v: "Engineer · PE" },
          { k: "Override a design value", v: "Engineer · PE" },
          { k: "Accept the package for sealing", v: "PE only", cls: "gold" },
          { k: "Read another firm’s data", v: "Never" }
        ]),
        "Least privilege · the stamp is the PE’s alone")
    ]));
  };

  /* ---------------- views: settings & help ---------------- */

  VIEWS.settings = function (host) {
    host.appendChild(pageHead("Settings", "Firm, roles, and appearance."));
    host.appendChild(el("div", { class: "grid g2" }, [
      card("Organization", null, dl([
        { k: "Firm", v: "Sample Structural PC" },
        { k: "Your role", v: "PE of record", cls: "gold" },
        { k: "Tenant", v: "Isolated per firm" },
        { k: "Default profile", v: getProfile(state.profileId).name }
      ]), "Switching firms switches the whole data boundary"),
      card("Appearance", null, el("div", { class: "field" }, [
        el("span", { class: "lbl", text: "Theme" }),
        el("div", { class: "seg", role: "group", "aria-label": "Theme" }, [
          el("button", { onclick: function () { setTheme("light"); }, "data-theme-btn": "light", text: "Light" }),
          el("button", { onclick: function () { setTheme("dark"); }, "data-theme-btn": "dark", text: "Dark" }),
          el("button", { onclick: function () { setTheme("system"); }, "data-theme-btn": "system", text: "System" })
        ]),
        el("p", { class: "field-hint", style: "margin-top:8px", text: "Figures and calculation sheets are legible in both themes." })
      ]), null)
    ]));
    syncThemeButtons();
  };

  VIEWS.help = function (host) {
    host.appendChild(pageHead("Help", "The shell, the palette, and your first project."));
    host.appendChild(el("div", { class: "grid g2" }, [
      card("Keyboard", null, dl([
        { k: "Command palette", v: "Ctrl K &nbsp;or&nbsp; /" },
        { k: "Go to Dashboard", v: "g d" },
        { k: "Go to Calculations", v: "g c" },
        { k: "Go to Sizing", v: "g z" },
        { k: "Go to Projects", v: "g p" },
        { k: "Go to Materials", v: "g m" },
        { k: "Go to Help", v: "g h" },
        { k: "Close / dismiss", v: "Esc" }
      ]), "Press g, release, then the second key"),
      card("The shell", null, el("div", { style: "display:grid;gap:9px;font-size:.86rem" }, [
        el("p", { text: "Firmark runs inside one persistent shell: a top bar, a single sidebar slot, and the working surface. Routes change what fills the slot and the surface; the shell itself never swaps out from under you." }),
        el("p", { text: "Inside a calculation the same slot shows that project’s navigation instead — its sheets and the project overview. The portal nav is one click away." }),
        el("p", { text: "Two header toggles change how much a sheet shows without changing what it computes. Quick collapses the design conditions and hides the factor ledger; Detailed shows the full record. Lock puts the sheet in presentation mode — a view state for working over someone’s shoulder, not an approval." })
      ]), null)
    ]));
  };

  /* ---------------- theme ---------------- */

  function setTheme(mode) {
    if (mode === "system") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", mode);
    try { localStorage.setItem("fm-theme", mode); } catch (e) {}
    syncThemeButtons();
  }
  function currentTheme() {
    return document.documentElement.getAttribute("data-theme") || "system";
  }
  /* what the user actually SEES right now — system mode has no attribute */
  function effectiveTheme() {
    var t = document.documentElement.getAttribute("data-theme");
    if (t) return t;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function syncThemeButtons() {
    Array.prototype.forEach.call(document.querySelectorAll("[data-theme-btn]"), function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-theme-btn") === currentTheme() ? "true" : "false");
    });
  }

  /* ---------------- command palette ---------------- */

  var paletteItems = [];
  var paletteIdx = 0;

  function buildPaletteItems() {
    var items = [];
    NAV.forEach(function (g) {
      g.items.forEach(function (it) {
        items.push({ group: "Go to", label: it.label, run: function () { go(it.id); } });
      });
    });
    PROJECTS.forEach(function (p) {
      items.push({ group: "Projects", label: p.name, hint: p.status, run: function () { go("project", { projectId: p.id }); } });
    });
    SHEETS.forEach(function (s) {
      items.push({ group: "Calculations", label: s.id + " · " + s.label, run: function () { go("sheet", { sheetId: s.id }); } });
    });
    items.push({ group: "Actions", label: "Toggle theme", run: function () { setTheme(currentTheme() === "dark" ? "light" : "dark"); } });
    items.push({ group: "Actions", label: "Download calc record", run: function () { FM.exportCalcs(); } });
    return items;
  }

  var paletteReturn = null;

  function openPalette() {
    paletteReturn = document.activeElement;
    var scrim = document.getElementById("paletteScrim");
    scrim.classList.add("on");
    document.getElementById("paletteOpen").setAttribute("aria-expanded", "true");
    var inp = document.getElementById("paletteInput");
    inp.value = "";
    renderPalette("");
    inp.focus();
  }
  function closePalette() {
    var scrim = document.getElementById("paletteScrim");
    if (!scrim.classList.contains("on")) return;
    scrim.classList.remove("on");
    document.getElementById("paletteOpen").setAttribute("aria-expanded", "false");
    /* return focus where the user left it */
    var back = paletteReturn && document.contains(paletteReturn) ? paletteReturn : document.getElementById("paletteOpen");
    paletteReturn = null;
    if (back && back.focus) back.focus();
  }

  /* keep Tab inside the dialog while it is open */
  function trapPaletteTab(e) {
    if (e.key !== "Tab") return;
    var scrim = document.getElementById("paletteScrim");
    if (!scrim.classList.contains("on")) return;
    var focusables = scrim.querySelectorAll("input, button, [tabindex]:not([tabindex='-1'])");
    if (!focusables.length) return;
    var first = focusables[0], last = focusables[focusables.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }
  function renderPalette(q) {
    var list = document.getElementById("paletteList");
    var all = buildPaletteItems();
    var ql = q.trim().toLowerCase();
    paletteItems = ql ? all.filter(function (i) { return (i.label + " " + i.group).toLowerCase().indexOf(ql) !== -1; }) : all;
    paletteIdx = 0;
    list.innerHTML = "";
    if (!paletteItems.length) {
      list.appendChild(el("div", { class: "palette-empty", text: "No matches. Try a project name or a page." }));
      return;
    }
    var lastGroup = null;
    paletteItems.forEach(function (it, i) {
      if (it.group !== lastGroup) {
        list.appendChild(el("div", { class: "palette-group", text: it.group }));
        lastGroup = it.group;
      }
      var node = el("div", {
        class: "palette-item", role: "option", id: "pal-" + i,
        "aria-selected": i === 0 ? "true" : "false",
        onclick: function () { closePalette(); it.run(); }
      }, [el("span", { text: it.label })]);
      if (it.hint) node.appendChild(el("span", { class: "kbd kbd-light", text: it.hint }));
      list.appendChild(node);
    });
    syncPaletteSel();
  }
  function syncPaletteSel() {
    var nodes = document.querySelectorAll(".palette-item");
    Array.prototype.forEach.call(nodes, function (n, i) {
      n.setAttribute("aria-selected", i === paletteIdx ? "true" : "false");
      if (i === paletteIdx) {
        n.scrollIntoView({ block: "nearest" });
        document.getElementById("paletteInput").setAttribute("aria-activedescendant", n.id);
      }
    });
  }

  /* ---------------- rail drawer (mobile) ---------------- */

  function isMobile() { return window.matchMedia("(max-width: 860px)").matches; }

  /* One place that owns drawer state, so aria-expanded and inert can never drift. */
  function setDrawer(open) {
    var rail = document.getElementById("rail");
    var scrim = document.getElementById("scrim");
    var btn = document.getElementById("railToggle");
    if (!rail) return;
    if (isMobile()) {
      rail.classList.toggle("open", open);
      scrim.classList.toggle("on", open);
      rail.toggleAttribute("inert", !open);
      rail.setAttribute("aria-hidden", open ? "false" : "true");
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    } else {
      rail.classList.remove("open");
      scrim.classList.remove("on");
      rail.removeAttribute("inert");
      rail.removeAttribute("aria-hidden");
      btn.setAttribute("aria-expanded",
        document.getElementById("shell").classList.contains("rail-collapsed") ? "false" : "true");
    }
  }
  function toggleRailDrawer() { setDrawer(!document.getElementById("rail").classList.contains("open")); }
  function closeRailDrawer() { setDrawer(false); }

  /* ---------------- export ---------------- */

  function exportCalcs() {
    if (!FM.engine) { toast("Engine not loaded."); return; }
    var lines = [];
    lines.push("FIRMARK — CALCULATION RECORD (beta)");
    lines.push("Generated from the Firmark beta build. Demonstration only — not for construction.");
    lines.push("A licensed PE reviews and stamps every package; AI never does.");
    lines.push("");
    SHEETS.forEach(function (s) {
      var r = FM.engine.run(inputsFor(s));
      lines.push(new Array(73).join("="));
      lines.push("MARK " + s.id + " — " + s.label);
      if (r.error) {
        /* never emit a mark that reads like it was checked when it was not */
        lines.push("  NOT EVALUATED — " + r.message);
        lines.push("");
        return;
      }
      lines.push("Member: " + s.inputs.size + " " + s.inputs.species + " " + s.inputs.grade +
                 " @ " + s.inputs.spacing + " in o.c. · span " + s.inputs.span + " ft");
      lines.push("Basis: " + r.basis);
      lines.push("");
      r.checks.forEach(function (c) {
        lines.push("  " + c.name.toUpperCase());
        c.lines.forEach(function (l) { lines.push("    " + l.replace(/<[^>]+>/g, "")); });
        lines.push("    DCR = " + fmt(c.dcr) + (c.dcr <= 1 ? "  OK" : "  NG"));
        lines.push("");
      });
      lines.push("  GOVERNING: " + r.governing.name + " · DCR " + fmt(r.governing.dcr) +
                 " · combination " + r.governing.combo);
      lines.push("");
    });
    /* The boundaries, from the one renderer in scope.js.

       This used to be `"Scope limits: " + FM.engine.LIMITS.join(" | ")` — a
       thirteen-item paraphrase, run together on a single 1,177-character line,
       missing twelve of the twenty-four calc-spec §8 boundaries. Item 17 was
       among the missing ones, and item 17 is the one that says the bearing
       check this record publishes above is a bearing-stress check and not a
       connection design. §8 says the list prints verbatim and unabridged on
       every output; the schedule export honoured that and this one did not. */
    var ruleLine = new Array(73).join("=");
    FM.scope.render(function (s) { lines.push(s === undefined ? "" : s); }, {
      heading: function (t) { lines.push(""); lines.push(ruleLine); lines.push(t); lines.push(ruleLine); lines.push(""); }
    });
    var blob = new Blob([lines.join("\n")], { type: "text/plain" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "firmark-calc-record.txt";
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
    toast("Calc record downloaded.");
  }

  /* ---------------- boot ---------------- */

  /* ---------------- the closed gate ----------------

     Nothing behind this renders until someone is signed in. Not because the
     data is sensitive — it is a demo — but because every artefact downstream
     is attributable. An approval trail whose entries say "someone" is not a
     trail, and the gates in pipeline.js are the reason the speed claim is
     defensible at all. */

  function showGate(show) {
    var g = document.getElementById("gate");
    var shell = document.getElementById("shell");
    if (!g) return;
    if (show) { g.removeAttribute("hidden"); shell.setAttribute("aria-hidden", "true"); }
    else { g.setAttribute("hidden", ""); shell.removeAttribute("aria-hidden"); }
  }

  function wireGate() {
    var form = document.getElementById("gateForm");
    if (!form || !FM.auth) return;

    function refresh() {
      var signedIn = FM.auth.require();
      showGate(!signedIn);
      if (signedIn) {
        var u = FM.auth.state().user;
        var av = document.querySelector(".avatar");
        if (av) { av.textContent = u.initials; av.title = u.name + " · " + u.roles.join(", "); }
      }
    }

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var err = document.getElementById("gateErr");
      var r = FM.auth.login(document.getElementById("gateUser").value,
                            document.getElementById("gatePass").value);
      if (!r.ok) {
        err.textContent = r.why;
        err.removeAttribute("hidden");
        document.getElementById("gatePass").value = "";
        document.getElementById("gatePass").focus();
        return;
      }
      err.setAttribute("hidden", "");
      refresh();
      toast("Signed in as " + r.user.name + ". Every approval from here carries this name.");
      applyHash();
    });

    refresh();
    if (!FM.auth.require()) {
      var uf = document.getElementById("gateUser");
      if (uf) uf.focus();
    }
    FM.signOut = function () {
      FM.auth.logout();
      if (FM.pipeline) { /* the trail survives; the session does not */ }
      refresh();
      toast("Signed out. The approval trail is kept — it is a record, not a session.");
    };
    FM.refreshGate = refresh;
  }

  /* The stage rail — the same chip row on every pipeline view, so a stage is
     never looked at without its position in the run being visible. */
  function stageRail(currentId) {
    var wrap = el("div", { class: "stage-rail", role: "list", "aria-label": "Pipeline stages" });
    if (!FM.pipeline) return wrap;
    var snap = FM.pipeline.snapshot();
    snap.stages.forEach(function (row, i) {
      var cls = "stage-chip";
      if (row.status === "approved") cls += " is-approved";
      else if (row.status === "stale") cls += " is-stale";
      else if (row.status === "rejected") cls += " is-rejected";
      if (row.stage.id === currentId) cls += " is-current";
      var label = row.status === "approved" ? "approved"
                : row.status === "stale" ? "needs re-approval"
                : row.status === "rejected" ? "rejected" : "not approved";
      wrap.appendChild(el("button", {
        class: cls, role: "listitem",
        title: row.stage.label + " — " + label + ". " + row.stage.gate,
        onclick: function () { go("pipeline"); }
      }, [
        el("span", { class: "dot" }),
        el("span", { text: String(i + 1) + " · " + row.stage.label }),
        el("span", { class: "sep", text: label })
      ]));
    });
    return wrap;
  }

  function boot() {
    try {
      var saved = localStorage.getItem("fm-theme");
      if (saved && saved !== "system") document.documentElement.setAttribute("data-theme", saved);
    } catch (e) {}

    document.getElementById("railToggle").addEventListener("click", function () {
      if (window.matchMedia("(max-width: 860px)").matches) { toggleRailDrawer(); return; }
      var shell = document.getElementById("shell");
      var collapsed = shell.classList.toggle("rail-collapsed");
      this.setAttribute("aria-expanded", collapsed ? "false" : "true");
    });
    document.getElementById("scrim").addEventListener("click", closeRailDrawer);
    var skip = document.querySelector(".skip");
    if (skip) skip.addEventListener("click", function (e) {
      e.preventDefault();
      var m = document.getElementById("main");
      if (m) { m.setAttribute("tabindex", "-1"); m.focus(); }
    });
    var themeBtn = document.getElementById("themeToggle");
    function syncThemeBtn() {
      themeBtn.setAttribute("aria-label",
        "Theme: " + currentTheme() + " — switch to " + (effectiveTheme() === "dark" ? "light" : "dark"));
    }
    themeBtn.addEventListener("click", function () {
      setTheme(effectiveTheme() === "dark" ? "light" : "dark");
      syncThemeBtn();
    });
    syncThemeBtn();
    document.getElementById("paletteOpen").addEventListener("click", openPalette);
    document.getElementById("paletteScrim").addEventListener("click", function (e) {
      if (e.target === this) closePalette();
    });

    var inp = document.getElementById("paletteInput");
    inp.addEventListener("input", function () { renderPalette(this.value); });
    inp.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown") { e.preventDefault(); paletteIdx = Math.min(paletteIdx + 1, paletteItems.length - 1); syncPaletteSel(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); paletteIdx = Math.max(paletteIdx - 1, 0); syncPaletteSel(); }
      else if (e.key === "Enter") { e.preventDefault(); var it = paletteItems[paletteIdx]; if (it) { closePalette(); it.run(); } }
      else if (e.key === "Escape") { closePalette(); }
    });

    /* global keys: Ctrl+K / "/" palette, g-sequences */
    var gPending = false, gTimer = null;
    document.addEventListener("keydown", trapPaletteTab);

    document.addEventListener("keydown", function (e) {
      var t = e.target;
      var typing = t && (t.tagName === "INPUT" || t.tagName === "SELECT" || t.tagName === "TEXTAREA" || t.isContentEditable);

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); openPalette(); return; }
      if (e.key === "Escape") { closePalette(); closeRailDrawer(); return; }
      if (typing) return;
      if (e.key === "/") { e.preventDefault(); openPalette(); return; }

      if (gPending) {
        var map = { d: "dashboard", c: "calculations", p: "projects", m: "materials", h: "help", o: "output", s: "settings", z: "sizing" };
        var target = map[e.key.toLowerCase()];
        gPending = false; clearTimeout(gTimer);
        if (target) { e.preventDefault(); go(target); }
        return;
      }
      if (e.key.toLowerCase() === "g") {
        gPending = true;
        gTimer = setTimeout(function () { gPending = false; }, 1200);
      }
    });

    wireGate();

    window.addEventListener("hashchange", applyHash);
    /* open on whatever the URL says — a reload, a bookmark or a pasted link
       all land where they point; an empty hash lands on the dashboard */
    applyHash();
  }

  return {
    boot: boot, go: go, el: el, esc: esc, fmt: fmt, comma: comma, toast: toast,
    registerSubRoute: registerSubRoute, syncHash: syncHash, stageRail: stageRail,
    dl: dl, card: card, pageHead: pageHead, betaStrip: betaStrip, statCard: statCard,
    dcrClass: dcrClass, dcrBadge: dcrBadge, gradeRank: gradeRank, effectiveTheme: effectiveTheme, getProfile: getProfile, exportCalcs: exportCalcs, inputsFor: inputsFor,
    VIEWS: VIEWS, state: state, SHEETS: SHEETS, PROJECTS: PROJECTS, PROFILES: PROFILES, ACTIVITY: ACTIVITY,
    engine: null, solver: null, weights: null
  };
})();

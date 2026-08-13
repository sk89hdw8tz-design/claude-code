/* ============================================================
   Materials browser — reads the embedded MATDATA payload, which
   was extracted verbatim from the public material-databases repo.
   Every value shown here carries the seed file it came from.
   ============================================================ */

(function () {
  "use strict";

  var el = FM.el, card = FM.card, fmt = FM.fmt, comma = FM.comma;

  var TABS = [
    { id: "sections",   label: "Section properties", cite: "sections" },
    { id: "sawn",       label: "Sawn design values", cite: "species_grades" },
    { id: "southern",   label: "Southern Pine",      cite: "southern_pine" },
    { id: "glulam",     label: "Glulam",             cite: "glulam" },
    { id: "steel",      label: "Steel shapes",       cite: "steel_shapes" }
  ];

  function meta(key) {
    return (window.MATDATA && MATDATA.meta && MATDATA.meta[key]) || {};
  }

  function citation(key) {
    var m = meta(key);
    if (!m.source_file) return null;
    return el("p", { class: "src-note", style: "margin-top:10px" }, [
      el("span", { text: "Source: " }),
      el("strong", { text: m.source_file }),
      el("span", { text: m.dataset_version ? "  ·  dataset revision " + m.dataset_version : "" }),
      el("br"),
      el("span", { text: m.governing_reference || m.title || "" })
    ]);
  }

  /* meta = { total, query, noun } — the count context.

     A filter with no matches used to render a table with headers and nothing
     under them, while the stat cards overhead still read "86 S4S sections".
     Nothing on the page said the list had been filtered, so an empty catalog
     and an over-narrow filter looked identical. The row count travels with the
     table now, and an empty result says what was searched and what it searched
     against — a table is not allowed to be silent about being empty. */
  function tableFrom(cols, rows, rowFn, meta) {
    meta = meta || {};
    var total = meta.total === undefined ? rows.length : meta.total;
    var noun = meta.noun || "rows";
    var q = (meta.query || "").trim();

    var tb = el("tbody");
    if (!rows.length) {
      tb.appendChild(el("tr", {}, [
        el("td", { colspan: String(cols.length), class: "empty-cell" }, [
          el("div", { class: "empty", style: "margin:0" }, [
            el("strong", { text: q ? "No " + noun + " match “" + q + "”" : "No " + noun + " in this tab" }),
            el("div", { class: "clause", style: "margin-top:4px",
                        text: q ? "The tab holds " + comma(total) + " " + noun +
                                  ". Clear the filter to see them."
                                : "The catalog payload carries none for this tab." })
          ])
        ])
      ]));
    } else {
      rows.forEach(function (r) { tb.appendChild(rowFn(r)); });
    }

    var showing = rows.length === total
      ? comma(total) + " " + noun
      : comma(rows.length) + " of " + comma(total) + " " + noun + (q ? " · filter “" + q + "”" : "");

    return el("div", {}, [
      el("div", { class: "tw", tabindex: "0", role: "region",
                  "aria-label": "Material data table — " + showing }, [
        el("table", {}, [
          el("thead", {}, [el("tr", {}, cols.map(function (c) {
            return el("th", { class: c.n ? "n" : null, text: c.label });
          }))]),
          tb
        ])
      ]),
      el("div", { class: "clause", style: "margin-top:6px", role: "status",
                  text: "Showing " + showing })
    ]);
  }

  FM.VIEWS.materials = function (host) {
    if (!window.MATDATA) {
      host.appendChild(FM.pageHead("Materials", "Catalog data"));
      host.appendChild(el("div", { class: "empty", text: "Material catalog failed to load." }));
      return;
    }

    /* "About this data" used to toast a github.com URL.

       This bundle is opened over file:// with no network. A toast that names a
       web address is not a citation, it is a lie of omission dressed as one:
       nothing in it can be clicked, nothing can be checked, and the one
       question the button exists to answer — WHERE DID THESE NUMBERS COME
       FROM — goes unanswered while looking answered.

       Every dataset in MATDATA already carries its own provenance, so the
       button now discloses it in place, offline, from the payload itself. */
    var provOpen = false;
    var provHost = el("div");
    var provBtn = el("button", {
      class: "btn btn-sm", "aria-expanded": "false", "aria-controls": "mat-provenance",
      text: "About this data",
      onclick: function () {
        provOpen = !provOpen;
        provBtn.setAttribute("aria-expanded", provOpen ? "true" : "false");
        drawProvenance();
        if (provOpen) provHost.scrollIntoView({ block: "nearest" });
      }
    });

    function drawProvenance() {
      provHost.innerHTML = "";
      if (!provOpen) return;
      var meta = (MATDATA.meta || {});
      var rows = el("tbody");
      var keys = [], k;
      for (k in meta) if (Object.prototype.hasOwnProperty.call(meta, k)) keys.push(k);
      keys.sort();
      keys.forEach(function (key) {
        var m = meta[key] || {};
        rows.appendChild(el("tr", {}, [
          el("td", { class: "k", text: key }),
          el("td", { text: m.source_file || "—" }),
          el("td", { class: "n", text: m.dataset_version || "—" }),
          el("td", { text: m.governing_reference || m.title || "—" })
        ]));
      });
      if (!keys.length) {
        rows.appendChild(el("tr", {}, [el("td", { colspan: "4", class: "empty-cell" }, [
          el("div", { class: "empty", style: "margin:0",
            text: "This payload carries no provenance block, so nothing here can be traced to a seed file." })
        ])]));
      }
      provHost.appendChild(el("div", { style: "margin-bottom:16px" }, [
        card("Where these numbers come from",
          el("span", { class: "badge b-blue", text: keys.length + " datasets", style: "margin-left:auto" }),
          el("div", {}, [
            el("p", { style: "font-size:.85rem;margin-bottom:10px",
              text: "Each catalog below was extracted verbatim from a published seed file and is " +
                    "reserialised into this bundle, never edited. The source file and dataset " +
                    "revision travel with every value the engine reads, and the same strings are " +
                    "printed on each calculation sheet under Provenance." }),
            el("div", { class: "tw", tabindex: "0", role: "region", "aria-label": "Catalog provenance" }, [
              el("table", {}, [
                el("thead", {}, [el("tr", {}, [
                  el("th", { text: "Dataset" }), el("th", { text: "Source file" }),
                  el("th", { class: "n", text: "Revision" }), el("th", { text: "Governing reference" })
                ])]),
                rows
              ])
            ])
          ]),
          "This bundle carries no network. Nothing here is fetched, and nothing here can be — " +
          "what is printed above is the whole of what the payload knows about itself.")
      ]));
    }

    host.appendChild(FM.pageHead("Materials", "Sourced reference values — the number on the sheet is the number in the book.",
      [provBtn]));
    provHost.id = "mat-provenance";
    host.appendChild(provHost);

    /* headline counts, computed from the payload itself */
    var counts = [
      { v: comma(MATDATA.sections.length), l: "S4S sections" },
      { v: comma(MATDATA.species_grades.length), l: "Sawn design values" },
      { v: comma(MATDATA.southern_pine.records.length), l: "Southern Pine rows" },
      { v: comma(MATDATA.glulam.length), l: "Glulam classes" },
      { v: comma(MATDATA.steel_shapes.length), l: "W-shapes" }
    ];
    host.appendChild(el("div", { class: "grid g5", style: "margin-bottom:16px" },
      counts.map(function (c) { return FM.statCard(c.v, c.l); })));

    var state = { tab: "sections", q: "" };

    var tabs = el("div", { class: "seg", role: "tablist", "aria-label": "Material catalog", style: "margin-bottom:12px" });

    function selectTab(id, focus) {
      state.tab = id;
      Array.prototype.forEach.call(tabs.querySelectorAll("button"), function (b, i) {
        var on = TABS[i].id === id;
        b.setAttribute("aria-selected", on ? "true" : "false");
        b.tabIndex = on ? 0 : -1;
        if (on && focus) b.focus();
      });
      draw();
    }

    TABS.forEach(function (t, i) {
      tabs.appendChild(el("button", {
        role: "tab", id: "mtab-" + t.id, "aria-controls": "mpanel",
        "aria-selected": t.id === state.tab ? "true" : "false",
        tabindex: t.id === state.tab ? "0" : "-1",
        text: t.label,
        onclick: function () { selectTab(t.id, false); },
        onkeydown: function (e) {
          var n = null;
          if (e.key === "ArrowRight") n = TABS[(i + 1) % TABS.length];
          else if (e.key === "ArrowLeft") n = TABS[(i - 1 + TABS.length) % TABS.length];
          else if (e.key === "Home") n = TABS[0];
          else if (e.key === "End") n = TABS[TABS.length - 1];
          if (n) { e.preventDefault(); selectTab(n.id, true); }
        }
      }));
    });

    var search = el("input", {
      type: "text", placeholder: "Filter…", "aria-label": "Filter material rows",
      style: "max-width:240px"
    });
    search.addEventListener("input", function () { state.q = this.value; draw(); });

    host.appendChild(el("div", { class: "filter-bar", style: "margin-bottom:12px" }, [tabs, search]));

    var body = el("div", { id: "mpanel", role: "tabpanel", tabindex: "0" });
    host.appendChild(body);

    function match(hay) {
      var q = state.q.trim().toLowerCase();
      return !q || hay.toLowerCase().indexOf(q) !== -1;
    }

    function draw() {
      body.innerHTML = "";
      var node, key;

      if (state.tab === "sections") {
        key = "sections";
        var rows = MATDATA.sections.filter(function (r) { return match(r.nominal + " " + r.size_class); });
        node = tableFrom(
          [{ label: "Nominal" }, { label: "Class" }, { label: "b (in)", n: 1 }, { label: "d (in)", n: 1 },
           { label: "A (in²)", n: 1 }, { label: "Sx (in³)", n: 1 }, { label: "Ix (in⁴)", n: 1 }],
          rows,
          function (r) {
            return el("tr", {}, [
              el("td", { class: "k", text: r.nominal }),
              el("td", { text: r.size_class }),
              el("td", { class: "n", text: fmt(r.b_in, 3) }),
              el("td", { class: "n", text: fmt(r.d_in, 3) }),
              el("td", { class: "n", text: fmt(r.A_in2, 3) }),
              el("td", { class: "n", text: fmt(r.Sx_in3, 3) }),
              el("td", { class: "n", text: fmt(r.Ix_in4, 2) })
            ]);
          },
          { total: MATDATA.sections.length, query: state.q, noun: "S4S sections" }
        );
      } else if (state.tab === "sawn" || state.tab === "southern") {
        key = state.tab === "sawn" ? "species_grades" : "southern_pine";
        var src = state.tab === "sawn" ? MATDATA.species_grades : MATDATA.southern_pine.records;
        var recs = src.filter(function (r) { return match(r.species + " " + r.grade + " " + r.size_class); });
        node = tableFrom(
          [{ label: "Species" }, { label: "Grade" }, { label: "Size class" },
           { label: "Fb", n: 1 }, { label: "Ft", n: 1 }, { label: "Fv", n: 1 },
           { label: "Fc⊥", n: 1 }, { label: "Fc", n: 1 }, { label: "E", n: 1 }, { label: "Emin", n: 1 }],
          recs,
          function (r) {
            var v = r.values_psi || {};
            return el("tr", {}, [
              el("td", { class: "k" }, [
                el("span", { text: r.species }),
                r.common ? el("span", { class: "badge b-gold", style: "margin-left:6px", text: "Common" }) : null
              ]),
              el("td", { text: r.grade }),
              el("td", { text: r.size_class }),
              el("td", { class: "n", text: v.Fb == null ? "—" : comma(v.Fb) }),
              el("td", { class: "n", text: v.Ft == null ? "—" : comma(v.Ft) }),
              el("td", { class: "n", text: v.Fv == null ? "—" : comma(v.Fv) }),
              el("td", { class: "n", text: v.Fc_perp == null ? "—" : comma(v.Fc_perp) }),
              el("td", { class: "n", text: v.Fc == null ? "—" : comma(v.Fc) }),
              el("td", { class: "n", text: v.E == null ? "—" : comma(v.E) }),
              el("td", { class: "n", text: v.Emin == null ? "—" : comma(v.Emin) })
            ]);
          },
          { total: src.length, query: state.q,
            noun: state.tab === "sawn" ? "sawn design-value rows" : "Southern Pine rows" }
        );
      } else if (state.tab === "glulam") {
        key = "glulam";
        var gl = MATDATA.glulam.filter(function (r) { return match(r.stress_class); });
        node = tableFrom(
          [{ label: "Stress class" }, { label: "Fbx+", n: 1 }, { label: "Fbx−", n: 1 }, { label: "Fvx", n: 1 },
           { label: "Fc⊥x", n: 1 }, { label: "Ex (app)", n: 1 }, { label: "Ex min", n: 1 }, { label: "Ft", n: 1 }, { label: "Fc", n: 1 }],
          gl,
          function (r) {
            return el("tr", {}, [
              el("td", { class: "k", text: r.stress_class }),
              el("td", { class: "n", text: r.Fbx_pos == null ? "—" : comma(r.Fbx_pos) }),
              el("td", { class: "n", text: r.Fbx_neg == null ? "—" : comma(r.Fbx_neg) }),
              el("td", { class: "n", text: r.Fvx == null ? "—" : comma(r.Fvx) }),
              el("td", { class: "n", text: r.Fc_perp_x == null ? "—" : comma(r.Fc_perp_x) }),
              el("td", { class: "n", text: r.Ex_app == null ? "—" : comma(r.Ex_app) }),
              el("td", { class: "n", text: r.Ex_min == null ? "—" : comma(r.Ex_min) }),
              el("td", { class: "n", text: r.Ft == null ? "—" : comma(r.Ft) }),
              el("td", { class: "n", text: r.Fc == null ? "—" : comma(r.Fc) })
            ]);
          },
          { total: MATDATA.glulam.length, query: state.q, noun: "glulam classes" }
        );
      } else {
        key = "steel_shapes";
        var st = MATDATA.steel_shapes.filter(function (r) { return match(r.designation + " " + r.family); });
        node = tableFrom(
          [{ label: "Shape" }, { label: "W (lb/ft)", n: 1 }, { label: "A (in²)", n: 1 }, { label: "d (in)", n: 1 },
           { label: "Ix (in⁴)", n: 1 }, { label: "Sx (in³)", n: 1 }, { label: "Zx (in³)", n: 1 }, { label: "ry (in)", n: 1 }],
          st,
          function (r) {
            return el("tr", {}, [
              el("td", { class: "k", text: r.designation }),
              el("td", { class: "n", text: fmt(r.W_lbft, 1) }),
              el("td", { class: "n", text: fmt(r.A_in2, 2) }),
              el("td", { class: "n", text: fmt(r.d_in, 2) }),
              el("td", { class: "n", text: comma(r.Ix_in4) }),
              el("td", { class: "n", text: fmt(r.Sx_in3, 1) }),
              el("td", { class: "n", text: fmt(r.Zx_in3, 1) }),
              el("td", { class: "n", text: fmt(r.ry_in, 2) })
            ]);
          },
          { total: MATDATA.steel_shapes.length, query: state.q, noun: "W-shapes" }
        );
      }

      body.setAttribute("aria-labelledby", "mtab-" + state.tab);
      body.appendChild(node);
      var c = citation(key);
      if (c) body.appendChild(c);
    }

    draw();

    /* the honest note about what the catalog does NOT carry */
    host.appendChild(el("div", { style: "margin-top:18px" }, [
      card("Not in the catalog", el("span", { class: "badge b-warn", text: "Gap", style: "margin-left:auto" }),
        el("div", { style: "display:grid;gap:8px;font-size:.85rem" }, [
          el("p", { text: "The NDS size-factor (C_F) table is not published in the material catalog. The engine therefore treats C_F as a typed input, marked as unsourced on every sheet that uses it, rather than substituting a remembered value." }),
          el("p", { class: "src-note", text: "Checked: Table 4A seed metadata, member_db migrations, and the phase-1 member database. The only C_F numbers in the repo are per-record wet-service threshold helpers, flagged by the seed itself as not a citable adjustment table." })
        ]),
        "Values are never invented, interpolated, or decoded from model names")
    ]));
  };
})();

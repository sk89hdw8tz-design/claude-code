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

  function tableFrom(cols, rows, rowFn) {
    var tb = el("tbody");
    rows.forEach(function (r) { tb.appendChild(rowFn(r)); });
    return el("div", { class: "tw", tabindex: "0", role: "region", "aria-label": "Material data table" }, [
      el("table", {}, [
        el("thead", {}, [el("tr", {}, cols.map(function (c) {
          return el("th", { class: c.n ? "n" : null, text: c.label });
        }))]),
        tb
      ])
    ]);
  }

  FM.VIEWS.materials = function (host) {
    if (!window.MATDATA) {
      host.appendChild(FM.pageHead("Materials", "Catalog data"));
      host.appendChild(el("div", { class: "empty", text: "Material catalog failed to load." }));
      return;
    }

    host.appendChild(FM.pageHead("Materials", "Sourced reference values — the number on the sheet is the number in the book.", [
      el("button", {
        class: "btn btn-sm",
        onclick: function () { FM.toast("Catalogs are published for review at github.com/Firmark/material-databases"); },
        text: "About this data"
      })
    ]));

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
          }
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
          }
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
          }
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
          }
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

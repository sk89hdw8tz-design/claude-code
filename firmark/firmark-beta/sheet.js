/* ============================================================
   The calculation sheet. Header strip → inputs → live results.
   Recomputes on every input change; nothing is cached.
   ============================================================ */

(function () {
  "use strict";

  var el = FM.el, fmt = FM.fmt, card = FM.card, dl = FM.dl;

  function pct(d) { return Math.round(d * 100) + "%"; }

  /* short labels for the header chips — the full names carry glyphs
     (Fc⊥) that mangle under text-transform: uppercase */
  var SHORT = {
    "Bending": "Bending",
    "Shear": "Shear",
    "Deflection (live)": "Defl · L",
    "Deflection (total)": "Defl · TL",
    "Bearing (Fc⊥)": "Bearing"
  };
  function utilClass(d) { return d > 1 ? "is-fail" : (d > 0.9 ? "is-warn" : "is-pass"); }

  FM.VIEWS.sheet = function (host) {
    var sheet = FM.SHEETS.filter(function (s) { return s.id === FM.state.sheetId; })[0] || FM.SHEETS[0];
    var proj = FM.PROJECTS.filter(function (p) { return p.id === sheet.project; })[0];
    var prof = FM.getProfile(proj ? proj.profile : "firm-standard");

    /* working copy of the inputs so edits don't mutate the stored sheet until changed */
    var inp = {};
    Object.keys(sheet.inputs).forEach(function (k) { inp[k] = sheet.inputs[k]; });
    inp.deflLive = prof.deflLive;
    inp.deflTotal = prof.deflTotal;
    if (inp.CF === undefined) inp.CF = 1.0;

    document.title = "Firmark · " + sheet.id + " — " + sheet.label;

    var wrap = el("div", { class: "sheet" });
    var headHost = el("div", { class: "sheet-headhost" });
    var inputPane = el("div", { class: "input-pane" });
    var resultPane = el("div", { class: "result-pane" });

    host.appendChild(headHost);
    wrap.appendChild(inputPane);
    wrap.appendChild(resultPane);
    host.appendChild(wrap);

    /* ---------- header strip ---------- */

    function drawHead(r) {
      headHost.innerHTML = "";
      var strip = el("div", { class: "sheet-head" });
      var failed = !r.error && isFinite(r.governing.dcr) && r.governing.dcr > 1;

      var top = el("div", { class: "sheet-head-top" }, [
        el("h1", { class: "sheet-mark", text: sheet.id }),
        el("span", { class: "badge b-mute", text: sheet.role }),
        el("span", { style: "font-size:.83rem;color:var(--muted)", text: sheet.label })
      ]);

      var tools = el("div", { class: "sheet-tools" }, [
        el("div", { class: "seg", role: "group", "aria-label": "View density" }, [
          el("button", {
            "aria-pressed": FM.state.density === "quick" ? "true" : "false", text: "Quick",
            "data-refocus": "quick",
            onclick: function () { FM.state.density = "quick"; apply("quick"); }
          }),
          el("button", {
            "aria-pressed": FM.state.density === "detailed" ? "true" : "false", text: "Detailed",
            "data-refocus": "detailed",
            onclick: function () { FM.state.density = "detailed"; apply("detailed"); }
          })
        ]),
        el("button", {
          class: "btn btn-sm", "aria-pressed": FM.state.locked ? "true" : "false",
          text: FM.state.locked ? "Unlock" : "Lock", "data-refocus": "lock",
          onclick: function () { FM.state.locked = !FM.state.locked; apply("lock"); }
        })
      ]);
      top.appendChild(tools);
      strip.appendChild(top);

      if (r.error) {
        strip.appendChild(el("div", { class: "banner banner-warn", style: "margin:0" }, [
          el("strong", { text: "Not evaluated — " }), el("span", { text: r.message })
        ]));
        headHost.appendChild(strip);
        return;
      }

      /* per-check utilization chips, straight from the engine result */
      var chips = el("div", { class: "sheet-utils" });
      r.checks.forEach(function (c) {
        var isGov = c.name === r.governing.name;
        if (!isFinite(c.dcr)) return;
        chips.appendChild(el("span", {
          class: "util " + utilClass(c.dcr) + (isGov ? " is-gov" : ""),
          title: c.name + " · DCR " + fmt(c.dcr, 3) + " · " + c.combo
        }, [
          el("span", { class: "util-k", text: SHORT[c.name] || c.name }),
          el("span", { class: "util-v", text: pct(c.dcr) })
        ]));
      });

      var verb = !failed ? "Governing · "
        : (r.governing.kind === "service" ? "Exceeds deflection limit · " : "Overstressed · ");
      var pill = el("span", { class: "gov-pill" + (failed ? " is-fail" : "") }, [
        el("span", { text: verb }),
        el("span", { text: r.governing.name }),
        el("span", { text: " " + fmt(r.governing.dcr, 2) }),
        el("span", { class: "sr-only", text: failed ? " — exceeds the limit" : " — within the limit" })
      ]);

      var row = el("div", { style: "display:flex;flex-wrap:wrap;gap:8px;align-items:center" }, [chips, el("span", { style: "margin-left:auto" }, [pill])]);
      strip.appendChild(row);

      strip.appendChild(el("div", { class: "lock-note" }, [
        el("span", { text: "Locked for presentation — inputs are read-only. Lock is a view state, not an approval." })
      ]));

      headHost.appendChild(strip);
    }

    /* ---------- inputs ---------- */

    function field(label, node, hint) {
      var f = el("div", { class: "field" }, [el("label", { text: label }), node]);
      if (hint) f.appendChild(el("span", { class: "field-hint", text: hint }));
      return f;
    }

    function numInput(key, step, min) {
      var n = el("input", { type: "number", value: String(inp[key]), step: step || "0.5", min: min === undefined ? "0" : min });
      n.addEventListener("input", function () {
        var val = parseFloat(this.value);
        inp[key] = isNaN(val) ? 0 : val;
        recompute();
      });
      return n;
    }

    var substituted = null;

    function drawInputs() {
      inputPane.innerHTML = "";

      /* member */
      var speciesSel = el("select", {}, FM.engine.speciesList().map(function (s) {
        return el("option", { value: s.species, text: s.species, selected: s.species === inp.species ? "selected" : null });
      }));
      var gradeSel = el("select");
      function fillGrades() {
        gradeSel.innerHTML = "";
        var entry = FM.engine.speciesList().filter(function (s) { return s.species === inp.species; })[0];
        var glist = (entry ? entry.grades.slice() : []);
        glist.sort(function (a, b) { return FM.gradeRank(a) - FM.gradeRank(b); });
        glist.forEach(function (g) {
          gradeSel.appendChild(el("option", { value: g, text: g, selected: g === inp.grade ? "selected" : null }));
        });
      }
      fillGrades();
      speciesSel.addEventListener("change", function () {
        inp.species = this.value;
        var entry = FM.engine.speciesList().filter(function (s) { return s.species === inp.species; })[0];
        substituted = null;
        if (entry && entry.grades.indexOf(inp.grade) === -1) {
          /* Substitute the STRONGEST grade the new species offers, not the first
             one alphabetically. Table 4B's grades sort with "Construction" first,
             which is tabulated at 4" wide only — so the alphabetical pick errored
             out every sheet that wasn't a 2x4. */
          var best = entry.grades.slice().sort(function (a, b) {
            return FM.gradeRank(a) - FM.gradeRank(b);
          })[0];
          substituted = { from: inp.grade, to: best };
          inp.grade = best;
        }
        fillGrades();
        recompute();
      });
      gradeSel.addEventListener("change", function () { inp.grade = this.value; substituted = null; recompute(); });

      var sizeSel = el("select", {}, FM.engine.sizeList().map(function (s) {
        return el("option", { value: s, text: s, selected: s === inp.size ? "selected" : null });
      }));
      sizeSel.addEventListener("change", function () { inp.size = this.value; recompute(); });

      inputPane.appendChild(card("Member", null, el("div", { style: "display:grid;gap:10px" }, [
        field("Species", speciesSel),
        field("Grade", gradeSel),
        field("Size (S4S)", sizeSel)
      ]), null));

      /* geometry */
      inputPane.appendChild(card("Geometry", null, el("div", { style: "display:grid;gap:10px" }, [
        el("div", { class: "field-row" }, [
          field("Span (ft)", numInput("span", "0.5")),
          field("Spacing (in o.c.)", numInput("spacing", "1"))
        ]),
        field("Bearing length (in)", numInput("bearing", "0.25"))
      ]), null));

      /* loads — floor live and roof load are separate so that
         D + 0.75L + 0.75(Lr or S) can actually be formed */
      var roofTypeSel = el("select", {}, [
        { v: "snow", t: "Snow (S) · C_D 1.15" },
        { v: "roof_live", t: "Roof live (Lr) · C_D 1.25" }
      ].map(function (o) {
        return el("option", { value: o.v, text: o.t, selected: o.v === inp.roofType ? "selected" : null });
      }));
      roofTypeSel.addEventListener("change", function () { inp.roofType = this.value; recompute(); });

      var useSel = el("select", {}, [
        { v: "floor", t: "Floor · L/360, L/240" },
        { v: "roof_nonplaster", t: "Roof, non-plaster ceiling · L/240, L/180" },
        { v: "roof_no_ceiling", t: "Roof, no ceiling · L/180, L/180" },
        { v: "roof_plaster", t: "Roof, plaster ceiling · L/360, L/240" }
      ].map(function (o) {
        return el("option", { value: o.v, text: o.t, selected: o.v === inp.memberUse ? "selected" : null });
      }));
      useSel.addEventListener("change", function () { inp.memberUse = this.value; recompute(); });

      inputPane.appendChild(card("Loads", null, el("div", { style: "display:grid;gap:10px" }, [
        el("div", { class: "field-row" }, [
          field("Dead (psf)", numInput("dead", "1")),
          field("Floor live L (psf)", numInput("live", "1"))
        ]),
        field("Roof load Lr or S (psf)", numInput("roofLoad", "1")),
        field("Roof load type", roofTypeSel),
        field("Deflection limits", useSel)
      ]), null));

      /* conditions */
      function check(label, key, hint) {
        var c = el("input", { type: "checkbox" });
        c.checked = !!inp[key];
        c.addEventListener("change", function () { inp[key] = this.checked; recompute(); });
        var lab = el("label", {
          style: "display:flex;gap:8px;align-items:center;text-transform:none;letter-spacing:0;font-family:var(--sans);font-size:.85rem;color:var(--text);font-weight:500"
        }, [c, el("span", { text: label })]);
        var w = el("div", {}, [lab]);
        if (hint) w.appendChild(el("span", { class: "field-hint", style: "margin-left:24px", text: hint }));
        return w;
      }

      var cfInput = el("input", { type: "number", value: String(inp.CF), step: "0.05", min: "0.5", max: "2" });
      cfInput.addEventListener("input", function () {
        var val = parseFloat(this.value);
        inp.CF = isNaN(val) ? 1 : val;
        recompute();
      });

      inputPane.appendChild(card("Conditions", null, el("div", { style: "display:grid;gap:11px" }, [
        check("Repetitive member (C_r = 1.15)", "repetitive", "3+ members, ≤24″ o.c., load-distributing element · NDS §4.3.9"),
        check("Compression edge continuously braced", "braced", "Unchecked computes C_L from R_B per §3.3.3"),
        check("Wet service (MC > 19%)", "wet", "Applies the Table 4A C_M multipliers"),
        el("div", { class: "field" }, [
          el("label", {}, [
            el("span", { text: "C_F size factor" }),
            el("span", { class: "badge b-warn", style: "margin-left:6px", text: "Typed" })
          ]),
          cfInput,
          el("span", { class: "field-hint", text: "Not carried in the material catalog — enter per NDS Supplement Table 4A." })
        ])
      ]), null));
    }

    /* ---------- results ---------- */

    function drawResults(r) {
      resultPane.innerHTML = "";

      if (r.error) {
        /* the header strip already carries this banner — don't say it twice */
        return;
      }

      if (substituted) {
        resultPane.appendChild(el("div", { class: "banner banner-gold" }, [
          el("strong", { text: "Note — " }),
          el("span", { text: "\u201C" + substituted.from + "\u201D is not tabulated for " + inp.species +
                             "; grade changed to \u201C" + substituted.to + "\u201D." })
        ]));
      }

      if (r.warnings && r.warnings.length) {
        r.warnings.forEach(function (w) {
          resultPane.appendChild(el("div", { class: "banner banner-gold" }, [
            el("strong", { text: "Note — " }), el("span", { text: w })
          ]));
        });
      }

      /* governing summary */
      var gov = r.checks.filter(function (c) { return c.name === r.governing.name; })[0];
      var meter = el("div", { class: "meter" }, [
        el("div", { class: "meter-bar" }, [
          el("span", {
            class: "meter-fill " + (r.governing.dcr > 1 ? "fail" : (r.governing.dcr > 0.9 ? "warn" : "")),
            style: "display:block;width:" + Math.min(100, r.governing.dcr * 100) + "%"
          })
        ]),
        el("div", { class: "meter-legend" }, [
          el("span", { text: "0.0" }),
          el("span", { text: "governing DCR " + fmt(r.governing.dcr, 3) + " · " + r.governing.name }),
          el("span", { text: "1.0" })
        ])
      ]);

      var summary = el("div", { style: "display:grid;gap:12px" }, [
        meter,
        dl([
          { k: "Member", v: FM.esc(inp.size + " " + inp.species + " " + inp.grade) },
          { k: "Span · spacing", v: fmt(inp.span, 1) + " ft · " + inp.spacing + "″ o.c." },
          { k: "Section", v: "A " + fmt(r.section.A_in2, 2) + " in² · S<sub>x</sub> " + fmt(r.section.Sx_in3, 2) + " in³ · I<sub>x</sub> " + fmt(r.section.Ix_in4, 1) + " in⁴" },
          { k: "Governing case", v: FM.esc(r.governing.name) + " · " + FM.esc(r.governing.combo), cls: "gold" },
          { k: "Strength governing", v: FM.esc(r.strength.name) + " · " + fmt(r.strength.dcr, 3), cls: r.strength.dcr > 1 ? "fail" : "" },
          { k: "Serviceability governing", v: FM.esc(r.service.name) + " · " + fmt(r.service.dcr, 3), cls: r.service.dcr > 1 ? "fail" : "" },
          { k: "Verdict", v: r.governing.dcr > 1 ? (r.governing.kind === "service" ? "Exceeds deflection limit" : "Overstressed") : "Within limits", cls: r.governing.dcr > 1 ? "fail" : "pass" }
        ])
      ]);

      resultPane.appendChild(card("Result", el("span", {
        class: "badge " + (r.governing.dcr > 1 ? "b-fail" : "b-pass"),
        style: "margin-left:auto",
        text: r.governing.dcr > 1 ? "NG" : "OK"
      }), summary, r.basis));

      /* per-check detail */
      r.checks.forEach(function (c) {
        if (!isFinite(c.dcr)) return;
        var body = el("div", { style: "display:grid;gap:10px" });

        body.appendChild(el("div", { class: "eq", html: c.lines.map(function (l) { return FM.esc(l); }).join("<br>") }));

        if (c.detail && c.detail.factors) {
          var led = el("div", { class: "dl ledger detail-only" });
          c.detail.factors.forEach(function (f) {
            var kNode = el("span", { class: "dl-k" }, [
              el("span", { html: FM.esc(f.k) }),
              f.cite ? el("span", { class: "clause", text: f.cite }) : null,
              f.src ? el("span", { class: "badge b-blue", style: "margin-left:6px", text: "DB" }) : null,
              f.typed ? el("span", { class: "badge b-warn", style: "margin-left:6px", text: "Typed" }) : null
            ]);
            led.appendChild(el("div", { class: "dl-row" + (f.total ? " total" : "") }, [
              kNode,
              el("span", { class: "dl-v" + (f.total ? " gold" : ""), html: FM.esc(f.v) })
            ]));
          });
          body.appendChild(led);
        }

        var acc = el("details", { class: "acc" }, [
          el("summary", {}, [
            el("span", { text: c.name }),
            el("span", { class: "util " + utilClass(c.dcr), style: "margin-left:8px" }, [
              el("span", { class: "util-v", text: fmt(c.dcr, 3) })
            ]),
            el("span", { style: "font-family:var(--mono);font-size:.7rem;color:var(--muted);margin-left:8px", text: c.combo })
          ]),
          el("div", { class: "acc-body" }, [body])
        ]);
        if (c.name === r.governing.name) acc.open = true;
        resultPane.appendChild(acc);
      });

      /* load combinations actually enveloped */
      var comboRows = r.combos.map(function (c) {
        return { k: FM.esc(c.label) + " <span class='clause'>" + FM.esc(c.cdLabel) + "</span>", v: "C_D " + fmt(c.cd, 2) + " · " + fmt(c.psf, 0) + " psf" };
      });
      resultPane.appendChild(card("Load combinations enveloped", null, dl(comboRows),
        "ASCE 7 §2.4 · C_D corresponds to the shortest-duration load in each combination"));

      /* scope limits — printed on every sheet */
      var lim = el("ul", { style: "display:grid;gap:5px" });
      FM.engine.LIMITS.forEach(function (l) {
        lim.appendChild(el("li", { style: "font-size:.8rem;color:var(--muted);padding-left:14px;position:relative" }, [
          el("span", { style: "position:absolute;left:0", text: "·" }),
          el("span", { text: l })
        ]));
      });
      resultPane.appendChild(card("Excluded from this check", el("span", { class: "badge b-warn", text: "Scope", style: "margin-left:auto" }),
        lim, "Every sheet prints its exact edition, applicability conditions, and excluded checks"));

      /* provenance */
      var m = (window.MATDATA && MATDATA.meta) || {};
      resultPane.appendChild(card("Provenance", null, el("div", { class: "src-note" }, [
        el("p", { text: "Reference design values: " + ((m.species_grades && m.species_grades.source_file) || "—") +
                        " · revision " + ((m.species_grades && m.species_grades.dataset_version) || "—") }),
        el("p", { text: "Section properties: " + ((m.sections && m.sections.source_file) || "—") +
                        " · revision " + ((m.sections && m.sections.dataset_version) || "—") }),
        el("p", { style: "margin-top:6px", text: "A licensed PE reviews and stamps; the software never does." })
      ]), null));
    }

    /* ---------- wiring ---------- */

    function apply(refocus) {
      host.classList.toggle("quick", FM.state.density === "quick");
      host.classList.toggle("locked", FM.state.locked);
      /* enforcement, not just styling: inert takes the pane out of the tab order
         and blocks all input, so the "read-only" claim on screen is true. */
      inputPane.toggleAttribute("inert", !!FM.state.locked);
      inputPane.setAttribute("aria-disabled", FM.state.locked ? "true" : "false");
      recompute();
    }

    function recompute() {
      var r = FM.engine.run(inp);
      drawHead(r);
      drawResults(r);
    }

    drawInputs();
    apply();
  };
})();

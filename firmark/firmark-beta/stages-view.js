/* ============================================================
   stages-view.js — the screens for takeoff, loads-and-code, and the
   materials list.

   Those three modules are deliberately DOM-free so their logic can be
   tested headlessly, which means their screens live here. `cad.js` and
   `planset.js` carry their own views because their output IS a
   drawing.

   A shape repeats on all three, and it is the point of the product:
   what the stage PRODUCED goes on the left of the eye, and what it
   COULD NOT RESOLVE goes above it, not below. A reviewer approving a
   stage should have to scroll past the problems to reach the results,
   never the other way round.
   ============================================================ */

(function () {
  "use strict";

  var el = FM.el, card = FM.card, dl = FM.dl, esc = FM.esc, fmt = FM.fmt, comma = FM.comma;

  function missing(host, title, sub, what) {
    host.appendChild(FM.pageHead(title, sub));
    host.appendChild(FM.stageRail ? FM.stageRail(null) : el("div"));
    host.appendChild(el("div", { class: "empty" }, [
      el("strong", { text: what }),
      el("div", { class: "clause", style: "margin-top:6px",
                  text: "This is a missing module, not an empty result. The build says which parts are absent." })
    ]));
  }

  function n2(v, d) {
    return (v === null || v === undefined || !isFinite(v)) ? "—" : Number(v).toFixed(d === undefined ? 2 : d);
  }

  /* A block of things a stage could not answer. Never collapsed, never
     truncated silently, and it says zero rather than disappearing — an
     absent list and an empty list read identically and mean opposite things. */
  function openItems(title, rows, emptyText) {
    var body = el("div", { style: "display:grid;gap:7px" });
    if (!rows.length) {
      body.appendChild(el("p", { class: "clause", text: emptyText }));
    } else {
      rows.forEach(function (r) {
        body.appendChild(el("div", { style: "border-left:3px solid var(--warn);padding-left:10px" }, [
          el("div", { style: "font-size:.85rem;font-weight:650", text: r.what }),
          r.why ? el("div", { class: "clause", text: r.why }) : null,
          r.need ? el("div", { style: "font-size:.8rem;margin-top:2px", text: "Needs: " + r.need }) : null
        ].filter(Boolean)));
      });
    }
    return card(title + " — " + rows.length,
      el("span", { class: "badge " + (rows.length ? "b-gold" : "b-pass"), style: "margin-left:auto",
                   text: rows.length ? "Blocking" : "None" }),
      body,
      "A stage is not approvable while anything here is unanswered.");
  }

  /* ============================================================
     2 · TAKEOFF
     ============================================================ */

  FM.VIEWS.takeoff = function (host) {
    if (!FM.takeoff || !FM.project) {
      return missing(host, "Takeoff", "Spans, tributaries and bearing, derived from the geometry.",
                     "takeoff.js is not in this build.");
    }

    host.appendChild(FM.pageHead("2 · Takeoff",
      "Every span, tributary width and bearing condition, and where each one came from.",
      [el("button", { class: "btn", text: "Back to the run", onclick: function () { FM.go("pipeline"); } })]));
    host.appendChild(FM.stageRail("takeoff"));

    var t = FM.project.takeoff();
    if (!t) {
      host.appendChild(el("div", { class: "empty" }, [
        el("strong", { text: "No geometry to take off." }),
        el("div", { class: "clause", style: "margin-top:6px",
                    text: "Draw a plan, or start a run from a master set, on the Geometry stage." }),
        el("div", { style: "margin-top:12px" }, [
          el("button", { class: "btn btn-primary", text: "Go to Geometry", onclick: function () { FM.go("cad"); } })
        ])
      ]));
      return;
    }
    if (t.error) {
      host.appendChild(el("div", { class: "banner banner-warn" }, [
        el("strong", { text: "The takeoff threw — " }), el("span", { text: t.message })
      ]));
      return;
    }

    var unresolved = t.unresolved || [];

    host.appendChild(el("div", { class: "grid g4", style: "margin-bottom:16px" }, [
      FM.statCard(String((t.marks || []).length), "Marks derived"),
      FM.statCard(String(unresolved.length), "Unresolved", unresolved.length ? "gold" : "pass"),
      FM.statCard(String((t.derivations || []).length), "Traced values"),
      FM.statCard(String((t.warnings || []).length), "Warnings")
    ]));

    /* the problems, first */
    host.appendChild(el("div", { style: "margin-bottom:16px" }, [
      openItems("Unresolved", unresolved.map(function (u) {
        return { what: u.what, why: u.why, need: u.need };
      }), "The geometry determined every value. Nothing was assumed.")
    ]));

    if ((t.warnings || []).length) {
      var wl = el("div", { style: "display:grid;gap:6px" });
      t.warnings.forEach(function (w) {
        wl.appendChild(el("p", { style: "font-size:.83rem", text: typeof w === "string" ? w : (w.text || JSON.stringify(w)) }));
      });
      host.appendChild(el("div", { style: "margin-bottom:16px" }, [
        card("Warnings — " + t.warnings.length,
          el("span", { class: "badge b-gold", text: "Not blocking", style: "margin-left:auto" }), wl,
          "Worth reading before approving; they do not stop the gate.")
      ]));
    }

    /* the marks */
    var tb = el("tbody");
    (t.marks || []).forEach(function (m) {
      tb.appendChild(el("tr", {}, [
        el("td", { class: "k", text: m.id }),
        el("td", { text: m.label || "" }),
        el("td", { text: m.role || "—" }),
        el("td", { class: "n", text: n2(m.span, 2) }),
        el("td", { class: "n", text: m.trib === undefined ? "—" : n2(m.trib, 2) }),
        el("td", { class: "n", text: m.bearing === undefined ? "—" : n2(m.bearing, 2) }),
        el("td", { class: "n", text: m.count === undefined ? "—" : String(m.count) }),
        el("td", { text: m.carries || "—" })
      ]));
    });
    host.appendChild(el("div", { style: "margin-bottom:16px" }, [
      card("Marks — " + (t.marks || []).length,
        el("span", { class: "badge b-blue", text: "Derived", style: "margin-left:auto" }),
        el("div", { class: "tw", tabindex: "0", role: "region", "aria-label": "Derived marks" }, [
          el("table", {}, [
            el("thead", {}, [el("tr", {}, [
              el("th", { text: "Mark" }), el("th", { text: "Label" }), el("th", { text: "Role" }),
              el("th", { class: "n", text: "Span ft" }), el("th", { class: "n", text: "Trib ft" }),
              el("th", { class: "n", text: "Bearing in" }), el("th", { class: "n", text: "Count" }),
              el("th", { text: "Carries" })
            ])]), tb
          ])
        ]),
        "These become the demands the calculation stage checks.")
    ]));

    /* the derivations — the reason this stage is reviewable at all */
    var byMark = {};
    (t.derivations || []).forEach(function (d) {
      var k = d.markId || "(plan)";
      if (!byMark[k]) byMark[k] = [];
      byMark[k].push(d);
    });
    var dBody = el("div", { style: "display:grid;gap:8px" });
    var keys = [];
    for (var k in byMark) if (Object.prototype.hasOwnProperty.call(byMark, k)) keys.push(k);
    keys.sort();
    if (!keys.length) {
      dBody.appendChild(el("p", { class: "clause",
        text: "No derivations were recorded. That is a defect — every number in the table above should have one." }));
    }
    keys.forEach(function (id) {
      var rows = byMark[id].map(function (d) {
        return {
          k: esc(d.field),
          v: esc(String(d.value)) + " <span class='clause'>" + esc(d.how || "") +
             (d.from ? " · from " + esc(String(d.from)) : "") + "</span>"
        };
      });
      dBody.appendChild(el("details", { class: "acc" }, [
        el("summary", {}, [
          el("span", { class: "badge b-mute", text: id }),
          el("span", { class: "clause", text: byMark[id].length + " values traced" })
        ]),
        el("div", { class: "acc-body" }, [dl(rows)])
      ]));
    });

    host.appendChild(card("Where every number came from",
      el("span", { class: "badge b-blue", text: "Reviewable", style: "margin-left:auto" }),
      dBody,
      "A takeoff you cannot reconstruct is a takeoff you cannot approve. Open a mark to see the arithmetic."));
  };

  /* ============================================================
     3 · LOADS AND CODE
     ============================================================ */

  FM.VIEWS.jurisdiction = function (host) {
    if (!FM.juris || !FM.project) {
      return missing(host, "Loads and code", "Where this house is being built, and what that requires.",
                     "jurisdiction.js is not in this build.");
    }

    host.appendChild(FM.pageHead("3 · Loads and code",
      "The adopted code, the site hazard parameters, and what still has to be confirmed.",
      [el("button", { class: "btn", text: "Back to the run", onclick: function () { FM.go("pipeline"); } })]));
    host.appendChild(FM.stageRail("jurisdiction"));

    var s = FM.project.state();

    /* the picker */
    var stateSel = el("select", { "aria-label": "State" });
    stateSel.appendChild(el("option", { value: "", text: "Choose a state…" }));
    FM.juris.STATES.forEach(function (st) {
      var o = el("option", { value: st, text: st });
      stateSel.appendChild(o);
    });

    var jurisSel = el("select", { "aria-label": "Jurisdiction" });

    function currentState() {
      if (!s.jurisId) return stateSel.value || "";
      var j = FM.juris.jurisdictionById ? FM.juris.jurisdictionById(s.jurisId) : null;
      return j ? j.state : (stateSel.value || "");
    }

    function fillJuris() {
      jurisSel.innerHTML = "";
      var st = currentState();
      jurisSel.appendChild(el("option", { value: "", text: st ? "Choose a jurisdiction…" : "Choose a state first" }));
      if (!st) return;
      (FM.juris.jurisdictions(st) || []).forEach(function (j) {
        jurisSel.appendChild(el("option", { value: j.id, text: j.name + (j.county ? " · " + j.county : "") }));
      });
      if (s.jurisId) jurisSel.value = s.jurisId;
    }

    stateSel.value = currentState();
    fillJuris();

    stateSel.addEventListener("change", function () {
      FM.project.set({ jurisId: null, packId: null });
      fillJuris();
      FM.go("jurisdiction");
    });
    jurisSel.addEventListener("change", function () {
      FM.project.set({ jurisId: this.value || null, packId: null });
      FM.go("jurisdiction");
    });

    host.appendChild(el("div", { class: "filter-bar", style: "margin-bottom:16px" }, [stateSel, jurisSel]));

    var site = FM.project.site();
    if (!site) {
      host.appendChild(el("div", { class: "empty" }, [
        el("strong", { text: "No jurisdiction chosen." }),
        el("div", { class: "clause", style: "margin-top:6px",
          text: "The code edition, the design wind speed and the ground snow all depend on where this is being built. " +
                "There is no sensible default — a default here is a wrong answer somewhere." })
      ]));
      return;
    }

    /* the code basis */
    var codeRows = (site.codes || []).map(function (c) {
      return {
        k: esc(c.name),
        v: esc(c.edition || "—") +
           " <span class='badge " + clsBadge(c.cls) + "' style='margin-left:6px'>" + esc(String(c.cls || "?")) + "</span>" +
           "<span class='clause'>" + esc(c.cite || "") + (c.adopted ? " · adopted " + esc(c.adopted) : "") + "</span>"
      };
    });
    host.appendChild(el("div", { style: "margin-bottom:16px" }, [
      card("Governing code", null, dl(codeRows.length ? codeRows : [{ k: "—", v: "none recorded" }]),
        site.authority ? "Authority having jurisdiction: " + site.authority : null)
    ]));

    /* the design criteria */
    function crit(label, v, unit) {
      if (!v) return null;
      return {
        k: label,
        v: esc(String(v.v !== undefined ? v.v : v.vMph !== undefined ? v.vMph : v.pgPsf !== undefined ? v.pgPsf : v.sdc)) +
           (unit ? " " + unit : "") +
           " <span class='badge " + clsBadge(v.cls) + "' style='margin-left:6px'>" + esc(String(v.cls || "?")) + "</span>" +
           "<span class='clause'>" + esc(v.cite || "") + (v.note ? " · " + esc(v.note) : "") + "</span>"
      };
    }
    var critRows = [
      crit("Design wind speed", site.wind, "mph"),
      site.wind && site.wind.exposure ? { k: "Exposure", v: esc(site.wind.exposure) } : null,
      crit("Ground snow", site.snow, "psf"),
      crit("Seismic", site.seismic, ""),
      site.frostDepthIn ? { k: "Frost depth", v: esc(String(site.frostDepthIn)) + " in" } : null,
      site.termite ? { k: "Termite", v: esc(String(site.termite)) } : null,
      site.windborneDebris !== undefined
        ? { k: "Wind-borne debris region", v: site.windborneDebris ? "Yes — opening protection required" : "No" }
        : null,
      site.hvhz !== undefined
        ? { k: "HVHZ", v: site.hvhz ? "Yes — High-Velocity Hurricane Zone" : "No" }
        : null
    ].filter(Boolean);

    host.appendChild(el("div", { style: "margin-bottom:16px" }, [
      card("Design criteria", null, dl(critRows),
        "Every value carries its provenance class. A [site] value is a planning default until it is confirmed.")
    ]));

    /* the pack this maps to, and how well */
    var pk = FM.project.pack();
    var fit = FM.juris.packFor ? FM.juris.packFor(s.jurisId) : null;
    if (pk) {
      var fitBody = el("div", { style: "display:grid;gap:8px" }, [
        el("p", { style: "font-size:.85rem",
          text: "Loads for this run come from the “" + pk.name + "” region pack." })
      ]);
      if (fit && fit.differences && fit.differences.length) {
        fit.differences.forEach(function (d) {
          fitBody.appendChild(el("div", { style: "border-left:3px solid var(--gold);padding-left:10px" }, [
            el("div", { style: "font-size:.84rem;font-weight:650", text: d.what }),
            el("div", { class: "clause", text: d.detail || "" })
          ]));
        });
      } else {
        fitBody.appendChild(el("p", { class: "clause",
          text: "No differences were reported between this jurisdiction and the pack." }));
      }
      host.appendChild(el("div", { style: "margin-bottom:16px" }, [
        card("Load basis",
          el("span", { class: "badge " + (fit && fit.differences && fit.differences.length ? "b-gold" : "b-blue"),
                       text: pk.id, style: "margin-left:auto" }),
          fitBody,
          "A region pack is an approximation of a site. Where it differs, the difference is printed rather than absorbed.")
      ]));
    }

    /* what must be verified — the honest half */
    host.appendChild(el("div", { style: "margin-bottom:16px" }, [
      openItems("Must be verified before this is sealed",
        (site.mustVerify || []).map(function (v) {
          return typeof v === "string" ? { what: v } : { what: v.what, why: v.why, need: v.need || v.against };
        }),
        "Nothing listed — which should not happen. Wind speed and snow are site-specific and this list should never be empty.")
    ]));

    if ((site.amendments || []).length) {
      var ab = el("div", { style: "display:grid;gap:7px" });
      site.amendments.forEach(function (a) {
        ab.appendChild(el("div", {}, [
          el("div", { style: "font-size:.84rem", text: a.text }),
          el("div", { class: "clause", text: a.cite || "" })
        ]));
      });
      host.appendChild(el("div", { style: "margin-bottom:16px" }, [
        card("Local amendments — " + site.amendments.length, null, ab,
          "State or local changes to the model code that affect structural design.")
      ]));
    }

    if ((site.checklist || (FM.juris.checklist && FM.juris.checklist(s.jurisId)) || []).length) {
      var list = site.checklist || FM.juris.checklist(s.jurisId);
      var cb = el("div", { style: "display:grid;gap:6px" });
      list.forEach(function (c) {
        cb.appendChild(el("p", { style: "font-size:.84rem", text: "· " + (typeof c === "string" ? c : c.text) }));
      });
      host.appendChild(card("Submittal checklist", null, cb,
        "What this jurisdiction expects to receive. This system produces some of it, not all of it."));
    }
  };

  function clsBadge(cls) {
    return cls === "code" ? "b-blue" : cls === "site" ? "b-gold" : cls === "derived" ? "b-pass" : "b-mute";
  }

  /* ============================================================
     5 · MATERIALS LIST
     ============================================================ */

  FM.VIEWS.bom = function (host) {
    if (!FM.bom || !FM.project) {
      return missing(host, "Materials list", "What to buy, and what is not in it.",
                     "bom.js is not in this build.");
    }

    host.appendChild(FM.pageHead("5 · Materials list",
      "Quantities derived from the schedule — and, in full, what is not in them.",
      [
        el("button", { class: "btn", text: "Back to the run", onclick: function () { FM.go("pipeline"); } }),
        el("button", {
          class: "btn btn-primary", text: "Export list (.txt)",
          onclick: function () {
            var b = FM.project.bom();
            if (!b || !FM.bom.text) { FM.toast("Nothing to export yet."); return; }
            FM.download ? FM.download(FM.bom.text(b), "firmark-materials.txt")
                        : FM.toast("Export is unavailable in this build.");
          }
        })
      ]));
    host.appendChild(FM.stageRail("bom"));

    var b = FM.project.bom();
    if (!b) {
      host.appendChild(el("div", { class: "empty" }, [
        el("strong", { text: "Nothing calculated yet." }),
        el("div", { class: "clause", style: "margin-top:6px",
                    text: "A materials list is derived from the selected members. Run the calculation stage first." }),
        el("div", { style: "margin-top:12px" }, [
          el("button", { class: "btn btn-primary", text: "Go to Calculations", onclick: function () { FM.go("sizing"); } })
        ])
      ]));
      return;
    }
    if (b.error) {
      host.appendChild(el("div", { class: "banner banner-warn" }, [
        el("strong", { text: "The materials list threw — " }), el("span", { text: b.message })
      ]));
      return;
    }

    var tot = b.totals || {};
    host.appendChild(el("div", { class: "grid g4", style: "margin-bottom:16px" }, [
      FM.statCard(comma(tot.pieces || 0), "Pieces"),
      FM.statCard(comma(Math.round(tot.bf || 0)), "Board feet"),
      FM.statCard(tot.usd ? "$" + comma(Math.round(tot.usd)) : "—", "Estimated, market"),
      FM.statCard(String((b.excluded || []).length), "Excluded items", (b.excluded || []).length ? "gold" : "")
    ]));

    host.appendChild(el("div", { class: "banner banner-gold", style: "margin-bottom:16px" }, [
      el("strong", { text: "Money here is a placeholder. " }),
      el("span", { text: "Quantities are derived from the schedule and are the useful part. Prices are firm " +
                         "placeholders with no code standing and no supplier behind them." })
    ]));

    /* what is NOT in it — before the list, deliberately */
    host.appendChild(el("div", { style: "margin-bottom:16px" }, [
      openItems("Not in this list",
        (b.excluded || []).map(function (x) {
          return { what: x.what, why: x.why, need: x.need };
        }),
        "Nothing excluded — which cannot be right. Connectors, sheathing and fasteners are never sized here.")
    ]));

    var tb = el("tbody");
    (b.lines || []).forEach(function (L) {
      tb.appendChild(el("tr", {}, [
        el("td", { class: "k", text: L.sku || "" }),
        el("td", { text: (L.marks || []).join(", ") }),
        el("td", { class: "n", text: L.piecesPerHouse === undefined ? "—" : comma(L.piecesPerHouse) }),
        el("td", { class: "n", text: L.stockLengthFt ? n2(L.stockLengthFt, 0) + " ft" : "—" }),
        el("td", { class: "n", text: L.bf === undefined ? "—" : comma(Math.round(L.bf)) }),
        el("td", { class: "n", text: L.extUSD === undefined ? "—" : "$" + comma(Math.round(L.extUSD)) })
      ]));
    });
    host.appendChild(el("div", { style: "margin-bottom:16px" }, [
      card("Per house — " + (b.lines || []).length + " lines",
        el("span", { class: "badge b-blue", text: "Derived", style: "margin-left:auto" }),
        el("div", { class: "tw", tabindex: "0", role: "region", "aria-label": "Materials list" }, [
          el("table", {}, [
            el("thead", {}, [el("tr", {}, [
              el("th", { text: "SKU" }), el("th", { text: "Marks" }),
              el("th", { class: "n", text: "Pieces" }), el("th", { class: "n", text: "Stock" }),
              el("th", { class: "n", text: "BF" }), el("th", { class: "n", text: "Ext" })
            ])]), tb
          ])
        ]),
        b.waste ? "Waste policy: " + b.waste.policy : null)
    ]));

    if (b.perCommunity) {
      host.appendChild(card("Across the community", null,
        dl([
          { k: "Lots", v: String(b.perCommunity.lots || "—") },
          { k: "Pieces", v: comma(b.perCommunity.pieces || 0) },
          { k: "Board feet", v: comma(Math.round(b.perCommunity.bf || 0)) },
          { k: "Estimated", v: b.perCommunity.usd ? "$" + comma(Math.round(b.perCommunity.usd)) : "—" }
        ]),
        b.perCommunity.basis || null));
    }
  };
})();

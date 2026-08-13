/* ============================================================
   Sizing — the solver's surface.

   Three questions this view has to answer, in order:
     1. What member did it pick, and by how much did it pass?
     2. What did it reject, and why — including what it never
        evaluated, and on what grounds.
     3. What changes when the same plan is built in another state?

   A recommendation with no visible runner-up is a black box, which
   is the thing this product exists not to be.
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

  /* every number in a pack says what kind of number it is */
  function classBadge(cls) {
    var m = {
      code:   { c: "b-blue", t: "Code" },
      site:   { c: "b-warn", t: "Site" },
      market: { c: "b-mute", t: "Market" }
    }[cls];
    if (!m) return null;
    return el("span", { class: "badge " + m.c, style: "margin-left:6px", text: m.t });
  }

  function spacingText(cand) {
    return cand.spacing ? cand.spacing + "″ o.c." : "single";
  }

  FM.VIEWS.sizing = function (host) {
    if (!FM.solver || !FM.weights) {
      host.appendChild(FM.pageHead("Sizing", "Solver"));
      host.appendChild(el("div", { class: "empty", text: "The sizing solver failed to load." }));
      return;
    }

    var state = FM.state.sizing || (FM.state.sizing = {
      packId: "nc-piedmont", planId: "sunbelt-ranch-1850", open: null, tab: "schedule"
    });

    host.appendChild(FM.pageHead("Sizing",
      "One plan, solved against a region. The engine decides what passes; the weights only rank what already did.", [
        el("button", { class: "btn", onclick: function () { FM.go("materials"); }, text: "Materials" })
      ]));

    host.appendChild(FM.betaStrip(
      "The solver proposes members and shows its work. Prices, availability and site loads in the region packs are " +
      "placeholders — replace them with your own before reading any dollar figure as real. Nothing here is stamped."));

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
    planSel.addEventListener("change", function () { state.planId = this.value; state.open = null; draw(); });
    Array.prototype.forEach.call(tabs.querySelectorAll("button"), function (b) {
      b.addEventListener("click", function () { state.tab = b.getAttribute("data-tab"); draw(); });
    });

    /* ---------- schedule ---------- */

    function drawSchedule(res, pack, plan) {
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
      if (!r.complete) {
        body.appendChild(el("div", { class: "banner banner-warn" }, [
          el("strong", { text: "Not a complete schedule — " }),
          el("span", { text: r.incompleteBecause + ". Do not read the solved marks as a finished design." })
        ]));
      }
      body.appendChild(el("div", { class: "grid g5", style: "margin-bottom:16px" }, [
        FM.statCard(String(r.solved) + "/" + plan.marks.length, "Marks solved", r.escalated ? "warn" : "pass"),
        FM.statCard(String(r.escalated), "Escalated", r.escalated ? "fail" : ""),
        FM.statCard(String(r.notApplicable), "Not this engine", "blue"),
        FM.statCard(String(r.skuCount), "Distinct SKUs"),
        FM.statCard(usd0(r.lumberUSD), "Modelled cost / house")
      ]));

      var tb = el("tbody");
      res.marks.forEach(function (m) {
        var row = m.unifiedTo || (m.solution && m.solution.pick);
        var cells;
        if (m.notApplicable) {
          cells = [
            el("td", { class: "k", text: m.mark.id }),
            el("td", { text: m.mark.label }),
            el("td", { colspan: "4" }, [
              el("span", { class: "badge " + (m.notApplicable.reason === "out-of-scope" || m.notApplicable.reason === "underdetermined" ? "b-warn" : "b-blue"),
                text: { component: "Manufactured component", "wall-system": "Not a wood member here",
                        "out-of-scope": "Out of this engine's scope",
                        underdetermined: "Not sized — tributary not derivable" }[m.notApplicable.reason] || "Not this engine" }),
              el("span", { class: "clause", text: m.notApplicable.note })
            ]),
            el("td", { class: "n", text: "—" })
          ];
        } else if (!row) {
          cells = [
            el("td", { class: "k", text: m.mark.id }),
            el("td", { text: m.mark.label }),
            el("td", { colspan: "4" }, [
              el("span", { class: "badge b-fail", text: "Escalate" }),
              el("span", { class: "clause", text: m.solution.note ? m.solution.note.wall + " — " + m.solution.note.move : "" })
            ]),
            el("td", { class: "n", text: "—" })
          ];
        } else {
          cells = [
            el("td", { class: "k", text: m.mark.id }),
            el("td", { text: m.mark.label }),
            el("td", {}, [
              el("span", { text: row.cand.size + " " + row.cand.species + " " + row.cand.grade }),
              m.unifiedTo ? el("span", { class: "badge b-blue", style: "margin-left:6px", text: "Unified" }) : null
            ]),
            el("td", { class: "n", text: spacingText(row.cand) }),
            el("td", {}, [el("span", { class: "util " + utilClass(row.dcr) }, [
              el("span", { class: "util-k", text: row.governing }),
              el("span", { class: "util-v", text: fmt(row.dcr, 3) })
            ])]),
            el("td", { class: "n", text: fmt(m.mark.span, 1) + " ft" }),
            el("td", { class: "n", text: usd(row.cost.totalUSD) })
          ];
        }
        var tr = FM.el("tr", {
          class: "clickable", tabindex: "0", role: "button",
          "aria-label": "Show search detail for " + m.mark.id,
          onclick: function () { state.open = state.open === m.mark.id ? null : m.mark.id; draw(); },
          onkeydown: function (e) {
            if (e.key === "Enter" || e.key === " ") { e.preventDefault(); state.open = state.open === m.mark.id ? null : m.mark.id; draw(); }
          }
        }, cells);
        tb.appendChild(tr);
      });

      body.appendChild(el("div", { class: "tw", tabindex: "0", role: "region", "aria-label": "Member schedule" }, [
        el("table", {}, [
          el("thead", {}, [el("tr", {}, [
            el("th", { text: "Mark" }), el("th", { text: "Member" }), el("th", { text: "Selected" }),
            el("th", { class: "n", text: "Spacing" }), el("th", { text: "Governs" }),
            el("th", { class: "n", text: "Span" }), el("th", { class: "n", text: "Cost" })
          ])]),
          tb
        ])
      ]));

      /* the open mark's full search record */
      var openMark = res.marks.filter(function (m) { return m.mark.id === state.open && !m.notApplicable; })[0];
      if (openMark) body.appendChild(drawSearch(openMark));

      /* SKU unification */
      if (res.unified && res.unified.length) {
        var uRows = res.unified.map(function (u) {
          return {
            k: esc(u.group) + " <span class='clause'>" + u.skusBefore + " SKUs → 1</span>",
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

    /* ---------- the search record for one mark ---------- */

    function drawSearch(m) {
      var sol = m.solution, b = sol.bounds, st = sol.stats;
      var wrap = el("div", { style: "margin-top:14px;display:grid;gap:12px" });

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
        { k: "Deflection row", v: esc(b.deflection.row) + " <span class='clause'>L/" + b.deflection.live + " variable, L/" + b.deflection.total + " total</span>" },
        { k: "Service", v: m.demand.wet ? "Wet · MC &gt; 19%" : "Dry" },
        { k: "Compression edge", v: m.demand.braced ? "Continuously braced — C_L = 1.0" : "Unbraced — C_L computed from R_B" },
        !m.demand.repetitive ? { k: "Self-weight added", v: "§1.3(b) · &gamma; = " + FM.solver.GAMMA_PCF + " pcf <span class='clause'>assumption</span>" } : null
      ].filter(Boolean)), null));

      /* the seed bounds and what they cost the search */
      wrap.appendChild(card("Search trace", el("span", { class: "badge b-blue", text: st.evaluated + " engine calls", style: "margin-left:auto" }),
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
            { k: "Search space", v: sol.searchSpace + " candidates in " + st.families + " families" },
            { k: "Cut by seed bounds", v: String(st.prunedByBound) + " <span class='clause'>H1 · admissible</span>" },
            { k: "Cut by cost dominance", v: String(st.prunedByDominance) + " <span class='clause'>H2 · deeper rung of a family already beaten</span>" },
            { k: "Cut by incumbent", v: String(st.prunedByIncumbent) + " <span class='clause'>H3 · branch and bound</span>" },
            { k: "Engine evaluations", v: String(st.evaluated) + (st.cacheHits ? " (+" + st.cacheHits + " cached)" : ""), total: true }
          ])
        ]), "Every cut is exact — no candidate was dropped on a guess"));

      /* the feasible ladder */
      if (sol.feasible.length) {
        var ftb = el("tbody");
        sol.feasible.slice(0, 8).forEach(function (f, i) {
          ftb.appendChild(el("tr", {}, [
            el("td", { class: "k" }, [
              el("span", { text: f.cand.size + " " + f.cand.species + " " + f.cand.grade }),
              i === 0 ? el("span", { class: "badge b-pass", style: "margin-left:6px", text: "Pick" }) : null
            ]),
            el("td", { class: "n", text: spacingText(f.cand) }),
            el("td", { class: "n", text: fmt(f.dcr, 3) }),
            el("td", { text: f.governing }),
            el("td", { class: "n", text: usd(f.cost.totalUSD) }),
            el("td", { class: "n", text: usd(f.score) })
          ]));
        });
        wrap.appendChild(card("Passed the check · ranked", null,
          el("div", { class: "tw", tabindex: "0", role: "region", "aria-label": "Feasible members" }, [
            el("table", {}, [
              el("thead", {}, [el("tr", {}, [
                el("th", { text: "Member" }), el("th", { class: "n", text: "Spacing" }), el("th", { class: "n", text: "DCR" }),
                el("th", { text: "Governs" }), el("th", { class: "n", text: "Cost" }), el("th", { class: "n", text: "Score" })
              ])]), ftb
            ])
          ]),
          "Score = cost + a small penalty for unused capacity. The engine decided the DCR column; the weights only ordered the rows."));
      }

      /* why the rest did not make it */
      if (sol.rejected.length) {
        var rtb = el("tbody");
        sol.rejected.slice(0, 10).forEach(function (rj) {
          rtb.appendChild(el("tr", {}, [
            el("td", { class: "k", text: rj.cand.size + " " + rj.cand.species + " " + rj.cand.grade }),
            el("td", { text: rj.reason }),
            el("td", { text: rj.next || "—" })
          ]));
        });
        wrap.appendChild(card("Rejected", el("span", { class: "badge b-warn", text: String(sol.rejected.length), style: "margin-left:auto" }),
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

      /* nothing worked */
      if (!sol.pick && sol.note) {
        var escLabel = sol.status === "escalate:procurement" ? "Procurement, not engineering"
          : (sol.status === "escalate:geometry" ? "Will not fit" : "Beyond solid sawn");
        wrap.appendChild(card("Escalated — " + escLabel, el("span", { class: "badge b-fail", text: sol.status.replace("escalate:", ""), style: "margin-left:auto" }),
          el("div", { style: "display:grid;gap:9px;font-size:.86rem" }, [
            el("p", {}, [el("strong", { text: "Wall: " }), el("span", { text: sol.note.wall })]),
            sol.note.procurement ? el("p", {}, [el("strong", { text: "The member that passes: " }), el("span", { text: sol.note.procurement })]) : null,
            el("p", {}, [el("strong", { text: "What would move it: " }), el("span", { text: sol.note.move })]),
            el("p", { class: "src-note", text: sol.note.outOfScope })
          ]), null));
      }

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
      var pick = m.unifiedTo || sol.pick;
      if (pick) {
        var t = pick.cost.terms;
        wrap.appendChild(card("Why this one — weight breakdown", null, dl([
          { k: "Material <span class='clause'>" + fmt(pick.cost.boardFeet, 1) + " bf @ " + usd(pick.cost.bfUSD) + "/bf</span>", v: usd(t.material) },
          { k: "Labor <span class='clause'>per piece + " + fmt(pick.cost.weightLb, 0) + " lb handling</span>", v: usd(t.labor) },
          { k: "Drop handling <span class='clause'>cut from a " + pick.cost.lengthFt + " ft stick</span>", v: usd(t.drop) },
          { k: "Structural depth <span class='clause'>plate height, chases, finishes</span>", v: usd(t.depth) },
          { k: "Stock risk <span class='clause'>availability " + fmt(pick.cost.availability, 2) + "</span>", v: usd(t.stock) },
          { k: "Unsourced C_F review <span class='clause'>" + pick.cost.cfBasis + "</span>", v: usd(t.risk) },
          { k: "Score", v: usd(pick.score), total: true }
        ]), "Market weights, not code values — they rank passing members and can never promote a failing one"));
      }

      return wrap;
    }

    /* ---------- region pack ---------- */

    function drawRegion(pack) {
      var c = pack.climate;
      body.appendChild(el("div", { class: "grid g2" }, [
        card("Site conditions · " + pack.name, el("span", { class: "badge " + (pack.governs === "wind" ? "b-warn" : "b-mute"), text: pack.governs === "wind" ? "Wind governs" : "Gravity governs", style: "margin-left:auto" }),
          el("div", {}, [
            dl([
              { k: "Markets", v: esc(pack.markets) },
              { k: "Ground snow", v: c.groundSnow.v + " psf" },
              { k: "Roof live", v: c.roofLive.v + " psf" },
              { k: "Basic wind", v: c.windMph.v + " mph" },
              { k: "Exposure", v: esc(c.exposure.v) },
              { k: "Seismic (SDC)", v: esc(c.sdc.v) },
              { k: "Firm DCR target", v: fmt(pack.maxDCR, 2), cls: "gold" }
            ]),
            el("p", { class: "src-note", style: "margin-top:10px", text:
              "Snow, wind, exposure and seismic are PLANNING DEFAULTS for laying out a repeatable plan. " +
              "They are not site values. Replace them from the ASCE 7 Hazard Tool and the AHJ before anything is stamped." })
          ]), pack.climate.groundSnow.note || null),

        card("Design loads handed to the engine", null, el("div", {}, [
          dl([
            { k: "Roof assembly", v: esc(FM.weights.ASSEMBLY[pack.loads.roofAssembly].label) + " · " + FM.weights.ASSEMBLY[pack.loads.roofAssembly].psf + " psf" },
            { k: "Floor assembly", v: esc(FM.weights.ASSEMBLY[pack.loads.floorAssembly].label) + " · " + FM.weights.ASSEMBLY[pack.loads.floorAssembly].psf + " psf" },
            { k: "Ceiling assembly", v: esc(FM.weights.ASSEMBLY[pack.loads.ceilingAssembly].label) + " · " + FM.weights.ASSEMBLY[pack.loads.ceilingAssembly].psf + " psf" },
            { k: "Floor live", v: pack.loads.floorLive + " psf" },
            { k: "Attic live", v: pack.loads.ceilingLive + " psf" },
            { k: "Design roof load", v: pack.loads.roofLoad + " psf · " + (pack.loads.roofType === "snow" ? "snow, C_D 1.15" : "roof live, C_D 1.25"), cls: "gold" }
          ]),
          el("p", { class: "src-note", style: "margin-top:10px", text: pack.loads.roofLoadBasis })
        ]), null)
      ]));

      var ptb = el("tbody");
      pack.palette.forEach(function (p) {
        ptb.appendChild(el("tr", {}, [
          el("td", { class: "k", text: p.species }),
          el("td", { text: p.grade }),
          el("td", { class: "n", text: usd(p.bfUSD) + "/bf" }),
          el("td", { class: "n", text: fmt(p.stockFactor, 2) }),
          el("td", { text: p.note || "" })
        ]));
      });
      body.appendChild(el("div", { style: "margin-top:16px" }, [
        card("Species palette", el("span", { class: "badge b-mute", text: "Market", style: "margin-left:auto" }),
          el("div", { class: "tw", tabindex: "0", role: "region", "aria-label": "Species palette" }, [
            el("table", {}, [
              el("thead", {}, [el("tr", {}, [
                el("th", { text: "Species" }), el("th", { text: "Grade" }), el("th", { class: "n", text: "Price" }),
                el("th", { class: "n", text: "Stock factor" }), el("th", { text: "Note" })
              ])]), ptb
            ])
          ]),
          "Placeholder prices. Replace with your yard's quoted $/bf — it changes the ranking, never the pass/fail.")
      ]));

      var w = FM.weights.policyFor(pack, null).weights;
      body.appendChild(el("div", { style: "margin-top:16px" }, [
        card("Model weights", el("span", { class: "badge b-mute", text: "Firm-calibrated", style: "margin-left:auto" }), dl([
          { k: "Material multiplier", v: fmt(w.material, 2) },
          { k: "Base price fallback", v: usd(w.baseBfUSD) + "/bf" },
          { k: "Labor per piece", v: usd(w.laborPerPiece) },
          { k: "Labor per lb handled", v: usd(w.laborPerLb) },
          { k: "Structural depth", v: usd(w.depthPerInchSf) + " /sf per inch" },
          { k: "Stock risk at zero availability", v: usd(w.stockPenaltySf) + " /sf" },
          { k: "Unsourced C_F review", v: usd(w.unsourcedCF) + " /member" },
          { k: "Unused capacity", v: usd(w.slackPenalty) + " per unit" },
          { k: "Distinct SKU on the plan", v: usd(w.skuPenalty), cls: "gold" }
        ]), "Every weight has a unit. A weight with no unit is one nobody can argue with, which is worse than one that is wrong.")
      ]));

      if (pack.governsNote) {
        body.appendChild(el("div", { style: "margin-top:16px" }, [
          card("What this pack cannot tell you", el("span", { class: "badge b-warn", text: "Scope", style: "margin-left:auto" }),
            el("p", { style: "font-size:.86rem", text: pack.governsNote }), null)
        ]));
      }
    }

    /* ---------- repeat matrix ---------- */

    function drawMatrix(plan) {
      var packs = FM.weights.PACKS;
      var cmp = FM.solver.compare(plan, packs);

      body.appendChild(el("div", { class: "grid g5", style: "margin-bottom:16px" }, [
        FM.statCard(String(cmp.commonMarks), "Same member where applicable", "pass"),
        FM.statCard(String(cmp.varyingMarks), "Regionally forced", "gold"),
        FM.statCard(String(cmp.unansweredMarks), "Unanswered anywhere", cmp.unansweredMarks ? "fail" : ""),
        FM.statCard(String(cmp.solvedMarks) + "/" + plan.marks.length, "Marks with an answer"),
        FM.statCard(String(packs.length), "Regions compared")
      ]));

      var tb = el("tbody");
      cmp.rows.forEach(function (row) {
        var cells = [
          el("td", { class: "k" }, [
            el("span", { text: row.mark.id }),
            row.unanswered ? el("span", { class: "badge b-fail", style: "margin-left:6px", text: "Unanswered" })
              : (row.varies ? el("span", { class: "badge b-gold", style: "margin-left:6px", text: "Varies" })
                            : el("span", { class: "badge b-pass", style: "margin-left:6px", text: "Common" }))
          ]),
          el("td", { text: row.mark.label })
        ];
        row.cells.forEach(function (c) {
          cells.push(el("td", {}, c.notApplicable
            ? [el("span", { class: "badge b-blue", text: c.note === "component" ? "component" : "n/a" })]
            : c.sku
            ? [el("span", { text: c.sku.replace(" Southern Pine", " SYP").replace(" Spruce-Pine-Fir", " SPF").replace(" Douglas Fir-Larch", " DF-L") }),
               el("span", { class: "clause", text: (c.spacing ? c.spacing + "″ · " : "") + "DCR " + fmt(c.dcr, 2) })]
            : [el("span", { class: "badge b-fail", text: "none" })]));
        });
        tb.appendChild(el("tr", {}, cells));
      });

      body.appendChild(el("div", { class: "tw", tabindex: "0", role: "region", "aria-label": "Cross-region member matrix" }, [
        el("table", {}, [
          el("thead", {}, [el("tr", {}, [el("th", { text: "Mark" }), el("th", { text: "Member" })].concat(
            packs.map(function (p) { return el("th", { text: p.name.replace(" · ", " ") }); })
          ))]),
          tb
        ])
      ]));

      body.appendChild(el("div", { style: "margin-top:16px" }, [
        card("Reading this", null, el("div", { style: "display:grid;gap:9px;font-size:.86rem" }, [
          el("p", { text: "A mark marked Unanswered produced no member in any region — it is not portable, it is unanswered, and counting it as common would turn silence into evidence for this product's central claim." }),
          el("p", { text: "A mark marked Common is the same member in every region on this board — build it the same everywhere and buy it in one order. A mark marked Varies is regionally forced, and the region pack says which variable forced it." }),
          el("p", { text: "The three forcings that actually move members across these six packs are: snow duration in the Carolina mountains, which drops C_D from 1.25 to 1.15; concrete tile dead load in the HVHZ, which is 22 psf against 15 for shingle; and species availability, which decides what the yard can hand the framer." }),
          el("p", { class: "src-note", text: "Every cell is an independent solve against that region's palette, ladder, loads and DCR target. No cell is inferred from another." })
        ]), null)
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

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

  /* Six modules, six authors, one contract — and a field name that moved is
     invisible until it renders as "undefined" in front of somebody. Read the
     first field that is actually present rather than asserting one. */
  function pick(o, names) {
    if (!o) return "";
    for (var i = 0; i < names.length; i++) {
      var v = o[names[i]];
      if (v !== undefined && v !== null && v !== "") return String(v);
    }
    return "";
  }

  /* A provenance-carrying record used to render as one dl() row here. It was
     replaced by factRow(), below: dl() puts the value AND its citation inside
     `.dl-v`, which is a right-aligned nowrap mono column, and a citation
     paragraph in it is clipped off the right edge of the card with no
     scrollbar. Kept out rather than kept around — a second row renderer is
     how the two would drift. */

  function n2(v, d) {
    return (v === null || v === undefined || !isFinite(v)) ? "—" : Number(v).toFixed(d === undefined ? 2 : d);
  }

  /* A DERIVED NUMBER, AS A PERSON READS IT — AND AS THE ENGINE HOLDS IT.

     The derivation panel printed String(d.value), so a tributary derived as
     half a 31.708333 ft clear span rendered as "15.854167" on the one screen
     whose whole purpose is being read by a person before they approve it.
     Seventeen significant figures is not more accurate, it is less legible,
     and the takeoff's own prose beside it says 15.854 ft.

     Rounding for display and then saying nothing would be the worse fix,
     because the number the solver consumed is the long one and a reviewer
     re-deriving from the short one gets a different answer in the last
     place. So the short form is shown and the exact one is named whenever
     they differ. Nothing is hidden and nothing is over-stated. */
  function derivedValue(v) {
    if (typeof v !== "number" || !isFinite(v)) return { shown: String(v), exact: null };
    var shown = v.toFixed(3);
    if (shown.indexOf(".") !== -1) shown = shown.replace(/0+$/, "").replace(/\.$/, "");
    return { shown: shown, exact: Number(shown) === v ? null : String(v) };
  }

  /* WHAT AN EXPORTED FILE IS FOR.

     This was `firmark-materials.txt` — no plan, no region, no variant — while
     its two siblings in this product both carry identity:

         firmark-planset-starter-1210-tx-i35-for-PE-review.txt
         firmark-schedule-two-story-2450-tx-i35.txt

     Two materials exports from two different plans therefore collided in
     Downloads under one name, the second silently replacing the first, and
     neither could be traced back to what produced it. A quantity takeoff that
     cannot be tied to a plan and a region pack is a number with no basis,
     which is the one thing this product exists not to ship.

     The identity is read off the BOM's own `plan` and `pack` records rather
     than off the project state, so the name always describes the document in
     the file. What is missing is NAMED in the filename — "no-plan" /
     "no-region", the same words planset.js uses on the cover — never quietly
     omitted, because a file called `firmark-materials-tx-i35.txt` reads like
     a complete name and is not one. */
  function bomFilename(b) {
    var pl = (b && b.plan) || null, pk = (b && b.pack) || null;
    var parts = [pl && pl.id ? String(pl.id) : "no-plan",
                 pk && pk.id ? String(pk.id) : "no-region"];
    if (pl && pl.variant && pl.variant.id) parts.push(String(pl.variant.id));
    return ("firmark-materials-" + parts.join("-")).replace(/[^\w.-]+/g, "-") + ".txt";
  }
  FM.bomFilename = bomFilename;

  /* A block of things a stage could not answer. Never collapsed, never
     truncated silently, and it says zero rather than disappearing — an
     absent list and an empty list read identically and mean opposite things. */
  /* `blocks` says whether this list ACTUALLY stops the gate — it is not a
     decoration. The footer read "A stage is not approvable while anything here
     is unanswered" on all three screens, and it was true on exactly one:
     project.js pushes every takeoff `unresolved` as a blocker, but the loads
     gate blocks only on a missing jurisdiction and the BOM gate blocks on
     nothing at all. So a card with a gold BLOCKING badge sat over ten
     unanswered must-verify items on a stage that approved cleanly.

     A false claim about a gate is worse than a missing gate: it tells a
     reviewer the system is holding a line it is not holding. Either the badge
     tells the truth or the gate does; here the badge does, and the wording
     says who the item is for instead. */
  function openItems(title, rows, emptyText, blocks, forWhom) {
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
    var badge = !rows.length ? { c: "b-pass", t: "None" }
              : blocks ? { c: "b-fail", t: "Blocks this gate" }
                       : { c: "b-gold", t: "Does not block" };
    return card(title + " — " + rows.length,
      el("span", { class: "badge " + badge.c, style: "margin-left:auto", text: badge.t }),
      body,
      blocks
        ? "This gate cannot be approved while anything here is unanswered."
        : (forWhom || "These do not stop the gate. Approving this stage means you have read them " +
                      "and accepted them as open — they travel to the PE package as open items."));
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
      }), "The geometry determined every value. Nothing was assumed.", true)
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
        var dv = derivedValue(d.value);
        return {
          k: esc(d.field),
          v: esc(dv.shown) +
             (dv.exact ? " <span class='clause'>shown to 3 dp — the value carried into the " +
                         "calculation is " + esc(dv.exact) + "</span>" : "") +
             " <span class='clause'>" + esc(d.how || "") +
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

     THE CAVEAT GOES ABOVE THE NUMBERS.

     On 13 August 2026 a verification pass found two published values in
     jurisdiction.js wrong. Austin was carried on the 2021 IRC when the city
     adopted the 2024 IRC (Ordinance 20250410-040, effective 10 July 2025) —
     wrong by a full code generation, and it took the referenced wind
     standard with it, so anyone who read an Austin wind speed off this
     screen read the ASCE 7-16 map for a permit governed by ASCE 7-22. And
     the wind-borne-debris test — the one that decides whether opening
     protection is required — was the pre-ASCE-7-22 criterion, which made
     "not coastal" look like a complete answer for an inland Florida county
     when the code in force deletes the word "coastal" and substitutes an
     Exposure D fetch condition that pulls large inland lakes in.

     What this screen has to carry is not those two facts. It is their SHAPE:
     a plausible, confidently formatted, five-year-stale value survived until
     somebody checked, and the module's own must-verify list had already
     named Austin's adoption as the one most likely to have moved. The list
     was right and the data was wrong. So the caveat sits ABOVE the design
     criteria rather than under them, because this is the screen where a
     reader is most likely to take a number and act on it, and a warning
     underneath a table has already been scrolled past by the person who
     needed it.

     The must-verify count is COUNTED, never typed. It went 203 -> 204
     during the verification: it grew, which is the honest direction, and
     this codebase has been bitten four times by a headline number written
     into prose by hand.
     ============================================================ */

  var mvTotal = null;
  function mustVerifyTotal() {
    if (mvTotal !== null) return mvTotal;
    var n = 0, ok = true;
    try {
      FM.juris.STATES.forEach(function (st) {
        (FM.juris.jurisdictions(st) || []).forEach(function (j) {
          var site = FM.juris.forSite(j.id);
          n += (site && site.mustVerify ? site.mustVerify.length : 0);
        });
      });
    } catch (e) { ok = false; }
    mvTotal = ok ? n : null;
    return mvTotal;
  }

  /* How a source was retrieved is a provenance class in its own right, and
     "two independent routes agreed" is not the same claim as "one search
     summary said so". They get different badges. */
  function retrievalOf(srcId) {
    if (!srcId || !FM.juris.SOURCES) return null;
    var hit = null;
    FM.juris.SOURCES.forEach(function (s) { if (!hit && s.id === srcId) hit = s; });
    return hit ? hit.retrieved : null;
  }
  function retrievalBadge(retrieved) {
    if (retrieved === "search-summary-corroborated") {
      return { c: "b-blue", t: "corroborated", title: "Multiple independent search routes agreed on this value." };
    }
    if (retrieved === "search-summary") {
      return { c: "b-gold", t: "one summary", title: "A single search summary. The primary document was not opened." };
    }
    if (retrieved === "not-fetched") {
      return { c: "b-mute", t: "not fetched", title: "The source was named but not retrieved at all." };
    }
    return null;
  }

  /* The banner. Deliberately not collapsible and deliberately first. */
  function planningDataCaveat() {
    var n = mustVerifyTotal();
    var box = el("div", { class: "banner banner-warn",
                          style: "margin-bottom:16px;display:block",
                          role: "note", "aria-label": "Planning data caveat" });
    box.appendChild(el("div", { style: "font-weight:700;font-size:.95rem;margin-bottom:6px",
      text: "Planning data only — not permit data." }));
    box.appendChild(el("p", { style: "margin:0 0 6px;font-size:.86rem", text:
      "No value on this screen was read from a primary code document. Every one of them " +
      "came from search summaries of pages this build could not open." }));
    box.appendChild(el("p", { style: "margin:0 0 6px;font-size:.86rem", text:
      "Two published values were found WRONG on " +
      (FM.juris.CHECKED || "13 August 2026") +
      ": Austin's code edition, and the wind-borne-debris test. Both are corrected and " +
      "both are shown below, because a product that shows its own corrections is making " +
      "a stronger claim than one that shows none." }));
    box.appendChild(el("p", { style: "margin:0;font-size:.86rem", text:
      "Confirm the edition in force on your permit date, and every design value, with the " +
      "authority having jurisdiction and the ASCE 7 Hazard Tool before drawing. " +
      (n === null
        ? "The must-verify items on this dataset could not be counted in this build — read them per jurisdiction."
        : n + " open items across the covered jurisdictions — read them.") }));
    return box;
  }

  /* WHAT WAS WRONG, WHAT REPLACED IT, AND WHO DISAGREES.

     Shown open, not behind a toggle, and shown on every jurisdiction rather
     than only on the two that were corrected — because the finding is about
     the dataset and a reader looking at Wake County has the same reason to
     distrust a confidently formatted edition date as a reader looking at
     Austin. The dissent is printed: the window-vendor pages that say Orlando
     is outside the debris region are lower authority than the Commission's
     own study, and saying so is more useful than deleting them. */
  function correctionsCard() {
    var list = FM.juris.CORRECTIONS;
    var body = el("div", { style: "display:grid;gap:12px" });
    if (!list || !list.length) {
      body.appendChild(el("p", { class: "clause", text:
        "This build records no corrections to the jurisdiction dataset. That is not the " +
        "same as the dataset being right — two values were found wrong the first time " +
        "anyone checked, and nothing here has been read from a primary document." }));
      return card("Corrections to this dataset — 0",
        el("span", { class: "badge b-mute", text: "None recorded", style: "margin-left:auto" }),
        body, null);
    }
    /* Stacked, not dl(). `.dl-v` is a right-aligned nowrap MONO COLUMN built
       for numbers: hand it a paragraph and the paragraph runs off the right
       edge of the card and is clipped without a scrollbar. These findings are
       prose and the prose is the point, so each one gets a label above its
       text rather than beside it. */
    function part(label, text) {
      if (!text) return null;
      return el("div", { style: "margin-top:6px" }, [
        el("div", { class: "lbl", text: label }),
        el("p", { style: "margin:2px 0 0;font-size:.84rem", text: String(text) })
      ]);
    }
    list.forEach(function (c) {
      body.appendChild(el("div", { style: "border-left:3px solid var(--warn);padding-left:10px" }, [
        el("div", { style: "font-size:.88rem;font-weight:700;display:flex;gap:8px;align-items:center;flex-wrap:wrap" }, [
          el("span", { class: "badge " + (c.severity === "blocking" ? "b-fail" : "b-gold"),
                       text: String(c.severity || "correction") }),
          el("span", { text: String(c.id || "correction") }),
          c.checked ? el("span", { class: "clause", text: "checked " + c.checked }) : null
        ].filter(Boolean)),
        part("Was — and this is what the product published", c.was),
        part("Now", c.now),
        part("Why it matters", c.why),
        part("Established by", c.establishedBy),
        part("Sources that dissent", c.dissent),
        part("Confirmed", String(c.confirmed || "not stated") +
             " — search summaries agreed across independent routes; no primary document " +
             "was opened, because this build cannot reach one.")
      ].filter(Boolean)));
    });
    var rc = FM.juris.RECHECKED;
    if (rc && rc.length) {
      var agreed = 0;
      rc.forEach(function (r) { if (r.agreed) agreed++; });
      body.appendChild(el("p", { class: "clause", style: "margin-top:2px", text:
        "The same pass re-checked " + rc.length + " other published facts and " + agreed +
        " of them held, each against a named route — see “What was re-checked and held”, below." }));
    }
    return el("div", { style: "margin-bottom:16px" }, [
      card("Corrections to this dataset — " + list.length,
        el("span", { class: "badge b-fail", text: "Found wrong on " + (FM.juris.CHECKED || "13 Aug 2026"),
                     style: "margin-left:auto" }),
        body,
        "A published value that is wrong and confident is the failure mode this whole " +
        "product is built against. These two survived until somebody checked, and the " +
        "module's own must-verify list had already named the first of them as the " +
        "adoption most likely to have moved. The list was right and the data was wrong.")
    ]);
  }

  /* A PROVENANCE ROW WHOSE CITATION IS ACTUALLY LEGIBLE.

     Every value on this screen was built with dl(), and `.dl-v` is a
     right-aligned MONO COLUMN with `white-space: nowrap` — it exists for
     numbers. The citations here are paragraphs, so the design wind speed row
     rendered 3,072 PIXELS PAST THE RIGHT EDGE of its card, clipped, with no
     scrollbar and no affordance. What fell off included the sentence "MUST BE
     CONFIRMED FOR THE ACTUAL SITE. This is a planning value, not a lookup"
     and, after the Austin correction, "READ THIS OFF THE ASCE 7-22 MAP, NOT
     7-16" — the two sentences on the screen that most needed reading.

     This is register §O.1's B1 again (1,807px of table in a 996px container)
     in a place nobody re-checked: the provenance was published and invisible,
     which reads exactly like provenance that was never written. So the value
     and its badges go on one line and the citation goes UNDER them as
     wrapping prose. */
  function factRow(label, value, badges, cite, note) {
    var head = el("div", { style: "display:flex;gap:8px;align-items:baseline;flex-wrap:wrap" }, [
      el("span", { style: "font-size:.84rem;color:var(--muted);min-width:11rem", text: label }),
      el("span", { class: "mono", style: "font-weight:650;font-size:.86rem", text: String(value) })
    ]);
    (badges || []).forEach(function (b) {
      if (!b) return;
      head.appendChild(el("span", { class: "badge " + b.c, text: b.t, title: b.title || null }));
    });
    var kids = [head];
    if (cite) kids.push(el("p", { class: "clause", style: "margin:3px 0 0", text: String(cite) }));
    if (note) kids.push(el("p", { class: "clause", style: "margin:3px 0 0", text: String(note) }));
    return el("div", { style: "padding:7px 0;border-bottom:1px dashed var(--line)" }, kids);
  }

  function recheckedCard() {
    var rc = FM.juris.RECHECKED;
    if (!rc || !rc.length) return null;
    var body = el("div", { style: "display:grid;gap:7px" });
    rc.forEach(function (r) {
      body.appendChild(el("div", {}, [
        el("div", { style: "font-size:.84rem" }, [
          el("span", { class: "badge " + (r.agreed ? "b-pass" : "b-gold"),
                       text: (isFinite(r.routes) ? r.routes + " route" + (r.routes === 1 ? "" : "s") : "routes not stated") +
                             (r.agreed ? " agreed" : " DISAGREED") }),
          el("span", { style: "margin-left:6px", text: String(r.item || "(unnamed fact)") })
        ]),
        r.against ? el("div", { class: "clause", style: "margin-left:12px",
                                text: "checked against " + r.against }) : null
      ].filter(Boolean)));
    });
    return el("div", { style: "margin-bottom:16px" }, [
      card("What was re-checked and held — " + rc.length,
        el("span", { class: "badge b-blue", text: "Secondary sources only", style: "margin-left:auto" }),
        body,
        "Holding across two or three search routes is the strongest claim this build can " +
        "make about any of these values, and it is weaker than reading the ordinance. " +
        "Nothing in this list is a substitute for the AHJ.")
    ]);
  }

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

    /* This called FM.juris.jurisdictionById(), which does not exist — so it
       returned "" on every render, the state picker read "Choose a state…"
       above a full criteria table, and picking a state wiped the jurisdiction
       you were already on. The module has no by-id lookup, so find it the way
       the data allows: the id is prefixed with the state, and the listing is
       authoritative. */
    function currentState() {
      if (!s.jurisId) return stateSel.value || "";
      for (var i = 0; i < FM.juris.STATES.length; i++) {
        var st = FM.juris.STATES[i];
        var found = (FM.juris.jurisdictions(st) || []).filter(function (j) {
          return j.id === s.jurisId;
        })[0];
        if (found) return st;
      }
      return stateSel.value || "";
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

    /* ABOVE EVERY PUBLISHED VALUE, including the empty state — the caveat is
       about the dataset the picker is about to hand you, not about one site. */
    host.appendChild(planningDataCaveat());
    host.appendChild(correctionsCard());

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
    var codeBody = el("div", {});
    if (!(site.codes || []).length) {
      codeBody.appendChild(el("p", { class: "clause", text: "None recorded." }));
    }
    (site.codes || []).forEach(function (c) {
      /* HOW the value was retrieved rides next to the value, because "four
         independent routes agreed on this ordinance number" and "one search
         summary said so" are different claims and the Austin error was
         published under the second one wearing the confidence of the first. */
      codeBody.appendChild(factRow(c.name, c.edition || "—", [
        { c: clsBadge(c.cls), t: String(c.cls || "?") },
        retrievalBadge(retrievalOf(c.src)),
        (c.status && c.status !== "in force") ? { c: "b-mute", t: String(c.status) } : null,
        c.asce ? { c: "b-blue", t: "references " + c.asce } : null
      ], (c.cite || "") + (c.adopted ? "  · adopted " + c.adopted : ""), c.note || null));
    });
    host.appendChild(el("div", { style: "margin-bottom:16px" }, [
      card("Governing code", null, codeBody,
        (site.authority ? "Authority having jurisdiction: " + site.authority + ". " : "") +
        "The badge on each row says how the value was retrieved, not how sure this " +
        "product is of it: nothing here was read from a primary code document.")
    ]));

    /* the design criteria */
    var critBody = el("div", {});
    function crit(label, v, unit) {
      if (!v) return;
      var value = v.v !== undefined ? v.v
                : v.vMph !== undefined ? v.vMph
                : v.pgPsf !== undefined ? v.pgPsf : v.sdc;
      critBody.appendChild(factRow(label,
        (value === null || value === undefined ? "NOT DECLARED" : String(value) + (unit ? " " + unit : "")),
        [ (value === null || value === undefined) ? { c: "b-mute", t: "not stated" }
                                                  : { c: clsBadge(v.cls), t: String(v.cls || "?") },
          retrievalBadge(retrievalOf(v.src)),
          v.band && v.band.length === 2 ? { c: "b-gold", t: "band " + v.band[0] + "–" + v.band[1] } : null ],
        v.cite || "", v.note || null));
    }
    function critRec(label, r, valueKey, unit) {
      if (!r) return;
      var v = (typeof r === "object") ? r[valueKey] : r;
      critBody.appendChild(factRow(label,
        (v === undefined || v === null) ? "not established" : String(v) + (unit ? " " + unit : ""),
        [ (v === undefined || v === null) ? { c: "b-mute", t: "not stated" }
                                          : { c: clsBadge(r.cls), t: String(r.cls || "?") } ],
        (r && r.cite) || "", (r && r.note) || null));
    }

    crit("Design wind speed", site.wind, "mph");
    /* Exposure is deliberately NOT a jurisdiction fact — ASCE 7 §26.7 makes it
       a fetch determination at the site — so the record carries `exposure:
       null` and an advisory `exposureCommon`. Printing the advisory as the
       value would manufacture a design input. */
    if (site.wind) {
      critBody.appendChild(factRow("Exposure category",
        site.wind.exposure ? String(site.wind.exposure) : "NOT DECLARED — a site determination",
        [ site.wind.exposure ? { c: clsBadge(site.wind.cls), t: String(site.wind.cls || "?") }
                             : { c: "b-mute", t: "not stated" },
          (!site.wind.exposure && site.wind.exposureCommon)
            ? { c: "b-gold", t: "commonly " + site.wind.exposureCommon + " — advisory" } : null ],
        site.wind.exposureNote || "", null));
    }
    crit("Ground snow", site.snow, "psf");
    crit("Seismic design category", site.seismic, "");
    /* These arrive as RECORDS — {inches, cls, cite, confirmed} and {level, …} —
       because "every value carries cls and cite" outranks the convenience of
       a bare number. String() on one prints "[object Object]". */
    critRec("Frost depth", site.frostDepthIn, "inches", "in");
    critRec("Termite", site.termite, "level", "");
    critRec("Decay", site.decay, "level", "");

    /* WIND-BORNE DEBRIS — the row that was asserting a code requirement.

       `site.windborneDebris` is a RECORD — {inRegion, likely, criterion, …} —
       and this row read it as a boolean. An object is always truthy, so the
       screen printed "Yes — opening protection required" on EVERY
       jurisdiction in the product: on Austin, where the module says
       inRegion:false, and on Orange County, where the module deliberately
       says inRegion:NULL because the ASCE 7-22 test cannot be settled at
       county level. The consultant set that value to null precisely so the
       product would stop asserting it, and the view asserted it anyway — in
       the affirmative, on the one criterion that decides whether impact-rated
       glazing is required.

       Three states, three sentences, and null is not one of the other two. */
    if (site.windborneDebris !== undefined && site.windborneDebris !== null) {
      var wb = site.windborneDebris;
      var inR = (typeof wb === "object") ? wb.inRegion : wb;
      var wbText = inR === true ? "YES — opening protection is required"
                 : inR === false ? "No — outside the region on the test below"
                 : "NOT DETERMINED — this is a site test, not a county fact";
      var wbBadge = inR === true ? { c: "b-fail", t: "required" }
                  : inR === false ? { c: "b-pass", t: "not required here" }
                                  : { c: "b-gold", t: "undetermined" };
      var likelyBadge = null;
      if (typeof wb === "object" && wb.likely !== null && wb.likely !== undefined && wb.inRegion === null) {
        likelyBadge = { c: "b-mute", t: "likely " + (wb.likely ? "yes" : "no") + " — advisory only" };
      }
      critBody.appendChild(factRow("Wind-borne debris region", wbText,
        [wbBadge, likelyBadge,
         (typeof wb === "object" && wb.cls) ? { c: clsBadge(wb.cls), t: String(wb.cls) } : null,
         retrievalBadge(retrievalOf(typeof wb === "object" ? wb.src : null))],
        (typeof wb === "object" ? (wb.cite || "") : ""),
        (typeof wb === "object" ? (wb.criterion || "") : "")));
      if (typeof wb === "object" && wb.note) {
        critBody.appendChild(el("p", { class: "clause", style: "margin:2px 0 8px",
                                       text: String(wb.note) }));
      }
    }
    if (site.hvhz !== undefined && site.hvhz !== null) {
      critBody.appendChild(factRow("HVHZ",
        site.hvhz ? "Yes — High-Velocity Hurricane Zone" : "No",
        [{ c: site.hvhz ? "b-fail" : "b-mute", t: site.hvhz ? "HVHZ" : "outside" }],
        "The HVHZ is Miami-Dade and Broward only. It is its own code regime, not a wind speed.",
        null));
    }

    host.appendChild(el("div", { style: "margin-bottom:16px" }, [
      card("Design criteria", null, critBody,
        "Every value carries its provenance class and its citation, and the citation is " +
        "printed rather than truncated. A [site] value is a planning default until it is " +
        "confirmed; a row reading NOT DECLARED or NOT DETERMINED is one this product " +
        "refuses to supply, not one it forgot.")
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
          /* The module reports jurisValue / packValue / why / effect. `effect`
             is the one that matters and it is written to be read out loud —
             it says whether a difference moves a member here or moves
             something this engine does not design at all. */
          var num = (d.jurisValue !== null && d.jurisValue !== undefined)
            ? String(d.jurisValue) + " here vs " +
              (d.packValue === null || d.packValue === undefined
                 ? "nothing declared by the pack" : String(d.packValue) + " in the pack")
            : null;
          fitBody.appendChild(el("div", { style: "border-left:3px solid var(--gold);padding-left:10px" }, [
            el("div", { style: "font-size:.84rem;font-weight:650", text: d.what }),
            num ? el("div", { class: "mono", style: "font-size:.8rem", text: num }) : null,
            d.why ? el("div", { class: "clause", text: d.why }) : null,
            d.effect ? el("div", { style: "font-size:.82rem;margin-top:3px", text: d.effect }) : null
          ].filter(Boolean)));
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
          /* mustVerify carries `check` (what to check) and `authority` (who
             against). ARCHITECTURE requires the item say what to check it
             against; the module does that and this view was dropping both. */
          if (typeof v === "string") return { what: v };
          return {
            what: pick(v, ["what", "item", "label"]),
            why: pick(v, ["why", "note", "detail"]),
            need: pick(v, ["need", "check", "against", "how"]) +
                  (v.authority ? " — " + v.authority : "")
          };
        }),
        "Nothing listed — which should not happen. Wind speed and snow are site-specific and this list should never be empty.",
        false,
        "These do NOT stop the loads gate — a site is confirmed against the ASCE 7 Hazard Tool " +
        "and the AHJ, not in this browser. Approving this stage means you accept them as open, " +
        "and every one of them prints on the PE package as an open item.")
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
      /* A checklist item is `{item, why, cite}` — reading `.text` printed the
         literal word "undefined" five times on every jurisdiction, and the
         first of those five is the sentence that says this software does not
         seal. suite-juris asserts that sentence exists; it passes, because it
         tests the module. The view was deleting it. Read whichever field is
         actually there rather than assuming one. */
      list.forEach(function (c) {
        var txt = typeof c === "string" ? c : pick(c, ["item", "text", "what", "label"]);
        var why = typeof c === "string" ? null : pick(c, ["why", "note", "detail"]);
        cb.appendChild(el("div", { style: "font-size:.84rem" }, [
          el("span", { text: "· " + txt }),
          why ? el("div", { class: "clause", style: "margin-left:12px", text: why }) : null,
          (c && c.cite) ? el("div", { class: "clause", style: "margin-left:12px", text: c.cite }) : null
        ].filter(Boolean)));
      });
      host.appendChild(el("div", { style: "margin-bottom:16px" }, [
        card("Submittal checklist", null, cb,
          "What this jurisdiction expects to receive. This system produces some of it, not all of it.")
      ]));
    }

    /* the 15 facts that HELD, and the route each was checked against. Last,
       because it is the reassuring half and the caveat is the load-bearing
       one — a screen that opens with what held and closes with what was
       wrong has the emphasis backwards. */
    var rcCard = recheckedCard();
    if (rcCard) host.appendChild(rcCard);
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
            if (!FM.download) { FM.toast("Export is unavailable in this build."); return; }
            var name = bomFilename(b);
            FM.download(FM.bom.text(b), name);
            FM.toast(/no-plan|no-region/.test(name)
              ? "Exported as " + name + " — this list could not name the plan or the region " +
                "pack it came from, and the filename says so rather than hiding it."
              : "Exported as " + name + " — quantities only; prices are [market] placeholders.");
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
        "Nothing excluded — which cannot be right. Connectors, sheathing and fasteners are never sized here.",
        false,
        "These do NOT stop the materials gate — they are what the list does not cover, not defects " +
        "in it. Approving this stage means you have read them and know what still has to be priced " +
        "elsewhere.")
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

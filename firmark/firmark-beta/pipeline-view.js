/* ============================================================
   pipeline-view.js — the run screen.

   Six stages, six gates, one page. This is the view that makes the
   product's claim legible: a plan becomes a review package quickly,
   and a named person accepted each step on the way.

   The design decision worth stating: a gate is rendered with its
   BLOCKERS first and its approve button last. The reason is that the
   button is the cheap part. What makes an approval worth anything is
   that the person pressing it was shown, immediately above it, the
   list of things this stage could not resolve.
   ============================================================ */

(function () {
  "use strict";

  var el = FM.el, card = FM.card, dl = FM.dl, esc = FM.esc;

  function fmtWhen(iso) {
    if (!iso) return "—";
    return String(iso).slice(0, 16).replace("T", " ") + " UTC";
  }

  FM.VIEWS.pipeline = function (host) {
    if (!FM.pipeline) {
      host.appendChild(FM.pageHead("Run", "Pipeline"));
      host.appendChild(el("div", { class: "empty", text: "The pipeline module failed to load." }));
      return;
    }

    var snap = FM.pipeline.snapshot();
    var user = FM.auth ? FM.auth.state().user : null;

    host.appendChild(FM.pageHead(
      "Run",
      "An architectural plan to a package a licensed engineer can review — with a name on every step.",
      [
        el("button", {
          class: "btn", text: "Sign out",
          onclick: function () { if (FM.signOut) FM.signOut(); FM.go("pipeline"); }
        }),
        el("button", {
          class: "btn", text: "Reset approvals",
          onclick: function () {
            /* deliberately not a confirm() — the trail keeps the reset, so the
               action is reversible in the only sense that matters: visible */
            FM.pipeline.reset();
            FM.toast("Approvals cleared. The reset is in the audit trail.");
            FM.go("pipeline");
          }
        })
      ]));

    host.appendChild(FM.stageRail("pipeline"));

    /* ---- where the run stands ---- */
    var done = 0, stale = 0;
    snap.stages.forEach(function (r) {
      if (r.status === "approved") done++;
      if (r.status === "stale") stale++;
    });

    host.appendChild(el("div", { class: "grid g4", style: "margin-bottom:16px" }, [
      FM.statCard(done + "/" + snap.stages.length, "Stages approved", done === snap.stages.length ? "pass" : ""),
      FM.statCard(String(stale), "Need re-approval", stale ? "gold" : ""),
      FM.statCard(user ? user.name : "—", "Signed in as"),
      FM.statCard(snap.complete ? "Ready for PE" : FM.pipeline.stageById(snap.current).label, "Next")
    ]));

    if (stale) {
      host.appendChild(el("div", { class: "banner banner-gold", style: "margin-bottom:14px" }, [
        el("strong", { text: stale + " approval" + (stale === 1 ? "" : "s") + " went stale — " }),
        el("span", { text: "something upstream changed after they were given. An approval that " +
                           "survives a change to what was approved is worth nothing, so they are " +
                           "withdrawn rather than carried. Re-approve after checking what moved." })
      ]));
    }

    /* ---- the stages ---- */
    snap.stages.forEach(function (row, i) {
      var st = row.stage;
      var cls = "gate-panel";
      if (row.status === "approved") cls += " is-approved";
      else if (row.status === "stale") cls += " is-stale";
      else if (row.blockedBy.length) cls += " is-blocked";
      else if (st.id === snap.current) cls += " is-open";

      var body = el("div", { class: cls, style: "display:grid;gap:10px" });

      body.appendChild(el("p", { style: "font-size:.85rem", text: st.detail }));
      body.appendChild(el("p", { class: "clause", text: "GATE — " + st.gate }));

      /* what this stage could not resolve. First, deliberately. */
      if (row.blockers.length) {
        var ul = el("ul", { class: "gate-block-list" });
        row.blockers.forEach(function (b) { ul.appendChild(el("li", { text: b })); });
        body.appendChild(el("div", {}, [
          el("p", { style: "font-size:.8rem;font-weight:650", text: "This stage cannot be approved until these are resolved:" }),
          ul
        ]));
      }

      if (row.status === "stale" && row.moved.length) {
        body.appendChild(el("div", { class: "banner banner-gold" }, [
          el("strong", { text: "Withdrawn — " }),
          el("span", { text: row.moved.map(function (m) {
            return m.self ? "this stage's own content changed after approval"
                          : m.label + " changed after this was approved";
          }).join("; ") + "." })
        ]));
      }

      if (row.rec && row.rec.status === "approved") {
        body.appendChild(dl([
          { k: "Approved by", v: esc(row.rec.by) + " <span class='clause'>as " +
              esc(FM.auth && FM.auth.ROLES[row.rec.role] ? FM.auth.ROLES[row.rec.role].label : row.rec.role) + "</span>" },
          { k: "When", v: fmtWhen(row.rec.at) },
          { k: "Fingerprint", v: "<span class='mono'>" + esc(row.rec.fp || "—") + "</span> " +
              "<span class='clause'>of what was in front of them</span>" },
          row.rec.note ? { k: "Note", v: esc(row.rec.note) } : null
        ].filter(Boolean)));
      } else if (row.rec && row.rec.status === "rejected") {
        body.appendChild(el("div", { class: "banner banner-warn" }, [
          el("strong", { text: "Rejected by " + esc(row.rec.by) + " — " }),
          el("span", { text: row.rec.note || "no reason given" })
        ]));
      }

      /* the controls */
      var note = el("input", {
        type: "text", placeholder: "What did you check? (goes in the record)",
        "aria-label": "Approval note for " + st.label, style: "flex:1;min-width:200px"
      });

      var actions = el("div", { style: "display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:2px" }, [
        note,
        el("button", {
          class: "btn btn-primary",
          text: row.status === "approved" ? "Re-approve" : "Approve",
          disabled: row.can ? null : "disabled",
          onclick: function () {
            var r = FM.pipeline.approve(st.id, note.value);
            if (!r.ok) { FM.toast("Not approved — " + r.why.join("; ")); return; }
            FM.toast(st.label + " approved by " + FM.auth.state().user.name + ".");
            FM.go("pipeline");
          }
        }),
        el("button", {
          class: "btn", text: "Reject",
          onclick: function () {
            FM.pipeline.reject(st.id, note.value || "no reason given");
            FM.toast(st.label + " rejected. Downstream stages stay closed.");
            FM.go("pipeline");
          }
        }),
        el("button", {
          class: "btn btn-sm", text: "Open stage",
          onclick: function () { FM.go(VIEW_OF[st.id] || "pipeline"); }
        })
      ]);

      if (!row.can && row.blockedBy.length) {
        actions.appendChild(el("span", { class: "clause", text: "blocked: " + row.blockedBy.join(" · ") }));
      }
      body.appendChild(actions);

      var badge = row.status === "approved"
        ? el("span", { class: "badge b-pass", text: "Approved", style: "margin-left:auto" })
        : row.status === "stale"
          ? el("span", { class: "badge b-gold", text: "Needs re-approval", style: "margin-left:auto" })
          : row.status === "rejected"
            ? el("span", { class: "badge b-fail", text: "Rejected", style: "margin-left:auto" })
            : el("span", { class: "badge b-mute", text: "Not approved", style: "margin-left:auto" });

      host.appendChild(el("div", { style: "margin-bottom:12px" }, [
        card(String(i + 1) + " · " + st.label, badge, body,
             "Needs the " + (FM.auth && FM.auth.ROLES[st.needs] ? FM.auth.ROLES[st.needs].label : st.needs) +
             " role" + (st.inputs.length ? " · depends on " + st.inputs.join(", ") : ""))
      ]));
    });

    /* ---- the trail ---- */
    var trail = FM.pipeline.audit().slice().reverse();
    var tb = el("tbody");
    if (!trail.length) {
      tb.appendChild(el("tr", {}, [
        el("td", { colspan: "4", class: "empty-cell" }, [
          el("div", { class: "empty", style: "margin:0", text: "Nothing has been approved yet." })
        ])
      ]));
    } else {
      trail.slice(0, 40).forEach(function (e) {
        tb.appendChild(el("tr", {}, [
          el("td", { class: "k", text: fmtWhen(e.at) }),
          el("td", { text: e.by }),
          el("td", {}, [el("span", {
            class: "badge " + (e.kind === "approve" ? "b-pass" : e.kind === "reject" ? "b-fail" : "b-mute"),
            text: e.kind
          }), el("span", { style: "margin-left:6px", text: e.stage || "—" })]),
          el("td", { text: e.note || "" })
        ]));
      });
    }
    host.appendChild(el("div", { style: "margin-top:18px" }, [
      card("Audit trail",
        el("span", { class: "badge b-blue", text: "Append-only", style: "margin-left:auto" }),
        el("div", { class: "tw", tabindex: "0", role: "region", "aria-label": "Audit trail" }, [
          el("table", {}, [
            el("thead", {}, [el("tr", {}, [
              el("th", { text: "When" }), el("th", { text: "Who" }),
              el("th", { text: "What" }), el("th", { text: "Note" })
            ])]), tb
          ])
        ]),
        "Rejections and resets stay in the record. A clean history is not the goal; a true one is.")
    ]));
  };

  /* which view each stage opens */
  var VIEW_OF = {
    geometry: "cad",
    takeoff: "takeoff",
    loads: "jurisdiction",
    calcs: "sizing",
    bom: "bom",
    "package": "planset"
  };
  FM.STAGE_VIEW = VIEW_OF;
})();

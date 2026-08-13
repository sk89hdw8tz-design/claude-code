/* ============================================================
   calc-spec §8 — the 24 scope boundaries, verbatim.

   §8 opens: "The app must print this list, verbatim and unabridged,
   on every output. A calculation that does not state its boundaries
   is not an engineering deliverable."

   What shipped instead was a ten-item paraphrase on the sheet view,
   and the schedule had no export at all — so every honesty mechanism
   in the product died at the browser window. This file is generated
   from calc-spec.md by test/extract-scope.js; the extraction is
   re-run and diffed by the test suite, so the two cannot drift.
   ============================================================ */

(function () {
  "use strict";

  FM.scope = {
    source: "calc-spec.md §8",
    preamble: "The app must print this list, verbatim and unabridged, on every output. A calculation that does not state its boundaries is not an engineering deliverable.",
    items: [
          {
                "n": 1,
                "group": "Structural configuration",
                "text": "Multi-span and continuous members. Only simply-supported single spans. No two-span, three-span, or continuous-over-support conditions; no moment redistribution; no negative moment at interior supports."
          },
          {
                "n": 2,
                "group": "Structural configuration",
                "text": "Cantilevers, including back-span/overhang combinations. The Table 3.3.3 cantilever l_e rows are deliberately not selectable."
          },
          {
                "n": 3,
                "group": "Structural configuration",
                "text": "Non-uniform loading. No concentrated loads, no partial-span loads, no triangular or trapezoidal distributions, no pattern loading. Uniform full-span load only."
          },
          {
                "n": 4,
                "group": "Structural configuration",
                "text": "Non-prismatic members — tapered, curved, or pitched-and-tapered glulam. C_c and C_I are held at 1.0 and no tapered-section stress-interaction check is performed."
          },
          {
                "n": 5,
                "group": "Structural configuration",
                "text": "Sloped-member axial thrust, rafter-tie/collar-tie action, and horizontal thrust at bearings. Spans are horizontal projections; axial force in the rafter is not computed."
          },
          {
                "n": 6,
                "group": "Structural configuration",
                "text": "Built-up and composite members — multi-ply nailed or bolted beams, flitch beams, ply-to-ply load sharing, and the NDS 15.3 spaced-column / built-up-column provisions."
          },
          {
                "n": 7,
                "group": "Member modifications",
                "text": "Notches of any kind (NDS §3.4.3.2, §3.2.3). A notched member's shear capacity is governed by a different equation and this app does not implement it."
          },
          {
                "n": 8,
                "group": "Member modifications",
                "text": "Holes and penetrations — round, square, or slotted; web holes; utility penetrations. NDS has no general design method for these; the app must refuse rather than approximate."
          },
          {
                "n": 9,
                "group": "Member modifications",
                "text": "Camber. No camber is calculated, specified, or credited against deflection."
          },
          {
                "n": 10,
                "group": "Loads and load effects",
                "text": "LRFD. ASD only. The φ, λ, and K_F format-conversion apparatus of NDS Appendix N is not implemented."
          },
          {
                "n": 11,
                "group": "Loads and load effects",
                "text": "Lateral loads — wind and seismic. No C_D = 1.6 combinations, no 0.6D + 0.6W, no 0.6D + 0.7E, no uplift, no net-uplift reversal on the member, no combined bending + axial from lateral drift."
          },
          {
                "n": 12,
                "group": "Loads and load effects",
                "text": "Rain load R and ponding (NDS §3.3.2 requires a positive-drainage / stiffness check against progressive deflection). Neither the R combination nor the ponding stability check is implemented."
          },
          {
                "n": 13,
                "group": "Loads and load effects",
                "text": "Live load reduction per IBC 1607.11 / ASCE 7 §4.7 and roof-live reduction per ASCE 7 §4.8. Enter unreduced psf values; no reduction is applied."
          },
          {
                "n": 14,
                "group": "Loads and load effects",
                "text": "Drift, sliding, unbalanced, and rain-on-snow snow loads (ASCE 7 Ch. 7). Enter a single uniform q_S."
          },
          {
                "n": 15,
                "group": "Loads and load effects",
                "text": "Impact and vibration. No impact factor is applied, and no floor-vibration check is performed. A floor joist that passes ℓ/360 can still be objectionably bouncy; that is a separate serviceability criterion (TR-12, or a proprietary manufacturer method) and it is not implemented here."
          },
          {
                "n": 16,
                "group": "Loads and load effects",
                "text": "Fire design. No char-rate calculation, no NDS Chapter 16 reduced-section method, no fire-resistance rating."
          },
          {
                "n": 17,
                "group": "Materials and environment",
                "text": "Connections of every kind — hangers, straps, bolts, screws, nails, hold-downs, bearing plates as designed elements, and the group-action / row-tear-out provisions of NDS Ch. 11–13. Bearing is checked as f_c⊥ on wood only."
          },
          {
                "n": 18,
                "group": "Materials and environment",
                "text": "Interaction of wet service with pressure-preservative treatment and fire-retardant treatment. The app applies C_M and C_i as independent multipliers per NDS. It does not model FRT-specific strength reductions, which are proprietary to the treater's evaluation report and are not in the material repo. If FRT is selected, the app must refuse and direct the user to the treater's report."
          },
          {
                "n": 19,
                "group": "Materials and environment",
                "text": "Species and grades outside NDS-S Tables 4A, 4B, and 5A — MSR/MEL (Table 4C), decking (Table 4E), non-North-American species (Table 4F), timbers (Table 4D), SCL, I-joists, CLT, and mass plywood. The repo has data for most of these; this spec does not cover their design equations."
          },
          {
                "n": 20,
                "group": "Materials and environment",
                "text": "Bi-axial bending and combined bending + axial (NDS §3.9). C_P is specified in §4.10 for completeness but no interaction equation is evaluated."
          },
          {
                "n": 21,
                "group": "Materials and environment",
                "text": "Deformation-limited F_c⊥. NDS permits a reduced F_c⊥ where a 0.02 in deformation limit is required rather than the 0.04 in basis of the tabulated value. Not implemented."
          },
          {
                "n": 22,
                "group": "Materials and environment",
                "text": "Creep beyond the optional IBC D/2 + L footnote (§5.5). No long-term creep factor K_cr per NDS §3.5.2 is applied to the total-load deflection."
          },
          {
                "n": 23,
                "group": "Process",
                "text": "This is a member check, not a design. It does not select sections, iterate, or optimize."
          },
          {
                "n": 24,
                "group": "Process",
                "text": "Output is not sealed engineering. A licensed engineer must review the inputs, assumptions, and results and take professional responsibility for them."
          }
    ]
  };

  /* ---------------- the one renderer ----------------

     The schedule export and the calc record both have to carry §8, and
     they used to carry it separately: the schedule printed all 24 from
     FM.scope.items, and the calc record printed a 13-item paraphrase of
     FM.engine.LIMITS on a single line — missing item 17, which is the
     one that says the bearing check the calc record publishes is NOT a
     connection design. Closing §8 in one output and not the other is
     how a scope list stops being a scope boundary, so there is now one
     implementation and both outputs call it.

     Takes an emit callback rather than returning a string so a caller
     can interleave it with its own line buffer at any indent. */

  function wrap(text, width) {
    var words = String(text).split(/\s+/), lines = [], line = "";
    width = width || 70;
    for (var i = 0; i < words.length; i++) {
      if (line && (line + " " + words[i]).length > width) { lines.push(line); line = ""; }
      line = line ? line + " " + words[i] : words[i];
    }
    if (line) lines.push(line);
    return lines;
  }
  function lpad(s, n) { s = String(s); while (s.length < n) s = " " + s; return s; }

  /* opts.heading lets a caller supply its own section banner — the schedule
     rules its headings with '=' lines, the calc record does not — without
     either caller owning a second copy of the list itself. */
  function render(emit, opts) {
    opts = opts || {};
    var heading = opts.heading || function (t) { emit(""); emit(t); emit(""); };

    /* engine.LIMITS is the check's own list. It is NOT a summary of §8 and does
       not stand in for it — both are printed, labelled, in that order. */
    var lim = opts.limits === false ? null
            : (opts.limits || (FM.engine && FM.engine.LIMITS));
    if (lim && lim.length) {
      heading("ENGINE LIMITS — " + lim.length + " ITEM(S), AS engine.js DECLARES THEM");
      emit("  Printed from FM.engine.LIMITS, the check's own list. This is not a summary");
      emit("  of the calc-spec §8 boundaries below and does not replace them — read both.");
      emit("");
      lim.forEach(function (t, i) {
        var lines = wrap(String(t), 70);
        emit("  " + lpad(i + 1, 3) + ". " + lines[0]);
        lines.slice(1).forEach(function (x) { emit("       " + x); });
      });
    }

    heading("SCOPE BOUNDARIES — calc-spec §8, VERBATIM AND UNABRIDGED");
    wrap(FM.scope.preamble, 76).forEach(emit);
    emit("");
    var group = null;
    FM.scope.items.forEach(function (it) {
      if (it.group !== group) { group = it.group; emit(""); emit("  " + group.toUpperCase()); emit(""); }
      var lines = wrap(it.text, 70);
      emit("  " + lpad(it.n, 3) + ". " + lines[0]);
      lines.slice(1).forEach(function (x) { emit("       " + x); });
    });
    emit("");
    emit("  Source: " + FM.scope.source + ". Reproduced in full, not paraphrased.");
  }

  FM.scope.render = render;
  FM.scope.wrap = wrap;
})();

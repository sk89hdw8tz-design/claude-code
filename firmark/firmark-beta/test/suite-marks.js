/* ============================================================
   suite-marks.js — invariants over the MARK DATA itself.

   WHY THIS FILE EXISTS

   A ten-person review panel (five structural PEs, five architects) was
   asked whether three garage headers should have their span raised or
   their bearing lowered. Round one voted 10-0 for one of them. Round two
   withdrew it: the question was unanswerable as posed, because the
   defect was not in three numbers, it was in the SCHEMA.

   `span` was the stored field and the rough opening was DERIVED from it
   as span − 2 × bearing. So the hole a customer's door goes through was
   a function of the jack count. An engineer changing bearing on a
   reaction check silently moved the door — and cad.js drew the result,
   so it reached the framing plan and the DXF.

   Three garage doors came out 3 in narrower than the door their own note
   named. A 9'-0" door does not enter an 8'-11" opening.

   The fix was to invert the dependency: the rough opening is the
   architectural fact, declared; the span is its structural consequence.
   These assertions hold that inversion in place. Fixing the three marks
   without them fixes the instances and leaves the class open, which is
   what the panel said in almost exactly those words.
   ============================================================ */

module.exports = function (t, FM) {

  var W = FM.weights;

  /* Every mark that declares BOTH a rough opening and a bearing must have
     a span that follows from them. This is the assertion whose absence let
     span and bearing be authored by two different methods with nothing
     cross-checking them. */
  t.suite("marks · a declared rough opening determines the span");
  (function () {
    var checked = 0, bad = [];
    W.PLANS.forEach(function (pl) {
      (pl.marks || []).forEach(function (mk) {
        var ro = mk.roFt;
        if (ro === undefined && mk.opening) ro = mk.opening.roFt;
        if (typeof ro !== "number") return;
        if (typeof mk.bearing !== "number" || typeof mk.span !== "number") return;
        checked++;
        /* 1e-3 ft is 0.012 in. Spans are authored as decimal feet and round
           (3'-2" is 3.1667, not 3.166666…), so an exact comparison fails on
           the rounding rather than on a defect. The error this guards
           against is three INCHES — 0.25 ft — so the tolerance is two
           orders of magnitude tighter than the thing it must catch. */
        var want = ro + 2 * mk.bearing / 12;
        if (Math.abs(mk.span - want) > 1e-3) {
          bad.push(pl.id + "/" + mk.id + ": rough opening " + ro + " ft + " + mk.bearing +
                   " in of bearing at each end = " + want.toFixed(4) +
                   " ft, but the mark declares span " + mk.span);
        }
      });
    });
    t.truthy(checked >= 5,
             "the five door headers with a bearing declare a rough opening — found " + checked);
    t.eq(bad.join(" | "), "",
         "every declared rough opening ties to its span through the declared bearing");
  })();

  /* A sectional overhead door is framed at its NOMINAL size — the track and
     jambs mount inside the opening. "Door + 2 in" is the pre-hung SWING-door
     allowance, and applying it to a sectional door is what drew every garage
     opening in the catalogue wrong. Four reviewers reached this
     independently; the architects' vote carried it 4-1.

     The rough openings below are whole feet on purpose. If a future mark
     declares a garage rough opening that is not the nominal door size, it is
     either a different product or the swing-door rule creeping back. */
  t.suite("marks · sectional garage doors are framed at nominal size");
  (function () {
    var found = 0, bad = [];
    W.PLANS.forEach(function (pl) {
      (pl.marks || []).forEach(function (mk) {
        if (!/GAR/.test(mk.id)) return;
        var ro = mk.roFt;
        if (ro === undefined && mk.opening) ro = mk.opening.roFt;
        if (typeof ro !== "number") return;
        found++;
        if (Math.abs(ro - Math.round(ro)) > 1e-6) {
          bad.push(pl.id + "/" + mk.id + " rough opening " + ro +
                   " ft is not a nominal door size — swing-door allowance creeping back?");
        }
      });
    });
    t.truthy(found >= 4, "all four garage door marks declare a rough opening — found " + found);
    t.eq(bad.join(" | "), "", "each is the nominal door size, in whole feet");
  })();

  /* The one mark that legitimately carries the +2 in allowance, asserted so
     nobody "fixes" it to match the garage doors. A 3'-0" pre-hung swing door
     really does take a 3'-2" rough opening. The rule is per door TYPE, not
     per project. */
  t.suite("marks · a pre-hung swing door keeps its +2 in allowance");
  (function () {
    var pl = W.planById("starter-1210");
    var ent = (pl.marks || []).filter(function (m) { return m.id === "HDR-ENT"; })[0];
    t.truthy(!!ent, "starter-1210 declares HDR-ENT");
    t.near(ent.opening.roFt, 3 + 2 / 12, 1e-4,
           "a 3'-0\" pre-hung swing door is framed at 3'-2\" — door plus two inches");
    t.near(ent.span, ent.opening.roFt + 2 * ent.bearing / 12, 1e-3,
           "and its span follows the same rule as every other mark");
  })();

  /* An area with no stated measurement standard cannot be reconciled or
     reviewed. Gross framed area and ANSI Z765 finished area are different
     measurements of the same house, and the catalogue carried FOUR field
     names — sfPerUnit, grossSfPerFloor, underRoofSf, conditionedSf — with
     no plan saying what any of them measured.

     That is how coastal-duplex-1600's 64 sf sat unexplained: 26 x 32 x 2 is
     1,664 gross against a declared 1,600, and with no standard on the field
     there was no way to tell whether that was an error or two correct
     numbers measured differently. The architects' vote was unanimous — name
     the standard rather than restate the number or invent a deduction. */
  t.suite("marks · every declared area says what it measures");
  (function () {
    var AREA_FIELDS = ["sfPerUnit", "grossSfPerFloor", "underRoofSf", "conditionedSf"];
    var unlabelled = [];
    W.PLANS.forEach(function (pl) {
      var g = pl.geometry || {};
      var basis = g.areaBasis || {};
      AREA_FIELDS.forEach(function (f) {
        if (typeof g[f] !== "number") return;
        var b = basis[f];
        if (typeof b !== "string" || b.length < 20) {
          unlabelled.push(pl.id + "." + f);
        }
      });
    });
    t.eq(unlabelled.join(", "), "",
         "no plan declares a square footage without stating the standard it was measured under");

    /* The one that does not reconcile must SAY it does not reconcile. */
    var cd = W.planById("coastal-duplex-1600");
    var cdb = (cd.geometry.areaBasis || {}).sfPerUnit || "";
    t.truthy(cdb.indexOf("1,664") !== -1 && cdb.indexOf("64 sf") !== -1,
             "coastal-duplex-1600 states the gross it does not match and the size of the gap");
    t.truthy(/NOT DECLARED|STANDARD NOT DECLARED/.test(cdb),
             "and says outright that its standard is undeclared rather than implying one");
  })();

  /* The drawn opening must be the DECLARED one. This is the assertion that
     would have caught the original defect: it compares what cad.js puts on
     the drawing against what the plan says the door is, with no reference to
     span at all. */
  t.suite("marks · the drawn opening is the declared opening");
  (function () {
    if (!FM.cad || typeof FM.cad.fromPlan !== "function") {
      t.truthy(false, "cad.js is loadable");
      return;
    }
    var bad = [], drawn = 0;
    W.PLANS.forEach(function (pl) {
      var m;
      try { m = FM.cad.fromPlan(pl.id); } catch (e) { return; }
      if (!m || !m.levels) return;
      m.levels.forEach(function (lv) {
        (lv.openings || []).forEach(function (o) {
          var mk = (pl.marks || []).filter(function (x) { return x.id === o.markId; })[0];
          if (!mk) return;
          var ro = mk.roFt;
          if (ro === undefined && mk.opening) ro = mk.opening.roFt;
          if (typeof ro !== "number") return;
          drawn++;
          if (Math.abs(o.widthFt - ro) > 1e-3) {
            bad.push(pl.id + "/" + mk.id + ": plan declares a " + ro +
                     " ft opening, the drawing shows " + o.widthFt);
          }
        });
      });
    });
    t.truthy(drawn >= 3, "at least three declared openings reach a drawing — found " + drawn);
    t.eq(bad.join(" | "), "",
         "no drawn opening differs from the rough opening its plan declares");
  })();
};

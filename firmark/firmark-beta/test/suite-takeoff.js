/* ============================================================
   suite-takeoff.js — FM.takeoff · geometry -> structural demands

   Exported as module.exports = function (t, FM) { ... } so it can be
   mounted from test/run-tests.js without this file and that one being
   edited by two people at once.

   What is being defended here, in order of how much it would cost to get
   wrong:

     1. The arithmetic. One fixture is small enough to compute entirely by
        hand, and the hand computation is written out in the comments. If
        the module and the comment ever disagree, one of them is a bug and
        the reviewer can see which.
     2. The refusals. A region with one support, an opening in a
        non-bearing wall, a multi-span region, a cantilever, a partial
        load, an interior wall framed on one side — each must produce an
        unresolved entry and NOT a mark. A guessed tributary is the defect
        this module exists to prevent.
     3. The round trip. Every mark must be a mark FM.solver.solvePlan
        already consumes, for every plan, with no throw.
     4. The invariant that makes derivations trustworthy: every field of
        every mark, on every fixture, has exactly one derivations entry.
   ============================================================ */

"use strict";

module.exports = function (t, FM) {

  /* ---------------------------------------------------------------
     fixture helpers — the FM.cad model shape from ARCHITECTURE.md
     --------------------------------------------------------------- */

  function wall(id, x1, y1, x2, y2, bearing, exterior, thicknessIn) {
    return {
      id: id, x1: x1, y1: y1, x2: x2, y2: y2,
      exterior: !!exterior, bearing: !!bearing,
      heightFt: 9.0, thicknessIn: thicknessIn === undefined ? 5.5 : thicknessIn, note: ""
    };
  }
  function box(x0, y0, x1, y1) { return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]; }
  function region(id, poly, kind, dirDeg, spacingIn, bearsOn) {
    return { id: id, polygon: poly, kind: kind, directionDeg: dirDeg,
             spacingIn: spacingIn, bearsOn: bearsOn, note: "" };
  }
  function opening(id, wallId, offsetFt, widthFt, headHeightFt, kind) {
    return { id: id, wallId: wallId, offsetFt: offsetFt, widthFt: widthFt,
             headHeightFt: headHeightFt, kind: kind || "window", note: "" };
  }
  function level(id, label, walls, openings, framing) {
    return { id: id, label: label, topPlateFt: 9.0,
             walls: walls, openings: openings || [], framing: framing || [] };
  }
  function model(name, levels) {
    return { version: (FM.cad && FM.cad.MODEL_VERSION) || 1, name: name, levels: levels };
  }

  function markOf(res, id) {
    return res.marks.filter(function (m) { return m.id === id; })[0] || null;
  }
  function derivOf(res, id, field) {
    return res.derivations.filter(function (d) {
      return d.markId === id && d.field === field;
    })[0] || null;
  }
  function unresolvedMentioning(res, idOrText) {
    return res.unresolved.filter(function (u) {
      return (u.refs || []).indexOf(idOrText) !== -1 ||
             u.what.indexOf(idOrText) !== -1;
    });
  }
  function warningMentioning(res, idOrText) {
    return res.warnings.filter(function (w) {
      return (w.refs || []).indexOf(idOrText) !== -1 || w.text.indexOf(idOrText) !== -1;
    });
  }

  /* ===============================================================
     1. THE HAND FIXTURE

     A 30 ft x 20 ft rectangle. Wall centrelines on the rectangle, all
     walls 5.5 in thick. The two 30 ft walls (W-S at y = 0, W-N at
     y = 20) are bearing; the two 20 ft walls are not. One floor region
     fills the rectangle with the joists running in +y (directionDeg 90)
     at 16 in o.c. One 6.00 ft opening in W-S, 4.00 ft from its start.

     BY HAND:

       wall thickness   5.5 in            = 0.458333 ft
       half thickness   5.5 / 2 = 2.75 in = 0.229167 ft

       SPAN (clear, face to face, along the joist direction)
         centreline to centreline  20.000000 ft
         less half of W-S          -0.229167
         less half of W-N          -0.229167
         =                         19.541667 ft

       RUN (across the joists, along the bearing walls)
         30.000000 ft  (the region's own extent; the walls run the same)

       COUNT
         ceil(30 x 12 / 16) + 1 = ceil(22.5) + 1 = 23 + 1 = 24 pieces

       HEADER at O-1, clear opening 6.00 ft
         span      = the clear opening                     =  6.000000 ft
         tributary = half the joist span, one side only
                     (W-S is exterior, nothing outboard)
                   = 19.541667 / 2                         =  9.770833 ft
         bearing   = 6.00 ft is NOT under 6 ft -> 2 jacks
                     2 x 1.5 in                            =  3.0 in
         carries   = "floor", from the framing KIND, not the role
         head      = 6.83 ft x 12                          = 81.96 in
     =============================================================== */

  var HAND = model("Hand fixture 30x20", [
    level("L1", "First floor",
      [ wall("W-S", 0, 0, 30, 0, true, true),
        wall("W-N", 0, 20, 30, 20, true, true),
        wall("W-W", 0, 0, 0, 20, false, true),
        wall("W-E", 30, 0, 30, 20, false, true) ],
      [ opening("O-1", "W-S", 4.0, 6.0, 6.83, "slider") ],
      [ region("F-1", box(0, 0, 30, 20), "floor", 90, 16, ["W-S", "W-N"]) ])
  ]);

  t.suite("takeoff · the hand fixture, every number computed by hand above");
  var hand = FM.takeoff.run(HAND);

  t.eq(hand.marks.length, 2, "one framing mark and one header mark, nothing else");
  t.eq(hand.unresolved.length, 0, "nothing unresolved — this geometry determines everything");

  var FJ = markOf(hand, "FJ-F-1");
  t.truthy(FJ, "the floor region became mark FJ-F-1, named after the region it came from");
  t.near(FJ.span, 19.541667, 1e-6, "span 19.541667 ft = 20.0 centre-to-centre less 2.75 in each side");
  t.near(FJ.runFt, 30, 1e-9, "runFt 30.0 ft measured across the joists");
  t.eq(FJ.count, 24, "count 24 = ceil(30 x 12 / 16) + 1");
  t.eq(FJ.spacingIn, 16, "spacing 16 in o.c. read off the region");
  t.eq(FJ.role, "joist", "kind floor -> role joist");
  t.eq(FJ.carries, "floor", "carries floor, read from the KIND and declared on the mark");
  t.eq(FJ.skuGroup, "floor", "sku group floor");

  var HDR = markOf(hand, "HDR-O-1");
  t.truthy(HDR, "the opening in the bearing wall became mark HDR-O-1");
  t.eq(HDR.role, "header", "role header");
  t.near(HDR.span, 6.0, 1e-9, "header span 6.00 ft = the clear opening between jacks");
  t.near(HDR.trib, 9.770833, 1e-6, "tributary 9.770833 ft = half the 19.541667 ft joist span");
  t.eq(HDR.bearing, 3.0, "bearing 3.0 in = 2 jacks x 1.5 in (6.00 ft opening is in the under-12 band)");
  t.eq(HDR.carries, "floor", "header carries floor — from the framing kind landing on the wall");
  t.eq(HDR.count, 1, "one opening, one header");
  t.near(HDR.headHeightIn, 81.96, 1e-9, "head height 6.83 ft x 12 = 81.96 in");
  t.eq(HDR.wallPosition, "exterior-first-floor",
       "wallPosition declared: exterior wall on the lowest level, so a block market removes it");
  t.eq(HDR.braced, true, "braced declared true (restrained by the wall framing), not left to default");

  /* the arithmetic has to be legible in the derivation, not just correct */
  var dSpan = derivOf(hand, "FJ-F-1", "span");
  t.truthy(dSpan && dSpan.fromIds.length === 2 &&
           dSpan.fromIds.indexOf("W-S") !== -1 && dSpan.fromIds.indexOf("W-N") !== -1,
           "the span derivation names both walls it was measured between");
  t.truthy(dSpan && dSpan.how.indexOf("19.542") !== -1 &&
           dSpan.how.indexOf("5.50 in / 2 = 0.229 ft") !== -1,
           "and shows the arithmetic: centreline distance less half of each wall thickness");
  t.truthy(dSpan && dSpan.how.indexOf("centre-to-centre") !== -1,
           "and prints the centre-to-centre alternative beside it rather than choosing it quietly");
  var dTrib = derivOf(hand, "HDR-O-1", "trib");
  t.truthy(dTrib && dTrib.fromIds.indexOf("F-1") !== -1,
           "the tributary derivation names the framing region it halved");
  t.truthy(dTrib && dTrib.how.indexOf("outboard") !== -1,
           "and says out loud why the other side contributes nothing (exterior wall)");
  var dBear = derivOf(hand, "HDR-O-1", "bearing");
  t.truthy(dBear && dBear.cls === "derived",
           "bearing is marked `derived` so a reviewer can challenge the jack rule");
  t.truthy(dBear && dBear.how.indexOf("IRC R602.7") !== -1,
           "and the jack rule states what it is NOT: a code table lookup");
  t.eq(derivOf(hand, "FJ-F-1", "spacingIn").cls, "user",
       "spacing is classed `user` — it was read off the drawing, not derived");

  /* ===============================================================
     2. REFUSALS — the half of the module that makes it trustworthy
     =============================================================== */

  t.suite("takeoff · a region bearing on ONE wall is unresolved, not halved");
  var ONE = model("One support", [
    level("L1", "First floor",
      [ wall("W-S", 0, 0, 30, 0, true, true),
        wall("W-E", 30, 0, 30, 20, false, true) ],
      [ opening("O-1", "W-S", 4.0, 6.0, 6.83, "slider") ],
      [ region("F-1", box(0, 0, 30, 20), "floor", 90, 16, ["W-S"]) ])
  ]);
  var one = FM.takeoff.run(ONE);
  t.eq(one.marks.length, 0, "no mark is emitted for a region with one support");
  t.truthy(unresolvedMentioning(one, "F-1").length >= 1, "the region is named in unresolved");
  var u1 = unresolvedMentioning(one, "F-1")[0];
  t.truthy(u1.why.indexOf("invented") !== -1 || u1.why.indexOf("undetermined") !== -1,
           "the reason says the second support is undetermined, not that the span is 'about' anything");
  t.truthy(u1.need.length > 20, "and it says precisely what a human must supply");
  t.truthy(unresolvedMentioning(one, "O-1").length >= 1,
           "the header over the opening in that wall is refused too — an undetermined region " +
           "poisons every support it lands on, rather than being quietly left out of the tributary");
  t.eq(one.marks.filter(function (m) { return m.role === "header"; }).length, 0,
       "and no header mark is emitted on a guessed tributary");

  t.suite("takeoff · an opening in a NON-BEARING wall makes no header, with a stated reason");
  var NB = model("Non-bearing opening", [
    level("L1", "First floor",
      [ wall("W-S", 0, 0, 30, 0, true, true),
        wall("W-N", 0, 20, 30, 20, true, true),
        wall("W-W", 0, 0, 0, 20, false, true),
        wall("W-E", 30, 0, 30, 20, false, true) ],
      [ opening("O-G", "W-E", 6.0, 4.0, 6.83, "window") ],
      [ region("F-1", box(0, 0, 30, 20), "floor", 90, 16, ["W-S", "W-N"]) ])
  ]);
  var nb = FM.takeoff.run(NB);
  t.eq(nb.marks.filter(function (m) { return m.role === "header"; }).length, 0,
       "no header mark for an opening in a wall declared bearing:false");
  var wNb = warningMentioning(nb, "O-G");
  t.truthy(wNb.length >= 1, "and the reason is stated in warnings, not left as silence");
  t.truthy(wNb[0].text.indexOf("bearing:false") !== -1,
           "the reason names the wall flag that decided it");
  t.truthy(wNb[0].text.indexOf("still required") !== -1,
           "and does NOT claim the opening needs no header — only that this engine sizes none");

  t.suite("takeoff · a header carrying only a WALL above is refused the way weights.js refuses it");
  var TWO_ST = model("Wall over a non-bearing wall", [
    level("L1", "First floor",
      [ wall("W-S", 0, 0, 30, 0, false, true),
        wall("W-N", 0, 20, 30, 20, true, true),
        wall("W-W", 0, 0, 0, 20, true, true),
        wall("W-E", 30, 0, 30, 20, true, true) ],
      [ opening("O-GAR", "W-S", 8.0, 9.0, 7.0, "garage") ],
      []),
    level("L2", "Second floor",
      [ wall("W2-S", 0, 0, 30, 0, false, true),
        wall("W2-W", 0, 0, 0, 20, true, true),
        wall("W2-E", 30, 0, 30, 20, true, true) ],
      [],
      [ region("F2-1", box(0, 0, 30, 20), "floor", 0, 16, ["W-W", "W-E"]) ])
  ]);
  var two = FM.takeoff.run(TWO_ST);
  t.eq(two.marks.filter(function (m) { return m.role === "header"; }).length, 0,
       "no header mark over the garage door in the non-bearing front wall");
  var uWall = unresolvedMentioning(two, "O-GAR");
  t.truthy(uWall.length >= 1, "it is unresolved, not merely warned about — a real member is unsized");
  t.truthy(uWall[0].why.indexOf("wall dead load") !== -1,
           "and the reason is the one weights.js gives: ASSEMBLY{} has no wall dead load (§L6)");
  t.truthy(two.marks.filter(function (m) { return m.id === "L2-FJ-F2-1"; }).length === 1,
           "the second-floor joists that DO bear on walls a level below are still taken off");

  t.suite("takeoff · refusals that are about the engine's own scope");
  (function () {
    /* three bearing lines across one region = multi-span, calc-spec §8.1 */
    var MS = model("Multi-span", [
      level("L1", "First floor",
        [ wall("W-S", 0, 0, 30, 0, true, true),
          wall("W-C", 0, 10, 30, 10, true, false),
          wall("W-N", 0, 20, 30, 20, true, true) ],
        [], [ region("F-1", box(0, 0, 30, 20), "floor", 90, 16, ["W-S", "W-C", "W-N"]) ])
    ]);
    var ms = FM.takeoff.run(MS);
    t.eq(ms.marks.length, 0, "a region crossing three bearing lines produces no mark");
    t.truthy(unresolvedMentioning(ms, "F-1")[0].why.indexOf("8.1") !== -1,
             "and cites calc-spec §8.1 — simply-supported single spans only");

    /* framing running past the outside face of its support = cantilever, §8.2 */
    var CA = model("Cantilever", [
      level("L1", "First floor",
        [ wall("W-S", 0, 0, 30, 0, true, true),
          wall("W-N", 0, 20, 30, 20, true, true) ],
        [], [ region("F-1", box(0, 0, 30, 23), "floor", 90, 16, ["W-S", "W-N"]) ])
    ]);
    var ca = FM.takeoff.run(CA);
    t.eq(ca.marks.length, 0, "a region running 3 ft past its support produces no mark");
    t.truthy(unresolvedMentioning(ca, "F-1")[0].why.indexOf("8.2") !== -1,
             "and cites calc-spec §8.2 — cantilevers excluded outright");

    /* framing over only part of an opening = partial-span load, §8.3 */
    var PA = model("Partial load", [
      level("L1", "First floor",
        [ wall("W-S", 0, 0, 30, 0, true, true),
          wall("W-N", 0, 20, 30, 20, true, true) ],
        [ opening("O-1", "W-S", 8.0, 6.0, 6.83, "slider") ],
        [ region("F-1", box(0, 0, 10, 20), "floor", 90, 16, ["W-S", "W-N"]) ])
    ]);
    var pa = FM.takeoff.run(PA);
    t.eq(pa.marks.filter(function (m) { return m.role === "header"; }).length, 0,
         "an opening only partly covered by the framing above it produces no header");
    t.truthy(unresolvedMentioning(pa, "O-1")[0].why.indexOf("8.3") !== -1,
             "and cites calc-spec §8.3 — uniform full-span load only");

    /* an interior bearing wall framed on one side only */
    var IN = model("Interior one side", [
      level("L1", "First floor",
        [ wall("W-S", 0, 0, 30, 0, true, true),
          wall("W-C", 0, 20, 30, 20, true, false),
          wall("W-N", 0, 40, 30, 40, true, true) ],
        [ opening("O-1", "W-C", 8.0, 6.0, 6.83, "door") ],
        [ region("F-1", box(0, 0, 30, 20), "floor", 90, 16, ["W-S", "W-C"]) ])
    ]);
    var inn = FM.takeoff.run(IN);
    t.eq(inn.marks.filter(function (m) { return m.role === "header"; }).length, 0,
         "an INTERIOR wall framed on one side only gets no header");
    t.truthy(unresolvedMentioning(inn, "O-1")[0].why.indexOf("inside the building") !== -1,
             "because the other side of an interior wall is inside the building — something frames there");

    /* the same wall declared exterior IS determined, and says why */
    var EX = model("Exterior one side", [
      level("L1", "First floor",
        [ wall("W-S", 0, 0, 30, 0, true, true),
          wall("W-N", 0, 20, 30, 20, true, true) ],
        [ opening("O-1", "W-N", 8.0, 6.0, 6.83, "door") ],
        [ region("F-1", box(0, 0, 30, 20), "floor", 90, 16, ["W-S", "W-N"]) ])
    ]);
    var ex = FM.takeoff.run(EX);
    t.eq(ex.marks.filter(function (m) { return m.role === "header"; }).length, 1,
         "the same one-sided condition on an EXTERIOR wall is determined and does produce a header");
  })();

  t.suite("takeoff · carries comes from the framing KIND, never from the role string");
  (function () {
    /* This is the defect weights.js documents at CARRIES_DEFAULT: a deck
       beam checked as a roof beam printed 4x8 at 59% for a member
       overstressed at 1.05. A deck region must carry "deck". */
    var DK = model("Deck", [
      level("L1", "First floor",
        [ wall("W-S", 0, 0, 20, 0, true, true),
          wall("W-N", 0, 12, 20, 12, true, true) ],
        [], [ region("D-1", box(0, 0, 20, 12), "deck", 90, 16, ["W-S", "W-N"]) ])
    ]);
    var dk = FM.takeoff.run(DK);
    var m = markOf(dk, "DK-D-1");
    t.truthy(m, "a deck region becomes a deck mark");
    t.eq(m.carries, "deck", "and it carries DECK — not roof, not floor");
    t.eq(m.role, "deck", "role deck");
    t.eq(m.exposure, "exterior", "exposure exterior, which drives wet service and treatment");
    t.truthy(derivOf(dk, "DK-D-1", "carries").how.indexOf("never from the role string") !== -1,
             "and the derivation states the rule, because this is the failure mode that shipped once");

    var RF = model("Roof", [
      level("L1", "First floor",
        [ wall("W-S", 0, 0, 46, 0, true, true),
          wall("W-N", 0, 32, 46, 32, true, true) ],
        [], [ region("R-1", box(0, 0, 46, 32), "roof", 90, 24, ["W-S", "W-N"]) ])
    ]);
    var rf = FM.takeoff.run(RF);
    t.eq(markOf(rf, "RF-R-1").carries, "roof", "a roof region carries roof");
    t.eq(markOf(rf, "RF-R-1").role, "rafter", "kind roof -> role rafter");
    t.truthy(warningMentioning(rf, "RF-R-1").filter(function (w) {
      return w.kind === "roof-pitch-absent";
    }).length === 1, "and the horizontal-projection limitation is stated: the model has no pitch");
  })();

  t.suite("takeoff · a header landing on a post publishes its reaction instead of dropping it");
  (function () {
    /* the opening runs to the very end of the wall, so the header's bearing
       is a post / king-stud pack at the corner, not wall */
    var PS = model("Post end", [
      level("L1", "First floor",
        [ wall("W-S", 0, 0, 30, 0, true, true),
          wall("W-N", 0, 20, 30, 20, true, true) ],
        [ opening("O-1", "W-S", 0, 9.0, 7.0, "garage") ],
        [ region("F-1", box(0, 0, 30, 20), "roof", 90, 24, ["W-S", "W-N"]) ])
    ]);
    var ps = FM.takeoff.run(PS);
    var post = markOf(ps, "PST-HDR-O-1");
    t.truthy(post, "a post mark is emitted where the header lands on a post");
    t.eq(post.component, true, "flagged component so the member search removes it rather than failing it");
    t.eq(post.reactionFrom[0], "HDR-O-1",
         "and it names the header whose reaction is its design load, resolved live by solvePlan");
    t.truthy(post.componentNote.indexOf("8.20") !== -1,
             "the note cites §8.20 — no interaction equation is evaluated here");
    t.truthy(FM.weights.applicability(post, FM.weights.PACKS[0]).applicable === false,
             "weights.applicability agrees it is out of scope, so solvePlan never sizes it");
  })();

  /* ===============================================================
     3. THE FIVE PLANS — round trip

     FM.cad.fromPlan is built in parallel by the CAD agent. If it is
     present the round trip runs on ITS geometry; if it is not, the same
     round trip runs on equivalent fixture models built here from each
     plan's own stated `geometry` block, so this suite is never blocked
     and never silently skipped.
     =============================================================== */

  function planFixture(planId) {
    if (planId === "sunbelt-ranch-1850") {
      /* 50 x 46, common trusses clear-span the 46 ft depth onto the two
         50 ft walls, 24 in o.c.; 14 ft lanai off the rear wall standing
         on posts — which this geometry model cannot express, so it is a
         refusal, not a mark. */
      return model("Sunbelt Ranch 1850", [
        level("L1", "First floor",
          [ wall("W-FRONT", 0, 0, 50, 0, true, true),
            wall("W-REAR", 0, 46, 50, 46, true, true),
            wall("W-LEFT", 0, 0, 0, 46, false, true),
            wall("W-RIGHT", 50, 0, 50, 46, false, true) ],
          [ opening("O-W1", "W-FRONT", 4, 3, 6.67, "window"),
            opening("O-W2", "W-FRONT", 12, 3, 6.67, "window"),
            opening("O-W3", "W-FRONT", 20, 3, 6.67, "window"),
            opening("O-GAR", "W-FRONT", 30, 16, 7.0, "garage"),
            opening("O-SLD", "W-REAR", 20, 12, 6.67, "slider") ],
          [ region("F-ROOF", box(0, 0, 50, 46), "roof", 90, 24, ["W-FRONT", "W-REAR"]),
            region("F-LANAI", box(0, 46, 50, 60), "roof", 90, 24, ["W-REAR"]) ])
      ]);
    }
    if (planId === "two-story-2450") {
      /* 40 x 38 first floor with a centre bearing line; second floor over
         part of it; a single-storey wing roof landing on the same
         first-floor rear wall the second floor bears on, which is the
         roof+floor header condition. */
      return model("Two-Story 2450", [
        level("L1", "First floor",
          [ wall("W1-FRONT", 0, 0, 40, 0, true, true),
            wall("W1-CTR", 0, 14, 40, 14, true, false),
            wall("W1-REAR", 0, 28.5, 40, 28.5, true, true),
            wall("W1-WING", 0, 38, 40, 38, true, true),
            wall("W1-LEFT", 0, 0, 0, 38, false, true),
            wall("W1-RIGHT", 40, 0, 40, 38, false, true) ],
          [ opening("O1-GB", "W1-CTR", 12, 10, 6.83, "door"),
            opening("O1-SLD", "W1-REAR", 16, 8, 6.83, "slider") ],
          [ region("F1-WING", box(0, 28.5, 40, 38), "roof", 90, 24, ["W1-REAR", "W1-WING"]) ]),
        level("L2", "Second floor",
          [ wall("W2-FRONT", 0, 0, 40, 0, true, true),
            wall("W2-REAR", 0, 28.5, 40, 28.5, true, true),
            wall("W2-LEFT", 0, 0, 0, 28.5, false, true),
            wall("W2-RIGHT", 40, 0, 40, 28.5, false, true) ],
          [ opening("O2-W", "W2-FRONT", 6, 4, 6.67, "window") ],
          [ region("F2-A", box(0, 0, 40, 14), "floor", 90, 16, ["W1-FRONT", "W1-CTR"]),
            region("F2-B", box(0, 14, 40, 28.5), "floor", 90, 16, ["W1-CTR", "W1-REAR"]),
            region("F2-ROOF", box(0, 0, 40, 28.5), "roof", 90, 24, ["W2-FRONT", "W2-REAR"]) ])
      ]);
    }
    if (planId === "coastal-duplex-1600") {
      /* 26 x 32 per unit, party wall and end wall bearing, one interior
         line 15.5 ft off the exterior wall on the second floor. */
      return model("Coastal Duplex 1600", [
        level("L1", "First floor",
          [ wall("W1-PARTY", 0, 0, 0, 32, true, false),
            wall("W1-END", 26, 0, 26, 32, true, true),
            wall("W1-LINE", 15.5, 0, 15.5, 32, true, false),
            wall("W1-FRONT", 0, 0, 26, 0, false, true),
            wall("W1-BACK", 0, 32, 26, 32, false, true) ],
          [ opening("O1-SLD", "W1-LINE", 10, 8, 6.83, "slider") ],
          []),
        level("L2", "Second floor",
          [ wall("W2-PARTY", 0, 0, 0, 32, true, false),
            wall("W2-END", 26, 0, 26, 32, true, true),
            wall("W2-FRONT", 0, 0, 26, 0, false, true),
            wall("W2-BACK", 0, 32, 26, 32, false, true) ],
          [ opening("O2-W", "W2-END", 8, 5, 6.67, "window") ],
          [ region("F2-A", box(0, 0, 15.5, 32), "floor", 0, 16, ["W1-PARTY", "W1-LINE"]),
            region("F2-B", box(15.5, 0, 26, 32), "floor", 0, 16, ["W1-LINE", "W1-END"]),
            region("F2-ROOF", box(0, 0, 26, 32), "roof", 0, 24, ["W2-PARTY", "W2-END"]) ])
      ]);
    }
    if (planId === "starter-1210") {
      /* 46 x 32 slab on grade, trusses clear-span the 32 ft depth onto the
         two 46 ft walls; the two 32 ft walls are gable ends and bear
         nothing, so an opening in one produces no header and says so. */
      return model("Starter 1210", [
        level("L1", "First floor",
          [ wall("W-FRONT", 0, 0, 46, 0, true, true),
            wall("W-REAR", 0, 32, 46, 32, true, true),
            wall("W-GBL-L", 0, 0, 0, 32, false, true),
            wall("W-GBL-R", 46, 0, 46, 32, false, true) ],
          [ opening("O-W1", "W-FRONT", 4, 4, 6.67, "window"),
            opening("O-W2", "W-FRONT", 12, 4, 6.67, "window"),
            opening("O-ENT", "W-FRONT", 20, 3.17, 6.67, "door"),
            opening("O-GAR", "W-FRONT", 30, 9.17, 7.0, "garage"),
            opening("O-SLD", "W-REAR", 20, 6.08, 6.67, "slider"),
            opening("O-GBL", "W-GBL-L", 12, 4, 6.67, "window") ],
          [ region("F-ROOF", box(0, 0, 46, 32), "roof", 90, 24, ["W-FRONT", "W-REAR"]) ])
      ]);
    }
    if (planId === "townhome-1220") {
      /* 20 x 36 interior unit. Both party walls bear; the front and rear
         walls carry nothing but wall, which is exactly why the garage door
         header is the mark weights.js refuses. */
      return model("Townhome 1220", [
        level("L1", "First floor",
          [ wall("T1-PL", 0, 0, 0, 36, true, false),
            wall("T1-PR", 20, 0, 20, 36, true, false),
            wall("T1-LINE", 11, 0, 11, 36, true, false),
            wall("T1-FRONT", 0, 0, 20, 0, false, true),
            wall("T1-REAR", 0, 36, 20, 36, false, true) ],
          [ opening("T-GAR", "T1-FRONT", 4, 9.17, 7.0, "garage") ],
          []),
        level("L2", "Second floor",
          [ wall("T2-PL", 0, 0, 0, 36, true, false),
            wall("T2-PR", 20, 0, 20, 36, true, false),
            wall("T2-FRONT", 0, 0, 20, 0, false, true),
            wall("T2-REAR", 0, 36, 20, 36, false, true) ],
          [ opening("T2-W", "T2-PL", 10, 4, 6.67, "window") ],
          [ region("T2-A", box(0, 0, 11, 36), "floor", 0, 16, ["T1-PL", "T1-LINE"]),
            region("T2-B", box(11, 0, 20, 36), "floor", 0, 16, ["T1-LINE", "T1-PR"]),
            region("T2-ROOF", box(0, 0, 20, 36), "roof", 0, 24, ["T2-PL", "T2-PR"]) ])
      ]);
    }
    return null;
  }

  var PLAN_IDS = FM.weights.PLANS.map(function (p) { return p.id; });
  var haveFromPlan = !!(FM.cad && typeof FM.cad.fromPlan === "function");

  t.suite("takeoff · round trip for every plan — geometry -> marks -> solver.solvePlan");
  t.truthy(true, haveFromPlan
    ? "FM.cad.fromPlan is present: the round trip runs on the CAD agent's own geometry"
    : "FM.cad.fromPlan is NOT present yet, so the round trip runs on equivalent fixture " +
      "models built in this suite from each plan's stated geometry block. Re-run once cad.js " +
      "lands to exercise the real path.");

  var pack = FM.weights.PACKS[0];
  var ROUND = [];
  PLAN_IDS.forEach(function (pid) {
    var m = null, src = "fixture";
    if (haveFromPlan) {
      try { m = FM.cad.fromPlan(pid); src = "FM.cad.fromPlan"; } catch (e) { m = null; }
    }
    if (!m) m = planFixture(pid);
    t.truthy(m, pid + " · a model is available to take off (" + src + ")");
    if (!m) return;

    var res = FM.takeoff.run(m);
    ROUND.push({ id: pid, res: res });

    t.truthy(res.marks.length > 0 || res.unresolved.length > 0,
             pid + " · the takeoff says something: " + res.marks.length + " marks, " +
             res.unresolved.length + " unresolved, " + res.warnings.length + " warnings");

    /* the round trip proper: solvePlan must accept these marks unchanged */
    var plan = { id: "takeoff-" + pid, name: "Takeoff of " + pid, marks: res.marks };
    var threw = null;
    try { FM.solver.solvePlan(plan, pack, { unify: false }); }
    catch (e) { threw = e; }
    t.truthy(!threw, pid + " · solver.solvePlan accepts every emitted mark without throwing" +
             (threw ? " — threw: " + threw.message : ""));

    /* and demandFor accepts each sizeable mark on its own, in every pack —
       this is what a header missing `bearing` or `carries` would fail */
    var dThrew = null, dMark = null;
    FM.weights.PACKS.forEach(function (pk) {
      res.marks.forEach(function (mk) {
        if (mk.component) return;
        if (!FM.weights.applicability(mk, pk).applicable) return;
        try { FM.weights.demandFor(mk, plan, pk); }
        catch (e) { if (!dThrew) { dThrew = e; dMark = mk.id + " in " + pk.id; } }
      });
    });
    t.truthy(!dThrew, pid + " · weights.demandFor accepts every applicable mark in all six packs" +
             (dThrew ? " — " + dMark + ": " + dThrew.message : ""));
  });

  t.suite("takeoff · the conditions each plan exists to pose");
  (function () {
    function res(id) {
      var r = ROUND.filter(function (x) { return x.id === id; })[0];
      return r ? r.res : null;
    }

    /* Sunbelt: the lanai roof stands on POSTS, and the geometry model has no
       post or beam entity — so the lanai beam is not derivable at all, and
       the rear-wall slider header that shares the load path goes with it.
       This is the single biggest gap in the model shape and it must show up
       as a refusal, not as a thinner house. */
    var sb = res("sunbelt-ranch-1850");
    if (sb && !haveFromPlan) {
      t.truthy(unresolvedMentioning(sb, "F-LANAI").length >= 1,
               "sunbelt · the post-supported lanai roof is unresolved — the model has no post or " +
               "beam entity, so its span has no second support to measure to");
      t.truthy(unresolvedMentioning(sb, "F-LANAI")[0].need.indexOf("no beam or post entity") !== -1,
               "and the fix names the missing entity rather than asking for a number");
      t.truthy(unresolvedMentioning(sb, "O-SLD").length >= 1,
               "sunbelt · and the rear slider header goes with it rather than being sized on the " +
               "main roof alone, which would be the lanai load silently dropped");
      var gar = markOf(sb, "HDR-O-GAR");
      t.truthy(gar && gar.bearing === 4.5,
               "sunbelt · the 16 ft garage opening derives 3 jacks x 1.5 in = 4.5 in of bearing");
    }

    /* Two-storey: a single-storey wing roof and the second floor land on the
       same first-floor wall. That is the roof+floor case, and weights.js
       will only accept it with BOTH tributaries declared separately. */
    var ts = res("two-story-2450");
    if (ts && !haveFromPlan) {
      var rf = ts.marks.filter(function (m) { return m.carries === "roof+floor"; })[0];
      t.truthy(rf, "two-storey · a wall carrying both a wing roof and the floor above produces a " +
               "roof+floor header");
      if (rf) {
        t.truthy(rf.tribRoof > 0 && rf.tribFloor > 0,
                 "with tribRoof and tribFloor declared separately (" + rf.tribRoof + " / " +
                 rf.tribFloor + " ft)");
        t.eq(rf.trib, undefined,
             "and no single blended `trib` — weights.demandFor does that conversion itself, exactly");
        t.truthy(derivOf(ts, rf.id, "tribRoof").fromIds.length >= 1 &&
                 derivOf(ts, rf.id, "tribFloor").fromIds.length >= 1,
                 "each of the two tributaries names the region it came from");
      }
      t.truthy(warningMentioning(ts, "wall-above-not-loaded").length +
               ts.warnings.filter(function (w) { return w.kind === "wall-above-not-loaded"; }).length > 0,
               "two-storey · headers carrying a storey of wall above them are flagged: the framing " +
               "tributary is complete, the wall standing on it is not in ASSEMBLY{} at all");
    }

    /* Townhome: an interior unit's party wall has the neighbour's framing on
       the other side, and the model draws one unit. The takeoff must refuse
       rather than take half the load. */
    var th = res("townhome-1220");
    if (th && !haveFromPlan) {
      t.truthy(unresolvedMentioning(th, "T2-W").length >= 1,
               "townhome · a header in a PARTY wall is refused: the model draws one unit, so what " +
               "frames on the neighbour's side of an interior wall is not in the geometry");
      t.truthy(unresolvedMentioning(th, "T-GAR").length >= 1,
               "townhome · and the garage door header is refused for the reason weights.js gives " +
               "for the same mark — it carries a wall, and this model has no wall dead load");
    }

    /* Starter: the gable-end walls bear nothing, so an opening in one makes
       no header — the same answer weights.js reaches for HDR-GBL. */
    var st = res("starter-1210");
    if (st && !haveFromPlan) {
      t.truthy(warningMentioning(st, "O-GBL").length >= 1,
               "starter · the gable-end window produces no header mark and says why");
      var w1 = markOf(st, "HDR-O-W1");
      t.truthy(w1 && w1.count === 2,
               "starter · the two identical front windows are one mark built twice");
      t.truthy(w1 && Math.abs(w1.trib - (32 - 5.5 / 12) / 2) < 2e-6,
               "starter · and their tributary is half the clear truss span, " +
               ((32 - 5.5 / 12) / 2).toFixed(4) + " ft — the tributary is a property of the WALL, " +
               "not of the opening, which is the whole point of a clear-span truss plan");
    }
  })();

  /* ===============================================================
     4. STRUCTURAL INVARIANTS over every fixture in this file
     =============================================================== */

  var ALL = [
    { id: "hand", res: hand }, { id: "one-support", res: one }, { id: "non-bearing", res: nb },
    { id: "wall-above", res: two }
  ].concat(ROUND);

  t.suite("takeoff · every emitted mark field has exactly one derivation, over every fixture");
  (function () {
    var missing = [], extra = [], dupes = [], nMarks = 0, nFields = 0;
    ALL.forEach(function (fx) {
      var seen = {};
      fx.res.derivations.forEach(function (d) {
        var k = d.markId + "." + d.field;
        if (seen[k]) dupes.push(fx.id + " " + k);
        seen[k] = d;
      });
      fx.res.marks.forEach(function (m) {
        nMarks++;
        var k;
        for (k in m) {
          if (!Object.prototype.hasOwnProperty.call(m, k)) continue;
          nFields++;
          if (!seen[m.id + "." + k]) missing.push(fx.id + " " + m.id + "." + k);
        }
      });
      fx.res.derivations.forEach(function (d) {
        var mk = fx.res.marks.filter(function (m) { return m.id === d.markId; })[0];
        if (!mk) { extra.push(fx.id + " " + d.markId + " (no such mark)"); return; }
        if (!Object.prototype.hasOwnProperty.call(mk, d.field)) {
          extra.push(fx.id + " " + d.markId + "." + d.field + " (no such field)");
        }
      });
    });
    t.eq(missing.length, 0, "no mark field is emitted without a derivation (" + nFields +
         " fields on " + nMarks + " marks checked)" + (missing.length ? ": " + missing.join(", ") : ""));
    t.eq(extra.length, 0, "no derivation describes a field or mark that was not emitted" +
         (extra.length ? ": " + extra.join(", ") : ""));
    t.eq(dupes.length, 0, "no field carries two competing derivations" +
         (dupes.length ? ": " + dupes.join(", ") : ""));
  })();

  t.suite("takeoff · a derivation is reconstructable without reading code");
  (function () {
    var thin = [];
    ALL.forEach(function (fx) {
      fx.res.derivations.forEach(function (d) {
        if (typeof d.how !== "string" || d.how.length < 25) thin.push(fx.id + " " + d.markId + "." + d.field);
        if (typeof d.from !== "string" || !d.from.length) thin.push(fx.id + " " + d.markId + "." + d.field + " (no source)");
        if (!d.cls) thin.push(fx.id + " " + d.markId + "." + d.field + " (no provenance class)");
        if (d.value === undefined) thin.push(fx.id + " " + d.markId + "." + d.field + " (no value)");
      });
    });
    t.eq(thin.length, 0, "every derivation carries a value, a source, a provenance class and the " +
         "arithmetic in words" + (thin.length ? ": " + thin.slice(0, 6).join(", ") : ""));

    var classes = {};
    ALL.forEach(function (fx) {
      fx.res.derivations.forEach(function (d) { classes[d.cls] = 1; });
    });
    var bad = Object.keys(classes).filter(function (c) {
      return ["code", "site", "market", "derived", "user"].indexOf(c) === -1;
    });
    t.eq(bad.length, 0, "and every provenance class is one of code|site|market|derived|user" +
         (bad.length ? ": " + bad.join(", ") : ""));
  })();

  t.suite("takeoff · every unresolved entry is a blocking item somebody can act on");
  (function () {
    var weak = [], n = 0;
    ALL.forEach(function (fx) {
      fx.res.unresolved.forEach(function (u) {
        n++;
        if (!u.what || u.what.length < 15) weak.push(fx.id + ": what");
        if (!u.why || u.why.length < 40) weak.push(fx.id + ": why (" + u.what + ")");
        if (!u.need || u.need.length < 25) weak.push(fx.id + ": need (" + u.what + ")");
      });
    });
    t.eq(weak.length, 0, n + " unresolved entries checked; each names what is unresolved, why the " +
         "geometry does not determine it, and what a human must supply" +
         (weak.length ? " — thin: " + weak.slice(0, 5).join(", ") : ""));
  })();

  t.suite("takeoff · never emits a mark weights.demandFor would throw on");
  (function () {
    var bad = [], nHdr = 0, nMark = 0;
    ALL.forEach(function (fx) {
      fx.res.marks.forEach(function (m) {
        nMark++;
        if (m.component) return;                       /* not sized by the engine at all */
        if (m.underdetermined) bad.push(fx.id + " " + m.id + " is marked underdetermined — " +
          "an underdetermined mark belongs in unresolved[], not in marks[]");
        if (!m.carries) bad.push(fx.id + " " + m.id + " declares no carries");
        if (m.role === "header") {
          nHdr++;
          if (!(m.bearing > 0)) bad.push(fx.id + " " + m.id + " is a header with no bearing");
        }
        if (m.carries === "roof+floor" && !(m.tribRoof >= 0 && m.tribFloor >= 0)) {
          bad.push(fx.id + " " + m.id + " carries roof+floor without tribRoof/tribFloor");
        }
        if (FM.weights.DEFL_BY_CARRIES &&
            !Object.prototype.hasOwnProperty.call(FM.weights.DEFL_BY_CARRIES, m.carries)) {
          bad.push(fx.id + " " + m.id + " declares carries \"" + m.carries + "\" which weights.js " +
                   "does not define");
        }
      });
    });
    t.eq(bad.length, 0, nMark + " marks checked, " + nHdr + " of them headers — every one declares " +
         "the fields weights.demandFor throws without" + (bad.length ? ": " + bad.join("; ") : ""));
  })();

  t.suite("takeoff · nothing is padded and nothing is silently defaulted");
  (function () {
    /* Two models identical except for wall thickness must give different
       spans. If a span ever came from a bounding box or a default, this
       fails. */
    var thin6 = FM.takeoff.run(model("t5.5", [
      level("L1", "First floor",
        [ wall("A", 0, 0, 30, 0, true, true, 5.5), wall("B", 0, 20, 30, 20, true, true, 5.5) ],
        [], [ region("F", box(0, 0, 30, 20), "floor", 90, 16, ["A", "B"]) ])
    ]));
    var thick = FM.takeoff.run(model("t9.5", [
      level("L1", "First floor",
        [ wall("A", 0, 0, 30, 0, true, true, 9.5), wall("B", 0, 20, 30, 20, true, true, 9.5) ],
        [], [ region("F", box(0, 0, 30, 20), "floor", 90, 16, ["A", "B"]) ])
    ]));
    t.near(markOf(thin6, "FJ-F").span, 19.541667, 2e-6, "5.5 in walls 20 ft apart give a 19.541667 ft clear span");
    t.near(markOf(thick, "FJ-F").span, 19.208333, 2e-6, "9.5 in walls 20 ft apart give a 19.208333 ft clear span");
    t.near(markOf(thin6, "FJ-F").span - markOf(thick, "FJ-F").span, (9.5 - 5.5) / 12, 2e-6,
           "the span tracks the wall thickness exactly — it is a clear distance, not a bounding box. " +
           "The 2e-6 tolerance is the module's own 1e-6 ft (1.2e-5 in) float-noise quantisation, " +
           "twice over for a difference of two quantised values");

    /* a wall with no thickness is refused, not assumed to be 2x6 */
    var noT = FM.takeoff.run(model("no thickness", [
      level("L1", "First floor",
        [ { id: "A", x1: 0, y1: 0, x2: 30, y2: 0, bearing: true, exterior: true },
          wall("B", 0, 20, 30, 20, true, true) ],
        [], [ region("F", box(0, 0, 30, 20), "floor", 90, 16, ["A", "B"]) ])
    ]));
    t.eq(noT.marks.length, 0, "a bearing wall with no declared thickness produces no mark");
    t.truthy(unresolvedMentioning(noT, "A").length >= 1, "it is refused by name");

    /* the framing direction decides the span; there is no default for it */
    var noDir = FM.takeoff.run(model("no direction", [
      level("L1", "First floor",
        [ wall("A", 0, 0, 30, 0, true, true), wall("B", 0, 20, 30, 20, true, true) ],
        [], [ { id: "F", polygon: box(0, 0, 30, 20), kind: "floor", spacingIn: 16,
                bearsOn: ["A", "B"] } ])
    ]));
    t.eq(noDir.marks.length, 0, "a region with no directionDeg produces no mark — 0 and 90 are " +
         "different members, so there is no defensible default");

    /* an unclassifiable framing kind is unresolved, not defaulted to joist */
    var oddKind = FM.takeoff.run(model("odd kind", [
      level("L1", "First floor",
        [ wall("A", 0, 0, 30, 0, true, true), wall("B", 0, 20, 30, 20, true, true) ],
        [], [ region("F", box(0, 0, 30, 20), "mezzanine", 90, 16, ["A", "B"]) ])
    ]));
    t.eq(oddKind.marks.length, 0, "an unclassifiable framing kind produces no mark");
    t.truthy(unresolvedMentioning(oddKind, "F")[0].why.indexOf("Defaulting") !== -1,
             "and the reason says why defaulting it would pick both a ladder and a load set");

    /* the drawing contradicting itself is refused rather than resolved */
    var contra = FM.takeoff.run(model("contradiction", [
      level("L1", "First floor",
        [ wall("A", 0, 0, 30, 0, false, true), wall("B", 0, 20, 30, 20, true, true) ],
        [], [ region("F", box(0, 0, 30, 20), "floor", 90, 16, ["A", "B"]) ])
    ]));
    t.truthy(unresolvedMentioning(contra, "A").length >= 1,
             "a wall declared bearing:false that framing declares it bears on is a contradiction, " +
             "and the takeoff refuses to pick which half of the drawing to believe");
  })();

  t.suite("takeoff · a bearing line drawn as two wall segments is still one bearing line");
  (function () {
    /* The rear wall is drawn as two segments either side of a break — a
       normal thing in a traced plan. It is one bearing line and it must give
       the same span as one continuous wall, not read as a third support. */
    var SPLIT = model("Split bearing line", [
      level("L1", "First floor",
        [ wall("A", 0, 0, 30, 0, true, true),
          wall("B1", 0, 20, 14, 20, true, true),
          wall("B2", 14, 20, 30, 20, true, true) ],
        [ opening("O-1", "B1", 4, 4, 6.67, "window") ],
        [ region("F", box(0, 0, 30, 20), "floor", 90, 16, ["A", "B1", "B2"]) ])
    ]);
    var sp = FM.takeoff.run(SPLIT);
    var m = markOf(sp, "FJ-F");
    t.truthy(m, "the region is taken off — two collinear segments are grouped into one bearing line");
    t.near(m.span, 19.541667, 2e-6, "and the span is the same 19.541667 ft a single wall would give");
    t.eq(sp.unresolved.length, 0, "not read as a three-support multi-span condition");
    t.truthy(markOf(sp, "HDR-O-1"), "and an opening in one of the segments still gets its header");

    /* two segments of one line with different thicknesses put the bearing
       face in two places, and that IS refused */
    var MIXED = model("Split line, two thicknesses", [
      level("L1", "First floor",
        [ wall("A", 0, 0, 30, 0, true, true, 5.5),
          wall("B1", 0, 20, 14, 20, true, true, 5.5),
          wall("B2", 14, 20, 30, 20, true, true, 9.5) ],
        [], [ region("F", box(0, 0, 30, 20), "floor", 90, 16, ["A", "B1", "B2"]) ])
    ]);
    var mx = FM.takeoff.run(MIXED);
    t.eq(mx.marks.length, 0, "one bearing line drawn with two different thicknesses is refused");
    t.truthy(unresolvedMentioning(mx, "F")[0].why.indexOf("two places") !== -1,
             "because the face the span is measured to would be in two places");
  })();

  t.suite("takeoff · the surface refuses bad input loudly and takes no options that assume");
  (function () {
    var threw = null;
    try { FM.takeoff.run(null); } catch (e) { threw = e; }
    t.truthy(threw && threw.name === "TypeError",
             "run(null) throws rather than returning an empty takeoff that reads as 'nothing to do'");

    var g = model("two identical windows", [
      level("L1", "First floor",
        [ wall("A", 0, 0, 40, 0, true, true), wall("B", 0, 20, 40, 20, true, true) ],
        [ opening("O-1", "A", 4, 4, 6.67, "window"), opening("O-2", "A", 12, 4, 6.67, "window") ],
        [ region("F", box(0, 0, 40, 20), "floor", 90, 16, ["A", "B"]) ])
    ]);
    t.eq(FM.takeoff.run(g, { groupHeaders: false }).marks
      .filter(function (m) { return m.role === "header"; }).length, 2,
      "groupHeaders:false keeps one mark per opening — the only option this module has, and it " +
      "changes presentation, never a number");
    t.eq(FM.takeoff.run(g).marks.filter(function (m) { return m.role === "header"; })[0].count, 2,
      "and the default groups them");
  })();

  t.suite("takeoff · identical openings become one mark with a traceable count");
  (function () {
    var g = FM.takeoff.run(model("three identical windows", [
      level("L1", "First floor",
        [ wall("A", 0, 0, 40, 0, true, true), wall("B", 0, 20, 40, 20, true, true) ],
        [ opening("O-1", "A", 4, 4, 6.67, "window"),
          opening("O-2", "A", 12, 4, 6.67, "window"),
          opening("O-3", "A", 20, 4, 6.67, "window") ],
        [ region("F", box(0, 0, 40, 20), "floor", 90, 16, ["A", "B"]) ])
    ]));
    var hdrs = g.marks.filter(function (m) { return m.role === "header"; });
    t.eq(hdrs.length, 1, "three identical openings collapse to one mark");
    t.eq(hdrs[0].count, 3, "with count 3");
    var d = derivOf(g, hdrs[0].id, "count");
    t.truthy(d.fromIds.length === 3 && d.how.indexOf("O-2") !== -1,
             "and the count derivation lists every opening id it stands for");
    t.truthy(d.how.indexOf("nothing is rounded") !== -1,
             "grouping is on exact equality of every derived number, never on rounding two to match");
  })();
};

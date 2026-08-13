/* ============================================================
   cad.js — the geometry model, its validator, and fromPlan().

   Three things are pinned here.

   1. validate() catches each defect class it claims to, and gets
      the SEVERITY right — an error blocks the geometry gate and a
      warn does not, so a defect filed at the wrong severity either
      lets a broken model through or stops a sound one. Every class
      has a deliberately broken model of its own, differing from a
      known-clean base in exactly one way, so a passing assertion
      cannot be an accident of some other defect.

   2. fromPlan() produces a model that validates with no errors for
      every plan in weights.js, and reports honestly for the plans
      whose geometry does not determine a layout. The regression
      that matters most: every wall it emits carries a thickness.
      A wall with none stops the takeoff dead — the clear span is
      measured between wall FACES — so this is the seam that broke
      the whole pipeline once already.

   3. The two pieces of arithmetic a human's fingers depend on:
      the underlay's ft-per-pixel, and whether an opening fits the
      wall it was just clicked into.
   ============================================================ */

"use strict";

module.exports = function (t, FM) {

  var cad = FM.cad;

  function codes(rows) {
    return rows.map(function (r) { return r.code; });
  }
  function row(rows, code) {
    var hit = null;
    rows.forEach(function (r) { if (!hit && r.code === code) hit = r; });
    return hit;
  }
  function has(rows, code) { return !!row(rows, code); }
  function errs(rows) { return rows.filter(function (r) { return r.severity === "error"; }); }
  function warns(rows) { return rows.filter(function (r) { return r.severity === "warn"; }); }
  function clone(m) { return cad.fromJSON(cad.toJSON(m)); }

  /* A 20 x 12 box with a roof over it, bearing on the two 20 ft walls.
     Everything in the defect section is this, broken once. */
  function base() {
    var m = cad.blank("Test box");
    var L = m.levels[0];
    L.topPlateFt = 9;
    function w(x1, y1, x2, y2) {
      var ww = cad.newWall(L, x1, y1, x2, y2, { thicknessIn: 3.5, heightFt: 9 });
      L.walls.push(ww);
      return ww;
    }
    w(0, 0, 20, 0);    /* W1 front  */
    w(20, 0, 20, 12);  /* W2 right  */
    w(0, 12, 20, 12);  /* W3 rear   */
    w(0, 0, 0, 12);    /* W4 left   */
    L.framing.push(cad.newFraming(L, [[0, 0], [20, 0], [20, 12], [0, 12]], {
      kind: "roof", directionDeg: 90, spacingIn: 24, bearsOn: ["W1", "W3"]
    }));
    return m;
  }

  /* ============================================================
     1. the model round-trips
     ============================================================ */

  t.suite("cad · the model round-trips through JSON");
  (function () {
    var m = base();
    var L = m.levels[0];
    L.openings.push(cad.newOpening(L, "W1", 4, 6, { headHeightFt: 6.67, kind: "slider", note: "rear slider" }));
    m.underlay = { dataUri: "data:image/png;base64,AAAA", opacity: 0.4, pxW: 1200, pxH: 900,
                   originFt: [2, 3], name: "lot17.png",
                   calib: { ax: 100, ay: 100, bx: 400, by: 500, knownFt: 50 } };
    m.unresolved.push({ what: "the porch", why: "no position declared", need: "an offset from a corner" });

    var back = cad.fromJSON(cad.toJSON(m));
    t.eq(back.name, "Test box", "round-trip · name survives");
    t.eq(back.version, cad.MODEL_VERSION, "round-trip · version is stamped");
    t.eq(back.levels[0].walls.length, 4, "round-trip · four walls");
    t.eq(back.levels[0].walls[0].id, "W1", "round-trip · wall ids survive");
    t.near(back.levels[0].walls[1].x2, 20, 1e-9, "round-trip · wall coordinates survive exactly");
    t.eq(back.levels[0].walls[0].thicknessIn, 3.5, "round-trip · thickness survives");
    t.eq(back.levels[0].openings.length, 1, "round-trip · one opening");
    t.eq(back.levels[0].openings[0].wallId, "W1", "round-trip · the opening keeps its wall");
    t.eq(back.levels[0].openings[0].kind, "slider", "round-trip · opening kind survives");
    t.near(back.levels[0].openings[0].headHeightFt, 6.67, 1e-9, "round-trip · head height survives");
    t.eq(back.levels[0].framing[0].bearsOn.join(","), "W1,W3", "round-trip · bearsOn survives");
    t.eq(back.levels[0].framing[0].polygon.length, 4, "round-trip · the region polygon survives");
    t.eq(back.underlay.pxW, 1200, "round-trip · the underlay's pixel size survives");
    t.near(back.underlay.calib.knownFt, 50, 1e-9, "round-trip · the calibration survives");
    t.eq(back.unresolved.length, 1, "round-trip · the unresolved list survives");
    t.eq(back.unresolved[0].what, "the porch", "round-trip · an unresolved item keeps its text");
    t.eq(cad.toJSON(back), cad.toJSON(clone(back)), "round-trip · a second pass is byte-identical");

    /* and it refuses what is not a model, by name */
    var why = "";
    try { cad.fromJSON("{nope"); } catch (e) { why = e.message; }
    t.truthy(why.indexOf("not JSON") !== -1, "fromJSON · bad JSON is refused and says so");
    why = "";
    try { cad.fromJSON("[1,2,3]"); } catch (e) { why = e.message; }
    t.truthy(why.indexOf("array") !== -1, "fromJSON · an array is refused and says what it got");
    why = "";
    try { cad.fromJSON('{"levels":[]}'); } catch (e) { why = e.message; }
    t.truthy(why.indexOf("levels") !== -1, "fromJSON · a model with no levels is refused by name");
    why = "";
    try { cad.fromJSON('{"version":99,"levels":[{"walls":[]}]}'); } catch (e) { why = e.message; }
    t.truthy(why.indexOf("version 99") !== -1,
             "fromJSON · a model from a newer build is refused, not half-read");

    /* a hand-edited file that omits a thickness reads as UNDECLARED, never 3.5 */
    var thin = cad.fromJSON('{"levels":[{"id":"L1","walls":[{"id":"W1","x1":0,"y1":0,"x2":10,"y2":0}]}]}');
    t.eq(thin.levels[0].walls[0].thicknessIn, null,
         "fromJSON · a missing thickness is null, not a default");
    t.eq(thin.levels[0].walls[0].heightFt, null, "fromJSON · a missing height is null, not a default");
  })();

  /* ============================================================
     2. the base model is clean — every defect below is measured
        against this, so it has to hold
     ============================================================ */

  t.suite("cad · a sound model produces no findings");
  (function () {
    var rows = cad.validate(base());
    t.eq(rows.length, 0, "clean · a 20x12 box with a roof over it has no findings at all");

    var st = cad.stats(base());
    t.eq(st.walls, 4, "stats · four walls");
    t.eq(st.bearingWalls, 4, "stats · all four are bearing by default");
    t.near(st.areaSf, 240, 1e-6, "stats · the closed exterior loop gives 240 sf");
    t.near(st.wallLf, 64, 1e-6, "stats · 64 lf of wall");
    t.eq(st.framing, 1, "stats · one framing region");
    t.near(st.framedSf, 240, 1e-6, "stats · the region is 240 sf");

    /* an open loop has no area rather than a wrong one */
    var open = base();
    open.levels[0].walls[3].x1 = 3;
    t.eq(cad.footprintAreaSf(open.levels[0]), null,
         "stats · an exterior loop that does not close reports no area, not a partial one");
  })();

  /* ============================================================
     3. every defect class, one broken model each
     ============================================================ */

  t.suite("cad · validate catches each defect class");

  /* --- walls --- */
  (function () {
    var m = base();
    m.levels[0].walls[1].x2 = 20; m.levels[0].walls[1].y2 = 0;   /* both ends at (20,0) */
    var rows = cad.validate(m);
    t.truthy(has(rows, "wall-zero-length"), "defect · a zero-length wall is caught");
    t.eq(row(rows, "wall-zero-length").severity, "error", "defect · a zero-length wall is an error");
    t.truthy(row(rows, "wall-zero-length").text.indexOf("W2") === 0,
             "defect · the finding names the wall it is about");
  })();

  (function () {
    var m = base();
    m.levels[0].walls[1].y2 = 0.25;                              /* 3 in long */
    var rows = cad.validate(m);
    t.truthy(has(rows, "wall-too-short"), "defect · a wall shorter than the minimum is caught");
    t.eq(row(rows, "wall-too-short").severity, "error", "defect · a mis-click wall is an error");
  })();

  (function () {
    var m = base();
    var L = m.levels[0];
    L.walls = [cad.newWall(L, 0, 0, 0.3, 0, { thicknessIn: 5.5, heightFt: 9 })];
    L.framing = [];
    var rows = cad.validate(m);
    t.truthy(has(rows, "wall-shorter-than-thick"),
             "defect · a wall thicker than it is long is caught");
    t.eq(row(rows, "wall-shorter-than-thick").severity, "error",
         "defect · thicker-than-long is an error");
    t.truthy(row(rows, "wall-shorter-than-thick").text.indexOf("Delete it or extend it") !== -1,
             "defect · and it says what to do about it");
  })();

  (function () {
    var m = base();
    m.levels[0].walls[0].thicknessIn = 0;
    t.eq(row(cad.validate(m), "wall-thickness-zero").severity, "error",
         "defect · a zero thickness is an error");
    var m2 = base();
    m2.levels[0].walls[0].heightFt = 0;
    t.eq(row(cad.validate(m2), "wall-height-zero").severity, "error",
         "defect · a zero wall height is an error");
    var m3 = base();
    m3.levels[0].walls[0].thicknessIn = null;
    var r3 = cad.validate(m3);
    t.eq(row(r3, "wall-no-thickness").severity, "error",
         "defect · an undeclared thickness BLOCKS the gate — a span cannot be measured without it");
    t.truthy(row(r3, "wall-no-thickness").text.indexOf("clear span") !== -1,
             "defect · and it says why the takeoff needs it");
  })();

  (function () {
    /* two interior walls crossing mid-span, with no node at the crossing */
    var m = base();
    var L = m.levels[0];
    L.walls.push(cad.newWall(L, 4, 2, 16, 2, { exterior: false, thicknessIn: 3.5, heightFt: 9 }));
    L.walls.push(cad.newWall(L, 10, 1, 10, 8, { exterior: false, thicknessIn: 3.5, heightFt: 9 }));
    var rows = cad.validate(m);
    t.truthy(has(rows, "walls-cross-no-node"), "defect · two walls crossing with no node is caught");
    t.eq(row(rows, "walls-cross-no-node").severity, "error", "defect · a crossing with no node is an error");
    t.truthy(row(rows, "walls-cross-no-node").text.indexOf("(10.00, 2.00)") !== -1,
             "defect · the finding gives the coordinates of the crossing");

    /* a T-junction IS a node and must not be reported */
    var m2 = base();
    var L2 = m2.levels[0];
    L2.walls.push(cad.newWall(L2, 10, 0, 10, 8, { exterior: false, thicknessIn: 3.5, heightFt: 9 }));
    t.eq(errs(cad.validate(m2)).length, 0,
         "defect · a T-junction landing on a wall's mid-span is a node, not a crossing");

    /* and so is a shared corner — the base box is four of them */
    t.eq(codes(cad.validate(base())).indexOf("walls-cross-no-node"), -1,
         "defect · four walls sharing corners are not crossings");
  })();

  /* --- openings --- */
  (function () {
    var m = base();
    var L = m.levels[0];
    L.openings.push(cad.newOpening(L, "W2", 1, 30, { headHeightFt: 6.67 }));  /* W2 is 12 ft */
    var rows = cad.validate(m);
    t.truthy(has(rows, "opening-wider-than-wall"), "defect · an opening wider than its wall is caught");
    t.eq(row(rows, "opening-wider-than-wall").severity, "error",
         "defect · wider-than-its-wall is an error");
  })();

  (function () {
    var m = base();
    var L = m.levels[0];
    L.openings.push(cad.newOpening(L, "W2", 9, 4, { headHeightFt: 6.67 }));   /* 9 + 4 > 12 */
    var rows = cad.validate(m);
    t.truthy(has(rows, "opening-overhangs"), "defect · an opening hanging off the end is caught");
    t.eq(row(rows, "opening-overhangs").severity, "error", "defect · an overhanging opening is an error");
    t.truthy(row(rows, "opening-overhangs").text.indexOf("end") !== -1,
             "defect · and it says which end it hangs off");
  })();

  (function () {
    var m = base();
    var L = m.levels[0];
    L.openings.push(cad.newOpening(L, "W2", 0.05, 4, { headHeightFt: 6.67 }));
    var rows = cad.validate(m);
    t.truthy(has(rows, "opening-no-jack-room"),
             "defect · an opening with no room for its jack and king studs is caught");
    t.eq(row(rows, "opening-no-jack-room").severity, "error", "defect · no jack room is an error");
    t.truthy(row(rows, "opening-no-jack-room").text.indexOf("jack and a king stud") !== -1,
             "defect · and it names what does not fit");
  })();

  (function () {
    var m = base();
    var L = m.levels[0];
    L.openings.push(cad.newOpening(L, "W1", 2, 4, { headHeightFt: 6.67 }));
    L.openings.push(cad.newOpening(L, "W1", 5, 4, { headHeightFt: 6.67 }));
    t.eq(row(cad.validate(m), "openings-overlap").severity, "error",
         "defect · two overlapping openings in one wall is an error");

    var m2 = base();
    var L2 = m2.levels[0];
    L2.openings.push(cad.newOpening(L2, "W1", 2, 4, { headHeightFt: 6.67 }));
    L2.openings.push(cad.newOpening(L2, "W1", 6.3, 4, { headHeightFt: 6.67 }));  /* 0.3 ft apart */
    var r2 = cad.validate(m2);
    t.truthy(has(r2, "openings-too-close"),
             "defect · two openings 0.3 ft apart have no room for two pairs of studs");
    t.eq(row(r2, "openings-too-close").severity, "error", "defect · too-close openings is an error");

    var m3 = base();
    var L3 = m3.levels[0];
    L3.openings.push(cad.newOpening(L3, "W1", 2, 4, { headHeightFt: 6.67 }));
    L3.openings.push(cad.newOpening(L3, "W1", 6.5, 4, { headHeightFt: 6.67 }));  /* exactly 0.5 */
    t.eq(errs(cad.validate(m3)).length, 0,
         "defect · two openings exactly 0.5 ft apart fit two pairs of studs and pass");
  })();

  (function () {
    var m = base();
    var L = m.levels[0];
    L.openings.push(cad.newOpening(L, "W9", 2, 4, { headHeightFt: 6.67 }));
    t.eq(row(cad.validate(m), "opening-orphan").severity, "error",
         "defect · an opening naming a wall that is not there is an error");

    var m2 = base();
    var L2 = m2.levels[0];
    L2.openings.push(cad.newOpening(L2, "W1", 2, 4, { headHeightFt: 9.5 }));   /* wall is 9 ft */
    t.eq(row(cad.validate(m2), "opening-head-above-wall").severity, "error",
         "defect · a head height at or above the wall height leaves no room for a header");

    var m3 = base();
    var L3 = m3.levels[0];
    L3.openings.push(cad.newOpening(L3, "W1", 2, 4));                          /* no head height */
    t.eq(row(cad.validate(m3), "opening-no-head-height").severity, "warn",
         "defect · an undeclared head height is a warn");
  })();

  /* --- framing regions --- */
  (function () {
    var m = base();
    m.levels[0].framing[0].bearsOn = ["W1"];
    var rows = cad.validate(m);
    t.truthy(has(rows, "framing-bears-on-too-few"),
             "defect · a region bearing on one wall is caught");
    t.eq(row(rows, "framing-bears-on-too-few").severity, "error",
         "defect · bearing on fewer than two walls is an error");

    var m2 = base();
    m2.levels[0].framing[0].bearsOn = [];
    t.truthy(row(cad.validate(m2), "framing-bears-on-too-few").text.indexOf("no wall") !== -1,
             "defect · a region bearing on nothing says so in the finding");

    var m3 = base();
    m3.levels[0].framing[0].bearsOn = ["W1", "W99"];
    t.eq(row(cad.validate(m3), "framing-bears-on-missing-wall").severity, "error",
         "defect · a region naming a wall that is not there is an error");
  })();

  (function () {
    /* the region is a strip across the middle of the box; it touches
       neither of the two walls it claims to bear on */
    var m = base();
    m.levels[0].framing[0].polygon = [[4, 4], [16, 4], [16, 8], [4, 8]];
    var rows = cad.validate(m);
    t.truthy(has(rows, "framing-not-touching-wall"),
             "defect · a region that does not reach the walls it claims is caught");
    t.eq(row(rows, "framing-not-touching-wall").severity, "error",
         "defect · claiming a wall it does not touch is an error");
    t.eq(rows.filter(function (r) { return r.code === "framing-not-touching-wall"; }).length, 2,
         "defect · both untouched walls are reported, not just the first");

    /* a region whose edge lies ON the wall does touch it */
    var m2 = base();
    m2.levels[0].framing[0].polygon = [[0, 0], [20, 0], [20, 12], [0, 12]];
    t.eq(codes(cad.validate(m2)).indexOf("framing-not-touching-wall"), -1,
         "defect · a region edge lying on the wall counts as bearing on it");

    /* and so does a wall running underneath the region */
    var m3 = base();
    var L3 = m3.levels[0];
    L3.walls.push(cad.newWall(L3, 0, 6, 20, 6, { exterior: false, thicknessIn: 3.5, heightFt: 9 }));
    L3.framing[0].bearsOn = ["W1", "W5", "W3"];
    t.eq(codes(cad.validate(m3)).indexOf("framing-not-touching-wall"), -1,
         "defect · an interior bearing line under the region counts as bearing on it");
  })();

  (function () {
    var m = base();
    m.levels[0].walls[0].bearing = false;
    var rows = cad.validate(m);
    t.eq(row(rows, "framing-on-nonbearing-wall").severity, "error",
         "defect · a region bearing on a wall not marked bearing is a contradiction and an error");

    var m2 = base();
    m2.levels[0].framing[0].polygon = [[0, 0], [20, 0]];
    t.eq(row(cad.validate(m2), "framing-not-a-region").severity, "error",
         "defect · a two-corner region is an error");

    var m3 = base();
    m3.levels[0].framing[0].polygon = [[0, 0], [10, 0], [20, 0]];
    t.eq(row(cad.validate(m3), "framing-zero-area").severity, "error",
         "defect · three collinear corners enclose nothing and are an error");

    var m4 = base();
    m4.levels[0].framing[0].spacingIn = null;
    t.eq(row(cad.validate(m4), "framing-no-spacing").severity, "error",
         "defect · an undeclared spacing blocks the gate — no member count comes out of it");
    var m5 = base();
    m5.levels[0].framing[0].directionDeg = null;
    t.eq(row(cad.validate(m5), "framing-no-direction").severity, "error",
         "defect · an undeclared span direction blocks the gate — it is what decides the span");
  })();

  /* --- model-wide --- */
  (function () {
    var m = base();
    m.levels[0].walls.forEach(function (w) { w.bearing = false; });
    m.levels[0].framing = [];
    var rows = cad.validate(m);
    t.truthy(has(rows, "no-bearing-walls"), "defect · a model with no bearing wall is caught");
    t.eq(row(rows, "no-bearing-walls").severity, "error", "defect · no bearing walls is an error");

    t.eq(row(cad.validate(cad.blank("Empty")), "no-walls").severity, "error",
         "defect · an empty model does not pass the geometry gate");

    var m2 = base();
    m2.levels[0].framing = [];
    t.eq(row(cad.validate(m2), "level-no-framing").severity, "warn",
         "defect · a level with no framing region is a warn, not a block");

    var m3 = base();
    m3.levels[0].walls[3].y2 = 11;                       /* the loop no longer closes */
    t.eq(row(cad.validate(m3), "exterior-not-closed").severity, "warn",
         "defect · exterior walls that do not close a loop is a warn");

    var m4 = base();
    m4.underlay = { dataUri: "data:image/png;base64,AA", calib: null, opacity: 0.35,
                    pxW: 100, pxH: 100, originFt: [0, 0], name: "x.png" };
    t.eq(row(cad.validate(m4), "underlay-uncalibrated").severity, "warn",
         "defect · an uncalibrated underlay is a warn and says nothing traced off it is real");

    var m5 = base();
    m5.unresolved.push({ what: "the porch", why: "the plan does not locate it.", need: "an offset" });
    var r5 = row(cad.validate(m5), "unresolved");
    t.eq(r5.severity, "warn", "defect · an unresolved item is reported as a warn");
    t.truthy(r5.text.indexOf("the porch") !== -1 && r5.text.indexOf("Need: an offset") !== -1,
             "defect · and it carries what, why and what is needed");
  })();

  /* The gate rule: approving geometry means it was fit to pass on. Anything
     the takeoff cannot proceed without is an ERROR, never a warn — a warn that
     silently blocks the next stage means someone put their name on a model
     that cannot produce a span. */
  (function () {
    var blocking = ["wall-no-thickness", "framing-no-spacing", "framing-no-direction",
                    "framing-bears-on-too-few"];
    var m = base();
    var L = m.levels[0];
    L.walls[0].thicknessIn = null;
    L.framing[0].spacingIn = null;
    L.framing[0].directionDeg = null;
    L.framing[0].bearsOn = [];
    var rows = cad.validate(m);
    blocking.forEach(function (c) {
      t.truthy(has(rows, c), "gate · " + c + " is reported");
      t.eq(row(rows, c).severity, "error",
           "gate · " + c + " blocks the geometry gate rather than following it downstream");
    });
    t.eq(warns(rows).filter(function (r) { return blocking.indexOf(r.code) !== -1; }).length, 0,
         "gate · none of the four blocking classes is filed as a warn");
  })();

  /* every finding names an element and tells the reader what to do */
  (function () {
    var bad = base();
    var L = bad.levels[0];
    L.walls[1].y2 = 0.25;
    L.openings.push(cad.newOpening(L, "W1", 0.05, 4));
    L.framing[0].bearsOn = ["W1"];
    var rows = cad.validate(bad);
    var mute = rows.filter(function (r) {
      return !r.text || r.text.length < 40 || !r.id;
    });
    t.eq(mute.length, 0, "findings · every finding names an element and says something specific");
    t.eq(rows.filter(function (r) { return r.severity !== "error" && r.severity !== "warn"; }).length, 0,
         "findings · every finding is either an error or a warn");
  })();

  /* ============================================================
     4. the opening-fits arithmetic
     ============================================================ */

  t.suite("cad · does this opening fit its wall");
  (function () {
    var wall = { id: "W1", x1: 0, y1: 0, x2: 10, y2: 0, thicknessIn: 3.5 };
    t.near(cad.wallLength(wall), 10, 1e-9, "fit · the wall is 10 ft long");
    t.near(cad.endClearFt(), 0.25, 1e-9,
           "fit · a jack (1.5 in) and a king (1.5 in) need 0.25 ft at each end");

    t.eq(cad.openingFits(wall, { id: "O1", wallId: "W1", offsetFt: 3, widthFt: 4 }, []).ok, true,
         "fit · a 4 ft opening 3 ft in fits a 10 ft wall");
    t.eq(cad.openingFits(wall, { id: "O1", wallId: "W1", offsetFt: 0.25, widthFt: 9.5 }, []).ok, true,
         "fit · exactly 0.25 ft at each end is the tightest that fits");
    t.eq(cad.openingFits(wall, { id: "O1", wallId: "W1", offsetFt: 0.24, widthFt: 9.5 }, []).code,
         "opening-no-jack-room", "fit · one hundredth of a foot tighter does not");
    t.eq(cad.openingFits(wall, { id: "O1", wallId: "W1", offsetFt: 1, widthFt: 12 }, []).code,
         "opening-wider-than-wall", "fit · a 12 ft opening does not fit a 10 ft wall");
    t.eq(cad.openingFits(wall, { id: "O1", wallId: "W1", offsetFt: 8, widthFt: 4 }, []).code,
         "opening-overhangs", "fit · an opening running past the end is caught");
    t.eq(cad.openingFits(wall, { id: "O1", wallId: "W1", offsetFt: -1, widthFt: 4 }, []).code,
         "opening-overhangs", "fit · a negative offset is caught");
    t.eq(cad.openingFits(wall, { id: "O1", wallId: "W1", offsetFt: 1, widthFt: 0 }, []).code,
         "opening-no-width", "fit · a zero-width opening is refused by name");

    var others = [{ id: "O2", wallId: "W1", offsetFt: 1, widthFt: 3 }];
    t.eq(cad.openingFits(wall, { id: "O1", wallId: "W1", offsetFt: 3, widthFt: 3 }, others).code,
         "openings-overlap", "fit · an opening overlapping its neighbour is caught");
    t.eq(cad.openingFits(wall, { id: "O1", wallId: "W1", offsetFt: 4.3, widthFt: 3 }, others).code,
         "openings-too-close", "fit · 0.3 ft between two openings is not two pairs of studs");
    t.eq(cad.openingFits(wall, { id: "O1", wallId: "W1", offsetFt: 4.5, widthFt: 3 }, others).ok, true,
         "fit · 0.5 ft between two openings is");
    t.eq(cad.openingFits(wall, { id: "O1", wallId: "W2", offsetFt: 1, widthFt: 3 },
                         [{ id: "O2", wallId: "W3", offsetFt: 1, widthFt: 3 }]).ok, true,
         "fit · an opening in another wall is not a neighbour");

    /* the message is a instruction, not a complaint */
    var why = cad.openingFits(wall, { id: "O1", wallId: "W1", offsetFt: 8, widthFt: 4 }, []).text;
    t.truthy(why.indexOf("O1") === 0 && why.indexOf("Move it back inside the wall") !== -1,
             "fit · the refusal names the opening and says what to do");
  })();

  /* ============================================================
     5. underlay scale calibration
     ============================================================ */

  t.suite("cad · underlay scale calibration");
  (function () {
    /* a 3-4-5 triangle: 300 px across and 400 px down is 500 px */
    t.near(cad.scaleOf({ calib: { ax: 100, ay: 100, bx: 400, by: 500, knownFt: 50 } }),
           0.1, 1e-12, "calib · 50 ft across 500 px is 0.1 ft per pixel");
    t.near(cad.scaleOf({ calib: { ax: 0, ay: 0, bx: 1000, by: 0, knownFt: 46 } }),
           0.046, 1e-12, "calib · a 46 ft wall traced 1000 px long is 0.046 ft per pixel");
    t.near(1 / cad.scaleOf({ calib: { ax: 0, ay: 0, bx: 1000, by: 0, knownFt: 46 } }),
           21.739130, 1e-5, "calib · which reads back as 21.74 pixels per foot");
    t.near(cad.scaleOf({ calib: { ax: 20, ay: 60, bx: 20, by: 260, knownFt: 12.5 } }),
           0.0625, 1e-12, "calib · a vertical baseline calibrates the same way");

    t.eq(cad.scaleOf(null), null, "calib · no underlay has no scale");
    t.eq(cad.scaleOf({ dataUri: "x" }), null, "calib · an uncalibrated underlay has no scale");
    t.eq(cad.scaleOf({ calib: { ax: 0, ay: 0, bx: 100, by: 0, knownFt: 0 } }), null,
         "calib · a known distance of zero is refused, not divided by");
    t.eq(cad.scaleOf({ calib: { ax: 0, ay: 0, bx: 100, by: 0, knownFt: -5 } }), null,
         "calib · a negative distance is refused");
    t.eq(cad.scaleOf({ calib: { ax: 40, ay: 40, bx: 40, by: 40, knownFt: 10 } }), null,
         "calib · two points at the same pixel give no scale rather than infinity");

    /* recalibrating replaces the claim outright */
    var u = { dataUri: "x", calib: { ax: 0, ay: 0, bx: 500, by: 0, knownFt: 50 }, opacity: 0.35 };
    t.near(cad.scaleOf(u), 0.1, 1e-12, "calib · first calibration");
    u.calib = { ax: 0, ay: 0, bx: 500, by: 0, knownFt: 25 };
    t.near(cad.scaleOf(u), 0.05, 1e-12, "calib · re-calibrating over the same baseline halves the scale");
  })();

  /* ============================================================
     6. fromPlan
     ============================================================ */

  t.suite("cad · fromPlan builds a model from a weights.js plan");
  (function () {
    t.eq(cad.fromPlan("no-such-plan"), null, "fromPlan · an unknown plan id returns null, not a guess");

    /* Four of the five plans declare enough to be approved as drawn. The
       fifth does not, and the error it produces is named here rather than
       tolerated: Townhome 1220 states that its joist piece count follows
       whatever spacing the solver picks, so no spacing can be read back out
       of it, and a human has to declare one before this geometry passes the
       gate. That is the intended outcome, not a gap. */
    var EXPECT_ERRORS = {
      "townhome-1220": ["framing-no-spacing", "framing-no-spacing"]
    };

    FM.weights.PLANS.forEach(function (p) {
      var m = cad.fromPlan(p.id);
      var rows = cad.validate(m);
      var e = errs(rows);
      var want = EXPECT_ERRORS[p.id] || [];
      t.eq(codes(e).join(","), want.join(","),
           "fromPlan · " + p.id + " produces exactly the errors it should" +
           (e.length ? " (got: " + e[0].text.slice(0, 90) + ")" : " — none"));
      t.eq(m.version, cad.MODEL_VERSION, "fromPlan · " + p.id + " is stamped with the model version");
      t.truthy(m.levels[0].walls.length >= 4,
               "fromPlan · " + p.id + " draws at least the four envelope walls");
      t.eq(cad.toJSON(clone(m)), cad.toJSON(m),
           "fromPlan · " + p.id + " round-trips through JSON unchanged");

      /* the seam that stopped the pipeline once: a wall with no thickness
         gives the takeoff no clear span, and it is right to refuse */
      var noThick = m.levels[0].walls.filter(function (w) { return w.thicknessIn === null; });
      t.eq(noThick.length, 0,
           "fromPlan · " + p.id + " gives every wall a thickness — the takeoff measures between faces");

      /* and it is declared as assumed rather than passed off as read */
      t.truthy(has(rows, "wall-thickness-assumed"),
               "fromPlan · " + p.id + " reports that thickness was assumed, not read from the plan");
      t.truthy(row(rows, "wall-thickness-assumed").text.indexOf("ASSUMED") !== -1,
               "fromPlan · " + p.id + " says the word out loud");

      /* every wall height comes from the packs' one declared plate */
      var noHeight = m.levels[0].walls.filter(function (w) { return w.heightFt === null; });
      t.eq(noHeight.length, 0, "fromPlan · " + p.id + " gives every wall a height");
    });
  })();

  t.suite("cad · fromPlan · Starter 1210, the simplest complete house");
  (function () {
    var m = cad.fromPlan("starter-1210");
    var L = m.levels[0];
    var st = cad.stats(m);

    t.eq(st.walls, 4, "starter · four walls, because the plan says there is no third bearing line");
    t.eq(st.bearingWalls, 2, "starter · two of them bear");
    t.near(st.areaSf, 1472, 1e-6, "starter · 46 x 32 = 1,472 sf, the plan's own underRoofSf");
    t.near(cad.wallLength(L.walls[0]), 46, 1e-9, "starter · the front wall is the 46 ft face");
    t.eq(L.walls[0].bearing, true, "starter · the 46 ft front wall carries the trusses");
    t.eq(L.walls[1].bearing, false, "starter · the 32 ft gable end does not");
    t.eq(L.walls[2].bearing, true, "starter · the 46 ft rear wall does");
    t.eq(L.walls[3].bearing, false, "starter · the other gable end does not");
    t.near(L.topPlateFt, 109.125 / 12, 1e-9,
           "starter · the top plate is the 109.125 in precut every region pack declares");

    t.eq(st.framing, 1, "starter · one framing region — the roof");
    t.eq(L.framing[0].kind, "roof", "starter · and it is a roof");
    t.eq(L.framing[0].directionDeg, 90,
         "starter · the trusses run along +y, because the 32 ft span is the depth");
    t.eq(L.framing[0].spacingIn, 24, "starter · at the plan's declared 24 in o.c.");
    t.eq(L.framing[0].bearsOn.join(","), "W1,W3", "starter · bearing on the two 46 ft walls");

    t.eq(st.openings, 14, "starter · 8 windows + entry + slider + garage + 3 gable windows");
    var garage = L.openings.filter(function (o) { return o.kind === "garage"; });
    t.eq(garage.length, 1, "starter · one garage door");
    t.eq(garage[0].wallId, "W1", "starter · in the front wall, which the mark says is a bearing line");
    t.near(garage[0].widthFt, 9.67 - 2 * 4.5 / 12, 1e-9,
           "starter · its rough opening is the 9.67 ft header span less 4.5 in of bearing each end");
    t.near(garage[0].headHeightFt, 7, 1e-9, "starter · at the 84 in head height the mark declares");
    var slider = L.openings.filter(function (o) { return o.kind === "slider"; });
    t.eq(slider[0].wallId, "W3", "starter · the REAR slider is in the rear wall");
    var doors = L.openings.filter(function (o) { return o.kind === "door"; });
    t.eq(doors[0].wallId, "W1", "starter · the FRONT entry door is in the front wall");

    /* the gable-end windows land in the walls that are not bearing lines */
    var gable = L.openings.filter(function (o) { return o.wallId === "W2" || o.wallId === "W4"; });
    t.eq(gable.length, 3, "starter · the three gable-end windows are in the two gable walls");

    /* every one of them is honest about not being located */
    var placed = L.openings.filter(function (o) { return o.offsetBasis === "placeholder"; });
    t.eq(placed.length, 14, "starter · every opening is flagged as a placeholder position");
    var rows = cad.validate(m);
    t.eq(rows.filter(function (r) { return r.code === "opening-placeholder-offset"; }).length, 4,
         "starter · reported once per wall, not once per opening");
    t.eq(errs(rows).length, 0, "starter · and none of it blocks the gate");

    /* the two things the plan sizes but does not locate */
    var un = m.unresolved.map(function (u) { return u.what; }).join(" | ");
    t.truthy(un.indexOf("covered entry") !== -1,
             "starter · the 8 x 6 covered entry is named as unresolved, not drawn somewhere");
    t.truthy(un.indexOf("garage walls") !== -1,
             "starter · so are the garage walls, whose position the plan does not give");
    t.eq(m.unresolved.length, 2, "starter · and nothing else is left hanging");
  })();

  t.suite("cad · fromPlan · Townhome 1220, where the joist bays locate a bearing line");
  (function () {
    var m = cad.fromPlan("townhome-1220");
    var L = m.levels[0];
    var st = cad.stats(m);

    t.eq(st.walls, 5, "townhome · four envelope walls plus the interior bearing line");
    t.near(st.areaSf, 720, 1e-6, "townhome · 20 x 36 = 720 sf, the plan's own grossSfPerFloor");
    var interior = L.walls[4];
    t.eq(interior.exterior, false, "townhome · the fifth wall is interior");
    t.eq(interior.bearing, true, "townhome · and it bears");
    t.near(interior.x1, 11, 1e-9,
           "townhome · at 11 ft — FJ-1's 11 ft bay and FJ-2's 9 ft bay add to the 20 ft width");
    t.near(interior.x2, 11, 1e-9, "townhome · running front to back");
    t.near(interior.y2 - interior.y1, 36, 1e-9, "townhome · the full 36 ft depth");

    t.eq(st.framing, 3, "townhome · the roof plus two floor bays");
    t.eq(L.framing[0].kind, "roof", "townhome · the roof spans the 20 ft width party wall to party wall");
    t.eq(L.framing[0].directionDeg, 0, "townhome · so the trusses run along +x");
    t.eq(L.framing[0].bearsOn.join(","), "W4,W2", "townhome · onto the two 36 ft party walls");
    t.eq(L.framing[1].kind, "floor", "townhome · the second bay is the 11 ft floor bay");
    t.eq(L.framing[1].bearsOn.join(","), "W4,W5", "townhome · from the left party wall to the line");
    t.eq(L.framing[2].bearsOn.join(","), "W5,W2", "townhome · and from the line to the right");
    t.eq(L.framing[1].spacingIn, null,
         "townhome · with no joist spacing, because the plan says the solver picks it");

    t.eq(st.openings, 1, "townhome · only the garage door is a first-floor exterior opening");
    t.eq(L.openings[0].wallId, "W1", "townhome · in the front wall, as its label says");

    var un = m.unresolved.map(function (u) { return u.what; }).join(" | ");
    t.truthy(un.indexOf("party wall") !== -1,
             "townhome · which wall is the shared party wall is not declared, and is not guessed");
    t.truthy(un.indexOf("upper storey") !== -1,
             "townhome · the second storey is named as absent from this model");
    t.truthy(un.indexOf("covered patio") !== -1,
             "townhome · the 20 x 8 patio has no element here and says so");
    t.truthy(un.indexOf("HDR-ST") !== -1,
             "townhome · the stair header is not an opening in a wall and says why");
    var trows = cad.validate(m);
    t.eq(codes(errs(trows)).join(","), "framing-no-spacing,framing-no-spacing",
         "townhome · the only errors are the two floor bays with no declared spacing");
    t.truthy(row(trows, "framing-no-spacing").text.indexOf("consequence") !== -1,
             "townhome · and the finding explains why the piece count cannot be read back as one");
    t.truthy(row(trows, "framing-no-spacing").text.indexOf("16 in o.c.") !== -1,
             "townhome · while still handing the reviewer what the counts are consistent with");
  })();

  t.suite("cad · fromPlan · the plans whose geometry does not determine a layout");
  (function () {
    /* Two-Story 2450 declares no truss span, so nothing says which way
       anything runs. The model refuses to pick, and says so. */
    var m = cad.fromPlan("two-story-2450");
    var rows = cad.validate(m);
    t.eq(cad.stats(m).framing, 0,
         "two-story · no framing region, because no declared number gives a span direction");
    t.eq(row(rows, "level-no-framing").severity, "warn",
         "two-story · the missing framing is a warn, so the model is still readable");
    t.eq(errs(rows).length, 0, "two-story · and it produces no errors");
    var un = m.unresolved.map(function (u) { return u.what; }).join(" | ");
    t.truthy(un.indexOf("roof span direction") !== -1,
             "two-story · the roof span direction is named as undetermined");

    /* the centre bearing line IS located — a 13.5 ft FRONT bay starts at the
       front wall, so the line behind it is fixed even though the bays do not
       add up to the footprint depth */
    var mid = m.levels[0].walls[4];
    t.eq(m.levels[0].walls.length, 5, "two-story · the centre bearing line is drawn");
    t.eq(mid.exterior, false, "two-story · as an interior wall");
    t.eq(mid.bearing, true, "two-story · that bears");
    t.near(mid.y1, 13.5, 1e-9, "two-story · 13.5 ft back from the front wall, FJ-1's front bay");
    t.near(mid.y2, 13.5, 1e-9, "two-story · running side to side");
    t.truthy(un.indexOf("floor bays") !== -1,
             "two-story · but the bays themselves are unresolved — they do not span the 40 ft width");
    t.truthy(m.unresolved.filter(function (u) {
      return u.what.indexOf("floor bays") !== -1;
    })[0].why.indexOf("13.5") !== -1,
             "two-story · and the finding shows the declared bay depths it could not place");

    /* Coastal Duplex 1600: one of the bearing walls is a party wall and
       the plan does not say which, so no opening is placed in either. */
    var c = cad.fromPlan("coastal-duplex-1600");
    t.eq(cad.stats(c).openings, 0,
         "coastal · no opening is placed, because one candidate wall may be the party wall");
    t.eq(cad.stats(c).bearingWalls, 2, "coastal · the 26 ft truss span still marks two walls bearing");
    t.eq(c.levels[0].framing[0].spacingIn, 24,
         "coastal · the roof spacing is recovered from T-1's count: 32 ft of run across 17 trusses");
    t.truthy(c.levels[0].framing[0].basis.indexOf("DERIVED") !== -1,
             "coastal · and the region says the spacing was derived, not declared");
    t.eq(errs(cad.validate(c)).length, 0, "coastal · no errors");

    /* Sunbelt Ranch 1850 carries two marks for one garage opening and they
       disagree about which wall it is in. */
    var s = cad.fromPlan("sunbelt-ranch-1850");
    t.eq(cad.stats(s).openings, 15, "sunbelt · 14 windows and the rear slider are placed");
    t.eq(s.levels[0].openings.filter(function (o) { return o.kind === "garage"; }).length, 0,
         "sunbelt · the garage door is NOT placed");
    var g = s.unresolved.filter(function (u) { return u.what.indexOf("16.7 ft opening") !== -1; })[0];
    t.truthy(!!g, "sunbelt · and the reason is recorded against the opening");
    t.truthy(g.why.indexOf("HDR-GAR-G") !== -1 && g.why.indexOf("HDR-GAR-B") !== -1,
             "sunbelt · naming both marks that describe it");
    t.truthy(g.why.indexOf("truss direction") !== -1,
             "sunbelt · and the one fact that would settle it");
    t.eq(errs(cad.validate(s)).length, 0, "sunbelt · no errors");
  })();

  t.suite("cad · fromPlan · master-set variants");
  (function () {
    var base1 = cad.fromPlan("starter-1210");
    var carport = cad.fromPlan("starter-1210", "c");
    t.eq(cad.stats(base1).openings, 14, "variant · the base elevation has 14 openings");
    t.eq(cad.stats(carport).openings, 13,
         "variant · Elevation C deletes the garage header, so the opening goes with it");
    t.eq(carport.source.variantId, "c", "variant · the model records which variant it was built from");
    t.eq(errs(cad.validate(carport)).length, 0, "variant · and it still validates clean");

    var bogus = cad.fromPlan("starter-1210", "not-a-variant");
    t.eq(cad.stats(bogus).openings, 14,
         "variant · an unknown variant falls back to the base plan rather than throwing");
    t.truthy(bogus.unresolved.filter(function (u) {
      return u.what.indexOf("not-a-variant") !== -1;
    }).length === 1, "variant · and it says out loud that the variant was not applied");
  })();

  /* ============================================================
     7. geometry helpers the canvas leans on
     ============================================================ */

  t.suite("cad · geometry helpers");
  (function () {
    var w = { id: "W1", x1: 0, y1: 0, x2: 3, y2: 4 };
    t.near(cad.wallLength(w), 5, 1e-12, "geom · a 3-4-5 wall is 5 ft long");
    t.near(cad.wallAngleDeg({ x1: 0, y1: 0, x2: 0, y2: 5 }), 90, 1e-12, "geom · a wall up +y is 90 degrees");
    var p = cad.pointAlong(w, 2.5);
    t.near(p.x, 1.5, 1e-12, "geom · halfway along is 1.5 in x");
    t.near(p.y, 2, 1e-12, "geom · and 2.0 in y");

    var pr = cad.projectOnWall({ x1: 0, y1: 0, x2: 10, y2: 0 }, 4, 3);
    t.near(pr.t, 4, 1e-12, "geom · a point 3 ft off the wall lands 4 ft along it");
    t.near(pr.d, 3, 1e-12, "geom · at a distance of 3 ft");

    t.truthy(!!cad.segCross({ x1: 0, y1: 0, x2: 10, y2: 0 }, { x1: 5, y1: -5, x2: 5, y2: 5 }),
             "geom · two segments crossing at an interior point cross");
    t.eq(cad.segCross({ x1: 0, y1: 0, x2: 10, y2: 0 }, { x1: 5, y1: 0, x2: 5, y2: 5 }), null,
         "geom · a T-junction does not");
    t.eq(cad.segCross({ x1: 0, y1: 0, x2: 10, y2: 0 }, { x1: 0, y1: 0, x2: 0, y2: 5 }), null,
         "geom · a shared corner does not");
    t.eq(cad.segCross({ x1: 0, y1: 0, x2: 10, y2: 0 }, { x1: 0, y1: 2, x2: 10, y2: 2 }), null,
         "geom · parallel walls do not");

    t.near(cad.polyArea([[0, 0], [10, 0], [10, 4], [0, 4]]), 40, 1e-12, "geom · a 10 x 4 region is 40 sf");
    t.near(cad.polyArea([[0, 0], [0, 4], [10, 4], [10, 0]]), 40, 1e-12,
           "geom · wound the other way it is still 40 sf");
    t.eq(cad.pointInPoly([[0, 0], [10, 0], [10, 4], [0, 4]], 5, 2), true, "geom · a point inside is inside");
    t.eq(cad.pointInPoly([[0, 0], [10, 0], [10, 4], [0, 4]], 12, 2), false, "geom · one outside is not");

    t.eq(cad.ftIn(46), "46'-0\"", "geom · 46.0 ft reads as 46'-0\"");
    t.eq(cad.ftIn(9.67), "9'-8\"", "geom · 9.67 ft reads as 9'-8\"");
    t.eq(cad.ftIn(6.6667), "6'-8\"", "geom · a 6'-8\" head height reads back as one");
    t.eq(cad.ftIn(0.5), "0'-6\"", "geom · the default 6 in grid reads as 0'-6\"");
    t.eq(cad.ftIn(null), "—", "geom · an undeclared length does not read as zero");
  })();
};

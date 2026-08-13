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

    /* All five plans now draw with no errors at all, and the entry that used
       to sit here is gone rather than relaxed. Townhome 1220 used to produce
       two `framing-no-spacing` errors because FJ-1 said its piece count
       "follows the spacing the solver picks" — which is backwards: the
       solver picks a SECTION for a demand, and the spacing is an INPUT to
       the tributary that demand is computed from, so it can only ever be a
       plan declaration. weights.js now declares geometry.floorSpacingIn = 16
       with that reasoning written out, and all three of the plan's joist
       counts read back to it (36/(16/12) + 1 = 28 exactly). The errors are
       gone because the plan closed the hole, not because this map stopped
       looking: an empty map means EVERY plan must validate error-free.

       This assertion is the gate, so it stays an equality on the whole code
       list rather than a count — a plan that starts producing a different
       error must fail here by name. */
    var EXPECT_ERRORS = {};

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
    var plan = FM.weights.planById("starter-1210");
    var dr = plan.geometry.drawn;
    var m = cad.fromPlan("starter-1210");
    var L = m.levels[0];
    var st = cad.stats(m);

    /* SIX walls, not four. The plan used to state the garage's size and not
       its position, so the two garage walls were an unresolved hole; it now
       declares geometry.drawn.garageAt (front face at 34 ft) and both walls
       endpoint by endpoint, so they are DRAWN. "No third bearing line" is
       still the plan's claim and is still true — it is a claim about what
       BEARS, and both garage walls are drawn non-bearing below, which is
       that claim shown on the drawing instead of asserted in prose. */
    t.eq(st.walls, 6, "starter · six walls — the four envelope walls plus the two garage walls");
    t.eq(st.bearingWalls, 2, "starter · two of them bear, and the plan says there is no third line");
    t.eq(st.exteriorWalls, 4, "starter · four of them are envelope, so the garage walls are interior");
    t.near(st.areaSf, 1472, 1e-6, "starter · 46 x 32 = 1,472 sf, the plan's own underRoofSf");
    t.near(cad.wallLength(L.walls[0]), 46, 1e-9, "starter · the front wall is the 46 ft face");
    t.eq(L.walls[0].bearing, true, "starter · the 46 ft front wall carries the trusses");
    t.eq(L.walls[1].bearing, false, "starter · the 32 ft gable end does not");
    t.eq(L.walls[2].bearing, true, "starter · the 46 ft rear wall does");
    t.eq(L.walls[3].bearing, false, "starter · the other gable end does not");
    t.near(L.topPlateFt, 109.125 / 12, 1e-9,
           "starter · the top plate is the 109.125 in precut every region pack declares");

    /* the garage walls, endpoint for endpoint against what the plan declares
       — read out of weights.js rather than typed here, so the drawing and
       the declaration cannot drift apart without this failing */
    dr.interiorWalls.forEach(function (d, i) {
      var w = cad.wallById(L, d.id);
      t.truthy(!!w, "starter · " + d.id + " is drawn, because the plan now locates it");
      t.eq([w.x1, w.y1, w.x2, w.y2].join(","), d.fromFt.concat(d.toFt).join(","),
           "starter · " + d.id + " runs (" + d.fromFt.join(", ") + ") to (" + d.toFt.join(", ") +
           ") ft, exactly as geometry.drawn.interiorWalls declares it");
      t.eq(w.exterior, false, "starter · " + d.id + " is an interior wall");
      t.eq(w.bearing, false,
           "starter · and it does NOT bear — the 32 ft trusses clear-span onto the two 46 ft walls" +
           (i === 0 ? ", so a wall running with them carries none" : ""));
    });
    /* 46 - 12 = 34 ft: the garage bay closes against the right envelope wall */
    t.near(cad.wallById(L, "GW1").x1, plan.geometry.footprintFt[0] - plan.geometry.garage.widthFt, 1e-9,
           "starter · the garage's inboard wall stands a garage width in from the right corner");
    t.near(cad.wallLength(cad.wallById(L, "GW2")), plan.geometry.garage.widthFt, 1e-9,
           "starter · and its rear wall is the 12 ft garage width");
    t.near(cad.wallLength(cad.wallById(L, "GW1")), plan.geometry.garage.depthFt, 1e-9,
           "starter · by the 22 ft garage depth — 12 x 22 = 264 sf, the plan's own garage.sf");

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

    /* TWO of the fourteen are PINNED, and they are exactly the two marks that
       declare an `opening` block in weights.js — the front door and the
       garage door. Everything else on this plan is still a count and a width
       with no position, and still says so. The pinned pair is read out of
       the plan here, not typed in, so a mark that gains or loses a declared
       offset moves this assertion with it. */
    var pins = plan.marks.filter(function (mk) {
      return mk.opening && typeof mk.opening.offsetFt === "number";
    });
    t.eq(pins.length, 2, "starter · weights.js declares an offset for exactly two of its marks");
    t.eq(pins.map(function (mk) { return mk.id; }).join(","), "HDR-ENT,HDR-GAR",
         "starter · the front entry door and the garage door");
    var pinned = L.openings.filter(function (o) { return o.offsetBasis === "plan"; });
    t.eq(pinned.length, 2, "starter · and both are drawn at the offset the plan gives, not a placeholder");
    pins.forEach(function (mk) {
      var hit = L.openings.filter(function (o) { return o.note.indexOf("From mark " + mk.id + ":") === 0; })[0];
      t.near(hit.offsetFt, mk.opening.offsetFt, 1e-9,
             "starter · " + mk.id + " sits at the " + mk.opening.offsetFt +
             " ft its own `opening` block declares");
      t.eq(hit.offsetBasis, "plan", "starter · and " + mk.id + " is marked as read from the plan");
    });
    /* and each declared offset is the centre of the thing the plan says it is
       centred on: the door on the 8 ft stoop that runs 24-32 ft, the garage
       door in the 12 ft bay that runs 34-46 ft */
    var entryAp = dr.appendages[0];
    t.near(doors[0].offsetFt + doors[0].widthFt / 2, entryAp.offsetFt + entryAp.widthFt / 2, 1e-9,
           "starter · the entry door centres on the 8 ft covered entry at 28 ft, as its note says");
    t.near(garage[0].offsetFt + garage[0].widthFt / 2,
           dr.garageAt.offsetFt + plan.geometry.garage.widthFt / 2, 1e-9,
           "starter · and the garage door centres in the 12 ft garage bay at 40 ft");

    /* the other twelve are honest about not being located */
    var placed = L.openings.filter(function (o) { return o.offsetBasis === "placeholder"; });
    t.eq(placed.length, 12, "starter · the other twelve are flagged as placeholder positions");
    t.eq(placed.length + pinned.length, st.openings,
         "starter · every opening is one or the other — none is silently unlabelled");
    var rows = cad.validate(m);
    t.eq(rows.filter(function (r) { return r.code === "opening-placeholder-offset"; }).length, 4,
         "starter · reported once per wall, not once per opening");
    t.eq(errs(rows).length, 0, "starter · and none of it blocks the gate");

    /* ONE thing the plan sizes but this model cannot draw. The garage walls
       used to be the second: the plan declared the garage's size and not its
       position, and drawing it anywhere would have been an invention. It now
       declares the position, so they are walls above rather than a hole here
       — and the entry stays, because what is missing there is not a
       dimension but an ELEMENT: this model has no beam or post (§Q.2). */
    var un = m.unresolved.map(function (u) { return u.what; }).join(" | ");
    t.truthy(un.indexOf("covered entry") !== -1,
             "starter · the 8 x 6 covered entry is named as unresolved, not drawn somewhere");
    t.truthy(m.unresolved[0].why.indexOf("position IS declared") !== -1 &&
             m.unresolved[0].why.indexOf("no beam, post or column entity") !== -1,
             "starter · and the reason is the missing ELEMENT, not a missing dimension");
    t.eq(un.indexOf("garage walls"), -1,
         "starter · the garage walls are NOT unresolved any more — the plan locates them and they are drawn");
    t.eq(m.unresolved.length, 1, "starter · and nothing else is left hanging");
  })();

  t.suite("cad · fromPlan · Townhome 1220, where the joist bays locate a bearing line");
  (function () {
    var plan = FM.weights.planById("townhome-1220");
    var dr = plan.geometry.drawn;
    var m = cad.fromPlan("townhome-1220");
    var L = m.levels[0];
    var st = cad.stats(m);

    /* TWO levels now: the plan declares its upper storey outline, so the
       second floor is real geometry instead of an unresolved hole. The
       convention the model keeps — and the reason the floor deck is on L2
       and not L1 — is that a level owns the deck at its BASE, plus the roof
       if it is the topmost. So L1 is a slab with walls and no framing, and
       L2 owns the second-floor deck it stands on and the roof over it. */
    t.eq(st.levels, 2, "townhome · two levels, because the plan declares the upper storey outline");
    t.eq(L.framing.length, 0, "townhome · the first floor is a slab: no framing of its own");
    var U = m.levels[1];
    t.eq(U.id, "L2", "townhome · and the second level is the L2 the plan names");

    t.eq(st.walls, 11, "townhome · six walls on the first floor and five on the second");
    t.eq(L.walls.length, 6,
         "townhome · four envelope walls, the interior bearing line and the garage rear wall");
    t.eq(U.walls.length, 5, "townhome · and the second floor stacks four envelope walls plus BL1");
    t.near(st.areaSf, 720, 1e-6, "townhome · 20 x 36 = 720 sf, the plan's own grossSfPerFloor");
    var interior = L.walls[4];
    t.eq(interior.id, "BL1", "townhome · the fifth wall is the bearing line the plan names BL1");
    t.eq(interior.exterior, false, "townhome · the fifth wall is interior");
    t.eq(interior.bearing, true, "townhome · and it bears");
    t.near(interior.x1, 11, 1e-9,
           "townhome · at 11 ft — FJ-1's 11 ft bay and FJ-2's 9 ft bay add to the 20 ft width");
    t.near(interior.x2, 11, 1e-9, "townhome · running front to back");
    t.near(interior.y2 - interior.y1, 36, 1e-9, "townhome · the full 36 ft depth");
    /* the same line stacks, and on the second floor it carries nothing —
       the trusses clear-span party wall to party wall over it */
    t.eq(cad.wallById(U, "L2-BL1").bearing, false,
         "townhome · BL1 stacks to the second floor and bears NOTHING there, as the plan declares");

    /* FOUR regions, not three: the roof and THREE floor bays. FJ-2's 9 ft
       bay and FJ-3's 9 ft bay share a span and are not the same region —
       [11,0,20,10] is the tiled bath-and-laundry stretch over the garage and
       [11,10,20,36] is the 26 ft behind it, and FJ-3 carries a wet-assembly
       10 psf that FJ-2 does not. Folding them together would lose that. */
    t.eq(st.framing, 4, "townhome · the roof plus THREE floor bays");
    t.eq(U.framing.length, 4, "townhome · all four sit on L2 — the deck at its base and the roof over it");
    t.eq(dr.framing.length, 4, "townhome · which is one region per geometry.drawn.framing entry");
    function reg(id) {
      var hit = null;
      U.framing.forEach(function (f) { if (f.id === id) hit = f; });
      return hit;
    }
    var roof = reg("L2-F-ROOF");
    t.eq(roof.kind, "roof", "townhome · the roof spans the 20 ft width party wall to party wall");
    t.eq(roof.directionDeg, 0, "townhome · so the trusses run along +x");
    t.eq(roof.bearsOn.join(","), "L2-W4,L2-W2",
         "townhome · onto the two 36 ft party walls OF THE SECOND FLOOR, which is what carries a roof");
    t.eq(roof.spacingIn, 24, "townhome · at the 24 in o.c. the plan declares for its trusses");
    t.eq(roof.system, "truss", "townhome · and it is a truss package, not a rafter");

    var flr1 = reg("L2-F-FLR-1");
    t.eq(flr1.kind, "floor", "townhome · F-FLR-1 is FJ-1's 11 ft bay");
    t.eq(flr1.bearsOn.join(","), "W4,BL1",
         "townhome · from the left party wall to the line — and on the FIRST floor, which is what " +
         "a second-floor deck bears on");
    t.eq(reg("L2-F-FLR-3").bearsOn.join(","), "BL1,W2", "townhome · FJ-3's bay runs line to right party wall");
    t.eq(reg("L2-F-FLR-2").bearsOn.join(","), "BL1,W2", "townhome · and so does FJ-2's");
    t.eq(reg("L2-F-FLR-3").polygon.map(function (p) { return p.join(" "); }).join(","),
         "11 0,20 0,20 10,11 10",
         "townhome · FJ-3 is the front 10 ft of the 9 ft bay, over the garage");
    t.eq(reg("L2-F-FLR-2").polygon.map(function (p) { return p.join(" "); }).join(","),
         "11 10,20 10,20 36,11 36",
         "townhome · and FJ-2 is the 26 ft behind it — 36 - 10, FJ-2's own declared run");

    /* the spacing is DECLARED, and it is declared because it has to be: the
       solver picks a section for a demand, and the spacing is an input to
       the tributary that demand is computed from, so it can never be an
       output. All three joist counts read back to it. */
    t.eq(plan.geometry.floorSpacingIn, 16, "townhome · the plan declares 16 in o.c. floor spacing");
    U.framing.forEach(function (f) {
      if (f.kind !== "floor") return;
      t.eq(f.spacingIn, plan.geometry.floorSpacingIn,
           "townhome · " + f.id + " carries the plan's declared 16 in o.c., not a guess");
    });
    var fj1 = plan.marks.filter(function (mk) { return mk.id === "FJ-1"; })[0];
    t.eq(Math.floor(fj1.runFt / (plan.geometry.floorSpacingIn / 12)) + 1, fj1.count,
         "townhome · and FJ-1's count of 28 reads back as 36/(16/12) + 1, which is the check on it");

    t.eq(st.openings, 2, "townhome · the garage door, and the break in the bearing line");
    var gar = L.openings.filter(function (o) { return o.kind === "garage"; })[0];
    t.eq(gar.wallId, "W1", "townhome · the garage door is in the front wall, as its label says");
    t.eq(gar.offsetBasis, "placeholder",
         "townhome · at a placeholder offset — HDR-GAR declares no `opening` block");
    /* but a placeholder still may not contradict the plan: the garage runs
       0-11 ft of the front face, so a door laid out across the whole 20 ft
       wall would cross the bearing line at 11 ft and stand in the great room */
    t.truthy(gar.offsetFt >= dr.garageAt.offsetFt &&
             gar.offsetFt + gar.widthFt <= dr.garageAt.offsetFt + plan.geometry.garage.widthFt,
             "townhome · and inside the 11 ft garage bay the plan declares, not across BL1 at 11 ft");
    t.near(gar.offsetFt + gar.widthFt / 2,
           dr.garageAt.offsetFt + plan.geometry.garage.widthFt / 2, 1e-9,
           "townhome · laid out centred in that bay, which is the only placement that favours neither jamb");

    /* GB-1's opening is the one this plan exists to pose: a 12 ft break in
       an INTERIOR bearing line, carried by a flush girder. It is not a
       window — a window is a hole in the envelope — and it used to be
       classified as one, which is wrong on a plan set and in the DXF. */
    var brk = L.openings.filter(function (o) { return o.wallId === "BL1"; })[0];
    t.eq(brk.kind, "passage",
         "townhome · the break in the bearing line is a PASSAGE, not a window — there is no outside here");
    t.eq(brk.offsetBasis, "plan", "townhome · its offset is declared on GB-1, not a placeholder");
    t.near(brk.offsetFt, 20, 1e-9, "townhome · 20 ft back, where the garage ends");
    t.near(brk.widthFt, 12, 1e-9, "townhome · and 12 ft wide — GB-1's span, which has no bearing declared");
    t.near(brk.offsetFt + brk.widthFt, 32, 1e-9,
           "townhome · so the line is interrupted from 20 to 32 ft, which is what GB-1's note says");
    t.truthy(brk.offsetFt + brk.widthFt < cad.wallLength(interior),
             "townhome · and the bearing line continues past it to the rear wall");

    var un = m.unresolved.map(function (u) { return u.what; }).join(" | ");
    t.eq(un.indexOf("party wall"), -1,
         "townhome · which wall is the party wall is no longer a hole — the plan declares BOTH sides are");
    t.eq(dr.partyWallSide, "both", "townhome · in geometry.drawn.partyWallSide");
    t.eq(un.indexOf("upper storey"), -1,
         "townhome · nor is the second storey — it is drawn above, from the plan's own outline");
    t.truthy(un.indexOf("covered patio") !== -1,
             "townhome · the 20 x 8 patio has no element here and says so");
    t.truthy(un.indexOf("HDR-ST") !== -1,
             "townhome · the stair header is not an opening in a wall and says why");
    t.truthy(un.indexOf("HDR-GAR") !== -1,
             "townhome · and the garage header is drawn but not sizeable — it carries a WALL");
    t.eq(m.unresolved.length, 3, "townhome · three holes, and nothing else is left hanging");
    var trows = cad.validate(m);
    t.eq(codes(errs(trows)).join(","), "",
         "townhome · and no errors at all — the two framing-no-spacing errors are gone because " +
         "the plan declares geometry.floorSpacingIn, not because this stopped checking");
    t.truthy(has(trows, "opening-no-head-height"),
             "townhome · GB-1 declares no head height, and that is still reported as a warn");
  })();

  t.suite("cad · fromPlan · the plans whose geometry does not determine a layout");
  (function () {
    /* Two-Story 2450 declares no truss span, so nothing says which way
       anything runs. The model refuses to pick, and says so. */
    var plan2450 = FM.weights.planById("two-story-2450");
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

    /* The centre bearing line is NOT drawn, and this is the assertion that
       has to stay hard. It is tempting to place it 13.5 ft back from the
       front wall, because FJ-1's front bay is 13.5 ft — and that is exactly
       the invention non-negotiable 2 forbids. A joist SPAN is the distance
       between two supports; it is not an offset from a corner, nothing on
       this plan says the front bay starts at the front wall, and the two
       bays it does name (13.5 + 15.0 = 28.5 ft) do not reach the 38 ft
       depth in the first place — the upper floor is 930 sf of a 1,520 sf
       first floor, so they need not touch either wall. Four plans in this
       build now declare geometry.drawn and get their interior lines drawn
       from it. This one does not, and it stays a named hole until it does. */
    t.eq(m.levels[0].walls.length, 4,
         "two-story · four walls: the centre bearing line is NOT drawn, because nothing locates it");
    t.eq(m.levels[0].walls.filter(function (w) { return !w.exterior; }).length, 0,
         "two-story · and no interior wall is invented from the bay depths");
    t.truthy(!plan2450.geometry.drawn,
             "two-story · which is the honest reading: this plan declares no geometry.drawn at all");
    var line = m.unresolved.filter(function (u) {
      return u.what.indexOf("interior bearing line") !== -1;
    })[0];
    t.truthy(!!line, "two-story · the interior bearing line is named as unresolved instead");
    t.truthy(line.why.indexOf("FJ-1 13.5 ft") !== -1 && line.why.indexOf("FJ-2 15.0 ft") !== -1,
             "two-story · and the finding shows the declared bay depths it could not place");
    t.truthy(line.why.indexOf("not a distance from a named corner") !== -1,
             "two-story · saying why a span is not an offset");
    t.truthy(line.why.indexOf("930 sf of a 1520 sf") !== -1,
             "two-story · and that the upper floor does not even cover the footprint");
    t.truthy(line.need.indexOf("geometry.drawn.interiorWalls") !== -1,
             "two-story · with what would have to be declared to close it");

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

    /* This plan is two storeys and its upper storey is not drawn, so the roof
       region has nowhere to sit but the FIRST-floor level — which shows it
       bearing on first-floor walls, when on the building it stands on the
       walls above them. That is a consequence of the missing level and it has
       to be said on the region, or the load path reads as one somebody chose. */
    t.eq(c.levels.length, 1, "coastal · the model carries one level, though the plan is two storeys");
    t.truthy(c.unresolved.filter(function (u) {
      return u.what.indexOf("upper storey") !== -1;
    }).length === 1, "coastal · the missing upper storey is a named hole");
    t.truthy(c.levels[0].framing[0].basis.indexOf("bears on the walls of the storey above") !== -1,
             "coastal · and the roof region says out loud that the walls under it are the wrong ones");
    t.eq(errs(cad.validate(c)).length, 0, "coastal · no errors");

    /* Sunbelt Ranch 1850 used to carry TWO marks for one 16'-8" garage
       opening — HDR-GAR-G reading it as a gable end at 2.0 ft of tributary
       and HDR-GAR-B as a truss bearing line at 11.0 ft — and this model
       refused to draw it, because two marks that disagree about which wall a
       hole is in cannot both be drawn and neither can be picked.

       weights.js settled it rather than carrying it: the garage door is in
       the street face, the street face is one of the two 50 ft walls, and
       bearingLines says those two walls ARE the bearing lines. The gable-end
       reading describes a condition this plan does not have, so HDR-GAR-G is
       deleted and HDR-GAR-B's tributary moved to 23.0 ft — half the 46 ft
       clear span, the same figure every other opening in that wall takes.
       So the opening is now drawn, at the offset the plan declares. */
    var plan1850 = FM.weights.planById("sunbelt-ranch-1850");
    var s = cad.fromPlan("sunbelt-ranch-1850");
    var sL = s.levels[0];
    t.eq(plan1850.marks.filter(function (mk) { return mk.id === "HDR-GAR-G"; }).length, 0,
         "sunbelt · the gable-end reading of the garage header is gone from the plan");
    t.eq(plan1850.marks.filter(function (mk) {
      return mk.role === "header" && Math.abs(mk.span - 16.67) < 1e-9;
    }).length, 1, "sunbelt · exactly one mark now describes the 16'-8\" hole");
    t.eq(cad.stats(s).openings, 15,
         "sunbelt · 13 of the 14 typical windows, the rear slider and the garage door");
    var sGar = sL.openings.filter(function (o) { return o.kind === "garage"; });
    t.eq(sGar.length, 1, "sunbelt · the garage door IS placed now, because only one mark describes it");
    t.eq(sGar[0].wallId, "W1", "sunbelt · in the front 50 ft wall, which is a truss bearing line");
    t.eq(sGar[0].offsetBasis, "plan", "sunbelt · at a declared offset, not a placeholder");
    t.near(sGar[0].offsetFt, 31.915, 1e-9,
           "sunbelt · 31.915 ft, which is HDR-GAR-B's own `opening` block");
    t.near(sGar[0].offsetFt + sGar[0].widthFt / 2,
           plan1850.geometry.drawn.garageAt.offsetFt + plan1850.geometry.garage.widthFt / 2, 1e-9,
           "sunbelt · centred in the 20 ft garage bay that runs 30-50 ft along that face");
    t.eq(s.unresolved.filter(function (u) { return u.what.indexOf("16.7 ft opening") !== -1; }).length, 0,
         "sunbelt · and the two-marks-one-hole finding is gone with the second mark");

    /* what has NOT closed: the plan declares 14 typical windows and does not
       say which face each is in. Thirteen fit the two bearing walls once the
       garage door and the slider are in them; the fourteenth does not, and
       it is named rather than crammed in or dropped. */
    t.eq(sL.openings.filter(function (o) { return o.kind === "window"; }).length, 13,
         "sunbelt · 13 of HDR-W's 14 windows are drawn");
    var over = s.unresolved.filter(function (u) { return u.what.indexOf("HDR-W") !== -1; })[0];
    t.truthy(!!over, "sunbelt · and the fourteenth is named as one the wall will not hold");
    t.truthy(over.what.indexOf("W1") !== -1,
             "sunbelt · against the wall it could not go in");
    t.truthy(over.why.indexOf("jack and king studs") !== -1,
             "sunbelt · with the reason it will not fit");
    t.truthy(over.need.indexOf("opening: {level, face}") !== -1,
             "sunbelt · and what the plan would have to say to place it");
    t.eq(errs(cad.validate(s)).length, 0, "sunbelt · no errors");
  })();

  t.suite("cad · fromPlan · master-set variants");
  (function () {
    var base1 = cad.fromPlan("starter-1210");
    var carport = cad.fromPlan("starter-1210", "c");
    function garageCount(m) {
      return m.levels[0].openings.filter(function (o) { return o.kind === "garage"; }).length;
    }
    t.eq(cad.stats(base1).openings, 14, "variant · the base elevation has 14 openings");
    t.eq(garageCount(base1), 1, "variant · one of them the garage door");
    t.eq(cad.stats(carport).openings, 13,
         "variant · Elevation C deletes the garage header, so the opening goes with it");
    /* the count alone would pass if ANY opening had gone missing — it is the
       garage door specifically, because a carport has no door */
    t.eq(garageCount(carport), 0, "variant · and it is the garage door that is gone, not some other hole");
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

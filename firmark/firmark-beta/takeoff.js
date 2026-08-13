/* ============================================================
   takeoff.js — FM.takeoff · geometry -> structural demands

   This is the module where a wrong answer is most dangerous. A tributary
   width that is quietly wrong produces a confident, wrong member on a
   drawing somebody stamps. So the whole file is built around one rule:

       EVERY NUMBER IS EITHER DERIVED FROM THE DRAWING OR REFUSED.

   There is no default span, no assumed tributary, no "half, probably", no
   rounding up to be safe. Padding is still an invented number — it just
   hides the question instead of asking it.

   Two lists carry that discipline out of this file:

     derivations[]  every field of every mark, with the ids it came from and
                    the arithmetic in words. A reviewer at approval gate 2
                    must be able to reconstruct the takeoff without reading
                    code. A number with no derivation is a defect.

     unresolved[]   what the geometry does not determine, why it does not,
                    and precisely what a human must supply. These are the
                    blocking items on the gate. An empty unresolved list is
                    a claim, and it has to be earned.

   The output marks are exactly the shape weights.js PLANS use, so
   FM.solver.solvePlan consumes them unchanged.

   ---- the four rules, stated as an engineer would state them ----

   SPAN         The clear distance between the two walls the framing bears
                on, measured along the framing direction, face to face:
                (centreline to centreline) - t_a/2 - t_b/2. It is measured
                at both ends of the region's run; if those two disagree by
                more than SPAN_VARY_FT the region is not one simple span and
                it is refused, not averaged.
                For a header, the span is the clear opening between jacks.

                DISCLOSED: calc-spec's symbol table defines L as "clear
                span, simple span, center-to-center of bearings", which is
                one bearing length LONGER than the clear distance (0.25 ft
                at a 3 in bearing — about 1% of moment on a 12 ft span, and
                the direction that matters). The FM.takeoff contract says
                clear distance, so clear distance is what is emitted; the
                centre-to-centre value is printed in the span derivation of
                every mark so a reviewer can rule on it rather than discover
                it. This module does not choose the larger number on the
                reviewer's behalf.

   TRIBUTARY    Half the clear span of each framing region that bears on the
                support, summed over the sides that carry framing:
                t = L_left/2 + L_right/2.
                It is emitted ONLY when every contributing span is
                determined. One side framed and the other side undetermined
                is refused. One side framed on a wall declared EXTERIOR is
                determined — the outboard side is outside the building — and
                the derivation says so out loud. One side framed on an
                INTERIOR wall is refused: the other side of an interior wall
                is inside the building, so framing there is either missing
                from the model or bears somewhere the model does not say.

                DISCLOSED: half the CLEAR span, consistent with the span
                rule above, which is t/4 (about 0.11 ft on a 5.5 in wall)
                less than half the centre-to-centre span. And roof overhang
                / eave tributary is NOT included, because the geometry model
                has no eave: a 1 ft overhang on a 16 ft tributary is 6% of
                load that is not here. Both are flagged in warnings.

   BEARING      Header bearing length = jacks x 1.5 in, jacks taken from the
                clear opening: 1 under 6 ft, 2 under 12 ft, 3 under 18 ft,
                refuse at 18 ft and over. Declared on the mark and marked
                `derived` so a reviewer can challenge it. It is a TAKEOFF
                CONVENTION, not a table lookup — IRC R602.7 sets jacks from
                width AND load, and this rule reads only width.

   COUNT        count = ceil(runFt x 12 / spacingIn) + 1, where runFt is the
                region's extent measured perpendicular to the framing
                direction. n bays plus one member: a member at each end of
                the run. This is the same arithmetic solver.js pieceCount()
                uses, so the two cannot disagree when the spacing survives
                the solver's spacing search.

   ---- what this module refuses to determine, and why ----

   * Any framing region with fewer or more than two bearing LINES across it.
     One line is undetermined. Three is a multi-span condition, and
     calc-spec §8.1 admits simple spans only — the human splits it into bays.
   * Any region that is not rectangular in the framing frame: its members do
     not all span the same distance, and a mark is one span.
   * Any region that runs past the outside face of its support: that is a
     cantilever, calc-spec §8.2.
   * Any opening whose tributary framing covers it only partly: that is a
     partial-span load, calc-spec §8.3.
   * Any opening carrying a load path this model has no expression for —
     roof+deck, floor+ceiling, or a WALL standing on the header (ASSEMBLY{}
     in weights.js has no wall dead load of any kind; register §L6).
   * Anything the drawing contradicts itself about: a wall declared
     bearing:false that framing declares it bears on, two overlapping
     regions on one side of a wall, a wall id that exists on two levels.

   ---- ES5 only. No let/const/arrow/template literal/class/Object.assign.
   ---- No DOM, no network, no libraries. Loads in the node harness.
   ============================================================ */

(function () {
  "use strict";

  var VERSION = 1;

  /* ---------------- epsilons ----------------

     EPS_FT is the width of "the same place" in this model. Coordinates are
     decimal feet typed or traced by a human, and the finest dimension anyone
     means in a framing drawing is 1/16 in = 0.0052 ft. Anything smaller than
     that is floating-point noise or drawing slop, not intent. It is
     deliberately NOT scaled to the size of the building: a tolerance that
     grew with the plan would let a 50 ft wall drift two inches and still
     read as coincident. */
  var EPS_FT = 0.005;

  /* Two directions are square or parallel within half a degree. This value
     only decides whether a wall is a CANDIDATE support; it never decides a
     number, because the consequence of being out of square is then measured
     rather than assumed — the span is computed at both ends of the run and
     refused if they disagree by more than SPAN_VARY_FT. */
  var ANG_EPS_DEG = 0.5;

  /* A span that varies by more than half an inch across the region is not
     one simple span. calc-spec §8.1 admits a single simple span per member,
     so a human splits the region; this module will not average two spans
     into a member that exists nowhere on the plan. */
  var SPAN_VARY_FT = 0.5 / 12;

  /* Float-noise cleanup only: 1e-6 ft is 1.2e-5 in. This changes no value a
     human could have meant, it only stops 31.999999999999996 from being
     printed on a schedule. */
  function clean(n) { return Math.round(n * 1e6) / 1e6; }

  var JACK_IN = 1.5;

  /* ---------------- role / carries maps ----------------

     `carries` is set from the framing KIND, never from the role string.
     weights.js is explicit about why: deriving loads from a role name put a
     treated deck beam on roof dead load at C_D 1.25 and l/180 and printed a
     4x8 at 59% for a member overstressed at 1.05. A role is a name; carries
     is the structure. Every mark this module emits declares it. */
  var ROLE_BY_KIND    = { floor: "joist", roof: "rafter", ceiling: "ceiling", deck: "deck" };
  var CARRIES_BY_KIND = { floor: "floor", roof: "roof",   ceiling: "ceiling", deck: "deck" };
  var TAG_BY_KIND     = { floor: "FJ",    roof: "RF",     ceiling: "CJ",      deck: "DK" };
  var SKU_BY_KIND     = { floor: "floor", roof: "rafter", ceiling: "ceiling", deck: "deck" };

  /* The two-load-path case weights.js can express. Anything else is refused
     rather than collapsed into one number. */
  var CARRIES_PAIR = { "floor|roof": "roof+floor" };

  var JACKS_BY_OPENING = [
    { underFt: 6,  jacks: 1 },
    { underFt: 12, jacks: 2 },
    { underFt: 18, jacks: 3 }
  ];

  var JACK_RULE_TEXT =
    "Jack studs per end from the clear opening: 1 under 6 ft, 2 from 6 ft to under 12 ft, " +
    "3 from 12 ft to under 18 ft; 18 ft and over is refused here. Bearing length = jacks x 1.5 in. " +
    "This is a TAKEOFF CONVENTION, not a table lookup — IRC R602.7 Table R602.7(1)/(2) sets the " +
    "jack count from the opening width AND the load carried, and this rule reads only the width. " +
    "Confirm it against the table for the tributary actually derived before the drawing is issued. " +
    "The value is marked `derived` so it can be challenged, and the engine checks bearing (Fc perp), " +
    "so an under-declared bearing escalates rather than passing quietly.";

  var POST_NOTE =
    "AXIAL MEMBER — NOT CHECKED HERE. calc-spec §4.10 specifies C_P (NDS §3.7.1) and §8.20 states " +
    "that no interaction equation is evaluated; engine.js implements neither. The design load is the " +
    "end reaction of the member above, which this tool does compute and publishes live. Uplift, the " +
    "continuous load path and both the base and cap connections are out of scope (§8.11, §8.17). " +
    "Slenderness is not a formality: for a typical 8 ft 4x4, C_P runs 0.25 to 0.35, so a check that " +
    "omits it overstates axial capacity roughly threefold.";

  /* The rules, in a form the plan set can print verbatim at gate 2. */
  var RULES = [
    { id: "span",
      text: "SPAN — the clear distance between the two walls the framing bears on, measured along " +
            "the framing direction, face to face: centre-to-centre less half of each wall thickness. " +
            "Measured at both ends of the run and refused if they differ by more than " +
            (SPAN_VARY_FT * 12).toFixed(2) + " in. A header's span is the clear opening between jacks. " +
            "calc-spec's symbol L also reads 'center-to-center of bearings', which is one bearing " +
            "length longer; that number is printed in every span derivation and is NOT what is emitted." },
    { id: "trib",
      text: "TRIBUTARY — half the clear span of each framing region bearing on the support, summed " +
            "over the framed sides. Emitted only when every contributing span is determined. An " +
            "exterior wall framed on one side is determined (the outboard side is outside the " +
            "building); an interior wall framed on one side is refused. Roof overhang and eave " +
            "tributary are not in the geometry model and are therefore not included." },
    { id: "bearing", text: "BEARING — " + JACK_RULE_TEXT },
    { id: "count",
      text: "COUNT — count = ceil(runFt x 12 / spacingIn) + 1, runFt measured perpendicular to the " +
            "framing direction. n bays plus one: a member at each end of the run. Same arithmetic as " +
            "solver.js pieceCount()." },
    { id: "carries",
      text: "CARRIES — set from the framing KIND (floor/roof/ceiling/deck), never from the role " +
            "string. Only one kind, or exactly roof+floor, can be expressed; any other combination " +
            "is refused." },
    { id: "refusal",
      text: "REFUSAL — nothing is rounded up to be safe and nothing is assumed. Anything the drawing " +
            "does not determine appears in unresolved[] with what a human must supply." }
  ];

  /* ---------------- tiny helpers ---------------- */

  function has(o, k) { return !!o && Object.prototype.hasOwnProperty.call(o, k); }
  function isNum(v) { return typeof v === "number" && isFinite(v); }
  function f2(n) { return (Math.round(n * 100) / 100).toFixed(2); }
  function f3(n) { return (Math.round(n * 1000) / 1000).toFixed(3); }
  function list(a) { return a.join(", "); }

  /* ---------------- run accumulator ---------------- */

  function makeRun() {
    return { marks: [], derivations: [], unresolved: [], warnings: [] };
  }

  function refuse(run, kind, what, why, need, refs) {
    run.unresolved.push({
      kind: kind, what: what, why: why, need: need, refs: refs || []
    });
  }

  function warn(run, kind, text, refs) {
    run.warnings.push({ kind: kind, text: text, refs: refs || [] });
  }

  /* A mark is built ONLY through a spec, and a spec cannot set a field
     without also recording where the value came from. That makes "every
     number has a derivation" a structural property of this file rather than
     a discipline somebody has to remember. */
  function spec() {
    var sp = { fields: [] };
    sp.set = function (name, value, from, fromIds, how, cls) {
      sp.fields.push({
        name: name, value: value,
        from: from, fromIds: fromIds || [],
        how: how, cls: cls || "derived"
      });
      return sp;
    };
    sp.get = function (name) {
      var i;
      for (i = 0; i < sp.fields.length; i++) if (sp.fields[i].name === name) return sp.fields[i].value;
      return undefined;
    };
    sp.replace = function (name, value, from, fromIds, how, cls) {
      var i;
      for (i = 0; i < sp.fields.length; i++) {
        if (sp.fields[i].name === name) {
          sp.fields.splice(i, 1);
          break;
        }
      }
      return sp.set(name, value, from, fromIds, how, cls);
    };
    return sp;
  }

  function emit(run, sp) {
    var mark = {}, seen = {}, id = null, i, fd;
    for (i = 0; i < sp.fields.length; i++) {
      fd = sp.fields[i];
      if (has(seen, fd.name)) {
        throw new Error("takeoff: field \"" + fd.name + "\" was set twice on one mark — every mark " +
                        "field must have exactly one derivation");
      }
      seen[fd.name] = 1;
      mark[fd.name] = fd.value;
      if (fd.name === "id") id = fd.value;
    }
    if (!id) throw new Error("takeoff: a mark was built with no id");
    for (i = 0; i < sp.fields.length; i++) {
      fd = sp.fields[i];
      run.derivations.push({
        markId: id, field: fd.name, value: fd.value,
        from: fd.from, fromIds: fd.fromIds, how: fd.how, cls: fd.cls
      });
    }
    run.marks.push(mark);
    return mark;
  }

  /* ---------------- geometry ---------------- */

  /* The framing frame: u runs ALONG the members (directionDeg 0 = +x), v
     runs across them, along the bearing lines. Every span is a u distance
     and every run is a v distance. */
  function frameOf(deg) {
    var r = deg * Math.PI / 180;
    return { deg: deg, c: Math.cos(r), s: Math.sin(r) };
  }
  function uOf(fr, x, y) { return x * fr.c + y * fr.s; }
  function vOf(fr, x, y) { return -x * fr.s + y * fr.c; }

  function wallGeom(w) {
    var dx = w.x2 - w.x1, dy = w.y2 - w.y1;
    var len = Math.sqrt(dx * dx + dy * dy);
    if (!(len > 0)) return null;
    return {
      dx: dx, dy: dy, len: len,
      ux: dx / len, uy: dy / len,
      nx: -dy / len, ny: dx / len,          /* left-hand normal */
      mx: (w.x1 + w.x2) / 2, my: (w.y1 + w.y2) / 2
    };
  }

  /* degrees this wall is off perpendicular to the framing direction.
     |wallDir . framingDir| = |sin(off-perpendicular angle)|. */
  function offPerpDeg(g, fr) {
    var d = Math.abs(g.ux * fr.c + g.uy * fr.s);
    if (d > 1) d = 1;
    return Math.asin(d) * 180 / Math.PI;
  }

  /* Drop repeated and collinear vertices so a rectangle drawn with five
     points is still a rectangle. */
  function tidyPolygon(poly) {
    var pts = [], i, p, last;
    for (i = 0; i < poly.length; i++) {
      p = poly[i];
      if (!p || !isNum(p[0]) || !isNum(p[1])) return null;
      last = pts[pts.length - 1];
      if (last && Math.abs(last[0] - p[0]) < EPS_FT && Math.abs(last[1] - p[1]) < EPS_FT) continue;
      pts.push([p[0], p[1]]);
    }
    if (pts.length > 1) {
      last = pts[pts.length - 1];
      if (Math.abs(last[0] - pts[0][0]) < EPS_FT && Math.abs(last[1] - pts[0][1]) < EPS_FT) pts.pop();
    }
    /* strip collinear runs */
    var out = [], n = pts.length, a, b, cpt, cross;
    if (n < 3) return pts;
    for (i = 0; i < n; i++) {
      a = pts[(i + n - 1) % n]; b = pts[i]; cpt = pts[(i + 1) % n];
      cross = (b[0] - a[0]) * (cpt[1] - b[1]) - (b[1] - a[1]) * (cpt[0] - b[0]);
      if (Math.abs(cross) > EPS_FT * EPS_FT) out.push(b);
    }
    return out.length >= 3 ? out : pts;
  }

  /* ---------------- levels and the wall index ---------------- */

  function indexWalls(model, run) {
    var byId = {}, dupes = {};
    (model.levels || []).forEach(function (lv, li) {
      (lv.walls || []).forEach(function (w) {
        if (!w || !w.id) return;
        if (has(byId, w.id)) { dupes[w.id] = 1; return; }
        byId[w.id] = { wall: w, level: lv, levelIndex: li, geom: wallGeom(w) };
      });
    });
    Object.keys(dupes).forEach(function (id) {
      refuse(run, "wall-id",
        "wall id \"" + id + "\" is used on more than one level",
        "bearsOn references and opening.wallId are wall ids only; with the same id on two levels " +
        "there is no way to know which wall a framing region or an opening means, and picking one " +
        "would silently assign a load path.",
        "make wall ids unique across the whole model (prefix them with the level id), then re-run " +
        "the takeoff.",
        [id]);
      byId[id] = null;
    });
    return byId;
  }

  /* ---------------- pass A: framing regions ---------------- */

  function regionRecord(run, model, index, lv, li, reg, prefix) {
    var rec = {
      id: reg.id, kind: reg.kind, level: lv.id, levelIndex: li,
      determined: false, poisons: [], why: null,
      supportIds: [], extentByWall: {}, centroid: null,
      spanFt: NaN, halfSpanFt: NaN, role: null, carries: null, markId: null
    };
    var refs = [reg.id];

    if (!reg.id) {
      refuse(run, "framing", "a framing region on level " + lv.id + " has no id",
             "a mark has to name the drawn object it came from; an unnamed region cannot be traced " +
             "back at a review.",
             "give every framing region an id in the CAD model.", [lv.id]);
      return null;
    }

    /* --- role and carries, from the KIND --- */
    if (!has(ROLE_BY_KIND, reg.kind)) {
      refuse(run, "framing-kind",
        "framing region " + reg.id + " declares kind \"" + String(reg.kind) + "\", which this " +
        "takeoff cannot classify",
        "role and carries are both read from the framing kind, and only floor, roof, ceiling and " +
        "deck are defined. Defaulting an unknown kind would pick both a member ladder and a load " +
        "set for it.",
        "set kind to one of floor / roof / ceiling / deck, or add the kind to the takeoff's " +
        "ROLE_BY_KIND and CARRIES_BY_KIND maps together with the load path weights.js should use.",
        refs);
      rec.poisons = (reg.bearsOn || []).slice();
      rec.why = "kind not classifiable";
      return rec;
    }
    rec.role = ROLE_BY_KIND[reg.kind];
    rec.carries = CARRIES_BY_KIND[reg.kind];

    /* --- polygon --- */
    var poly = Array.isArray(reg.polygon) ? tidyPolygon(reg.polygon) : null;
    if (!poly || poly.length < 3) {
      refuse(run, "framing-polygon",
        "framing region " + reg.id + " has no usable polygon",
        "the span, the run and the count are all measured off the polygon; there is nothing to " +
        "measure.",
        "draw the region as a closed polygon of at least three distinct points in feet.",
        refs);
      rec.poisons = (reg.bearsOn || []).slice();
      rec.why = "no usable polygon";
      return rec;
    }

    var fr = frameOf(isNum(reg.directionDeg) ? reg.directionDeg : NaN);
    if (!isNum(reg.directionDeg)) {
      refuse(run, "framing-direction",
        "framing region " + reg.id + " declares no directionDeg",
        "which way the members run decides which walls are supports and which are not. There is no " +
        "defensible default: 0 and 90 give different spans, different tributaries and different " +
        "members.",
        "declare directionDeg on the region (0 = members run along +x).",
        refs);
      rec.poisons = (reg.bearsOn || []).slice();
      rec.why = "no framing direction";
      return rec;
    }

    /* centroid — the polygon is required to be a rectangle below, so the
       vertex mean is the true centroid */
    var cx = 0, cy = 0;
    poly.forEach(function (p) { cx += p[0]; cy += p[1]; });
    cx /= poly.length; cy /= poly.length;
    rec.centroid = [cx, cy];

    /* extents in the framing frame */
    var uv = poly.map(function (p) { return { u: uOf(fr, p[0], p[1]), v: vOf(fr, p[0], p[1]) }; });
    var umin = uv[0].u, umax = uv[0].u, vmin = uv[0].v, vmax = uv[0].v;
    uv.forEach(function (q) {
      if (q.u < umin) umin = q.u; if (q.u > umax) umax = q.u;
      if (q.v < vmin) vmin = q.v; if (q.v > vmax) vmax = q.v;
    });
    rec.uv = { umin: umin, umax: umax, vmin: vmin, vmax: vmax, fr: fr };

    /* walls it bears on — resolved before anything else, so an unresolvable
       region still poisons the walls it touches */
    var bearsOn = Array.isArray(reg.bearsOn) ? reg.bearsOn : [];
    rec.poisons = bearsOn.slice();

    /* extent along each named wall, for the "is this framing over that
       opening" test later */
    bearsOn.forEach(function (wid) {
      var e = index[wid];
      if (!e || !e.geom) return;
      var g = e.geom, lo = Infinity, hi = -Infinity;
      poly.forEach(function (p) {
        var r = (p[0] - e.wall.x1) * g.ux + (p[1] - e.wall.y1) * g.uy;
        if (r < lo) lo = r; if (r > hi) hi = r;
      });
      if (lo < 0) lo = 0;
      if (hi > g.len) hi = g.len;
      rec.extentByWall[wid] = [lo, hi];
    });

    /* --- rectangular in the framing frame? --- */
    var rectOk = poly.length === 4;
    if (rectOk) {
      var i;
      for (i = 0; i < 4 && rectOk; i++) {
        var a = uv[i], b = uv[(i + 1) % 4];
        if (Math.abs(a.u - b.u) > EPS_FT && Math.abs(a.v - b.v) > EPS_FT) rectOk = false;
      }
    }
    if (!rectOk) {
      refuse(run, "framing-shape",
        "framing region " + reg.id + " is not a rectangle in its own framing frame",
        "members at different positions across the region then span different distances, and a mark " +
        "is one span. Averaging them would print a member that exists nowhere on the plan; taking " +
        "the longest would size the whole region for its worst bay without saying so.",
        "split the region into one rectangular bay per span and re-run. Each bay becomes its own " +
        "mark with its own span, run and count.",
        refs);
      rec.why = "region not rectangular in the framing frame";
      return rec;
    }

    /* --- the bearing lines --- */
    var perp = [], parallel = [], missing = [];
    bearsOn.forEach(function (wid) {
      var e = index[wid];
      if (!e) { missing.push(wid); return; }
      if (!e.geom) { missing.push(wid); return; }
      var off = offPerpDeg(e.geom, fr);
      if (off <= ANG_EPS_DEG) perp.push(e);
      else if (off >= 90 - ANG_EPS_DEG) parallel.push(e);
      else {
        refuse(run, "framing-support-angle",
          "wall " + wid + " is " + f2(off) + " deg off perpendicular to framing region " + reg.id,
          "a support that is neither square to the members nor parallel to them gives a span that " +
          "changes continuously along the run, so there is no single span for the mark.",
          "square the wall to the framing, or split the region so each mark has a constant span, or " +
          "declare the region's members individually.",
          [reg.id, wid]);
        rec.why = "a support is out of square";
      }
    });
    if (missing.length) {
      refuse(run, "framing-support-missing",
        "framing region " + reg.id + " bears on wall id(s) " + list(missing) + ", which are not in " +
        "the model (or are ambiguous / zero length)",
        "a support that does not exist cannot give a span.",
        "correct bearsOn to name real walls, or draw the missing wall.",
        [reg.id].concat(missing));
      rec.why = "named support missing";
      return rec;
    }
    if (rec.why) return rec;

    parallel.forEach(function (e) {
      warn(run, "support-parallel",
        "wall " + e.wall.id + " is listed in " + reg.id + ".bearsOn but runs PARALLEL to the members. " +
        "A wall parallel to the framing carries at most one member line, not a half span, so it " +
        "contributes nothing to this region's span and no tributary is derived from it. If a " +
        "member does bear on it, draw that member as its own region.",
        [reg.id, e.wall.id]);
    });

    /* group perpendicular supports into bearing LINES — one line may be
       drawn as two wall segments either side of a corner or a break */
    var lines = [];
    perp.forEach(function (e) {
      var u = uOf(fr, e.geom.mx, e.geom.my), i, hit = null;
      for (i = 0; i < lines.length; i++) {
        if (Math.abs(lines[i].u - u) <= EPS_FT) { hit = lines[i]; break; }
      }
      if (hit) hit.walls.push(e);
      else lines.push({ u: u, walls: [e] });
    });

    if (lines.length !== 2) {
      if (lines.length < 2) {
        refuse(run, "framing-underdetermined",
          "framing region " + reg.id + " (" + reg.kind + ", level " + lv.id + ") bears on " +
          lines.length + " bearing line" + (lines.length === 1 ? "" : "s") +
          (lines.length === 1 ? " (" + list(lines[0].walls.map(function (e) { return e.wall.id; })) + ")" : ""),
          "a simple span needs two supports. With one support determined and the other end " +
          "undetermined, the span is unknown — and so is the tributary of every member and every " +
          "header that this region lands on. Half of an unknown span is not a conservative estimate, " +
          "it is an invented number.",
          "declare the second support: add the wall, beam or bearing line at the other end of the " +
          "region to bearsOn (the model has no beam or post entity, so a member landing on a beam " +
          "or a post line cannot be expressed at all yet — see the takeoff report), or trim the " +
          "region to the bay that does bear on two walls.",
          [reg.id].concat(lines.length === 1 ? lines[0].walls.map(function (e) { return e.wall.id; }) : []));
      } else {
        refuse(run, "framing-multispan",
          "framing region " + reg.id + " crosses " + lines.length + " bearing lines",
          "that is a continuous or multi-span condition. calc-spec §8.1 admits simply-supported " +
          "single spans only — no two-span, no continuous-over-support, no moment redistribution. " +
          "Which bay a given member is in is also not determined by one polygon.",
          "split the region into one bay per span, each bearing on exactly two lines, and re-run.",
          [reg.id].concat(perp.map(function (e) { return e.wall.id; })));
      }
      rec.why = "wrong number of bearing lines (" + lines.length + ")";
      return rec;
    }

    /* thickness — refused, never assumed */
    var badT = [];
    perp.forEach(function (e) {
      if (!isNum(e.wall.thicknessIn) || !(e.wall.thicknessIn > 0)) badT.push(e.wall.id);
    });
    if (badT.length) {
      refuse(run, "wall-thickness",
        "wall(s) " + list(badT) + " carry framing region " + reg.id + " and declare no thickness",
        "the span is the CLEAR distance between wall faces, so half of each wall's thickness comes " +
        "out of the centreline distance. With no thickness there is no face, and assuming 2x6 " +
        "framing would invent up to 0.46 ft of span.",
        "declare thicknessIn on every bearing wall.",
        [reg.id].concat(badT));
      rec.why = "support thickness not declared";
      return rec;
    }

    /* two segments of one bearing line must agree on thickness, or the face
       is in two places */
    var mixed = null;
    lines.forEach(function (ln) {
      var t0 = ln.walls[0].wall.thicknessIn;
      ln.walls.forEach(function (e) { if (Math.abs(e.wall.thicknessIn - t0) > 1e-9) mixed = ln; });
    });
    if (mixed) {
      refuse(run, "wall-thickness-mixed",
        "the bearing line carrying " + reg.id + " is drawn as walls " +
        list(mixed.walls.map(function (e) { return e.wall.id; })) + " with different thicknesses",
        "the clear span is measured to a wall face, and two thicknesses on one line put the face in " +
        "two places — the members over one segment span further than the members over the other.",
        "make the segments of one bearing line the same thickness, or split the region so each mark " +
        "sits over a single thickness.",
        [reg.id].concat(mixed.walls.map(function (e) { return e.wall.id; })));
      rec.why = "one bearing line, two thicknesses";
      return rec;
    }

    /* which line is at low u, which at high u */
    var A = lines[0].u <= lines[1].u ? lines[0] : lines[1];
    var B = lines[0].u <= lines[1].u ? lines[1] : lines[0];
    var tA = A.walls[0].wall.thicknessIn / 12, tB = B.walls[0].wall.thicknessIn / 12;

    /* the supports must actually straddle the region */
    if (!(A.u < (umin + umax) / 2 && B.u > (umin + umax) / 2)) {
      refuse(run, "framing-supports-same-side",
        "both bearing lines of framing region " + reg.id + " sit on the same side of it",
        "the members cannot span between two supports that are not on opposite ends of the span " +
        "direction. Either the framing direction or the bearsOn list is wrong.",
        "check directionDeg against the walls named in bearsOn.",
        [reg.id].concat(perp.map(function (e) { return e.wall.id; })));
      rec.why = "supports on the same side";
      return rec;
    }

    /* each line must cover the whole run, or some members have no support */
    var shortLines = [];
    [A, B].forEach(function (ln) {
      var cov = [];
      ln.walls.forEach(function (e) {
        var v1 = vOf(fr, e.wall.x1, e.wall.y1), v2 = vOf(fr, e.wall.x2, e.wall.y2);
        cov.push([Math.min(v1, v2), Math.max(v1, v2)]);
      });
      /* merge and test coverage of [vmin, vmax] */
      cov.sort(function (a, b) { return a[0] - b[0]; });
      var reach = -Infinity, ok = false, i;
      for (i = 0; i < cov.length; i++) {
        if (i === 0) { if (cov[i][0] > vmin + EPS_FT) break; reach = cov[i][1]; }
        else {
          if (cov[i][0] > reach + EPS_FT) break;
          if (cov[i][1] > reach) reach = cov[i][1];
        }
        if (reach >= vmax - EPS_FT) { ok = true; break; }
      }
      if (!ok) {
        shortLines.push({ line: ln, reach: reach });
      }
    });
    if (shortLines.length) {
      refuse(run, "framing-support-short",
        "the bearing line(s) " +
        list(shortLines.map(function (s) {
          return list(s.line.walls.map(function (e) { return e.wall.id; }));
        })) + " do not run the full " + f2(vmax - vmin) + " ft length of framing region " + reg.id,
        "members over the uncovered part of the run have no support at that end. Sizing the whole " +
        "region as if the wall ran the full length would print a member for a condition the drawing " +
        "does not show.",
        "extend the wall, or split the region so each mark sits entirely over its supports, or draw " +
        "the beam that carries the rest (the model has no beam entity today — see the report).",
        [reg.id]);
      rec.why = "a bearing line is shorter than the run";
      return rec;
    }

    /* span, measured at BOTH ends of the run */
    function uAt(ln, v) {
      /* the segment of this line whose v range contains v (or the nearest) */
      var best = null, bestD = Infinity, i;
      for (i = 0; i < ln.walls.length; i++) {
        var e = ln.walls[i];
        var u1 = uOf(fr, e.wall.x1, e.wall.y1), v1 = vOf(fr, e.wall.x1, e.wall.y1);
        var u2 = uOf(fr, e.wall.x2, e.wall.y2), v2 = vOf(fr, e.wall.x2, e.wall.y2);
        var lo = Math.min(v1, v2), hi = Math.max(v1, v2);
        var d = v < lo ? lo - v : (v > hi ? v - hi : 0);
        if (d < bestD) {
          bestD = d;
          best = Math.abs(v2 - v1) < EPS_FT ? u1 : u1 + (u2 - u1) * (v - v1) / (v2 - v1);
        }
      }
      return best;
    }
    var span1 = (uAt(B, vmin) - tB / 2) - (uAt(A, vmin) + tA / 2);
    var span2 = (uAt(B, vmax) - tB / 2) - (uAt(A, vmax) + tA / 2);
    if (Math.abs(span1 - span2) > SPAN_VARY_FT) {
      refuse(run, "framing-span-varies",
        "the clear span of framing region " + reg.id + " varies from " + f3(span1) + " ft to " +
        f3(span2) + " ft across its run",
        "that is more than " + (SPAN_VARY_FT * 12).toFixed(2) + " in of variation, so this is not " +
        "one simple span. A single number here would be an average nobody builds, and the longest " +
        "member would be sized as if it were the shortest somewhere on the plan.",
        "square the bearing lines to each other, or split the region into bays of constant span.",
        [reg.id].concat(perp.map(function (e) { return e.wall.id; })));
      rec.why = "span varies across the run";
      return rec;
    }
    var spanFt = Math.max(span1, span2);
    if (!(spanFt > 0)) {
      refuse(run, "framing-span-nonpositive",
        "framing region " + reg.id + " computes a clear span of " + f3(spanFt) + " ft",
        "the two bearing lines are coincident, overlapping, or thicker than the distance between " +
        "them. There is no member here.",
        "check the wall positions, thicknesses and the region's polygon.",
        [reg.id].concat(perp.map(function (e) { return e.wall.id; })));
      rec.why = "non-positive span";
      return rec;
    }

    /* cantilever check — the region may not run past the OUTSIDE face of
       either support */
    var overA = (Math.min(uAt(A, vmin), uAt(A, vmax)) - tA / 2) - umin;
    var overB = umax - (Math.max(uAt(B, vmin), uAt(B, vmax)) + tB / 2);
    if (overA > EPS_FT || overB > EPS_FT) {
      refuse(run, "framing-cantilever",
        "framing region " + reg.id + " runs past the outside face of its support by " +
        f3(Math.max(overA, overB)) + " ft",
        "framing past its support is a cantilever, and calc-spec §8.2 excludes cantilevers outright " +
        "— including back-span/overhang combinations. Sizing the back span alone would understate " +
        "the member and say nothing about the overhang.",
        "trim the region to its supports and size the overhang outside this engine, or move the " +
        "support to the end of the framing.",
        [reg.id].concat(perp.map(function (e) { return e.wall.id; })));
      rec.why = "region cantilevers past its support";
      return rec;
    }

    /* spacing and the run */
    if (!isNum(reg.spacingIn) || !(reg.spacingIn > 0)) {
      refuse(run, "framing-spacing",
        "framing region " + reg.id + " declares no spacingIn",
        "the piece count and the member's own tributary both come from the spacing. There is no " +
        "default: 16 and 24 in o.c. are different members and different quantities.",
        "declare spacingIn on the region.",
        [reg.id]);
      rec.why = "no spacing declared";
      return rec;
    }
    var runFt = vmax - vmin;
    var count = Math.ceil(runFt * 12 / reg.spacingIn) + 1;

    /* --- the mark --- */
    var markId = prefix + TAG_BY_KIND[reg.kind] + "-" + reg.id;
    var wallsA = A.walls.map(function (e) { return e.wall.id; });
    var wallsB = B.walls.map(function (e) { return e.wall.id; });
    var supportIds = wallsA.concat(wallsB);
    var fromWalls = "walls " + list(supportIds) + " (level " + lv.id + ")";
    var fromRegion = "framing region " + reg.id;

    var sp = spec();
    sp.set("id", markId, fromRegion, [reg.id],
      "mark id = level prefix + role tag for kind \"" + reg.kind + "\" + the drawn region's id, so " +
      "every row on the schedule points back to exactly one object on the plan.");
    sp.set("label",
      (reg.kind === "floor" ? "Floor joist" : reg.kind === "roof" ? "Roof rafter" :
       reg.kind === "ceiling" ? "Ceiling joist" : "Deck joist") +
      " · " + reg.id + " · " + lv.label + (reg.note ? " · " + reg.note : ""),
      fromRegion, [reg.id],
      "label composed from the region's kind, its id and the level label; the region's own note is " +
      "appended verbatim if it has one.");
    sp.set("role", rec.role, fromRegion, [reg.id],
      "framing kind \"" + reg.kind + "\" maps to role \"" + rec.role + "\" (floor->joist, " +
      "roof->rafter, ceiling->ceiling, deck->deck), the same mapping weights.js uses.");
    sp.set("carries", rec.carries, fromRegion, [reg.id],
      "carries is read from the framing KIND (\"" + reg.kind + "\" -> \"" + rec.carries + "\"), " +
      "never from the role string. weights.js CARRIES_DEFAULT exists for the obvious cases; it is " +
      "declared here anyway so the load path is on the mark and not inferred downstream.");
    sp.set("span", clean(spanFt), fromWalls, supportIds,
      "clear distance between the bearing lines along the framing direction (" + f2(reg.directionDeg) +
      " deg): centreline to centreline " + f3(spanFt + tA / 2 + tB / 2) + " ft, less half of " +
      list(wallsA) + " (" + f2(A.walls[0].wall.thicknessIn) + " in / 2 = " + f3(tA / 2) + " ft) and " +
      "half of " + list(wallsB) + " (" + f2(B.walls[0].wall.thicknessIn) + " in / 2 = " + f3(tB / 2) +
      " ft) = " + f3(spanFt) + " ft. Measured at both ends of the run (" + f3(span1) + " ft and " +
      f3(span2) + " ft) and the longer taken, because that member is on the plan. NOTE: " +
      "centre-to-centre of bearings — calc-spec's other reading of L — would be " +
      f3(spanFt + 3 / 12) + " ft at a 3 in bearing; this module emits the CLEAR distance the " +
      "FM.takeoff contract specifies and does not pad.");
    sp.set("runFt", clean(runFt), fromRegion, [reg.id],
      "the region's extent measured perpendicular to the framing direction (along the bearing " +
      "lines): " + f3(vmax) + " ft - " + f3(vmin) + " ft = " + f3(runFt) + " ft.");
    sp.set("spacingIn", reg.spacingIn, fromRegion, [reg.id],
      "read straight off the drawn region.", "user");
    sp.set("count", count, fromRegion + " and its spacing", [reg.id],
      "count = ceil(runFt x 12 / spacing) + 1 = ceil(" + f3(runFt) + " x 12 / " + reg.spacingIn +
      ") + 1 = ceil(" + f3(runFt * 12 / reg.spacingIn) + ") + 1 = " + count + ". The +1 is the " +
      "member at the far end of the run. solver.js pieceCount() recomputes this from runFt and the " +
      "spacing it actually picks, so if the solver's ladder has no " + reg.spacingIn + " in rung " +
      "the schedule quantity will differ from this one — see the spacing-ladder warning.");
    sp.set("skuGroup", SKU_BY_KIND[reg.kind], fromRegion, [reg.id],
      "SKU group from the framing kind, so unification only ever collapses members of the same " +
      "assembly.");
    sp.set("braced", true, fromRegion, [reg.id],
      "the compression edge is taken as continuously braced by the sheathing or decking fastened " +
      "to it. This is a CONSTRUCTION assumption, not a geometric one — the model does not draw " +
      "sheathing. If this region is exposed framing with no diaphragm, this is wrong and C_L must " +
      "be evaluated: declare braced:false on the mark.");
    if (reg.kind === "deck") {
      sp.set("exposure", "exterior", fromRegion, [reg.id],
        "framing kind \"deck\" is an exterior framed surface by definition, so exposure is exterior. " +
        "In weights.demandFor this drives wet service and treatment. If a \"deck\" region is in fact " +
        "under cover and dry, the kind is wrong, not this field.");
    }
    sp.set("note",
      "Takeoff-derived. Span = clear " + f3(spanFt) + " ft between " + list(wallsA) + " and " +
      list(wallsB) + "; run " + f3(runFt) + " ft at " + reg.spacingIn + " in o.c. -> " + count +
      " pieces. Region " + reg.id + " on level " + lv.id + ".",
      fromRegion, [reg.id],
      "one-line restatement of this mark's own derivations, so the schedule row carries its basis.");

    var mk = emit(run, sp);
    rec.markId = mk.id;
    rec.determined = true;
    rec.spanFt = clean(spanFt);
    rec.halfSpanFt = clean(spanFt / 2);
    rec.supportIds = supportIds;
    rec.lineA = { u: A.u, walls: wallsA };
    rec.lineB = { u: B.u, walls: wallsB };
    return rec;
  }

  /* ---------------- pass B: what lands on each wall ---------------- */

  function supportTable(index, regions) {
    var table = {};
    function entry(wid) {
      if (!has(table, wid)) table[wid] = { contributions: [], poisoned: [] };
      return table[wid];
    }
    regions.forEach(function (rec) {
      if (!rec) return;
      if (!rec.determined) {
        rec.poisons.forEach(function (wid) {
          entry(wid).poisoned.push({ regionId: rec.id, why: rec.why || "undetermined",
                                     extent: rec.extentByWall[wid] || null });
        });
        return;
      }
      rec.supportIds.forEach(function (wid) {
        var e = index[wid];
        if (!e || !e.geom) return;
        var g = e.geom;
        var sn = (rec.centroid[0] - e.wall.x1) * g.nx + (rec.centroid[1] - e.wall.y1) * g.ny;
        entry(wid).contributions.push({
          regionId: rec.id, kind: rec.kind, carries: rec.carries,
          spanFt: rec.spanFt, halfSpanFt: rec.halfSpanFt,
          side: sn >= 0 ? "+" : "-",
          extent: rec.extentByWall[wid] || [0, g.len],
          markId: rec.markId
        });
      });
    });
    return table;
  }

  /* ---------------- pass C: openings -> headers ---------------- */

  function jacksFor(widthFt) {
    var i;
    for (i = 0; i < JACKS_BY_OPENING.length; i++) {
      if (widthFt < JACKS_BY_OPENING[i].underFt) {
        return { jacks: JACKS_BY_OPENING[i].jacks,
                 bearingIn: JACKS_BY_OPENING[i].jacks * JACK_IN,
                 band: "under " + JACKS_BY_OPENING[i].underFt + " ft" };
      }
    }
    return null;
  }

  function overlap(a, b) {
    var lo = Math.max(a[0], b[0]), hi = Math.min(a[1], b[1]);
    return hi > lo ? hi - lo : 0;
  }

  /* is there a wall on the level above standing over this opening? */
  function wallAbove(model, entry, opening, o1, o2) {
    var above = (model.levels || [])[entry.levelIndex + 1];
    if (!above) return null;
    var g = entry.geom, hit = null;
    (above.walls || []).forEach(function (w2) {
      if (hit) return;
      var g2 = wallGeom(w2);
      if (!g2) return;
      var dot = Math.abs(g2.ux * g.ux + g2.uy * g.uy);
      if (dot < Math.cos(ANG_EPS_DEG * Math.PI / 180)) return;      /* not parallel */
      var off = Math.abs((g2.mx - entry.wall.x1) * g.nx + (g2.my - entry.wall.y1) * g.ny);
      var t1 = isNum(entry.wall.thicknessIn) ? entry.wall.thicknessIn / 12 : 0;
      var t2 = isNum(w2.thicknessIn) ? w2.thicknessIn / 12 : 0;
      if (off > (t1 + t2) / 2 + EPS_FT) return;                     /* not stacked on it */
      var r1 = (w2.x1 - entry.wall.x1) * g.ux + (w2.y1 - entry.wall.y1) * g.uy;
      var r2 = (w2.x2 - entry.wall.x1) * g.ux + (w2.y2 - entry.wall.y1) * g.uy;
      if (overlap([Math.min(r1, r2), Math.max(r1, r2)], [o1, o2]) > EPS_FT) hit = w2;
    });
    return hit;
  }

  /* another bearing wall teeing into this one inside the opening = a point
     load on the header */
  function teeInOpening(model, index, entry, o1, o2) {
    var g = entry.geom, hits = [];
    (model.levels || []).forEach(function (lv, li) {
      if (li !== entry.levelIndex) return;
      (lv.walls || []).forEach(function (w2) {
        if (w2.id === entry.wall.id) return;
        if (w2.bearing !== true) return;
        var g2 = wallGeom(w2);
        if (!g2) return;
        var dot = Math.abs(g2.ux * g.ux + g2.uy * g.uy);
        if (dot > Math.cos((90 - ANG_EPS_DEG) * Math.PI / 180)) return;   /* parallel — not a tee */
        [[w2.x1, w2.y1], [w2.x2, w2.y2]].forEach(function (p) {
          var off = Math.abs((p[0] - entry.wall.x1) * g.nx + (p[1] - entry.wall.y1) * g.ny);
          var t1 = isNum(entry.wall.thicknessIn) ? entry.wall.thicknessIn / 12 : 0;
          var t2 = isNum(w2.thicknessIn) ? w2.thicknessIn / 12 : 0;
          if (off > (t1 + t2) / 2 + EPS_FT) return;
          var r = (p[0] - entry.wall.x1) * g.ux + (p[1] - entry.wall.y1) * g.uy;
          if (r > o1 - EPS_FT && r < o2 + EPS_FT && hits.indexOf(w2.id) === -1) hits.push(w2.id);
        });
      });
    });
    return hits;
  }

  function headerSpec(run, model, index, table, lv, li, op, prefix, multiLevel) {
    var refs = [op.id];
    if (!op.id) {
      refuse(run, "opening", "an opening on level " + lv.id + " has no id",
             "a header mark has to name the opening it came from.",
             "give every opening an id in the CAD model.", [lv.id]);
      return null;
    }
    var entry = index[op.wallId];
    if (!entry || !entry.geom) {
      refuse(run, "opening-wall",
        "opening " + op.id + " names wall \"" + String(op.wallId) + "\", which is not in the model " +
        "(or is ambiguous / zero length)",
        "an opening with no wall has no header: there is nothing to carry and nothing to bear on.",
        "correct opening.wallId, or draw the wall.",
        [op.id, String(op.wallId)]);
      return null;
    }
    var w = entry.wall, g = entry.geom;

    if (!isNum(op.widthFt) || !(op.widthFt > 0) || !isNum(op.offsetFt)) {
      refuse(run, "opening-geometry",
        "opening " + op.id + " in wall " + w.id + " has no usable offsetFt/widthFt",
        "the header's span IS the clear opening; there is no other source for it.",
        "declare offsetFt and widthFt on the opening, in feet along the wall from (x1,y1).",
        refs);
      return null;
    }
    var o1 = op.offsetFt, o2 = op.offsetFt + op.widthFt;
    if (o1 < -EPS_FT || o2 > g.len + EPS_FT) {
      refuse(run, "opening-overruns-wall",
        "opening " + op.id + " runs from " + f2(o1) + " ft to " + f2(o2) + " ft along wall " + w.id +
        ", which is " + f2(g.len) + " ft long",
        "the opening is not inside its wall, so neither its span nor its bearing is real.",
        "correct the opening's offset or width, or the wall's endpoints.",
        refs.concat([w.id]));
      return null;
    }

    var above = wallAbove(model, entry, op, o1, o2);

    /* --- non-bearing wall: no header MARK, and say exactly why --- */
    if (w.bearing !== true) {
      warn(run, "no-header",
        "No header mark for opening " + op.id + ": wall " + w.id + " is declared bearing:" +
        String(w.bearing) + ", so no framing tributary lands on it and this engine has nothing to " +
        "size. A physical header or lintel is still required over the opening to carry the wall and " +
        "any rim above it — that member is NOT in this schedule and is NOT sized here.",
        [op.id, w.id]);
      if (above) {
        refuse(run, "header-carries-wall",
          "opening " + op.id + " in non-bearing wall " + w.id + " still carries wall " + above.id +
          " on the level above",
          "what that header carries is a WALL, and this model has no wall dead load: ASSEMBLY{} in " +
          "weights.js has no wall entry of any kind (register §L6). There is no roof strip and no " +
          "floor strip to substitute either — borrowing one from a bearing wall would assert a load " +
          "path this framing does not have.",
          "declare a wall dead load (psf of wall elevation) and the rim condition, then this header " +
          "can be derived; until then it must be sized outside this engine and shown on the plan " +
          "set as an open item.",
          [op.id, w.id, above.id]);
      }
      return null;
    }

    var sup = table[op.wallId] || { contributions: [], poisoned: [] };

    /* --- anything undetermined that lands over this opening poisons it --- */
    var poison = sup.poisoned.filter(function (p) {
      return !p.extent || overlap(p.extent, [o1, o2]) > EPS_FT;
    });
    if (poison.length) {
      refuse(run, "header-tributary-undetermined",
        "header at opening " + op.id + " (wall " + w.id + ") cannot be given a tributary",
        "the framing that lands on this wall over the opening is itself undetermined: " +
        list(poison.map(function (p) { return p.regionId + " (" + p.why + ")"; })) + ". Half of an " +
        "undetermined span is not a tributary, and leaving the region out entirely would silently " +
        "size this header for less load than it carries.",
        "resolve the framing region(s) named above first — the unresolved entry for each says what " +
        "it needs — then re-run the takeoff.",
        [op.id, w.id].concat(poison.map(function (p) { return p.regionId; })));
      return null;
    }

    /* --- contributions over the opening --- */
    var over = [], partial = [];
    sup.contributions.forEach(function (c) {
      var ov = overlap(c.extent, [o1, o2]);
      if (ov <= EPS_FT) return;
      if (ov < op.widthFt - EPS_FT) partial.push({ c: c, ov: ov });
      else over.push(c);
    });
    if (partial.length) {
      refuse(run, "header-partial-load",
        "framing region(s) " + list(partial.map(function (p) { return p.c.regionId; })) +
        " cover only part of opening " + op.id + " (" +
        list(partial.map(function (p) { return f2(p.ov) + " ft of " + f2(op.widthFt) + " ft"; })) + ")",
        "that is a partial-span load on the header, and calc-spec §8.3 admits a uniform full-span " +
        "load only — no partial-span, no concentrated, no pattern loading. Spreading the load over " +
        "the whole header would understate the moment where it lands; applying it full length would " +
        "overstate the total.",
        "extend or split the framing region so it either covers the opening completely or not at " +
        "all, or size this header outside this engine as a partially loaded beam.",
        [op.id, w.id].concat(partial.map(function (p) { return p.c.regionId; })));
      return null;
    }

    if (!over.length) {
      refuse(run, "header-no-framing",
        "wall " + w.id + " is declared bearing:true but no framing region bears on it over opening " +
        op.id,
        "a bearing wall with nothing bearing on it is a contradiction in the drawing. The tributary " +
        "would be zero, which would print a header sized for no load at all.",
        "either add the framing region that bears on this wall to its bearsOn list, or set " +
        "bearing:false on the wall — and if the header carries only wall and rim, say so, because " +
        "this model has no wall dead load and cannot size it.",
        [op.id, w.id]);
      return null;
    }

    /* two regions overlapping on the same side would be counted twice */
    var dupSide = null;
    over.forEach(function (a) {
      over.forEach(function (b) {
        if (a === b || dupSide) return;
        if (a.side === b.side && overlap(a.extent, b.extent) > EPS_FT) dupSide = [a, b];
      });
    });
    if (dupSide) {
      refuse(run, "framing-overlap",
        "framing regions " + dupSide[0].regionId + " and " + dupSide[1].regionId + " both bear on " +
        "wall " + w.id + " on the same side and overlap over opening " + op.id,
        "their half-spans would both be added, counting the same floor or roof area twice.",
        "trim the regions so they do not overlap, or merge them into one region.",
        [op.id, w.id, dupSide[0].regionId, dupSide[1].regionId]);
      return null;
    }

    /* --- both sides determined? --- */
    var sides = {};
    over.forEach(function (c) { sides[c.side] = 1; });
    var nSides = Object.keys(sides).length;
    if (nSides < 2 && w.exterior !== true) {
      refuse(run, "header-one-sided-interior",
        "interior bearing wall " + w.id + " carries framing on one side only over opening " + op.id,
        "the other side of an INTERIOR wall is inside the building envelope, so something frames " +
        "there. Either it is missing from the model or it bears somewhere the model does not say. " +
        "Taking half a span from one side and nothing from the other would size this header for " +
        "roughly half the load it carries.",
        "draw the framing region on the other side of the wall and add this wall to its bearsOn, " +
        "or declare the wall exterior if it genuinely is the edge of the framed area.",
        [op.id, w.id].concat(over.map(function (c) { return c.regionId; })));
      return null;
    }

    /* --- carries, from the KINDS that land here --- */
    var kinds = {}, tribByKind = {};
    over.forEach(function (c) {
      kinds[c.kind] = 1;
      tribByKind[c.kind] = (tribByKind[c.kind] || 0) + c.halfSpanFt;
    });
    var kindList = Object.keys(kinds).sort();
    var carries = null, pairKey = kindList.join("|");
    if (kindList.length === 1) carries = CARRIES_BY_KIND[kindList[0]];
    else if (has(CARRIES_PAIR, pairKey)) carries = CARRIES_PAIR[pairKey];
    if (!carries) {
      refuse(run, "header-carries-unexpressible",
        "the header at opening " + op.id + " carries " + list(kindList) + " together",
        "weights.js expresses one load path per mark, plus the single combination roof+floor. " +
        "\"" + pairKey + "\" is not one of them, and blending two load sets into one psf would " +
        "invent an assembly with no code basis — that is exactly the defect DEFL_BY_CARRIES and the " +
        "roof+floor conversion exist to prevent.",
        "model the combined assembly as one framing kind with a declared assembly psf, or split the " +
        "opening so each header carries one path, or add the combination to weights.js " +
        "DEFL_BY_CARRIES and demandFor with a stated load conversion.",
        [op.id, w.id].concat(over.map(function (c) { return c.regionId; })));
      return null;
    }
    /* guard: never emit a carries weights.js will throw on */
    if (FM.weights && FM.weights.DEFL_BY_CARRIES && !has(FM.weights.DEFL_BY_CARRIES, carries)) {
      refuse(run, "header-carries-unknown",
        "the header at opening " + op.id + " would declare carries \"" + carries + "\", which " +
        "weights.js DEFL_BY_CARRIES does not define",
        "weights.demandFor throws on an unknown carries. Emitting the mark would move a takeoff " +
        "question into a crash at solve time.",
        "add the load path to weights.js DEFL_BY_CARRIES with its deflection row, or change the " +
        "framing kinds landing on this wall.",
        [op.id, w.id]);
      return null;
    }

    /* --- bearing: jacks from the clear opening --- */
    var jk = jacksFor(op.widthFt);
    if (!jk) {
      refuse(run, "header-opening-too-wide",
        "opening " + op.id + " is " + f2(op.widthFt) + " ft clear, at or over the 18 ft limit of " +
        "this module's jack rule",
        "the jack count for an opening this size is a designed bearing detail — a post or a column " +
        "with a designed cap, not a stack of jack studs — and reading it off a width band would be " +
        "an invented number on the one check (Fc perp) it governs.",
        "declare the bearing detail for this opening (jack count or the designed bearing length in " +
        "inches), and expect an engineered header: a solid-sawn simple span this long is outside " +
        "the engine's ladder anyway (calc-spec §8.6, §8.19).",
        [op.id, w.id]);
      return null;
    }
    var bearingFt = jk.bearingIn / 12;

    /* --- the wall each end bears on --- */
    var leftWall = o1, rightWall = g.len - o2;
    var postEnds = [];
    var shortEnds = [];
    if (leftWall <= EPS_FT) postEnds.push("start");
    else if (leftWall < bearingFt - EPS_FT) shortEnds.push(["start", leftWall]);
    if (rightWall <= EPS_FT) postEnds.push("end");
    else if (rightWall < bearingFt - EPS_FT) shortEnds.push(["end", rightWall]);
    if (shortEnds.length) {
      refuse(run, "header-bearing-short",
        "opening " + op.id + " leaves " +
        list(shortEnds.map(function (s) { return f3(s[1]) + " ft of wall at its " + s[0]; })) +
        ", less than the " + f3(bearingFt) + " ft (" + f2(jk.bearingIn) + " in) of jack bearing this " +
        "header needs",
        "the bearing this header would declare does not exist in the wall as drawn. Declaring it " +
        "anyway would pass a bearing check against studs that are not there — and bearing is a " +
        "governing check, not a formality.",
        "widen the wall segment, move the opening, or declare a post/column with a designed cap at " +
        "that end (axial members are out of scope here — calc-spec §4.10, §8.20).",
        [op.id, w.id]);
      return null;
    }

    /* --- a bearing wall teeing into the opening is a point load --- */
    var tees = teeInOpening(model, index, entry, o1, o2);
    if (tees.length) {
      refuse(run, "header-point-load",
        "bearing wall(s) " + list(tees) + " land on wall " + w.id + " inside opening " + op.id,
        "that is a concentrated load on the header, and calc-spec §8.3 admits a uniform full-span " +
        "load only. Smearing a bearing-line reaction into a uniform psf would understate the " +
        "moment under the point and misplace the shear.",
        "move the intersecting wall clear of the opening, or size this header outside this engine " +
        "as a beam with a point load and publish the reaction.",
        [op.id, w.id].concat(tees));
      return null;
    }

    /* --- head height --- */
    var headHeightIn = null;
    if (isNum(op.headHeightFt) && op.headHeightFt > 0) headHeightIn = op.headHeightFt * 12;

    /* --- build the spec (grouped and emitted by the caller) --- */
    var trib = 0;
    over.forEach(function (c) { trib += c.halfSpanFt; });

    var regionIds = over.map(function (c) { return c.regionId; });
    var tribHow = over.map(function (c) {
      return "region " + c.regionId + " (" + c.kind + ", " + (c.side === "+" ? "one side" : "other side") +
             " of the wall): clear span " + f3(c.spanFt) + " ft / 2 = " + f3(c.halfSpanFt) + " ft";
    }).join("; ");
    if (nSides < 2) {
      tribHow += ". The other side contributes nothing: wall " + w.id + " is declared exterior:true, " +
                 "so the outboard side is outside the building and no framing region bears on it " +
                 "there. Roof overhang / eave tributary is NOT included — the geometry model has no " +
                 "eave, and inventing one would be a number off a sales sheet.";
    }
    tribHow += ". Half of the CLEAR span, consistent with the span rule; half of the centre-to-" +
               "centre span would be about " + f3(over.length * (w.thicknessIn || 0) / 48) +
               " ft more in total.";

    var sp = spec();
    var markId = prefix + "HDR-" + op.id;
    sp.set("id", markId, "opening " + op.id, [op.id],
      "mark id = level prefix + HDR + the drawn opening's id. If identical openings are grouped, " +
      "the id names the first opening in the group and the count derivation lists the rest.");
    sp.set("label",
      "Header · " + (op.kind || "opening") + " " + f2(op.widthFt) + " ft · wall " + w.id +
      " · " + lv.label,
      "opening " + op.id + " and wall " + w.id, [op.id, w.id],
      "label composed from the opening kind, its clear width, the wall it is in and the level.");
    sp.set("role", "header", "opening " + op.id, [op.id],
      "an opening in a bearing wall is spanned by a header. This module emits no beam marks: the " +
      "geometry model has no beam or girder entity, so a flush girder in a bearing line reaches " +
      "here as an opening in that wall and is carried as a header (same ladder, same repetitive " +
      "flag in weights.js; only the bearing default differs, and bearing is declared here).");
    sp.set("carries", carries, "framing regions " + list(regionIds), regionIds,
      "carries is read from the framing KIND(s) that land on this wall over the opening (" +
      list(kindList) + "), never from the role string. weights.js deliberately has no CARRIES_DEFAULT " +
      "for a header for exactly this reason.");
    sp.set("span", clean(op.widthFt), "opening " + op.id, [op.id],
      "the clear opening between jacks, straight off the drawing: " + f3(op.widthFt) + " ft. NOTE: " +
      "centre-to-centre of bearings — calc-spec's other reading of L — would be " +
      f3(op.widthFt + bearingFt) + " ft (clear + " + f2(jk.bearingIn) + " in, half a bearing at each " +
      "end), and the existing weights.js plan marks use clear + a full bearing at each end (" +
      f3(op.widthFt + 2 * bearingFt) + " ft). This module emits the CLEAR distance the FM.takeoff " +
      "contract specifies. If the reviewer wants a longer span it is a stated decision, not a " +
      "default this module made quietly.");
    if (carries === "roof+floor") {
      sp.set("tribRoof", clean(tribByKind.roof || 0), "framing regions " + list(regionIds), regionIds,
        "roof tributary = " + tribHow);
      sp.set("tribFloor", clean(tribByKind.floor || 0), "framing regions " + list(regionIds), regionIds,
        "floor tributary = " + tribHow + " weights.demandFor converts the two paths exactly: total " +
        "line load q_roof x t_roof + q_floor x t_floor, expressed as psf over t_roof + t_floor.");
    } else {
      sp.set("trib", clean(trib), "framing regions " + list(regionIds), regionIds,
        "tributary = sum of half the clear span of every framing region bearing on wall " + w.id +
        " over this opening: " + tribHow + " Total " + f3(trib) + " ft.");
    }
    sp.set("bearing", jk.bearingIn, "opening " + op.id + " width", [op.id],
      "clear opening " + f2(op.widthFt) + " ft is " + jk.band + ", so " + jk.jacks + " jack stud" +
      (jk.jacks === 1 ? "" : "s") + " per end x 1.5 in = " + f2(jk.bearingIn) + " in of bearing. " +
      JACK_RULE_TEXT);
    sp.set("count", 1, "opening " + op.id, [op.id],
      "one header per opening: opening " + op.id + " is the only one in this model whose derived " +
      "values are all identical (clear opening, tributary, load path, bearing, head height, wall " +
      "position), so it stands alone rather than being grouped into a type.");
    sp.set("skuGroup", "header", "role", [op.id],
      "headers are unified against other headers only.");
    sp.set("braced", true, "wall " + w.id, [w.id],
      "the header sits in a framed wall with the top plate continuous over it and cripples above, " +
      "so the compression edge is restrained by the wall framing and C_L is taken as 1.0. This is a " +
      "CONSTRUCTION assumption, not a geometric one — the model does not draw studs. A dropped or " +
      "exposed beam in an open wall is NOT braced and must declare braced:false; on the unbraced " +
      "path the engine's own §7.3 fixture moves from DCR 0.543 to 1.252.");
    if (headHeightIn !== null) {
      sp.set("headHeightIn", clean(headHeightIn), "opening " + op.id, [op.id],
        "head height " + f3(op.headHeightFt) + " ft x 12 = " + f2(headHeightIn) + " in. " +
        "weights.demandFor turns this into the depth budget: plate height - head height - 3.0 in " +
        "(double top plate) - 0.5 in (shim).");
    }
    if (w.exterior === true && li === 0) {
      sp.set("wallPosition", "exterior-first-floor", "wall " + w.id + " on level " + lv.id,
        [w.id, lv.id],
        "wall " + w.id + " declares exterior:true and it is on the lowest level in the model, which " +
        "is taken as the first floor above grade (levels are read bottom-up). weights.applicability " +
        "uses this to remove the mark in concrete-block markets, where a first-floor exterior " +
        "opening is spanned by a lintel rather than a wood header. Declaring it wrongly deletes a " +
        "real member; omitting it sizes wood where the market builds block.");
    }
    sp.set("note",
      "Takeoff-derived. Clear opening " + f3(op.widthFt) + " ft in bearing wall " + w.id +
      "; tributary " + (carries === "roof+floor"
        ? f3(tribByKind.roof || 0) + " ft roof + " + f3(tribByKind.floor || 0) + " ft floor"
        : f3(trib) + " ft") +
      " from region(s) " + list(regionIds) + "; bearing " + f2(jk.bearingIn) + " in (" + jk.jacks +
      " jack" + (jk.jacks === 1 ? "" : "s") + " per end, " + jk.band + " rule)." +
      (above ? " CARRIES A WALL ABOVE (" + above.id + ") THAT IS NOT IN THE LOAD — see warnings." : ""),
      "opening " + op.id, [op.id],
      "one-line restatement of this mark's own derivations, so the schedule row carries its basis.");

    if (above) {
      warn(run, "wall-above-not-loaded",
        "Header " + markId + " (opening " + op.id + ", wall " + w.id + ") carries wall " + above.id +
        " standing on it on the level above, and that load is NOT in the demand: ASSEMBLY{} in " +
        "weights.js has no wall dead load of any kind (register §L6). The framing tributary derived " +
        "here is real and complete; the wall on top of it is missing. A 9 ft wall is of the order of " +
        "a tenth of what a floor strip of the same tributary contributes, and it is systematically " +
        "on the unsafe side. Add a wall dead load to weights.js, or check this header by hand.",
        [markId, op.id, w.id, above.id]);
    }
    if (headHeightIn === null) {
      warn(run, "no-head-height",
        "Opening " + op.id + " declares no headHeightFt, so header " + markId + " carries no depth " +
        "budget and weights.demandFor will impose no maxDepthIn. A member that does not fit under " +
        "the plate would not be caught — and a header that does not fit is not a cheaper header, it " +
        "is a plate-height change and a revision.",
        [markId, op.id]);
    }

    return {
      sp: sp, markId: markId, openingId: op.id, wallId: w.id, count: 1,
      postEnds: postEnds, carries: carries,
      key: [carries, f3(op.widthFt), f3(trib), f3(tribByKind.roof || 0), f3(tribByKind.floor || 0),
            String(jk.bearingIn), String(headHeightIn), String(w.exterior === true && li === 0),
            postEnds.join("+"), (multiLevel ? lv.id : "")].join("|")
    };
  }

  /* ---------------- posts ---------------- */

  function emitPost(run, hdr, openingIds, wallIds, nHeaders) {
    var n = hdr.postEnds.length * nHeaders;
    var sp = spec();
    var id = "PST-" + hdr.markId;
    sp.set("id", id, "header " + hdr.markId, [hdr.markId],
      "post mark id = PST- + the header it stands under.");
    sp.set("label", "Post under header " + hdr.markId + " · " + list(hdr.postEnds) + " end",
      "header " + hdr.markId, [hdr.markId],
      "names the header and which end(s) of it land on a post rather than on wall.");
    sp.set("role", "post", "geometry", [hdr.markId],
      "the header's bearing at " + list(hdr.postEnds) + " falls at the end of wall " +
      list(wallIds) + " — there is no wall beyond it, so the reaction lands on a post or king-stud " +
      "pack at the corner.");
    sp.set("count", n, "openings " + list(openingIds), openingIds,
      hdr.postEnds.length + " post end(s) per header x " + nHeaders + " header(s) = " + n + ".");
    sp.set("component", true, "calc-spec §4.10, §8.20", [],
      "flagged component so weights.applicability removes it from the member search rather than " +
      "reporting it as a member that failed. It is not this engine's member.");
    sp.set("reactionFrom", [hdr.markId], "header " + hdr.markId, [hdr.markId],
      "solver.solvePlan resolves the design load live from THIS run's reaction for the named mark, " +
      "for this pack and this variant, instead of a number typed into prose that goes stale the " +
      "next time a load moves.");
    sp.set("componentNote", POST_NOTE, "calc-spec §4.10, §8.20", [],
      "the standing refusal for axial members in this codebase, restated on the mark so the " +
      "schedule shows what is NOT being designed.");
    sp.set("note",
      "Emitted because header " + hdr.markId + " lands on a post at its " + list(hdr.postEnds) +
      " end, not on wall. Published rather than dropped: a bearing this engine will not check is " +
      "still a bearing somebody has to detail.",
      "geometry", openingIds.concat(wallIds),
      "states why the mark exists at all.");
    emit(run, sp);
  }

  /* ---------------- the audit ----------------
     Nothing leaves this module that weights.demandFor would throw on, and
     nothing leaves it without a derivation. A failure here is a bug in this
     file, not a condition in the data — every data condition became an
     unresolved entry upstream — so it throws loudly. */
  function audit(run) {
    var byMark = {};
    run.derivations.forEach(function (d) {
      if (!has(byMark, d.markId)) byMark[d.markId] = {};
      byMark[d.markId][d.field] = 1;
    });
    run.marks.forEach(function (m) {
      var k, seen = byMark[m.id] || {};
      for (k in m) {
        if (!has(m, k)) continue;
        if (!has(seen, k)) {
          throw new Error("takeoff: mark " + m.id + " field \"" + k + "\" has no derivation");
        }
      }
      if (m.component) return;                       /* out-of-scope marks are not sized */
      if (!m.carries) throw new Error("takeoff: mark " + m.id + " has no carries");
      if (!(m.span > 0)) throw new Error("takeoff: mark " + m.id + " has no positive span");
      if (m.role === "header" && !(m.bearing > 0)) {
        throw new Error("takeoff: header " + m.id + " has no bearing — weights.demandFor throws on " +
                        "a header that does not declare jack studs x 1.5 in");
      }
      if (m.carries === "roof+floor" && !(m.tribRoof >= 0 && m.tribFloor >= 0 &&
                                          m.tribRoof + m.tribFloor > 0)) {
        throw new Error("takeoff: mark " + m.id + " carries roof+floor and must declare tribRoof " +
                        "and tribFloor");
      }
      if (m.carries !== "roof+floor" && !(m.trib > 0) && !(m.role === "joist" || m.role === "rafter" ||
          m.role === "ceiling" || m.role === "deck")) {
        throw new Error("takeoff: mark " + m.id + " has no tributary");
      }
    });
  }

  /* ---------------- run ---------------- */

  /* run(model, opts) -> { marks, derivations, unresolved, warnings, stats }

     opts.groupHeaders   default true. Openings identical in EVERY derived
                         value become one mark with a count, the way a
                         schedule names a type rather than an instance.
                         Set false to keep one mark per opening.

     There is no option that makes this module assume anything. */
  function run(model, opts) {
    opts = opts || {};
    if (!model || typeof model !== "object" || !Array.isArray(model.levels)) {
      throw new TypeError("FM.takeoff.run(model): model must be an FM.cad model with a levels array");
    }
    var out = makeRun();
    var index = indexWalls(model, out);
    var levels = model.levels;
    var multiLevel = levels.length > 1;

    if (!levels.length) {
      refuse(out, "model", "the model has no levels",
             "there is no geometry to take off.",
             "draw at least one level with walls and framing.", []);
      return finish(out, model);
    }

    /* --- pass A ---
       Every level is analysed, always. There is deliberately no "just this
       level" option: framing on level 2 bears on walls on level 1, so a
       level filter would drop supports and turn a determined span into a
       refusal — or worse, drop a load path off a header and leave the mark
       looking complete. Filter the returned marks by id prefix instead. */
    var regions = [];
    levels.forEach(function (lv, li) {
      var prefix = multiLevel ? lv.id + "-" : "";
      (lv.framing || []).forEach(function (reg) {
        regions.push(regionRecord(out, model, index, lv, li, reg, prefix));
      });
    });

    /* --- pass B --- */
    var table = supportTable(index, regions);

    /* a wall declared non-bearing that framing declares it bears on is a
       contradiction in the drawing, and it decides whether openings in it
       get headers */
    Object.keys(table).forEach(function (wid) {
      var e = index[wid];
      if (!e) return;
      var t = table[wid];
      if (e.wall.bearing !== true && (t.contributions.length || t.poisoned.length)) {
        var ids = t.contributions.map(function (c) { return c.regionId; })
          .concat(t.poisoned.map(function (p) { return p.regionId; }));
        refuse(out, "wall-bearing-contradiction",
          "wall " + wid + " is declared bearing:" + String(e.wall.bearing) + " but framing region(s) " +
          list(ids) + " declare that they bear on it",
          "the drawing says two different things about the same wall. Following bearsOn would put a " +
          "header under an opening the wall flag says needs none; following the flag would drop the " +
          "framing's support. Neither can be chosen without guessing which one the drafter meant.",
          "set bearing:true on the wall if framing lands on it, or remove it from the framing's " +
          "bearsOn list — and check the framing region's span afterwards, because it may then have " +
          "only one support.",
          [wid].concat(ids));
      }
    });

    /* --- pass C --- */
    var pending = [];
    levels.forEach(function (lv, li) {
      var prefix = multiLevel ? lv.id + "-" : "";
      (lv.openings || []).forEach(function (op) {
        var h = headerSpec(out, model, index, table, lv, li, op, prefix, multiLevel);
        if (h) pending.push(h);
      });
    });

    /* group identical headers into one mark with a count — a mark is a TYPE.
       The key covers every field that could differ, so two marks are only
       ever merged when every derived number on them is identical. */
    var groups = [], byKey = {};
    pending.forEach(function (h) {
      if (opts.groupHeaders === false) { groups.push([h]); return; }
      if (!has(byKey, h.key)) { byKey[h.key] = []; groups.push(byKey[h.key]); }
      byKey[h.key].push(h);
    });
    groups.forEach(function (grp) {
      var first = grp[0];
      var ids = grp.map(function (h) { return h.openingId; });
      var wallIds = [];
      grp.forEach(function (h) { if (wallIds.indexOf(h.wallId) === -1) wallIds.push(h.wallId); });
      if (grp.length > 1) {
        first.sp.replace("count", grp.length, "openings " + list(ids), ids,
          grp.length + " openings in this model are identical in every derived value — clear " +
          "opening, tributary, load path, bearing, head height and wall position — so they are one " +
          "mark built " + grp.length + " times: " + list(ids) + ". They are grouped only on exact " +
          "equality of those numbers; nothing is rounded to make two marks match.");
      }
      emit(out, first.sp);
      if (first.postEnds.length) emitPost(out, first, ids, wallIds, grp.length);
    });

    /* --- run-level conventions the reviewer has to see --- */
    conventionWarnings(out, model, regions);

    audit(out);
    return finish(out, model);
  }

  function conventionWarnings(out, model, regions) {
    var framing = out.marks.filter(function (m) {
      return m.role === "joist" || m.role === "rafter" || m.role === "ceiling" || m.role === "deck";
    });
    var headers = out.marks.filter(function (m) { return m.role === "header"; });

    if (out.marks.length) {
      warn(out, "span-convention",
        "SPANS ARE CLEAR DISTANCES. Every span in this takeoff is face to face — for framing, " +
        "between the wall faces; for a header, the clear opening between jacks. calc-spec's symbol " +
        "table also reads L as \"center-to-center of bearings\", which is one bearing length longer " +
        "(0.25 ft at a 3 in bearing: about 2% of span and 4% of moment on a 12 ft member, always in " +
        "the unsafe direction from here). Each span derivation prints the centre-to-centre value " +
        "beside the clear one. This module does not choose the larger number on the reviewer's " +
        "behalf — approval gate 2 does.",
        out.marks.map(function (m) { return m.id; }));
    }
    if (headers.length) {
      warn(out, "trib-convention",
        "TRIBUTARIES ARE HALF THE CLEAR SPAN and exclude roof overhang. Half the centre-to-centre " +
        "span would be about a quarter of a wall thickness more per side (0.11 ft on a 5.5 in wall). " +
        "Roof overhang and eave are not in the geometry model at all: on a 1 ft eave over a 16 ft " +
        "tributary that is 6% of load that is not here. If the eave is real, it must be drawn or " +
        "declared.",
        headers.map(function (m) { return m.id; }));
      warn(out, "jack-rule",
        "BEARING IS A DERIVED VALUE, NOT A MEASURED ONE. " + JACK_RULE_TEXT,
        headers.map(function (m) { return m.id; }));
      warn(out, "braced-assumed",
        "EVERY HEADER IS DECLARED braced:true — restrained by the wall framing. The model does not " +
        "draw studs or sheathing, so this is a construction assumption. On the engine's own §7.3 " +
        "fixture, removing bracing moves bending DCR from 0.543 to 1.252. Any exposed or dropped " +
        "member in this list must be re-declared braced:false.",
        headers.map(function (m) { return m.id; }));
    }

    var roofMarks = out.marks.filter(function (m) { return m.carries === "roof"; });
    if (roofMarks.length) {
      warn(out, "roof-pitch-absent",
        "ROOF SPANS ARE HORIZONTAL. The geometry model declares no roof pitch, so a roof framing " +
        "region is measured in plan projection and the sloped length of the member is not " +
        "derivable. That matches how weights.js applies roof assembly psf (horizontal projection) " +
        "and it is wrong for a steep pitch if the assembly is expressed along the slope. Add a " +
        "pitch to the framing region to remove this.",
        roofMarks.map(function (m) { return m.id; }));
    }

    /* the drawn spacing versus the ladder the solver will actually search */
    if (FM.weights && FM.weights.SPACINGS) {
      framing.forEach(function (m) {
        var ladder = FM.weights.SPACINGS[m.role];
        if (ladder && ladder.indexOf(m.spacingIn) === -1) {
          warn(out, "spacing-not-in-ladder",
            "Mark " + m.id + " is drawn at " + m.spacingIn + " in o.c., which is not in the spacing " +
            "ladder weights.js offers for a " + m.role + " (" + ladder.join(", ") + " in). The solver " +
            "will size the member at a spacing the drawing does not show, and solver.pieceCount() " +
            "will recompute the quantity from that spacing — so the member AND the count on the " +
            "schedule will both differ from this takeoff. Reconcile the drawing with the ladder, or " +
            "add the rung in weights.js with its reason.",
            [m.id]);
        }
      });
    }

    /* regions drawn but not taken off */
    var lost = regions.filter(function (r) { return r && !r.determined; });
    if (lost.length) {
      warn(out, "regions-not-taken-off",
        lost.length + " framing region(s) produced no mark: " +
        list(lost.map(function (r) { return r.id; })) + ". Each has an unresolved entry saying why " +
        "and what it needs. Any header in a wall those regions bear on is refused too, rather than " +
        "sized on the framing that did resolve.",
        lost.map(function (r) { return r.id; }));
    }
  }

  function finish(out, model) {
    out.model = { name: model.name || null, version: model.version || null,
                  levels: (model.levels || []).length };
    out.stats = {
      marks: out.marks.length,
      derivations: out.derivations.length,
      unresolved: out.unresolved.length,
      warnings: out.warnings.length,
      byRole: (function () {
        var r = {};
        out.marks.forEach(function (m) { r[m.role] = (r[m.role] || 0) + 1; });
        return r;
      })()
    };
    return out;
  }

  FM.takeoff = {
    VERSION: VERSION,
    run: run,
    RULES: RULES,
    EPS_FT: EPS_FT,
    ANG_EPS_DEG: ANG_EPS_DEG,
    SPAN_VARY_FT: SPAN_VARY_FT,
    JACKS_BY_OPENING: JACKS_BY_OPENING,
    JACK_RULE_TEXT: JACK_RULE_TEXT,
    ROLE_BY_KIND: ROLE_BY_KIND,
    CARRIES_BY_KIND: CARRIES_BY_KIND,
    jacksFor: jacksFor
  };
})();

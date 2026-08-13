/* ============================================================
   CAD — the geometry model, its validator, and the drawing canvas.

   Units are decimal feet, origin bottom-left, +x right, +y up.
   Everything here is serialisable; nothing in the model layer
   touches the DOM, so the node harness can load this file and
   exercise validate() and fromPlan() headlessly.

   Three rules this file is built around:

     1. A model that cannot be built is not a model. validate()
        is the gate into takeoff, so every defect it knows about
        names the element and says what to do about it. A finding
        with no instruction is a complaint.

     2. Nothing is invented. fromPlan() derives geometry from the
        numbers weights.js actually declares. Where the plan does
        not determine something — where a lanai sits along a face,
        which side of a duplex is the party wall, how thick a wall
        is — the model records the hole by name in `unresolved`
        and validate() reports it as a warn. An opening whose
        position the plan does not state is placed as a PLACEHOLDER
        and says so on the element; it is never quietly asserted.

     3. The human traces; the machine does not read drawings. An
        underlay is a calibrated raster and nothing more. Two
        clicks and a real distance give ft-per-pixel — that is the
        whole of the machine's opinion about the image.
   ============================================================ */

(function () {
  "use strict";

  var MODEL_VERSION = 1;

  /* ---------------- framing conventions ----------------

     These are GEOMETRIC framing conventions, not load values, and
     they are named here rather than buried in a check so the
     number a finding is measured against can be read and changed.

     jack + king = 1.5 + 1.5 in of stud at each side of an opening:
     one jack carrying the header and one king running full height.
     weights.js uses the same 1.5 in per jack for header bearing
     ("a header bears on jack studs — 1.5 in per jack"). Two
     adjacent openings each need their own pair, so the minimum
     clear framing between them is twice the end clearance. */

  var RULES = {
    jackStudIn: 1.5,
    kingStudIn: 1.5,
    minWallFt: 0.5,        /* shorter than this is a mis-click, not a wall */
    orthoDeg: 4,           /* auto-lock to an axis inside this angle */
    snapPx: 11,            /* endpoint snap radius, screen pixels */
    touchTolFt: 0.5,       /* how close a wall must lie to a region to bear on it */
    touchMinFt: 1.0,       /* and for how much of its length */
    crossTolFt: 0.02,      /* below this, a crossing is a shared node */
    undoDepth: 50
  };
  function endClearFt() { return (RULES.jackStudIn + RULES.kingStudIn) / 12; }

  var OPENING_KINDS = ["window", "door", "slider", "garage"];
  var FRAMING_KINDS = ["floor", "roof", "ceiling", "deck"];
  var STORE_KEY = "firmark.cad.models.v1";

  /* ---------------- small helpers ---------------- */

  function isArr(x) { return Object.prototype.toString.call(x) === "[object Array]"; }
  function own(o, k) { return o && Object.prototype.hasOwnProperty.call(o, k) ? o[k] : undefined; }
  function num(v) {
    if (v === null || v === undefined || v === "") return null;
    var n = Number(v);
    return isFinite(n) ? n : null;
  }
  function near(a, b, tol) { return Math.abs(a - b) <= (tol === undefined ? 0.01 : tol); }
  function dist(x1, y1, x2, y2) {
    var dx = x2 - x1, dy = y2 - y1;
    return Math.sqrt(dx * dx + dy * dy);
  }
  function copy(o) {
    var out = {}, k;
    for (k in o) if (Object.prototype.hasOwnProperty.call(o, k)) out[k] = o[k];
    return out;
  }
  function f1(v) { return (Math.round(v * 10) / 10).toFixed(1); }
  function f2(v) { return (Math.round(v * 100) / 100).toFixed(2); }

  /* feet-and-inches to the nearest quarter inch — what a framer reads */
  function ftIn(v) {
    if (v === null || v === undefined || !isFinite(v)) return "—";
    var neg = v < 0;
    var q = Math.round(Math.abs(v) * 48);          /* quarter inches */
    var ft = Math.floor(q / 48);
    var rem = q - ft * 48;
    var inch = Math.floor(rem / 4);
    var qq = rem - inch * 4;
    var s = ft + "'-" + inch;
    if (qq === 1) s += " 1/4";
    else if (qq === 2) s += " 1/2";
    else if (qq === 3) s += " 3/4";
    return (neg ? "-" : "") + s + "\"";
  }

  /* ---------------- geometry ---------------- */

  function wallLength(w) { return w ? dist(w.x1, w.y1, w.x2, w.y2) : 0; }
  function wallAngleDeg(w) {
    return Math.atan2(w.y2 - w.y1, w.x2 - w.x1) * 180 / Math.PI;
  }
  /* a point `t` feet along the wall from (x1,y1) */
  function pointAlong(w, t) {
    var L = wallLength(w);
    if (L < 1e-9) return { x: w.x1, y: w.y1 };
    return { x: w.x1 + (w.x2 - w.x1) * (t / L), y: w.y1 + (w.y2 - w.y1) * (t / L) };
  }
  /* unit normal, left of the wall's own direction */
  function wallNormal(w) {
    var L = wallLength(w);
    if (L < 1e-9) return { x: 0, y: 1 };
    return { x: -(w.y2 - w.y1) / L, y: (w.x2 - w.x1) / L };
  }
  /* distance from a point to a segment, and how far along it lands */
  function projectOnWall(w, px, py) {
    var dx = w.x2 - w.x1, dy = w.y2 - w.y1;
    var L2 = dx * dx + dy * dy;
    if (L2 < 1e-12) return { t: 0, d: dist(px, py, w.x1, w.y1), x: w.x1, y: w.y1, u: 0 };
    var u = ((px - w.x1) * dx + (py - w.y1) * dy) / L2;
    var cu = Math.max(0, Math.min(1, u));
    var qx = w.x1 + dx * cu, qy = w.y1 + dy * cu;
    return { t: cu * Math.sqrt(L2), d: dist(px, py, qx, qy), x: qx, y: qy, u: u };
  }

  /* Interior crossing of two segments — a shared endpoint or a
     T-junction is a NODE and does not count. Only a true X does. */
  function segCross(a, b) {
    var ax = a.x2 - a.x1, ay = a.y2 - a.y1;
    var bx = b.x2 - b.x1, by = b.y2 - b.y1;
    var den = ax * by - ay * bx;
    if (Math.abs(den) < 1e-12) return null;                  /* parallel */
    var ua = ((b.x1 - a.x1) * by - (b.y1 - a.y1) * bx) / den;
    var ub = ((b.x1 - a.x1) * ay - (b.y1 - a.y1) * ax) / den;
    var la = Math.sqrt(ax * ax + ay * ay), lb = Math.sqrt(bx * bx + by * by);
    if (la < 1e-9 || lb < 1e-9) return null;
    var ea = RULES.crossTolFt / la, eb = RULES.crossTolFt / lb;
    if (ua <= ea || ua >= 1 - ea || ub <= eb || ub >= 1 - eb) return null;
    return { x: a.x1 + ax * ua, y: a.y1 + ay * ua };
  }

  function polyArea(poly) {
    if (!isArr(poly) || poly.length < 3) return 0;
    var s = 0, i, j;
    for (i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      s += (poly[j][0] * poly[i][1]) - (poly[i][0] * poly[j][1]);
    }
    return Math.abs(s) / 2;
  }
  function pointInPoly(poly, x, y) {
    if (!isArr(poly) || poly.length < 3) return false;
    var inside = false, i, j;
    for (i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      var xi = poly[i][0], yi = poly[i][1], xj = poly[j][0], yj = poly[j][1];
      if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) inside = !inside;
    }
    return inside;
  }
  function distToPolyEdge(poly, x, y) {
    var best = Infinity, i, j;
    for (i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      var seg = { x1: poly[j][0], y1: poly[j][1], x2: poly[i][0], y2: poly[i][1] };
      var p = projectOnWall(seg, x, y);
      if (p.d < best) best = p.d;
    }
    return best;
  }
  /* How many feet of this wall lie on or inside the region. A wall on
     the region's edge bears it; so does an interior line running
     underneath it. Sampled, because exact segment-polygon clipping is
     more machinery than a 40 ft wall needs. */
  function wallOverlapFt(poly, w) {
    var L = wallLength(w);
    if (L < 1e-9 || !isArr(poly) || poly.length < 3) return 0;
    var step = 0.25, n = Math.max(3, Math.ceil(L / step)), hit = 0, i;
    for (i = 0; i <= n; i++) {
      var p = pointAlong(w, L * i / n);
      if (pointInPoly(poly, p.x, p.y) || distToPolyEdge(poly, p.x, p.y) <= RULES.touchTolFt) hit++;
    }
    return (hit / (n + 1)) * L;
  }
  function touchesRegion(poly, w) {
    var L = wallLength(w);
    return wallOverlapFt(poly, w) >= Math.min(RULES.touchMinFt, L * 0.5);
  }

  /* ---------------- the model ---------------- */

  function blankLevel(id, label, topPlateFt) {
    return {
      id: id || "L1",
      label: label || "First floor",
      topPlateFt: topPlateFt === undefined ? null : topPlateFt,
      walls: [], openings: [], framing: []
    };
  }

  function blank(name) {
    return {
      version: MODEL_VERSION,
      name: name || "Untitled plan",
      levels: [blankLevel("L1", "First floor", null)],
      underlay: null,
      /* Holes the model itself cannot show: something the source plan
         declares but does not locate, or a member this model has no
         element for. Same shape takeoff.js publishes. */
      unresolved: []
    };
  }

  function levelOf(model, levelId) {
    if (!model || !isArr(model.levels) || !model.levels.length) return null;
    if (!levelId) return model.levels[0];
    var hit = null;
    model.levels.forEach(function (l) { if (l.id === levelId) hit = l; });
    return hit;
  }
  function wallById(level, id) {
    var hit = null;
    (level.walls || []).forEach(function (w) { if (w.id === id) hit = w; });
    return hit;
  }
  function nextId(list, prefix) {
    var max = 0;
    (list || []).forEach(function (o) {
      var m = new RegExp("^" + prefix + "(\\d+)$").exec(String(o.id || ""));
      if (m) max = Math.max(max, Number(m[1]));
    });
    return prefix + (max + 1);
  }

  function newWall(level, x1, y1, x2, y2, over) {
    var w = {
      id: nextId(level.walls, "W"),
      x1: x1, y1: y1, x2: x2, y2: y2,
      exterior: true, bearing: true,
      heightFt: level.topPlateFt === null ? null : level.topPlateFt,
      thicknessIn: null,
      /* "user" — a human set it; "assumed" — fromPlan chose it because the
         source plan declares no stud size, and validate() says so out loud */
      thicknessBasis: "user",
      note: ""
    };
    if (over) Object.keys(over).forEach(function (k) { w[k] = over[k]; });
    return w;
  }
  function newOpening(level, wallId, offsetFt, widthFt, over) {
    var o = {
      id: nextId(level.openings, "O"),
      wallId: wallId, offsetFt: offsetFt, widthFt: widthFt,
      headHeightFt: null, kind: "window", note: "",
      /* "user" — a human put it there; "plan" — the source plan located
         it; "placeholder" — nothing located it and it must be moved. */
      offsetBasis: "user"
    };
    if (over) Object.keys(over).forEach(function (k) { o[k] = over[k]; });
    return o;
  }
  function newFraming(level, poly, over) {
    var f = {
      id: nextId(level.framing, "F"),
      polygon: poly, kind: "floor",
      directionDeg: 0, spacingIn: null, bearsOn: [], note: ""
    };
    if (over) Object.keys(over).forEach(function (k) { f[k] = over[k]; });
    return f;
  }

  /* ---------------- serialisation ---------------- */

  function toJSON(model) { return JSON.stringify(model, null, 2); }

  function fromJSON(str) {
    var raw;
    try { raw = JSON.parse(String(str)); }
    catch (e) {
      throw new Error("That is not JSON — the parser stopped at: " + e.message +
                      ". Paste the whole file, from the first { to the last }.");
    }
    if (!raw || typeof raw !== "object" || isArr(raw)) {
      throw new Error("A model is a JSON object with a `levels` array. This was " +
                      (isArr(raw) ? "an array" : typeof raw) + ".");
    }
    var v = num(raw.version);
    if (v !== null && v > MODEL_VERSION) {
      throw new Error("This model says version " + v + " and this build understands version " +
                      MODEL_VERSION + ". Open it in the build that wrote it, or export it again from there.");
    }
    if (!isArr(raw.levels) || !raw.levels.length) {
      throw new Error("This model has no `levels` array, so there is nothing to draw. " +
                      "A model needs at least one level with a `walls` array.");
    }
    return normalise(raw);
  }

  /* Fill in what a hand-edited or older file may leave out. Missing is
     null, never a number: a wall with no declared thickness reads as
     undeclared, not as 3.5 in. */
  function normalise(raw) {
    var m = blank(raw.name || "Untitled plan");
    m.version = MODEL_VERSION;
    m.levels = [];
    (raw.levels || []).forEach(function (L, i) {
      var lv = blankLevel(L.id || ("L" + (i + 1)), L.label || ("Level " + (i + 1)), num(L.topPlateFt));
      lv.note = L.note || "";
      (L.walls || []).forEach(function (w) {
        lv.walls.push({
          id: String(w.id || nextId(lv.walls, "W")),
          x1: num(w.x1) || 0, y1: num(w.y1) || 0, x2: num(w.x2) || 0, y2: num(w.y2) || 0,
          exterior: !!w.exterior, bearing: !!w.bearing,
          heightFt: num(w.heightFt), thicknessIn: num(w.thicknessIn),
          thicknessBasis: w.thicknessBasis === "assumed" ? "assumed" : "user",
          note: w.note || "", basis: w.basis || ""
        });
      });
      (L.openings || []).forEach(function (o) {
        lv.openings.push({
          id: String(o.id || nextId(lv.openings, "O")),
          wallId: String(o.wallId || ""),
          offsetFt: num(o.offsetFt) || 0, widthFt: num(o.widthFt) || 0,
          headHeightFt: num(o.headHeightFt),
          kind: OPENING_KINDS.indexOf(o.kind) === -1 ? "window" : o.kind,
          note: o.note || "", offsetBasis: o.offsetBasis || "user"
        });
      });
      (L.framing || []).forEach(function (f) {
        var poly = [];
        (isArr(f.polygon) ? f.polygon : []).forEach(function (p) {
          if (isArr(p) && p.length >= 2) poly.push([num(p[0]) || 0, num(p[1]) || 0]);
        });
        lv.framing.push({
          id: String(f.id || nextId(lv.framing, "F")),
          polygon: poly,
          kind: FRAMING_KINDS.indexOf(f.kind) === -1 ? "floor" : f.kind,
          directionDeg: num(f.directionDeg),
          spacingIn: num(f.spacingIn),
          bearsOn: isArr(f.bearsOn) ? f.bearsOn.slice() : [],
          note: f.note || "", basis: f.basis || ""
        });
      });
      m.levels.push(lv);
    });
    if (raw.underlay && raw.underlay.dataUri) {
      var u = raw.underlay;
      m.underlay = {
        dataUri: String(u.dataUri),
        calib: u.calib && num(u.calib.knownFt) !== null ? {
          ax: num(u.calib.ax) || 0, ay: num(u.calib.ay) || 0,
          bx: num(u.calib.bx) || 0, by: num(u.calib.by) || 0,
          knownFt: num(u.calib.knownFt)
        } : null,
        opacity: num(u.opacity) === null ? 0.35 : num(u.opacity),
        /* the raster's own pixel size and where its bottom-left corner
           sits in the model — placement, not interpretation */
        pxW: num(u.pxW), pxH: num(u.pxH),
        originFt: isArr(u.originFt) ? [num(u.originFt[0]) || 0, num(u.originFt[1]) || 0] : [0, 0],
        name: u.name || ""
      };
    }
    m.unresolved = [];
    (isArr(raw.unresolved) ? raw.unresolved : []).forEach(function (u) {
      m.unresolved.push({ what: String(u.what || ""), why: String(u.why || ""), need: String(u.need || "") });
    });
    if (raw.source) m.source = raw.source;
    return m;
  }

  /* ---------------- underlay scale ---------------- */

  function scaleOf(underlay) {
    if (!underlay || !underlay.calib) return null;
    var c = underlay.calib;
    var known = num(c.knownFt);
    if (known === null || known <= 0) return null;
    var px = dist(num(c.ax) || 0, num(c.ay) || 0, num(c.bx) || 0, num(c.by) || 0);
    if (!(px > 0)) return null;
    return known / px;
  }

  /* ---------------- stats ---------------- */

  /* The footprint area, but only when the exterior walls actually close
     one loop. A wall missing from the loop returns null rather than an
     area that silently omits a bay. */
  function footprintAreaSf(level) {
    var walls = (level.walls || []).filter(function (w) { return w.exterior && wallLength(w) > 1e-6; });
    if (walls.length < 3) return null;
    var nodes = {}, i;
    function key(x, y) { return (Math.round(x * 100) / 100) + "," + (Math.round(y * 100) / 100); }
    for (i = 0; i < walls.length; i++) {
      var a = key(walls[i].x1, walls[i].y1), b = key(walls[i].x2, walls[i].y2);
      if (a === b) return null;
      nodes[a] = (nodes[a] || []); nodes[a].push({ w: i, to: b });
      nodes[b] = (nodes[b] || []); nodes[b].push({ w: i, to: a });
    }
    var ks = Object.keys(nodes);
    for (i = 0; i < ks.length; i++) if (nodes[ks[i]].length !== 2) return null;
    /* walk it */
    var start = ks[0], cur = start, prevWall = -1, poly = [], guard = 0;
    while (guard++ < walls.length + 2) {
      var parts = cur.split(",");
      poly.push([Number(parts[0]), Number(parts[1])]);
      var opts = nodes[cur].filter(function (e) { return e.w !== prevWall; });
      if (!opts.length) return null;
      prevWall = opts[0].w;
      cur = opts[0].to;
      if (cur === start) break;
    }
    if (poly.length !== walls.length) return null;
    return polyArea(poly);
  }

  function stats(model) {
    var out = {
      levels: 0, walls: 0, exteriorWalls: 0, bearingWalls: 0, openings: 0,
      framing: 0, wallLf: 0, openingLf: 0, areaSf: null, framedSf: 0, unresolved: 0
    };
    if (!model || !isArr(model.levels)) return out;
    out.levels = model.levels.length;
    out.unresolved = isArr(model.unresolved) ? model.unresolved.length : 0;
    model.levels.forEach(function (L, i) {
      (L.walls || []).forEach(function (w) {
        out.walls++;
        if (w.exterior) out.exteriorWalls++;
        if (w.bearing) out.bearingWalls++;
        out.wallLf += wallLength(w);
      });
      (L.openings || []).forEach(function (o) { out.openings++; out.openingLf += (num(o.widthFt) || 0); });
      (L.framing || []).forEach(function (f) { out.framing++; out.framedSf += polyArea(f.polygon); });
      if (i === 0) out.areaSf = footprintAreaSf(L);
    });
    out.wallLf = Math.round(out.wallLf * 100) / 100;
    out.openingLf = Math.round(out.openingLf * 100) / 100;
    out.framedSf = Math.round(out.framedSf * 100) / 100;
    if (out.areaSf !== null) out.areaSf = Math.round(out.areaSf * 100) / 100;
    return out;
  }

  /* ---------------- does this opening fit its wall ----------------

     Exported because it is the maths behind four findings and behind
     the refusal to place an opening the user just clicked for. */

  function openingFits(wall, opening, others) {
    var L = wallLength(wall);
    var w = num(opening.widthFt), off = num(opening.offsetFt);
    var end = endClearFt();
    var id = opening.id || "this opening";
    if (w === null || w <= 0) {
      return { ok: false, code: "opening-no-width",
               text: id + " has no width. Give it a rough-opening width in feet." };
    }
    if (off === null) {
      return { ok: false, code: "opening-no-offset",
               text: id + " has no offset along " + wall.id + ". Set how far it sits from the wall start." };
    }
    if (w > L) {
      return { ok: false, code: "opening-wider-than-wall",
               text: id + " is " + f2(w) + " ft wide in " + wall.id + ", which is only " + f2(L) +
                     " ft long. Narrow the opening or lengthen the wall." };
    }
    if (off < 0 || off + w > L + 1e-9) {
      return { ok: false, code: "opening-overhangs",
               text: id + " runs from " + f2(off) + " ft to " + f2(off + w) + " ft along " + wall.id +
                     ", which is " + f2(L) + " ft long — it hangs off the " + (off < 0 ? "start" : "end") +
                     ". Move it back inside the wall." };
    }
    if (off < end - 1e-9 || (L - (off + w)) < end - 1e-9) {
      return { ok: false, code: "opening-no-jack-room",
               text: id + " leaves " + f2(Math.min(off, L - (off + w))) + " ft at one end of " + wall.id +
                     ". A jack and a king stud need " + f2(end) + " ft (" +
                     RULES.jackStudIn + " in + " + RULES.kingStudIn + " in). Move it " +
                     f2(end - Math.min(off, L - (off + w))) + " ft further in or shorten it." };
    }
    var clash = null;
    (others || []).forEach(function (o) {
      if (clash || o === opening || o.id === opening.id || o.wallId !== opening.wallId) return;
      var a1 = off, a2 = off + w, b1 = num(o.offsetFt) || 0, b2 = b1 + (num(o.widthFt) || 0);
      if (a1 < b2 - 1e-9 && b1 < a2 - 1e-9) {
        clash = { ok: false, code: "openings-overlap",
                  text: id + " overlaps " + o.id + " in " + wall.id + " — " + id + " runs " + f2(a1) +
                        "–" + f2(a2) + " ft and " + o.id + " runs " + f2(b1) + "–" + f2(b2) +
                        " ft. Move one of them." };
        return;
      }
      var gap = a1 >= b2 ? a1 - b2 : b1 - a2;
      if (gap < 2 * end - 1e-9) {
        clash = { ok: false, code: "openings-too-close",
                  text: id + " and " + o.id + " leave " + f2(gap) + " ft of wall between them in " +
                        wall.id + ". Each opening needs its own jack and king stud, so " +
                        f2(2 * end) + " ft is the minimum. Move one of them apart." };
      }
    });
    if (clash) return clash;
    return { ok: true, code: "", text: "" };
  }

  /* ---------------- validate ---------------- */

  function validate(model) {
    var rows = [];
    function add(level, id, severity, code, text) {
      rows.push({ level: level, id: id, severity: severity, code: code, text: text });
    }
    if (!model || !isArr(model.levels) || !model.levels.length) {
      add(null, "model", "error", "no-levels",
          "This model has no levels, so there is nothing to check. Start a new model or import one.");
      return rows;
    }

    var anyWall = false, anyBearing = false;

    model.levels.forEach(function (L) {
      var lid = L.id;
      var walls = L.walls || [], openings = L.openings || [], framing = L.framing || [];
      var i, j;
      /* Findings that would otherwise repeat once per element are collected
         and reported once. Fourteen identical warnings bury the one finding
         that is not identical. */
      var noThick = [], assumedThick = [], placeholders = {};

      if (walls.length) anyWall = true;

      /* ---- walls ---- */
      walls.forEach(function (w) {
        var len = wallLength(w);
        if (w.bearing) anyBearing = true;

        if (len < 1e-6) {
          add(lid, w.id, "error", "wall-zero-length",
              w.id + " has zero length — both ends are at (" + f2(w.x1) + ", " + f2(w.y1) +
              "). Delete it or drag one end away.");
          return;
        }
        if (len < RULES.minWallFt) {
          add(lid, w.id, "error", "wall-too-short",
              w.id + " is " + f2(len) + " ft long. Anything under " + f2(RULES.minWallFt) +
              " ft is a mis-click rather than a wall — delete it or extend it.");
        }
        var th = num(w.thicknessIn);
        if (th === null) {
          noThick.push(w.id);
        } else if (w.thicknessBasis === "assumed") {
          assumedThick.push(w.id + " " + f1(th) + " in");
        }
        if (th === null) {
          /* grouped below */
        } else if (th <= 0) {
          add(lid, w.id, "error", "wall-thickness-zero",
              w.id + " has a thickness of " + f2(th) + " in. A wall has to be thicker than nothing; " +
              "set 3.5 in or 5.5 in.");
        } else if (len < th / 12) {
          add(lid, w.id, "error", "wall-shorter-than-thick",
              w.id + " is " + f2(len) + " ft long and " + f2(th) + " in (" + f2(th / 12) +
              " ft) thick — it is thicker than it is long, so it is not a wall. Delete it or extend it.");
        }
        var h = num(w.heightFt);
        if (h === null) {
          add(lid, w.id, "warn", "wall-no-height",
              w.id + " has no height. Set the wall height in feet, or set the level's top plate and " +
              "apply it.");
        } else if (h <= 0) {
          add(lid, w.id, "error", "wall-height-zero",
              w.id + " has a height of " + f2(h) + " ft. Set a real wall height.");
        }
      });

      /* ---- walls that cross without a node ---- */
      for (i = 0; i < walls.length; i++) {
        for (j = i + 1; j < walls.length; j++) {
          if (wallLength(walls[i]) < 1e-6 || wallLength(walls[j]) < 1e-6) continue;
          var hit = segCross(walls[i], walls[j]);
          if (hit) {
            add(lid, walls[i].id + "+" + walls[j].id, "error", "walls-cross-no-node",
                walls[i].id + " and " + walls[j].id + " cross at (" + f2(hit.x) + ", " + f2(hit.y) +
                ") with no node there. A span measured across that point would be wrong. Split both " +
                "walls at the intersection so the node exists.");
          }
        }
      }

      /* ---- openings ---- */
      openings.forEach(function (o) {
        var w = wallById(L, o.wallId);
        if (!w) {
          add(lid, o.id, "error", "opening-orphan",
              o.id + " names wall \"" + o.wallId + "\", which is not in this level. Re-attach it to a " +
              "wall or delete it.");
          return;
        }
        var fit = openingFits(w, o, openings);
        if (!fit.ok) add(lid, o.id, "error", fit.code, fit.text);

        if (num(o.headHeightFt) === null) {
          add(lid, o.id, "warn", "opening-no-head-height",
              o.id + " in " + w.id + " has no head height. Set it (6'-8\" = 6.67 ft is the usual " +
              "first-floor head) so the header depth budget can be checked.");
        } else if (num(w.heightFt) !== null && num(o.headHeightFt) >= num(w.heightFt)) {
          add(lid, o.id, "error", "opening-head-above-wall",
              o.id + " has a head height of " + f2(o.headHeightFt) + " ft in a " + f2(w.heightFt) +
              " ft wall — there is no room above it for a header. Lower the head or raise the wall.");
        }
        if (o.offsetBasis === "placeholder") {
          placeholders[w.id] = placeholders[w.id] || [];
          placeholders[w.id].push(o.id);
        }
      });

      /* ---- the grouped wall and opening findings ---- */
      if (noThick.length) {
        add(lid, noThick.length === 1 ? noThick[0] : "walls", "warn", "wall-no-thickness",
            (noThick.length === 1 ? noThick[0] + " has" : noThick.length + " walls have") +
            " no thickness (" + noThick.join(", ") + "). The takeoff measures a clear span between " +
            "wall FACES, so half of each wall comes out of the centreline dimension and it cannot " +
            "derive a span without one. Set 3.5 in for a 2x4 wall or 5.5 in for a 2x6.");
      }
      if (assumedThick.length) {
        add(lid, assumedThick.length === 1 ? assumedThick[0].split(" ")[0] : "walls", "warn",
            "wall-thickness-assumed",
            "Wall thickness on " + assumedThick.length + " wall" + (assumedThick.length === 1 ? "" : "s") +
            " was ASSUMED, not read from the plan: " + assumedThick.join(", ") + ". No plan or region " +
            "pack in this build declares a stud size, so a 2x4 (3.5 in) framed wall was taken as the " +
            "default — it is the common production wall in TX, FL and NC, and it is the conservative " +
            "reading, because a thinner wall leaves a LONGER clear span between faces. Confirm the " +
            "stud size against the architectural set and change it here if the walls are 2x6.");
      }
      Object.keys(placeholders).forEach(function (wid) {
        var ids = placeholders[wid];
        add(lid, wid, "warn", "opening-placeholder-offset",
            wid + " carries " + ids.length + " opening" + (ids.length === 1 ? "" : "s") +
            " at PLACEHOLDER offsets (" + ids.join(", ") + "). The source plan declares how many " +
            "openings this wall has and how wide they are, not where along it they sit — these are " +
            "spaced evenly so the wall can be read, and no dimension off them is real. Drag them to " +
            "the architectural elevation before the takeoff gate.");
      });

      /* ---- framing ---- */
      framing.forEach(function (f) {
        var poly = f.polygon;
        if (!isArr(poly) || poly.length < 3) {
          add(lid, f.id, "error", "framing-not-a-region",
              f.id + " has " + (isArr(poly) ? poly.length : 0) + " corners. A framing region needs at " +
              "least three. Redraw it.");
          return;
        }
        if (polyArea(poly) < 1e-6) {
          add(lid, f.id, "error", "framing-zero-area",
              f.id + " encloses no area — its corners are collinear. Redraw it.");
          return;
        }
        var bearsOn = isArr(f.bearsOn) ? f.bearsOn : [];
        var known = [], missing = [];
        bearsOn.forEach(function (id) {
          var w = wallById(L, id);
          if (w) known.push(w); else missing.push(id);
        });
        missing.forEach(function (id) {
          add(lid, f.id, "error", "framing-bears-on-missing-wall",
              f.id + " says it bears on \"" + id + "\", which is not a wall in this level. Pick the " +
              "walls again in the framing panel.");
        });
        if (known.length < 2) {
          add(lid, f.id, "error", "framing-bears-on-too-few",
              f.id + " (" + f.kind + ", " + Math.round(polyArea(poly)) + " sf) bears on " +
              (known.length === 0 ? "no wall" : "only " + known[0].id) +
              ". A framing region needs at least two bearing walls for a span to exist between them. " +
              "Tick the walls it lands on — and if it lands on a beam or a post, this model has no " +
              "element for that, so record it as an open item instead.");
        }
        known.forEach(function (w) {
          if (!touchesRegion(poly, w)) {
            add(lid, f.id, "error", "framing-not-touching-wall",
                f.id + " claims to bear on " + w.id + ", but " + w.id + " does not run along or under " +
                "the region — the nearest they come is more than " + f2(RULES.touchTolFt) +
                " ft. Move the region edge onto the wall, or untick " + w.id + ".");
          }
          if (!w.bearing) {
            add(lid, f.id, "error", "framing-on-nonbearing-wall",
                f.id + " bears on " + w.id + ", which is not marked as a bearing wall. Either mark " +
                w.id + " bearing or take it off this region.");
          }
        });
        if (num(f.spacingIn) === null) {
          add(lid, f.id, "warn", "framing-no-spacing",
              f.id + " has no member spacing. Set it (16 in or 24 in o.c.) — the takeoff cannot count " +
              "members without it.");
        } else if (num(f.spacingIn) <= 0) {
          add(lid, f.id, "error", "framing-spacing-zero",
              f.id + " has a spacing of " + f2(f.spacingIn) + " in. Set a real o.c. spacing.");
        }
        if (num(f.directionDeg) === null) {
          add(lid, f.id, "warn", "framing-no-direction",
              f.id + " has no span direction. Set which way the members run — 0° along +x, 90° along " +
              "+y — because the direction is what decides the span.");
        }
      });

      if (walls.length && !framing.length) {
        add(lid, "framing", "warn", "level-no-framing",
            "Level " + lid + " has " + walls.length + " walls and no framing region. Nothing says " +
            "which way anything spans, so the takeoff can derive no span from this level. Draw the " +
            "roof or floor region and tick the walls it bears on.");
      }
      if (walls.length && footprintAreaSf(L) === null) {
        add(lid, "footprint", "warn", "exterior-not-closed",
            "The exterior walls on level " + lid + " do not close a single loop, so this level has no " +
            "footprint area. Join the ends — snap each wall to its neighbour's endpoint — or mark the " +
            "walls that are not part of the envelope as interior.");
      }
    });

    if (!anyWall) {
      add(null, "model", "error", "no-walls",
          "This model has no walls. Draw the exterior walls first, or load a plan.");
    } else if (!anyBearing) {
      add(null, "model", "error", "no-bearing-walls",
          "No wall in this model is marked as bearing, so nothing carries the roof or the floor. " +
          "Mark the walls the framing lands on as bearing.");
    }

    if (model.underlay && !scaleOf(model.underlay)) {
      add(null, "underlay", "warn", "underlay-uncalibrated",
          "The underlay is not calibrated, so it is shown at a provisional size and no length traced " +
          "off it means anything. Click Calibrate, click two points a known distance apart, and type " +
          "that distance.");
    }

    (isArr(model.unresolved) ? model.unresolved : []).forEach(function (u, i) {
      add(null, "unresolved-" + (i + 1), "warn", "unresolved",
          u.what + " — " + u.why + " Need: " + u.need);
    });

    return rows;
  }

  function errorsIn(rows) {
    return rows.filter(function (r) { return r.severity === "error"; });
  }

  /* ============================================================
     fromPlan — a model from a weights.js plan

     Every wall, opening and region below comes from a number the
     plan states. Where it states none, this function does not
     choose one: the hole goes into `unresolved` with what would
     have to be declared to close it.

     Two drawing CONVENTIONS are used, and they are conventions
     rather than values because they locate nothing and measure
     nothing:
       · footprintFt is [x, y] — the first number runs along +x.
       · the front of the house is the wall at y = 0.
     Both are recorded on the level so a reader can mirror the
     drawing without wondering what was assumed.
     ============================================================ */

  /* Only the LABEL is read for a wall hint. The notes discuss walls
     the mark is not in ("would follow from neither the 46 ft clear
     span nor the gable end") and reading them puts windows in the
     wrong wall. */
  var WALL_HINTS = [
    { re: /gable[\s-]*end/i, where: "gable" },
    { re: /\brear\b|\bback\b/i, where: "rear" },
    { re: /\bfront\b|\bentry\b|\bgarage\b/i, where: "front" }
  ];
  function wallHint(mark) {
    var label = String(mark.label || "");
    var out = null;
    WALL_HINTS.forEach(function (h) { if (!out && h.re.test(label)) out = h.where; });
    return out;
  }
  function openingKind(mark) {
    var label = String(mark.label || "");
    if (/garage|carport/i.test(label)) return "garage";
    if (/slider|sliding/i.test(label)) return "slider";
    if (/\bdoor\b|entry/i.test(label)) return "door";
    return "window";
  }

  /* the one plate height every region pack in weights.js declares */
  function plateFtFromPacks() {
    var W = FM.weights;
    if (!W || !isArr(W.PACKS)) return null;
    var seen = [];
    W.PACKS.forEach(function (p) {
      var v = num(p.plateHeightIn);
      if (v !== null && seen.indexOf(v) === -1) seen.push(v);
    });
    if (seen.length !== 1) return null;
    return { ft: seen[0] / 12, inches: seen[0] };
  }

  /* Truss spacing: declared if the plan declares it, otherwise read back out
     of the truss mark's own count — but ONLY because these plans state that
     relationship in as many words ("Count is the 46 ft ridge run at 24 in
     o.c. plus one"). A count that is declared as a CONSEQUENCE of a spacing
     can be inverted to recover it; a count the plan says follows whatever the
     solver picks cannot, and the floor bays below are left undeclared for
     exactly that reason. */
  function trussSpacing(plan, g, runFt) {
    var declared = num(g.trussSpacingIn);
    var truss = null;
    (plan.marks || []).forEach(function (mk) {
      if (!truss && mk.role === "rafter" && mk.component && num(mk.count) > 1) truss = mk;
    });
    /* The inversion checks itself: a count that really is "the run at some
       spacing plus one" reads back as one of the spacings anybody frames at.
       A count that means something else does not, and then nothing is
       derived. 19.2 in is the 5-per-8-ft layout. */
    var STD = [12, 16, 19.2, 24];
    var derived = null, rawDerived = null;
    if (truss && runFt > 0) {
      var run = num(truss.runFt) !== null ? num(truss.runFt) : runFt;
      rawDerived = Math.round((run / (num(truss.count) - 1)) * 12 * 100) / 100;
      STD.forEach(function (s) { if (derived === null && near(rawDerived, s, 0.05)) derived = s; });
    }
    if (declared !== null) {
      var agree = derived === null || near(declared, derived, 0.01);
      return { inches: declared,
               basis: "Spacing " + declared + " in from geometry.trussSpacingIn" +
                      (derived === null ? "." : agree
                        ? "; the truss mark's count reads back the same " + derived + " in."
                        : "; NOTE the truss mark's count reads back " + derived +
                          " in instead — reconcile the two before the takeoff gate.") };
    }
    if (derived !== null) {
      return { inches: derived,
               basis: "Spacing " + derived + " in DERIVED from " + truss.id + ": its count of " +
                      truss.count + " is declared as the " +
                      (num(truss.runFt) !== null ? truss.runFt : runFt) +
                      " ft run at that spacing plus one, so the spacing follows from the count." };
    }
    return { inches: null,
             basis: "Spacing is not declared and no count reads it back." };
  }

  /* equal gaps, openings in the order given — the only layout that
     does not favour one end of a wall over the other */
  function layoutEqualGaps(wallLenFt, widths) {
    var total = 0, i;
    for (i = 0; i < widths.length; i++) total += widths[i];
    var gap = (wallLenFt - total) / (widths.length + 1);
    if (gap < 2 * endClearFt()) return null;
    var out = [], at = gap;
    for (i = 0; i < widths.length; i++) { out.push(at); at += widths[i] + gap; }
    return out;
  }

  /* No plan and no region pack in this build declares a stud size, and the
     takeoff measures a clear span between wall FACES — so a wall with no
     thickness stops the whole pipeline. A stated assumption a reviewer can
     see and change is the right answer; a null is not, and neither is a
     silent one. 2x4 because it is the production wall in these three states,
     and because it is the conservative reading: a THINNER wall leaves a
     LONGER clear span between faces, so nothing downstream is under-sized by
     it. validate() reports every wall carrying this value as assumed. */
  var ASSUMED_STUD_IN = 3.5;

  function fromPlan(planId, variantId) {
    var W = FM.weights;
    if (!W || typeof W.planById !== "function") return null;
    var plan = W.planById(planId);
    if (!plan) return null;

    var basePlan = plan, variantNote = "";
    if (variantId) {
      if (typeof W.planForVariant !== "function") {
        variantNote = "This build's weights.js has no planForVariant(), so variant \"" + variantId +
                      "\" was not applied.";
      } else {
        try { plan = W.planForVariant(basePlan, variantId); }
        catch (e) { plan = basePlan; variantNote = e.message; }
      }
    }

    var m = blank(plan.name);
    m.source = { kind: "plan", planId: basePlan.id, variantId: variantId || null,
                 builtBy: "FM.cad.fromPlan" };
    var un = m.unresolved;
    function hole(what, why, need) { un.push({ what: what, why: why, need: need }); }

    if (variantNote) {
      hole("Variant \"" + variantId + "\"",
           "It was not applied, so this geometry is the base plan: " + variantNote,
           "Name a variant this build has, or read this model as the stamped base case.");
    }
    if (plan.variant && plan.variant.geometry) {
      hole("Geometry added by variant \"" + (plan.variant.id || variantId) + "\"",
           "This variant declares its own geometry block, and this model draws the base footprint " +
           "only — a porch or a stoop the variant adds is not on the canvas.",
           "Declare where the added geometry sits relative to a named corner, then draw it.");
    }

    var g = plan.geometry || {};
    var fp = isArr(g.footprintFt) ? g.footprintFt : null;
    var L = m.levels[0];

    var plate = plateFtFromPacks();
    if (plate) {
      L.topPlateFt = plate.ft;
      L.note = "Top plate " + plate.inches + " in — every region pack in weights.js declares the same " +
               "precut plate height, so it is the one value the plan does not have to state. " +
               "Provenance [market], not code.";
    } else {
      hole("First-floor plate height",
           "The region packs in weights.js do not agree on plateHeightIn, so no single wall height " +
           "follows from them, and " + plan.name + " states none of its own.",
           "Declare the plate height for this plan, or size the model against one region pack.");
    }

    if (!fp || num(fp[0]) === null || num(fp[1]) === null) {
      hole("The footprint",
           plan.name + " declares no geometry.footprintFt, so there is no outline to draw.",
           "Declare footprintFt: [width, depth] in feet on the plan.");
      return m;
    }

    var Wd = num(fp[0]), D = num(fp[1]);

    /* ---- the exterior envelope ---- */
    var thickNote = "Thickness " + ASSUMED_STUD_IN + " in is ASSUMED — a 2x4 framed wall. " +
                    plan.name + " declares no stud size and neither does any region pack.";
    var basis = "Exterior envelope from " + plan.name + " geometry.footprintFt = [" + Wd + ", " + D +
                "] ft. Front is the wall at y = 0 (drawing convention). " + thickNote;
    /* pushed one at a time — nextId reads the list, so building all four
       first hands out the same id twice */
    function envelope(x1, y1, x2, y2, label) {
      var w = newWall(L, x1, y1, x2, y2, {
        note: label + " · " + thickNote, basis: basis, bearing: false,
        thicknessIn: ASSUMED_STUD_IN, thicknessBasis: "assumed"
      });
      L.walls.push(w);
      return w;
    }
    var front = envelope(0, 0, Wd, 0, "Front wall");
    var right = envelope(Wd, 0, Wd, D, "Right wall");
    var rear = envelope(0, D, Wd, D, "Rear wall");
    var left = envelope(0, 0, 0, D, "Left wall");

    /* ---- which walls bear, and which way the roof spans ---- */
    var span = num(g.trussSpanFt);
    var bearWalls = null, roofDirDeg = null, gableWalls = null;
    var bl = String(g.bearingLines || "");

    if (span !== null && near(span, D, 0.01) && !near(span, Wd, 0.01)) {
      bearWalls = [front, rear]; gableWalls = [left, right]; roofDirDeg = 90;
    } else if (span !== null && near(span, Wd, 0.01) && !near(span, D, 0.01)) {
      bearWalls = [left, right]; gableWalls = [front, rear]; roofDirDeg = 0;
    } else if (span !== null) {
      hole("Which walls carry the roof",
           "geometry.trussSpanFt is " + span + " ft, which matches " +
           (near(span, D, 0.01) ? "both footprint dimensions" : "neither footprint dimension (" +
            Wd + " ft and " + D + " ft)") + ", so the truss direction does not follow from it.",
           "State the truss bearing walls, or correct trussSpanFt to one footprint dimension.");
    } else if (/exterior walls/i.test(bl)) {
      /* the plan says so in as many words */
      bearWalls = [front, right, rear, left];
      hole("The roof span direction",
           plan.name + " declares no trussSpanFt, so nothing says which way the roof or ceiling spans " +
           "even though its bearingLines names the exterior walls as bearing.",
           "Declare trussSpanFt, or draw the roof region and set its direction by hand.");
    } else {
      hole("Which walls bear",
           plan.name + " declares no trussSpanFt and its bearingLines text does not name the exterior " +
           "walls, so no wall can be marked bearing from what the plan states.",
           "Declare trussSpanFt, or mark the bearing walls by hand.");
    }
    if (bearWalls) {
      bearWalls.forEach(function (w) {
        w.bearing = true;
        w.basis = basis + " Bearing: " + (span !== null
          ? "geometry.trussSpanFt = " + span + " ft spans this pair."
          : "geometry.bearingLines names the exterior walls.");
      });
    }
    if (gableWalls) {
      gableWalls.forEach(function (w) {
        w.note = w.note + " · gable end, non-bearing";
        w.basis = basis + " Non-bearing: the " + span + " ft truss span runs onto the other pair.";
      });
    }
    if (bl) {
      L.note = (L.note ? L.note + " " : "") + "Plan bearingLines: " + bl;
    }
    if (/party wall/i.test(bl)) {
      hole("Which wall is the party wall",
           plan.name + " is an attached unit and its bearingLines names a party wall, but nothing says " +
           "which side of the footprint is shared.",
           "Name the shared wall on the plan. Until then the drawing may be mirrored, and no opening " +
           "has been placed in a wall that could be the party wall.");
    }

    /* ---- an interior bearing line, only when the joist bays derive one ----
       Two declared joist spans that add exactly to a footprint dimension
       locate the line between them. Anything else does not. */
    var joistSpans = [];
    (plan.marks || []).forEach(function (mk) {
      if (mk.role !== "joist") return;
      var s = num(mk.span);
      if (s === null) return;
      var seen = false;
      joistSpans.forEach(function (v) { if (near(v, s, 0.001)) seen = true; });
      if (!seen) joistSpans.push(s);
    });
    var interior = null, floorDirDeg = null;
    if (joistSpans.length === 2) {
      var sum = joistSpans[0] + joistSpans[1];
      var acrossX = near(sum, Wd, 0.01), acrossY = near(sum, D, 0.01);
      if (acrossX && !acrossY) {
        interior = newWall(L, joistSpans[0], 0, joistSpans[0], D, {
          exterior: false, bearing: true,
          note: "Interior bearing line · " + thickNote,
          thicknessIn: ASSUMED_STUD_IN, thicknessBasis: "assumed",
          basis: "Derived: the two declared joist bays (" + joistSpans[0] + " ft and " + joistSpans[1] +
                 " ft) add to the " + Wd + " ft footprint width, so the line sits " + joistSpans[0] +
                 " ft from one side. " + thickNote
        });
        floorDirDeg = 0;
      } else if (acrossY && !acrossX) {
        interior = newWall(L, 0, joistSpans[0], Wd, joistSpans[0], {
          exterior: false, bearing: true,
          note: "Interior bearing line · " + thickNote,
          thicknessIn: ASSUMED_STUD_IN, thicknessBasis: "assumed",
          basis: "Derived: the two declared joist bays (" + joistSpans[0] + " ft and " + joistSpans[1] +
                 " ft) add to the " + D + " ft footprint depth. " + thickNote
        });
        floorDirDeg = 90;
      }
      if (interior) {
        L.walls.push(interior);
        hole("Which side the interior bearing line is measured from",
             "The two joist bays locate the line " + joistSpans[0] + " ft from one edge, but the plan " +
             "does not say which edge.",
             "Name the side on the plan, or mirror the drawing to match the architectural set.");
      }
    }
    /* "There is no third bearing line" declares the absence of one. Reading
       that as a hole would invent a finding out of a plan being explicit. */
    var declaresInterior = /interior line|centre bearing|center bearing|third bearing/i.test(bl) &&
                           !/\bno (third bearing|interior|other bearing)/i.test(bl);
    if (!interior && declaresInterior) {
      hole("The interior bearing line",
           plan.name + " declares an interior bearing line in its bearingLines text, but no pair of " +
           "declared joist spans adds to a footprint dimension, so its position does not follow from " +
           "any stated number" +
           (joistSpans.length ? " (the declared joist spans are " + joistSpans.join(" ft, ") + " ft)" : "") + ".",
           "Declare the offset of the interior bearing line from a named exterior wall.");
    }

    /* ---- framing regions ---- */
    var fpPoly = [[0, 0], [Wd, 0], [Wd, D], [0, D]];
    if (bearWalls && roofDirDeg !== null) {
      var runFt = roofDirDeg === 90 ? Wd : D;      /* the ridge run, across the span */
      var sp = trussSpacing(plan, g, runFt);
      L.framing.push(newFraming(L, fpPoly, {
        kind: "roof", directionDeg: roofDirDeg, spacingIn: sp.inches,
        bearsOn: bearWalls.map(function (w) { return w.id; }),
        note: "Common trusses, " + span + " ft clear span",
        basis: "Region is the footprint. Direction from geometry.trussSpanFt = " + span + " ft. " + sp.basis
      }));
      if (sp.inches === null) {
        hole("Roof member spacing",
             plan.name + " declares no geometry.trussSpacingIn, and its truss mark declares no count " +
             "the spacing could be read back out of.",
             "Declare the truss spacing, or set it on the roof region by hand.");
      }
    }
    if (interior && floorDirDeg !== null && num(g.storeys) > 1) {
      var a = joistSpans[0];
      var poly1, poly2;
      if (floorDirDeg === 0) {
        poly1 = [[0, 0], [a, 0], [a, D], [0, D]];
        poly2 = [[a, 0], [Wd, 0], [Wd, D], [a, D]];
      } else {
        poly1 = [[0, 0], [Wd, 0], [Wd, a], [0, a]];
        poly2 = [[0, a], [Wd, a], [Wd, D], [0, D]];
      }
      var side1 = floorDirDeg === 0 ? left : front;
      var side2 = floorDirDeg === 0 ? right : rear;
      /* the floor bays land on the two envelope walls parallel to the
         interior line, which are bearing for the floor whatever carries
         the roof */
      [side1, side2].forEach(function (w) { w.bearing = true; });
      L.framing.push(newFraming(L, poly1, {
        kind: "floor", directionDeg: floorDirDeg, spacingIn: null,
        bearsOn: [side1.id, interior.id],
        note: "Floor bay · " + joistSpans[0] + " ft",
        basis: "Bay from the declared joist span " + joistSpans[0] + " ft. Spacing is not declared — " +
               "the plan says the piece count follows the spacing the solver picks."
      }));
      L.framing.push(newFraming(L, poly2, {
        kind: "floor", directionDeg: floorDirDeg, spacingIn: null,
        bearsOn: [interior.id, side2.id],
        note: "Floor bay · " + joistSpans[1] + " ft",
        basis: "Bay from the declared joist span " + joistSpans[1] + " ft. Spacing is not declared."
      }));
      hole("Floor member spacing",
           plan.name + " declares no spacing for the second-floor joists — the marks say the piece " +
           "count follows the spacing the solver picks.",
           "Set the spacing on each floor region once the solver has picked one.");
    }

    /* ---- storeys this model does not carry ---- */
    if (num(g.storeys) > 1) {
      hole("The upper storey",
           plan.name + " is " + g.storeys + " storeys and this model carries the first-floor level " +
           "only. footprintFt describes the first floor" +
           (num(g.secondFloorSf) !== null ? " (" + g.secondFloorSf + " sf above " +
            (num(g.firstFloorSf) !== null ? g.firstFloorSf + " sf" : "it") + "), and the upper " +
            "outline is not declared" : "") + ".",
           "Declare the upper-floor outline, then draw it as a second level.");
    }

    /* ---- porches, lanais, patios: declared depth, undeclared position ---- */
    var appendages = [
      { key: "lanaiDepthFt", label: "lanai" },
      { key: "coveredEntryFt", label: "covered entry" },
      { key: "coveredPatioFt", label: "covered patio" },
      { key: "porchFt", label: "porch" },
      { key: "deckFt", label: "deck" }
    ];
    appendages.forEach(function (ap) {
      var v = own(g, ap.key);
      if (v === undefined || v === null) return;
      var sizeText = isArr(v) ? v[0] + " ft x " + v[1] + " ft" : v + " ft deep";
      hole("The " + ap.label + " (" + sizeText + ")",
           plan.name + " declares the size of the " + ap.label + " but not where along the face it " +
           "sits, and it is carried by a beam on posts — which this model has no element for, since " +
           "framing here bears on walls only.",
           "Declare the offset of the " + ap.label + " from a named corner. Its beam and posts stay " +
           "out of this model either way; they are marks on the schedule.");
    });
    if (g.garage && num(g.garage.widthFt) !== null) {
      hole("The garage walls (" + g.garage.widthFt + " ft x " + g.garage.depthFt + " ft)",
           plan.name + " declares the garage size but not its position along the footprint, so its " +
           "interior walls cannot be drawn.",
           "Declare the garage offset from a named corner.");
    }

    /* ---- openings from the header marks ---- */
    placeOpenings(plan, L, {
      front: front, rear: rear, left: left, right: right,
      bearWalls: bearWalls, gableWalls: gableWalls,
      partyWall: /party wall/i.test(bl)
    }, hole);

    return m;
  }

  /* Openings are the only thing here that gets a PLACEHOLDER position.
     A plan that declares eight windows in its bearing walls has declared
     eight windows; refusing to draw them would lose a fact the plan
     states. Refusing to state WHERE they go is the honest half, and
     that is what offsetBasis: "placeholder" and the warn are for. */
  function placeOpenings(plan, L, W, hole) {
    var pending = {};   /* wall id -> [{mark, widthFt, kind, headFt}] */
    var groups = {};

    /* Two marks can describe ONE hole — the Sunbelt garage door is carried
       twice, once read as a gable end and once as a bearing line. The plan
       says so in as many words ("Same opening as HDR-GAR-B"), so that
       declaration is what groups them. Two marks that merely share a width
       are two openings. */
    var headers = (plan.marks || []).filter(function (mk) { return mk.role === "header"; });
    var ids = {};
    headers.forEach(function (mk) { ids[mk.id] = 1; });
    headers.forEach(function (mk) {
      var alias = /same opening as\s+([A-Za-z0-9_-]+)/i.exec(String(mk.note || ""));
      var k = mk.id;
      if (alias && own(ids, alias[1])) k = alias[1];
      groups[k] = groups[k] || [];
      groups[k].push(mk);
    });

    Object.keys(groups).forEach(function (k) {
      var marks = groups[k];
      var mk = marks[0];

      /* two marks for the same opening — the plan is carrying two
         readings of one hole, and they do not agree on the wall */
      if (marks.length > 1) {
        var hints = [], ids = [];
        marks.forEach(function (x) { ids.push(x.id); var h = wallHint(x) || "unhinted"; if (hints.indexOf(h) === -1) hints.push(h); });
        if (hints.length > 1) {
          hole("The " + f1(num(mk.span)) + " ft opening behind " + ids.join(" and "),
               plan.name + " carries " + ids.length + " header marks for one opening — " +
               ids.join(" and ") + " — and they put it in different walls (" + hints.join(", ") +
               "). The truss direction there decides which reading applies and the plan does not " +
               "state it.",
               "State the truss direction at that opening, then draw it in the wall that follows.");
          return;
        }
      }

      var count = 0;
      marks.forEach(function (x) { count = Math.max(count, num(x.count) || 1); });

      if (mk.wallPosition !== "exterior-first-floor") {
        hole("Opening for " + mk.id + " (" + mk.label + ")",
             "This header is not declared as a first-floor exterior opening (wallPosition is " +
             (mk.wallPosition ? "\"" + mk.wallPosition + "\"" : "absent") + "), so there is no wall on " +
             "this level to put it in — it is a floor-framing or upper-storey header.",
             "Draw the level it belongs to, or declare wallPosition on the mark.");
        return;
      }

      var hint = wallHint(mk);
      var targets = null;
      if (hint === "front") targets = [W.front];
      else if (hint === "rear") targets = [W.rear];
      else if (hint === "gable") targets = W.gableWalls;
      else targets = W.bearWalls;

      if (!targets || !targets.length) {
        hole("Opening for " + mk.id + " (" + mk.label + ")",
             "The wall this opening belongs to is not determined — " +
             (hint === "gable" ? "the gable ends are not identified, because the truss direction is not."
                               : "the mark names no face and the bearing walls are not determined."),
             "Declare the truss direction, or name the wall on the mark.");
        return;
      }
      if (!hint && W.partyWall) {
        hole("Opening for " + mk.id + " (" + mk.label + ")",
             "The mark names no face, and on this plan one of the walls it would land in is a party " +
             "wall — an opening put there would be an invention, not a placement.",
             "Name the face on the mark, or name which wall is the party wall.");
        return;
      }

      /* rough opening = the header span less its bearing at each end */
      var spanFt = num(mk.span);
      var bearingIn = num(mk.bearing);
      var roFt = bearingIn === null ? spanFt : spanFt - 2 * bearingIn / 12;
      var headFt = num(mk.headHeightIn) === null ? null : num(mk.headHeightIn) / 12;
      var basisText = "From mark " + mk.id + ": rough opening = span " + f2(spanFt) + " ft less " +
                      (bearingIn === null ? "no declared bearing" : f1(bearingIn) + " in of bearing at each end") +
                      ". Offset along the wall is a PLACEHOLDER — " + plan.name +
                      " does not say where along the face it sits.";
      var i;
      for (i = 0; i < count; i++) {
        var w = targets[i % targets.length];
        pending[w.id] = pending[w.id] || [];
        pending[w.id].push({
          widthFt: Math.round(roFt * 1000) / 1000,
          kind: openingKind(mk),
          headFt: headFt === null ? null : Math.round(headFt * 1000) / 1000,
          note: basisText, markId: mk.id
        });
      }
      if (mk.underdetermined) {
        hole("The header over " + mk.id + "'s opening",
             "The opening is drawn, but " + plan.name + " declares this mark underdetermined: " +
             String(mk.underdeterminedNote || "").split(".")[0] + ".",
             "Close the mark's own finding in weights.js; the geometry here is not what is missing.");
      }
    });

    Object.keys(pending).forEach(function (wid) {
      var w = wallById(L, wid);
      var list = pending[wid];
      var widths = list.map(function (p) { return p.widthFt; });
      var offs = layoutEqualGaps(wallLength(w), widths);
      if (!offs) {
        var total = 0;
        widths.forEach(function (x) { total += x; });
        hole(list.length + " openings assigned to " + w.id,
             "They total " + f1(total) + " ft of rough opening in a " + f1(wallLength(w)) +
             " ft wall, which leaves no room for jack and king studs between them, so none of them " +
             "was placed.",
             "Check the mark counts on " + plan.name + ", or state which face each opening is in.");
        return;
      }
      list.forEach(function (p, i) {
        L.openings.push(newOpening(L, w.id, Math.round(offs[i] * 1000) / 1000, p.widthFt, {
          headHeightFt: p.headFt, kind: p.kind, note: p.note, offsetBasis: "placeholder"
        }));
      });
    });
  }

  /* ---------------- local storage ---------------- */

  function storeRead() {
    try {
      var raw = window.localStorage.getItem(STORE_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch (e) { return {}; }
  }
  function listLocal() {
    var all = storeRead(), out = [];
    Object.keys(all).forEach(function (k) {
      out.push({ key: k, name: (all[k] && all[k].name) || k, at: (all[k] && all[k].savedAt) || "" });
    });
    out.sort(function (a, b) { return a.name < b.name ? -1 : 1; });
    return out;
  }
  function saveLocal(key, model) {
    var all = storeRead();
    var rec = JSON.parse(toJSON(model));
    rec.savedAt = new Date().toISOString();
    all[key] = rec;
    try {
      window.localStorage.setItem(STORE_KEY, JSON.stringify(all));
      return { ok: true };
    } catch (e) {
      return { ok: false, why: "This browser refused to store the model (" + e.name +
                              "). Copy the JSON out of the export box instead — it is the same bytes." };
    }
  }
  function loadLocal(key) {
    var all = storeRead();
    if (!own(all, key)) return null;
    return normalise(all[key]);
  }
  function removeLocal(key) {
    var all = storeRead();
    if (!own(all, key)) return false;
    delete all[key];
    try { window.localStorage.setItem(STORE_KEY, JSON.stringify(all)); return true; }
    catch (e) { return false; }
  }

  /* ---------------- the surface ---------------- */

  FM.cad = {
    MODEL_VERSION: MODEL_VERSION,
    RULES: RULES,
    ASSUMED_STUD_IN: ASSUMED_STUD_IN,
    OPENING_KINDS: OPENING_KINDS,
    FRAMING_KINDS: FRAMING_KINDS,
    STORE_KEY: STORE_KEY,

    blank: blank,
    validate: validate,
    errorsIn: errorsIn,
    stats: stats,
    scaleOf: scaleOf,
    toJSON: toJSON,
    fromJSON: fromJSON,
    fromPlan: fromPlan,

    /* geometry the view and the tests both need */
    levelOf: levelOf,
    wallById: wallById,
    wallLength: wallLength,
    wallAngleDeg: wallAngleDeg,
    pointAlong: pointAlong,
    projectOnWall: projectOnWall,
    segCross: segCross,
    polyArea: polyArea,
    pointInPoly: pointInPoly,
    touchesRegion: touchesRegion,
    footprintAreaSf: footprintAreaSf,
    openingFits: openingFits,
    endClearFt: endClearFt,
    newWall: newWall,
    newOpening: newOpening,
    newFraming: newFraming,
    ftIn: ftIn,

    listLocal: listLocal,
    saveLocal: saveLocal,
    loadLocal: loadLocal,
    removeLocal: removeLocal
  };

  /* ============================================================
     THE VIEW

     Everything below needs a DOM. It is registered only when core.js
     has been loaded, so the node harness can require this file and
     exercise the model layer above without a browser.
     ============================================================ */

  if (!FM.VIEWS) return;

  var el = FM.el, esc = FM.esc, card = FM.card, dl = FM.dl, toast = FM.toast;
  var NS = "http://www.w3.org/2000/svg";

  function sv(tag, attrs, kids) {
    var n = document.createElementNS(NS, tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === "text") n.textContent = attrs[k];
      else if (k.slice(0, 2) === "on") n.addEventListener(k.slice(2), attrs[k]);
      else if (attrs[k] !== null && attrs[k] !== undefined) n.setAttribute(k, String(attrs[k]));
    });
    (kids || []).forEach(function (c) { if (c) n.appendChild(c); });
    return n;
  }
  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

  /* ---------------- view state ----------------
     Module-level, because core's go() rebuilds the view host on every
     navigation and a drawing that survives only until you glance at
     the dashboard is not a drawing tool. */

  var TOOLS = [
    { id: "select",  key: "V", label: "Select",  hint: "click a wall, opening or region; drag to move; drag an endpoint to stretch" },
    { id: "wall",    key: "W", label: "Wall",    hint: "drag to draw, or click-click to chain; Shift or a near-axis angle locks orthogonal" },
    { id: "opening", key: "O", label: "Opening", hint: "click a wall where the opening goes" },
    { id: "rect",    key: "R", label: "Region",  hint: "drag a rectangular framing region" },
    { id: "poly",    key: "P", label: "Polygon", hint: "click each corner, Enter or click the first corner to close" },
    { id: "calib",   key: "C", label: "Calibrate", hint: "click two points on the underlay, then type the real distance" },
    { id: "pan",     key: "H", label: "Pan",     hint: "drag to pan — the wheel zooms in every tool" }
  ];

  var S = {
    src: { kind: "plan", id: "starter-1210" },
    tool: "select",
    sel: null,                       /* {kind, id} */
    snapFt: 0.5, snapOn: true,
    view: { k: 12, x: -6, y: -6 },
    draft: null,                     /* in-progress wall / region / calibration */
    hover: null,
    cursor: null,
    saveKey: "",
    defaults: { thicknessIn: ASSUMED_STUD_IN, openWidthFt: 4, headHeightFt: 6.67, kind: "window", framingKind: "roof" }
  };
  var MODEL = null;
  var UNDO = [], REDO = [];
  var IMG = null;                    /* decoded underlay, for its pixel size */

  function level() { return levelOf(MODEL, null); }

  function pushUndo() {
    if (!MODEL) return;
    UNDO.push(toJSON(MODEL));
    if (UNDO.length > RULES.undoDepth) UNDO.shift();
    REDO.length = 0;
  }
  function undo() {
    if (!UNDO.length) { toast("Nothing to undo."); return; }
    REDO.push(toJSON(MODEL));
    MODEL = normalise(JSON.parse(UNDO.pop()));
    S.sel = null;
    redraw();
  }
  function redo() {
    if (!REDO.length) { toast("Nothing to redo."); return; }
    UNDO.push(toJSON(MODEL));
    MODEL = normalise(JSON.parse(REDO.pop()));
    S.sel = null;
    redraw();
  }

  /* ---------------- the address bar ----------------
     #/cad/<kind>/<id>   kind is "plan", "saved" or "new". */

  if (typeof FM.registerSubRoute === "function") {
    FM.registerSubRoute("cad", {
      read: function () { return [S.src.kind, S.src.id]; },
      write: function (args) {
        args = args || [];
        var lost = [];
        var kind = args[0], id = args[1];
        if (kind === "new") { S.src = { kind: "new", id: "blank" }; return; }
        if (kind === "plan") {
          if (FM.weights && FM.weights.planById(id)) S.src = { kind: "plan", id: id };
          else lost.push("plan “" + id + "”");
        } else if (kind === "saved") {
          if (loadLocal(id)) S.src = { kind: "saved", id: id };
          else lost.push("saved model “" + id + "”");
        } else if (kind) {
          lost.push("source “" + kind + "”");
        }
        if (lost.length && FM.toast) {
          FM.toast("This link names " + lost.join(" and ") + ", which this browser does not have. " +
                   "Showing " + (S.src.kind === "plan" ? "the " +
                   ((FM.weights.planById(S.src.id) || {}).name || S.src.id) + " geometry" : S.src.id) +
                   " instead — check the link before drawing on it.");
          if (FM.syncHash) setTimeout(function () { FM.syncHash(true); }, 0);
        }
      }
    });
  }

  /* ---------------- screen <-> world ---------------- */

  var SVG = null, VW = 900, VH = 560;

  function sx(wx) { return (wx - S.view.x) * S.view.k; }
  function sy(wy) { return VH - (wy - S.view.y) * S.view.k; }
  function wx(px) { return S.view.x + px / S.view.k; }
  function wy(py) { return S.view.y + (VH - py) / S.view.k; }

  function eventPoint(e) {
    var r = SVG.getBoundingClientRect();
    var px = e.clientX - r.left, py = e.clientY - r.top;
    return { px: px, py: py, x: wx(px), y: wy(py) };
  }

  function contentBox() {
    var L = level(), b = null;
    function add(x, y) {
      if (!b) b = { x1: x, y1: y, x2: x, y2: y };
      else { b.x1 = Math.min(b.x1, x); b.y1 = Math.min(b.y1, y); b.x2 = Math.max(b.x2, x); b.y2 = Math.max(b.y2, y); }
    }
    if (L) {
      (L.walls || []).forEach(function (w) { add(w.x1, w.y1); add(w.x2, w.y2); });
      (L.framing || []).forEach(function (f) { (f.polygon || []).forEach(function (p) { add(p[0], p[1]); }); });
    }
    var u = underlayBox();
    if (u) { add(u.x1, u.y1); add(u.x2, u.y2); }
    return b;
  }

  function fit() {
    var b = contentBox();
    if (!b) { S.view = { k: 12, x: -6, y: -6 }; return; }
    var w = Math.max(b.x2 - b.x1, 4), h = Math.max(b.y2 - b.y1, 4);
    var k = Math.min((VW - 90) / w, (VH - 70) / h);
    S.view.k = Math.max(1, Math.min(160, k));
    S.view.x = b.x1 - (VW / S.view.k - w) / 2;
    S.view.y = b.y1 - (VH / S.view.k - h) / 2;
  }

  function zoomAt(px, py, factor) {
    var ax = wx(px), ay = wy(py);
    S.view.k = Math.max(1, Math.min(200, S.view.k * factor));
    S.view.x = ax - px / S.view.k;
    S.view.y = ay - (VH - py) / S.view.k;
  }

  /* ---------------- snapping ----------------

     Endpoints first: a wall that lands 2 in from its neighbour looks
     joined, does not close the footprint, and produces a span that is
     wrong by exactly that much. Then the grid. Orthogonal lock is held
     with Shift or taken automatically inside RULES.orthoDeg, which is
     the only way freehand drawing produces a wall that is actually
     square. */

  function snap(pt, fromPt, shift) {
    var out = { x: pt.x, y: pt.y, on: "free" };
    var L = level();
    var best = null, bestD = RULES.snapPx / S.view.k;
    if (S.snapOn && L) {
      (L.walls || []).forEach(function (w) {
        [[w.x1, w.y1], [w.x2, w.y2]].forEach(function (p) {
          var d = dist(pt.x, pt.y, p[0], p[1]);
          if (d < bestD) { bestD = d; best = { x: p[0], y: p[1], on: "endpoint " + w.id }; }
        });
      });
    }
    if (best) return best;

    if (fromPt) {
      var dx = pt.x - fromPt.x, dy = pt.y - fromPt.y;
      var len = Math.sqrt(dx * dx + dy * dy);
      if (len > 1e-6) {
        var ang = Math.abs(Math.atan2(dy, dx) * 180 / Math.PI);
        var offAxis = Math.min(Math.abs(ang - 0), Math.abs(ang - 90), Math.abs(ang - 180));
        if (shift || offAxis <= RULES.orthoDeg) {
          if (Math.abs(dx) >= Math.abs(dy)) { out.y = fromPt.y; out.on = "ortho"; }
          else { out.x = fromPt.x; out.on = "ortho"; }
        }
      }
    }
    if (S.snapOn) {
      var g = S.snapFt;
      if (out.on !== "ortho" || out.y !== (fromPt && fromPt.y)) out.y = Math.round(out.y / g) * g;
      if (out.on !== "ortho" || out.x !== (fromPt && fromPt.x)) out.x = Math.round(out.x / g) * g;
      if (out.on === "free") out.on = "grid";
    }
    return out;
  }

  function hitTest(pt) {
    var L = level();
    if (!L) return null;
    var tolFt = 9 / S.view.k, i, j;
    /* openings first — they sit on top of their wall */
    for (i = 0; i < L.openings.length; i++) {
      var o = L.openings[i], w = wallById(L, o.wallId);
      if (!w) continue;
      var p = projectOnWall(w, pt.x, pt.y);
      if (p.d <= tolFt && p.t >= o.offsetFt && p.t <= o.offsetFt + o.widthFt) {
        return { kind: "opening", id: o.id };
      }
    }
    for (i = 0; i < L.walls.length; i++) {
      var q = projectOnWall(L.walls[i], pt.x, pt.y);
      if (q.d <= tolFt && q.u >= -0.001 && q.u <= 1.001) return { kind: "wall", id: L.walls[i].id };
    }
    for (j = L.framing.length - 1; j >= 0; j--) {
      if (pointInPoly(L.framing[j].polygon, pt.x, pt.y)) return { kind: "framing", id: L.framing[j].id };
    }
    return null;
  }

  function selected() {
    if (!S.sel) return null;
    var L = level();
    if (!L) return null;
    var pool = S.sel.kind === "wall" ? L.walls : (S.sel.kind === "opening" ? L.openings : L.framing);
    var hit = null;
    pool.forEach(function (o) { if (o.id === S.sel.id) hit = o; });
    return hit;
  }

  /* ---------------- the underlay's place in the world ---------------- */

  function underlayScale() {
    var u = MODEL && MODEL.underlay;
    if (!u) return null;
    var s = scaleOf(u);
    if (s) return { s: s, provisional: false };
    /* Uncalibrated: shown at a provisional 50 ft across so it is visible
       and can be clicked on. Nothing traced off it means anything until
       the two calibration points are set, and the canvas says so. */
    return { s: 50 / (num(u.pxW) || 1000), provisional: true };
  }
  function underlayBox() {
    var u = MODEL && MODEL.underlay;
    if (!u) return null;
    var sc = underlayScale();
    var ox = u.originFt[0], oy = u.originFt[1];
    return {
      x1: ox, y1: oy,
      x2: ox + (num(u.pxW) || 1000) * sc.s,
      y2: oy + (num(u.pxH) || 800) * sc.s,
      s: sc.s, provisional: sc.provisional
    };
  }
  function worldToImg(x, y) {
    var u = MODEL.underlay, b = underlayBox();
    return { px: (x - u.originFt[0]) / b.s, py: (num(u.pxH) || 800) - (y - u.originFt[1]) / b.s };
  }
  function imgToWorld(px, py) {
    var u = MODEL.underlay, b = underlayBox();
    return { x: u.originFt[0] + px * b.s, y: u.originFt[1] + ((num(u.pxH) || 800) - py) * b.s };
  }

  /* ---------------- drawing ---------------- */

  function txt(x, y, s, cls, anchor) {
    return sv("text", { x: x, y: y, class: cls || "cad-t", "text-anchor": anchor || "middle", text: s });
  }

  function drawGrid(g) {
    var x0 = wx(0), x1 = wx(VW), y0 = wy(VH), y1 = wy(0);
    var minor = S.snapFt, major = 5, i;
    if (minor * S.view.k >= 7) {
      for (i = Math.ceil(x0 / minor) * minor; i <= x1; i += minor) {
        if (Math.abs(i / major - Math.round(i / major)) < 1e-6) continue;
        g.appendChild(sv("line", { x1: sx(i), y1: 0, x2: sx(i), y2: VH, class: "cad-grid-minor" }));
      }
      for (i = Math.ceil(y0 / minor) * minor; i <= y1; i += minor) {
        if (Math.abs(i / major - Math.round(i / major)) < 1e-6) continue;
        g.appendChild(sv("line", { x1: 0, y1: sy(i), x2: VW, y2: sy(i), class: "cad-grid-minor" }));
      }
    }
    if (major * S.view.k >= 16) {
      for (i = Math.ceil(x0 / major) * major; i <= x1; i += major) {
        g.appendChild(sv("line", { x1: sx(i), y1: 0, x2: sx(i), y2: VH,
          class: i === 0 ? "cad-grid-axis" : "cad-grid-major" }));
      }
      for (i = Math.ceil(y0 / major) * major; i <= y1; i += major) {
        g.appendChild(sv("line", { x1: 0, y1: sy(i), x2: VW, y2: sy(i),
          class: i === 0 ? "cad-grid-axis" : "cad-grid-major" }));
      }
    }
  }

  function drawScaleBar(g) {
    var steps = [1, 2, 5, 10, 20, 50, 100], want = null, i;
    for (i = 0; i < steps.length; i++) {
      if (steps[i] * S.view.k >= 60 && steps[i] * S.view.k <= 200) { want = steps[i]; break; }
    }
    if (want === null) want = steps[steps.length - 1];
    var px = want * S.view.k, x = 16, y = VH - 18;
    g.appendChild(sv("line", { x1: x, y1: y, x2: x + px, y2: y, class: "cad-scale" }));
    g.appendChild(sv("line", { x1: x, y1: y - 5, x2: x, y2: y + 5, class: "cad-scale" }));
    g.appendChild(sv("line", { x1: x + px, y1: y - 5, x2: x + px, y2: y + 5, class: "cad-scale" }));
    g.appendChild(txt(x + px / 2, y - 8, want + " ft", "cad-t cad-t-dim"));
  }

  function drawWall(g, w, isSel) {
    var th = num(w.thicknessIn);
    var a = { x: sx(w.x1), y: sy(w.y1) }, b = { x: sx(w.x2), y: sy(w.y2) };
    var cls = "cad-wall" + (w.exterior ? " is-ext" : " is-int") + (w.bearing ? " is-bearing" : "") +
              (isSel ? " is-sel" : "");
    if (th !== null && th > 0 && (th / 12) * S.view.k > 3) {
      var n = wallNormal(w), h = (th / 12) / 2;
      var pts = [
        [sx(w.x1 + n.x * h), sy(w.y1 + n.y * h)], [sx(w.x2 + n.x * h), sy(w.y2 + n.y * h)],
        [sx(w.x2 - n.x * h), sy(w.y2 - n.y * h)], [sx(w.x1 - n.x * h), sy(w.y1 - n.y * h)]
      ];
      g.appendChild(sv("polygon", {
        points: pts.map(function (p) { return p[0] + "," + p[1]; }).join(" "),
        class: "cad-wall-band" + (w.bearing ? " is-bearing" : "") + (isSel ? " is-sel" : "")
      }));
    }
    g.appendChild(sv("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y, class: cls }));
    if (th === null) {
      g.appendChild(sv("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y, class: "cad-wall-nothick" }));
    }
  }

  function drawOpening(g, o, w, isSel) {
    var p1 = pointAlong(w, o.offsetFt), p2 = pointAlong(w, o.offsetFt + o.widthFt);
    var n = wallNormal(w);
    var th = num(w.thicknessIn), h = ((th === null ? 5.5 : th) / 12) / 2;
    var pts = [
      [sx(p1.x + n.x * h), sy(p1.y + n.y * h)], [sx(p2.x + n.x * h), sy(p2.y + n.y * h)],
      [sx(p2.x - n.x * h), sy(p2.y - n.y * h)], [sx(p1.x - n.x * h), sy(p1.y - n.y * h)]
    ];
    g.appendChild(sv("polygon", {
      points: pts.map(function (p) { return p[0] + "," + p[1]; }).join(" "),
      class: "cad-open is-" + o.kind + (isSel ? " is-sel" : "") +
             (o.offsetBasis === "placeholder" ? " is-placeholder" : "")
    }));
    g.appendChild(sv("line", { x1: sx(p1.x), y1: sy(p1.y), x2: sx(p2.x), y2: sy(p2.y),
      class: "cad-open-line is-" + o.kind }));
    if (o.widthFt * S.view.k > 34) {
      var mid = pointAlong(w, o.offsetFt + o.widthFt / 2);
      g.appendChild(txt(sx(mid.x) + n.x * 15, sy(mid.y) - n.y * 15 + 4, ftIn(o.widthFt), "cad-t cad-t-open"));
    }
  }

  function drawFramingRegion(g, f, isSel) {
    var pts = (f.polygon || []).map(function (p) { return sx(p[0]) + "," + sy(p[1]); }).join(" ");
    g.appendChild(sv("polygon", { points: pts, class: "cad-region is-" + f.kind + (isSel ? " is-sel" : "") }));

    /* direction hatching — the span direction is the whole point of a region */
    var dir = num(f.directionDeg);
    if (dir !== null && f.polygon.length >= 3) {
      var box = { x1: Infinity, y1: Infinity, x2: -Infinity, y2: -Infinity };
      f.polygon.forEach(function (p) {
        box.x1 = Math.min(box.x1, p[0]); box.y1 = Math.min(box.y1, p[1]);
        box.x2 = Math.max(box.x2, p[0]); box.y2 = Math.max(box.y2, p[1]);
      });
      var cx = (box.x1 + box.x2) / 2, cy = (box.y1 + box.y2) / 2;
      var rad = dir * Math.PI / 180;
      var ux = Math.cos(rad), uy = Math.sin(rad);
      var span = Math.max(box.x2 - box.x1, box.y2 - box.y1);
      var stepFt = num(f.spacingIn) ? Math.max(num(f.spacingIn) / 12, span / 24) : span / 8;
      var i, k;
      for (k = -12; k <= 12; k++) {
        var offx = -uy * k * stepFt, offy = ux * k * stepFt;
        var ax = cx + offx - ux * span, ay = cy + offy - uy * span;
        var bx = cx + offx + ux * span, by = cy + offy + uy * span;
        /* keep only the part inside the polygon, sampled */
        var segs = [], on = false, s0 = null;
        for (i = 0; i <= 60; i++) {
          var t = i / 60;
          var px = ax + (bx - ax) * t, py = ay + (by - ay) * t;
          var inside = pointInPoly(f.polygon, px, py);
          if (inside && !on) { on = true; s0 = [px, py]; }
          else if (!inside && on) { on = false; segs.push([s0, [px, py]]); }
        }
        if (on) segs.push([s0, [bx, by]]);
        segs.forEach(function (sg) {
          g.appendChild(sv("line", {
            x1: sx(sg[0][0]), y1: sy(sg[0][1]), x2: sx(sg[1][0]), y2: sy(sg[1][1]),
            class: "cad-region-dir is-" + f.kind
          }));
        });
      }
      var lab = f.id + " · " + f.kind + " · " + dir + "°" +
                (num(f.spacingIn) ? " @ " + num(f.spacingIn) + " in o.c." : " · spacing not set");
      g.appendChild(txt(sx(cx), sy(cy), lab, "cad-t cad-t-region"));
    }
  }

  function drawDims(g) {
    var L = level();
    (L.walls || []).forEach(function (w) {
      var len = wallLength(w);
      if (len * S.view.k < 40) return;
      var m = pointAlong(w, len / 2), n = wallNormal(w);
      var off = 15;
      var ang = wallAngleDeg(w);
      if (ang > 90) ang -= 180;
      if (ang < -90) ang += 180;
      var tx = sx(m.x + n.x * (off / S.view.k)), ty = sy(m.y + n.y * (off / S.view.k));
      g.appendChild(sv("text", {
        x: tx, y: ty, class: "cad-t cad-t-dim", "text-anchor": "middle",
        transform: "rotate(" + (-ang) + " " + tx + " " + ty + ")",
        text: w.id + "  " + ftIn(len)
      }));
    });
  }

  function drawCanvas() {
    if (!SVG) return;
    clear(SVG);
    var L = level();
    var gBack = sv("g"), gMid = sv("g"), gTop = sv("g");
    SVG.appendChild(gBack); SVG.appendChild(gMid); SVG.appendChild(gTop);

    /* underlay */
    var u = MODEL && MODEL.underlay;
    if (u) {
      var b = underlayBox();
      gBack.appendChild(sv("image", {
        href: u.dataUri, x: sx(b.x1), y: sy(b.y2),
        width: (b.x2 - b.x1) * S.view.k, height: (b.y2 - b.y1) * S.view.k,
        opacity: u.opacity, preserveAspectRatio: "none"
      }));
      if (b.provisional) {
        gBack.appendChild(sv("rect", { x: sx(b.x1), y: sy(b.y2), width: (b.x2 - b.x1) * S.view.k,
          height: (b.y2 - b.y1) * S.view.k, class: "cad-underlay-warn" }));
        gBack.appendChild(txt(sx((b.x1 + b.x2) / 2), sy(b.y2) + 20,
          "UNDERLAY NOT CALIBRATED — provisional size, trace nothing off it yet", "cad-t cad-t-warn"));
      }
    }

    drawGrid(gBack);

    if (L) {
      (L.framing || []).forEach(function (f) {
        drawFramingRegion(gMid, f, S.sel && S.sel.kind === "framing" && S.sel.id === f.id);
      });
      (L.walls || []).forEach(function (w) {
        drawWall(gMid, w, S.sel && S.sel.kind === "wall" && S.sel.id === w.id);
      });
      (L.openings || []).forEach(function (o) {
        var w = wallById(L, o.wallId);
        if (w) drawOpening(gMid, o, w, S.sel && S.sel.kind === "opening" && S.sel.id === o.id);
      });
      drawDims(gTop);

      /* endpoint handles on the selected wall */
      var sel = selected();
      if (sel && S.sel.kind === "wall") {
        [[sel.x1, sel.y1], [sel.x2, sel.y2]].forEach(function (p) {
          gTop.appendChild(sv("circle", { cx: sx(p[0]), cy: sy(p[1]), r: 5, class: "cad-handle" }));
        });
      }
      if (sel && S.sel.kind === "framing") {
        (sel.polygon || []).forEach(function (p) {
          gTop.appendChild(sv("circle", { cx: sx(p[0]), cy: sy(p[1]), r: 4, class: "cad-handle" }));
        });
      }
    }

    /* in-progress geometry */
    var d = S.draft;
    if (d && d.kind === "wall" && d.to) {
      gTop.appendChild(sv("line", { x1: sx(d.from.x), y1: sy(d.from.y), x2: sx(d.to.x), y2: sy(d.to.y),
        class: "cad-draft" }));
      var len = dist(d.from.x, d.from.y, d.to.x, d.to.y);
      var ang = Math.atan2(d.to.y - d.from.y, d.to.x - d.from.x) * 180 / Math.PI;
      gTop.appendChild(txt(sx((d.from.x + d.to.x) / 2), sy((d.from.y + d.to.y) / 2) - 10,
        ftIn(len) + "  " + (Math.round(ang * 10) / 10) + "°", "cad-t cad-t-live"));
    }
    if (d && d.kind === "rect" && d.to) {
      var x1 = Math.min(d.from.x, d.to.x), x2 = Math.max(d.from.x, d.to.x);
      var y1 = Math.min(d.from.y, d.to.y), y2 = Math.max(d.from.y, d.to.y);
      gTop.appendChild(sv("rect", { x: sx(x1), y: sy(y2), width: (x2 - x1) * S.view.k,
        height: (y2 - y1) * S.view.k, class: "cad-draft-fill" }));
      gTop.appendChild(txt(sx((x1 + x2) / 2), sy((y1 + y2) / 2),
        ftIn(x2 - x1) + " x " + ftIn(y2 - y1) + " = " + Math.round((x2 - x1) * (y2 - y1)) + " sf",
        "cad-t cad-t-live"));
    }
    if (d && d.kind === "poly" && d.pts.length) {
      var ptsStr = d.pts.map(function (p) { return sx(p[0]) + "," + sy(p[1]); }).join(" ");
      if (d.to) ptsStr += " " + sx(d.to.x) + "," + sy(d.to.y);
      gTop.appendChild(sv("polyline", { points: ptsStr, class: "cad-draft" }));
      d.pts.forEach(function (p) {
        gTop.appendChild(sv("circle", { cx: sx(p[0]), cy: sy(p[1]), r: 4, class: "cad-handle" }));
      });
    }
    if (d && d.kind === "calib") {
      if (d.a) gTop.appendChild(sv("circle", { cx: sx(d.a.x), cy: sy(d.a.y), r: 5, class: "cad-calib-pt" }));
      if (d.a && d.to) {
        gTop.appendChild(sv("line", { x1: sx(d.a.x), y1: sy(d.a.y), x2: sx(d.to.x), y2: sy(d.to.y),
          class: "cad-calib-line" }));
      }
    }
    /* an existing calibration stays visible — it is a claim about the drawing */
    if (u && u.calib) {
      var A = imgToWorld(u.calib.ax, u.calib.ay), B = imgToWorld(u.calib.bx, u.calib.by);
      gTop.appendChild(sv("line", { x1: sx(A.x), y1: sy(A.y), x2: sx(B.x), y2: sy(B.y), class: "cad-calib-line" }));
      gTop.appendChild(sv("circle", { cx: sx(A.x), cy: sy(A.y), r: 4, class: "cad-calib-pt" }));
      gTop.appendChild(sv("circle", { cx: sx(B.x), cy: sy(B.y), r: 4, class: "cad-calib-pt" }));
      gTop.appendChild(txt(sx((A.x + B.x) / 2), sy((A.y + B.y) / 2) - 8,
        "calibrated " + ftIn(u.calib.knownFt), "cad-t cad-t-live"));
    }

    /* origin */
    gTop.appendChild(sv("circle", { cx: sx(0), cy: sy(0), r: 3, class: "cad-origin" }));
    gTop.appendChild(txt(sx(0) + 14, sy(0) - 8, "0,0", "cad-t cad-t-dim"));
    drawScaleBar(gTop);
  }

  /* ---------------- mutations ---------------- */

  function deleteSelected() {
    var L = level(), sel = selected();
    if (!sel) { toast("Nothing is selected. Click a wall, an opening or a region first."); return; }
    pushUndo();
    if (S.sel.kind === "wall") {
      var lost = L.openings.filter(function (o) { return o.wallId === sel.id; });
      var usedBy = L.framing.filter(function (f) { return f.bearsOn.indexOf(sel.id) !== -1; });
      L.walls = L.walls.filter(function (w) { return w.id !== sel.id; });
      L.openings = L.openings.filter(function (o) { return o.wallId !== sel.id; });
      L.framing.forEach(function (f) {
        f.bearsOn = f.bearsOn.filter(function (id) { return id !== sel.id; });
      });
      toast("Deleted " + sel.id +
            (lost.length ? " and its " + lost.length + " opening" + (lost.length > 1 ? "s" : "") : "") +
            (usedBy.length ? ". " + usedBy.map(function (f) { return f.id; }).join(", ") +
             " now bears on one wall fewer — check the framing panel." : "."));
    } else if (S.sel.kind === "opening") {
      L.openings = L.openings.filter(function (o) { return o.id !== sel.id; });
      toast("Deleted opening " + sel.id + ".");
    } else {
      L.framing = L.framing.filter(function (f) { return f.id !== sel.id; });
      toast("Deleted framing region " + sel.id + ".");
    }
    S.sel = null;
    redraw();
  }

  function moveSelected(dx, dy) {
    var sel = selected(), L = level();
    if (!sel) return;
    if (S.sel.kind === "wall") {
      sel.x1 += dx; sel.y1 += dy; sel.x2 += dx; sel.y2 += dy;
    } else if (S.sel.kind === "framing") {
      sel.polygon = sel.polygon.map(function (p) { return [p[0] + dx, p[1] + dy]; });
    } else {
      var w = wallById(L, sel.wallId);
      if (!w) return;
      var ux = (w.x2 - w.x1) / wallLength(w), uy = (w.y2 - w.y1) / wallLength(w);
      var along = dx * ux + dy * uy;
      var want = Math.max(0, Math.min(wallLength(w) - sel.widthFt, sel.offsetFt + along));
      var was = sel.offsetFt;
      sel.offsetFt = Math.round(want * 1000) / 1000;
      var fitNow = openingFits(w, sel, L.openings);
      if (!fitNow.ok) { sel.offsetFt = was; toast(fitNow.text); return; }
      if (sel.offsetBasis === "placeholder") sel.offsetBasis = "user";
    }
  }

  function addWall(from, to) {
    var L = level();
    if (dist(from.x, from.y, to.x, to.y) < RULES.minWallFt) {
      toast("That wall would be " + f2(dist(from.x, from.y, to.x, to.y)) + " ft long. Walls under " +
            f2(RULES.minWallFt) + " ft are mis-clicks, so nothing was added.");
      return null;
    }
    pushUndo();
    var w = newWall(L, from.x, from.y, to.x, to.y, {
      thicknessIn: S.defaults.thicknessIn,
      heightFt: L.topPlateFt === null ? null : L.topPlateFt
    });
    L.walls.push(w);
    S.sel = { kind: "wall", id: w.id };
    return w;
  }

  function addOpeningAt(pt) {
    var L = level();
    var hit = null, bestD = 14 / S.view.k;
    L.walls.forEach(function (w) {
      var p = projectOnWall(w, pt.x, pt.y);
      if (p.d < bestD && p.u >= 0 && p.u <= 1) { bestD = p.d; hit = { w: w, t: p.t }; }
    });
    if (!hit) { toast("Click on a wall — an opening belongs to a wall and moves with it."); return; }
    var wdt = S.defaults.openWidthFt;
    var off = Math.round((hit.t - wdt / 2) / S.snapFt) * S.snapFt;
    var probe = { id: "this opening", wallId: hit.w.id, offsetFt: off, widthFt: wdt };
    var fitNow = openingFits(hit.w, probe, L.openings);
    if (!fitNow.ok) {
      /* try nudging it inside before refusing — the click is a position, not a demand */
      var end = endClearFt(), L2 = wallLength(hit.w);
      probe.offsetFt = Math.max(end, Math.min(L2 - wdt - end, off));
      fitNow = openingFits(hit.w, probe, L.openings);
    }
    if (!fitNow.ok) { toast(fitNow.text); return; }
    pushUndo();
    var o = newOpening(L, hit.w.id, Math.round(probe.offsetFt * 1000) / 1000, wdt, {
      kind: S.defaults.kind, headHeightFt: S.defaults.headHeightFt, offsetBasis: "user"
    });
    L.openings.push(o);
    S.sel = { kind: "opening", id: o.id };
    if (!hit.w.bearing) {
      toast("Placed " + o.id + " in " + hit.w.id + ", which is not a bearing wall — it produces no " +
            "header mark in the takeoff.");
    }
  }

  function addFramingPoly(poly) {
    var L = level();
    if (polyArea(poly) < 1) {
      toast("That region encloses " + f1(polyArea(poly)) + " sf. Draw it larger.");
      return;
    }
    pushUndo();
    var touching = L.walls.filter(function (w) { return w.bearing && touchesRegion(poly, w); });
    var f = newFraming(L, poly, {
      kind: S.defaults.framingKind,
      directionDeg: 0, spacingIn: null,
      bearsOn: touching.map(function (w) { return w.id; })
    });
    L.framing.push(f);
    S.sel = { kind: "framing", id: f.id };
    toast(f.id + " · " + Math.round(polyArea(poly)) + " sf. " +
          (touching.length ? "Ticked the " + touching.length + " bearing wall" +
            (touching.length > 1 ? "s" : "") + " it touches (" +
            touching.map(function (w) { return w.id; }).join(", ") + ") — change them in the panel."
           : "No bearing wall touches it, so nothing is ticked: set the span direction and the walls " +
             "it lands on in the panel."));
  }

  /* ---------------- pointer ---------------- */

  var drag = null;

  function onDown(e) {
    if (e.button === 2) return;
    SVG.focus();
    var pt = eventPoint(e);
    var isPan = S.tool === "pan" || e.button === 1 || e.altKey;
    if (isPan) {
      drag = { kind: "pan", px: pt.px, py: pt.py, vx: S.view.x, vy: S.view.y };
      if (SVG.setPointerCapture && e.pointerId !== undefined) SVG.setPointerCapture(e.pointerId);
      return;
    }
    var sp = snap(pt, null, e.shiftKey);

    if (S.tool === "wall") {
      if (S.draft && S.draft.kind === "wall") return;   /* chained: the up-click ends it */
      S.draft = { kind: "wall", from: { x: sp.x, y: sp.y }, to: null, downPx: { x: pt.px, y: pt.py } };
      drag = { kind: "draw" };
      if (SVG.setPointerCapture && e.pointerId !== undefined) SVG.setPointerCapture(e.pointerId);
      return;
    }
    if (S.tool === "rect") {
      S.draft = { kind: "rect", from: { x: sp.x, y: sp.y }, to: null };
      drag = { kind: "draw" };
      if (SVG.setPointerCapture && e.pointerId !== undefined) SVG.setPointerCapture(e.pointerId);
      return;
    }
    if (S.tool === "poly") {
      if (!S.draft || S.draft.kind !== "poly") S.draft = { kind: "poly", pts: [], to: null };
      var first = S.draft.pts[0];
      if (first && dist(first[0], first[1], sp.x, sp.y) * S.view.k < 12 && S.draft.pts.length >= 3) {
        var poly = S.draft.pts.slice();
        S.draft = null;
        addFramingPoly(poly);
        redraw();
        return;
      }
      S.draft.pts.push([sp.x, sp.y]);
      drawCanvas();
      return;
    }
    if (S.tool === "opening") {
      addOpeningAt(pt);
      redraw();
      return;
    }
    if (S.tool === "calib") {
      if (!MODEL.underlay) { toast("There is no underlay to calibrate. Load a PNG or JPG first."); return; }
      if (!S.draft || S.draft.kind !== "calib") S.draft = { kind: "calib", a: null, to: null };
      if (!S.draft.a) { S.draft.a = { x: pt.x, y: pt.y }; drawCanvas(); toast("First point set. Click the second point."); }
      else { finishCalibration({ x: pt.x, y: pt.y }); }
      return;
    }

    /* select */
    var sel = selected();
    if (sel && S.sel.kind === "wall") {
      var grab = null;
      [["a", sel.x1, sel.y1], ["b", sel.x2, sel.y2]].forEach(function (h) {
        if (dist(pt.x, pt.y, h[1], h[2]) * S.view.k < 10) grab = h[0];
      });
      if (grab) {
        pushUndo();
        drag = { kind: "endpoint", end: grab };
        if (SVG.setPointerCapture && e.pointerId !== undefined) SVG.setPointerCapture(e.pointerId);
        return;
      }
    }
    var hit = hitTest(pt);
    S.sel = hit;
    if (hit) {
      pushUndo();
      drag = { kind: "move", last: { x: sp.x, y: sp.y }, moved: false };
      if (SVG.setPointerCapture && e.pointerId !== undefined) SVG.setPointerCapture(e.pointerId);
    }
    redraw();
  }

  function onMove(e) {
    var pt = eventPoint(e);
    S.cursor = pt;
    if (drag && drag.kind === "pan") {
      S.view.x = drag.vx - (pt.px - drag.px) / S.view.k;
      S.view.y = drag.vy + (pt.py - drag.py) / S.view.k;
      drawCanvas(); updateHud();
      return;
    }
    if (drag && drag.kind === "endpoint") {
      var sel = selected();
      var sp2 = snap(pt, drag.end === "a" ? { x: sel.x2, y: sel.y2 } : { x: sel.x1, y: sel.y1 }, e.shiftKey);
      if (drag.end === "a") { sel.x1 = sp2.x; sel.y1 = sp2.y; } else { sel.x2 = sp2.x; sel.y2 = sp2.y; }
      drawCanvas(); updateHud();
      return;
    }
    if (drag && drag.kind === "move") {
      var sp3 = snap(pt, null, e.shiftKey);
      var dx = sp3.x - drag.last.x, dy = sp3.y - drag.last.y;
      if (dx || dy) {
        moveSelected(dx, dy);
        drag.last = { x: sp3.x, y: sp3.y };
        drag.moved = true;
        drawCanvas();
      }
      updateHud();
      return;
    }
    if (S.draft) {
      var from = S.draft.kind === "wall" ? S.draft.from
               : (S.draft.kind === "poly" && S.draft.pts.length
                  ? { x: S.draft.pts[S.draft.pts.length - 1][0], y: S.draft.pts[S.draft.pts.length - 1][1] }
                  : (S.draft.kind === "calib" ? null : S.draft.from));
      var sp4 = snap(pt, S.draft.kind === "calib" ? null : from, e.shiftKey);
      S.draft.to = S.draft.kind === "calib" ? { x: pt.x, y: pt.y } : { x: sp4.x, y: sp4.y };
      drawCanvas();
    }
    updateHud();
  }

  function onUp(e) {
    var pt = eventPoint(e);
    if (drag && drag.kind === "pan") { drag = null; return; }
    if (drag && (drag.kind === "endpoint" || drag.kind === "move")) {
      if (!drag.moved && drag.kind === "move") UNDO.pop();   /* a click is not an edit */
      drag = null;
      redraw();
      return;
    }
    if (S.draft && S.draft.kind === "wall") {
      var moved = dist(pt.px, pt.py, S.draft.downPx.x, S.draft.downPx.y) > 4;
      if (!moved) {
        /* click-click chaining: leave the draft open, the next click ends it */
        if (S.draft.to && dist(S.draft.from.x, S.draft.from.y, S.draft.to.x, S.draft.to.y) > 1e-6) {
          var w = addWall(S.draft.from, S.draft.to);
          S.draft = w ? { kind: "wall", from: { x: S.draft.to.x, y: S.draft.to.y }, to: null,
                          downPx: { x: pt.px, y: pt.py } } : null;
        }
        drag = null;
        redraw();
        return;
      }
      var sp = snap(pt, S.draft.from, e.shiftKey);
      addWall(S.draft.from, { x: sp.x, y: sp.y });
      S.draft = null;
      drag = null;
      redraw();
      return;
    }
    if (S.draft && S.draft.kind === "rect") {
      var a = S.draft.from, b = S.draft.to;
      S.draft = null; drag = null;
      if (b && Math.abs(a.x - b.x) > 0.1 && Math.abs(a.y - b.y) > 0.1) {
        var x1 = Math.min(a.x, b.x), x2 = Math.max(a.x, b.x);
        var y1 = Math.min(a.y, b.y), y2 = Math.max(a.y, b.y);
        addFramingPoly([[x1, y1], [x2, y1], [x2, y2], [x1, y2]]);
      }
      redraw();
      return;
    }
    drag = null;
  }

  function onWheel(e) {
    e.preventDefault();
    var pt = eventPoint(e);
    var f = Math.exp(-(e.deltaY || 0) * 0.0016);
    zoomAt(pt.px, pt.py, Math.max(0.5, Math.min(2, f)));
    drawCanvas(); updateHud();
  }

  /* ---------------- calibration ---------------- */

  function finishCalibration(b) {
    var a = S.draft.a;
    var pxDist = dist(a.x, a.y, b.x, b.y) / underlayBox().s;
    if (pxDist < 4) {
      toast("Those two points are " + Math.round(pxDist) + " pixels apart on the image. Pick two " +
            "points further apart — a short baseline multiplies its own error.");
      S.draft = null; drawCanvas();
      return;
    }
    var typed = window.prompt("How far apart are those two points on the real building, in feet?\n" +
                             "(e.g. 46 for a 46 ft wall, 3.5 for a 3'-6\" door)", "");
    if (typed === null) { S.draft = null; drawCanvas(); return; }
    var known = num(typed);
    if (known === null || known <= 0) {
      toast("“" + typed + "” is not a distance in feet. Calibration is unchanged.");
      S.draft = null; drawCanvas();
      return;
    }
    pushUndo();
    var ia = worldToImg(a.x, a.y), ib = worldToImg(b.x, b.y);
    MODEL.underlay.calib = { ax: ia.px, ay: ia.py, bx: ib.px, by: ib.py, knownFt: known };
    S.draft = null;
    S.tool = "select";
    var ftPerPx = scaleOf(MODEL.underlay);
    toast("Calibrated: " + known + " ft across " + Math.round(pxDist) + " px = " +
          (Math.round(ftPerPx * 100000) / 100000) + " ft per pixel (" +
          (Math.round((1 / ftPerPx) * 10) / 10) + " px per ft).");
    fit();
    redraw();
  }

  /* ---------------- keyboard ---------------- */

  function onKey(e) {
    var k = e.key;
    if (k === "Escape") {
      if (S.draft) { S.draft = null; toast("Cancelled."); }
      else if (S.sel) { S.sel = null; }
      redraw(); return;
    }
    if (k === "Delete" || k === "Backspace") { e.preventDefault(); deleteSelected(); return; }
    if (k === "Enter" && S.draft && S.draft.kind === "poly" && S.draft.pts.length >= 3) {
      var poly = S.draft.pts.slice(); S.draft = null; addFramingPoly(poly); redraw(); return;
    }
    if ((e.ctrlKey || e.metaKey) && k.toLowerCase() === "z") {
      e.preventDefault();
      if (e.shiftKey) redo(); else undo();
      return;
    }
    if ((e.ctrlKey || e.metaKey) && k.toLowerCase() === "y") { e.preventDefault(); redo(); return; }
    if (k === "ArrowLeft" || k === "ArrowRight" || k === "ArrowUp" || k === "ArrowDown") {
      if (!S.sel) return;
      e.preventDefault();
      var step = e.shiftKey ? S.snapFt * 10 : S.snapFt;
      pushUndo();
      moveSelected(k === "ArrowLeft" ? -step : (k === "ArrowRight" ? step : 0),
                   k === "ArrowDown" ? -step : (k === "ArrowUp" ? step : 0));
      redraw();
      return;
    }
    if (k === "+" || k === "=") { zoomAt(VW / 2, VH / 2, 1.2); drawCanvas(); updateHud(); return; }
    if (k === "-" || k === "_") { zoomAt(VW / 2, VH / 2, 1 / 1.2); drawCanvas(); updateHud(); return; }
    if (k.toLowerCase() === "f") { fit(); drawCanvas(); updateHud(); return; }
    if (k.toLowerCase() === "g") { S.snapOn = !S.snapOn; toast("Snap " + (S.snapOn ? "on" : "off") + "."); redraw(); return; }
    var t = null;
    TOOLS.forEach(function (tt) { if (tt.key.toLowerCase() === k.toLowerCase()) t = tt.id; });
    if (t) { setTool(t); }
  }

  function setTool(id) {
    S.tool = id;
    S.draft = null;
    redraw();
  }

  /* ---------------- form helpers ---------------- */

  var uid = 0;
  function field(label, node, hint) {
    var id = "cad-f" + (++uid);
    node.setAttribute("id", id);
    var f = el("div", { class: "field" }, [el("label", { "for": id, text: label }), node]);
    if (hint) f.appendChild(el("span", { class: "field-hint", text: hint }));
    return f;
  }
  function numBox(value, step, onCommit) {
    var n = el("input", { type: "number", step: step || "0.5",
      value: (value === null || value === undefined) ? "" : String(value) });
    n.addEventListener("change", function () { onCommit(this.value === "" ? null : num(this.value)); });
    return n;
  }
  function textBox(value, onCommit) {
    var n = el("input", { type: "text", value: value || "" });
    n.addEventListener("change", function () { onCommit(this.value); });
    return n;
  }
  function pickBox(options, value, onCommit) {
    var n = el("select", {}, options.map(function (o) {
      return el("option", { value: o, text: o, selected: o === value ? "selected" : null });
    }));
    n.addEventListener("change", function () { onCommit(this.value); });
    return n;
  }
  function toggle(label, checked, onCommit) {
    var id = "cad-c" + (++uid);
    var box = el("input", { type: "checkbox", id: id, style: "width:auto" });
    box.checked = !!checked;
    box.addEventListener("change", function () { onCommit(this.checked); });
    return el("div", { style: "display:flex;align-items:center;gap:7px" }, [
      box, el("label", { "for": id, text: label, style: "text-transform:none;letter-spacing:0;font-size:.83rem;font-family:var(--sans);color:var(--ink)" })
    ]);
  }
  function edit(fn) { pushUndo(); fn(); redraw(); }

  /* ---------------- the side panel ---------------- */

  function panelWall(w) {
    var L = level();
    var mine = L.openings.filter(function (o) { return o.wallId === w.id; });
    var rows = [
      el("div", { class: "field-row" }, [
        field("x1 (ft)", numBox(w.x1, "0.5", function (v) { edit(function () { w.x1 = v === null ? 0 : v; }); })),
        field("y1 (ft)", numBox(w.y1, "0.5", function (v) { edit(function () { w.y1 = v === null ? 0 : v; }); }))
      ]),
      el("div", { class: "field-row" }, [
        field("x2 (ft)", numBox(w.x2, "0.5", function (v) { edit(function () { w.x2 = v === null ? 0 : v; }); })),
        field("y2 (ft)", numBox(w.y2, "0.5", function (v) { edit(function () { w.y2 = v === null ? 0 : v; }); }))
      ]),
      toggle("Exterior wall", w.exterior, function (v) { edit(function () { w.exterior = v; }); }),
      toggle("Bearing — carries framing above", w.bearing, function (v) { edit(function () { w.bearing = v; }); }),
      el("div", { class: "field-row" }, [
        field("Thickness (in)", numBox(w.thicknessIn, "0.5", function (v) {
          edit(function () { w.thicknessIn = v; w.thicknessBasis = "user"; });
        }), w.thicknessBasis === "assumed" ? "ASSUMED 2x4 — confirm and retype" : "3.5 = 2x4, 5.5 = 2x6"),
        field("Height (ft)", numBox(w.heightFt, "0.25", function (v) { edit(function () { w.heightFt = v; }); }))
      ]),
      field("Note", textBox(w.note, function (v) { edit(function () { w.note = v; }); }))
    ];
    var body = el("div", { style: "display:grid;gap:10px" }, rows);
    body.appendChild(dl([
      { k: "Length", v: esc(ftIn(wallLength(w))) + " · " + f2(wallLength(w)) + " ft" },
      { k: "Bearing", v: w.bearing ? "yes" : "no", cls: w.bearing ? "" : "gold" },
      { k: "Openings", v: String(mine.length) }
    ]));
    if (w.basis) body.appendChild(el("p", { class: "clause", text: w.basis }));
    if (mine.length) {
      var chips = el("div", { class: "chips" }, mine.map(function (o) {
        return el("button", { class: "chip", text: o.id + " " + ftIn(o.widthFt),
          onclick: function () { S.sel = { kind: "opening", id: o.id }; redraw(); } });
      }));
      body.appendChild(chips);
    }
    body.appendChild(el("button", { class: "btn btn-sm", text: "Delete " + w.id, onclick: deleteSelected }));
    return card("Wall " + w.id, el("span", { class: "badge " + (w.exterior ? "b-blue" : "b-mute"),
      text: w.exterior ? "Exterior" : "Interior", style: "margin-left:auto" }), body, null);
  }

  function panelOpening(o) {
    var L = level(), w = wallById(L, o.wallId);
    var fitNow = w ? openingFits(w, o, L.openings) : { ok: false, text: "This opening names no wall." };
    var body = el("div", { style: "display:grid;gap:10px" }, [
      field("Kind", pickBox(OPENING_KINDS, o.kind, function (v) { edit(function () { o.kind = v; }); })),
      el("div", { class: "field-row" }, [
        field("Offset (ft)", numBox(o.offsetFt, "0.25", function (v) {
          edit(function () { o.offsetFt = v === null ? 0 : v; if (o.offsetBasis === "placeholder") o.offsetBasis = "user"; });
        }), "from " + o.wallId + " start"),
        field("Width (ft)", numBox(o.widthFt, "0.25", function (v) { edit(function () { o.widthFt = v === null ? 0 : v; }); }))
      ]),
      field("Head height (ft)", numBox(o.headHeightFt, "0.25", function (v) { edit(function () { o.headHeightFt = v; }); }),
        "6.67 = 6'-8\"; 7.0 = 7'-0\""),
      field("Note", textBox(o.note, function (v) { edit(function () { o.note = v; }); }))
    ]);
    body.appendChild(dl([
      { k: "In wall", v: esc(o.wallId) + " · " + esc(ftIn(w ? wallLength(w) : 0)) },
      { k: "Fits", v: fitNow.ok ? "yes" : "NO", cls: fitNow.ok ? "pass" : "fail" },
      { k: "Position", v: o.offsetBasis === "placeholder" ? "placeholder" : o.offsetBasis,
        cls: o.offsetBasis === "placeholder" ? "gold" : "" }
    ]));
    if (!fitNow.ok) body.appendChild(el("div", { class: "banner banner-warn", style: "margin:0" }, [el("span", { text: fitNow.text })]));
    if (o.offsetBasis === "placeholder") {
      body.appendChild(el("p", { class: "clause",
        text: "Placeholder position — the source plan does not say where along the wall this opening " +
              "sits. Drag it or type an offset; the flag clears when you do." }));
    }
    if (o.note) body.appendChild(el("p", { class: "clause", text: o.note }));
    body.appendChild(el("button", { class: "btn btn-sm", text: "Delete " + o.id, onclick: deleteSelected }));
    return card("Opening " + o.id, el("span", { class: "badge b-mute", text: o.kind, style: "margin-left:auto" }), body, null);
  }

  function panelFraming(f) {
    var L = level();
    var body = el("div", { style: "display:grid;gap:10px" }, [
      field("Kind", pickBox(FRAMING_KINDS, f.kind, function (v) { edit(function () { f.kind = v; }); })),
      el("div", { class: "field-row" }, [
        field("Direction (deg)", numBox(f.directionDeg, "15", function (v) { edit(function () { f.directionDeg = v; }); }),
          "0 = along +x"),
        field("Spacing (in o.c.)", numBox(f.spacingIn, "2", function (v) { edit(function () { f.spacingIn = v; }); }))
      ]),
      el("div", { class: "chips" }, [
        el("button", { class: "chip", text: "0° — along +x", onclick: function () { edit(function () { f.directionDeg = 0; }); } }),
        el("button", { class: "chip", text: "90° — along +y", onclick: function () { edit(function () { f.directionDeg = 90; }); } }),
        el("button", { class: "chip", text: "16 in", onclick: function () { edit(function () { f.spacingIn = 16; }); } }),
        el("button", { class: "chip", text: "24 in", onclick: function () { edit(function () { f.spacingIn = 24; }); } })
      ])
    ]);
    body.appendChild(el("div", { class: "lbl", text: "Bears on", style: "margin-top:4px" }));
    var list = el("div", { style: "display:grid;gap:5px" });
    L.walls.forEach(function (w) {
      var on = f.bearsOn.indexOf(w.id) !== -1;
      var touches = touchesRegion(f.polygon, w);
      var lab = w.id + " · " + ftIn(wallLength(w)) + (w.bearing ? " · bearing" : " · NOT bearing") +
                (touches ? "" : " · does not touch this region");
      list.appendChild(toggle(lab, on, function (v) {
        edit(function () {
          if (v && f.bearsOn.indexOf(w.id) === -1) f.bearsOn.push(w.id);
          if (!v) f.bearsOn = f.bearsOn.filter(function (id) { return id !== w.id; });
        });
      }));
    });
    body.appendChild(list);
    body.appendChild(field("Note", textBox(f.note, function (v) { edit(function () { f.note = v; }); })));
    body.appendChild(dl([
      { k: "Area", v: FM.comma(Math.round(polyArea(f.polygon))) + " sf" },
      { k: "Corners", v: String((f.polygon || []).length) },
      { k: "Bears on", v: String(f.bearsOn.length), cls: f.bearsOn.length < 2 ? "fail" : "" }
    ]));
    if (f.basis) body.appendChild(el("p", { class: "clause", text: f.basis }));
    body.appendChild(el("button", { class: "btn btn-sm", text: "Delete " + f.id, onclick: deleteSelected }));
    return card("Framing " + f.id, el("span", { class: "badge b-blue", text: f.kind, style: "margin-left:auto" }), body, null);
  }

  function panelModel() {
    var L = level();
    var body = el("div", { style: "display:grid;gap:10px" }, [
      field("Model name", textBox(MODEL.name, function (v) { edit(function () { MODEL.name = v || "Untitled plan"; }); })),
      field("Level top plate (ft)", numBox(L.topPlateFt, "0.25", function (v) {
        edit(function () { L.topPlateFt = v; });
      }), "applies to new walls; use the button below for the ones already drawn")
    ]);
    body.appendChild(el("button", {
      class: "btn btn-sm", text: "Set every wall height to the top plate",
      onclick: function () {
        if (L.topPlateFt === null) { toast("Set a top plate height first — there is nothing to apply."); return; }
        edit(function () { L.walls.forEach(function (w) { w.heightFt = L.topPlateFt; }); });
        toast("Set " + L.walls.length + " wall heights to " + f2(L.topPlateFt) + " ft.");
      }
    }));
    body.appendChild(el("div", { class: "lbl", text: "New-element defaults", style: "margin-top:6px" }));
    body.appendChild(el("div", { class: "field-row" }, [
      field("Wall thickness (in)", numBox(S.defaults.thicknessIn, "0.5", function (v) { S.defaults.thicknessIn = v; })),
      field("Opening width (ft)", numBox(S.defaults.openWidthFt, "0.5", function (v) { S.defaults.openWidthFt = v === null ? 3 : v; }))
    ]));
    body.appendChild(el("div", { class: "field-row" }, [
      field("Head height (ft)", numBox(S.defaults.headHeightFt, "0.25", function (v) { S.defaults.headHeightFt = v; })),
      field("Opening kind", pickBox(OPENING_KINDS, S.defaults.kind, function (v) { S.defaults.kind = v; }))
    ]));
    body.appendChild(field("Region kind", pickBox(FRAMING_KINDS, S.defaults.framingKind, function (v) { S.defaults.framingKind = v; })));
    if (L.note) body.appendChild(el("p", { class: "clause", text: L.note }));
    return card("Model", el("span", { class: "badge b-mute", text: L.label, style: "margin-left:auto" }), body,
      "Nothing is selected — click a wall, an opening or a region to edit it");
  }

  function panelUnderlay() {
    var u = MODEL.underlay;
    var body = el("div", { style: "display:grid;gap:10px" });
    var picker = el("input", { type: "file", accept: "image/png,image/jpeg", style: "width:100%;font-size:.8rem" });
    picker.addEventListener("change", function () { if (this.files && this.files[0]) acceptFile(this.files[0]); });
    body.appendChild(field("PNG or JPG", picker, "or drop the file straight onto the drawing"));

    if (!u) {
      body.appendChild(el("p", { class: "clause",
        text: "No underlay. A PDF cannot be traced directly — run  node tools/pdf-to-underlay.js <file.pdf>  " +
              "and drop the PNG it writes." }));
      return card("Underlay", null, body, null);
    }
    var ftPerPx = scaleOf(u);
    var op = el("input", { type: "range", min: "0.05", max: "1", step: "0.05", value: String(u.opacity),
      style: "width:100%", "aria-label": "Underlay opacity" });
    op.addEventListener("input", function () { u.opacity = num(this.value); drawCanvas(); });
    body.appendChild(field("Opacity", op));
    body.appendChild(dl([
      { k: "Image", v: esc(u.name || "untitled") },
      { k: "Pixels", v: (u.pxW || "?") + " x " + (u.pxH || "?") },
      { k: "Scale", v: ftPerPx ? (Math.round(ftPerPx * 100000) / 100000) + " ft/px" : "NOT CALIBRATED",
        cls: ftPerPx ? "pass" : "fail" },
      ftPerPx ? { k: "Known distance", v: esc(ftIn(u.calib.knownFt)) } : null,
      ftPerPx ? { k: "Across", v: Math.round(dist(u.calib.ax, u.calib.ay, u.calib.bx, u.calib.by)) + " px" } : null
    ]));
    body.appendChild(el("div", { class: "chips" }, [
      el("button", { class: "chip", text: ftPerPx ? "Re-calibrate" : "Calibrate — 2 clicks",
        onclick: function () { setTool("calib"); toast("Click two points on the underlay a known distance apart."); } }),
      el("button", { class: "chip", text: "Remove underlay", onclick: function () {
        edit(function () { MODEL.underlay = null; });
        toast("Underlay removed. The walls you traced stay.");
      } })
    ]));
    if (!ftPerPx) {
      body.appendChild(el("div", { class: "banner banner-warn", style: "margin:0" }, [
        el("strong", { text: "Not calibrated — " }),
        el("span", { text: "the image is shown at a provisional size. Nothing traced off it is a real dimension yet." })
      ]));
    }
    return card("Underlay", ftPerPx ? el("span", { class: "badge b-pass", text: "Calibrated", style: "margin-left:auto" })
      : el("span", { class: "badge b-fail", text: "Uncalibrated", style: "margin-left:auto" }), body, null);
  }

  /* ---------------- findings ---------------- */

  function panelFindings() {
    var rows = validate(MODEL);
    var errs = rows.filter(function (r) { return r.severity === "error"; });
    var warns = rows.filter(function (r) { return r.severity !== "error"; });
    var body = el("div", { class: "dl" });
    if (!rows.length) {
      body = el("div", { class: "empty", text: "No findings. This geometry is ready for the takeoff gate." });
    } else {
      errs.concat(warns).forEach(function (r) {
        var badge = el("span", { class: "badge " + (r.severity === "error" ? "b-fail" : "b-warn"),
          text: r.severity === "error" ? "Error" : "Warn" });
        var row = el("div", { class: "dl-row", style: "align-items:flex-start;gap:9px" }, [
          el("span", { class: "dl-k", style: "display:flex;gap:8px;align-items:flex-start" }, [
            badge, el("span", { text: r.text })
          ]),
          el("span", { class: "dl-v", text: r.id })
        ]);
        var L = level();
        var kind = L && wallById(L, r.id) ? "wall"
          : (L && L.openings.filter(function (o) { return o.id === r.id; }).length ? "opening"
          : (L && L.framing.filter(function (f) { return f.id === r.id; }).length ? "framing" : null));
        if (kind) {
          row.setAttribute("tabindex", "0");
          row.setAttribute("role", "button");
          row.setAttribute("aria-label", "Select " + r.id + " — " + r.text);
          row.className += " clickable";
          row.addEventListener("click", function () { S.sel = { kind: kind, id: r.id }; redraw(); });
          row.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") { e.preventDefault(); S.sel = { kind: kind, id: r.id }; redraw(); }
          });
        }
        body.appendChild(row);
      });
    }
    return card("Findings", el("span", {
      class: "badge " + (errs.length ? "b-fail" : (warns.length ? "b-warn" : "b-pass")),
      text: errs.length + " error" + (errs.length === 1 ? "" : "s") + " · " + warns.length + " warn",
      style: "margin-left:auto"
    }), body, errs.length
      ? "Errors block the geometry gate. Warnings do not — they are the things a reviewer has to answer."
      : "Warnings do not block the gate. They are what this model does not know, named.");
  }

  /* ---------------- underlay input ---------------- */

  function acceptFile(file) {
    if (!file) return;
    var name = file.name || "the dropped file";
    if (/\.pdf$/i.test(name) || file.type === "application/pdf") {
      toast("A PDF cannot be traced in the browser. Run  node tools/pdf-to-underlay.js \"" + name +
            "\"  — it writes a PNG beside the PDF — then drop that PNG here.");
      return;
    }
    if (!/^image\/(png|jpeg)$/i.test(file.type || "") && !/\.(png|jpe?g)$/i.test(name)) {
      toast("“" + name + "” is " + (file.type ? "a " + file.type : "not a type this build recognises") +
            ". The underlay has to be a PNG or a JPG.");
      return;
    }
    var rd = new FileReader();
    rd.onerror = function () { toast("This browser could not read “" + name + "”. Try re-saving it as a PNG."); };
    rd.onload = function () {
      var img = new window.Image();
      img.onerror = function () {
        toast("“" + name + "” was read but could not be decoded as an image. Re-save it as a PNG.");
      };
      img.onload = function () {
        pushUndo();
        MODEL.underlay = {
          dataUri: rd.result, calib: null, opacity: 0.35,
          pxW: img.naturalWidth, pxH: img.naturalHeight, originFt: [0, 0], name: name
        };
        IMG = img;
        fit();
        redraw();
        toast("Loaded " + name + " · " + img.naturalWidth + " x " + img.naturalHeight +
              " px. It is NOT calibrated: click Calibrate, click two points a known distance apart, " +
              "and type that distance.");
      };
      img.src = rd.result;
    };
    rd.readAsDataURL(file);
  }

  /* ---------------- redraw ---------------- */

  var PANEL = null, FINDINGS = null, STATS = null, HUD = null, TOOLBAR = null;

  function updateHud() {
    if (!HUD) return;
    var tool = null;
    TOOLS.forEach(function (t) { if (t.id === S.tool) tool = t; });
    var c = S.cursor;
    HUD.textContent = (tool ? tool.label : S.tool) +
      (c ? "  ·  x " + f1(c.x) + " ft, y " + f1(c.y) + " ft" : "") +
      "  ·  grid " + ftIn(S.snapFt) + (S.snapOn ? "" : " (snap off)") +
      "  ·  " + Math.round(S.view.k) + " px/ft";
  }

  function redraw() {
    if (!PANEL) return;
    drawCanvas();
    updateHud();
    clear(PANEL);
    var sel = selected();
    if (sel && S.sel.kind === "wall") PANEL.appendChild(panelWall(sel));
    else if (sel && S.sel.kind === "opening") PANEL.appendChild(panelOpening(sel));
    else if (sel && S.sel.kind === "framing") PANEL.appendChild(panelFraming(sel));
    else PANEL.appendChild(panelModel());
    PANEL.appendChild(panelUnderlay());

    clear(FINDINGS);
    FINDINGS.appendChild(panelFindings());

    var st = stats(MODEL);
    clear(STATS);
    [FM.statCard(String(st.walls), "Walls"),
     FM.statCard(String(st.bearingWalls), "Bearing walls", st.bearingWalls ? "" : "fail"),
     FM.statCard(String(st.openings), "Openings"),
     FM.statCard(String(st.framing), "Framing regions"),
     FM.statCard(st.areaSf === null ? "—" : FM.comma(st.areaSf), "Footprint sf",
       st.areaSf === null ? "gold" : "blue")
    ].forEach(function (n) { STATS.appendChild(n); });

    if (TOOLBAR) {
      Array.prototype.forEach.call(TOOLBAR.querySelectorAll("button[data-tool]"), function (b) {
        b.setAttribute("aria-pressed", b.getAttribute("data-tool") === S.tool ? "true" : "false");
      });
    }
  }

  /* ---------------- loading a source ---------------- */

  function loadSource(announce) {
    if (S.src.kind === "plan") {
      var m = fromPlan(S.src.id);
      if (!m) {
        toast("This build has no plan called “" + S.src.id + "”. Starting an empty model instead.");
        MODEL = blank("Untitled plan");
      } else {
        MODEL = m;
        if (announce) {
          var st = stats(m);
          toast(m.name + ": " + st.walls + " walls, " + st.openings + " openings, " + st.framing +
                " framing regions, " + m.unresolved.length + " open items the plan does not determine.");
        }
      }
    } else if (S.src.kind === "saved") {
      var s = loadLocal(S.src.id);
      if (!s) {
        toast("No saved model called “" + S.src.id + "” in this browser. Starting an empty model.");
        MODEL = blank("Untitled plan");
      } else {
        MODEL = s;
        if (announce) toast("Loaded “" + S.src.id + "”.");
      }
    } else {
      MODEL = blank("Untitled plan");
      var plate = plateFtFromPacks();
      if (plate) {
        MODEL.levels[0].topPlateFt = plate.ft;
        MODEL.levels[0].note = "Top plate " + plate.inches + " in — the precut height every region " +
                               "pack in weights.js declares. Provenance [market], not code.";
      }
      if (announce) toast("Empty model. Press W and drag to draw the first wall.");
    }
    UNDO.length = 0; REDO.length = 0;
    S.sel = null; S.draft = null;
    fit();
  }

  /* ---------------- the view ---------------- */

  FM.VIEWS.cad = function (host) {
    if (!MODEL) loadSource(false);

    host.appendChild(FM.pageHead("Plan",
      "Draw the geometry, or trace it over a calibrated plan. Everything downstream — spans, " +
      "tributaries, headers — is read off what is on this canvas.", [
        el("button", { class: "btn", text: "Sizing", onclick: function () { FM.go("sizing"); } }),
        el("button", { class: "btn btn-primary", text: "Fit to content", onclick: function () { fit(); redraw(); } })
      ]));

    host.appendChild(FM.betaStrip(
      "This is the geometry gate. A model with errors does not pass it. Warnings are the things the " +
      "source plan does not determine — an opening the plan sizes but does not locate, a porch beam " +
      "this model has no element for — and they are listed rather than filled in."));

    /* ---- source bar ---- */
    var srcSel = el("select", { "aria-label": "Geometry source" });
    srcSel.appendChild(el("option", { value: "new|blank", text: "Empty model — draw from scratch" }));
    (FM.weights ? FM.weights.PLANS : []).forEach(function (p) {
      srcSel.appendChild(el("option", { value: "plan|" + p.id, text: "Plan · " + p.name + " — " + p.summary }));
    });
    listLocal().forEach(function (r) {
      srcSel.appendChild(el("option", { value: "saved|" + r.key, text: "Saved · " + r.name + " (" + r.key + ")" }));
    });
    srcSel.value = S.src.kind + "|" + S.src.id;
    srcSel.addEventListener("change", function () {
      var parts = this.value.split("|");
      S.src = { kind: parts[0], id: parts[1] };
      loadSource(true);
      redraw();
      if (FM.syncHash) FM.syncHash(false);
    });

    var tools = el("div", { class: "seg", role: "group", "aria-label": "Drawing tool" },
      TOOLS.map(function (t) {
        return el("button", {
          "data-tool": t.id, text: t.label, title: t.label + " (" + t.key + ") — " + t.hint,
          "aria-pressed": t.id === S.tool ? "true" : "false",
          onclick: function () { setTool(t.id); }
        });
      }));
    TOOLBAR = tools;

    var snapSel = el("select", { "aria-label": "Grid and snap step" }, [
      el("option", { value: "0.25", text: "Grid 3\"" }),
      el("option", { value: "0.5", text: "Grid 6\"" }),
      el("option", { value: "1", text: "Grid 1 ft" }),
      el("option", { value: "2", text: "Grid 2 ft" })
    ]);
    snapSel.value = String(S.snapFt);
    snapSel.addEventListener("change", function () { S.snapFt = num(this.value); redraw(); });

    host.appendChild(el("div", { class: "filter-bar", style: "margin-bottom:12px" }, [
      srcSel, tools, snapSel,
      el("button", { class: "btn btn-sm", text: "Undo", onclick: undo, title: "Ctrl+Z" }),
      el("button", { class: "btn btn-sm", text: "Redo", onclick: redo, title: "Ctrl+Shift+Z" }),
      el("button", { class: "btn btn-sm", text: "Reload source", title: "Discard edits and rebuild from the source",
        onclick: function () {
          if (window.confirm("Rebuild from the source and discard every edit on this canvas?")) {
            loadSource(true); redraw();
          }
        } })
    ]));

    /* ---- stage + panel ---- */
    var stage = el("div", { class: "cad-stage" });
    SVG = document.createElementNS(NS, "svg");
    SVG.setAttribute("class", "cad-svg");
    SVG.setAttribute("tabindex", "0");
    SVG.setAttribute("role", "application");
    SVG.setAttribute("aria-label",
      "Plan drawing canvas. Keyboard: V select, W wall, O opening, R region, P polygon, C calibrate, " +
      "H pan. Arrow keys nudge the selection, Delete removes it, Escape cancels, F fits, G toggles snap.");
    stage.appendChild(SVG);
    HUD = el("div", { class: "cad-hud", "aria-live": "off" });
    stage.appendChild(HUD);
    stage.appendChild(el("div", { class: "cad-drop-note", text: "Drop a PNG or JPG plan here to trace it" }));

    SVG.addEventListener("pointerdown", onDown);
    SVG.addEventListener("pointermove", onMove);
    SVG.addEventListener("pointerup", onUp);
    SVG.addEventListener("pointercancel", function () { drag = null; });
    SVG.addEventListener("wheel", onWheel, { passive: false });
    SVG.addEventListener("keydown", onKey);
    SVG.addEventListener("contextmenu", function (e) { e.preventDefault(); });

    stage.addEventListener("dragover", function (e) { e.preventDefault(); stage.className = "cad-stage is-drop"; });
    stage.addEventListener("dragleave", function () { stage.className = "cad-stage"; });
    stage.addEventListener("drop", function (e) {
      e.preventDefault();
      stage.className = "cad-stage";
      var f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (f) acceptFile(f);
      else toast("Nothing came with that drop. Drag a PNG or JPG file from your file manager.");
    });

    PANEL = el("div", { class: "cad-panel" });
    host.appendChild(el("div", { class: "cad-wrap" }, [stage, PANEL]));

    STATS = el("div", { class: "grid g5", style: "margin-top:14px" });
    host.appendChild(STATS);

    FINDINGS = el("div", { style: "margin-top:14px" });
    host.appendChild(FINDINGS);

    /* ---- shortcuts, persistence, JSON ---- */
    host.appendChild(el("div", { class: "grid g2", style: "margin-top:14px" }, [
      cardShortcuts(), cardStore()
    ]));
    host.appendChild(el("div", { style: "margin-top:14px" }, [cardJson()]));

    /* size the canvas from its box, then draw */
    var box = SVG.getBoundingClientRect();
    VW = Math.max(320, Math.round(box.width || 900));
    VH = Math.max(320, Math.round(box.height || 560));
    SVG.setAttribute("viewBox", "0 0 " + VW + " " + VH);
    if (!MODEL._fitted) { fit(); MODEL._fitted = true; }
    redraw();

    if (window.addEventListener) {
      window.addEventListener("resize", function () {
        if (!SVG || !SVG.parentNode) return;
        var b2 = SVG.getBoundingClientRect();
        if (!b2.width) return;
        VW = Math.round(b2.width); VH = Math.round(b2.height);
        SVG.setAttribute("viewBox", "0 0 " + VW + " " + VH);
        drawCanvas();
      });
    }
  };

  function cardShortcuts() {
    var body = el("div", { class: "cad-keys" });
    var keys = [
      ["V / W / O", "select · wall · opening"],
      ["R / P", "rectangular region · polygon region"],
      ["C / H", "calibrate the underlay · pan"],
      ["drag", "draw a wall; click-click chains wall to wall"],
      ["Shift", "lock the wall orthogonal (it also locks itself within " + RULES.orthoDeg + "°)"],
      ["wheel", "zoom at the cursor · Alt-drag or middle-drag pans"],
      ["arrows", "nudge the selection one grid step · Shift for ten"],
      ["Delete", "remove the selection — a wall takes its openings with it"],
      ["Esc", "cancel the wall, polygon or calibration in progress"],
      ["Enter", "close a polygon region"],
      ["Ctrl+Z / Ctrl+Shift+Z", "undo · redo (" + RULES.undoDepth + " deep)"],
      ["F / G", "fit to content · snap on and off"]
    ];
    keys.forEach(function (k) {
      body.appendChild(el("div", { class: "cad-key" }, [
        el("span", { class: "cad-kbd", text: k[0] }),
        el("span", { text: k[1] })
      ]));
    });
    return card("Keyboard and mouse", null, body,
      "The canvas takes focus when you click it, and it is reachable by Tab");
  }

  function cardStore() {
    var body = el("div", { style: "display:grid;gap:10px" });
    var keyIn = el("input", { type: "text", value: S.saveKey || slug(MODEL.name),
      placeholder: "a short key, e.g. lot-17-plan" });
    body.appendChild(field("Save as", keyIn, "stored in this browser under " + STORE_KEY));
    body.appendChild(el("div", { class: "chips" }, [
      el("button", { class: "chip", text: "Save", onclick: function () {
        var k = slug(keyIn.value);
        if (!k) { toast("Give the model a key first — a short name like lot-17-plan."); return; }
        var r = saveLocal(k, MODEL);
        if (!r.ok) { toast(r.why); return; }
        S.saveKey = k;
        S.src = { kind: "saved", id: k };
        toast("Saved “" + k + "”. It is in this browser only — export the JSON to move it.");
        if (FM.syncHash) FM.syncHash(true);
        FM.go("cad");
      } }),
      el("button", { class: "chip", text: "New empty model", onclick: function () {
        S.src = { kind: "new", id: "blank" };
        loadSource(true); redraw();
        if (FM.syncHash) FM.syncHash(false);
      } })
    ]));
    var saved = listLocal();
    if (!saved.length) {
      body.appendChild(el("p", { class: "clause", text: "Nothing saved in this browser yet." }));
    } else {
      var list = el("div", { class: "dl" });
      saved.forEach(function (r) {
        list.appendChild(el("div", { class: "dl-row" }, [
          el("span", { class: "dl-k", text: r.name + " · " + r.key }),
          el("span", { class: "dl-v" }, [
            el("button", { class: "chip", text: "Load", onclick: function () {
              S.src = { kind: "saved", id: r.key }; loadSource(true); redraw();
              if (FM.syncHash) FM.syncHash(false);
            } }),
            el("button", { class: "chip", text: "Delete", onclick: function () {
              if (!window.confirm("Delete the saved model “" + r.key + "”?")) return;
              removeLocal(r.key);
              toast("Deleted “" + r.key + "”.");
              FM.go("cad");
            } })
          ])
        ]));
      });
      body.appendChild(list);
    }
    return card("Save and load", null, body, "localStorage · this browser, this profile, nothing else");
  }

  function cardJson() {
    var ta = el("textarea", {
      rows: "8", spellcheck: "false", "aria-label": "Model JSON",
      style: "width:100%;font-family:var(--mono);font-size:.76rem;padding:9px;border-radius:var(--r);" +
             "border:1px solid var(--line-strong);background:var(--surface);color:var(--ink)"
    });
    var body = el("div", { style: "display:grid;gap:10px" }, [
      el("div", { class: "chips" }, [
        el("button", { class: "chip", text: "Export into the box", onclick: function () {
          ta.value = toJSON(MODEL);
          toast("The whole model is in the box — " + ta.value.length + " characters. Select all and copy.");
        } }),
        el("button", { class: "chip", text: "Import from the box", onclick: function () {
          if (!ta.value.trim()) { toast("The box is empty. Paste a model JSON into it first."); return; }
          var m;
          try { m = fromJSON(ta.value); }
          catch (err) { toast(err.message); return; }
          pushUndo();
          MODEL = m;
          S.src = { kind: "new", id: "blank" };
          S.sel = null;
          fit(); redraw();
          toast("Imported “" + m.name + "” — " + stats(m).walls + " walls. It is not saved yet.");
        } })
      ]),
      ta
    ]);
    return card("JSON in and out", null, body,
      "The export is the whole model, including what it does not know");
  }

  function slug(s) {
    return String(s || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40);
  }
})();

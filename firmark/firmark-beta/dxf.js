/* ============================================================
   dxf.js — FM.dxf · the CAD model -> AutoCAD DXF

   The product could draw a framing plan on screen and hand out nothing
   but plain text. This file is the other half: the same geometry, in the
   format the architect's AutoCAD reads.

   ---- WHICH DXF, AND WHY --------------------------------------------

   AutoCAD R12 — $ACADVER = AC1009 — ASCII.

   R12 is the last DXF revision before the format grew the parts that
   silently break hand-written files: there is no CLASSES section, no
   OBJECTS section, no root dictionary, no BLOCK_RECORD table, and no
   requirement that every entity carry a unique handle. A file missing
   any one of those in R13+ opens as an empty drawing rather than as an
   error, which is the exact failure this exporter exists to avoid. R12
   is also the widest-read revision in existence: AutoCAD, LibreCAD,
   QCAD, DraftSight, BricsCAD, Illustrator, Inkscape and every online
   viewer read it.

   Two consequences follow, and they are deliberate, not oversights:

     · LWPOLYLINE DOES NOT EXIST IN R12. It arrived in R14 (AC1014).
       Writing an LWPOLYLINE into a file whose header says AC1009 is a
       malformed hybrid — a strict reader drops it and the walls vanish.
       So regions and wall faces are POLYLINE / VERTEX / SEQEND, which
       is what R12 actually defines. Heavier on the wire, correct on
       disk.

     · MTEXT DOES NOT EXIST IN R12 either (R13). All annotation is TEXT,
       one entity per line. TEXT is the more portable entity anyway: it
       has no formatting dialect for a reader to disagree about.

   $INSUNITS and $MEASUREMENT are R13+/R14 header variables. They are
   written anyway: a reader that does not know a header variable skips
   it (the format requires that), and every reader that does know them
   gets the unit answer stated rather than guessed. This is the one
   place where writing forward of the declared version is strictly
   better than not.

   ---- UNITS ---------------------------------------------------------

   The model is decimal feet. This file is written in INCHES:

       1 drawing unit = 1 inch     $INSUNITS = 1
       imperial                    $MEASUREMENT = 0
       architectural display       $LUNITS = 4, $LUPREC = 4 (1/16")

   Inches because US architectural DXF is inches — AutoCAD's own
   imperial templates are 1 unit = 1 inch — so a recipient who inserts
   this file into their architectural drawing gets it at 1:1 instead of
   at 12x. Every coordinate leaves this file through ONE function, so
   the scale cannot be right in one entity and wrong in another.

   ---- WHAT THIS FILE WILL NOT DO ------------------------------------

   It will not invent. A wall with no thickness gets no faces — it gets
   its centreline and a note naming it. A framing region with no
   declared direction gets no direction arrow. A member mark lands on
   the plan ONLY where the takeoff's own derivations name the wall,
   opening or region it came from; every other mark is listed by name
   in the notes as NOT PLACED, with the reason. There is no structural
   grid on S-GRID because the model declares none, and that layer ships
   empty and says so rather than carrying a plausible 10 ft grid that a
   framer would build to.

   And a DXF containing NaN or Infinity is a corrupt file. Every number
   passes through one formatter that refuses non-finite input, and the
   assembled text is scanned again before it is returned. This module
   would rather throw than hand out a file that opens blank.
   ============================================================ */

(function () {
  "use strict";

  var GEN = "Firmark dxf.js 1.0";
  var ACADVER = "AC1009";

  /* ---------------- ES5 helpers ---------------- */

  function isArr(v) { return Object.prototype.toString.call(v) === "[object Array]"; }
  function own(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }
  function fin(v) { return typeof v === "number" && isFinite(v); }

  /* Not an engineering limit — a FORMAT limit. Past about 1e21 units,
     JavaScript's toFixed switches to exponent notation, and several DXF
     readers parse "1e+21" as 1. Anything beyond this is refused BY NAME
     up in readLevel rather than throwing anonymously at write time. */
  var MAX_COORD_FT = 1e12;
  function numOf(v) {
    if (v === null || v === undefined || v === "") return null;
    var n = Number(v);
    return isFinite(n) ? n : null;
  }
  function str(v, dflt) {
    if (v === null || v === undefined) return dflt === undefined ? "" : dflt;
    var s = String(v);
    return s === "" && dflt !== undefined ? dflt : s;
  }

  /* ============================================================
     UNITS

     One conversion, one place. `U()` is the only route from the
     model's feet to the file's units; if it is wrong the whole
     drawing is wrong by the same factor, which is a failure a
     single test catches. Twelve scattered `* 12`s is the failure
     mode where three of them are right.
     ============================================================ */

  var UNITS = {
    "in": { perFt: 12, insunits: 1, lunits: 4, luprec: 4, label: "1 DRAWING UNIT = 1 INCH" },
    "ft": { perFt: 1, insunits: 2, lunits: 2, luprec: 4, label: "1 DRAWING UNIT = 1 FOOT" }
  };

  /* common architectural plot scales, for the label only — the drawing
     itself is 1:1 in real units and carries no scale factor */
  var SCALE_LABEL = {
    "12": "1\" = 1'-0\"", "16": "3/4\" = 1'-0\"", "24": "1/2\" = 1'-0\"",
    "32": "3/8\" = 1'-0\"", "48": "1/4\" = 1'-0\"", "64": "3/16\" = 1'-0\"",
    "96": "1/8\" = 1'-0\"", "192": "1/16\" = 1'-0\""
  };

  /* ============================================================
     TEXT ENCODING

     R12 ASCII DXF carries no encoding declaration, so a byte above
     0x7F means whatever the reader's codepage says it means — which
     is how a note comes back as mojibake in one CAD and as nothing
     in another. Output here is pure ASCII:

       · the typographic characters this codebase actually uses are
         transliterated to their ASCII equivalent, which loses no
         meaning;
       · degree and plus/minus become the DXF control sequences %%d
         and %%p, which R12 defines;
       · anything left becomes \U+XXXX, the escape AutoCAD 2000+ and
         ezdxf read back. A reader that does not know it shows the
         escape — legible and recoverable, unlike a mangled byte.

     Newlines and control characters cannot appear in a DXF value at
     all: they would break the group-code/value pairing and corrupt
     everything after them. They are removed here, and callers that
     have multi-line text emit one TEXT entity per line.
     ============================================================ */

  var TRANSLIT = {
    "·": "-", "•": "-", "–": "-", "—": "--", "−": "-",
    "‘": "'", "’": "'", "“": "\"", "”": "\"",
    "…": "...", "×": "x", " ": " ", "′": "'", "″": "\"",
    "½": "1/2", "¼": "1/4", "¾": "3/4",
    "≤": "<=", "≥": ">=", "≠": "!=", "√": "sqrt",
    "✓": "y", "✗": "x", "→": "->", "←": "<-"
  };

  function encodeText(s) {
    s = String(s === null || s === undefined ? "" : s);
    var out = "", i, ch, code;
    for (i = 0; i < s.length; i++) {
      ch = s.charAt(i);
      code = s.charCodeAt(i);
      if (own(TRANSLIT, ch)) { out += TRANSLIT[ch]; continue; }
      if (ch === "°") { out += "%%d"; continue; }
      if (ch === "±") { out += "%%p"; continue; }
      if (ch === "∅" || ch === "Ø") { out += "%%c"; continue; }
      if (code === 9) { out += "    "; continue; }
      if (code < 32 || code === 127) { out += " "; continue; }   /* incl. \r \n */
      if (code < 127) { out += ch; continue; }
      out += "\\U+" + ("0000" + code.toString(16).toUpperCase()).slice(-4);
    }
    return out;
  }

  /* Layer and linetype names in R12: uppercase, and only letters,
     digits, `$`, `-`, `_`. 31 characters. A name outside that set is
     rejected by AutoCAD's own loader, so it is sanitised here rather
     than shipped and discovered. */
  function cleanName(s) {
    var t = String(s === null || s === undefined ? "" : s).toUpperCase();
    t = t.replace(/[^A-Z0-9$_\-]/g, "-");
    if (t.length > 31) t = t.slice(0, 31);
    if (!t.length) t = "X";
    return t;
  }

  /* ============================================================
     NUMBERS — the refusal point

     Every coordinate, height, radius and angle in the output passes
     through fmt(). A DXF holding "NaN" where a double belongs is a
     corrupt file that most readers open as an empty drawing, so this
     throws rather than writes. Callers guard upstream and name the
     offending entity; this is the backstop that makes "never" true.
     ============================================================ */

  function DxfRefusal(msg, detail) {
    var e = new Error(msg);
    e.name = "DxfRefusal";
    e.dxfRefusal = true;
    e.detail = detail || null;
    return e;
  }

  function fmt(v, where) {
    if (typeof v !== "number" || !isFinite(v)) {
      throw DxfRefusal("dxf.js refused to write a non-finite number (" + String(v) +
                       ") at " + (where || "an unnamed coordinate") +
                       ". A DXF containing NaN or Infinity is a corrupt file.",
                       { value: String(v), where: where || null });
    }
    /* fixed notation only: exponent form ("1e-7") is legal JSON and
       illegal-in-practice for several DXF readers */
    var s = v.toFixed(6);
    if (s.indexOf("e") !== -1 || s.indexOf("E") !== -1) {
      /* toFixed falls back to exponent form at 1e21 and above. Several DXF
         readers parse "1e+21" as 1. A coordinate that large is not a
         building, so this refuses rather than writing a number that will
         be silently misread. */
      throw DxfRefusal("dxf.js refused the coordinate " + String(v) + " at " +
                       (where || "an unnamed coordinate") + ": it is too large to write in the " +
                       "fixed notation DXF readers agree on.", { value: String(v), where: where || null });
    }
    /* trim trailing zeros but keep a decimal point — DXF reals are doubles */
    if (s.indexOf(".") !== -1) {
      s = s.replace(/0+$/, "");
      if (s.charAt(s.length - 1) === ".") s += "0";
    }
    if (s === "-0.0") s = "0.0";
    return s;
  }

  /* ============================================================
     FEET-AND-INCHES

     For dimension text and for anything a framer reads. Rounds to
     1/16" and reduces the fraction. Returns null — never a guess —
     for a value that is not a finite number, so the caller declines
     to draw the dimension rather than drawing "NaN'-NaN"".
     ============================================================ */

  function ftIn(feet) {
    var f = numOf(feet);
    if (f === null) return null;
    var neg = f < 0;
    var totalSixteenths = Math.round(Math.abs(f) * 192);   /* 12 * 16 */
    var ft = Math.floor(totalSixteenths / 192);
    var rem = totalSixteenths - ft * 192;
    var inch = Math.floor(rem / 16);
    var six = rem - inch * 16;
    var frac = "";
    if (six > 0) {
      var n = six, d = 16;
      while (n % 2 === 0 && d % 2 === 0) { n /= 2; d /= 2; }
      frac = " " + n + "/" + d;
    }
    return (neg ? "-" : "") + ft + "'-" + inch + frac + "\"";
  }

  /* ============================================================
     THE LAYER SCHEME

     AIA CAD Layer Guidelines shape — DISCIPLINE-MAJOR-MINOR-STATUS —
     so a recipient can freeze by wildcard: `S-WALL-*` is every wall,
     `*-NBRG-*` is everything non-bearing, `S-ANNO-*` is every scrap
     of annotation. The structural split the drawing exists to make —
     BEARING against NON-BEARING — is a layer, not a lineweight,
     because a lineweight cannot be turned off and a wrong reading of
     one is a wrong reading of the structure.

     Every layer below is written to the file whether or not anything
     lands on it. An empty layer that is PRESENT tells the recipient
     the exporter had nothing to put there; an absent layer tells them
     nothing at all, and S-GRID in particular is empty on purpose.
     ============================================================ */

  var LAYERS = [
    { name: "0",                color: 7,   lt: "CONTINUOUS", what: "DXF requires it. Left empty deliberately." },
    { name: "S-WALL-BRNG-EXTR", color: 1,   lt: "CONTINUOUS", what: "BEARING exterior wall - both faces" },
    { name: "S-WALL-BRNG-INTR", color: 12,  lt: "CONTINUOUS", what: "BEARING interior wall - both faces" },
    { name: "S-WALL-NBRG-EXTR", color: 8,   lt: "CONTINUOUS", what: "Non-bearing exterior wall - both faces" },
    { name: "S-WALL-NBRG-INTR", color: 9,   lt: "CONTINUOUS", what: "Non-bearing interior wall - both faces" },
    { name: "S-WALL-CNTR",      color: 251, lt: "CENTER",     what: "Wall centreline - the line the model actually stores" },
    { name: "S-WALL-IDEN",      color: 7,   lt: "CONTINUOUS", what: "Wall id text" },
    { name: "S-OPNG",           color: 2,   lt: "CONTINUOUS", what: "Openings - jambs and rough opening" },
    { name: "S-OPNG-IDEN",      color: 2,   lt: "CONTINUOUS", what: "Opening id, kind and width text" },
    { name: "S-FRAM-RGN",       color: 3,   lt: "DASHED",     what: "Framed region boundary" },
    { name: "S-FRAM-DIRN",      color: 4,   lt: "CONTINUOUS", what: "Framing span-direction indicator" },
    { name: "S-FRAM-IDEN",      color: 3,   lt: "CONTINUOUS", what: "Framed region label - kind, spacing, direction" },
    { name: "S-ANNO-MARK",      color: 5,   lt: "CONTINUOUS", what: "Member marks and their selected members" },
    { name: "S-ANNO-DIMS",      color: 6,   lt: "CONTINUOUS", what: "Dimensions (exploded geometry, not associative)" },
    { name: "S-ANNO-NOTE",      color: 7,   lt: "CONTINUOUS", what: "General notes, provenance and everything undetermined" },
    { name: "S-ANNO-TTLB",      color: 7,   lt: "CONTINUOUS", what: "Title block" },
    { name: "S-ANNO-SEAL",      color: 1,   lt: "CONTINUOUS", what: "PE seal block - INTENTIONALLY EMPTY" },
    { name: "S-ANNO-NORT",      color: 7,   lt: "CONTINUOUS", what: "North arrow - ASSUMED, see notes" },
    { name: "S-ANNO-LEGN",      color: 7,   lt: "CONTINUOUS", what: "Legend" },
    { name: "S-ANNO-SCLE",      color: 7,   lt: "CONTINUOUS", what: "Graphic scale" },
    { name: "S-GRID",           color: 253, lt: "CENTER",     what: "Structural grid - EMPTY: this model declares no grid" }
  ];

  var LT = [
    { name: "CONTINUOUS", desc: "Solid line", pat: [] },
    { name: "DASHED",     desc: "Dashed __ __ __ __ __ __ __ __", pat: [0.5, -0.25] },
    { name: "CENTER",     desc: "Center ____ _ ____ _ ____ _ ____", pat: [1.25, -0.25, 0.25, -0.25] },
    { name: "HIDDEN",     desc: "Hidden __ __ __ __ __ __ __ __", pat: [0.25, -0.125] },
    { name: "PHANTOM",    desc: "Phantom ___ _ _ ___ _ _ ___ _ _", pat: [1.25, -0.25, 0.25, -0.25, 0.25, -0.25] }
  ];

  function layerNames() { return LAYERS.map(function (l) { return l.name; }); }
  function layerScheme() {
    return LAYERS.map(function (l) {
      return { name: l.name, color: l.color, linetype: l.lt, what: l.what };
    });
  }

  /* ============================================================
     THE ENTITY BUFFER

     Entities are built as plain objects first and serialised last,
     for two reasons that both matter:

       1. $EXTMIN / $EXTMAX are measured from THE ENTITIES ACTUALLY
          WRITTEN, not from the model's bounding box. The title
          block, the notes and the dimension strings all sit outside
          the geometry; extents taken off the model would cut them
          off, and a drawing that opens with its own title block off
          screen is the second-most-common complaint after opening
          blank.

       2. an entity can be counted, and a count can be asserted
          against the model.
     ============================================================ */

  function Buf() {
    this.ents = [];
    this.minX = null; this.minY = null; this.maxX = null; this.maxY = null;
    this.counts = {};
  }
  Buf.prototype.see = function (x, y) {
    if (!fin(x) || !fin(y)) return;
    if (this.minX === null || x < this.minX) this.minX = x;
    if (this.maxX === null || x > this.maxX) this.maxX = x;
    if (this.minY === null || y < this.minY) this.minY = y;
    if (this.maxY === null || y > this.maxY) this.maxY = y;
  };
  Buf.prototype.push = function (e) {
    this.counts[e.t] = (this.counts[e.t] || 0) + 1;
    this.ents.push(e);
    return e;
  };
  /* `look` is an optional {color, ltype} override, used ONLY by the legend
     so a swatch can be drawn in a wall's colour without being a wall. A
     swatch living on S-WALL-BRNG-EXTR would be counted as a bearing wall
     by anything reading quantities off this file — a phantom wall in the
     legend is still a phantom wall. */
  Buf.prototype.line = function (layer, x1, y1, x2, y2, where, look) {
    if (!fin(x1) || !fin(y1) || !fin(x2) || !fin(y2)) {
      throw DxfRefusal("dxf.js refused a LINE with a non-finite endpoint on " + layer +
                       " at " + (where || "an unnamed line"), { where: where || null });
    }
    this.see(x1, y1); this.see(x2, y2);
    return this.push({ t: "LINE", layer: layer, x1: x1, y1: y1, x2: x2, y2: y2,
                       color: look ? look.color : null, ltype: look ? look.ltype : null });
  };
  Buf.prototype.pline = function (layer, pts, closed, where) {
    var i;
    if (!isArr(pts) || pts.length < 2) {
      throw DxfRefusal("dxf.js refused a POLYLINE with fewer than 2 vertices at " +
                       (where || "an unnamed polyline"), { where: where || null });
    }
    for (i = 0; i < pts.length; i++) {
      if (!fin(pts[i][0]) || !fin(pts[i][1])) {
        throw DxfRefusal("dxf.js refused a POLYLINE with a non-finite vertex on " + layer +
                         " at " + (where || "an unnamed polyline"), { where: where || null });
      }
      this.see(pts[i][0], pts[i][1]);
    }
    return this.push({ t: "POLYLINE", layer: layer, pts: pts, closed: !!closed });
  };
  Buf.prototype.circle = function (layer, x, y, r, where) {
    if (!fin(x) || !fin(y) || !fin(r) || r <= 0) {
      throw DxfRefusal("dxf.js refused a CIRCLE with a non-finite or non-positive value on " +
                       layer + " at " + (where || "an unnamed circle"), { where: where || null });
    }
    this.see(x - r, y - r); this.see(x + r, y + r);
    return this.push({ t: "CIRCLE", layer: layer, x: x, y: y, r: r });
  };
  /* just: 0 left, 1 centre, 2 right.  rot: degrees. */
  Buf.prototype.text = function (layer, x, y, h, s, just, rot, where) {
    if (!fin(x) || !fin(y) || !fin(h) || h <= 0) {
      throw DxfRefusal("dxf.js refused a TEXT with a non-finite position or height on " +
                       layer + " at " + (where || "an unnamed label"), { where: where || null });
    }
    rot = fin(rot) ? rot : 0;
    just = (just === 1 || just === 2) ? just : 0;
    var body = encodeText(s);
    /* an approximate ink box, so extents cover the words and not just
       their insertion points. txt.shx runs about 0.62em wide. */
    var w = body.length * h * 0.62;
    var rad = rot * Math.PI / 180, cs = Math.cos(rad), sn = Math.sin(rad);
    var x0 = x - (just === 1 ? w / 2 : just === 2 ? w : 0);
    this.see(x, y);
    this.see(x0 + w * cs, y + w * sn);
    this.see(x0 - h * sn, y + h * cs);
    this.see(x0 + w * cs - h * sn, y + w * sn + h * cs);
    return this.push({ t: "TEXT", layer: layer, x: x, y: y, h: h, s: body, just: just, rot: rot });
  };

  /* ============================================================
     SERIALISATION
     ============================================================ */

  function W(L, code, value) { L.push(String(code)); L.push(value); }
  function Wn(L, code, value, where) { L.push(String(code)); L.push(fmt(value, where)); }

  function writeEntity(L, e) {
    var i;
    if (e.t === "LINE") {
      W(L, 0, "LINE"); W(L, 8, e.layer);
      if (e.ltype) W(L, 6, e.ltype);
      if (e.color !== null && e.color !== undefined) W(L, 62, String(e.color));
      Wn(L, 10, e.x1, "LINE.10"); Wn(L, 20, e.y1, "LINE.20"); Wn(L, 30, 0, "LINE.30");
      Wn(L, 11, e.x2, "LINE.11"); Wn(L, 21, e.y2, "LINE.21"); Wn(L, 31, 0, "LINE.31");
      return;
    }
    if (e.t === "CIRCLE") {
      W(L, 0, "CIRCLE"); W(L, 8, e.layer);
      Wn(L, 10, e.x, "CIRCLE.10"); Wn(L, 20, e.y, "CIRCLE.20"); Wn(L, 30, 0, "CIRCLE.30");
      Wn(L, 40, e.r, "CIRCLE.40");
      return;
    }
    if (e.t === "TEXT") {
      W(L, 0, "TEXT"); W(L, 8, e.layer);
      Wn(L, 10, e.x, "TEXT.10"); Wn(L, 20, e.y, "TEXT.20"); Wn(L, 30, 0, "TEXT.30");
      Wn(L, 40, e.h, "TEXT.40");
      W(L, 1, e.s);
      Wn(L, 50, e.rot, "TEXT.50");
      W(L, 7, "STANDARD");
      W(L, 72, String(e.just));
      /* THE TRAP: with 72 non-zero the reader uses the ALIGNMENT point
         (11/21/31), not the insertion point, and a writer that omits it
         drops the text at the origin. Both are written, always. */
      Wn(L, 11, e.x, "TEXT.11"); Wn(L, 21, e.y, "TEXT.21"); Wn(L, 31, 0, "TEXT.31");
      return;
    }
    if (e.t === "POLYLINE") {
      W(L, 0, "POLYLINE"); W(L, 8, e.layer);
      W(L, 66, "1");                       /* vertices follow — required in R12 */
      Wn(L, 10, 0, "POLYLINE.10"); Wn(L, 20, 0, "POLYLINE.20"); Wn(L, 30, 0, "POLYLINE.30");
      W(L, 70, e.closed ? "1" : "0");
      for (i = 0; i < e.pts.length; i++) {
        W(L, 0, "VERTEX"); W(L, 8, e.layer);
        Wn(L, 10, e.pts[i][0], "VERTEX.10"); Wn(L, 20, e.pts[i][1], "VERTEX.20");
        Wn(L, 30, 0, "VERTEX.30");
      }
      W(L, 0, "SEQEND"); W(L, 8, e.layer);
      return;
    }
    throw DxfRefusal("dxf.js does not know how to write entity type " + String(e.t));
  }

  function writeHeader(L, hd) {
    W(L, 0, "SECTION"); W(L, 2, "HEADER");

    W(L, 9, "$ACADVER");     W(L, 1, ACADVER);
    W(L, 9, "$INSBASE");     Wn(L, 10, 0, "$INSBASE"); Wn(L, 20, 0, "$INSBASE"); Wn(L, 30, 0, "$INSBASE");
    W(L, 9, "$EXTMIN");      Wn(L, 10, hd.extMinX, "$EXTMIN.x"); Wn(L, 20, hd.extMinY, "$EXTMIN.y"); Wn(L, 30, 0, "$EXTMIN.z");
    W(L, 9, "$EXTMAX");      Wn(L, 10, hd.extMaxX, "$EXTMAX.x"); Wn(L, 20, hd.extMaxY, "$EXTMAX.y"); Wn(L, 30, 0, "$EXTMAX.z");
    W(L, 9, "$LIMMIN");      Wn(L, 10, hd.limMinX, "$LIMMIN.x"); Wn(L, 20, hd.limMinY, "$LIMMIN.y");
    W(L, 9, "$LIMMAX");      Wn(L, 10, hd.limMaxX, "$LIMMAX.x"); Wn(L, 20, hd.limMaxY, "$LIMMAX.y");
    W(L, 9, "$ORTHOMODE");   W(L, 70, "0");
    W(L, 9, "$REGENMODE");   W(L, 70, "1");
    W(L, 9, "$FILLMODE");    W(L, 70, "1");
    W(L, 9, "$QTEXTMODE");   W(L, 70, "0");
    W(L, 9, "$MIRRTEXT");    W(L, 70, "0");
    W(L, 9, "$LTSCALE");     Wn(L, 40, hd.ltScale, "$LTSCALE");
    W(L, 9, "$TEXTSIZE");    Wn(L, 40, hd.textSize, "$TEXTSIZE");
    W(L, 9, "$TRACEWID");    Wn(L, 40, hd.textSize / 4, "$TRACEWID");
    W(L, 9, "$TEXTSTYLE");   W(L, 7, "STANDARD");
    W(L, 9, "$CLAYER");      W(L, 8, "0");
    W(L, 9, "$CELTYPE");     W(L, 6, "BYLAYER");
    W(L, 9, "$CECOLOR");     W(L, 62, "256");
    W(L, 9, "$DIMSCALE");    Wn(L, 40, hd.plotScale, "$DIMSCALE");
    W(L, 9, "$DIMTXT");      Wn(L, 40, hd.textSize, "$DIMTXT");
    /* the unit declaration — the single most consequential block in this
       file. Getting it wrong opens the drawing at 12x or 1/12. */
    W(L, 9, "$LUNITS");      W(L, 70, String(hd.lunits));
    W(L, 9, "$LUPREC");      W(L, 70, String(hd.luprec));
    W(L, 9, "$AUNITS");      W(L, 70, "0");
    W(L, 9, "$AUPREC");      W(L, 70, "2");
    W(L, 9, "$INSUNITS");    W(L, 70, String(hd.insunits));
    W(L, 9, "$MEASUREMENT"); W(L, 70, "0");        /* 0 = imperial */
    W(L, 9, "$PDMODE");      W(L, 70, "34");
    W(L, 9, "$PDSIZE");      Wn(L, 40, hd.textSize / 2, "$PDSIZE");
    W(L, 9, "$TILEMODE");    W(L, 70, "1");        /* open in model space */
    W(L, 9, "$HANDLING");    W(L, 70, "0");        /* no handles in this file */

    W(L, 0, "ENDSEC");
  }

  function writeTables(L, hd) {
    var i, j;
    W(L, 0, "SECTION"); W(L, 2, "TABLES");

    /* ---- VPORT. *ACTIVE is what makes a reader open ZOOMED TO THE
       DRAWING instead of at the origin with the house off screen. It
       is centred on, and sized to, the same extents the header
       declares. ---- */
    W(L, 0, "TABLE"); W(L, 2, "VPORT"); W(L, 70, "1");
    W(L, 0, "VPORT"); W(L, 2, "*ACTIVE"); W(L, 70, "0");
    Wn(L, 10, 0, "VPORT.10"); Wn(L, 20, 0, "VPORT.20");
    Wn(L, 11, 1, "VPORT.11"); Wn(L, 21, 1, "VPORT.21");
    Wn(L, 12, hd.viewCX, "VPORT.12"); Wn(L, 22, hd.viewCY, "VPORT.22");
    Wn(L, 13, 0, "VPORT.13"); Wn(L, 23, 0, "VPORT.23");
    Wn(L, 14, hd.snap, "VPORT.14"); Wn(L, 24, hd.snap, "VPORT.24");
    Wn(L, 15, hd.snap, "VPORT.15"); Wn(L, 25, hd.snap, "VPORT.25");
    Wn(L, 16, 0, "VPORT.16"); Wn(L, 26, 0, "VPORT.26"); Wn(L, 36, 1, "VPORT.36");
    Wn(L, 17, 0, "VPORT.17"); Wn(L, 27, 0, "VPORT.27"); Wn(L, 37, 0, "VPORT.37");
    Wn(L, 40, hd.viewH, "VPORT.40");
    Wn(L, 41, hd.aspect, "VPORT.41");
    Wn(L, 42, 50, "VPORT.42");
    Wn(L, 43, 0, "VPORT.43"); Wn(L, 44, 0, "VPORT.44");
    Wn(L, 50, 0, "VPORT.50"); Wn(L, 51, 0, "VPORT.51");
    W(L, 71, "0"); W(L, 72, "100"); W(L, 73, "1"); W(L, 74, "3");
    W(L, 75, "0"); W(L, 76, "0"); W(L, 77, "0"); W(L, 78, "0");
    W(L, 0, "ENDTAB");

    /* ---- LTYPE. Every linetype a LAYER names must exist here, or the
       layer is rejected and every entity on it goes with it. ---- */
    W(L, 0, "TABLE"); W(L, 2, "LTYPE"); W(L, 70, String(LT.length));
    for (i = 0; i < LT.length; i++) {
      var lt = LT[i], total = 0;
      for (j = 0; j < lt.pat.length; j++) total += Math.abs(lt.pat[j]);
      W(L, 0, "LTYPE"); W(L, 2, lt.name); W(L, 70, "0");
      W(L, 3, encodeText(lt.desc));
      W(L, 72, "65");                       /* 'A' alignment */
      W(L, 73, String(lt.pat.length));
      Wn(L, 40, total, "LTYPE." + lt.name + ".40");
      for (j = 0; j < lt.pat.length; j++) Wn(L, 49, lt.pat[j], "LTYPE." + lt.name + ".49");
    }
    W(L, 0, "ENDTAB");

    /* ---- LAYER ---- */
    W(L, 0, "TABLE"); W(L, 2, "LAYER"); W(L, 70, String(LAYERS.length));
    for (i = 0; i < LAYERS.length; i++) {
      W(L, 0, "LAYER"); W(L, 2, LAYERS[i].name); W(L, 70, "0");
      W(L, 62, String(LAYERS[i].color));
      W(L, 6, LAYERS[i].lt);
    }
    W(L, 0, "ENDTAB");

    /* ---- STYLE. TEXT names style STANDARD; a TEXT naming a style that
       is not in this table is a dangling reference. ---- */
    W(L, 0, "TABLE"); W(L, 2, "STYLE"); W(L, 70, "1");
    W(L, 0, "STYLE"); W(L, 2, "STANDARD"); W(L, 70, "0");
    Wn(L, 40, 0, "STYLE.40");          /* 0 = height not fixed */
    Wn(L, 41, 1, "STYLE.41");          /* width factor */
    Wn(L, 50, 0, "STYLE.50");          /* oblique */
    W(L, 71, "0");
    Wn(L, 42, hd.textSize, "STYLE.42");
    W(L, 3, "txt");
    W(L, 4, "");
    W(L, 0, "ENDTAB");

    /* ---- VIEW / UCS / APPID / DIMSTYLE: present and empty. R12 readers
       accept their absence, but several older ones assume the table set
       exists; an empty table costs six lines and removes the question. ---- */
    W(L, 0, "TABLE"); W(L, 2, "VIEW"); W(L, 70, "0"); W(L, 0, "ENDTAB");
    W(L, 0, "TABLE"); W(L, 2, "UCS"); W(L, 70, "0"); W(L, 0, "ENDTAB");
    W(L, 0, "TABLE"); W(L, 2, "APPID"); W(L, 70, "1");
    W(L, 0, "APPID"); W(L, 2, "ACAD"); W(L, 70, "0");
    W(L, 0, "ENDTAB");

    W(L, 0, "ENDSEC");
  }

  /* ============================================================
     THE FINAL SCAN

     fmt() already refuses non-finite numbers at the point of writing.
     This reads the assembled file back and refuses again, because the
     guarantee being made — "this exporter never emits NaN" — is worth
     more than the microseconds. It checks the VALUE line of every
     numeric group code, so the word "Infinity" inside somebody's note
     is not mistaken for a corrupt coordinate.
     ============================================================ */

  var NUMERIC_CODE = /^(1[0-9]|2[0-9]|3[0-7]|4[0-9]|5[0-8]|140|14[1-7]|21[0-3])$/;

  function scanNumeric(lines) {
    var bad = [];
    for (var i = 0; i + 1 < lines.length; i += 2) {
      var code = lines[i], val = lines[i + 1];
      if (!NUMERIC_CODE.test(code)) continue;
      if (!/^-?(\d+\.?\d*|\.\d+)$/.test(val)) bad.push({ at: i, code: code, value: val });
    }
    return bad;
  }

  /* ============================================================
     GEOMETRY HELPERS
     ============================================================ */

  function len2(dx, dy) { return Math.sqrt(dx * dx + dy * dy); }

  function polyCentroid(pts) {
    /* area centroid where the polygon has area, vertex mean where it
       does not (a degenerate sliver still needs a label position, and
       the mean of its own vertices is not an invented point) */
    var n = pts.length, i, a = 0, cx = 0, cy = 0, j, cross;
    for (i = 0; i < n; i++) {
      j = (i + 1) % n;
      cross = pts[i][0] * pts[j][1] - pts[j][0] * pts[i][1];
      a += cross; cx += (pts[i][0] + pts[j][0]) * cross; cy += (pts[i][1] + pts[j][1]) * cross;
    }
    a = a / 2;
    if (Math.abs(a) > 1e-9) return [cx / (6 * a), cy / (6 * a)];
    var sx = 0, sy = 0;
    for (i = 0; i < n; i++) { sx += pts[i][0]; sy += pts[i][1]; }
    return [sx / n, sy / n];
  }

  function bboxOf(pts) {
    var b = { minX: pts[0][0], maxX: pts[0][0], minY: pts[0][1], maxY: pts[0][1] };
    for (var i = 1; i < pts.length; i++) {
      if (pts[i][0] < b.minX) b.minX = pts[i][0];
      if (pts[i][0] > b.maxX) b.maxX = pts[i][0];
      if (pts[i][1] < b.minY) b.minY = pts[i][1];
      if (pts[i][1] > b.maxY) b.maxY = pts[i][1];
    }
    return b;
  }

  /* ============================================================
     READING THE MODEL

     Nothing here repairs anything. A value that is not a finite
     number stays null and the entity that needed it is not drawn;
     the reason lands in `refusals`, which is printed on S-ANNO-NOTE
     and returned to the caller. The rule this codebase runs on is
     that a thing which could not be drawn says so by name.
     ============================================================ */

  function readLevel(lv, refuse) {
    var L = { id: str(lv && lv.id, "(level)"), label: str(lv && lv.label, str(lv && lv.id, "(level)")),
              topPlateFt: numOf(lv && lv.topPlateFt),
              walls: [], openings: [], framing: [], wallById: {} };
    var walls = (lv && isArr(lv.walls)) ? lv.walls : [];
    var opens = (lv && isArr(lv.openings)) ? lv.openings : [];
    var frams = (lv && isArr(lv.framing)) ? lv.framing : [];

    walls.forEach(function (w, i) {
      if (!w) { refuse("wall #" + (i + 1) + " on level " + L.id, "the entry is null"); return; }
      var id = str(w.id, "(wall " + (i + 1) + ")");
      var x1 = numOf(w.x1), y1 = numOf(w.y1), x2 = numOf(w.x2), y2 = numOf(w.y2);
      var rec = {
        id: id, x1: x1, y1: y1, x2: x2, y2: y2,
        bearing: !!w.bearing, exterior: !!w.exterior,
        thicknessIn: numOf(w.thicknessIn),
        thicknessBasis: str(w.thicknessBasis, ""),
        note: str(w.note, ""), drawable: false, lengthFt: null, ux: 0, uy: 0, nx: 0, ny: 0
      };
      if (x1 === null || y1 === null || x2 === null || y2 === null) {
        refuse("wall " + id + " (level " + L.id + ")",
               "one or more endpoint coordinates are not finite numbers - nothing about this wall is drawn");
      } else if (Math.max(Math.abs(x1), Math.abs(y1), Math.abs(x2), Math.abs(y2)) > MAX_COORD_FT) {
        rec.x1 = rec.y1 = rec.x2 = rec.y2 = null;
        refuse("wall " + id + " (level " + L.id + ")",
               "a coordinate is beyond " + MAX_COORD_FT + " ft, which cannot be written in the fixed " +
               "decimal notation DXF readers agree on - the wall is not drawn rather than written in a " +
               "form a reader would parse as some other number");
      } else if (len2(x2 - x1, y2 - y1) <= 0) {
        refuse("wall " + id + " (level " + L.id + ")",
               "start and end are the same point, so the wall has zero length and no direction");
      } else {
        rec.drawable = true;
        rec.lengthFt = len2(x2 - x1, y2 - y1);
        rec.ux = (x2 - x1) / rec.lengthFt; rec.uy = (y2 - y1) / rec.lengthFt;
        rec.nx = -rec.uy; rec.ny = rec.ux;
        if (rec.thicknessIn === null || rec.thicknessIn <= 0) {
          refuse("wall " + id + " (level " + L.id + ")",
                 "no usable thickness (thicknessIn = " + str(w.thicknessIn, "absent") +
                 "), so its FACES ARE NOT DRAWN. Only its centreline is, on S-WALL-CNTR. " +
                 "This exporter does not assume a stud size.");
        }
      }
      L.walls.push(rec);
      if (!own(L.wallById, " " + id)) L.wallById[" " + id] = rec;
    });

    opens.forEach(function (o, i) {
      if (!o) { refuse("opening #" + (i + 1) + " on level " + L.id, "the entry is null"); return; }
      var id = str(o.id, "(opening " + (i + 1) + ")");
      var host = own(L.wallById, " " + str(o.wallId)) ? L.wallById[" " + str(o.wallId)] : null;
      var off = numOf(o.offsetFt), wid = numOf(o.widthFt);
      var rec = {
        id: id, wallId: str(o.wallId, "-"), kind: str(o.kind, "-"),
        offsetFt: off, widthFt: wid, headHeightFt: numOf(o.headHeightFt),
        offsetBasis: str(o.offsetBasis, ""), host: host, at: null, drawable: false
      };
      if (!host) {
        refuse("opening " + id + " (level " + L.id + ")",
               "names wall \"" + rec.wallId + "\", which is not on this level - it cannot be located");
      } else if (!host.drawable) {
        refuse("opening " + id + " (level " + L.id + ")",
               "its host wall " + host.id + " is not drawable, so the opening has no position");
      } else if (off === null || wid === null) {
        refuse("opening " + id + " (level " + L.id + ")",
               "offsetFt or widthFt is not a finite number, so its position along " + host.id + " is undetermined");
      } else if (wid <= 0) {
        refuse("opening " + id + " (level " + L.id + ")", "widthFt is " + wid + " - not a rough opening");
      } else {
        rec.drawable = true;
        rec.at = { x: host.x1 + host.ux * (off + wid / 2), y: host.y1 + host.uy * (off + wid / 2) };
        if (off < 0 || off + wid > host.lengthFt + 1e-6) {
          refuse("opening " + id + " (level " + L.id + ")",
                 "runs from " + off.toFixed(2) + " ft to " + (off + wid).toFixed(2) +
                 " ft along " + host.id + ", which is " + host.lengthFt.toFixed(2) +
                 " ft long - it is DRAWN WHERE THE MODEL PUTS IT, off the end of its wall, not clipped to fit");
        }
      }
      L.openings.push(rec);
    });

    frams.forEach(function (f, i) {
      if (!f) { refuse("framing region #" + (i + 1) + " on level " + L.id, "the entry is null"); return; }
      var id = str(f.id, "(region " + (i + 1) + ")");
      var raw = isArr(f.polygon) ? f.polygon : [];
      var pts = [], dropped = 0;
      raw.forEach(function (p) {
        if (!isArr(p) || p.length < 2) { dropped++; return; }
        var x = numOf(p[0]), y = numOf(p[1]);
        if (x === null || y === null) { dropped++; return; }
        pts.push([x, y]);
      });
      var rec = {
        id: id, kind: str(f.kind, "-"), pts: pts,
        directionDeg: numOf(f.directionDeg), spacingIn: numOf(f.spacingIn),
        system: str(f.system, ""), bearsOn: isArr(f.bearsOn) ? f.bearsOn.map(function (b) { return str(b); }) : [],
        note: str(f.note, ""), at: null, drawable: false
      };
      if (dropped) {
        refuse("framing region " + id + " (level " + L.id + ")",
               dropped + " of " + raw.length + " polygon points are not finite pairs and were not drawn - " +
               "the boundary shown is INCOMPLETE");
      }
      if (pts.length < 3) {
        refuse("framing region " + id + " (level " + L.id + ")",
               "fewer than 3 usable polygon points, so no region boundary is drawn");
      } else {
        rec.drawable = true;
        rec.at = polyCentroid(pts);
      }
      if (rec.directionDeg === null) {
        refuse("framing region " + id + " (level " + L.id + ")",
               "declares no framing direction, so NO SPAN-DIRECTION ARROW IS DRAWN for it");
      }
      if (rec.spacingIn === null) {
        refuse("framing region " + id + " (level " + L.id + ")",
               "declares no spacing, so its label reads SPACING NOT DECLARED rather than a number");
      }
      L.framing.push(rec);
    });

    return L;
  }

  /* ============================================================
     MARK PLACEMENT

     A mark is placed where the TAKEOFF'S OWN DERIVATIONS say it came
     from, and nowhere else. `fromIds` is structured and is read
     first; the prose `from` is scanned only when `fromIds` names
     nothing this drawing carries, and it is matched on whole tokens
     so W1 cannot match W11.

     Search order is opening, then framing region, then wall, because
     that is the order of specificity. A header drawn at the centroid
     of the whole roof is not slightly wrong, it is on the wrong part
     of the house.

     A mark whose derivations name nothing is NOT DRAWN. It goes to
     the notes by name. A mark box at a plausible-looking spot is a
     lie a plan reviewer has no way to detect.
     ============================================================ */

  /* `lead` is the direction a mark tag is nudged off its anchor so it does
     not sit on top of the thing it labels, plus how far the wall itself
     occupies. The ANCHOR is exact; only the tag moves, and a leader line
     is drawn back to the anchor so the pairing stays unambiguous. */
  function buildIndex(levels) {
    var index = {}, order = [];
    function put(id, at, levelIdx, on, lead) {
      if (!at || own(index, " " + id)) return;
      index[" " + id] = { at: at, level: levelIdx, on: on, lead: lead || null };
      order.push(id);
    }
    levels.forEach(function (L, li) {
      L.openings.forEach(function (o) {
        if (!o.drawable) return;
        var w = o.host;
        put(o.id, o.at, li, "opening " + o.id,
            { nx: w.nx, ny: w.ny,
              clearFt: (w.thicknessIn !== null && w.thicknessIn > 0) ? (w.thicknessIn / 2) / 12 : 0 });
      });
    });
    levels.forEach(function (L, li) {
      L.framing.forEach(function (f) { if (f.drawable) put(f.id, { x: f.at[0], y: f.at[1] }, li, "framing region " + f.id); });
    });
    levels.forEach(function (L, li) {
      L.walls.forEach(function (w) {
        if (!w.drawable) return;
        put(w.id, { x: (w.x1 + w.x2) / 2, y: (w.y1 + w.y2) / 2 }, li, "wall " + w.id,
            { nx: w.nx, ny: w.ny,
              clearFt: (w.thicknessIn !== null && w.thicknessIn > 0) ? (w.thicknessIn / 2) / 12 : 0 });
      });
    });
    return { index: index, order: order };
  }

  function tokenHit(index, order, text) {
    if (!text) return null;
    for (var i = 0; i < order.length; i++) {
      var key = order[i];
      if (text.indexOf(key) === -1) continue;
      var re = new RegExp("(^|[^A-Za-z0-9_-])" + key.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") +
                          "([^A-Za-z0-9_-]|$)");
      if (re.test(text)) return index[" " + key];
    }
    return null;
  }

  function placeMarks(levels, takeoff) {
    var idx = buildIndex(levels);
    var out = { placed: [], unplaced: [], basis: "" };
    var marks = (takeoff && isArr(takeoff.marks)) ? takeoff.marks : null;
    var derivs = (takeoff && isArr(takeoff.derivations)) ? takeoff.derivations : null;

    if (!marks || !marks.length) {
      out.basis = "no takeoff was supplied, so this drawing carries geometry and NO MEMBER MARKS";
      return out;
    }
    if (!derivs) {
      out.basis = "a takeoff was supplied with no derivations, so nothing says where any mark sits";
      marks.forEach(function (m) {
        out.unplaced.push({ id: str(m && m.id, "(mark)"),
          why: "the takeoff supplied no derivations, so nothing says where this mark sits on the plan" });
      });
      return out;
    }
    out.basis = "each mark is placed where the takeoff's own derivations say its numbers came from";

    marks.forEach(function (m) {
      var id = str(m && m.id, "");
      if (!id) return;
      var hit = null, how = "";
      for (var i = 0; i < derivs.length && !hit; i++) {
        var d = derivs[i];
        if (!d || str(d.markId) !== id) continue;
        if (isArr(d.fromIds)) {
          for (var j = 0; j < d.fromIds.length && !hit; j++) {
            var k = " " + str(d.fromIds[j]);
            if (own(idx.index, k)) { hit = idx.index[k]; }
          }
        }
        if (!hit) hit = tokenHit(idx.index, idx.order, str(d.from, ""));
        if (!hit) hit = tokenHit(idx.index, idx.order, str(d.how, ""));
        if (hit) how = str(d.field, "") + (d.field ? " " : "") + "from " + str(d.from, "the takeoff");
      }
      if (hit) out.placed.push({ id: id, mark: m, x: hit.at.x, y: hit.at.y, level: hit.level,
                                 on: hit.on, how: how, lead: hit.lead });
      else out.unplaced.push({ id: id,
        why: "no takeoff derivation names a wall, opening or framing region for this mark, " +
             "so this drawing does not know where it belongs" });
    });
    return out;
  }

  /* selected member text for a mark, from a solver result — matched by
     mark id and NEVER guessed. A mark the calculations do not carry says
     so on the drawing. */
  function memberIndex(calcs) {
    var out = { has: false, byId: {}, count: 0 };
    if (!calcs || !isArr(calcs.marks)) return out;
    out.has = true;
    calcs.marks.forEach(function (r) {
      var id = str(r && r.mark && r.mark.id, "");
      if (!id) return;
      var line = null;
      var sol = r.solution;
      if (r.notApplicable) line = "NOT APPLICABLE";
      else if (!sol) line = "NOT SIZED";
      else if (sol.status !== "ok" || !sol.pick || !sol.pick.cand) {
        line = "NOT SIZED" + (sol.status ? " (" + String(sol.status).toUpperCase() + ")" : "");
      } else {
        var c = sol.pick.cand;
        line = str(c.size, "?") + " " + str(c.species, "?") + " " + str(c.grade, "?");
        if (fin(numOf(c.spacing)) && numOf(c.spacing) > 0) line += " @ " + numOf(c.spacing) + "\" O.C.";
        if (fin(numOf(sol.pick.dcr))) line += "  DCR " + numOf(sol.pick.dcr).toFixed(2);
      }
      out.byId[" " + id] = line;
      out.count++;
    });
    return out;
  }

  /* ============================================================
     THE DRAWING
     ============================================================ */

  /* A button in a browser must not be able to throw an unhandled error.
     Every deliberate refusal inside buildInner is a DxfRefusal, and every
     one of them comes back here as a stated `why` and a null file. A
     genuine programming error is NOT swallowed — it rethrows, because a
     bug in this exporter reported as "the model refused" would send
     somebody looking at their geometry for a fault that is ours. */
  function build(model, opts) {
    try { return buildInner(model, opts); }
    catch (e) {
      if (!e || !e.dxfRefusal) throw e;
      return {
        ok: false, why: e.message, dxf: null,
        version: ACADVER, units: (opts && opts.units === "ft") ? "ft" : "in",
        refusals: [{ what: "the export as a whole", why: e.message }],
        notes: [], layers: layerScheme(), counts: {}, drawn: {},
        extents: null, marks: null, filename: null
      };
    }
  }

  function buildInner(model, opts) {
    opts = opts || {};

    var unitKey = (opts.units === "ft") ? "ft" : "in";
    var UN = UNITS[unitKey];
    var perFt = UN.perFt;
    function U(ft) { return ft * perFt; }                  /* the ONLY feet -> units route */

    var P = numOf(opts.plotScale);
    if (P === null || P <= 0) P = 48;                      /* 1/4" = 1'-0" */
    function pt(plottedInches) { return plottedInches * P * (unitKey === "ft" ? 1 / 12 : 1); }

    var H_TINY = pt(0.0625), H_TEXT = pt(0.09375), H_HEAD = pt(0.125),
        H_TITLE = pt(0.1875), H_BIG = pt(0.28);
    var LINEGAP = 1.75;

    var res = {
      ok: false, why: "", dxf: null,
      version: ACADVER, units: unitKey, unitsPerFt: perFt, plotScale: P,
      refusals: [], notes: [], layers: layerScheme(),
      counts: {}, drawn: {}, extents: null, marks: null, filename: null
    };
    function refuse(what, why) { res.refusals.push({ what: what, why: why }); }

    if (!model || typeof model !== "object") {
      res.why = "no CAD model was supplied to the DXF exporter";
      return res;
    }
    if (!isArr(model.levels)) {
      res.why = "the supplied model carries no levels array, so there is nothing to draw";
      return res;
    }

    /* ---- read ---- */
    var levels = model.levels.map(function (lv) { return readLevel(lv, refuse); });
    var placement = placeMarks(levels, opts.takeoff);
    var members = memberIndex(opts.calcs);

    /* ---- level layout ----
       Levels are laid out LEFT TO RIGHT, each with its own title, the
       way a framing plan sheet actually stacks two plans. Drawing L2
       on top of L1 in one model space is a drawing nobody can read.
       The gutter comes off the levels' own widths; it is a placement,
       not a datum, and the offset applied to each level is printed in
       the notes so a recipient can put it back. */
    var boxes = levels.map(function (L) {
      var pts = [];
      L.walls.forEach(function (w) { if (w.drawable) { pts.push([w.x1, w.y1]); pts.push([w.x2, w.y2]); } });
      L.framing.forEach(function (f) { if (f.drawable) f.pts.forEach(function (p) { pts.push(p); }); });
      return pts.length ? bboxOf(pts) : null;
    });
    var anyGeom = false;
    boxes.forEach(function (b) { if (b) anyGeom = true; });
    if (!anyGeom) {
      res.why = "this model determines no drawable geometry: no wall has two finite endpoints and " +
                "no framing region has three finite points. There is no drawing to export.";
      return res;
    }

    var maxW = 0, maxH = 0;
    boxes.forEach(function (b) {
      if (!b) return;
      if (b.maxX - b.minX > maxW) maxW = b.maxX - b.minX;
      if (b.maxY - b.minY > maxH) maxH = b.maxY - b.minY;
    });
    if (maxW <= 0) maxW = 1;
    if (maxH <= 0) maxH = 1;
    var gutterFt = Math.max(12, maxW * 0.18);
    var offsets = [], cursor = 0;
    levels.forEach(function (L, i) {
      var b = boxes[i];
      offsets.push({ dx: b ? cursor - b.minX : 0, dy: b ? -b.minY : 0 });
      if (b) cursor += (b.maxX - b.minX) + gutterFt;
    });
    function LX(li, xFt) { return U(xFt + offsets[li].dx); }
    function LY(li, yFt) { return U(yFt + offsets[li].dy); }

    var B = new Buf();
    var drawn = {
      wallFaces: 0, wallCentres: 0, wallLabels: 0,
      openings: 0, openingCentrelineOnly: 0,
      regions: 0, directionArrows: 0,
      marksPlaced: 0, marksUnplaced: 0,
      dimensions: 0, noteLines: 0
    };

    /* ------------------------------------------------------------
       WALLS

       Two offset lines, not a centreline — an architect reads faces,
       the takeoff measures the clear span face to face, and a single
       line hides which side of the wall the framing lands on. The
       centreline is drawn too, on its own layer, because it is what
       the model actually stores: keeping it means this file can be
       read back into the model without re-deriving anything.

       Faces are independent closed rectangles. THEY ARE NOT MITRED
       AT CORNERS. Cleaning a corner means deciding which two walls
       meet and how, and a wrong cleanup is a wrong wall line; this
       exporter draws what the model says and says so in the notes.
       ------------------------------------------------------------ */
    levels.forEach(function (L, li) {
      L.walls.forEach(function (w) {
        if (!w.drawable) return;
        var lay = (w.bearing ? "S-WALL-BRNG-" : "S-WALL-NBRG-") + (w.exterior ? "EXTR" : "INTR");
        var ax = LX(li, w.x1), ay = LY(li, w.y1), bx = LX(li, w.x2), by = LY(li, w.y2);

        B.line("S-WALL-CNTR", ax, ay, bx, by, "wall " + w.id + " centreline");
        drawn.wallCentres++;

        if (w.thicknessIn !== null && w.thicknessIn > 0) {
          var hIn = (w.thicknessIn / 2) / 12;             /* half thickness, in FEET */
          var ox = U(w.nx * hIn), oy = U(w.ny * hIn);
          B.pline(lay, [[ax + ox, ay + oy], [bx + ox, by + oy],
                        [bx - ox, by - oy], [ax - ox, ay - oy]], true, "wall " + w.id + " faces");
          drawn.wallFaces++;
        }

        var mx = (ax + bx) / 2, my = (ay + by) / 2;
        var rot = Math.atan2(by - ay, bx - ax) * 180 / Math.PI;
        if (rot > 90) rot -= 180; else if (rot <= -90) rot += 180;
        var offIn = (w.thicknessIn !== null && w.thicknessIn > 0)
          ? U((w.thicknessIn / 2) / 12) + H_TINY * 0.9 : H_TINY * 0.9;
        B.text("S-WALL-IDEN", mx + w.nx * offIn, my + w.ny * offIn,
               H_TINY, w.id, 1, rot, "wall " + w.id + " id");
        drawn.wallLabels++;
      });
    });

    /* ------------------------------------------------------------
       OPENINGS
       ------------------------------------------------------------ */
    levels.forEach(function (L, li) {
      L.openings.forEach(function (o) {
        if (!o.drawable) return;
        var w = o.host;
        var sx = LX(li, w.x1 + w.ux * o.offsetFt), sy = LY(li, w.y1 + w.uy * o.offsetFt);
        var ex = LX(li, w.x1 + w.ux * (o.offsetFt + o.widthFt)), ey = LY(li, w.y1 + w.uy * (o.offsetFt + o.widthFt));

        if (w.thicknessIn !== null && w.thicknessIn > 0) {
          var hIn = (w.thicknessIn / 2) / 12;
          var ox = U(w.nx * hIn), oy = U(w.ny * hIn);
          B.pline("S-OPNG", [[sx + ox, sy + oy], [ex + ox, ey + oy],
                             [ex - ox, ey - oy], [sx - ox, sy - oy]], true, "opening " + o.id);
          drawn.openings++;
        } else {
          /* the jamb positions ARE determined; the wall thickness is not,
             so the opening is drawn as the segment of centreline it
             occupies and nothing is invented across the wall */
          B.line("S-OPNG", sx, sy, ex, ey, "opening " + o.id + " on centreline");
          drawn.openingCentrelineOnly++;
        }

        var wid = ftIn(o.widthFt);
        var label = o.id + " " + o.kind.toUpperCase() + " " + (wid === null ? "WIDTH UNDETERMINED" : wid);
        /* an offset the plan did not give is stated ON THE DRAWING, not only
           in the notes: a framer reading a dimension off a placeholder is
           the failure this word exists to prevent */
        if (o.offsetBasis && o.offsetBasis !== "plan") label += " " + o.offsetBasis.toUpperCase();
        var rot = Math.atan2(ey - sy, ex - sx) * 180 / Math.PI;
        if (rot > 90) rot -= 180; else if (rot <= -90) rot += 180;
        /* (nx, ny) is the wall normal. The label goes on the MINUS side and
           the wall id and any member mark on the PLUS side, so the three
           annotations around one wall do not land on each other. */
        var perp = ((w.thicknessIn !== null && w.thicknessIn > 0) ? U((w.thicknessIn / 2) / 12) : 0) + H_TINY * 1.4;
        B.text("S-OPNG-IDEN", (sx + ex) / 2 - w.nx * perp, (sy + ey) / 2 - w.ny * perp,
               H_TINY, label, 1, rot, "opening " + o.id + " label");
      });
    });

    /* ------------------------------------------------------------
       FRAMING REGIONS AND THEIR DIRECTION
       ------------------------------------------------------------ */
    var KINDWORD = { floor: "FLOOR FRAMING", roof: "ROOF FRAMING",
                     ceiling: "CEILING FRAMING", deck: "DECK FRAMING" };
    var SYSWORD = { truss: "TRUSSES", manufactured: "MANUFACTURED" };

    levels.forEach(function (L, li) {
      L.framing.forEach(function (f) {
        if (!f.drawable) return;
        var pts = f.pts.map(function (p) { return [LX(li, p[0]), LY(li, p[1])]; });
        B.pline("S-FRAM-RGN", pts, true, "framing region " + f.id);
        drawn.regions++;

        var cx = LX(li, f.at[0]), cy = LY(li, f.at[1]);
        var word = (f.system && own(SYSWORD, f.system) ? SYSWORD[f.system] + " " : "") +
                   (own(KINDWORD, f.kind) ? KINDWORD[f.kind] : f.kind.toUpperCase());
        var spacing = (f.spacingIn === null) ? "SPACING NOT DECLARED" : "@ " + f.spacingIn + "\" O.C.";

        /* the region label sits ABOVE the centroid, because the centroid is
           where a member mark for this region lands and two labels in one
           place is one label nobody reads */
        B.text("S-FRAM-IDEN", cx, cy + H_TEXT * 4.2, H_TEXT, f.id + "  " + word, 1, 0,
               "region " + f.id + " label");
        B.text("S-FRAM-IDEN", cx, cy + H_TEXT * 2.7, H_TINY,
               spacing + "  BEARS ON " + (f.bearsOn.length ? f.bearsOn.join(", ") : "NOTHING DECLARED"),
               1, 0, "region " + f.id + " sublabel");

        if (f.directionDeg === null) return;   /* no arrow. named in refusals. */

        var a = f.directionDeg * Math.PI / 180;
        var dx = Math.cos(a), dy = Math.sin(a);
        var lo = null, hi = null;
        pts.forEach(function (p) {
          var s = (p[0] - cx) * dx + (p[1] - cy) * dy;
          if (lo === null || s < lo) lo = s;
          if (hi === null || s > hi) hi = s;
        });
        var half = Math.min(Math.abs(lo), Math.abs(hi)) * 0.78;
        if (!(half > 0)) half = Math.max(U(1), H_TEXT * 4);
        var p1x = cx - dx * half, p1y = cy - dy * half, p2x = cx + dx * half, p2y = cy + dy * half;
        B.line("S-FRAM-DIRN", p1x, p1y, p2x, p2y, "region " + f.id + " direction");
        var head = H_TEXT * 1.3, spread = 26 * Math.PI / 180;
        [[p1x, p1y, a], [p2x, p2y, a + Math.PI]].forEach(function (h) {
          B.line("S-FRAM-DIRN", h[0], h[1], h[0] + Math.cos(h[2] - spread) * head,
                 h[1] + Math.sin(h[2] - spread) * head, "region " + f.id + " arrowhead");
          B.line("S-FRAM-DIRN", h[0], h[1], h[0] + Math.cos(h[2] + spread) * head,
                 h[1] + Math.sin(h[2] + spread) * head, "region " + f.id + " arrowhead");
        });
        var trot = f.directionDeg;
        while (trot > 180) trot -= 360;
        while (trot <= -180) trot += 360;
        if (trot > 90) trot -= 180; else if (trot <= -90) trot += 180;
        B.text("S-FRAM-DIRN", cx - Math.sin(a) * H_TINY * 1.4, cy + Math.cos(a) * H_TINY * 1.4,
               H_TINY, word + " " + spacing, 1, trot, "region " + f.id + " direction label");
        drawn.directionArrows++;
      });
    });

    /* ------------------------------------------------------------
       MEMBER MARKS

       A framing plan without its marks is a wall diagram.
       ------------------------------------------------------------ */
    placement.placed.forEach(function (m) {
      var li = m.level;
      var ax = LX(li, m.x), ay = LY(li, m.y);          /* the exact anchor */
      var member = members.has
        ? (own(members.byId, " " + m.id) ? members.byId[" " + m.id] : "NOT IN THE SUPPLIED CALCULATIONS")
        : "NO CALCULATIONS SUPPLIED";
      var l1 = m.id, l2 = member;
      var wch = Math.max(l1.length, l2.length);
      var bw = wch * H_TEXT * 0.62 + H_TEXT * 0.9, bh = H_TEXT * 3.2;

      /* A tag drawn on top of the opening it labels hides the opening. It
         is nudged clear along the wall normal and a leader runs back to the
         anchor, so the mark is still unambiguously attached to ONE opening.
         The nudge is a drafting offset; the anchor it comes off is exact. */
      var x = ax, y = ay;
      if (m.lead) {
        var d = U(m.lead.clearFt) + bh / 2 + H_TEXT * 1.2;
        x = ax + m.lead.nx * d;
        y = ay + m.lead.ny * d;
        B.line("S-ANNO-MARK", ax, ay, ax + m.lead.nx * (d - bh / 2), ay + m.lead.ny * (d - bh / 2),
               "mark " + m.id + " leader");
      }

      B.pline("S-ANNO-MARK", [[x - bw / 2, y - bh / 2], [x + bw / 2, y - bh / 2],
                              [x + bw / 2, y + bh / 2], [x - bw / 2, y + bh / 2]], true,
              "mark " + m.id + " box");
      B.text("S-ANNO-MARK", x, y + H_TEXT * 0.35, H_TEXT, l1, 1, 0, "mark " + m.id);
      B.text("S-ANNO-MARK", x, y - H_TEXT * 1.25, H_TINY, l2, 1, 0, "mark " + m.id + " member");
      drawn.marksPlaced++;
    });
    drawn.marksUnplaced = placement.unplaced.length;

    /* ------------------------------------------------------------
       DIMENSIONS

       Exploded geometry — extension lines, a dimension line,
       architectural ticks, and the value as TEXT — not R12 DIMENSION
       entities. An R12 DIMENSION needs a DIMSTYLE table entry AND an
       anonymous block holding its own picture; if that block is
       wrong the dimension renders as nothing at all, silently. Lines
       always render. The cost is that these are NOT associative and
       will not follow the geometry if it moves, which is stated in
       the notes.

       Only the overall extents of each level are dimensioned. Wall
       runs and opening locations are NOT, because many opening
       offsets in this model are placeholders (cad.js says which) and
       a dimension off a placeholder is a number a framer builds to.
       ------------------------------------------------------------ */
    function sgn(v) { return v > 0 ? 1 : v < 0 ? -1 : 0; }
    function dimString(x1, y1, x2, y2, offX, offY, feet, tag) {
      var label = ftIn(feet);
      if (label === null) { refuse(tag, "the distance is not a finite number, so it is not dimensioned"); return; }
      var ax = x1 + offX, ay = y1 + offY, bx = x2 + offX, by = y2 + offY;
      var tick = H_TEXT * 0.5;
      B.line("S-ANNO-DIMS", x1, y1, ax + sgn(offX) * tick, ay + sgn(offY) * tick, tag + " ext1");
      B.line("S-ANNO-DIMS", x2, y2, bx + sgn(offX) * tick, by + sgn(offY) * tick, tag + " ext2");
      B.line("S-ANNO-DIMS", ax, ay, bx, by, tag + " dim line");
      B.line("S-ANNO-DIMS", ax - tick, ay - tick, ax + tick, ay + tick, tag + " tick1");
      B.line("S-ANNO-DIMS", bx - tick, by - tick, bx + tick, by + tick, tag + " tick2");
      var rot = Math.atan2(by - ay, bx - ax) * 180 / Math.PI;
      if (rot > 90) rot -= 180; else if (rot <= -90) rot += 180;
      var rad = rot * Math.PI / 180;
      B.text("S-ANNO-DIMS", (ax + bx) / 2 - Math.sin(rad) * H_TEXT * 0.5,
             (ay + by) / 2 + Math.cos(rad) * H_TEXT * 0.5, H_TEXT, label, 1, rot, tag + " text");
      drawn.dimensions++;
    }

    levels.forEach(function (L, li) {
      var b = boxes[li];
      if (!b) return;
      var x0 = LX(li, b.minX), x1 = LX(li, b.maxX), y0 = LY(li, b.minY), y1 = LY(li, b.maxY);
      var off = H_TEXT * 8;
      dimString(x0, y0, x1, y0, 0, -off, b.maxX - b.minX, "level " + L.id + " overall width");
      dimString(x0, y0, x0, y1, -off, 0, b.maxY - b.minY, "level " + L.id + " overall depth");
      B.text("S-ANNO-TTLB", x0, y1 + H_BIG * 3.0, H_BIG,
             L.id + " - " + L.label.toUpperCase() + " FRAMING PLAN", 0, 0, "level " + L.id + " title");
      B.text("S-ANNO-TTLB", x0, y1 + H_BIG * 1.6, H_TINY,
             "SCALE " + (own(SCALE_LABEL, String(P)) ? SCALE_LABEL[String(P)] : "1:" + P) +
             " WHEN PLOTTED AT THAT SCALE - THIS FILE IS 1:1 IN REAL UNITS",
             0, 0, "level " + L.id + " subtitle");
    });

    /* the plan itself is finished; everything after this is sheet
       furniture, and it is laid out AROUND this box rather than
       stacked under it, so the sheet comes out roughly square
       instead of a metre of notes below a small house */
    var planBox = { minX: B.minX, minY: B.minY, maxX: B.maxX, maxY: B.maxY };

    /* ------------------------------------------------------------
       NORTH — declared as an assumption, because it is one. The model
       contract has an origin and axes and NO true-north bearing.
       ------------------------------------------------------------ */
    (function () {
      var b = boxes[0];
      if (!b) return;
      var nx = planBox.maxX + H_BIG * 3, ny = LY(0, b.maxY);
      var h = H_BIG * 3;
      B.line("S-ANNO-NORT", nx, ny, nx, ny + h, "north shaft");
      B.line("S-ANNO-NORT", nx, ny + h, nx - h * 0.18, ny + h * 0.72, "north head");
      B.line("S-ANNO-NORT", nx, ny + h, nx + h * 0.18, ny + h * 0.72, "north head");
      B.text("S-ANNO-NORT", nx, ny - H_TEXT * 1.4, H_TEXT, "N (ASSUMED)", 1, 0, "north label");
      B.text("S-ANNO-NORT", nx, ny - H_TEXT * 3.0, H_TINY, "PLAN NORTH IS ASSUMED", 1, 0, "north note 1");
      B.text("S-ANNO-NORT", nx, ny - H_TEXT * 4.2, H_TINY, "TO BE THE MODEL +Y AXIS.", 1, 0, "north note 2");
      B.text("S-ANNO-NORT", nx, ny - H_TEXT * 5.4, H_TINY, "NOT A SURVEYED BEARING.", 1, 0, "north note 3");
    })();

    /* ------------------------------------------------------------
       GRAPHIC SCALE — real feet off the drawing's own units
       ------------------------------------------------------------ */
    var blockTop = planBox.minY - H_BIG * 4;
    var blockLeft = planBox.minX;
    (function () {
      var target = maxW / 5, step = 1;
      [1, 2, 5, 10, 20, 25, 50, 100].forEach(function (v) { if (v <= target) step = v; });
      var x0 = blockLeft, y0 = blockTop, w = U(step);
      B.line("S-ANNO-SCLE", x0, y0, x0 + w, y0, "scale bar");
      B.line("S-ANNO-SCLE", x0, y0 - H_TEXT * 0.5, x0, y0 + H_TEXT * 0.5, "scale tick 0");
      B.line("S-ANNO-SCLE", x0 + w, y0 - H_TEXT * 0.5, x0 + w, y0 + H_TEXT * 0.5, "scale tick 1");
      B.text("S-ANNO-SCLE", x0, y0 + H_TEXT * 0.9, H_TINY, "0", 0, 0, "scale 0");
      B.text("S-ANNO-SCLE", x0 + w, y0 + H_TEXT * 0.9, H_TINY, step + " FT", 1, 0, "scale n");
      blockTop = y0 - H_TEXT * 3;
    })();

    /* ------------------------------------------------------------
       LEGEND

       Every swatch lives on S-ANNO-LEGN and borrows the COLOUR and
       LINETYPE of the layer it describes, rather than living on that
       layer. A swatch drawn on S-WALL-BRNG-EXTR looks identical and
       is counted as a fifth bearing wall by anything that reads
       quantities off this file. The layer name is printed beside each
       row instead, which is more use to a recipient anyway.
       ------------------------------------------------------------ */
    (function () {
      var byName = {};
      LAYERS.forEach(function (l) { byName[l.name] = l; });
      var y = blockTop, x = blockLeft, sw = H_TEXT * 4, gap = H_TEXT * LINEGAP;
      B.text("S-ANNO-LEGN", x, y, H_HEAD, "LEGEND", 0, 0, "legend head");
      y -= gap * 1.4;
      var rows = [
        ["S-WALL-BRNG-EXTR", "BEARING EXTERIOR WALL (both faces)"],
        ["S-WALL-BRNG-INTR", "BEARING INTERIOR WALL (both faces)"],
        ["S-WALL-NBRG-EXTR", "NON-BEARING EXTERIOR WALL"],
        ["S-WALL-NBRG-INTR", "NON-BEARING INTERIOR WALL"],
        ["S-WALL-CNTR", "WALL CENTRELINE - the line the model stores"],
        ["S-OPNG", "OPENING - rough opening through the wall"],
        ["S-FRAM-RGN", "FRAMED REGION BOUNDARY"],
        ["S-FRAM-DIRN", "SPAN DIRECTION AND SPACING"],
        ["S-ANNO-MARK", "MEMBER MARK - id over selected member"],
        ["S-ANNO-DIMS", "DIMENSION (exploded, not associative)"],
        ["S-GRID", "STRUCTURAL GRID - EMPTY, see note 6"]
      ];
      rows.forEach(function (r) {
        var src = byName[r[0]];
        B.line("S-ANNO-LEGN", x, y + H_TEXT * 0.35, x + sw, y + H_TEXT * 0.35,
               "legend swatch " + r[0],
               src ? { color: src.color, ltype: src.lt } : null);
        B.text("S-ANNO-LEGN", x + sw + H_TEXT, y, H_TEXT, r[1] + "   [" + r[0] + "]", 0, 0, "legend row");
        y -= gap;
      });
      blockTop = y - gap;
    })();

    /* ------------------------------------------------------------
       NOTES — everything undetermined, by name.
       ------------------------------------------------------------ */
    var noteLines = [];
    function N(s) { noteLines.push(s === undefined ? "" : String(s)); }
    function NW(prefix, s, width) {
      /* wrap without breaking a word; DXF has no MTEXT in R12 so the
         wrapping is done here rather than left to the reader */
      var words = String(s).split(/\s+/), line = prefix, first = true, pad = "";
      var i; for (i = 0; i < prefix.length; i++) pad += " ";
      width = width || 96;
      words.forEach(function (wd) {
        if (line.length + 1 + wd.length > width && !first) { N(line); line = pad + wd; }
        else { line = (first ? line : line + " ") + wd; }
        first = false;
      });
      if (line.replace(/\s+$/, "").length) N(line);
    }

    N("GENERAL NOTES");
    N("");
    NW("1.  ", "PREPARED FOR PE REVIEW - NOT SEALED ENGINEERING. This drawing carries no " +
       "engineer's seal and none is implied. It is issued for review by a licensed " +
       "Professional Engineer, who alone signs and seals the design. The software never stamps.");
    NW("2.  ", "UNITS: " + UN.label + ". $INSUNITS=" + UN.insunits + ", $MEASUREMENT=0 (imperial), " +
       "$LUNITS=" + UN.lunits + ". The model is in decimal feet; every coordinate in this file was " +
       "converted once, at one place in the exporter. If this file opens at 12x or 1/12, the " +
       "receiving drawing's units are set differently - check INSUNITS there before rescaling anything.");
    NW("3.  ", "GEOMETRY IS 1:1 IN REAL UNITS. Annotation text and symbols are sized for plotting at " +
       (own(SCALE_LABEL, String(P)) ? SCALE_LABEL[String(P)] : "1:" + P) +
       ". Plotting at another scale needs the annotation rescaled; the geometry does not change.");
    NW("4.  ", "WALLS are drawn as two offset faces from the model centreline and thickness, PLUS the " +
       "centreline itself on S-WALL-CNTR. Faces are independent closed polylines and ARE NOT MITRED " +
       "OR CLEANED AT CORNERS - each wall is drawn as the model states it, with no junction inferred.");
    NW("5.  ", "BEARING and NON-BEARING walls are on separate layers (S-WALL-BRNG-* and S-WALL-NBRG-*), " +
       "not distinguished by lineweight, so the structural reading survives being printed, " +
       "re-coloured or re-plotted by somebody else.");
    NW("6.  ", "S-GRID IS EMPTY ON PURPOSE. This geometry model declares no structural grid, and this " +
       "exporter does not invent one. Grid lines and bubbles must be laid out by the engineer or " +
       "architect against the real dimensions.");
    NW("7.  ", "DIMENSIONS are exploded lines and text, not associative DIMENSION entities, and they " +
       "WILL NOT UPDATE if the geometry is moved. Only the overall extents of each level are " +
       "dimensioned: individual wall runs and opening locations are not, because opening offsets in " +
       "this model may be placeholders (see the model validation notes below) and a dimension taken " +
       "off a placeholder is a number somebody builds to.");
    NW("8.  ", "NO DOOR SWINGS, no window sills, no hatch patterns, no schedules and no sections are " +
       "exported. This is a structural framing plan, not an architectural background.");
    if (levels.length > 1) {
      NW("9.  ", "This model has " + levels.length + " levels. They are drawn SIDE BY SIDE, left to right, " +
         "each at its own origin - not stacked. Each level's plan was translated in X only; the " +
         "translations are listed under LEVEL PLACEMENT below so the model coordinates can be recovered.");
    }
    N("");

    N("HOW EACH THING ON THIS DRAWING GOT THERE");
    N("");
    NW("*   ", "Walls, openings and framed regions are the CAD model verbatim. Nothing is smoothed, " +
       "closed, squared or snapped by this exporter.");
    NW("*   ", "Member marks: " + placement.basis + ".");
    NW("*   ", members.has
        ? "Selected members are read from the supplied calculations and matched to marks BY MARK ID. " +
          "A placed mark the calculations do not carry reads NOT IN THE SUPPLIED CALCULATIONS on the " +
          "drawing rather than reading blank."
        : "NO CALCULATIONS WERE SUPPLIED to this export, so every mark box reads NO CALCULATIONS " +
          "SUPPLIED in place of a member. The marks locate the members; they do not size them.");
    N("");

    if (levels.length > 1) {
      N("LEVEL PLACEMENT");
      N("");
      levels.forEach(function (L, i) {
        NW("*   ", L.id + " (" + L.label + ") translated by X " + offsets[i].dx.toFixed(3) +
           " ft, Y " + offsets[i].dy.toFixed(3) + " ft from model coordinates.");
      });
      N("");
    }

    /* model validation, verbatim — whatever cad.js says is wrong with
       this model travels with the geometry rather than staying in a
       browser tab the recipient never saw */
    var vrows = null;
    if (typeof FM !== "undefined" && FM && FM.cad && FM.cad.validate) {
      try { vrows = FM.cad.validate(model) || []; } catch (e) { vrows = null; }
    }
    N("MODEL VALIDATION AT EXPORT" + (vrows === null ? " - NOT AVAILABLE" : ""));
    N("");
    if (vrows === null) {
      NW("!   ", "FM.cad.validate was not available to this export, so this drawing cannot state " +
         "whether the model it came from validates. Treat the geometry as unchecked.");
    } else if (!vrows.length) {
      NW("*   ", "FM.cad.validate reported nothing on this model.");
    } else {
      vrows.forEach(function (r) {
        NW(String(r.severity || "note").toUpperCase() + ": ",
           "[" + str(r.level, "-") + " " + str(r.id, "-") + "] " + str(r.text, ""));
      });
    }
    N("");

    if (isArr(model.unresolved) && model.unresolved.length) {
      N("UNRESOLVED IN THE MODEL - " + model.unresolved.length + " ITEM(S)");
      N("");
      model.unresolved.forEach(function (u) {
        NW("*   ", str(u.what, "(unnamed)") + " - " + str(u.why, "no reason recorded") +
           "  NEED: " + str(u.need, "not stated"));
      });
      N("");
    }

    if (opts.takeoff && isArr(opts.takeoff.unresolved) && opts.takeoff.unresolved.length) {
      N("UNRESOLVED IN THE TAKEOFF - " + opts.takeoff.unresolved.length + " ITEM(S)");
      N("");
      opts.takeoff.unresolved.forEach(function (u) {
        NW("*   ", str(u.what, "(unnamed)") + " - " + str(u.why, "no reason recorded") +
           "  NEED: " + str(u.need, "not stated"));
      });
      N("");
    }

    if (placement.unplaced.length) {
      N("MARKS NOT PLACED ON THIS DRAWING - " + placement.unplaced.length);
      N("");
      NW("    ", "These marks exist in the takeoff and are NOT drawn, because nothing in the takeoff " +
         "says where they sit. They are listed rather than placed at a plausible point.");
      N("");
      placement.unplaced.forEach(function (u) { NW("*   ", u.id + " - " + u.why); });
      N("");
    }

    if (res.refusals.length) {
      N("NOT DRAWN, AND WHY - " + res.refusals.length + " ITEM(S)");
      N("");
      res.refusals.forEach(function (r) { NW("*   ", r.what + ": " + r.why); });
      N("");
    } else {
      N("NOT DRAWN, AND WHY");
      N("");
      NW("*   ", "Every wall, opening and framed region in this model was drawable and is drawn.");
      N("");
    }

    N("END OF NOTES");

    /* Notes go in a RIGHT-HAND COLUMN beside the plan, the way a sheet's
       note margin actually runs, rather than in one tall stack under it.
       Stacked, a package with 90 lines of honest disclosure produced a
       drawing four times taller than wide, which plots as a small house
       at the top of a very long page. */
    (function () {
      var x = B.maxX + H_BIG * 2;
      var y = planBox.maxY;
      noteLines.forEach(function (s) {
        if (s !== "") B.text("S-ANNO-NOTE", x, y, H_TINY, s, 0, 0, "note line");
        y -= H_TINY * LINEGAP;
        drawn.noteLines++;
      });
    })();

    /* ------------------------------------------------------------
       TITLE BLOCK + THE EMPTY SEAL

       Non-negotiable #1. The statement travels with the geometry or
       the geometry travels without it.
       ------------------------------------------------------------ */
    var date = str(opts.date, "");
    if (!date) { try { date = new Date().toISOString().slice(0, 10); } catch (e) { date = "DATE NOT SUPPLIED"; } }

    function pick(v, what) { var s = str(v, ""); return s ? s : ("NOT SUPPLIED - " + what); }

    var codeBasis = "NOT SUPPLIED - no jurisdiction was passed to this export";
    if (opts.juris && isArr(opts.juris.codes) && opts.juris.codes.length) {
      codeBasis = opts.juris.codes.map(function (c) {
        return str(c.name, "?") + " " + str(c.edition, "?");
      }).join("; ");
    }

    var rowsTB = [
      ["PROJECT", pick(opts.projectName || (model && model.name), "no project name was passed")],
      ["PLAN", str(model.name, "(unnamed model)") +
               (model.source && model.source.planId ? "   (" + model.source.planId + ")" : "")],
      ["LEVELS", levels.map(function (L) { return L.id + " " + L.label; }).join(";  ")],
      ["REGION / PACK", pick(opts.pack && (opts.pack.name || opts.pack.id), "no region pack was passed")],
      ["JURISDICTION", pick(opts.juris && (opts.juris.name || opts.juris.id), "no jurisdiction was passed")],
      ["CODE BASIS", codeBasis],
      ["DATE", date],
      ["UNITS", UN.label + "  ($INSUNITS=" + UN.insunits + ", $MEASUREMENT=0, $LUNITS=" + UN.lunits + ")"],
      ["ANNOTATION FOR", (own(SCALE_LABEL, String(P)) ? SCALE_LABEL[String(P)] : "1:" + P) +
                         "   (geometry itself is 1:1 in real units)"],
      ["SOURCE", "FM.cad model v" + str(model.version, "?") +
                 (model.source && model.source.builtBy ? ", built by " + model.source.builtBy : "")],
      ["GENERATED BY", GEN + "   DXF " + ACADVER + " (AutoCAD R12) ASCII"]
    ];

    (function () {
      var x = blockLeft, y = blockTop;
      var lab = H_TEXT * 13;
      var w = Math.max(H_TEXT * 62, lab + H_TEXT * 46);
      var rowH = H_TEXT * LINEGAP;
      var top = y;

      B.text("S-ANNO-TTLB", x + H_TEXT, y - H_BIG, H_BIG, "FIRMARK - STRUCTURAL FRAMING PLAN", 0, 0, "tb title");
      y -= H_BIG * 2.2;
      rowsTB.forEach(function (r) {
        B.text("S-ANNO-TTLB", x + H_TEXT, y, H_TINY, r[0], 0, 0, "tb key");
        B.text("S-ANNO-TTLB", x + lab, y, H_TINY, r[1], 0, 0, "tb value");
        y -= rowH;
      });
      y -= rowH * 0.5;

      B.text("S-ANNO-TTLB", x + H_TEXT, y, H_HEAD, "PREPARED FOR PE REVIEW - NOT SEALED ENGINEERING", 0, 0, "tb statement");
      y -= H_HEAD * LINEGAP;
      ["This drawing is not a sealed engineering document. No engineer's seal has been",
       "applied to it and none is implied. It is issued for review by a licensed",
       "Professional Engineer, who alone signs and seals the design. The software never",
       "stamps. Do not submit this drawing for permit as issued."].forEach(function (s) {
        B.text("S-ANNO-TTLB", x + H_TEXT, y, H_TINY, s, 0, 0, "tb disclaimer");
        y -= H_TINY * LINEGAP;
      });
      y -= rowH;

      /* the seal block: drawn, labelled, and LEFT EMPTY */
      var sw = H_TEXT * 22, sh = H_TEXT * 16;
      var sx = x + H_TEXT, sy = y - sh;
      B.pline("S-ANNO-SEAL", [[sx, sy], [sx + sw, sy], [sx + sw, sy + sh], [sx, sy + sh]], true, "seal block");
      B.text("S-ANNO-SEAL", sx + sw / 2, sy + sh - H_TEXT * 1.6, H_TEXT, "SEAL", 1, 0, "seal head");
      B.text("S-ANNO-SEAL", sx + sw / 2, sy + sh / 2, H_TINY, "(INTENTIONALLY BLANK)", 1, 0, "seal blank");
      B.text("S-ANNO-SEAL", sx + sw / 2, sy + H_TEXT * 1.2, H_TINY, "NO SEAL HAS BEEN APPLIED", 1, 0, "seal none");
      var ly = sy + sh - H_TEXT * 2;
      var lx = sx + sw + H_TEXT * 2;
      ["TO BE SEALED BY ______________________________________, PE",
       "LICENCE NO. ____________________   STATE ______________",
       "DATE SEALED ____________________",
       "",
       "REVIEWED BY _____________________________________________",
       "DATE REVIEWED __________________"].forEach(function (s) {
        if (s !== "") B.text("S-ANNO-SEAL", lx, ly, H_TINY, s, 0, 0, "seal line");
        ly -= H_TINY * 2.2;
      });

      B.pline("S-ANNO-TTLB", [[x, sy - H_TEXT * 2], [x + w, sy - H_TEXT * 2],
                              [x + w, top], [x, top]], true, "title block frame");
    })();

    /* ------------------------------------------------------------
       HEADER: extents measured off the entities actually written
       ------------------------------------------------------------ */
    if (B.minX === null) {
      res.why = "no entity was produced, so there is nothing to write";
      return res;
    }
    var pad = Math.max((B.maxX - B.minX), (B.maxY - B.minY)) * 0.04;
    if (!(pad > 0)) pad = H_BIG;
    var hd = {
      extMinX: B.minX, extMinY: B.minY, extMaxX: B.maxX, extMaxY: B.maxY,
      limMinX: B.minX - pad, limMinY: B.minY - pad,
      limMaxX: B.maxX + pad, limMaxY: B.maxY + pad,
      viewCX: (B.minX + B.maxX) / 2, viewCY: (B.minY + B.maxY) / 2,
      viewH: Math.max(B.maxY - B.minY, 1) * 1.08,
      aspect: (B.maxY - B.minY) > 0 ? Math.max((B.maxX - B.minX) / (B.maxY - B.minY), 0.01) : 1,
      snap: pt(0.5), ltScale: P * (unitKey === "ft" ? 1 / 12 : 1),
      textSize: H_TEXT, plotScale: P,
      lunits: UN.lunits, luprec: UN.luprec, insunits: UN.insunits
    };

    var L = [];
    writeHeader(L, hd);
    writeTables(L, hd);
    W(L, 0, "SECTION"); W(L, 2, "BLOCKS"); W(L, 0, "ENDSEC");
    W(L, 0, "SECTION"); W(L, 2, "ENTITIES");
    B.ents.forEach(function (e) { writeEntity(L, e); });
    W(L, 0, "ENDSEC");
    W(L, 0, "EOF");

    var badNums = scanNumeric(L);
    if (badNums.length) {
      throw DxfRefusal("dxf.js assembled a file containing " + badNums.length +
                       " non-numeric value(s) where DXF requires a number (first: group " +
                       badNums[0].code + " = \"" + badNums[0].value + "\"). Refusing to return it.",
                       { bad: badNums.slice(0, 5) });
    }

    res.ok = true;
    res.dxf = L.join("\r\n") + "\r\n";     /* CRLF: what DXF has always used */
    res.counts = B.counts;
    res.drawn = drawn;
    res.entityCount = B.ents.length;
    res.extents = { minX: B.minX, minY: B.minY, maxX: B.maxX, maxY: B.maxY };
    res.marks = { placed: placement.placed.map(function (m) { return { id: m.id, on: m.on, how: m.how }; }),
                  unplaced: placement.unplaced, basis: placement.basis,
                  membersMatched: members.count };
    res.notes = noteLines;
    res.filename = filename(model, opts);
    return res;
  }

  /* ============================================================
     PUBLIC SURFACE
     ============================================================ */

  function slug(s) {
    return String(s === null || s === undefined ? "" : s)
      .toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 48) || "model";
  }

  function filename(model, opts) {
    opts = opts || {};
    var id = (model && model.source && model.source.planId) || (model && model.name) || "model";
    var d = str(opts.date, "");
    if (!d) { try { d = new Date().toISOString().slice(0, 10); } catch (e) { d = "undated"; } }
    return "firmark-framing-" + slug(id) + "-" + slug(d) + ".dxf";
  }

  /* The contracted entry point. Returns the DXF text, or THROWS a
     DxfRefusal naming what could not be drawn. It does not return an
     empty string, a placeholder file or a drawing of nothing: a file
     that opens blank is worse than no file, because the recipient
     believes they have the geometry. */
  function fromModel(model, opts) {
    var r = build(model, opts);
    if (!r.ok) {
      throw DxfRefusal("dxf.js refused to export: " + (r.why || "the model produced no drawing"),
                       { refusals: r.refusals });
    }
    return r.dxf;
  }

  FM.dxf = {
    VERSION: GEN,
    ACADVER: ACADVER,
    LAYERS: layerScheme(),
    layerNames: layerNames,

    fromModel: fromModel,
    build: build,
    filename: filename,

    /* exposed because they are the parts worth testing on their own */
    encodeText: encodeText,
    cleanName: cleanName,
    ftIn: ftIn,
    fmt: fmt
  };
})();

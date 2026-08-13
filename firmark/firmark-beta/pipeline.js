/* ============================================================
   pipeline.js — the stage machine and the approval gates.

   The product's claim is "an architectural plan to a review package
   in minutes, with human approval at every stage". The gates are the
   half that makes the speed defensible: fast is only safe if a person
   put their name on each step and the software can prove nothing
   changed under them afterwards.

   THE RULE THAT MAKES A GATE MEAN ANYTHING
   ----------------------------------------
   An approval is recorded against a FINGERPRINT of what was approved.
   If an upstream stage changes after you approved a downstream one,
   your approval is invalidated and says so by name.

   Without that, the gates are theatre: approve the takeoff, then edit
   the geometry, and the calculations carry an approval for a takeoff
   that no longer exists. That is worse than having no gate at all,
   because the audit trail then testifies to a review that did not
   happen. Every serious version of this defect has the same shape —
   evidence outliving the thing it was evidence for.

   The trail is append-only. Rejections and invalidations stay in it;
   a clean-looking history is not the goal, a true one is.

   WHAT THE FINGERPRINT COVERS, AND WHAT IT DOES NOT
   -------------------------------------------------
   Stated here because a guarantee whose limits are only in the code is
   a guarantee nobody can rely on.

   1. It covers ALL of the content. There is no size at which the walk
      quietly starts skipping. The previous version truncated at 20,000
      nodes and returned the same placeholder for everything after that,
      and because keys are sorted, `walls` was the first thing dropped
      from a CAD level. On a model with 2,614 openings a bearing wall
      could stop bearing, move 950 ft, change thickness, and the model
      could be renamed — all four at once — for a BYTE-IDENTICAL
      fingerprint. Truncation that drops content silently is not a
      coarse fingerprint, it is a false one.

   2. Where a limit still exists it is NAMED, not silent. Two remain —
      nesting deeper than MAX_DEPTH, and a walk longer than MAX_STEPS —
      and both mark the fingerprint incomplete. An incomplete
      fingerprint cannot be approved against, invalidates any approval
      standing on it, and prints the reason. See `fingerprintOf`.

   3. It is a fingerprint of CONTENT, not of identity or of edit count.
      Key order does not matter. Re-serialising a model does not matter.
      Shared references do not matter: the same object reached twice is
      walked twice and reads the same as two equal copies, so a model
      that survived a JSON round trip fingerprints as the model that
      went in.

   4. It is not a signature. There is no secret in it, so it detects
      that something moved; it does not prove that nobody moved it on
      purpose. See the note above `Hash` for what the width buys.
   ============================================================ */

(function () {
  "use strict";

  var KEY = "fm-pipeline";

  /* `needs` is the role required to approve. `inputs` names the stages whose
     fingerprints this stage's approval depends on — change any of them and
     this approval dies.

     `inputs` is the FULL transitive set, not just the immediate predecessor.
     That is deliberate and `test/suite-pipeline.js` asserts it: an approval
     records what it saw of every stage it stands on, so a change two steps
     upstream cannot reach this gate through an intermediate stage that
     happened to produce the same output. */
  var STAGES = [
    { id: "geometry", label: "Geometry", short: "Plan geometry",
      gate: "The drawn plan is what the architectural set says.",
      needs: "drafter", inputs: [],
      detail: "Walls, bearing lines, openings and framing directions. Nothing " +
              "downstream can be right if this is wrong, and nothing downstream " +
              "can detect that it is wrong." },

    { id: "takeoff", label: "Takeoff", short: "Spans and tributaries",
      gate: "Every span, tributary width and bearing condition is what the plan means.",
      needs: "engineer", inputs: ["geometry"],
      detail: "This is the gate that matters most. A tributary width that is " +
              "quietly wrong produces a confident, wrong member, and every check " +
              "downstream will agree with it." },

    { id: "loads", label: "Loads and code", short: "Design criteria",
      gate: "The code edition, wind speed, snow and live loads are right for this site.",
      needs: "engineer", inputs: ["geometry", "takeoff"],
      detail: "Jurisdiction, adopted code, and the site hazard parameters. The " +
              "defaults are planning values — a site is not designed off a default." },

    { id: "calcs", label: "Calculations", short: "Member selection",
      gate: "The selected members, the escalations, and what was not sized are accepted.",
      needs: "engineer", inputs: ["geometry", "takeoff", "loads"],
      detail: "Including the refusals. Accepting the calculations means accepting " +
              "the list of marks this engine would not size." },

    { id: "bom", label: "Bill of materials", short: "Quantities",
      gate: "The quantities are right and the exclusions are understood.",
      needs: "estimator", inputs: ["geometry", "takeoff", "loads", "calcs"],
      detail: "Approving this means you have read what is NOT in it — connectors, " +
              "sheathing, fasteners and anything escalated." },

    { id: "package", label: "Package for PE", short: "Ready for review",
      gate: "The package is complete enough to hand to a licensed engineer.",
      needs: "pe", inputs: ["geometry", "takeoff", "loads", "calcs", "bom"],
      detail: "This gate does NOT seal anything. It records that a licensed " +
              "engineer received a package and found it reviewable. The seal is " +
              "applied by that engineer, outside this system, under their licence." }
  ];

  function stageById(id) {
    for (var i = 0; i < STAGES.length; i++) if (STAGES[i].id === id) return STAGES[i];
    return null;
  }
  function indexOf(id) {
    for (var i = 0; i < STAGES.length; i++) if (STAGES[i].id === id) return i;
    return -1;
  }
  /* never throw on an id that is not a stage — statusOf() is public and
     localStorage is user-writable, so an unknown id will arrive one day */
  function labelOf(id) { var s = stageById(id); return s ? s.label : String(id); }

  /* Array.isArray is ES5 and, unlike `instanceof`, is right across realms. */
  var isArr = Array.isArray || function (v) {
    return Object.prototype.toString.call(v) === "[object Array]";
  };

  /* ============================================================
     THE DIGEST

     MurmurHash3, x86 128-bit variant, restricted to whole 32-bit words.
     A named, published algorithm rather than something invented here,
     because the number it produces ends up on the cover sheet of a
     package a licensed engineer is asked to seal, and "we wrote our
     own hash" is not a sentence that belongs in that conversation.

     WHY 128 BITS AND NOT THE 32 THIS FILE USED TO HAVE.

     The job is: an edit happened, and the fingerprint must change. The
     chance a single edit leaves a hash unchanged is 2^-w. At w = 32
     that is 1 in 4.3 billion PER EDIT, which sounds ample until you
     write down what one miss costs: an approval that survives the
     change it was supposed to catch, silently, on a document that
     testifies to a review. This is the failure this whole file exists
     to prevent, so buying it down to 2^-128 for roughly the same
     arithmetic per byte is not a close call. Four lanes of 32 bits
     cost less here than the old single lane did, because the old lane
     emulated its multiply with five shifts and five adds.

     The 32-bit width was also a live collision surface for a different
     reason: fingerprints are compared to each other, and a birthday
     bound of 2^16 ≈ 65,000 is inside the number of fingerprints a busy
     shop computes in a week.

     WHAT IT IS NOT. Murmur3 is not cryptographic and there is no key
     in this, so anyone who can edit the model can also compute a
     colliding model if they set out to. This detects that something
     moved. It does not prove that nobody moved it deliberately. If
     this trail ever has to survive a hostile party, that needs a
     keyed MAC and a place to keep the key, and neither exists in a
     file:// bundle.
     ============================================================ */

  /* Math.imul is ES6; the fallback is the ES5 form and is exact. */
  var imul = Math.imul || function (a, b) {
    var ah = (a >>> 16) & 0xffff, al = a & 0xffff;
    var bh = (b >>> 16) & 0xffff, bl = b & 0xffff;
    return ((al * bl) + ((((ah * bl + al * bh) & 0xffff) << 16) >>> 0)) | 0;
  };
  function rotl(x, r) { return (x << r) | (x >>> (32 - r)); }

  var C1 = 0x239b961b, C2 = 0xab0e9789, C3 = 0x38b34ae5, C4 = 0xa1e38b93;

  function Hash() {
    this.h1 = 0x9747b28c; this.h2 = 0x85ebca6b;
    this.h3 = 0xc2b2ae35; this.h4 = 0x27d4eb2f;
    this.b0 = 0; this.b1 = 0; this.b2 = 0; this.b3 = 0;
    this.n = 0; this.len = 0;
  }
  Hash.prototype.word = function (w) {
    if (this.n === 0) this.b0 = w;
    else if (this.n === 1) this.b1 = w;
    else if (this.n === 2) this.b2 = w;
    else this.b3 = w;
    this.n++; this.len++;
    if (this.n === 4) { this.block(); this.n = 0; }
  };
  Hash.prototype.block = function () {
    var k1 = this.b0, k2 = this.b1, k3 = this.b2, k4 = this.b3;
    var h1 = this.h1, h2 = this.h2, h3 = this.h3, h4 = this.h4;
    k1 = imul(k1, C1); k1 = rotl(k1, 15); k1 = imul(k1, C2); h1 ^= k1;
    h1 = rotl(h1, 19); h1 = (h1 + h2) | 0; h1 = (imul(h1, 5) + 0x561ccd1b) | 0;
    k2 = imul(k2, C2); k2 = rotl(k2, 16); k2 = imul(k2, C3); h2 ^= k2;
    h2 = rotl(h2, 17); h2 = (h2 + h3) | 0; h2 = (imul(h2, 5) + 0x0bcaa747) | 0;
    k3 = imul(k3, C3); k3 = rotl(k3, 17); k3 = imul(k3, C4); h3 ^= k3;
    h3 = rotl(h3, 15); h3 = (h3 + h4) | 0; h3 = (imul(h3, 5) + 0x96cd1c35) | 0;
    k4 = imul(k4, C4); k4 = rotl(k4, 18); k4 = imul(k4, C1); h4 ^= k4;
    h4 = rotl(h4, 13); h4 = (h4 + h1) | 0; h4 = (imul(h4, 5) + 0x32ac3b17) | 0;
    this.h1 = h1; this.h2 = h2; this.h3 = h3; this.h4 = h4;
  };
  /* A string is written LENGTH FIRST, then its UTF-16 code units packed two
     to a word. The length prefix is what makes the whole encoding injective:
     no string value, and no key name, can imitate a structural token, because
     the reader always knows how many words of text to expect. That is the
     hole the old `'"…cycle…"'` marker had — a model carrying the literal
     string "…cycle…" produced the same output as a genuine cycle. */
  Hash.prototype.text = function (s) {
    var n = s.length, i = 0;
    this.word(n);
    while (i + 1 < n) { this.word(s.charCodeAt(i) | (s.charCodeAt(i + 1) << 16)); i += 2; }
    if (i < n) this.word(s.charCodeAt(i));
  };
  function fmix(h) {
    h ^= h >>> 16; h = imul(h, 0x85ebca6b);
    h ^= h >>> 13; h = imul(h, 0xc2b2ae35);
    h ^= h >>> 16; return h >>> 0;
  }
  function hex8(x) { return ("0000000" + (x >>> 0).toString(16)).slice(-8); }
  Hash.prototype.hex = function () {
    var h1 = this.h1, h2 = this.h2, h3 = this.h3, h4 = this.h4, k;
    if (this.n > 0) { k = imul(this.b0, C1); k = rotl(k, 15); h1 ^= imul(k, C2); }
    if (this.n > 1) { k = imul(this.b1, C2); k = rotl(k, 16); h2 ^= imul(k, C3); }
    if (this.n > 2) { k = imul(this.b2, C3); k = rotl(k, 17); h3 ^= imul(k, C4); }
    var L = this.len * 4;
    h1 ^= L; h2 ^= L; h3 ^= L; h4 ^= L;
    h1 = (h1 + h2) | 0; h1 = (h1 + h3) | 0; h1 = (h1 + h4) | 0;
    h2 = (h2 + h1) | 0; h3 = (h3 + h1) | 0; h4 = (h4 + h1) | 0;
    h1 = fmix(h1); h2 = fmix(h2); h3 = fmix(h3); h4 = fmix(h4);
    h1 = (h1 + h2) | 0; h1 = (h1 + h3) | 0; h1 = (h1 + h4) | 0;
    h2 = (h2 + h1) | 0; h3 = (h3 + h1) | 0; h4 = (h4 + h1) | 0;
    return hex8(h1) + hex8(h2) + hex8(h3) + hex8(h4);
  };

  /* The same sink surface, recording the words instead of absorbing them.
     `stableString()` returns this. It is the EXACT stream the digest reads,
     so a test can prove two values are distinguished by the encoding without
     depending on the hash — and a diff of two traces points at the token
     where they part. It is a diagnostic: it builds an array as long as the
     content, which is precisely what the hash path exists to avoid. */
  function Trace() { this.out = []; }
  Trace.prototype.word = function (w) { this.out.push((w >>> 0).toString(36)); };
  Trace.prototype.text = Hash.prototype.text;
  Trace.prototype.hex = function () { return this.out.join("."); };

  /* ============================================================
     THE CANONICAL WALK

     A value is written to a sink as a stream of 32-bit words in a grammar
     that is unambiguous by construction: every value starts with a tag word,
     every string and every collection carries its own count, so one word
     stream has exactly one reading. Nothing is escaped and nothing is
     quoted, so nothing in the DATA can be mistaken for STRUCTURE.

     BOUNDED, AND BOUNDED OUT LOUD.

     A solver result is not a tree. A mark points at its solution, a solution
     at candidates, a unification move back at the marks it collapsed — so
     the graph has shared nodes and back-references. Two things follow.

     Cycles: an object already on the CURRENT PATH is written as a
     back-reference giving how many levels up it sits. That is a relative
     marker, so an object graph and a deep copy of it write the same stream.
     This is path-based detection and nothing else — there is NO seen-set.
     An earlier version of this comment claimed one; there never was one, and
     a comment describing a mechanism the code does not have is its own
     defect, because the next reader trusts it.

     Sharing: with no seen-set, a node reached down N different paths is
     walked N times. That is what keeps the fingerprint a function of content
     rather than of how the object happened to be built — two equal copies
     and one shared reference read the same — and it is why a JSON round trip
     does not change a fingerprint. The cost is that a graph with heavy
     sharing is walked once per path, which can grow much faster than the
     node count. Measured on everything this product produces: the largest is
     the whole PE package at 28,363 steps, and the worst re-walk factor is
     8.6x on a solver result. MAX_STEPS sits two orders of magnitude above
     that, and reaching it is REPORTED — see below.

     DETERMINISM. Same input, same stream, same digest, including any cut.
     Keys are sorted; there is no identity, no iteration order and no clock
     in the encoding. A fingerprint that varied with traversal luck would
     invalidate approvals at random, which is a different way of making the
     gate meaningless.
     ============================================================ */

  /* Deeper than any real structure — the deepest thing this product builds is
     the PE package at 12 — and far below the engine's stack limit. */
  var MAX_DEPTH = 512;
  /* ~70x the largest object this product has ever produced. A walk this long
     takes well under a second; it is a hang-guard, not a size limit. */
  var MAX_STEPS = 4000000;

  /* tag words. Values are arbitrary but must stay DISTINCT and must not
     change once approvals exist in the wild — changing one re-fingerprints
     every stored approval and reads as "everything moved". */
  var T_NULL = 0x01, T_UNDEF = 0x02, T_HOLE = 0x03,
      T_FALSE = 0x04, T_TRUE = 0x05,
      T_INT = 0x06, T_NUM = 0x07, T_NAN = 0x08, T_POSINF = 0x09, T_NEGINF = 0x0a,
      T_STR = 0x0b, T_FN = 0x0c,
      T_ARR = 0x0d, T_OBJ = 0x0e, T_CLASS = 0x0f,
      T_DATE = 0x10, T_REGEXP = 0x11, T_BOX = 0x12, T_ERR = 0x13,
      T_CYCLE = 0x14, T_CUT_DEPTH = 0x15, T_CUT_STEPS = 0x16;

  /* Is `k` the string form of an index below `n`? Written out rather than as
     String(k >>> 0) === k because that allocates a string for every element
     of every array, which on a 20,000-wall model is 20,000 allocations
     nobody ever looks at. */
  function isIndexKey(k, n) {
    var len = k.length, c, num, i;
    if (len === 0 || len > 10) return false;
    c = k.charCodeAt(0);
    if (c < 48 || c > 57) return false;
    if (c === 48 && len > 1) return false;      /* "01" is not an index */
    num = c - 48;
    for (i = 1; i < len; i++) {
      c = k.charCodeAt(i);
      if (c < 48 || c > 57) return false;
      num = num * 10 + (c - 48);
    }
    return num < n;
  }

  function Walk(sink) {
    this.sink = sink;
    this.steps = 0;
    this.path = [];       /* objects on the current path, for cycle detection */
    /* The key names alongside them, so a cut can say WHERE. Array indices go
       in as NUMBERS and are only formatted if a cut actually happens —
       building "[" + i + "]" per element costs an allocation per element for
       a message that is produced approximately never. */
    this.keys = [];
    this.reading = null;  /* the key being fetched, so a throwing getter can be named */
    /* One scratch key-buffer per depth, reused. The walk is depth-first, so
       at most one frame is live at each depth and they cannot collide. */
    this.pool = [];
    this.why = [];        /* named reasons the walk did not cover everything */
    this.cutDepth = false;
    this.cutSteps = false;
  }
  /* A readable path to the place the walk stopped. Elided in the middle,
     because the interesting case is 512 levels deep and a message nobody can
     read on a screen is the same as no message. */
  Walk.prototype.where = function () {
    var k = [], i;
    for (i = 0; i < this.keys.length; i++) {
      k.push(typeof this.keys[i] === "number" ? "[" + this.keys[i] + "]" : this.keys[i]);
    }
    if (this.reading !== null) k.push(this.reading);
    if (!k.length) return "the value itself";
    if (k.length <= 8) return k.join(".");
    return k.slice(0, 4).join(".") + " … (" + (k.length - 8) + " more) … " +
           k.slice(k.length - 4).join(".");
  };
  Walk.prototype.buf = function (depth) {
    var b = this.pool[depth];
    if (b === undefined) { b = []; this.pool[depth] = b; }
    else b.length = 0;
    return b;
  };
  Walk.prototype.cutBySteps = function (s) {
    if (!this.cutSteps) {
      this.cutSteps = true;
      this.why.push("this content needed more than " + MAX_STEPS + " steps to read in full, so " +
                    "the fingerprint covers only part of it — reached at " + this.where());
    }
    s.word(T_CUT_STEPS);
  };
  Walk.prototype.number = function (v) {
    var s = this.sink;
    /* -0 is written as 0. A sign on a zero is not a change to a drawing, and
       JSON does not preserve it, so treating them as different would make a
       save-and-reload invalidate approvals. Stated because it is a choice. */
    if (v === (v | 0)) { s.word(T_INT); s.word(v | 0); return; }
    if (v !== v) { s.word(T_NAN); return; }
    if (v === Infinity) { s.word(T_POSINF); return; }
    if (v === -Infinity) { s.word(T_NEGINF); return; }
    /* String() of a double is the shortest decimal that reads back to the
       same double, so it is exactly injective: two different numbers never
       write the same text. The old code wrote
       String(Math.round(v * 1e6) / 1e6), which quantised — every value within
       1e-6 of another collided, a DCR of 0.9999996 and one of 1.0000004 both
       became "1", and every magnitude above 1.798e302 overflowed the multiply
       and became the literal "Infinity", so the whole top of the double range
       shared one fingerprint. A tolerance you cannot see is not a tolerance. */
    s.word(T_NUM); s.text(String(v));
  };
  Walk.prototype.value = function (v, depth) {
    var s = this.sink, t;

    if (++this.steps > MAX_STEPS) { this.cutBySteps(s); return; }

    if (v === null) { s.word(T_NULL); return; }
    t = typeof v;
    if (t === "number") { this.number(v); return; }
    /* A string is charged for its length BEFORE it is written, so one
       enormous string cannot walk past the budget on its own. */
    if (t === "string") {
      this.steps += (v.length >>> 3);
      if (this.steps > MAX_STEPS) { this.cutBySteps(s); return; }
      s.word(T_STR); s.text(v); return;
    }
    if (t === "boolean") { s.word(v ? T_TRUE : T_FALSE); return; }
    if (t === "undefined") { s.word(T_UNDEF); return; }
    /* A rebuilt closure is not a content change. As an OBJECT PROPERTY a
       function is dropped entirely, key and all (see `object` below) — that
       is the long-standing contract and `planset.sheets[].render` depends on
       it. As an ARRAY ELEMENT it cannot be dropped without shifting every
       index after it, so it is written as its own tag. The old walk wrote
       "null" there, which collided with a genuine null. */
    if (t === "function") { s.word(T_FN); return; }

    /* objects from here down */
    var path = this.path;
    for (var c = path.length - 1; c >= 0; c--) {
      if (path[c] === v) { s.word(T_CYCLE); s.word(path.length - c); return; }
    }

    if (depth >= MAX_DEPTH) {
      if (!this.cutDepth) {
        this.cutDepth = true;
        this.why.push("this content nests more than " + MAX_DEPTH + " levels deep, so the " +
                      "fingerprint covers only the top of it — reached at " + this.where());
      }
      s.word(T_CUT_DEPTH);
      return;
    }

    path.push(v);
    if (isArr(v)) this.array(v, depth);
    else this.object(v, depth);
    path.pop();
  };
  Walk.prototype.array = function (v, depth) {
    var s = this.sink, n = v.length, i, k, probe, extra;
    var d1 = depth + 1, kp = this.keys, slot = kp.length;
    s.word(T_ARR); s.word(n);
    kp.push(0);
    for (i = 0; i < n; i++) {
      kp[slot] = i;
      /* a hole and an explicit undefined are different facts; JSON cannot
         tell them apart, this can */
      if (i in v) this.value(v[i], d1);
      else s.word(T_HOLE);
    }
    kp.pop();
    /* An array may carry own properties that are not indices. JSON drops
       them, so the old walk did too — which meant [1,2] and an [1,2] with a
       .note on it fingerprinted the same. They are written after the
       elements, count first, so the usual empty case costs one word. */
    extra = this.buf(depth);
    for (k in v) {
      if (!Object.prototype.hasOwnProperty.call(v, k)) continue;
      if (k === "length" || isIndexKey(k, n)) continue;
      this.reading = k;
      probe = v[k];
      this.reading = null;
      if (typeof probe === "function" || probe === undefined) continue;
      extra.push(k);
    }
    if (extra.length > 1) extra.sort();
    s.word(extra.length);
    for (i = 0; i < extra.length; i++) {
      k = extra[i];
      s.text(k);
      kp.push(k);
      this.value(v[k], d1);
      kp.pop();
    }
  };
  Walk.prototype.object = function (v, depth) {
    var s = this.sink, k, i, probe, keys = this.buf(depth);
    var d1 = depth + 1, kp = this.keys;
    var cls = Object.prototype.toString.call(v);

    if (cls === "[object Object]") {
      s.word(T_OBJ);
    } else {
      /* Class matters. `new Date(0)` and `new Date(1)` have NO own enumerable
         properties, so the old walk wrote "{}" for both — and for `{}`, and
         for a RegExp, and for an Error. Two models differing only in a date
         had the same fingerprint. */
      s.word(T_CLASS); s.text(cls);
      if (cls === "[object Date]") {
        s.word(T_DATE);
        var ms; try { ms = Date.prototype.getTime.call(v); } catch (e) { ms = NaN; }
        this.number(ms);
      } else if (cls === "[object RegExp]") {
        s.word(T_REGEXP);
        var src; try { src = RegExp.prototype.toString.call(v); } catch (e2) { src = "?"; }
        s.text(String(src));
      } else if (cls === "[object String]" || cls === "[object Number]" || cls === "[object Boolean]") {
        s.word(T_BOX);
        var prim; try { prim = v.valueOf(); } catch (e3) { prim = null; }
        this.value(prim, depth + 1);
      } else if (cls === "[object Error]") {
        /* name and message are own but NOT enumerable, so the key walk below
           cannot see them and every Error would read alike */
        s.word(T_ERR);
        s.text(String(v.name)); s.text(String(v.message));
      }
    }

    /* A function-valued property and an undefined-valued one are dropped key
       and all: the first because a rebuilt closure is not a content change,
       the second because JSON drops it, so keeping it would make a save and
       reload look like an edit. The count below is of what is actually
       written, so the stream stays unambiguous. */
    for (k in v) {
      if (!Object.prototype.hasOwnProperty.call(v, k)) continue;
      this.reading = k;                 /* so a getter that throws is named */
      probe = v[k];
      this.reading = null;
      if (typeof probe === "function" || probe === undefined) continue;
      keys.push(k);
    }
    /* sort() is UTF-16 code-unit order — total, and the same in every engine */
    if (keys.length > 1) keys.sort();
    s.word(keys.length);
    for (i = 0; i < keys.length; i++) {
      k = keys[i];
      s.text(k);
      kp.push(k);
      this.value(v[k], d1);
      kp.pop();
    }
  };

  /* The marker on a fingerprint that could not be taken in full. Chosen so it
     can never appear in a hex digest, so a complete and an incomplete
     fingerprint can never compare equal. */
  var PARTIAL = "!";

  /* fingerprintOf(v) -> { fp, complete, why: [ ... ], steps }

     `complete:false` means the digest does not cover all of the content. It
     is still deterministic and still usable as a cache key, but it is NOT
     something an approval may stand on, and every caller in this file
     treats it that way. */
  function fingerprintOf(v) {
    var sink = new Hash();
    var w = new Walk(sink);
    var failed = null;
    try {
      w.value(v, 0);
    } catch (e) {
      /* A getter that throws, an exotic host object, a stack the engine gave
         up on. Whatever it was, we did not read all of the content, and the
         one thing we must not do is return a confident digest of a partial
         read. */
      failed = (e && e.message) ? e.message : String(e);
      w.why.push("reading this content threw at " + w.where() + " — " + failed);
    }
    var complete = !w.cutDepth && !w.cutSteps && !failed;
    return {
      fp: (complete ? "" : PARTIAL) + sink.hex(),
      complete: complete,
      why: w.why,
      steps: w.steps
    };
  }

  function fingerprint(v) { return fingerprintOf(v).fp; }

  /* The canonical word stream as text. Diagnostics and tests only. */
  function stableString(v) {
    var sink = new Trace();
    var w = new Walk(sink);
    try { w.value(v, 0); } catch (e) { sink.word(0xffffffff); }
    return sink.hex();
  }

  /* ---------------- state ----------------

     { stages: { id: {status, by, at, note, fp, sawFp} }, trail: [...], dropped: n }
       status : "pending" | "approved" | "rejected" | "stale"
       fp     : the fingerprint of THIS stage's own content when approved
       sawFp  : {inputStageId: fp} — what the approver was looking at upstream */

  var state = null;

  function blank() { return { stages: {}, trail: [], dropped: 0 }; }

  function load() {
    if (state) return state;
    try {
      var raw = localStorage.getItem(KEY);
      state = raw ? JSON.parse(raw) : blank();
    } catch (e) { state = blank(); }
    if (!state || typeof state !== "object") state = blank();
    /* `if (!state.trail)` let a truthy non-array through, and a hand-written
       {"trail":"notanarray"} threw on the run screen — taking the audit trail
       card with it, which is the one card whose footer reads "a clean history
       is not the goal; a true one is". Storage is user-writable; shape-check
       it, do not truth-check it. */
    if (!state.stages || typeof state.stages !== "object" || isArr(state.stages)) state.stages = {};
    if (!isArr(state.trail)) state.trail = [];
    if (typeof state.dropped !== "number" || !isFinite(state.dropped) || state.dropped < 0) state.dropped = 0;
    return state;
  }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(load())); } catch (e) {}
  }

  function now() { return new Date().toISOString(); }

  /* The trail is append-only, but a browser's storage is not infinite, so it
     is capped. The cap USED to drop the oldest entries silently, which is the
     same defect as a truncated fingerprint wearing different clothes: the
     record shrank and nothing said so. Now the loss is itself an entry. */
  var TRAIL_MAX = 400;

  function trim(s) {
    if (s.trail.length <= TRAIL_MAX) return;
    var over = s.trail.length - TRAIL_MAX + 1;   /* +1 leaves room for the marker */
    var lost = 0, i;
    for (i = 0; i < over; i++) {
      lost += (s.trail[i] && s.trail[i].kind === "truncated") ? 0 : 1;
    }
    s.trail = s.trail.slice(over);
    s.dropped += lost;
    s.trail.unshift({
      kind: "truncated", stage: null, count: s.dropped, at: now(), by: "(the record itself)",
      note: s.dropped + " earlier entr" + (s.dropped === 1 ? "y is" : "ies are") + " not in this " +
            "trail. This browser keeps the most recent " + TRAIL_MAX + "; the rest are gone. This " +
            "line is here so that is visible rather than assumed."
    });
  }

  function log(entry) {
    var s = load();
    entry.at = now();
    var u = FM.auth && FM.auth.state().user;
    entry.by = u ? u.name : "(not signed in)";
    s.trail.push(entry);
    trim(s);
    save();
  }

  /* ---------------- content ----------------

     The pipeline does not own the artefacts; it observes them. A provider is
     registered per stage and returns whatever that stage's content currently
     is. Modules register themselves so pipeline.js does not have to know how
     to reach into any of them.

     ONE READ OF THE WORLD PER PUBLIC CALL. Every entry point below opens a
     read scope; every provider is called at most once inside it and its
     fingerprint is taken at most once. Two reasons, and the second is the
     one that matters:

       - snapshot() used to call statusOf() and can() for six stages, each of
         which re-read and re-fingerprinted every upstream stage. That was
         about 70 fingerprints of the same content per render.
       - approve() checked the gate, then took the fingerprint. Two reads.
         The fingerprint it wrote was therefore not provably the fingerprint
         of the content the gate had just validated. Now it is the same read,
         so the record says what was checked.

     The scope lives for exactly one call and is thrown away, so it can never
     go stale — there is no invalidate() to forget. */

  var providers = {};
  function provide(stageId, fn) { providers[stageId] = fn; }

  var blockerFns = {};
  function blocksOn(stageId, fn) { blockerFns[stageId] = fn; }

  var scope = null, scopeDepth = 0;
  function begin() { if (scopeDepth++ === 0) scope = { read: {}, blocked: {} }; }
  function end() { if (--scopeDepth <= 0) { scopeDepth = 0; scope = null; } }

  /* -> { has, content, threw, digest } — the content only. */
  function readStage(stageId) {
    if (scope && Object.prototype.hasOwnProperty.call(scope.read, stageId)) return scope.read[stageId];
    var r = { has: false, content: null, threw: null, digest: null };
    if (providers[stageId]) {
      var c = null;
      try { c = providers[stageId](); }
      catch (e) {
        /* A provider that threw and a provider with nothing to show are
           different facts. This used to return null for both, so a stage
           whose content BLEW UP reported "there is nothing to approve yet". */
        r.threw = (e && e.message) ? e.message : String(e);
        c = null;
      }
      if (c !== null && c !== undefined) { r.has = true; r.content = c; }
    }
    if (scope) scope.read[stageId] = r;
    return r;
  }

  /* Taken LAZILY and at most once per read, because on a large model it is
     the most expensive thing this file does and most of the six stages on a
     run screen have no question outstanding that the answer could settle.
     Nothing that could open a gate skips it — see `canInner`.

     The shape is normalised on the way out, and `why` is guaranteed to be an
     array even when it is empty. Every caller of this is on the path whose
     whole job is to EXPLAIN why a fingerprint is not whole, so a caller that
     throws while describing the problem takes down the mechanism that
     protects the approval guarantee, and does it precisely when that
     mechanism has something to say. An empty list is an answer; undefined is
     a second failure on top of the first. */
  function digestOf(read) {
    if (read.digest) return read.digest;
    var d = null;
    if (read.has) {
      try { d = fingerprintOf(read.content); }
      catch (e) {
        /* fingerprintOf catches everything the walk can throw. Reaching here
           means the failure was in the machinery itself — a stack the engine
           gave up on inside the handler, most likely. Fail closed. */
        d = { fp: PARTIAL + "00000000000000000000000000000000", complete: false,
              why: ["the fingerprint of this content could not be taken at all — " +
                    ((e && e.message) ? e.message : String(e))], steps: 0 };
      }
    }
    if (!d || typeof d !== "object") d = { fp: null, complete: true, why: [], steps: 0 };
    if (!isArr(d.why)) d.why = [];
    if (typeof d.complete !== "boolean") d.complete = false;
    read.digest = d;
    return d;
  }

  /* Reasons, joined, never empty — see the note on digestOf. */
  function whyText(list) {
    return (isArr(list) && list.length) ? list.join("; ")
         : "no reason was recorded, which is itself a defect in this check";
  }

  function contentOf(stageId) {
    begin();
    try { return readStage(stageId).content; } finally { end(); }
  }

  /* Stages may register hard blockers — a CAD model with validation errors, a
     takeoff with unresolved items. These are not warnings; they stop the gate. */
  function blockers(stageId) {
    if (scope && Object.prototype.hasOwnProperty.call(scope.blocked, stageId)) return scope.blocked[stageId];
    var out;
    if (!blockerFns[stageId]) out = [];
    else {
      try {
        var r = blockerFns[stageId]();
        out = isArr(r) ? r : [];
      } catch (e) { out = ["could not check this stage: " + ((e && e.message) || String(e))]; }
    }
    if (scope) scope.blocked[stageId] = out;
    return out;
  }

  /* Why a stage's content cannot carry an approval right now, in the words
     that go on screen and onto S5.0 of the package. Empty means it can. */
  function unusable(stageId, read) {
    var label = labelOf(stageId);
    if (read.threw) {
      return [label + " could not be read at all: " + read.threw + ". A stage that threw is " +
              "not a stage with nothing in it, and neither one can be approved."];
    }
    if (!read.has) return [];        /* "nothing yet" is said elsewhere, once */
    var d = digestOf(read);
    if (!d.complete) {
      return [label + " cannot be fingerprinted in full, so an approval could not be tied to " +
              "it — " + whyText(d.why) + ". An approval recorded against a partial " +
              "fingerprint could not be falsified by a change to the part that was not read, " +
              "which is not an approval."];
    }
    return [];
  }

  /* ---------------- the rule ----------------

     A stage is APPROVED only if it was approved AND nothing it depends on has
     moved since — including itself. Anything else is stale, and stale says
     exactly which input moved. */

  function statusOfInner(stageId) {
    var s = load();
    var rec = s.stages[stageId];

    /* localStorage is user-writable: a record that is not an object is not a
       record. Treat it as nothing rather than reading fields off a string. */
    if (rec && (typeof rec !== "object" || isArr(rec))) {
      return { status: "pending", rec: null, moved: [], unreadable: true };
    }
    if (!rec || rec.status !== "approved") {
      return { status: rec ? rec.status : "pending", rec: rec || null, moved: [] };
    }

    /* An approval with NO FINGERPRINT can never be falsified, so it is not an
       approval — it is a claim. This happens two ways: a record hand-written
       into localStorage, or approve() writing one when a provider threw
       between the gate check and the write. Both must read stale. */
    if (typeof rec.fp !== "string" || !rec.fp) {
      return { status: "stale", rec: rec, moved: [{
        stage: stageId, label: labelOf(stageId), self: true,
        why: "this approval carries no fingerprint, so there is nothing to check it against"
      }] };
    }
    /* Nor may one stand on a fingerprint that was never complete. approve()
       refuses to write these; a hand-written record can still carry one. */
    if (rec.fp.charAt(0) === PARTIAL) {
      return { status: "stale", rec: rec, moved: [{
        stage: stageId, label: labelOf(stageId), self: true,
        why: "this approval was recorded against a fingerprint that does not cover all of " +
             "the content, so a change to the part it never read could not falsify it"
      }] };
    }

    var moved = [];
    var st = stageById(stageId);

    /* CONTENT GONE IS NOT CONTENT UNCHANGED.
       This read `mine !== null && rec.fp && mine !== rec.fp`, so when a stage's
       content became unavailable — the model deleted, the plan cleared — fpOf()
       returned null, BOTH comparisons were skipped, and the approval stood.
       Delete the geometry after approving all six and the run reported
       "6/6 STAGES APPROVED · Ready for PE", with one card simultaneously saying
       APPROVED and "cannot be approved: no geometry yet". The false trail then
       printed on the PE package's cover sheet.

       That is precisely the defect the comment at the top of this file says the
       fingerprint exists to prevent — the audit trail testifying to a review
       that did not happen — and the check had a hole in exactly the shape of
       the thing it was guarding. Disappearing is the most complete change a
       stage's content can undergo.

       CONTENT THAT CAN NO LONGER BE READ IN FULL is the same shape again, one
       step subtler: the fingerprint still comes back, it just no longer covers
       everything. It must not be compared as though it did. */
    var me = readStage(stageId), meD;
    if (me.threw) {
      moved.push({ stage: stageId, label: labelOf(stageId), self: true,
                   why: "reading this stage's content threw — " + me.threw });
    } else if (!me.has) {
      moved.push({ stage: stageId, label: labelOf(stageId), self: true,
                   why: "the content this stage was approved on is no longer there" });
    } else if (!(meD = digestOf(me)).complete) {
      moved.push({ stage: stageId, label: labelOf(stageId), self: true,
                   why: "this stage's content can no longer be fingerprinted in full, so the " +
                        "approval cannot be checked against it — " + whyText(meD.why) });
    } else if (meD.fp !== rec.fp) {
      moved.push({ stage: stageId, label: labelOf(stageId), self: true });
    }

    if (!st) return { status: moved.length ? "stale" : "approved", rec: rec, moved: moved };

    for (var i = 0; i < st.inputs.length; i++) {
      var upId = st.inputs[i], upLabel = labelOf(upId);
      var up = readStage(upId), upD;
      var upThen = (rec.sawFp && typeof rec.sawFp === "object" && !isArr(rec.sawFp))
                 ? rec.sawFp[upId] : null;
      if (typeof upThen !== "string" || !upThen || upThen.charAt(0) === PARTIAL) {
        /* approved without recording what it saw upstream, or recorded a
           fingerprint that never covered it — same unfalsifiable shape as a
           missing self-fingerprint */
        moved.push({ stage: upId, label: upLabel, self: false,
                     why: "this approval did not record a usable fingerprint of " + upLabel });
      } else if (up.threw) {
        moved.push({ stage: upId, label: upLabel, self: false,
                     why: "reading " + upLabel + "'s content threw — " + up.threw });
      } else if (!up.has) {
        moved.push({ stage: upId, label: upLabel, self: false,
                     why: upLabel + "'s content is no longer there" });
      } else if (!(upD = digestOf(up)).complete) {
        moved.push({ stage: upId, label: upLabel, self: false,
                     why: upLabel + "'s content can no longer be fingerprinted in full — " +
                          whyText(upD.why) });
      } else if (upD.fp !== upThen) {
        moved.push({ stage: upId, label: upLabel, self: false });
      }
    }
    return { status: moved.length ? "stale" : "approved", rec: rec, moved: moved };
  }

  function statusOf(stageId) {
    begin();
    try { return statusOfInner(stageId); } finally { end(); }
  }

  /* Can this stage be approved right now? */
  function canInner(stageId) {
    var st = stageById(stageId);
    if (!st) return { ok: false, blockedBy: ["no such stage"] };
    var blocked = [], i;

    if (!FM.auth || !FM.auth.require()) blocked.push("nobody is signed in");
    else if (!FM.auth.has(st.needs)) {
      blocked.push("this gate needs the " +
        (FM.auth.ROLES[st.needs] ? FM.auth.ROLES[st.needs].label : st.needs) + " role");
    }

    for (i = 0; i < st.inputs.length; i++) {
      var up = statusOfInner(st.inputs[i]);
      if (up.status !== "approved") {
        blocked.push(labelOf(st.inputs[i]) + " is " + up.status + " — approve it first");
      }
    }

    var me = readStage(stageId);
    if (!me.has && !me.threw) {
      blocked.push("there is nothing to approve yet — " + st.label.toLowerCase() +
                   " has produced no content");
    }
    if (me.threw) blocked = blocked.concat(unusable(stageId, me));

    /* a stage that declares blocking problems cannot be approved past them */
    var b = blockers(stageId);
    for (var j = 0; j < b.length; j++) blocked.push(b[j]);

    /* THE FINGERPRINT CHECK IS LAST AND CONDITIONAL, and that ordering is
       load-bearing rather than an optimisation with a nice story.

       Taking a fingerprint is the expensive thing this file does, and the run
       screen calls this for six stages on every render. So it is skipped
       exactly when the gate is already shut for a reason that is already
       being reported — and run, always, whenever the gate would otherwise be
       OPEN. No stage can become approvable without its own content and every
       input's content having been proved fingerprintable in full first.

       An approval also records what it saw upstream, so an upstream stage
       whose fingerprint is not whole blocks this gate too: otherwise the tie
       to it would be a tie to a partial reading. */
    if (!blocked.length) {
      blocked = blocked.concat(unusable(stageId, me));
      for (i = 0; i < st.inputs.length; i++) {
        blocked = blocked.concat(unusable(st.inputs[i], readStage(st.inputs[i])));
      }
    }

    return { ok: blocked.length === 0, blockedBy: blocked };
  }

  function can(stageId) {
    begin();
    try { return canInner(stageId); } finally { end(); }
  }

  function approve(stageId, note) {
    begin();
    try {
      var gate = canInner(stageId);
      if (!gate.ok) return { ok: false, why: gate.blockedBy };

      var st = stageById(stageId);
      var u = FM.auth.state().user;

      /* The SAME read the gate just validated — see the scope note above.
         Belt and braces on top of it: an approval whose fingerprint is
         missing or partial is unfalsifiable, so writing one is worse than
         not approving at all. */
      var me = readStage(stageId), meD = digestOf(me);
      if (!me.has || !meD.complete || typeof meD.fp !== "string") {
        return { ok: false, why: ["this stage's content could not be read in full at the moment " +
                                  "of approval, so there is nothing to record the approval against"] };
      }
      var saw = {}, blind = [];
      for (var i = 0; i < st.inputs.length; i++) {
        var up = readStage(st.inputs[i]), upD = digestOf(up);
        if (!up.has || !upD.complete || typeof upD.fp !== "string") blind.push(labelOf(st.inputs[i]));
        else saw[st.inputs[i]] = upD.fp;
      }
      if (blind.length) {
        return { ok: false, why: ["could not read " + blind.join(" and ") + " in full at the " +
                                  "moment of approval, so this approval could not be tied to " +
                                  (blind.length === 1 ? "it" : "them")] };
      }

      load().stages[stageId] = {
        status: "approved",
        by: u.name, byId: u.id, role: st.needs,
        at: now(), note: note || "",
        fp: meD.fp, sawFp: saw
      };
      save();
      log({ kind: "approve", stage: stageId, note: note || "", fp: meD.fp });
      return { ok: true };
    } finally { end(); }
  }

  function reject(stageId, note) {
    if (!FM.auth || !FM.auth.require()) return { ok: false, why: ["nobody is signed in"] };
    load().stages[stageId] = {
      status: "rejected",
      by: FM.auth.state().user.name, at: now(), note: note || "", fp: null, sawFp: null
    };
    save();
    log({ kind: "reject", stage: stageId, note: note || "" });
    return { ok: true };
  }

  function clear(stageId) {
    delete load().stages[stageId];
    save();
    log({ kind: "clear", stage: stageId });
  }

  function reset() {
    state = blank();
    save();
    log({ kind: "reset", stage: null, note: "pipeline reset" });
  }

  /* The whole picture, for the view and for the package's approval trail.
     One read scope for the entire snapshot, so every row describes the same
     instant rather than six successive ones. */
  function snapshot() {
    begin();
    try {
      var out = { stages: [], current: null, complete: true, staleCount: 0, notFingerprintable: 0 };
      for (var i = 0; i < STAGES.length; i++) {
        var st = STAGES[i];
        var s = statusOfInner(st.id);
        var gate = canInner(st.id);
        var read = readStage(st.id);
        /* Whatever THIS call had reason to compute — see digestOf(). null
           means no decision in this snapshot turned on it, not that it is
           unknowable. */
        var d = read.digest;
        var row = {
          stage: st, status: s.status, rec: s.rec, moved: s.moved,
          can: gate.ok, blockedBy: gate.blockedBy,
          blockers: blockers(st.id),
          hasContent: read.has,
          threw: read.threw,
          fpNow: d ? d.fp : null,
          fpComplete: d ? d.complete : null,
          fpWhy: d ? d.why : []
        };
        if (s.status === "stale") out.staleCount++;
        if (d && read.has && !d.complete) out.notFingerprintable++;
        if (s.status !== "approved") {
          out.complete = false;
          if (!out.current) out.current = st.id;
        }
        out.stages.push(row);
      }
      if (!out.current) out.current = STAGES[STAGES.length - 1].id;
      return out;
    } finally { end(); }
  }

  function audit() { return load().trail.slice(); }
  function trailDropped() { return load().dropped; }

  FM.pipeline = {
    STAGES: STAGES,
    stageById: stageById,
    indexOf: indexOf,
    provide: provide,
    blocksOn: blocksOn,
    contentOf: contentOf,
    fingerprint: fingerprint,
    fingerprintOf: fingerprintOf,
    stableString: stableString,
    statusOf: statusOf,
    can: can,
    approve: approve,
    reject: reject,
    clear: clear,
    reset: reset,
    snapshot: snapshot,
    audit: audit,
    trailDropped: trailDropped,
    LIMITS: { maxDepth: MAX_DEPTH, maxSteps: MAX_STEPS, bits: 128, trail: TRAIL_MAX },
    state: function () { return load(); }
  };
})();
